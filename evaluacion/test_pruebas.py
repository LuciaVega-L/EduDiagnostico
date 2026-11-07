from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from .models import Intento, ItemPrueba, Pregunta, Prueba


class PrepararPruebasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('importar_banco', stdout=StringIO())
        cls.docente = get_user_model().objects.create_user('admin', password='x', is_staff=True)

    def test_crea_doce_pruebas_abiertas_con_las_veinte_preguntas_del_banco(self):
        call_command('preparar_pruebas', stdout=StringIO())
        pruebas = Prueba.objects.filter(docente=self.docente, estado=Prueba.Estado.ABIERTA)
        self.assertEqual(pruebas.count(), 12)
        self.assertEqual(ItemPrueba.objects.filter(prueba__in=pruebas).count(), 240)
        for prueba in pruebas:
            items = list(prueba.items.select_related('pregunta').order_by('orden'))
            self.assertEqual([i.orden for i in items], list(range(1, 21)))
            self.assertTrue(all(i.pregunta.grado == prueba.grado and i.pregunta.asignatura_id == prueba.asignatura_id for i in items))
            self.assertTrue(all(i.contenido.get('correcta') in 'ABCD' for i in items))
        self.assertEqual(ItemPrueba.objects.filter(prueba__in=pruebas).values('pregunta').distinct().count(), 240)

    def test_repetir_reutiliza_las_pruebas_abiertas(self):
        call_command('preparar_pruebas', stdout=StringIO())
        codigos = set(Prueba.objects.values_list('codigo', flat=True))
        salida = StringIO()
        call_command('preparar_pruebas', stdout=salida)
        self.assertEqual(set(Prueba.objects.values_list('codigo', flat=True)), codigos)
        self.assertIn('0 nuevas', salida.getvalue())

    def test_filtros_por_grado_y_asignatura(self):
        call_command('preparar_pruebas', grado=1, asignatura='MAT', stdout=StringIO())
        prueba = Prueba.objects.get()
        self.assertEqual((prueba.grado, prueba.asignatura.codigo, prueba.items.count()), (1, 'MAT', 20))

    def test_requiere_docente_y_banco(self):
        with self.assertRaises(CommandError):
            call_command('preparar_pruebas', docente='nadie', stdout=StringIO())
        Pregunta.objects.filter(grado=3, asignatura__codigo='SOC').update(activa=False)
        with self.assertRaises(CommandError):
            call_command('preparar_pruebas', stdout=StringIO())
        self.assertFalse(Prueba.objects.exists())

    def test_estudiante_responde_una_prueba_completa(self):
        call_command('preparar_pruebas', grado=3, asignatura='NAT', stdout=StringIO())
        prueba = Prueba.objects.get()
        datos = {'codigo': prueba.codigo, 'identificador': 'EST-20', 'acompanamiento': 'INDIVIDUAL'}
        self.assertRedirects(self.client.post(reverse('evaluacion:ingreso'), datos), reverse('evaluacion:responder'))
        intento = Intento.objects.get()
        items = list(prueba.items.all())
        envio = {'intento_id': intento.pk, **{f'pregunta_{i.pk}': i.contenido['correcta'] for i in items}}
        self.assertRedirects(self.client.post(reverse('evaluacion:responder'), envio), reverse('evaluacion:finalizado'))
        intento.refresh_from_db()
        self.assertEqual(intento.aciertos, 20)
