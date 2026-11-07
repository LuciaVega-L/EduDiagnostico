from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from evaluacion.models import GRADOS, Asignatura, ItemPrueba, Pregunta, Prueba
from evaluacion.services import habilitar_prueba

NOMBRES_GRADO = {1: 'primero', 2: 'segundo', 3: 'tercero'}
ORDEN_ASIGNATURAS = ['ESP', 'MAT', 'NAT', 'SOC']


def titulo_prueba(grado, asignatura):
    return f'Diagnóstico — {asignatura}, ingreso a {NOMBRES_GRADO[grado]}'


class Command(BaseCommand):
    help = ('Crea y habilita las pruebas diagnósticas completas (20 preguntas) de cada grado y asignatura. '
            'Reutiliza las pruebas abiertas del docente y no duplica registros.')

    def add_arguments(self, parser):
        parser.add_argument('--docente', default='admin')
        parser.add_argument('--grado', type=int, choices=[g for g, _ in GRADOS],
                            help='Limita la preparación a un grado de ingreso (1, 2 o 3).')
        parser.add_argument('--asignatura', choices=ORDEN_ASIGNATURAS,
                            help='Limita la preparación a una asignatura (ESP, MAT, NAT o SOC).')

    @transaction.atomic
    def handle(self, *args, **options):
        docente = get_user_model().objects.filter(username=options['docente'], is_active=True, is_staff=True).first()
        if not docente:
            raise CommandError('Debe existir la cuenta docente activa indicada.')
        grados = [options['grado']] if options['grado'] else [g for g, _ in GRADOS]
        codigos = [options['asignatura']] if options['asignatura'] else ORDEN_ASIGNATURAS
        asignaturas = {a.codigo: a for a in Asignatura.objects.filter(codigo__in=codigos)}
        if len(asignaturas) != len(codigos):
            raise CommandError('Faltan asignaturas en la base. Ejecute migrate antes de este comando.')

        creadas = 0
        for grado in grados:
            for codigo in codigos:
                asignatura = asignaturas[codigo]
                titulo = titulo_prueba(grado, asignatura)
                prueba = Prueba.objects.filter(titulo=titulo, docente=docente, estado=Prueba.Estado.ABIERTA).first()
                if prueba is None:
                    preguntas = list(Pregunta.objects.filter(grado=grado, asignatura=asignatura, activa=True).order_by('codigo'))
                    if not 1 <= len(preguntas) <= 20:
                        raise CommandError(f'{titulo}: se encontraron {len(preguntas)} preguntas activas. '
                                           'Ejecute importar_banco o revise las preguntas inactivas.')
                    prueba = Prueba.objects.create(titulo=titulo, docente=docente, grado=grado, asignatura=asignatura)
                    ItemPrueba.objects.bulk_create([
                        ItemPrueba(prueba=prueba, pregunta=pregunta, orden=orden)
                        for orden, pregunta in enumerate(preguntas, 1)
                    ])
                    try:
                        habilitar_prueba(prueba.pk, docente=docente)
                    except ValidationError as error:
                        raise CommandError(f'{titulo}: {"; ".join(error.messages)}') from error
                    prueba.refresh_from_db()
                    creadas += 1
                self.stdout.write(f'{prueba.codigo}  {titulo} ({prueba.items.count()} preguntas)')
        self.stdout.write(self.style.SUCCESS(
            f'Pruebas disponibles: {len(grados) * len(codigos)} ({creadas} nuevas). '
            'Use un identificador ficticio nuevo por intento.'))
