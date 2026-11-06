"""Operaciones del diagnóstico; las futuras vistas deben usar estas funciones."""

from collections.abc import Mapping

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Intento, Prueba, Respuesta


def _prueba_del_docente(prueba_id, docente):
    prueba = Prueba.objects.get(pk=prueba_id)
    if not docente.is_authenticated or not docente.is_active or not docente.is_staff:
        raise PermissionDenied('Se requiere una cuenta docente activa.')
    if not docente.is_superuser and prueba.docente_id != docente.pk:
        raise PermissionDenied('Esta prueba pertenece a otro docente.')
    return prueba


@transaction.atomic
def habilitar_prueba(prueba_id, *, docente):
    prueba = _prueba_del_docente(prueba_id, docente)
    if prueba.estado != Prueba.Estado.BORRADOR:
        raise ValidationError('Solo se puede habilitar una prueba en borrador.')
    prueba.full_clean()
    items = list(prueba.items.select_related('pregunta').prefetch_related('pregunta__opciones'))
    if not 1 <= len(items) <= 20:
        raise ValidationError('La prueba debe tener entre 1 y 20 preguntas.')
    for item in items:
        item.full_clean(exclude=['contenido'])
        pregunta = item.pregunta
        pregunta.full_clean()
        opciones = list(pregunta.opciones.all())
        if not pregunta.activa:
            raise ValidationError(f'La pregunta {pregunta.codigo} está inactiva.')
        if {op.letra for op in opciones} != set('ABCD') or len(opciones) != 4:
            raise ValidationError(f'{pregunta.codigo} debe tener las cuatro opciones A, B, C y D.')
        correctas = [op.letra for op in opciones if op.es_correcta]
        if len(correctas) != 1 or any(not op.texto.strip() for op in opciones):
            raise ValidationError(f'{pregunta.codigo} requiere opciones con texto y una sola respuesta correcta.')
        item.contenido = {
            'codigo': pregunta.codigo,
            'enunciado': pregunta.enunciado,
            'opciones': {op.letra: op.texto for op in opciones},
            'correcta': correctas[0],
            'referencia': pregunta.referencia,
            'justificacion': pregunta.justificacion,
            'guia_aplicacion': pregunta.guia_aplicacion,
        }
        item.save(update_fields=['contenido'])
    prueba.estado = Prueba.Estado.ABIERTA
    prueba.habilitada_en = timezone.now()
    prueba.save(update_fields=['estado', 'habilitada_en'])
    return prueba


@transaction.atomic
def cerrar_prueba(prueba_id, *, docente):
    prueba = _prueba_del_docente(prueba_id, docente)
    if prueba.estado != Prueba.Estado.ABIERTA:
        raise ValidationError('Solo se puede cerrar una prueba abierta.')
    prueba.estado = Prueba.Estado.CERRADA
    prueba.save(update_fields=['estado'])
    return prueba


@transaction.atomic
def iniciar_intento(codigo, identificador, *, acompanamiento, observaciones_apoyo=''):
    if not isinstance(codigo, str) or not isinstance(identificador, str):
        raise ValidationError('El código y el identificador deben ser texto.')
    codigo = codigo.strip().upper()
    identificador = identificador.strip().upper()
    if not identificador or len(identificador) > 50:
        raise ValidationError('El identificador debe tener entre 1 y 50 caracteres.')
    prueba = Prueba.objects.filter(codigo=codigo, estado=Prueba.Estado.ABIERTA).first()
    if prueba is None:
        raise ValidationError('El código no corresponde a una prueba abierta.')
    if Intento.objects.filter(prueba=prueba, identificador=identificador).exists():
        # No devolver el token de otra sesión con solo conocer el identificador.
        raise ValidationError('Este identificador ya tiene un intento. Continúe en su sesión original.')
    intento = Intento(
        prueba=prueba, identificador=identificador, acompanamiento=acompanamiento,
        observaciones_apoyo=observaciones_apoyo, total_preguntas=prueba.items.count(),
    )
    intento.full_clean()
    intento.save()
    return intento


def preguntas_para_estudiante(token):
    """Devuelve únicamente el contenido visible, sin claves ni justificaciones."""
    intento = Intento.objects.get(token=token)
    if intento.enviado_en or intento.prueba.estado != Prueba.Estado.ABIERTA:
        raise ValidationError('El intento no está disponible para responder.')
    return [
        {'id': item.pk, 'orden': item.orden, 'enunciado': item.contenido['enunciado'],
         'opciones': dict(item.contenido['opciones'])}
        for item in intento.prueba.items.all()
    ]


@transaction.atomic
def enviar_respuestas(token, respuestas):
    """Recibe {id_item: letra}; envío completo, atómico e idempotente."""
    intento = Intento.objects.select_related('prueba').get(token=token)
    if intento.enviado_en:
        return intento
    if intento.prueba.estado != Prueba.Estado.ABIERTA:
        raise ValidationError('La prueba está cerrada y no admite respuestas.')
    if not isinstance(respuestas, Mapping):
        raise ValidationError('Las respuestas deben relacionar cada pregunta con una opción.')
    normalizadas = {}
    for clave, valor in respuestas.items():
        if isinstance(clave, bool) or not str(clave).isascii() or not str(clave).isdigit():
            raise ValidationError('Identificador de pregunta inválido.')
        item_id = int(clave)
        if item_id in normalizadas:
            raise ValidationError('Una pregunta no puede aparecer dos veces.')
        normalizadas[item_id] = valor
    items = list(intento.prueba.items.all())
    if set(normalizadas) != {item.pk for item in items}:
        raise ValidationError('Debe responder todas las preguntas de esta prueba y ninguna de otra prueba.')
    registros = []
    for item in items:
        opcion = normalizadas[item.pk]
        if not isinstance(opcion, str) or opcion not in item.contenido['opciones']:
            raise ValidationError('Seleccione una opción válida para cada pregunta.')
        registros.append(Respuesta(
            intento=intento, item=item, opcion=opcion,
            es_correcta=opcion == item.contenido['correcta'],
        ))
    Respuesta.objects.bulk_create(registros)
    intento.aciertos = sum(respuesta.es_correcta for respuesta in registros)
    intento.enviado_en = timezone.now()
    intento.save(update_fields=['aciertos', 'enviado_en'])
    return intento
