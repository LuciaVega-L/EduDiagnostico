import secrets
import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


GRADOS = [(1, 'Primero'), (2, 'Segundo'), (3, 'Tercero')]
LETRAS = [(letra, letra) for letra in 'ABCD']


def generar_codigo():
    return secrets.token_hex(5).upper()


class Asignatura(models.Model):
    class Codigo(models.TextChoices):
        ESP = 'ESP', 'Español'
        MAT = 'MAT', 'Matemáticas'
        NAT = 'NAT', 'Ciencias Naturales'
        SOC = 'SOC', 'Ciencias Sociales'

    codigo = models.CharField(max_length=3, choices=Codigo.choices, unique=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.CheckConstraint(condition=Q(codigo__in=['ESP', 'MAT', 'NAT', 'SOC']), name='asignatura_codigo_valido'),
        ]

    def __str__(self):
        return self.get_codigo_display()


class Pregunta(models.Model):
    codigo = models.CharField(max_length=40, unique=True)
    asignatura = models.ForeignKey(Asignatura, on_delete=models.PROTECT, related_name='preguntas')
    grado = models.PositiveSmallIntegerField(choices=GRADOS, verbose_name='grado de ingreso')
    enunciado = models.TextField()
    referencia = models.TextField(help_text='Referente pedagógico, grado previo y página o enlace.')
    justificacion = models.TextField(blank=True)
    guia_aplicacion = models.TextField(blank=True, help_text='Apoyo permitido, lectura de instrucciones y ajustes del ítem.')
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['asignatura_id', 'grado', 'codigo']
        constraints = [models.CheckConstraint(condition=Q(grado__in=[1, 2, 3]), name='pregunta_grado_valido')]
        indexes = [models.Index(fields=['asignatura', 'grado', 'activa'], name='pregunta_banco_idx')]

    def __str__(self):
        return f'{self.codigo} — {self.asignatura}, ingreso a {self.grado}°'


class Opcion(models.Model):
    pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE, related_name='opciones')
    letra = models.CharField(max_length=1, choices=LETRAS)
    texto = models.TextField()
    es_correcta = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'opción'
        verbose_name_plural = 'opciones'
        ordering = ['letra']
        constraints = [
            models.UniqueConstraint(fields=['pregunta', 'letra'], name='opcion_letra_unica'),
            models.UniqueConstraint(fields=['pregunta'], condition=Q(es_correcta=True), name='opcion_una_correcta'),
            models.CheckConstraint(condition=Q(letra__in=list('ABCD')), name='opcion_letra_valida'),
        ]

    def __str__(self):
        return f'{self.letra}. {self.texto}'


class Prueba(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = 'BORRADOR', 'Borrador'
        ABIERTA = 'ABIERTA', 'Abierta'
        CERRADA = 'CERRADA', 'Cerrada'

    titulo = models.CharField(max_length=150)
    docente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pruebas')
    asignatura = models.ForeignKey(Asignatura, on_delete=models.PROTECT, related_name='pruebas')
    grado = models.PositiveSmallIntegerField(choices=GRADOS, verbose_name='grado de ingreso')
    codigo = models.CharField(max_length=10, unique=True, default=generar_codigo, editable=False)
    estado = models.CharField(max_length=8, choices=Estado.choices, default=Estado.BORRADOR, editable=False)
    creada_en = models.DateTimeField(auto_now_add=True)
    habilitada_en = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-creada_en']
        constraints = [
            models.CheckConstraint(condition=Q(grado__in=[1, 2, 3]), name='prueba_grado_valido'),
            models.CheckConstraint(
                condition=(Q(estado='BORRADOR', habilitada_en__isnull=True) | Q(estado__in=['ABIERTA', 'CERRADA'], habilitada_en__isnull=False)),
                name='prueba_estado_fecha_coherente',
            ),
        ]

    def clean(self):
        super().clean()
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).first()
            if anterior and anterior.habilitada_en and any(
                getattr(anterior, campo) != getattr(self, campo)
                for campo in ('grado', 'asignatura_id', 'docente_id')
            ):
                raise ValidationError('Una prueba habilitada conserva su grado, asignatura y docente.')

    def __str__(self):
        return f'{self.titulo} ({self.codigo})'


class ItemPrueba(models.Model):
    prueba = models.ForeignKey(Prueba, on_delete=models.CASCADE, related_name='items')
    pregunta = models.ForeignKey(Pregunta, on_delete=models.PROTECT, related_name='items_prueba')
    orden = models.PositiveSmallIntegerField()
    # Copia del contenido y clave al habilitar; nunca se envía completa al estudiante.
    contenido = models.JSONField(default=dict, editable=False)

    class Meta:
        verbose_name = 'pregunta de la prueba'
        verbose_name_plural = 'preguntas de la prueba'
        ordering = ['orden']
        constraints = [
            models.UniqueConstraint(fields=['prueba', 'pregunta'], name='item_pregunta_unica'),
            models.UniqueConstraint(fields=['prueba', 'orden'], name='item_orden_unico'),
            models.CheckConstraint(condition=Q(orden__gte=1) & Q(orden__lte=20), name='item_orden_rango'),
        ]

    def clean(self):
        super().clean()
        # El formulario puede estar creando simultáneamente la prueba y sus ítems.
        prueba = self._state.fields_cache.get('prueba')
        if prueba is None and self.prueba_id:
            prueba = self.prueba
        if prueba and prueba.estado != Prueba.Estado.BORRADOR:
            raise ValidationError('No se puede modificar una prueba habilitada.')
        if prueba and self.pregunta_id and (
            prueba.grado != self.pregunta.grado
            or prueba.asignatura_id != self.pregunta.asignatura_id
        ):
            raise ValidationError('La pregunta debe coincidir con el grado y la asignatura de la prueba.')

    def __str__(self):
        return f'{self.orden}. {self.pregunta.codigo}'


class Intento(models.Model):
    class Acompanamiento(models.TextChoices):
        SIN_APOYO = 'SIN_APOYO', 'Sin acompañamiento'
        INDIVIDUAL = 'INDIVIDUAL', 'Individual con docente y auxiliar'
        GRUPO_CUATRO = 'GRUPO_CUATRO', 'Grupo de hasta cuatro con docente y auxiliar'

    prueba = models.ForeignKey(Prueba, on_delete=models.PROTECT, related_name='intentos')
    identificador = models.CharField(max_length=50, help_text='Identificador asignado; no requiere nombre ni documento del niño.')
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    acompanamiento = models.CharField(max_length=12, choices=Acompanamiento.choices)
    observaciones_apoyo = models.TextField(blank=True, help_text='Ajustes de aplicación, sin datos personales innecesarios.')
    iniciado_en = models.DateTimeField(auto_now_add=True)
    enviado_en = models.DateTimeField(null=True, blank=True, editable=False)
    total_preguntas = models.PositiveSmallIntegerField(editable=False)
    aciertos = models.PositiveSmallIntegerField(default=0, editable=False)

    class Meta:
        ordering = ['-iniciado_en']
        constraints = [
            models.UniqueConstraint(fields=['prueba', 'identificador'], name='intento_identificador_unico'),
            models.CheckConstraint(condition=Q(total_preguntas__gte=1) & Q(total_preguntas__lte=20), name='intento_total_rango'),
            models.CheckConstraint(condition=Q(aciertos__lte=F('total_preguntas')), name='intento_aciertos_rango'),
            models.CheckConstraint(condition=Q(enviado_en__isnull=False) | Q(aciertos=0), name='intento_pendiente_sin_puntaje'),
            models.CheckConstraint(condition=Q(acompanamiento__in=['SIN_APOYO', 'INDIVIDUAL', 'GRUPO_CUATRO']), name='intento_apoyo_valido'),
        ]

    @property
    def porcentaje(self):
        if self.enviado_en is None:
            return None
        return (Decimal(self.aciertos) * 100 / self.total_preguntas).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

    def __str__(self):
        return f'{self.identificador} — {self.prueba}'


class Respuesta(models.Model):
    intento = models.ForeignKey(Intento, on_delete=models.PROTECT, related_name='respuestas')
    item = models.ForeignKey(ItemPrueba, on_delete=models.PROTECT, related_name='respuestas')
    opcion = models.CharField(max_length=1, choices=LETRAS)
    es_correcta = models.BooleanField(editable=False)

    class Meta:
        ordering = ['item__orden']
        constraints = [
            models.UniqueConstraint(fields=['intento', 'item'], name='respuesta_item_unica'),
            models.CheckConstraint(condition=Q(opcion__in=list('ABCD')), name='respuesta_opcion_valida'),
        ]

    def clean(self):
        super().clean()
        if self.intento_id and self.item_id:
            if self.intento.prueba_id != self.item.prueba_id:
                raise ValidationError('La pregunta no pertenece a la prueba de este intento.')
            if self.intento.enviado_en:
                raise ValidationError('Un intento enviado no admite cambios de respuestas.')
            if self.opcion not in self.item.contenido.get('opciones', {}):
                raise ValidationError('La opción no pertenece a esta pregunta.')
            self.es_correcta = self.opcion == self.item.contenido.get('correcta')

    def __str__(self):
        return f'{self.intento.identificador}: pregunta {self.item.orden}, opción {self.opcion}'
