"""Lectura estricta del formato tabular del banco Word del proyecto."""

import re
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
ENCABEZADO = ['ID', 'Pregunta', 'A', 'B', 'C', 'D', 'Resp.', 'Competencia']
AREAS = {'ESP': 'ESP', 'MAT': 'MAT', 'CN': 'NAT', 'SOC': 'SOC'}


def leer_banco(ruta):
    try:
        with ZipFile(ruta) as archivo:
            info = archivo.getinfo('word/document.xml')
            if info.file_size > 10_000_000:
                raise ValueError('El contenido del documento supera el tamaño esperado.')
            raiz = ET.fromstring(archivo.read(info))
    except (OSError, BadZipFile, KeyError, ET.ParseError) as error:
        raise ValueError(f'No se pudo leer el banco Word: {error}') from error
    preguntas = []
    for tabla in raiz.findall('.//w:tbl', NS):
        filas = [[
            '\n'.join(''.join(t.text or '' for t in p.findall('.//w:t', NS))
                      for p in celda.findall('w:p', NS)).strip()
            for celda in fila.findall('w:tc', NS)
        ] for fila in tabla.findall('w:tr', NS)]
        if not filas or filas[0] != ENCABEZADO:
            continue
        for fila in filas[1:]:
            if len(fila) != 8:
                raise ValueError('Cada pregunta debe tener ocho columnas.')
            codigo, enunciado, a, b, c, d, correcta, competencia = fila
            partes = re.fullmatch(r'([123])-(ESP|MAT|CN|SOC)-(\d{2})', codigo)
            if not partes or not 1 <= int(partes[3]) <= 20:
                raise ValueError(f'Identificador fuera del alcance: {codigo}.')
            if not all([enunciado, a, b, c, d]) or correcta not in 'ABCD' or len(correcta) != 1:
                raise ValueError(f'Enunciado, opciones o clave inválidos: {codigo}.')
            grado = int(partes[1])
            previo = 'transición' if grado == 1 else f'grado {grado - 1}'
            preguntas.append({
                'codigo': codigo, 'grado': grado, 'asignatura': AREAS[partes[2]],
                'enunciado': enunciado, 'opciones': dict(zip('ABCD', [a, b, c, d])), 'correcta': correcta,
                'referencia': f'Fuente: {Path(ruta).name}; ítem {codigo}. Referente general declarado: DBA de {previo} y estándares del MEN. Componente declarado: {competencia}. Referencia específica por ítem pendiente de revisión docente.',
            })
    if len({p['codigo'] for p in preguntas}) != len(preguntas):
        raise ValueError('El documento contiene identificadores duplicados.')
    grupos = Counter((p['grado'], p['asignatura']) for p in preguntas)
    esperados = {(grado, area): 20 for grado in (1, 2, 3) for area in AREAS.values()}
    if dict(grupos) != esperados:
        raise ValueError('Se esperaban 240 preguntas: 20 por cada uno de los 12 bancos.')
    return preguntas
