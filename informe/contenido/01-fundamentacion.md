# 1. Introducción

## 1.1 Fundamentación teórica

La Ingeniería de Software Asistida por Computadora (CASE, por sus siglas en inglés) se enmarca dentro de la **Ingeniería de Software**, y forma parte de las tecnologías de apoyo al desarrollo de software. Su propósito es proveer herramientas automatizadas que faciliten las fases del ciclo de vida: análisis, diseño, codificación, pruebas, implementación y mantenimiento.

Desde una perspectiva más amplia, la ingeniería asistida por computadora (CAE) engloba áreas como el diseño (CAD) y la manufactura (CAM). CASE es la aplicación de esos principios al software: es una **subcategoría de la Ingeniería de Software** y un subcampo de la ingeniería asistida por computadora. Su objetivo es aumentar la productividad, la calidad y la eficiencia en la construcción de sistemas mediante herramientas automatizadas.

Este informe recorre los diez temas de fundamentación pedidos (capítulos 1 a 10) y, en cada uno, indica cómo se aplicó en el proyecto: una plataforma CASE web de modelado UML 2.5 colaborativo, con inteligencia artificial como un integrante más de la sala, generación de backend (Spring Boot) y de proyecto Flutter, e IA local reentrenada.

## 1.2 Capítulo 1: Ingeniería de software asistida por computadora (CASE)

La ingeniería de software asistida por computadora, conocida por la sigla CASE (*Computer-Aided Software Engineering*), se ubica dentro de la **Ingeniería de Software** (en el ámbito de las tecnologías de apoyo y automatización) y es una subdisciplina de la ingeniería asistida por computadora (CAE), junto al diseño (CAD) y la manufactura (CAM) asistidos (Pressman & Maxim, 2020). Reúne reúne las herramientas que automatizan actividades del desarrollo: análisis, diseño, generación de código, pruebas, documentación y gestión del proyecto (Sommerville, 2011). Su propósito es aumentar la productividad, reducir errores humanos y mantener la coherencia entre los productos del proceso.

Las herramientas CASE suelen clasificarse según la etapa del ciclo de vida que apoyan: las **CASE superiores** (*upper CASE*) cubren planificación, análisis y diseño, y su producto típico son los modelos y diagramas; las **CASE inferiores** (*lower CASE*) cubren la implementación, las pruebas y el mantenimiento; y las **CASE integradas** (*I-CASE*) enlazan ambas con un repositorio común, de modo que el modelo y el código no se desincronizan (Pressman & Maxim, 2020). Fuggetta (1993) propone otra clasificación por alcance de la integración: *herramientas* (una tarea), *bancos de trabajo* (*workbenches*, un conjunto de tareas) y *entornos* (todo el proceso).

**Aplicación en el proyecto.** La plataforma es una herramienta CASE integrada de tipo banco de trabajo: modela (parte superior) y genera el backend Spring Boot, la colección de Postman y el proyecto Flutter a partir del mismo diagrama (parte inferior). El diagrama es la fuente única de la que salen el SQL, el XMI, la imagen y el código, lo que evita mantener esos productos a mano. La novedad de esta entrega es una herramienta CASE con **colaboración en tiempo real** y con **IA como integrante del equipo**.

## 1.3 Capítulo 2: Ingeniería de software basada en componentes

La ingeniería de software basada en componentes (CBSE) construye sistemas ensamblando piezas independientes y reutilizables en lugar de escribir todo desde cero. Un **componente** es una unidad de composición con interfaces contractualmente especificadas y dependencias de contexto explícitas, que puede desplegarse de forma independiente (Szyperski, 2002). Su objetivo principal es la **productividad**: reutilizar reduce tiempo y costo, y un componente ya probado aporta calidad (Sommerville, 2011).

Los principios son la **separación de interfaz e implementación** (quien usa un componente no conoce su interior), la **composición** (los sistemas se arman uniendo componentes) y la **reutilización** con un repositorio de piezas documentadas. Los riesgos son la dependencia de terceros, la incompatibilidad entre versiones y la dificultad de adaptar un componente a un uso para el que no fue diseñado.

**Aplicación en el proyecto.** El sistema está hecho de componentes con fronteras claras: el editor Angular (componentes de interfaz y servicios), la aplicación `collab` de Django (colaboración), la aplicación `uml_api` (IA, XMI, generador Flutter), el generador Spring Boot como servicio independiente y los servicios de infraestructura (Redis, PostgreSQL, Ollama). Se reutilizaron componentes de terceros (JointJS, Django Channels, Daphne, Spring Boot) y se decidió explícitamente no reescribir el editor existente sino extenderlo.

## 1.4 Capítulo 3: Desarrollo de software basado en componentes

El desarrollo basado en componentes es el proceso para aplicar la CBSE: se **identifican** los requisitos que pueden cubrirse con componentes existentes, se **seleccionan** candidatos según criterios (funcionalidad, calidad, licencia, soporte), se **adaptan** mediante envoltorios o configuración y se **integran** con un código de pegamento y pruebas de integración (Sommerville, 2011). Después del despliegue, el mantenimiento se divide en cuatro tipos: **correctivo** (errores), **adaptativo** (cambios del entorno), **perfectivo** (mejoras) y **preventivo** (reducir riesgos futuros).

**Aplicación en el proyecto.** Para elegir el motor de dibujo se evaluó reutilizar JointJS frente a construir uno propio; para la colaboración se eligió un relé de WebSocket propio sobre Django Channels, en lugar de un servicio externo, porque el servidor debía conocer los roles y registrar la actividad. Los mantenimientos fueron todos reales durante el proyecto: **correctivo** (la validación con IA bloqueaba el servidor al salir de una sala), **adaptativo** (nuevo proveedor de IA local detrás de una interfaz), **perfectivo** (entidad intermedia automática en relaciones muchos a muchos) y **preventivo** (límites de costo de la IA, rotación de una contraseña expuesta y revisión de código independiente).

## 1.5 Capítulo 4: Arquitectura de software

La arquitectura es la estructura fundamental de un sistema: sus elementos, las relaciones entre ellos y las propiedades de ambos (Bass et al., 2012). Su calidad se mide por atributos como la **modificabilidad** (que el software viva mucho tiempo porque sea sencillo de cambiar), el rendimiento, la disponibilidad y la seguridad. Se describe con varias **vistas** (lógica, de procesos, de despliegue) y con modelos como C4, que organiza la descripción en cuatro niveles: contexto, contenedores, componentes y código (Brown, s. f.).

Entre los **estilos** relevantes están la arquitectura **en capas**, el **cliente-servidor** y las arquitecturas **orientadas a eventos**. Para la comunicación en tiempo real, el protocolo **WebSocket** (Fette & Melnikov, 2011) mantiene una conexión bidireccional persistente sobre HTTP, de modo que el servidor puede enviar datos sin que el cliente los pida, a diferencia del modelo petición-respuesta de REST (Fielding, 2000).

**Aplicación en el proyecto.** La arquitectura combina capas y eventos: el cliente Angular habla con Django por REST (actividad, chat, respaldos) y por **WebSocket** (edición y presencia); Django actúa como **relé**: cada operación de edición llega al servidor y este la retransmite a todos los miembros de la sala, aplicando permisos (solo el *host* puede expulsar) y registrando la actividad. El estado efímero (orden de conexión, de donde sale el *host*) vive en **Redis**; el persistente, en **PostgreSQL**. La modificabilidad se cuidó con interfaces estables: el proveedor de IA es una interfaz con implementaciones intercambiables (nube o local) y el formato de las operaciones es el mismo para la edición manual y para los cambios de la IA.

## 1.6 Capítulo 5: Proceso de diseñar una base de datos

Diseñar una base de datos es una de las fases más críticas del ciclo de vida, porque garantiza que la información se represente correctamente y se manipule con eficiencia. El proceso recorre pasos ordenados, desde un nivel conceptual abstracto hasta la implementación física y su integración en el código del backend (Rumbaugh et al., 1991).

### 1) Diseño conceptual

Es el modelo del dominio con entidades, atributos y relaciones, independiente de cualquier sistema gestor de base de datos. La técnica habitual es el modelo entidad-relación o el modelo orientado a objetos. En el proyecto es el **diagrama de clases UML** que dibuja el usuario en el editor.

### 2) Diseño lógico

Es la traducción al modelo relacional: cada clase pasa a ser una tabla, se definen claves primarias y foráneas, una relación **muchos a muchos** se resuelve con una **tabla intermedia** y una herencia se resuelve con una de varias estrategias (tabla por clase, por jerarquía o por clase concreta). La plataforma crea automáticamente una **entidad intermedia visible** con sus dos claves foráneas cuando el usuario dibuja una relación muchos a muchos.

### 3) Diseño físico

Es la elección del motor y de los tipos de datos concretos, los índices y las restricciones. El proyecto apunta a **PostgreSQL** y exporta un guion SQL con las tablas.

### 4) Implementación en código backend

Son las entidades, los repositorios y los servicios que acceden a las tablas. La plataforma los genera en Spring Boot, con la estructura en capas que exige la materia.

### 5) Mantenimiento y evolución

Son las migraciones controladas cuando el modelo cambia. En Django, las migraciones versionan el esquema de la propia plataforma: la aplicación `collab` tiene cuatro migraciones, una por cada cambio de su modelo de datos.

## 1.7 Capítulo 6: Construcción del backend (ORM)

La construcción del backend implementa la lógica de negocio, la gestión de datos y la comunicación entre la aplicación y la base de datos. En este contexto, el mapeo objeto-relacional simplifica la interacción entre el modelo de datos y el código fuente (Fowler, 2002).

### 1. Concepto de ORM

Un **ORM** (*Object-Relational Mapping*) asocia las estructuras de una base relacional (tablas, atributos, claves) con clases de un lenguaje orientado a objetos, de modo que se manipulan objetos en lugar de escribir sentencias SQL.

### 2. Ventajas del uso de ORM en el backend

Aumenta la productividad, da portabilidad entre motores de base de datos, protege frente a la inyección SQL al usar consultas parametrizadas y versiona el esquema con migraciones. Sus costos son la curva de aprendizaje y las consultas poco eficientes si se usa sin cuidado (por ejemplo, el problema de las *N+1 consultas*).

### 3. Ciclo de construcción del backend con ORM

Se definen las entidades, se genera o escribe el esquema, se implementan los repositorios, se encapsula la lógica de negocio en servicios y se expone mediante controladores.

### 4. Herramientas ORM más utilizadas

**Hibernate/JPA** en Java y el **ORM de Django** en Python. El proyecto usa ambos: el ORM de Django para los datos de la propia plataforma (participantes, actividad, chats) y **Spring Data JPA** en el backend que se genera, con entidad, DTO, repositorio, servicio y controlador, más los endpoints JSON y una colección de Postman para probarlos. Una prueba automática de Spring compila de verdad el proyecto generado para evitar que el generador produzca código roto.

## 1.8 Capítulo 7: La IA aplicada a la ingeniería de software

Los **modelos de lenguaje grandes** (LLM), basados en la arquitectura *Transformer* (Vaswani et al., 2017), se aplican a la ingeniería de software en la generación y revisión de código, la redacción de documentación, la ayuda al modelado y las pruebas. Sus riesgos son las **alucinaciones** (respuestas plausibles pero falsas), el costo por uso, la privacidad de los datos enviados y la dependencia de un proveedor externo. Por eso conviene usarlos con límites: que un humano apruebe lo destructivo, que se mida su exactitud y que exista una alternativa.

**Dónde se aplica en el proyecto.**

- **Texto a UML, imagen a UML y voz a UML:** un pedido en lenguaje natural, una foto de un diagrama o una instrucción hablada se convierten en el JSON del diagrama.
- **La IA como integrante de la sala:** un solo modelo atiende a varias personas, con un **chat privado por participante** y con el **registro de actividad** de la sala como contexto, de modo que puede responder "¿qué hizo Bruno?". Tiene tres modos: *preguntar* (solo responde), *pedir cambio* (propone un cambio que se aplica en el navegador de quien lo pidió y queda registrado como "IA, a pedido de X") y *revisar* (publica observaciones para toda la sala, cada una con un botón para aplicarla). La IA no hace nada hasta que alguien se lo pide; los cambios que eliminan elementos piden confirmación.
- **IA local y reentrenada:** como alternativa sin internet, se reentrenó un modelo abierto. Se usó **LoRA** (*Low-Rank Adaptation*), que congela el modelo y entrena solo matrices de bajo rango añadidas a sus capas, con menos del 1 % de los parámetros (Hu et al., 2021), sobre un modelo cuantizado a 4 bits en la variante **QLoRA** (Dettmers et al., 2023), de la familia Qwen (Qwen Team, 2025), con el marco MLX de Apple. El resultado, un adaptador de unas decenas de megabytes, se fusiona con el modelo base y se sirve con Ollama. Los datos de entrenamiento se generan de forma determinista con reglas (la respuesta correcta se calcula, no se pide a otro modelo) y se mide con ejemplos que el modelo nunca vio: en la primera corrida, en dos corridas el modelo pasó de acertar el 35 % de los pedidos a acertar el 82 % (Anexo B).

## 1.9 Capítulo 8: UML 2.5

El Lenguaje Unificado de Modelado (UML) es el estándar del *Object Management Group* (OMG) para especificar, visualizar y documentar sistemas; su versión vigente en este proyecto es la 2.5.1 (OMG, 2017). Define **14 tipos de diagrama** en tres grupos:

| Grupo | Diagramas |
|---|---|
| **Estructura** | de clases, de objetos, de componentes, de estructura compuesta, de paquetes, de despliegue, de perfiles |
| **Comportamiento** | de casos de uso, de actividades, de máquina de estados |
| **Interacción** | de secuencia, de comunicación, de tiempos, de vista global de interacción |

El **diagrama de clases** describe clases (nombre, atributos y operaciones, con visibilidad `+ público`, `- privado`, `# protegido`) y sus **relaciones**:

| Relación | Significado | Notación |
|---|---|---|
| **Asociación** | Las instancias se conocen o se usan | línea; con **multiplicidad** (`1`, `0..1`, `*`, `1..*`) y nombre de rol |
| **Agregación** | "tiene un": el todo contiene partes que pueden existir sin él | línea con rombo vacío en el todo |
| **Composición** | agregación fuerte: las partes mueren con el todo | línea con rombo lleno |
| **Generalización (herencia)** | "es un": la subclase hereda de la superclase | línea con triángulo vacío hacia la superclase |
| **Dependencia** | una clase usa a otra de forma puntual | flecha discontinua |
| **Realización** | una clase implementa una interfaz | flecha discontinua con triángulo vacío |

**Aplicación en el proyecto.** El editor soporta clases con atributos tipados y operaciones, y las relaciones de asociación (con multiplicidades editables en cada extremo), agregación, composición, generalización y dependencia. La relación muchos a muchos genera la entidad intermedia. Los diagramas de la Parte 2 (casos de uso, comunicación, clases de análisis, paquetes, secuencia, componentes y despliegue) siguen esta notación. Para intercambiar modelos con herramientas externas se implementó **XMI** (OMG, 2015) en ambos sentidos con Enterprise Architect.

## 1.10 Capítulo 9: PUDS

El **Proceso Unificado de Desarrollo de Software** (PUDS) es un marco de proceso **dirigido por casos de uso**, **centrado en la arquitectura** e **iterativo e incremental** (Jacobson et al., 2000; Torossi, s. f.). Su ciclo de vida tiene cuatro **fases**, cada una cerrada por un **hito**:

| Fase | Hito | Pregunta que responde |
|---|---|---|
| **Inicio** | Objetivos del ciclo de vida | ¿Es viable y qué alcance tiene? |
| **Elaboración** | Arquitectura del ciclo de vida | ¿Tenemos una arquitectura estable que resuelva los riesgos principales? |
| **Construcción** | Capacidad operativa inicial | ¿Está construido el producto y es utilizable? |
| **Transición** | Lanzamiento del producto | ¿Está listo para sus usuarios? |

Y cinco **flujos de trabajo** (disciplinas) que se repiten en cada iteración con distinto peso: **requisitos, análisis, diseño, implementación y pruebas**. Cada uno produce artefactos (modelo de casos de uso, clases de análisis, descripción de la arquitectura, modelo de despliegue, componentes, casos de prueba, entre otros).

**Aplicación en el proyecto.** El trabajo se organizó en iteraciones: **I0** cerró la línea base (Inicio); **I1** (identidad y registro de actividad) validó la arquitectura de punta a punta (Elaboración); **I2 a I6** construyeron el chat, las acciones y la revisión, las sesiones continuas, la vista móvil y la IA local (Construcción); **I7** y el reentrenamiento cerraron con el endurecimiento, el despliegue y la entrega (Transición). Cada iteración terminó en un incremento probado e integrado. La Parte 2 registra los artefactos de cada disciplina.

## 1.11 Capítulo 10: Lenguaje de modelado de software (modelo C4)

El **modelo C4** es una técnica para describir y visualizar la arquitectura de un sistema en cuatro niveles de detalle, de lo general a lo particular (Brown, s. f.):

1. **Contexto:** el sistema como una caja negra, sus usuarios y los sistemas externos con los que se relaciona.
2. **Contenedores:** las aplicaciones y almacenes de datos que se ejecutan por separado (una aplicación web, una API, una base de datos) y cómo se comunican.
3. **Componentes:** las piezas internas de un contenedor y sus responsabilidades.
4. **Código:** las clases o módulos principales de un componente.

C4 no reemplaza a UML: lo complementa, porque cada nivel puede detallarse con diagramas UML cuando hace falta. Su ventaja es que cada diagrama tiene un público claro (quien decide, quien construye, quien programa) y se mantiene legible.

**Aplicación en el proyecto.** En la sección 2.3.1 se presentan los cuatro niveles: el contexto (participantes, observadores, Gemini, Ollama y Enterprise Architect), los contenedores (aplicación web, API y tiempo real, generador Spring, PostgreSQL y Redis), los componentes de la API de Django (relé de WebSocket, actividad e identidad, chat con la IA, guardia de cambios, proveedores de IA, XMI y generador Flutter) y el código de los proveedores de IA.
