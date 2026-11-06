from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from .forms import IngresoForm, RespuestasForm
from .models import Intento, Prueba
from .services import enviar_respuestas, iniciar_intento, preguntas_para_estudiante


CLAVE_SESION = 'evaluacion_intento'


def _intento_actual(request):
    token = request.session.get(CLAVE_SESION)
    if not token:
        return None
    try:
        return Intento.objects.select_related('prueba__asignatura').get(token=token)
    except (Intento.DoesNotExist, ValidationError):
        request.session.pop(CLAVE_SESION, None)
        return None


@never_cache
@require_http_methods(['GET', 'POST'])
def ingreso(request):
    intento = _intento_actual(request)
    if intento:
        return redirect('evaluacion:finalizado' if intento.enviado_en else 'evaluacion:responder')
    form = IngresoForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            intento = iniciar_intento(**form.cleaned_data)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            request.session.cycle_key()
            request.session[CLAVE_SESION] = str(intento.token)
            return redirect('evaluacion:responder')
    return render(request, 'evaluacion/ingreso.html', {'form': form})


@never_cache
@require_http_methods(['GET', 'POST'])
def responder(request):
    intento = _intento_actual(request)
    if intento is None:
        return redirect('evaluacion:ingreso')
    if intento.enviado_en:
        return redirect('evaluacion:finalizado')
    if intento.prueba.estado != Prueba.Estado.ABIERTA:
        return render(request, 'evaluacion/cerrada.html', {'intento': intento})
    try:
        preguntas = preguntas_para_estudiante(intento.token)
    except ValidationError:
        # La prueba pudo cerrarse entre ambas consultas.
        return render(request, 'evaluacion/cerrada.html', {'intento': intento})
    form = RespuestasForm(preguntas, intento.pk, request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            enviar_respuestas(intento.token, form.respuestas())
        except ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect('evaluacion:finalizado')
    return render(request, 'evaluacion/responder.html', {'form': form, 'intento': intento})


@never_cache
@require_http_methods(['GET'])
def finalizado(request):
    intento = _intento_actual(request)
    if intento is None:
        return redirect('evaluacion:ingreso')
    if not intento.enviado_en:
        return redirect('evaluacion:responder')
    return render(request, 'evaluacion/finalizado.html', {'intento': intento})


@never_cache
@require_POST
def salir(request):
    intento = _intento_actual(request)
    if intento and not intento.enviado_en and intento.prueba.estado == Prueba.Estado.ABIERTA:
        return redirect('evaluacion:responder')
    request.session.pop(CLAVE_SESION, None)
    request.session.cycle_key()
    return redirect('evaluacion:ingreso')
