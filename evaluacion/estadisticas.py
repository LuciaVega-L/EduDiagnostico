"""Estadísticas del panel docente: resultados por grado y asignatura."""

from django.db.models import Count, Q

from .models import GRADOS, Asignatura, Intento, Respuesta

# Rangos neutros de porcentaje de aciertos; no son niveles de desempeño.
RANGOS = [(0, 25, '0–25 %'), (26, 50, '26–50 %'), (51, 75, '51–75 %'), (76, 100, '76–100 %')]
NOMBRES_GRADO = dict(GRADOS)


def _porcentaje(parte, total):
    return round(parte * 100 / total, 1) if total else 0


def estadisticas_docente(docente):
    """Devuelve una lista por grado, cada una con sus asignaturas y estadísticas.

    Solo cuenta intentos enviados. Un superusuario ve todas las pruebas;
    un docente, únicamente las suyas.
    """
    intentos = Intento.objects.filter(enviado_en__isnull=False)
    respuestas = Respuesta.objects.filter(intento__enviado_en__isnull=False)
    if not docente.is_superuser:
        intentos = intentos.filter(prueba__docente=docente)
        respuestas = respuestas.filter(item__prueba__docente=docente)

    # Resultados individuales agrupados en Python (volumen pequeño por aplicación).
    por_grupo = {}
    for fila in intentos.values('prueba__grado', 'prueba__asignatura_id', 'aciertos', 'total_preguntas'):
        clave = (fila['prueba__grado'], fila['prueba__asignatura_id'])
        por_grupo.setdefault(clave, []).append(_porcentaje(fila['aciertos'], fila['total_preguntas']))

    # Porcentaje de acierto por pregunta; order_by() anula el orden por defecto
    # de Respuesta, que de lo contrario alteraría la agrupación.
    preguntas = {}
    consulta = (respuestas.order_by()
                .values('item__pregunta__grado', 'item__pregunta__asignatura_id',
                        'item__pregunta__codigo', 'item__pregunta__enunciado')
                .annotate(total=Count('id'), correctas=Count('id', filter=Q(es_correcta=True))))
    for fila in consulta:
        clave = (fila['item__pregunta__grado'], fila['item__pregunta__asignatura_id'])
        preguntas.setdefault(clave, []).append({
            'codigo': fila['item__pregunta__codigo'],
            'enunciado': fila['item__pregunta__enunciado'],
            'respuestas': fila['total'],
            'porcentaje': _porcentaje(fila['correctas'], fila['total']),
        })

    asignaturas = list(Asignatura.objects.all())
    resultado = []
    for grado, nombre in GRADOS:
        filas = []
        for asignatura in asignaturas:
            valores = por_grupo.get((grado, asignatura.pk), [])
            lista = sorted(preguntas.get((grado, asignatura.pk), []), key=lambda p: (p['porcentaje'], p['codigo']))
            distribucion = []
            for minimo, maximo, etiqueta in RANGOS:
                cantidad = sum(1 for v in valores if minimo <= round(v) <= maximo)
                distribucion.append({'etiqueta': etiqueta, 'cantidad': cantidad,
                                     'ancho': round(cantidad * 100 / len(valores)) if valores else 0})
            filas.append({
                'asignatura': asignatura,
                'estudiantes': len(valores),
                'promedio': round(sum(valores) / len(valores), 1) if valores else None,
                'ancho_promedio': round(sum(valores) / len(valores)) if valores else 0,
                'minimo': min(valores) if valores else None,
                'maximo': max(valores) if valores else None,
                'distribucion': distribucion,
                'preguntas': lista,
            })
        resultado.append({
            'grado': grado, 'nombre': nombre, 'asignaturas': filas,
            'estudiantes': sum(f['estudiantes'] for f in filas),
        })
    return resultado
