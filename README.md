# EduDiagnóstico

Aplicación web cliente-servidor para aplicar **evaluaciones diagnósticas** a estudiantes que ingresan a **1.º, 2.º y 3.º de primaria**, registrar sus respuestas y mostrar al docente los resultados por grado y asignatura.

Proyecto final de la asignatura **Redes de Computadoras**, Ingeniería de Sistemas, Universidad de los Llanos.

> 🚧 **Estado:** recorrido web del estudiante, administración y calificación implementados. Banco importado: 240 preguntas y 960 opciones, con un comando que habilita las 12 pruebas completas (20 preguntas por grado y asignatura). Quedan pendientes la revisión visual, la revisión pedagógica y la demostración entre dispositivos.

---

## ¿Qué problema resuelve?

Al iniciar el año escolar, los docentes necesitan conocer los saberes previos con los que llegan sus estudiantes para planear la nivelación. Aplicar estas pruebas en papel, calificarlas y consolidar los resultados toma tiempo y deja la información dispersa. EduDiagnóstico centraliza ese proceso: el estudiante responde desde el navegador, el servidor califica y el docente consulta un resumen.

El diagnóstico tiene **finalidad formativa**: sirve para orientar la nivelación, no para promover ni excluir estudiantes.

## Alcance de la primera versión

El flujo implementado es el siguiente:

1. El docente ingresa a su cuenta, selecciona grado y asignatura y habilita una prueba mediante un código de acceso.
2. El estudiante accede desde el navegador con el código y un identificador asignado para esa aplicación.
3. El estudiante responde preguntas objetivas y envía sus respuestas.
4. El servidor valida y guarda las respuestas, calcula los aciertos y registra el resultado individual.
5. El docente consulta los resultados y administra el banco de preguntas.

**Asignaturas:** Español, Matemáticas, Ciencias Naturales y Ciencias Sociales. Español corresponde al área de Lenguaje en los referentes oficiales.

**Grados de ingreso:** primero, segundo y tercero de primaria. Las preguntas abordan aprendizajes previos pertinentes para iniciar cada grado.

## Banco de preguntas y referentes pedagógicos

El [banco de preguntas en Word](docs/EduDiagnostico_Banco_de_Preguntas.docx) ya se importó en la base local: **240 preguntas y 960 opciones**, conservando identificadores, enunciados y claves. El comando `importar_banco` permite reproducir la carga sin duplicar registros ni sobrescribir cambios del docente. El prefijo `CN` de los identificadores se conserva y se relaciona con Ciencias Naturales (`NAT`).

La organización acordada contempla **12 bancos**: cuatro asignaturas por tres grados, con hasta 20 preguntas por banco y un alcance de hasta **240 preguntas**. La carga podrá realizarse progresivamente y cada prueba podrá utilizar una selección breve.

Los referentes previstos son los Estándares Básicos de Competencias del MEN y los Derechos Básicos de Aprendizaje (DBA):

- **Ingreso a primero:** actividades integradas basadas en los referentes de transición, sin convertir los DBA en requisitos de admisión ni en una lista de logros para aprobar.
- **Ingreso a segundo:** aprendizajes de primero.
- **Ingreso a tercero:** aprendizajes de segundo.

La elaboración del documento y su revisión pedagógica son etapas distintas. La propuesta contempla revisión docente antes de la aplicación; este README no acredita que esa revisión ya se haya realizado.

## Acompañamiento en primero

Se recomienda atender a cada estudiante individualmente con acompañamiento del docente y un auxiliar. Como alternativa, se podrán organizar grupos de hasta cuatro estudiantes: el docente acompañará a dos y el auxiliar a los otros dos. Cada niño responderá individualmente y tendrá su propio registro.

Los adultos ayudarán con la navegación y leerán las instrucciones cuando corresponda, sin indicar respuestas correctas. En preguntas que evalúen lectura, el apoyo se ajustará a la guía del ítem. La aplicación registra la modalidad de acompañamiento.

## Resultados

Para cada intento se mostrará el grado, la asignatura, la fecha, el número de preguntas aplicadas, los aciertos y el porcentaje de aciertos. Todas las preguntas tendrán el mismo peso:

```text
Porcentaje de aciertos = (aciertos / preguntas aplicadas) × 100
```

La primera versión presentará **desempeño general por asignatura**. No asignará niveles como bajo, medio o alto sin un criterio pedagógico acordado. Los aciertos por competencia y las recomendaciones automáticas quedan como trabajo futuro.

## Arquitectura

```
┌──────────────────────┐   HTTP / LAN    ┌──────────────────────┐   SQL interno   ┌──────────────┐
│       CLIENTES       │ ──────────────▶ │    SERVIDOR WEB      │ ──────────────▶ │    DATOS     │
│ Navegadores de       │ ◀────────────── │ Django / Python      │ ◀────────────── │ SQLite       │
│ estudiantes/docentes │   GET / POST    │ Lógica de la app     │                 │ (en servidor)│
└──────────────────────┘                 └──────────────────────┘                 └──────────────┘
```

- Los **clientes** accederán desde equipos distintos al servidor mediante una red local, que será el escenario inicial.
- El **servidor Django** atiende las solicitudes HTTP, procesa los formularios y genera las respuestas.
- La **base de datos** permanece en el servidor y no es accesible directamente desde los clientes.
- Los recursos de la interfaz se alojarán en el servidor para permitir el funcionamiento sin conexión a internet.
- Una publicación posterior en internet requerirá HTTPS y una configuración de despliegue adecuada.

La demostración de Redes deberá documentar las direcciones IP, el puerto, las solicitudes GET/POST y el almacenamiento separado de resultados. Se probará el acceso de **cuatro estudiantes simultáneos** desde dispositivos distintos al servidor.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python, Django |
| Frontend | Plantillas HTML de Django y CSS local; el recorrido funciona sin JavaScript |
| Base de datos | SQLite en el servidor |
| Análisis de red | Herramientas de desarrollo del navegador; Wireshark como apoyo |

El entorno local se verificó con **Python 3.13.7, Django 5.2.19 y SQLite 3.50.4**. Las dependencias están fijadas en [requirements.txt](requirements.txt). La propuesta indicaba Python 3.14.10 como versión prevista; la implementación actual se comprobó con Python 3.13.7. La interfaz usa CSS propio local y no requiere Bootstrap para funcionar.

## Instalación local

Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py importar_banco
.\.venv\Scripts\python.exe manage.py runserver
```

La entrada del estudiante está en `http://127.0.0.1:8000/` y la administración en `http://127.0.0.1:8000/admin/`. Las migraciones crean las tablas y las cuatro asignaturas; `importar_banco` carga las preguntas. La base local y el entorno virtual no se suben a Git. Las credenciales se crean en cada equipo y no se incluyen en el repositorio.

La [guía de base de datos](docs/Base_de_datos.md) explica las tablas, los permisos docentes, la importación y las operaciones utilizadas por las pantallas.

## Probar el recorrido del estudiante

Con una cuenta docente llamada `admin`, ejecutar una vez:

```powershell
.\.venv\Scripts\python.exe manage.py preparar_demo --docente admin
```

El comando muestra el código de una práctica de tres preguntas de Español para ingreso a segundo. En la página principal, ingresar ese código, un identificador ficticio nuevo (por ejemplo `EST-01`) y la modalidad de acompañamiento. Responder y enviar; el estudiante verá la confirmación y el docente podrá consultar los aciertos y el porcentaje en **Administración → Intentos**.

El intento se mantiene en la sesión del navegador. Si se vuelve al inicio antes de enviar, se retoma la misma prueba. Al completar, usar **Terminar y volver al inicio** para atender a otro estudiante. No se guardan borradores de respuestas al recargar o cerrar la página antes del envío. Una prueba breve sirve para comprobar el sistema; no constituye por sí sola un diagnóstico pedagógico completo.

## Habilitar las pruebas completas de todos los grados y asignaturas

Para tener disponibles las 12 pruebas diagnósticas (Español, Matemáticas, Ciencias Naturales y Ciencias Sociales para ingreso a primero, segundo y tercero), cada una con sus 20 preguntas del banco:

```powershell
.\.venv\Scripts\python.exe manage.py preparar_pruebas --docente admin
```

El comando lista el código de acceso de cada prueba. Repetirlo no duplica: devuelve los códigos de las pruebas que sigan abiertas y solo crea de nuevo las que se hayan cerrado. Para preparar una sola prueba se pueden usar los filtros `--grado 1|2|3` y `--asignatura ESP|MAT|NAT|SOC`, por ejemplo `preparar_pruebas --grado 1 --asignatura MAT`. La práctica breve de `preparar_demo` se conserva sin cambios.

Si el servidor ya estaba ejecutándose cuando se crearon las carpetas de recursos, reiniciarlo para que reconozca los estilos. Si se usa otro puerto, sustituir `8000` en las direcciones.

## Comprobaciones

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test --noinput
.\.venv\Scripts\python.exe scripts\comprobar_concurrencia.py
```

Las pruebas verifican calificación, integridad, permisos, conservación del contenido y envíos repetidos. El script de concurrencia usa una base temporal para comprobar cuatro estudiantes simultáneos y evitar duplicados al repetir un envío. La demostración HTTP desde dispositivos distintos sigue pendiente.

## Estado del desarrollo y próximos pasos

- [x] Crear el proyecto Django y registrar la aplicación `evaluacion`.
- [x] Elaborar el banco de preguntas en Word.
- [x] Incorporar la propuesta actualizada a la carpeta `docs`.
- [x] Fijar el entorno, las dependencias y las instrucciones de instalación.
- [x] Implementar los modelos de preguntas, opciones, pruebas, intentos y respuestas.
- [x] Configurar la administración del banco y las pruebas, y el acceso docente.
- [x] Implementar las operaciones de inicio de intento, envío y calificación.
- [x] Registrar el acompañamiento y permitir la consulta de resultados en el administrador.
- [x] Verificar las validaciones, los envíos duplicados y la separación de resultados.
- [x] Importar y comprobar la estructura y las claves del banco existente.
- [x] Implementar las pantallas del estudiante y conectarlas a las operaciones del servidor.
- [x] Habilitar las 12 pruebas completas (240 preguntas) mediante `preparar_pruebas`.
- [ ] Revisar visualmente las pantallas y completar la revisión pedagógica de los ítems.
- [ ] Ejecutar las pruebas en red local y documentar las evidencias.
- [ ] Completar la guía de uso y el informe final con resultados observados.

El recorrido de una evaluación breve ya se comprobó mediante HTTP local, desde el ingreso hasta el resultado guardado. El siguiente hito es repetirlo desde otros dispositivos en la red local.

Para las pruebas académicas se utilizarán estudiantes ficticios o identificadores de prueba. La aplicación real con menores se planificará con la institución.

## Documentación y referencias

- [Propuesta actualizada](docs/Propuesta_Proyecto_Redes_EduDiagnostico_Actualizada.docx.md).
- [Banco de preguntas](docs/EduDiagnostico_Banco_de_Preguntas.docx).
- [Base de datos, administración y guía de integración](docs/Base_de_datos.md).
- [MEN: Estándares Básicos de Competencias](https://www.mineducacion.gov.co/1621/articles-340021_recurso_1.pdf).
- [Colombia Aprende: colección de Derechos Básicos de Aprendizaje](https://www.colombiaaprende.edu.co/contenidos/coleccion/derechos-basicos-de-aprendizaje).

La propuesta remite al documento `Informe_Final_EduDiagnostico_Base.docx` para la bibliografía completa. Ese informe aún no está incluido en este repositorio.

## Trabajo futuro

Aciertos por competencia, recomendaciones automáticas, informes avanzados, exportación de resultados, adaptación de preguntas, recursos multimedia y ampliación del banco.
