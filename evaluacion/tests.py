from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Asignatura, Intento, ItemPrueba, Opcion, Pregunta, Prueba, Respuesta
from .services import cerrar_prueba, enviar_respuestas, habilitar_prueba, iniciar_intento, preguntas_para_estudiante


class DatosDiagnostico(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.docente = get_user_model().objects.create_user('docente', is_staff=True)
        cls.otro_docente = get_user_model().objects.create_user('otro', is_staff=True)
        cls.asignatura = Asignatura.objects.get(codigo='ESP')
        cls.prueba = Prueba.objects.create(titulo='Diagnóstico de muestra', docente=cls.docente, asignatura=cls.asignatura, grado=2)
        cls.preguntas = []
        cls.items = []
        for numero in range(1, 4):
            pregunta = Pregunta.objects.create(
                codigo=f'ESP-2-{numero:03}', asignatura=cls.asignatura, grado=2,
                enunciado=f'Pregunta de prueba {numero}', referencia='Referencia ficticia para pruebas automatizadas.',
            )
            Opcion.objects.bulk_create([
                Opcion(pregunta=pregunta, letra=letra, texto=f'Opción {letra}', es_correcta=letra == 'A')
                for letra in 'ABCD'
            ])
            cls.preguntas.append(pregunta)
            cls.items.append(ItemPrueba.objects.create(prueba=cls.prueba, pregunta=pregunta, orden=numero))

    def abrir(self):
        return habilitar_prueba(self.prueba.pk, docente=self.docente)

    def iniciar(self, identificador='EST-01'):
        return iniciar_intento(self.prueba.codigo, identificador, acompanamiento=Intento.Acompanamiento.INDIVIDUAL)

    def respuestas(self, letra='A'):
        return {item.pk: letra for item in self.items}


class FlujoDiagnosticoTests(DatosDiagnostico):
    def test_migracion_crea_solo_las_cuatro_asignaturas(self):
        self.assertSetEqual(set(Asignatura.objects.values_list('codigo', flat=True)), {'ESP', 'MAT', 'NAT', 'SOC'})

    def test_flujo_califica_y_registra_resultado(self):
        self.abrir()
        intento = self.iniciar()
        self.assertIsNone(intento.porcentaje)
        respuestas = self.respuestas()
        respuestas[self.items[-1].pk] = 'B'
        resultado = enviar_respuestas(intento.token, respuestas)
        self.assertEqual(resultado.total_preguntas, 3)
        self.assertEqual(resultado.aciertos, 2)
        self.assertEqual(resultado.porcentaje, Decimal('66.7'))
        self.assertEqual(resultado.respuestas.count(), 3)
        self.assertEqual(resultado.respuestas.filter(es_correcta=True).count(), 2)
        self.assertIsNotNone(resultado.enviado_en)

    def test_todos_los_aciertos_y_cero_aciertos(self):
        self.abrir()
        for identificador, letra, esperado in [('EST-01', 'A', '100.0'), ('EST-02', 'B', '0.0')]:
            with self.subTest(identificador=identificador):
                resultado = enviar_respuestas(self.iniciar(identificador).token, self.respuestas(letra))
                self.assertEqual(resultado.porcentaje, Decimal(esperado))

    def test_envio_repetido_conserva_primer_resultado(self):
        self.abrir()
        intento = self.iniciar()
        primero = enviar_respuestas(intento.token, self.respuestas())
        segundo = enviar_respuestas(intento.token, self.respuestas('B'))
        self.assertEqual(primero.enviado_en, segundo.enviado_en)
        self.assertEqual(segundo.aciertos, 3)
        self.assertEqual(Respuesta.objects.count(), 3)

    def test_rechaza_envios_incompletos_ajenos_e_invalidos_sin_guardar(self):
        self.abrir()
        intento = self.iniciar()
        casos = [
            {}, {self.items[0].pk: 'A'}, {**self.respuestas(), 999999: 'A'},
            {**self.respuestas(), self.items[1].pk: 'E'},
            {**self.respuestas(), self.items[1].pk: ['A']},
            {**self.respuestas(), str(self.items[0].pk): 'A'},
            {True: 'A'}, ['A', 'A', 'A'],
        ]
        for respuestas in casos:
            with self.subTest(respuestas=respuestas), self.assertRaises(ValidationError):
                enviar_respuestas(intento.token, respuestas)
            self.assertFalse(intento.respuestas.exists())
            intento.refresh_from_db()
            self.assertIsNone(intento.enviado_en)

    def test_acepta_identificadores_de_item_como_texto(self):
        self.abrir()
        resultado = enviar_respuestas(self.iniciar().token, {str(item.pk): 'A' for item in self.items})
        self.assertEqual(resultado.aciertos, 3)

    def test_correcciones_del_banco_no_cambian_prueba_habilitada(self):
        self.abrir()
        pregunta = self.preguntas[0]
        pregunta.enunciado = 'Texto corregido después de habilitar'
        pregunta.save()
        pregunta.opciones.filter(letra='A').update(es_correcta=False)
        pregunta.opciones.filter(letra='B').update(es_correcta=True, texto='Texto nuevo')
        intento = self.iniciar()
        visibles = preguntas_para_estudiante(intento.token)
        self.assertEqual(visibles[0]['enunciado'], 'Pregunta de prueba 1')
        self.assertEqual(visibles[0]['opciones']['B'], 'Opción B')
        resultado = enviar_respuestas(intento.token, self.respuestas())
        self.assertEqual(resultado.aciertos, 3)

    def test_contenido_estudiante_no_incluye_claves_ni_justificaciones(self):
        self.abrir()
        for item in preguntas_para_estudiante(self.iniciar().token):
            self.assertSetEqual(set(item), {'id', 'orden', 'enunciado', 'opciones'})

    def test_identificador_repetido_no_crea_intento_ni_revela_token(self):
        self.abrir()
        self.iniciar(' est-01 ')
        with self.assertRaises(ValidationError):
            self.iniciar('EST-01')
        self.assertEqual(Intento.objects.count(), 1)

    def test_cuatro_estudiantes_tienen_resultados_separados(self):
        self.abrir()
        for numero in range(4):
            intento = self.iniciar(f'EST-{numero}')
            enviar_respuestas(intento.token, self.respuestas('A' if numero % 2 else 'B'))
        self.assertEqual(Intento.objects.count(), 4)
        self.assertEqual(Respuesta.objects.count(), 12)
        self.assertEqual(Intento.objects.filter(aciertos=3).count(), 2)

    def test_cierre_impide_iniciar_y_enviar_pero_conserva_resultados(self):
        self.abrir()
        enviado = enviar_respuestas(self.iniciar('EST-01').token, self.respuestas())
        pendiente = self.iniciar('EST-02')
        cerrar_prueba(self.prueba.pk, docente=self.docente)
        with self.assertRaises(ValidationError):
            self.iniciar('EST-03')
        with self.assertRaises(ValidationError):
            enviar_respuestas(pendiente.token, self.respuestas())
        self.assertEqual(enviar_respuestas(enviado.token, self.respuestas()).aciertos, 3)

    def test_borrador_no_permite_intentos(self):
        with self.assertRaises(ValidationError):
            self.iniciar()

    def test_identificador_y_acompanamiento_invalidos(self):
        self.abrir()
        for identificador in ['', '   ', 'X' * 51]:
            with self.subTest(identificador=identificador), self.assertRaises(ValidationError):
                self.iniciar(identificador)
        with self.assertRaises(ValidationError):
            iniciar_intento(self.prueba.codigo, 'EST-01', acompanamiento='INVENTADO')

    def test_otro_docente_no_puede_habilitar_ni_cerrar(self):
        with self.assertRaises(PermissionDenied):
            habilitar_prueba(self.prueba.pk, docente=self.otro_docente)
        self.abrir()
        with self.assertRaises(PermissionDenied):
            cerrar_prueba(self.prueba.pk, docente=self.otro_docente)


class IntegridadTests(DatosDiagnostico):
    def test_rechaza_pregunta_incompleta_y_revierte_copias(self):
        self.preguntas[-1].opciones.filter(letra='D').delete()
        with self.assertRaises(ValidationError):
            self.abrir()
        self.prueba.refresh_from_db()
        self.assertEqual(self.prueba.estado, Prueba.Estado.BORRADOR)
        self.assertFalse(self.prueba.items.exclude(contenido={}).exists())

    def test_rechaza_preguntas_inactivas_sin_clave_o_sin_texto(self):
        pregunta = self.preguntas[0]
        pregunta.activa = False
        pregunta.save()
        with self.assertRaises(ValidationError):
            self.abrir()
        pregunta.activa = True
        pregunta.save()
        pregunta.opciones.update(es_correcta=False)
        with self.assertRaises(ValidationError):
            self.abrir()
        pregunta.opciones.filter(letra='A').update(es_correcta=True, texto='   ')
        with self.assertRaises(ValidationError):
            self.abrir()

    def test_rechaza_prueba_sin_preguntas(self):
        self.prueba.items.all().delete()
        with self.assertRaises(ValidationError):
            self.abrir()

    def test_rechaza_pregunta_de_otro_grado_o_asignatura(self):
        pregunta = self.preguntas[0]
        for campo, valor in [('grado', 3), ('asignatura', Asignatura.objects.get(codigo='MAT'))]:
            with self.subTest(campo=campo):
                anterior = getattr(pregunta, campo)
                setattr(pregunta, campo, valor)
                pregunta.save()
                with self.assertRaises(ValidationError):
                    self.abrir()
                setattr(pregunta, campo, anterior)
                pregunta.save()

    def test_bd_impide_dos_claves_y_opciones_duplicadas(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.preguntas[0].opciones.filter(letra='B').update(es_correcta=True)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Opcion.objects.create(pregunta=self.preguntas[0], letra='A', texto='Duplicada')

    def test_bd_impide_grados_y_asignaturas_fuera_de_alcance(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Pregunta.objects.filter(pk=self.preguntas[0].pk).update(grado=4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Asignatura.objects.create(codigo='ING')

    def test_bd_impide_preguntas_repetidas_y_orden_fuera_de_rango(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ItemPrueba.objects.create(prueba=self.prueba, pregunta=self.preguntas[0], orden=4)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ItemPrueba.objects.filter(pk=self.items[0].pk).update(orden=21)

    def test_bd_impide_respuestas_duplicadas_y_puntaje_imposible(self):
        self.abrir()
        intento = enviar_respuestas(self.iniciar().token, self.respuestas())
        with self.assertRaises(IntegrityError), transaction.atomic():
            Respuesta.objects.create(intento=intento, item=self.items[0], opcion='B', es_correcta=False)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Intento.objects.filter(pk=intento.pk).update(aciertos=4)

    def test_validacion_impide_respuesta_de_otra_prueba(self):
        self.abrir()
        intento = self.iniciar()
        otra = Prueba.objects.create(titulo='Otra', grado=2, asignatura=self.asignatura, docente=self.docente)
        item = ItemPrueba.objects.create(prueba=otra, pregunta=self.preguntas[0], orden=1)
        with self.assertRaises(ValidationError):
            Respuesta(intento=intento, item=item, opcion='A', es_correcta=False).full_clean()

    def test_no_rehabilita_ni_cambia_grado_de_prueba_publicada(self):
        self.abrir()
        with self.assertRaises(ValidationError):
            self.abrir()
        self.prueba.refresh_from_db()
        self.prueba.grado = 3
        with self.assertRaises(ValidationError):
            self.prueba.full_clean()


class AdministracionTests(DatosDiagnostico):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('admin', password='solo-pruebas')
        self.client.force_login(self.admin)

    def test_paginas_principales_del_administrador(self):
        self.abrir()
        intento = enviar_respuestas(self.iniciar().token, self.respuestas())
        urls = [
            reverse('admin:evaluacion_asignatura_changelist'),
            reverse('admin:evaluacion_pregunta_changelist'),
            reverse('admin:evaluacion_pregunta_change', args=[self.preguntas[0].pk]),
            reverse('admin:evaluacion_prueba_add'),
            reverse('admin:evaluacion_prueba_change', args=[self.prueba.pk]),
            reverse('admin:evaluacion_intento_changelist'),
            reverse('admin:evaluacion_intento_change', args=[intento.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_cambiar_clave_desde_admin_no_viola_restriccion(self):
        pregunta = self.preguntas[0]
        datos = {
            'codigo': pregunta.codigo, 'asignatura': self.asignatura.pk, 'grado': 2,
            'enunciado': pregunta.enunciado, 'referencia': pregunta.referencia, 'activa': 'on',
            'opciones-TOTAL_FORMS': 4, 'opciones-INITIAL_FORMS': 4,
            'opciones-MIN_NUM_FORMS': 0, 'opciones-MAX_NUM_FORMS': 4,
        }
        for indice, opcion in enumerate(pregunta.opciones.all()):
            datos.update({f'opciones-{indice}-id': opcion.pk, f'opciones-{indice}-letra': opcion.letra,
                          f'opciones-{indice}-texto': opcion.texto, f'opciones-{indice}-pregunta': pregunta.pk})
            if opcion.letra == 'B':
                datos[f'opciones-{indice}-es_correcta'] = 'on'
        url = reverse('admin:evaluacion_pregunta_change', args=[pregunta.pk])
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context.get('errors'))
        self.assertEqual(pregunta.opciones.get(es_correcta=True).letra, 'B')

    def test_admin_rechaza_pregunta_con_opciones_incompletas(self):
        datos = {
            'codigo': 'NUEVA', 'asignatura': self.asignatura.pk, 'grado': 2,
            'enunciado': 'Pregunta', 'referencia': 'Referencia de prueba',
            'opciones-TOTAL_FORMS': 1, 'opciones-INITIAL_FORMS': 0,
            'opciones-MIN_NUM_FORMS': 0, 'opciones-MAX_NUM_FORMS': 4,
            'opciones-0-letra': 'A', 'opciones-0-texto': 'Texto', 'opciones-0-es_correcta': 'on',
        }
        respuesta = self.client.post(reverse('admin:evaluacion_pregunta_add'), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Pregunta.objects.filter(codigo='NUEVA').exists())

    def test_docente_no_consulta_pruebas_ni_resultados_ajenos(self):
        self.abrir()
        intento = self.iniciar()
        permisos = Permission.objects.filter(content_type__app_label='evaluacion')
        self.otro_docente.user_permissions.set(permisos)
        self.client.force_login(self.otro_docente)
        for modelo, pk in [('prueba', self.prueba.pk), ('intento', intento.pk)]:
            lista = self.client.get(reverse(f'admin:evaluacion_{modelo}_changelist'))
            self.assertEqual(lista.context['cl'].result_count, 0)
            detalle = self.client.get(reverse(f'admin:evaluacion_{modelo}_change', args=[pk]))
            self.assertEqual(detalle.status_code, 302)

    def test_admin_habilita_y_bloquea_edicion_de_items(self):
        url = reverse('admin:evaluacion_prueba_changelist')
        respuesta = self.client.post(url, {'action': 'habilitar_seleccionadas', '_selected_action': [self.prueba.pk]})
        self.assertEqual(respuesta.status_code, 302)
        self.prueba.refresh_from_db()
        self.assertEqual(self.prueba.estado, Prueba.Estado.ABIERTA)
        pagina = self.client.get(reverse('admin:evaluacion_prueba_change', args=[self.prueba.pk]))
        inline = pagina.context['inline_admin_formsets'][0]
        self.assertFalse(inline.has_change_permission)
        self.assertFalse(inline.has_add_permission)
        self.assertFalse(inline.has_delete_permission)

    def test_admin_crea_pregunta_y_prueba_completas(self):
        datos = {
            'codigo': 'NUEVA', 'asignatura': self.asignatura.pk, 'grado': 2,
            'enunciado': 'Pregunta nueva', 'referencia': 'Referencia de prueba', 'activa': 'on',
            'opciones-TOTAL_FORMS': 4, 'opciones-INITIAL_FORMS': 0,
            'opciones-MIN_NUM_FORMS': 0, 'opciones-MAX_NUM_FORMS': 4,
        }
        for indice, letra in enumerate('ABCD'):
            datos.update({f'opciones-{indice}-letra': letra, f'opciones-{indice}-texto': f'Opción {letra}'})
        datos['opciones-2-es_correcta'] = 'on'
        respuesta = self.client.post(reverse('admin:evaluacion_pregunta_add'), datos)
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context.get('errors'))
        pregunta = Pregunta.objects.get(codigo='NUEVA')
        self.assertEqual(pregunta.opciones.get(es_correcta=True).letra, 'C')
        datos_prueba = {
            'titulo': 'Prueba desde el administrador', 'asignatura': self.asignatura.pk, 'grado': 2,
            'items-TOTAL_FORMS': 1, 'items-INITIAL_FORMS': 0,
            'items-MIN_NUM_FORMS': 0, 'items-MAX_NUM_FORMS': 20,
            'items-0-pregunta': pregunta.pk, 'items-0-orden': 1,
        }
        respuesta = self.client.post(reverse('admin:evaluacion_prueba_add'), datos_prueba)
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context.get('errors'))
        prueba = Prueba.objects.get(titulo=datos_prueba['titulo'])
        self.assertEqual(prueba.docente, self.admin)
        self.assertEqual(prueba.items.get().pregunta, pregunta)
        habilitar_prueba(prueba.pk, docente=self.admin)

    def test_admin_rechaza_prueba_nueva_con_pregunta_de_otro_grado(self):
        datos = {
            'titulo': 'Prueba incoherente', 'asignatura': self.asignatura.pk, 'grado': 1,
            'items-TOTAL_FORMS': 1, 'items-INITIAL_FORMS': 0,
            'items-MIN_NUM_FORMS': 0, 'items-MAX_NUM_FORMS': 20,
            'items-0-pregunta': self.preguntas[0].pk, 'items-0-orden': 1,
        }
        respuesta = self.client.post(reverse('admin:evaluacion_prueba_add'), datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Prueba.objects.filter(titulo='Prueba incoherente').exists())

    def test_admin_permite_reordenar_borrador_sin_perder_items(self):
        datos = {
            'titulo': self.prueba.titulo, 'asignatura': self.asignatura.pk, 'grado': 2,
            'items-TOTAL_FORMS': 3, 'items-INITIAL_FORMS': 3,
            'items-MIN_NUM_FORMS': 0, 'items-MAX_NUM_FORMS': 20,
        }
        for indice, item in enumerate(self.items):
            datos.update({
                f'items-{indice}-id': item.pk, f'items-{indice}-prueba': self.prueba.pk,
                f'items-{indice}-pregunta': item.pregunta_id, f'items-{indice}-orden': 3 - indice,
            })
        respuesta = self.client.post(reverse('admin:evaluacion_prueba_change', args=[self.prueba.pk]), datos)
        self.assertEqual(respuesta.status_code, 302, respuesta.context and respuesta.context.get('errors'))
        self.assertEqual(list(self.prueba.items.values_list('pk', flat=True)), [item.pk for item in reversed(self.items)])
        self.abrir()
