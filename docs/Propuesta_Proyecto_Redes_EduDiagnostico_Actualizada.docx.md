# **EduDiagnóstico**

## *Propuesta del proyecto final*

Aplicación web cliente servidor para evaluación diagnóstica en primero, segundo y tercero de primaria

Proyecto de Redes  \|  4 de noviembre de 2026

## **1 Situación problemática**

Al iniciar el año escolar, los docentes necesitan reconocer los conocimientos previos de los estudiantes. La aplicación y consolidación manual de diagnósticos puede demandar tiempo y dispersar la información. EduDiagnóstico propone centralizar respuestas y resultados para apoyar la planeación de actividades de refuerzo.

## **2 Objetivo y solución propuesta**

Desarrollar una aplicación web cliente servidor que permita aplicar evaluaciones diagnósticas a estudiantes que ingresan a primero, segundo y tercero de primaria, registrar sus respuestas y consultar el desempeño general por asignatura. El docente dispondrá de una vista de administración y resultados, y el estudiante de una interfaz sencilla para responder.

## **3 Alcance inicial**

* Grados: primero, segundo y tercero. Cada prueba abordará aprendizajes previos pertinentes para iniciar el grado seleccionado.  
* Asignaturas: Español, Matemáticas, Ciencias Naturales y Ciencias Sociales. Español se vincula con el área de Lenguaje de los referentes oficiales.  
* Banco: cuatro asignaturas por tres grados, 12 bancos. Meta de hasta 20 preguntas por banco, hasta 240 en total, con carga progresiva. Cada sesión podrá usar una selección breve.  
* Funciones: habilitar pruebas, seleccionar grado y asignatura, presentar preguntas objetivas, enviar respuestas, calificarlas y consultar cantidad de aciertos y porcentaje por asignatura.  
* Trabajo futuro: aciertos por competencia, recomendaciones automáticas, informes avanzados y adaptación de preguntas.

## **4 Referentes pedagógicos**

Las cuatro asignaturas se apoyarán en los estándares del MEN para primero a tercero y en los DBA de Lenguaje, Matemáticas, Ciencias Naturales y Ciencias Sociales. Para el ingreso a segundo se tomarán aprendizajes de primero; para tercero, de segundo. Para ingresar a primero se propondrán actividades integradas a partir de los referentes de transición, sin convertir sus DBA en requisitos de admisión o una lista de logros para aprobar. El banco requerirá revisión docente y tendrá finalidad formativa \[7–13\].

# **Aplicación y funcionamiento**

## **5 Acompañamiento en primero**

Se recomienda aplicar el diagnóstico estudiante por estudiante, con acompañamiento del docente y un auxiliar. Como alternativa se podrán organizar grupos de hasta cuatro estudiantes: el docente acompañará a dos niños y el auxiliar a los otros dos. Cada estudiante responderá de forma individual y tendrá su propio registro.

Los adultos explicarán la navegación, leerán las instrucciones cuando sea necesario y facilitarán el uso del dispositivo sin indicar la respuesta correcta. En preguntas que evalúen lectura, el apoyo se definirá en la guía del ítem para conservar el sentido de la evaluación. Se registrará la modalidad de acompañamiento para contextualizar el resultado.

## **6 Funcionamiento previsto**

1. El docente ingresa a su cuenta, selecciona grado y asignatura y habilita una prueba mediante un código de acceso.  
2. El estudiante accede desde un navegador con un identificador asignado para esa aplicación y responde con el apoyo previsto.  
3. El servidor valida las respuestas, las guarda y calcula los aciertos de las preguntas objetivas.  
4. El docente consulta el desempeño general por asignatura. Los análisis por competencia se reservan para una fase posterior.

## **7 Presentación del desempeño**

Para cada intento se mostrará la asignatura, el grado, la fecha, el número de preguntas aplicadas, los aciertos y el porcentaje de aciertos. Todas las preguntas tendrán el mismo peso. Porcentaje de aciertos \= aciertos / preguntas aplicadas × 100\. No se establecerán niveles como bajo, medio o alto sin un criterio pedagógico previamente acordado.

## **8 Arquitectura y relación con Redes**

Navegadores de estudiantes y docente → HTTP en red local → Django → SQLite en el servidor.

La demostración se realizará desde equipos distintos al servidor y documentará direcciones IP, puerto, solicitudes GET/POST y almacenamiento separado de resultados. Se probará el acceso de cuatro estudiantes en simultáneo como escenario previsto de aplicación. La base de datos será un archivo local del servidor, sin acceso directo desde los clientes.

La red local será el escenario inicial. Los recursos de la interfaz se alojarán en el servidor para funcionar sin conexión a internet. Una publicación posterior en internet requerirá HTTPS y una configuración de despliegue adecuada.

# **Tecnologías y desarrollo previsto**

## **9 Base tecnológica propuesta**

| Tecnología | Versión o criterio | Uso |
| :---- | :---- | :---- |
| Python | 3.14.10 \[1\] | Lenguaje del servidor |
| Django | 5.2.19 LTS \[2–4\] | Páginas, formularios, acceso y datos |
| SQLite | 3.x incluida en Python; mínimo 3.31.0 \[6\] | Datos del prototipo |
| Bootstrap | 5.3.8 \[5\] | Interfaz adaptable; archivos locales |
| HTML y CSS | HTML5 y CSS moderno | Estructura y presentación |
| JavaScript | Nativo del navegador | Interacciones puntuales |

Estas versiones constituyen la base propuesta al 4 de noviembre de 2026; no representan una instalación ya realizada. Django 5.2 admite Python 3.14 y su soporte extendido llega hasta abril de 2028\. Al preparar el entorno se comprobará la versión exacta de SQLite y se fijarán las dependencias instaladas. Las actualizaciones posteriores quedarán documentadas.

## **10 Entregables y evolución**

Se entregarán la aplicación, el banco inicial revisado, el registro y consulta de resultados, una guía de uso y las evidencias de comunicación entre dispositivos. El informe final incorporará requisitos, arquitectura, tecnologías, procedimiento de pruebas, resultados observados y conclusiones una vez se implemente y verifique el sistema.

Para las pruebas académicas se utilizarán estudiantes ficticios o identificadores de prueba. La aplicación real con menores se planificará con la institución. Como mejoras futuras se contemplan aciertos por competencia, recomendaciones, exportación, recursos multimedia y ampliación del banco.

## **Referencias y consulta**

Fuentes consultadas el 4 de noviembre de 2026\. La bibliografía completa está en Informe\_Final\_EduDiagnostico\_Base.docx: \[1–6\] tecnologías; \[7\] transición; \[8\] estándares; \[9–12\] DBA de las cuatro áreas; \[13\] Ley 115\. Enlaces pedagógicos principales:

MEN. Estándares Básicos de Competencias.

[https\://www\.mineducacion.gov.co/1621/articles-340021\_recurso\_1.pdf](https://www.mineducacion.gov.co/1621/articles-340021_recurso_1.pdf)

Colombia Aprende. Colección de DBA por área y grado.

[https\://www\.colombiaaprende.edu.co/contenidos/coleccion/derechos-basicos-de-aprendizaje](https://www.colombiaaprende.edu.co/contenidos/coleccion/derechos-basicos-de-aprendizaje)