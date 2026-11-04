# 1. Fundamentación teórica

Este capítulo reúne la teoría sobre la que se apoya el proyecto, en los seis temas que se evalúan en el segundo parcial, y la del Proceso Unificado de Desarrollo de Software, que ordena el registro del capítulo 2. En cada tema, después de la teoría, se dice cómo se aplica en la herramienta.

## 1.1 Continuación del primer parcial

Este documento es el **segundo parcial** y reúne todo lo construido: la herramienta CASE colaborativa del primer parcial y lo que se le agregó después. El modelo de casos de uso es el mismo para todo el proyecto y está organizado en **cuatro ciclos de vida**:

- **Ciclo 1:** ingresar a una sala de trabajo, modelar el diagrama de clases y retomar el trabajo en otra sesión (CU1, CU2 y CU5).
- **Ciclo 2:** colaborar en la edición, expulsar a un participante, modificar el modelo con la IA y crear el modelo desde una imagen (CU3, CU4, CU7 y CU8).
- **Ciclo 3:** intercambiar el diagrama con otras herramientas, generar el backend y generar la aplicación móvil (CU10, CU11 y CU12).
- **Ciclo 4, lo nuevo de este parcial:** consultar la actividad del equipo, consultar a la IA, mantenerse informado desde el celular y aprender a usar la herramienta con un asistente de ayuda (CU6, CU9, CU13 y CU14).

Después del primer parcial el docente pidió que la inteligencia artificial deje de ser una herramienta aparte y pase a ser **un integrante más de la sala**: un desarrollador que no hace nada hasta que se lo piden, que sabe lo que hizo cada persona, que es una sola instancia para todo el equipo y cuyas ideas todos pueden ver. Pidió además que el celular sea informativo y avise de lo que pasa, una base de datos NoSQL, la IA local como extra valorable y un mecanismo para que la persona aprenda a usar la herramienta. Su criterio de valor es **reducir el tiempo de desarrollo y mejorar la productividad** de quien diseña.

## 1.2 Tema 1: ingeniería de software asistida por computadora (CASE)

La **ingeniería de software** es la aplicación de un enfoque sistemático, disciplinado y cuantificable al desarrollo, la operación y el mantenimiento del software (Pressman & Maxim, 2020; Sommerville, 2011). Como el software es abstracto y cambia sin parar, desde los años ochenta se construyen herramientas que ayudan a quien lo desarrolla: las herramientas **CASE** (*Computer-Aided Software Engineering*).

Fuggetta (1993) las clasifica según cuánto del proceso cubren: las **herramientas** (*tools*) dan soporte a una tarea concreta, como un editor de diagramas; los **bancos de trabajo** (*workbenches*) integran varias herramientas para una fase, como el análisis y el diseño; y los **entornos** (*environments*) dan soporte a todo el proceso. Otra distinción usual separa las herramientas de las fases tempranas (*upper CASE*: requisitos, análisis, diseño) de las que producen código y lo prueban (*lower CASE*).

**En el proyecto.** La plataforma es un banco de trabajo CASE para el modelado UML 2.5 de clases y datos. Cubre el extremo temprano, porque modelar el diagrama de clases es su función central, y el tardío, porque del mismo diagrama genera el script SQL, un proyecto Spring Boot con PostgreSQL y su colección de Postman, y un proyecto Flutter con base de datos local. Lo que la diferencia de un editor de escritorio es que varias personas trabajan a la vez sobre el mismo modelo, con roles, recuperación del estado e intercambio con Enterprise Architect por XMI, y que una inteligencia artificial participa como un integrante más.

## 1.3 Tema 2: arquitectura del software

La **arquitectura del software** es el conjunto de decisiones de estructura que son costosas de cambiar después: cómo se divide el sistema en partes, qué responsabilidad tiene cada una y cómo se comunican (Bass et al., 2012). Su propósito es que el software **viva más tiempo**: que se pueda entender, cambiar y hacer crecer sin rehacerlo, cuidando atributos de calidad como la modificabilidad, el rendimiento, la seguridad y la disponibilidad. Una arquitectura se aborda desde varias perspectivas; aquí se tratan cuatro: el backend, el frontend, las bases de datos y el despliegue.

### 1.3.1 Backend: arquitectura hexagonal

La **arquitectura hexagonal** o de puertos y adaptadores (Cockburn, 2005) pone la lógica de la aplicación en el centro y la rodea de **puertos**, interfaces que dicen qué necesita el núcleo del mundo exterior (guardar un dato, llamar a un servicio de IA), e implementa cada puerto con **adaptadores** intercambiables (una base de datos concreta, un proveedor concreto). El núcleo depende solo de las interfaces, así que cambiar una tecnología es cambiar un adaptador, y las pruebas pueden sustituirlo por uno en memoria.

**En el proyecto.** El backend de Django declara sus puertos en `collab/ports.py` y `ai_provider.py`: `ActivityStore` y `ConversationStore` (dónde se guardan la actividad y la conversación), `TurnStore` (el turno de la IA de cada sala), `RateLimiter` (los topes de uso) y `AIProvider` (quién responde). Cada uno tiene sus adaptadores: PostgreSQL y MongoDB para la actividad y la conversación, Redis y la memoria para el turno y los topes, Gemini y Ollama para la IA. Una variable de entorno elige el adaptador y `collab/stores.py` lo entrega a las vistas. Las **mismas pruebas de contrato** se ejecutan contra cada adaptador, que es lo que garantiza que son intercambiables (secciones 2.3 y 2.5).

### 1.3.2 Frontend

El cliente es una aplicación de una sola página en **Angular 20**: una jerarquía de componentes (el editor, el panel de la IA, la actividad, la vista del celular) que dependen de servicios que se les inyectan (el diagrama, la colaboración, la IA, las exportaciones). Los estados que cambian con el tiempo se modelan con **señales** reactivas, que actualizan solo lo que depende de ellas. La separación entre componentes (presentación) y servicios (lógica y comunicación) es la misma idea de la arquitectura hexagonal aplicada al navegador: por ejemplo, `DiagramApi` es una interfaz que le dice al servicio de colaboración lo que necesita del diagrama sin depender del servicio que lo dibuja. El renderizado en servidor (SSR) entrega la primera pantalla desde el servidor.

### 1.3.3 Bases de datos

No hay una base de datos mejor en general: cada familia sirve a un tipo de dato (Elmasri & Navathe, 2016; MongoDB, Inc., s. f.).

- Las **relacionales** (PostgreSQL) guardan tablas con esquema fijo, integridad referencial y transacciones. Son la elección para datos con relaciones fuertes.
- Las **de clave-valor** (Redis; y Dynamo, el sistema de Amazon que inspiró a DynamoDB, DeCandia et al., 2007) guardan un valor por clave con acceso muy rápido y escalan a lo ancho; Redis vive en memoria y es ideal para lo efímero.
- Las **documentales** (MongoDB) guardan documentos con forma flexible, anidados, que se consultan por sus campos. Encajan con datos que se leen y se escriben como una unidad, que solo se agregan y cuya forma varía.
- Las **vectoriales** guardan vectores numéricos (*embeddings*) de textos o imágenes para buscar por parecido de significado; sirven para dar contexto a una IA con grandes colecciones de documentos (Lewis et al., 2020).

**En el proyecto.** Cada dato está donde le corresponde. PostgreSQL guarda lo relacional: los participantes, los intentos de uso de la IA y el respaldo del diagrama. MongoDB guarda la actividad y la conversación con la IA: son documentos que solo se agregan, con un `data` que cambia según el tipo de evento y que se consultan por sala y orden. Redis guarda lo efímero: quién está en la sala y en qué orden, el turno de la IA y los contadores de uso. No se usa una base vectorial porque el manual del asistente de ayuda cabe entero en la petición a la IA; si creciera mucho, sus secciones se guardarían como vectores y solo se enviarían las más parecidas a la pregunta.

### 1.3.4 Despliegue: monolito y microservicios

En un **monolito** todo el sistema es una sola unidad que se construye, se despliega y se escala junta; es simple de desarrollar y de operar, pero **lo más complicado es escalarlo**: para atender más carga hay que replicarlo entero, aunque solo una parte lo necesite, y todo comparte la tecnología y el ciclo de despliegue. En una arquitectura de **microservicios** (Fowler & Lewis, 2014; Newman, 2021) cada capacidad es un servicio pequeño, desplegable y escalable por separado, con su propia base de datos; su beneficio es que se puede subir una parte sin tocar las demás y asignarle recursos según su carga, a cambio de más complejidad: red entre servicios, datos repartidos y más piezas que operar.

**En el proyecto.** El sistema es un **monolito modular con un servicio aparte**: el servidor de Django concentra la API, la colaboración y la IA, y el generador de proyectos es un servicio de Spring Boot separado porque es otro lenguaje y otro ritmo de trabajo; el frontend, las bases de datos y Redis son contenedores propios. Corren con Docker Compose en una sola máquina de AWS detrás de nginx con HTTPS. El diseño ya prepara el crecimiento: el estado que los procesos comparten (turno de la IA, topes de uso, presencia) está en Redis y no en la memoria de un proceso, de modo que se pueden poner varios procesos de Django sin cambiar el código.

### 1.3.5 El modelo C4

El **modelo C4** es una técnica para describir la arquitectura en cuatro niveles de detalle, de lo general a lo particular (Brown, s. f.): el **contexto** (el sistema como una caja negra, sus usuarios y los sistemas externos), los **contenedores** (las aplicaciones y almacenes que se ejecutan por separado), los **componentes** (las piezas internas de un contenedor) y el **código**. No reemplaza a UML: lo complementa, porque cada nivel puede detallarse con diagramas UML. En la sección 2.3.1 se presentan los cuatro niveles del proyecto.

## 1.4 Tema 3: desarrollo de software basado en componentes

El **desarrollo basado en componentes** construye los sistemas ensamblando partes con interfaces bien definidas, en lugar de escribirlos como un bloque (Szyperski, 2002). Un **componente** es una unidad de composición con interfaces contractuales y dependencias explícitas, que se puede reemplazar por otra que cumpla las mismas interfaces. Sus ventajas son la reutilización, el mantenimiento por partes y el reparto del trabajo; su condición es que cada componente oculte sus detalles y exponga solo lo que otros necesitan (Parnas, 1972).

**En el proyecto.** El Proceso Unificado pide dividir el sistema en **subsistemas** con interfaces, y así se hizo (sección 2.3): nueve subsistemas que salen de los paquetes del análisis (el núcleo de la sala, la edición del diagrama, la gestión de la sala, la actividad del equipo, el seguimiento móvil, la asistencia inteligente, el asistente de ayuda, el intercambio y generación, y la carcasa del editor). Cada uno tiene sus interfaces, que son los puertos de la arquitectura hexagonal, y sus dependencias no forman ciclos. En el código, cada subsistema de diseño tiene un subsistema de implementación en carpetas y cada clase vive en un componente (un archivo) al que se puede llegar desde el diseño (sección 2.4). Los componentes de Angular y los puertos y adaptadores de Django son la misma idea aplicada en cada lado.

## 1.5 Tema 4: inteligencia artificial e IA local

Un **modelo de lenguaje grande** (LLM) es una red neuronal con arquitectura *transformer* (Vaswani et al., 2017) entrenada para predecir el siguiente fragmento de texto (*token*) a partir de lo anterior; con suficiente tamaño y datos aprende a seguir instrucciones, resumir, traducir y producir texto estructurado. No guarda memoria entre peticiones: lo único que «sabe» en cada una es el **contexto** que se le envía, es decir, las instrucciones, los datos y la pregunta. Eso define cómo se trabaja con él: se diseña el *prompt*, se le entrega el contexto necesario, se valida lo que devuelve y se decide qué hacer con la respuesta.

**Proceso para integrarla.** Integrar un modelo en un sistema sigue unos pasos: elegir el proveedor y aislarlo detrás de una interfaz; diseñar las instrucciones y el contexto; limitar lo que puede hacer (que solo actúe cuando una persona lo pide y que cada cambio sea revisable); validar la salida antes de usarla (un cambio enorme o con forma inválida se rechaza); controlar el costo y los fallos (topes de uso, mensajes claros si el proveedor falla); y medir con ejemplos que el modelo nunca vio.

**IA local.** Un modelo **local** corre en el propio computador, sin enviar datos a un tercero y sin depender de internet. Sus características son la privacidad, la ausencia de costo por petición y el control del modelo, a cambio de necesitar memoria y cómputo y de ser, por lo general, menos capaz que los modelos grandes de la nube. Para ajustarlo a una tarea se usa **LoRA** (*Low-Rank Adaptation*), que congela el modelo y entrena solo matrices de bajo rango añadidas a sus capas, con menos del 1 % de los parámetros (Hu et al., 2021), sobre un modelo cuantizado a 4 bits en la variante **QLoRA** (Dettmers et al., 2023); el resultado es un adaptador de unas decenas de megabytes que se fusiona con el modelo base y se sirve con herramientas como Ollama. Los datos de entrenamiento se generan de forma determinista y se reservan ejemplos de prueba que el modelo nunca ve, para medir con honestidad si mejoró.

**En el proyecto.** La IA es un **integrante de la sala**: aparece en la lista de participantes, hay una sola instancia y una sola conversación para todos, y conoce el diagrama y la actividad de cada persona. Tiene tres modos: *preguntar* (solo responde), *pedir cambio* (el cambio se aplica en el navegador de quien lo pidió y queda registrado como «IA, a pedido de X») y *revisar* (publica ideas que cualquiera puede aplicar). Para que sea un integrante confiable y no un riesgo, no hace nada hasta que alguien se lo pide, atiende un pedido a la vez por sala, los cambios que eliminan elementos piden confirmación, hay topes de uso por persona, por sala y para todo el servicio, y si el proveedor falla el diagrama no cambia. El proveedor está detrás del puerto `AIProvider`: **Gemini** en la nube o **Ollama con Qwen** en el computador, y para los cambios al diagrama puede usarse el modelo que el equipo reentrenó con LoRA y MLX (Anexos A y B; Qwen Team, 2025). El **asistente de ayuda** usa el mismo proveedor con el manual de la herramienta como contexto: responde solo sobre su uso.

## 1.6 Tema 5: desarrollo dirigido por especificaciones

En el **desarrollo dirigido por especificaciones** (*spec-driven development*) la especificación es la fuente de verdad: primero se escribe, de forma precisa y revisable, qué debe hacer el sistema; después se produce el código a partir de ella y se comprueba contra ella (GitHub, 2025). Es especialmente útil cuando parte del código lo escribe una inteligencia artificial, porque una especificación clara es lo que le dice al asistente qué hacer, qué reglas respetar y cuándo está terminado. Se complementa con el desarrollo guiado por pruebas, en el que la prueba que falla se escribe antes que el código (Beck, 2002).

**En el proyecto.** Así se integra la IA al proceso de desarrollo, no solo al producto:

- **Reglas para quien programa.** `AGENTS.md`, en la raíz del repositorio, le dice a las personas y a los asistentes de IA cómo trabajar: leer el código antes de cambiarlo, no duplicar lo que existe, no tocar los puertos, no guardar secretos, escribir pruebas de lo crítico y terminar solo cuando compila y pasa. Un asistente lo lee al empezar y lo sigue.
- **Especificaciones escritas antes del código.** `docs/REQUIREMENTS.md` lista los requisitos, `docs/GAP_MATRIX.md` dice el estado de cada uno, y los planes (`docs/PLAN_PUDS_IA_PARTICIPANTE.md` y `docs/PLAN_SEGUNDO_PARCIAL.md`) fijan el orden de trabajo, las decisiones y lo que queda fuera.
- **El modelo manda.** El análisis y el diseño del capítulo 2 no son dibujos aparte: son modelos en código (`informe/modelo/`) que se comprueban contra el repositorio. Lo que el diseño dice de una clase, una operación o un mensaje de secuencia tiene que existir en el código, y lo que no existe obliga a corregir el modelo o el software (sección 2.6). Donde faltaba algo, primero se diseñó y después se programó.
- **Pruebas primero.** Cada cambio del ciclo 4 empezó con una prueba que fallaba, y cada defecto que encontró la verificación se reprodujo con una prueba roja antes de corregirlo (secciones 2.4 y 2.5).
- **Revisión previa a cada commit.** Una revisión automática compara cada cambio con las reglas de `AGENTS.md` antes de aceptarlo.

## 1.7 Tema 6: UML 2.5 y del modelo de clases al modelo relacional y a Spring Boot

**UML 2.5.1** (Object Management Group, 2017) es el lenguaje de modelado estándar. De sus catorce diagramas, el **diagrama de clases** es el que describe la estructura estática de un sistema: las clases con sus atributos y operaciones, y las relaciones entre ellas: **asociación** (con sus multiplicidades), **agregación** y **composición** (todo-parte, la segunda con dependencia de vida), **generalización** (herencia), **dependencia** y la **clase asociativa**, que guarda los datos de una asociación. La herramienta de este proyecto edita diagramas de clases con esa notación, y el modelo se intercambia en XMI (Object Management Group, 2015).

**De clases a relacional.** Un diagrama de clases se traslada a un modelo relacional con reglas conocidas (Elmasri & Navathe, 2016): cada clase persistente es una tabla y cada atributo una columna; una asociación «uno a muchos» es una clave foránea en el lado de «muchos»; una asociación «muchos a muchos» exige una **tabla intermedia** con las dos claves foráneas (y la clase asociativa, sus datos); una composición hace que la parte dependa de su todo y se borre con él; y la generalización puede resolverse con una tabla por clase, unidas por la clave. El editor aplica la regla de la tabla intermedia al dibujar: cuando una asociación queda con «muchos» en ambos extremos, crea la entidad intermedia con sus dos relaciones 1:N.

**De clases a Spring Boot.** Por eso trasladar el modelo a Spring Boot es ordenado: el modelo ya trae los atributos y los métodos, y lo que debe generarse es el modelo (las entidades), los servicios, los controladores y los repositorios. El generador del proyecto produce, por cada clase, la **entidad** de JPA (con `@ManyToOne` y su columna de clave foránea, `@OneToMany` con cascada para la composición, `@OneToOne` e `@Inheritance` de tipo *joined* para la herencia), el **DTO**, el **repositorio** (Spring Data), el **servicio** y el **controlador** REST, más la configuración de PostgreSQL y una colección de Postman. El proyecto generado se compila de verdad en las pruebas del generador.

## 1.8 Proceso Unificado de Desarrollo de Software (PUDS)

El **Proceso Unificado de Desarrollo de Software** (Jacobson et al., 2000; Torossi, s. f.) es un proceso de desarrollo **dirigido por casos de uso, centrado en la arquitectura, iterativo e incremental**. No pide inventar nada: establece un flujo de trabajo que se repite en cada ciclo de vida. Los casos de uso son lo que le entrega valor a un actor y guían todo el trabajo; la arquitectura es la vista de los elementos más significativos; el trabajo se hace en iteraciones que producen incrementos del sistema.

Cada ciclo recorre cuatro fases (inicio, elaboración, construcción y transición) y, en cada una, **cinco flujos de trabajo**, que producen artefactos con una traza entre ellos:

| Flujo de trabajo | Qué produce | Dónde está en este documento |
|---|---|---|
| Requisitos | Actores, casos de uso con su ficha, priorización, prototipo de interfaz, glosario y requisitos adicionales | 2.1 |
| Análisis | Paquetes de análisis, clases de análisis (interfaz, control, entidad) y realizaciones de los casos de uso con diagramas de comunicación | 2.2 |
| Diseño | Arquitectura (nodos, subsistemas e interfaces), clases de diseño y realizaciones con diagramas de secuencia | 2.3 |
| Implementación | Subsistemas de implementación, componentes y plan de integración | 2.4 |
| Pruebas | Casos de prueba por cada camino de cada caso de uso, procedimientos, defectos y evaluación | 2.5 |

A ellos se suman en este parcial la validación, la verificación y la auditoría (sección 2.6), que comprueban que lo documentado y lo construido son lo mismo y que cada versión se puede rastrear. Todos los diagramas siguen la notación de UML 2.5.1 y están hechos en Enterprise Architect.
