from django.test import Client
from django.urls import reverse

from .models import Intento, Respuesta
from .services import cerrar_prueba
from .tests import DatosDiagnostico
from .views import CLAVE_SESION


class RecorridoEstudianteTests(DatosDiagnostico):
    def setUp(self):
        self.abrir()
        self.datos_ingreso = {'codigo': self.prueba.codigo, 'identificador': 'EST-01', 'acompanamiento': 'INDIVIDUAL'}

    def entrar(self, cliente=None):
        cliente = cliente or self.client
        respuesta = cliente.post(reverse('evaluacion:ingreso'), self.datos_ingreso)
        self.assertRedirects(respuesta, reverse('evaluacion:responder'))
        return Intento.objects.get(token=cliente.session[CLAVE_SESION])

    def envio(self, intento):
        return {'intento_id': intento.pk, **{f'pregunta_{item.pk}': 'A' for item in self.items}}

    def test_recorrido_completo_guarda_resultado_y_permite_otro_estudiante(self):
        inicio = self.client.get(reverse('evaluacion:ingreso'))
        self.assertContains(inicio, 'Entra a tu prueba')
        intento = self.entrar()
        pagina = self.client.get(reverse('evaluacion:responder'))
        self.assertContains(pagina, self.preguntas[0].enunciado)
        self.assertNotContains(pagina, str(intento.token))
        self.assertNotContains(pagina, 'correcta')
        resultado = self.client.post(reverse('evaluacion:responder'), self.envio(intento))
        self.assertRedirects(resultado, reverse('evaluacion:finalizado'))
        intento.refresh_from_db()
        self.assertEqual(intento.aciertos, 3)
        self.assertEqual(intento.respuestas.count(), 3)
        self.assertContains(self.client.get(reverse('evaluacion:finalizado')), 'Tus respuestas quedaron guardadas')
        self.assertRedirects(self.client.post(reverse('evaluacion:salir')), reverse('evaluacion:ingreso'))
        self.assertNotIn(CLAVE_SESION, self.client.session)

    def test_sin_sesion_no_se_accede_a_prueba_ni_confirmacion(self):
        for nombre in ['responder', 'finalizado']:
            with self.subTest(nombre=nombre):
                self.assertRedirects(self.client.get(reverse(f'evaluacion:{nombre}')), reverse('evaluacion:ingreso'))

    def test_codigo_invalido_no_crea_intentos(self):
        respuesta = self.client.post(reverse('evaluacion:ingreso'), {**self.datos_ingreso, 'codigo': 'NOEXISTE'})
        self.assertContains(respuesta, 'no corresponde a una prueba abierta')
        self.assertEqual(Intento.objects.count(), 0)

    def test_ingreso_repetido_misma_sesion_no_duplica_intento(self):
        self.entrar()
        self.entrar()
        self.assertEqual(Intento.objects.count(), 1)

    def test_otra_sesion_no_puede_recuperar_intento_por_identificador(self):
        self.entrar()
        otro = Client()
        respuesta = otro.post(reverse('evaluacion:ingreso'), self.datos_ingreso)
        self.assertContains(respuesta, 'ya tiene un intento')
        self.assertNotIn(CLAVE_SESION, otro.session)

    def test_envio_incompleto_conserva_seleccion_y_muestra_error(self):
        intento = self.entrar()
        datos = self.envio(intento)
        datos.pop(f'pregunta_{self.items[-1].pk}')
        respuesta = self.client.post(reverse('evaluacion:responder'), datos)
        self.assertContains(respuesta, 'Selecciona una respuesta.')
        self.assertEqual(respuesta.context['form'][f'pregunta_{self.items[0].pk}'].value(), 'A')
        self.assertFalse(Respuesta.objects.exists())

    def test_rechaza_pregunta_ajena_opcion_invalida_y_pagina_de_otro_intento(self):
        intento = self.entrar()
        for cambios in [{'pregunta_999999': 'A'}, {f'pregunta_{self.items[0].pk}': 'Z'}, {'intento_id': intento.pk + 1}]:
            with self.subTest(cambios=cambios):
                pagina = self.client.post(reverse('evaluacion:responder'), {**self.envio(intento), **cambios})
                self.assertEqual(pagina.status_code, 200)
                self.assertTrue(pagina.context['form'].errors)
                self.assertFalse(Respuesta.objects.exists())

    def test_no_permite_dos_valores_para_una_pregunta(self):
        intento = self.entrar()
        pagina = self.client.post(reverse('evaluacion:responder'), {**self.envio(intento), f'pregunta_{self.items[0].pk}': ['A', 'B']})
        self.assertContains(pagina, 'Selecciona una sola respuesta')
        self.assertFalse(Respuesta.objects.exists())

    def test_reenvio_http_no_duplica_resultado(self):
        intento = self.entrar()
        for _ in range(2):
            self.assertRedirects(self.client.post(reverse('evaluacion:responder'), self.envio(intento)), reverse('evaluacion:finalizado'))
        self.assertEqual(Respuesta.objects.count(), 3)

    def test_prueba_cerrada_muestra_mensaje_y_permite_salir(self):
        self.entrar()
        cerrar_prueba(self.prueba.pk, docente=self.docente)
        self.assertContains(self.client.get(reverse('evaluacion:responder')), 'Esta prueba ya está cerrada')
        self.assertRedirects(self.client.post(reverse('evaluacion:salir')), reverse('evaluacion:ingreso'))

    def test_no_abandona_intento_pendiente_por_get_o_post_salir(self):
        self.entrar()
        self.assertEqual(self.client.get(reverse('evaluacion:salir')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('evaluacion:salir')), reverse('evaluacion:responder'))

    def test_csrf_requerido_y_formulario_correcto_aceptado(self):
        cliente = Client(enforce_csrf_checks=True)
        self.assertEqual(cliente.post(reverse('evaluacion:ingreso'), self.datos_ingreso).status_code, 403)
        cliente.get(reverse('evaluacion:ingreso'))
        token = cliente.cookies['csrftoken'].value
        self.assertRedirects(cliente.post(reverse('evaluacion:ingreso'), {**self.datos_ingreso, 'csrfmiddlewaretoken': token}), reverse('evaluacion:responder'))
        intento = Intento.objects.get(token=cliente.session[CLAVE_SESION])
        self.assertEqual(cliente.post(reverse('evaluacion:responder'), self.envio(intento)).status_code, 403)

    def test_paginas_privadas_no_se_cachean(self):
        self.entrar()
        self.assertIn('no-store', self.client.get(reverse('evaluacion:responder'))['Cache-Control'])
