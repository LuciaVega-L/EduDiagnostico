from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.test import TestCase

from .banco import leer_banco
from .models import Opcion, Pregunta


class ImportacionBancoTests(TestCase):
    ruta = settings.BASE_DIR / 'docs' / 'EduDiagnostico_Banco_de_Preguntas.docx'

    def test_lectura_preserva_unicode_ids_y_claves_del_documento(self):
        preguntas = leer_banco(self.ruta)
        self.assertEqual(len(preguntas), 240)
        primera = preguntas[0]
        self.assertEqual(primera['codigo'], '1-MAT-01')
        self.assertIn('★ ★ ★ ★ ★ ★', primera['enunciado'])
        self.assertEqual(primera['opciones'][primera['correcta']], '6')
        self.assertEqual(next(p for p in preguntas if p['codigo'] == '1-CN-01')['asignatura'], 'NAT')

    def test_comprobacion_no_escribe(self):
        call_command('importar_banco', comprobar=True, stdout=StringIO())
        self.assertEqual(Pregunta.objects.count(), 0)

    def test_importacion_completa_y_repeticion_sin_duplicados(self):
        call_command('importar_banco', stdout=StringIO())
        call_command('importar_banco', stdout=StringIO())
        self.assertEqual(Pregunta.objects.count(), 240)
        self.assertEqual(Opcion.objects.count(), 960)
        grupos = Pregunta.objects.values('grado', 'asignatura').annotate(total=Count('id'))
        self.assertEqual(len(grupos), 12)
        self.assertTrue(all(grupo['total'] == 20 for grupo in grupos))

    def test_conflicto_revierte_importacion_y_conserva_edicion(self):
        call_command('importar_banco', stdout=StringIO())
        pregunta = Pregunta.objects.get(codigo='3-SOC-20')
        pregunta.enunciado = 'Edición del docente'
        pregunta.save()
        Pregunta.objects.filter(codigo='1-MAT-01').delete()
        with self.assertRaises(CommandError):
            call_command('importar_banco', stdout=StringIO())
        self.assertFalse(Pregunta.objects.filter(codigo='1-MAT-01').exists())
        pregunta.refresh_from_db()
        self.assertEqual(pregunta.enunciado, 'Edición del docente')

    def test_error_de_lectura_se_informa_sin_escribir(self):
        with patch('evaluacion.management.commands.importar_banco.leer_banco', side_effect=ValueError('Banco incompleto')):
            with self.assertRaisesMessage(CommandError, 'Banco incompleto'):
                call_command('importar_banco', stdout=StringIO())
        self.assertEqual(Pregunta.objects.count(), 0)
