# EduDiagnóstico

Aplicación web cliente-servidor para aplicar **evaluaciones diagnósticas** a estudiantes que ingresan a **1.º, 2.º y 3.º de primaria**, registrar sus respuestas y mostrar al docente los resultados por grado y asignatura.

Proyecto final de la asignatura **Redes de Computadoras**, Ingeniería de Sistemas, Universidad de los Llanos.

> 🚧 **Estado:** en desarrollo (primera versión funcional).

---

## ¿Qué problema resuelve?

Al iniciar el año escolar, los docentes necesitan conocer los saberes previos con los que llegan sus estudiantes para planear la nivelación. Aplicar estas pruebas en papel, calificarlas y consolidar los resultados toma tiempo y deja la información dispersa. EduDiagnóstico centraliza ese proceso: el estudiante responde desde el navegador, el servidor califica y el docente consulta un resumen.

El diagnóstico tiene **finalidad formativa**: sirve para orientar la nivelación, no para promover ni excluir estudiantes.

## Funcionalidades

- Selección de grado y asignatura, o acceso a una prueba mediante un código.
- Presentación de preguntas y envío de respuestas desde el navegador.
- Calificación automática de ítems de respuesta objetiva.
- Consulta de aciertos y puntajes por asignatura para el docente.
- Panel administrativo para gestionar el banco de preguntas.

**Asignaturas:** Matemáticas, Lenguaje, Inglés, Ciencias Sociales y Ética y Valores.

**Banco de preguntas:** meta de hasta 20 preguntas por asignatura y grado (≈300 en total), organizadas por competencia y basadas en los **Derechos Básicos de Aprendizaje (DBA)** del Ministerio de Educación Nacional. Como referente se usan los DBA del grado anterior al que ingresa el estudiante.

## Arquitectura

```
┌──────────────────────┐   HTTP/HTTPS    ┌──────────────────────┐   SQL interno   ┌──────────────┐
│       CLIENTES       │ ──────────────▶ │    SERVIDOR WEB      │ ──────────────▶ │    DATOS     │
│ Navegadores de       │ ◀────────────── │ Django / Python      │ ◀────────────── │ SQLite       │
│ estudiantes/docentes │   GET / POST    │ Lógica de la app     │                 │ (en servidor)│
└──────────────────────┘                 └──────────────────────┘                 └──────────────┘
```

- Los **clientes** acceden desde equipos distintos al servidor, por red local o internet.
- El **servidor Django** atiende las solicitudes HTTP, procesa los formularios y genera las respuestas.
- La **base de datos** permanece en el servidor y no es accesible directamente desde los clientes.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python, Django |
| Frontend | Plantillas HTML de Django, CSS, Bootstrap |
| Base de datos | SQLite (migrable a PostgreSQL) |
| Análisis de red | Wireshark, herramientas de desarrollo del navegador |


