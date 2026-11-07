# EduDiagnóstico — Cambios: pruebas completas para todos los grados y asignaturas

**Fecha:** 6 de noviembre de 2026.

## Situación anterior

- El banco Word (`docs/EduDiagnostico_Banco_de_Preguntas.docx`) contiene las 240 preguntas: 20 por cada uno de los 12 bancos (4 asignaturas × 3 grados). `importar_banco` ya las cargaba todas en la base.
- Sin embargo, la única prueba que se podía habilitar automáticamente era la práctica de `preparar_demo`: **tres preguntas de Español para ingreso a segundo**. Las demás materias de segundo y todas las de primero y tercero solo podían crearse a mano en el administrador, pregunta por pregunta.

## Qué se cambió

Se conservó toda la estructura existente: no se modificaron modelos, migraciones, vistas, plantillas, servicios, el importador, el comando `preparar_demo` ni el Word del banco.

| Archivo | Tipo | Cambio |
|---|---|---|
| `evaluacion/management/commands/preparar_pruebas.py` | Nuevo | Comando que crea y habilita las 12 pruebas diagnósticas, cada una con las 20 preguntas de su banco. |
| `evaluacion/test_pruebas.py` | Nuevo | 5 pruebas automatizadas del nuevo comando y del recorrido de una prueba de 20 preguntas. |
| `README.md` | Modificado | Estado del proyecto, nueva sección «Habilitar las pruebas completas…» y casilla marcada en el desarrollo. |
| `docs/Base_de_datos.md` | Modificado | Comando agregado a la importación y descripción de su funcionamiento. |
| `docs/Cambios_pruebas_completas.md` | Nuevo | Este documento. |

### Pruebas que crea `preparar_pruebas`

| Grado de ingreso | Español | Matemáticas | Ciencias Naturales | Ciencias Sociales |
|---|---|---|---|---|
| Primero | `1-ESP-01` a `1-ESP-20` | `1-MAT-01` a `1-MAT-20` | `1-CN-01` a `1-CN-20` | `1-SOC-01` a `1-SOC-20` |
| Segundo | `2-ESP-01` a `2-ESP-20` | `2-MAT-01` a `2-MAT-20` | `2-CN-01` a `2-CN-20` | `2-SOC-01` a `2-SOC-20` |
| Tercero | `3-ESP-01` a `3-ESP-20` | `3-MAT-01` a `3-MAT-20` | `3-CN-01` a `3-CN-20` | `3-SOC-01` a `3-SOC-20` |

Total: **12 pruebas y 240 preguntas**. Los títulos siguen el formato `Diagnóstico — <Asignatura>, ingreso a <grado>`, por ejemplo `Diagnóstico — Matemáticas, ingreso a primero`.

### Comportamiento del comando

- Usa `habilitar_prueba` de `services.py`: aplica las mismas validaciones que el administrador (cuatro opciones, una sola correcta, pregunta activa, entre 1 y 20 ítems) y guarda la copia del contenido de cada ítem.
- Ordena las preguntas por código (orden 1 a 20).
- Es repetible: si la prueba del docente sigue abierta, muestra su código sin duplicarla; si se cerró, crea una nueva.
- Si algún banco no tiene preguntas activas (por ejemplo, no se ejecutó `importar_banco`), informa el problema y revierte toda la operación.
- Opciones: `--docente USUARIO` (predeterminado `admin`), `--grado 1|2|3` y `--asignatura ESP|MAT|NAT|SOC` para preparar una sola prueba.
- No crea usuarios ni modifica preguntas.

## Verificaciones realizadas

- `manage.py check`: sin errores.
- `manage.py test --noinput`: **55 pruebas aprobadas** (las 50 existentes + 5 nuevas).
- Ejecución sobre una base nueva: `migrate` → `importar_banco` (240 nuevas) → `preparar_demo` → `preparar_pruebas` creó 12 pruebas de 20 preguntas; al repetirlo, 0 nuevas.
- Recorrido web de una prueba completa (Ciencias Naturales, ingreso a tercero): ingreso, envío de las 20 respuestas y resultado de 20 aciertos.

## Pasos para aplicar los cambios en tu copia local

Desde la raíz del proyecto (la carpeta que contiene `manage.py`), en PowerShell:

1. **Actualizar tu copia** con la última versión del repositorio:
   ```powershell
   git pull
   ```
2. **Copiar los archivos nuevos** en estas rutas exactas:
   - `preparar_pruebas.py` → `evaluacion\management\commands\preparar_pruebas.py`
   - `test_pruebas.py` → `evaluacion\test_pruebas.py`
   - `Cambios_pruebas_completas.md` → `docs\Cambios_pruebas_completas.md`
3. **Reemplazar** `README.md` (raíz) y `docs\Base_de_datos.md` por las versiones actualizadas.
4. **Comprobar** que todo sigue funcionando:
   ```powershell
   .\.venv\Scripts\python.exe manage.py check
   .\.venv\Scripts\python.exe manage.py test --noinput
   ```
   Deben aparecer 55 pruebas con resultado `OK`.
5. **Asegurar que el banco está cargado** (no duplica si ya lo está):
   ```powershell
   .\.venv\Scripts\python.exe manage.py importar_banco
   ```
6. **Crear las 12 pruebas**:
   ```powershell
   .\.venv\Scripts\python.exe manage.py preparar_pruebas --docente admin
   ```
   Anotar los 12 códigos que muestra; también se ven en **Administración → Pruebas**.
7. **Probar** con `runserver`, entrando en `http://127.0.0.1:8000/` con uno de los códigos y un identificador ficticio nuevo.
8. **Publicar en GitHub** (cuando el equipo lo apruebe):
   ```powershell
   git add evaluacion/management/commands/preparar_pruebas.py evaluacion/test_pruebas.py README.md docs/Base_de_datos.md docs/Cambios_pruebas_completas.md
   git commit -m "Agregar comando preparar_pruebas para las 12 pruebas completas"
   git push
   ```

## Pendiente

- Revisión pedagógica de los ítems por parte de los docentes (la validación técnica no la sustituye).
- Revisión visual de una prueba de 20 preguntas en los dispositivos del equipo, en especial para primero.
- Demostración en red local desde dispositivos distintos al servidor.
