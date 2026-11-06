# Base de datos de EduDiagnóstico

Estado verificado el 6 de noviembre de 2026. SQLite se ejecuta en el servidor; los navegadores accederán a Django, nunca al archivo de datos.

## Tablas

Las tablas `auth_*`, `django_admin_log`, `django_content_type`, `django_session` y `django_migrations` pertenecen a Django. Se reutilizan sus usuarios y permisos para el docente.

| Tabla del proyecto | Propósito y relaciones |
|---|---|
| `evaluacion_asignatura` | Cuatro registros iniciales: ESP, MAT, NAT y SOC. |
| `evaluacion_pregunta` | Código único, asignatura, grado de ingreso, enunciado, referencia, justificación, guía de aplicación y disponibilidad. |
| `evaluacion_opcion` | Opciones A–D de cada pregunta y marca de respuesta correcta. |
| `evaluacion_prueba` | Docente responsable, título, grado, asignatura, código de acceso, fechas y estado. |
| `evaluacion_itemprueba` | Selección ordenada de preguntas y copia de su contenido al habilitar la prueba. |
| `evaluacion_intento` | Registro individual por prueba e identificador, acompañamiento, fechas y aciertos. |
| `evaluacion_respuesta` | Opción elegida por cada ítem del intento y si fue correcta. |

No se crea una cuenta de acceso por niño ni se solicitan nombres o documentos de identidad. Cada aplicación usa un identificador asignado. Para una nueva aplicación al mismo grupo se crea otra prueba; dentro de una prueba cada identificador tiene un único intento.

## Reglas implementadas

- Solo existen las cuatro asignaturas acordadas y los grados de ingreso 1, 2 y 3.
- El administrador exige cuatro opciones con texto y exactamente una correcta. SQLite impide letras duplicadas y más de una clave correcta; el servicio vuelve a comprobar la integridad antes de habilitar una prueba.
- Una prueba contiene entre 1 y 20 preguntas activas de su mismo grado y asignatura, sin repetición y con orden único.
- Los estados son `BORRADOR → ABIERTA → CERRADA`. El cierre impide nuevos intentos y nuevos envíos, incluidos los intentos pendientes. Los resultados ya enviados se conservan. No se implementa reapertura.
- Al habilitar se copia el enunciado, las opciones, la clave y la ficha de cada pregunta en `ItemPrueba.contenido`. Editar posteriormente el banco no altera esa copia. La selección de una prueba habilitada queda bloqueada en el administrador.
- El inicio registra obligatoriamente la modalidad de acompañamiento y permite observaciones sobre ajustes de aplicación. En primero se recomienda el acompañamiento individual o en grupos de hasta cuatro, según la propuesta.
- El envío requiere todas las respuestas. Una pregunta sin responder impide el envío; no se cuenta como respuesta incorrecta.
- El servidor comprueba que cada ítem pertenece a la prueba y que su opción es válida. Guarda respuestas y resultado en una sola transacción.
- Repetir un envío devuelve el resultado previamente guardado, sin duplicar respuestas ni recalificar.
- El porcentaje se calcula como `aciertos / total × 100`, redondeado a un decimal. Un intento pendiente no tiene porcentaje; cero aciertos en un intento enviado equivale a 0.0%.
- Cada docente consulta sus pruebas y resultados. El superusuario puede administrarlos globalmente. El banco de preguntas es compartido entre los docentes con permisos.

Los resultados se limitan al desempeño general de la asignatura evaluada. No se incluyen niveles de desempeño, reportes por competencia ni recomendaciones automáticas.

## Operaciones utilizadas por las pantallas

El módulo `evaluacion/services.py` concentra las operaciones:

| Función | Uso |
|---|---|
| `habilitar_prueba(prueba_id, docente=usuario)` | Valida la selección y conserva las copias de preguntas. |
| `cerrar_prueba(prueba_id, docente=usuario)` | Cierra una prueba del docente. |
| `iniciar_intento(codigo, identificador, acompanamiento=modalidad, observaciones_apoyo='')` | Crea el registro individual y genera un token aleatorio. |
| `preguntas_para_estudiante(token)` | Devuelve los ítems visibles, sin respuestas correctas ni justificaciones. |
| `enviar_respuestas(token, respuestas)` | Recibe un diccionario `{id_item: 'A'}` y guarda la calificación. |

Las vistas de `evaluacion/views.py` utilizan estos servicios y mantienen el token del intento en la sesión del estudiante. Conocer el código y un identificador ya utilizado no permite recuperar el token de otra sesión. No se envía `ItemPrueba.contenido` completo al navegador del estudiante porque incluye la clave. Los formularios usan protección CSRF y las páginas del intento indican que no deben almacenarse en caché.

Las rutas son `/` para ingresar, `/prueba/` para responder, `/finalizado/` para confirmar el envío y `/salir/` para terminar la sesión del estudiante mediante POST. El servidor rechaza respuestas de una página perteneciente a otro intento. El cierre de sesión se permite después del envío o del cierre de la prueba; no abandona un intento abierto pendiente. Las respuestas sin enviar no se guardan como borrador.

Las restricciones de SQLite protegen rangos, unicidad y relaciones. Las reglas que comparan varias tablas o controlan las transiciones se aplican en los servicios y el administrador. Escribir directamente mediante SQL, `QuerySet.update()` o `save()` no ejecuta automáticamente la validación de Django; no deben usarse para reemplazar el flujo de evaluación.

## Uso desde el administrador

1. Crear una cuenta administradora con `python manage.py createsuperuser` e ingresar a `/admin/`.
2. Importar el banco con `python manage.py importar_banco` o registrar preguntas manualmente. Las asignaturas ya se crean mediante una migración.
3. Crear una prueba en borrador y agregar preguntas indicando su orden del 1 al 20. El docente responsable se asigna a la cuenta que la crea.
4. Desde la lista de pruebas, seleccionar la acción **Habilitar las pruebas seleccionadas**. Si falta contenido o existe una incoherencia, se mostrará el error y la prueba seguirá en borrador.
5. Entregar al estudiante el código y un identificador. Desde `/`, el estudiante registra el acompañamiento, responde las preguntas y envía sus respuestas. Al terminar ve la confirmación; los resultados se consultan en el administrador.
6. Consultar los intentos y sus respuestas desde el administrador; filtrar por grado, asignatura, fecha o identificador. Cerrar la prueba cuando ya no se admitan envíos.

Para otras cuentas docentes, un administrador debe marcar **Es staff** y conceder permisos de consulta de asignaturas; alta, consulta, cambio y eliminación de preguntas, opciones, pruebas e ítems de prueba; y consulta de intentos y respuestas. No necesitan permisos de administración de usuarios. La eliminación de pruebas habilitadas y la edición manual de resultados están desactivadas en el administrador.

## Instalación y migraciones

El entorno comprobado usa Python 3.13.7, Django 5.2.19 y SQLite 3.50.4. `requirements.txt` fija Django y sus dependencias instaladas. Python y SQLite se verifican en cada equipo; la versión de SQLite depende del intérprete. La propuesta indicaba Python 3.14.10 como base prevista; esta verificación corresponde al intérprete disponible en el repositorio.

Desde la raíz del repositorio en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

`migrate` crea las tablas y las cuatro asignaturas. El archivo `db.sqlite3` y el entorno `.venv` son locales y están excluidos de Git; las migraciones se comparten con el equipo. La importación se ejecuta por separado:

```powershell
.\.venv\Scripts\python.exe manage.py importar_banco --comprobar
.\.venv\Scripts\python.exe manage.py importar_banco
.\.venv\Scripts\python.exe manage.py preparar_demo --docente admin
```

El primer comando valida el documento sin escribir. El segundo importa las 240 preguntas y 960 opciones en una transacción; repetirlo conserva los registros coincidentes. Si una pregunta existente tiene contenido diferente, informa del conflicto y revierte toda la importación, sin sobrescribir cambios. Los códigos `CN` del documento se relacionan con la asignatura `NAT`, conservando el identificador original.

El documento solo declara referentes generales y componentes: se conserva esa procedencia en `referencia`, sin inventar un DBA o una página por ítem. No se generan reportes por competencia. La revisión pedagógica y las guías específicas de aplicación siguen pendientes.

`preparar_demo` habilita tres preguntas existentes de Español para ingreso a segundo y muestra su código. Reutiliza la práctica abierta del docente; si ya está cerrada, crea otra. No crea usuarios ni inventa preguntas. En esta copia local el banco está importado y la cuenta administradora ya existe.

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe scripts\comprobar_concurrencia.py
```

La suite comprueba el flujo de calificación, las restricciones de datos, las copias del contenido, el administrador, los permisos y los envíos repetidos. El script de concurrencia crea una base SQLite temporal y comprueba cuatro estudiantes simultáneos y cuatro envíos simultáneos del mismo intento; al finalizar elimina esa base temporal y no modifica `db.sqlite3`.

SQLite usa un tiempo de espera de 20 segundos y transacciones `IMMEDIATE` para las operaciones atómicas, siguiendo las opciones documentadas por [Django para SQLite](https://docs.djangoproject.com/en/5.2/ref/databases/#sqlite-notes). Las escrituras son breves y se realizan con [transacciones atómicas](https://docs.djangoproject.com/en/5.2/topics/db/transactions/). La comprobación local de concurrencia no sustituye la demostración HTTP desde cuatro dispositivos, que sigue pendiente.

## Trabajo pendiente

- Revisar visualmente las pantallas, incluido su uso en dispositivos pequeños.
- Completar la revisión docente y las referencias específicas de cada ítem.
- Realizar la demostración entre dispositivos y completar las evidencias del informe.
