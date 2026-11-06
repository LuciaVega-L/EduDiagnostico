"""Comprobación aislada de escrituras simultáneas sobre SQLite en disco."""

import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'edudiagnostico.settings')
    from django.conf import settings

    with tempfile.TemporaryDirectory(prefix='edudiagnostico_sqlite_') as carpeta:
        settings.DATABASES['default']['NAME'] = str(Path(carpeta) / 'concurrencia.sqlite3')
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        from django.core.management import call_command
        from django.db import connections
        from evaluacion.models import Asignatura, Intento, ItemPrueba, Opcion, Pregunta, Prueba, Respuesta
        from evaluacion.services import enviar_respuestas, habilitar_prueba, iniciar_intento

        try:
            call_command('migrate', verbosity=0, interactive=False)
            docente = get_user_model().objects.create_user('docente-prueba', is_staff=True)
            area = Asignatura.objects.get(codigo='ESP')
            prueba = Prueba.objects.create(titulo='Prueba temporal', docente=docente, asignatura=area, grado=1)
            for numero in range(1, 4):
                pregunta = Pregunta.objects.create(
                    codigo=f'TEMP-{numero}', asignatura=area, grado=1,
                    enunciado='Texto ficticio', referencia='Prueba técnica',
                )
                Opcion.objects.bulk_create([
                    Opcion(pregunta=pregunta, letra=letra, texto=letra, es_correcta=letra == 'A')
                    for letra in 'ABCD'
                ])
                ItemPrueba.objects.create(prueba=prueba, pregunta=pregunta, orden=numero)
            habilitar_prueba(prueba.pk, docente=docente)
            respuestas = {item.pk: 'A' for item in prueba.items.all()}
            barrera = Barrier(4)

            def responder(numero):
                try:
                    barrera.wait(timeout=10)
                    intento = iniciar_intento(prueba.codigo, f'EST-{numero}', acompanamiento='GRUPO_CUATRO')
                    return enviar_respuestas(intento.token, respuestas).aciertos
                finally:
                    connections.close_all()

            with ThreadPoolExecutor(max_workers=4) as equipo:
                puntajes = list(equipo.map(responder, range(4)))
            if puntajes != [3, 3, 3, 3] or Intento.objects.count() != 4 or Respuesta.objects.count() != 12:
                raise AssertionError('Los resultados concurrentes no corresponden a cuatro intentos independientes.')
            print('OK: cuatro estudiantes concurrentes, 4 intentos y 12 respuestas separadas.')

            intento = iniciar_intento(prueba.codigo, 'REINTENTO', acompanamiento='INDIVIDUAL')
            barrera = Barrier(4)

            def repetir(numero):
                try:
                    barrera.wait(timeout=10)
                    return enviar_respuestas(intento.token, respuestas).aciertos
                finally:
                    connections.close_all()

            with ThreadPoolExecutor(max_workers=4) as equipo:
                puntajes = list(equipo.map(repetir, range(4)))
            if puntajes != [3, 3, 3, 3] or intento.respuestas.count() != 3:
                raise AssertionError('El envío repetido produjo respuestas o resultados inconsistentes.')
            print('OK: cuatro envíos concurrentes del mismo intento guardan solo 3 respuestas.')
        finally:
            connections.close_all()


if __name__ == '__main__':
    main()
