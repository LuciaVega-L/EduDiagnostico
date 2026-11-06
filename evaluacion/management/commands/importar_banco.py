from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from evaluacion.banco import leer_banco
from evaluacion.models import Asignatura, Opcion, Pregunta


class Command(BaseCommand):
    help = 'Importa el banco Word de 240 preguntas sin duplicar ni sobrescribir preguntas existentes.'

    def add_arguments(self, parser):
        parser.add_argument('archivo', nargs='?', type=Path, default=settings.BASE_DIR / 'docs' / 'EduDiagnostico_Banco_de_Preguntas.docx')
        parser.add_argument('--comprobar', action='store_true', help='Valida el documento sin escribir en la base.')

    def handle(self, *args, **options):
        try:
            preguntas = leer_banco(options['archivo'])
            if options['comprobar']:
                self.stdout.write(self.style.SUCCESS('Documento válido: 240 preguntas, 12 bancos y 960 opciones.'))
                return
            nuevas = 0
            with transaction.atomic():
                asignaturas = {a.codigo: a for a in Asignatura.objects.all()}
                for datos in preguntas:
                    pregunta = Pregunta.objects.filter(codigo=datos['codigo']).first()
                    if pregunta:
                        opciones = {op.letra: (op.texto, op.es_correcta) for op in pregunta.opciones.all()}
                        esperado = {letra: (texto, letra == datos['correcta']) for letra, texto in datos['opciones'].items()}
                        if (pregunta.enunciado != datos['enunciado'] or pregunta.grado != datos['grado']
                                or pregunta.asignatura_id != asignaturas[datos['asignatura']].pk or opciones != esperado):
                            raise CommandError(f'{pregunta.codigo} difiere del documento. No se sobrescribió ningún registro; revise la diferencia.')
                        continue
                    pregunta = Pregunta(
                        codigo=datos['codigo'], grado=datos['grado'], asignatura=asignaturas[datos['asignatura']],
                        enunciado=datos['enunciado'], referencia=datos['referencia'],
                        guia_aplicacion='Definir el apoyo permitido con el docente antes de la aplicación. No leer en voz alta lo que el ítem pretenda evaluar como lectura independiente.',
                    )
                    pregunta.full_clean()
                    pregunta.save()
                    Opcion.objects.bulk_create([
                        Opcion(pregunta=pregunta, letra=letra, texto=texto, es_correcta=letra == datos['correcta'])
                        for letra, texto in datos['opciones'].items()
                    ])
                    nuevas += 1
        except (ValueError, ValidationError, KeyError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f'Importación completa: {nuevas} nuevas; {240 - nuevas} existentes conservadas.'))
