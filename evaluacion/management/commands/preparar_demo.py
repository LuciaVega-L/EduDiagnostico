from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from evaluacion.models import ItemPrueba, Pregunta, Prueba
from evaluacion.services import habilitar_prueba


class Command(BaseCommand):
    help = 'Prepara una prueba técnica de tres preguntas del banco para ingreso a segundo en Español.'

    def add_arguments(self, parser):
        parser.add_argument('--docente', default='admin')

    @transaction.atomic
    def handle(self, *args, **options):
        docente = get_user_model().objects.filter(username=options['docente'], is_active=True, is_staff=True).first()
        if not docente:
            raise CommandError('Debe existir la cuenta docente activa indicada.')
        titulo = 'Práctica técnica — Español, ingreso a segundo'
        prueba = Prueba.objects.filter(titulo=titulo, docente=docente, estado=Prueba.Estado.ABIERTA).first()
        if prueba is None:
            preguntas = list(Pregunta.objects.filter(codigo__in=['2-ESP-01', '2-ESP-02', '2-ESP-03']).order_by('codigo'))
            if len(preguntas) != 3:
                raise CommandError('Primero ejecute importar_banco para cargar las preguntas de la práctica.')
            prueba = Prueba.objects.create(titulo=titulo, docente=docente, grado=2, asignatura=preguntas[0].asignatura)
            for orden, pregunta in enumerate(preguntas, 1):
                ItemPrueba.objects.create(prueba=prueba, pregunta=pregunta, orden=orden)
            habilitar_prueba(prueba.pk, docente=docente)
        self.stdout.write(self.style.SUCCESS(f'Prueba disponible. Código: {prueba.codigo}. Use un identificador ficticio nuevo por intento.'))
