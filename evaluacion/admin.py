from django.contrib import admin
from django.contrib import messages
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet
from django.db import transaction

from .models import Asignatura, Intento, ItemPrueba, Opcion, Pregunta, Prueba, Respuesta
from .services import cerrar_prueba, habilitar_prueba


class OpcionesFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        datos = [form.cleaned_data for form in self.forms if form.cleaned_data and not form.cleaned_data.get('DELETE')]
        if len(datos) != 4 or {dato.get('letra') for dato in datos} != set('ABCD'):
            raise ValidationError('Registre exactamente cuatro opciones: A, B, C y D.')
        if sum(bool(dato.get('es_correcta')) for dato in datos) != 1:
            raise ValidationError('Marque exactamente una respuesta correcta.')

    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)
        # Mantiene los registros de cambios que Django usa en su historial.
        super().save(commit=False)
        # Libera la clave anterior antes de cambiarla, sin violar el índice único.
        self.instance.opciones.filter(es_correcta=True).update(es_correcta=False)
        guardadas = []
        for form in self.forms:
            if not form.cleaned_data:
                continue
            if form.cleaned_data.get('DELETE'):
                if form.instance.pk:
                    form.instance.delete()
                continue
            opcion = form.save(commit=False)
            opcion.pregunta = self.instance
            opcion.save()
            guardadas.append(opcion)
        return guardadas


class OpcionForm(forms.ModelForm):
    class Meta:
        model = Opcion
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['letra'].disabled = True


class OpcionInline(admin.TabularInline):
    model = Opcion
    form = OpcionForm
    formset = OpcionesFormSet
    extra = 4
    max_num = 4
    fields = ('letra', 'texto', 'es_correcta')


@admin.register(Asignatura)
class AsignaturaAdmin(admin.ModelAdmin):
    list_display = ('codigo', '__str__')
    readonly_fields = ('codigo',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Pregunta)
class PreguntaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'asignatura', 'grado', 'activa')
    list_filter = ('asignatura', 'grado', 'activa')
    search_fields = ('codigo', 'enunciado')
    inlines = (OpcionInline,)
    list_select_related = ('asignatura',)


class ItemsFormSet(BaseInlineFormSet):
    @transaction.atomic
    def save(self, commit=True):
        if not commit:
            return super().save(commit=False)
        if self.instance.estado != Prueba.Estado.BORRADOR:
            return []
        guardados = super().save(commit=False)
        for item in self.deleted_objects:
            item.delete()
        # SQLite comprueba la unicidad inmediatamente. Reinsertar los ítems
        # editados con su mismo ID permite intercambiar orden o preguntas.
        # Solo ocurre en borradores, que todavía no admiten intentos.
        modificados = [item.pk for item, campos in self.changed_objects]
        if modificados:
            ItemPrueba.objects.filter(pk__in=modificados, prueba=self.instance).delete()
        for item in guardados:
            item.save()
        self.save_m2m()
        return guardados


class ItemPruebaInline(admin.TabularInline):
    model = ItemPrueba
    formset = ItemsFormSet
    extra = 0
    max_num = 20
    fields = ('pregunta', 'orden')
    autocomplete_fields = ('pregunta',)

    def has_add_permission(self, request, obj=None):
        return (obj is None or obj.estado == Prueba.Estado.BORRADOR) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return (obj is None or obj.estado == Prueba.Estado.BORRADOR) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return (obj is None or obj.estado == Prueba.Estado.BORRADOR) and super().has_delete_permission(request, obj)


@admin.register(Prueba)
class PruebaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'codigo', 'grado', 'asignatura', 'estado', 'docente')
    list_filter = ('estado', 'grado', 'asignatura')
    search_fields = ('titulo', 'codigo')
    readonly_fields = ('docente', 'codigo', 'estado', 'creada_en', 'habilitada_en')
    inlines = (ItemPruebaInline,)
    actions = ('habilitar_seleccionadas', 'cerrar_seleccionadas')
    list_select_related = ('docente', 'asignatura')

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        return consulta if request.user.is_superuser else consulta.filter(docente=request.user)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.estado != Prueba.Estado.BORRADOR:
            return self.readonly_fields + ('titulo', 'grado', 'asignatura')
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:
            obj.docente = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return (obj is None or obj.estado == Prueba.Estado.BORRADOR) and super().has_delete_permission(request, obj)

    def get_actions(self, request):
        acciones = super().get_actions(request)
        acciones.pop('delete_selected', None)
        return acciones

    def _cambiar_estado(self, request, queryset, operacion):
        for prueba in queryset:
            try:
                operacion(prueba.pk, docente=request.user)
            except ValidationError as error:
                self.message_user(request, f'{prueba}: {"; ".join(error.messages)}', messages.ERROR)
            else:
                self.message_user(request, f'Estado actualizado: {prueba}.', messages.SUCCESS)

    @admin.action(description='Habilitar las pruebas seleccionadas', permissions=['change'])
    def habilitar_seleccionadas(self, request, queryset):
        self._cambiar_estado(request, queryset, habilitar_prueba)

    @admin.action(description='Cerrar las pruebas seleccionadas', permissions=['change'])
    def cerrar_seleccionadas(self, request, queryset):
        self._cambiar_estado(request, queryset, cerrar_prueba)


class RespuestaInline(admin.TabularInline):
    model = Respuesta
    extra = 0
    fields = ('item', 'opcion', 'es_correcta')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Intento)
class IntentoAdmin(admin.ModelAdmin):
    list_display = ('identificador', 'prueba', 'iniciado_en', 'enviado_en', 'total_preguntas', 'aciertos', 'porcentaje_aciertos')
    list_filter = ('prueba__grado', 'prueba__asignatura', 'acompanamiento', 'enviado_en')
    search_fields = ('identificador', 'prueba__titulo', 'prueba__codigo')
    readonly_fields = (
        'prueba', 'identificador', 'acompanamiento', 'observaciones_apoyo',
        'iniciado_en', 'enviado_en', 'total_preguntas', 'aciertos', 'porcentaje_aciertos',
    )
    fields = readonly_fields
    inlines = (RespuestaInline,)
    list_select_related = ('prueba',)

    @admin.display(description='Porcentaje de aciertos')
    def porcentaje_aciertos(self, obj):
        return 'Pendiente' if obj.porcentaje is None else f'{obj.porcentaje}%'

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        return consulta if request.user.is_superuser else consulta.filter(prueba__docente=request.user)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.site_header = 'EduDiagnóstico — Administración'
admin.site.site_title = 'EduDiagnóstico'
admin.site.index_title = 'Banco, pruebas y resultados'
