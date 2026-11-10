# 1. Fundamentación teórica

## 1.1 Ingeniería de software asistida por computadora (CASE)

### 1.1.1 El concepto de CASE y el trípode estratégico de Rational

La **ingeniería de software** es la aplicación de un enfoque sistemático, disciplinado y cuantificable al desarrollo, la operación y el mantenimiento del software (Pressman & Maxim, 2020; Sommerville, 2011). Como el software es abstracto y cambia sin parar, desde los años ochenta se construyen herramientas que ayudan a quien lo desarrolla: las herramientas **CASE** (*Computer-Aided Software Engineering*).

Bajo la visión de Booch, Rumbaugh y Jacobson, las herramientas CASE no son un complemento decorativo ni una utilidad de dibujo, sino la infraestructura que permite gestionar la complejidad de los sistemas grandes. Rational Software Corporation, donde los tres autores unificaron sus métodos, propuso un **trípode estratégico** para industrializar el desarrollo: un **proceso** adaptable (el Proceso Unificado), **herramientas** que lo automatizan (como Rational Rose, la herramienta CASE emblemática de la época) y **servicios** de formación y acompañamiento para adoptarlos (Jacobson et al., 2000). La herramienta CASE es el catalizador que hace que el proceso y el lenguaje de modelado, UML, se puedan ejecutar y sostener en el tiempo.

La filosofía que defiende Booch es que el **modelado visual** es esencial porque el código fuente, aunque es la verdad final del sistema, no basta para comunicar la arquitectura ni las intenciones de diseño a todos los interesados: un modelo hace visibles estructuras y dependencias que en el texto plano no se ven, y permite detectar cuellos de botella arquitectónicos antes de que se solidifiquen en la implementación (Booch et al., 1999).

### 1.1.2 Integración de herramientas y metodología

Fuggetta (1993) las clasifica según cuánto del proceso cubren: las **herramientas** (*tools*) dan soporte a una tarea concreta, como un editor de diagramas; los **bancos de trabajo** (*workbenches*) integran varias herramientas para una fase, como el análisis y el diseño; y los **entornos** (*environments*) dan soporte a todo el proceso. Otra distinción usual separa las herramientas de las fases tempranas (*upper CASE*: requisitos, análisis, diseño) de las que producen código y lo prueban (*lower CASE*).

La contribución del Proceso Unificado a esta integración fueron los **mentores de herramientas** (*tool mentors*): guías que explican cómo ejecutar una buena práctica, como el desarrollo iterativo o la gestión de requisitos, con una herramienta concreta; así se cerró la distancia entre la teoría metodológica y el trabajo diario de quien desarrolla. La automatización de CASE también hace posible la **ingeniería de ida y vuelta** (*round-trip engineering*): los cambios del modelo visual se reflejan en el código y los del código en el modelo, lo que mantiene la integridad del diseño durante la evolución del sistema y evita la degradación arquitectónica de los proyectos largos.

### 1.1.3 La plataforma como herramienta CASE

La plataforma es un banco de trabajo CASE para el modelado UML 2.5 de clases y datos. Cubre el extremo temprano, porque modelar el diagrama de clases es su función central, y el tardío, porque del mismo diagrama genera el script SQL, un proyecto Spring Boot con PostgreSQL y su colección de Postman, y un proyecto Flutter con base de datos local. Lo que la diferencia de un editor de escritorio es que varias personas trabajan a la vez sobre el mismo modelo, con roles, recuperación del estado e intercambio con Enterprise Architect por XMI, y que una inteligencia artificial participa como un integrante más.

## 1.2 Desarrollo de software basado en componentes

### 1.2.1 Definición y empaquetado físico

El **desarrollo basado en componentes** construye los sistemas ensamblando partes con interfaces bien definidas, en lugar de escribirlos como un bloque (Szyperski, 2002). Un **componente** es una unidad de composición con interfaces contractuales y dependencias explícitas, que se puede reemplazar por otra que cumpla las mismas interfaces. Sus ventajas son la reutilización, el mantenimiento por partes y el reparto del trabajo; su condición es que cada componente oculte sus detalles y exponga solo lo que otros necesitan (Parnas, 1972).

En el Proceso Unificado el componente es un elemento **físico** y reemplazable del sistema, que se empaqueta de distintas formas según su naturaleza: un archivo de código fuente (`<<file>>`), un ejecutable (`<<executable>>`), una biblioteca (`<<library>>`), una tabla de la base de datos (`<<table>>`) o un documento (`<<document>>`), y que ofrece un conjunto de interfaces a otros componentes (Jacobson et al., 2000).

### 1.2.2 Principios del proceso basado en componentes

Un proceso basado en componentes se apoya en cuatro principios. El primero es la **reutilización**: lo que ya existe y funciona se ensambla en lugar de volver a escribirse. El segundo es la **encapsulación**: cada componente oculta sus decisiones internas y expone solo sus interfaces, de modo que cambiar un componente no obliga a cambiar los demás (Parnas, 1972). El tercero es la **dependencia explícita**: lo que un componente necesita de otros se declara, y por eso se puede sustituir por otro que cumpla las mismas interfaces (Szyperski, 2002). El cuarto es que el ensamblaje lo **guía la arquitectura**: se decide primero cómo se divide el sistema en subsistemas y componentes, y se construye después cada parte, de modo que el trabajo se reparte y se prueba por partes.

### 1.2.3 Los componentes en el proyecto

El Proceso Unificado pide dividir el sistema en **subsistemas** con interfaces, y así se hizo (sección 2.3): nueve subsistemas que salen de los paquetes del análisis (el núcleo de la sala, la edición del diagrama, la gestión de la sala, la actividad del equipo, el seguimiento móvil, la asistencia inteligente, el asistente de ayuda, el intercambio y generación, y la carcasa del editor). Cada uno tiene sus interfaces, que son los puertos de la arquitectura hexagonal, y sus dependencias no forman ciclos. En el código, cada subsistema de diseño tiene un subsistema de implementación en carpetas y cada clase vive en un componente (un archivo) al que se puede llegar desde el diseño (sección 2.4). Los componentes de Angular y los puertos y adaptadores de Django son la misma idea aplicada en cada lado.

## 1.3 Arquitectura del software

### 1.3.1 La significancia de las decisiones arquitectónicas

La **arquitectura del software** es el conjunto de decisiones de estructura que son costosas de cambiar después: cómo se divide el sistema en partes, qué responsabilidad tiene cada una y cómo se comunican (Bass et al., 2012). Su propósito es que el software **viva más tiempo**: que se pueda entender, cambiar y hacer crecer sin rehacerlo, cuidando atributos de calidad como la modificabilidad, el rendimiento, la seguridad y la disponibilidad.

### 1.3.2 El modelo de vistas de la arquitectura

Una arquitectura es demasiado compleja para describirse con un solo diagrama, por eso se describe con **vistas**, cada una dirigida a un interesado distinto. El modelo «4+1» de Kruchten (1995) propone cuatro vistas, la **lógica** (las clases y sus relaciones), la de **procesos** (la concurrencia y la comunicación), la de **desarrollo** (cómo se organiza el código en módulos) y la **física** (en qué nodos corre el sistema), unidas por una quinta, la de **escenarios**, que son los casos de uso. El Proceso Unificado describe la arquitectura de forma parecida, con las vistas de casos de uso, lógica, de implementación y de despliegue (Jacobson et al., 2000). El modelo C4, que se explica más adelante, complementa esas vistas con cuatro niveles de detalle.

### 1.3.3 Estilos y patrones arquitectónicos

Un **estilo arquitectónico** es una forma de organizar un sistema que se repite porque resuelve bien un tipo de problema (Bass et al., 2012). Los más usados son la **arquitectura en capas**, donde cada capa solo usa a la inferior; **cliente-servidor**, que separa a quien pide de quien atiende; **modelo-vista-controlador**, que separa los datos, su presentación y la lógica que los conecta; la arquitectura **orientada a servicios**, que expone capacidades como servicios independientes; y la **hexagonal**, que pone la lógica en el centro y la rodea de puertos y adaptadores. Al elegir uno se ordenan los atributos de calidad que importan, como la modificabilidad, el rendimiento o la disponibilidad. En este proyecto se aplican desde cuatro perspectivas, que se tratan en los puntos siguientes: el backend, el frontend, las bases de datos y el despliegue.

### 1.3.4 Backend: arquitectura hexagonal

La **arquitectura hexagonal** o de puertos y adaptadores (Cockburn, 2005) pone la lógica de la aplicación en el centro y la rodea de **puertos**, interfaces que dicen qué necesita el núcleo del mundo exterior (guardar un dato, llamar a un servicio de IA), e implementa cada puerto con **adaptadores** intercambiables (una base de datos concreta, un proveedor concreto). El núcleo depende solo de las interfaces, así que cambiar una tecnología es cambiar un adaptador, y las pruebas pueden sustituirlo por uno en memoria.

**En el proyecto.** El backend de Django declara sus puertos en `collab/ports.py` y `ai_provider.py`: `ActivityStore` y `ConversationStore` (dónde se guardan la actividad y la conversación), `TurnStore` (el turno de la IA de cada sala), `RateLimiter` (los topes de uso) y `AIProvider` (quién responde). Cada uno tiene sus adaptadores: PostgreSQL y MongoDB para la actividad y la conversación, Redis y la memoria para el turno y los topes, Gemini y Ollama para la IA. Una variable de entorno elige el adaptador y `collab/stores.py` lo entrega a las vistas. Las **mismas pruebas de contrato** se ejecutan contra cada adaptador, que es lo que garantiza que son intercambiables (secciones 2.3 y 2.5).

### 1.3.5 Frontend

El cliente es una aplicación de una sola página en **Angular 20**: una jerarquía de componentes (el editor, el panel de la IA, la actividad, la vista del celular) que dependen de servicios que se les inyectan (el diagrama, la colaboración, la IA, las exportaciones). Los estados que cambian con el tiempo se modelan con **señales** reactivas, que actualizan solo lo que depende de ellas. La separación entre componentes (presentación) y servicios (lógica y comunicación) es la misma idea de la arquitectura hexagonal aplicada al navegador: por ejemplo, `DiagramApi` es una interfaz que le dice al servicio de colaboración lo que necesita del diagrama sin depender del servicio que lo dibuja. El renderizado en servidor (SSR) entrega la primera pantalla desde el servidor.

### 1.3.6 Bases de datos

No hay una base de datos mejor en general: cada familia sirve a un tipo de dato (Elmasri & Navathe, 2016; MongoDB, Inc., s. f.).

- Las **relacionales** (PostgreSQL) guardan tablas con esquema fijo, integridad referencial y transacciones. Son la elección para datos con relaciones fuertes.
- Las **de clave-valor** (Redis; y Dynamo, el sistema de Amazon que inspiró a DynamoDB, DeCandia et al., 2007) guardan un valor por clave con acceso muy rápido y escalan a lo ancho; Redis vive en memoria y es ideal para lo efímero.
- Las **documentales** (MongoDB) guardan documentos con forma flexible, anidados, que se consultan por sus campos. Encajan con datos que se leen y se escriben como una unidad, que solo se agregan y cuya forma varía.
- Las **vectoriales** guardan vectores numéricos (*embeddings*) de textos o imágenes para buscar por parecido de significado; sirven para dar contexto a una IA con grandes colecciones de documentos (Lewis et al., 2020).

**En el proyecto.** Cada dato está donde le corresponde. PostgreSQL guarda lo relacional: los participantes, los intentos de uso de la IA y el respaldo del diagrama. MongoDB guarda la actividad y la conversación con la IA: son documentos que solo se agregan, con un `data` que cambia según el tipo de evento y que se consultan por sala y orden. Redis guarda lo efímero: quién está en la sala y en qué orden, el turno de la IA y los contadores de uso. No se usa una base vectorial porque el manual del asistente de ayuda cabe entero en la petición a la IA; si creciera mucho, sus secciones se guardarían como vectores y solo se enviarían las más parecidas a la pregunta.

### 1.3.7 Despliegue: monolito y microservicios

En un **monolito** todo el sistema es una sola unidad que se construye, se despliega y se escala junta; es simple de desarrollar y de operar, pero **lo más complicado es escalarlo**: para atender más carga hay que replicarlo entero, aunque solo una parte lo necesite, y todo comparte la tecnología y el ciclo de despliegue. En una arquitectura de **microservicios** (Fowler & Lewis, 2014; Newman, 2021) cada capacidad es un servicio pequeño, desplegable y escalable por separado, con su propia base de datos; su beneficio es que se puede subir una parte sin tocar las demás y asignarle recursos según su carga, a cambio de más complejidad: red entre servicios, datos repartidos y más piezas que operar.

**En el proyecto.** El sistema es un **monolito modular con un servicio aparte**: el servidor de Django concentra la API, la colaboración y la IA, y el generador de proyectos es un servicio de Spring Boot separado porque es otro lenguaje y otro ritmo de trabajo; el frontend, las bases de datos y Redis son contenedores propios. Corren con Docker Compose en una sola máquina de AWS detrás de nginx con HTTPS. El diseño ya prepara el crecimiento: el estado que los procesos comparten (turno de la IA, topes de uso, presencia) está en Redis y no en la memoria de un proceso, de modo que se pueden poner varios procesos de Django sin cambiar el código.

### 1.3.8 El modelo C4

El **modelo C4** es una técnica para describir la arquitectura en cuatro niveles de detalle, de lo general a lo particular (Brown, s. f.): el **contexto** (el sistema como una caja negra, sus usuarios y los sistemas externos), los **contenedores** (las aplicaciones y almacenes que se ejecutan por separado), los **componentes** (las piezas internas de un contenedor) y el **código**. No reemplaza a UML: lo complementa, porque cada nivel puede detallarse con diagramas UML. En el Anexo D se presentan los niveles del proyecto.

## 1.4 Proceso Unificado de Desarrollo de Software (PUDS)

### 1.4.1 Pilares fundamentales del PUDS

El **Proceso Unificado de Desarrollo de Software** (Jacobson et al., 2000; Torossi, s. f.) es un proceso de desarrollo **dirigido por casos de uso, centrado en la arquitectura, iterativo e incremental**. No pide inventar nada: establece un flujo de trabajo que se repite en cada ciclo de vida. Los casos de uso son lo que le entrega valor a un actor y guían todo el trabajo; la arquitectura es la vista de los elementos más significativos; el trabajo se hace en iteraciones que producen incrementos del sistema.

### 1.4.2 Dinámica de las fases y milestones

Cada ciclo recorre cuatro fases (inicio, elaboración, construcción y transición) y, en cada una, **cinco flujos de trabajo**.

Cada fase termina en un **hito** (*milestone*), un punto de control donde se decide si se sigue y qué se logró:

| Fase | Hito con el que termina | Qué se logra |
|---|---|---|
| Inicio | Objetivos del ciclo de vida | Se acuerda el alcance: la visión del sistema, los casos de uso críticos y los riesgos principales |
| Elaboración | Arquitectura del ciclo de vida | Queda definida y probada la arquitectura (los casos de uso significativos para ella) y se reducen los riesgos mayores |
| Construcción | Capacidad operativa inicial | El sistema ya funciona y tiene lo necesario para que los usuarios empiecen a probarlo |
| Transición | Lanzamiento del producto | El producto se entrega, se despliega y se corrigen los defectos que aparecen en uso real |

### 1.4.3 Flujos de trabajo e iteraciones

El trabajo se hace en **iteraciones**: cada una recorre los cinco flujos de trabajo y termina en un incremento del sistema que se puede ejecutar, empezando por los casos de uso más significativos para la arquitectura. Cada flujo de trabajo produce artefactos, que se registran en el capítulo 2:

| Flujo de trabajo | Qué produce | Dónde está en este documento |
|---|---|---|
| Requisitos | Actores, casos de uso con su ficha, priorización y estructura del modelo de casos de uso | 2.1 |
| Análisis | Paquetes de análisis, clases de análisis (interfaz, control, entidad) y realizaciones de los casos de uso con diagramas de comunicación | 2.2 |
| Diseño | Arquitectura (nodos, subsistemas e interfaces), clases de diseño y realizaciones con diagramas de secuencia | 2.3 |
| Implementación | Subsistemas de implementación, componentes y plan de integración | 2.4 |
| Pruebas | Casos de prueba por cada camino de cada caso de uso, procedimientos, defectos y evaluación | 2.5 |

A ellos se suman la validación, la verificación y la auditoría (sección 2.6), que comprueban que lo documentado y lo construido son lo mismo y que cada versión se puede rastrear. Todos los diagramas siguen la notación de UML 2.5.1 y están hechos en Enterprise Architect.

## 1.5 UML 2.5 y del modelo de clases al modelo relacional y a Spring Boot

### 1.5.1 Historia y la convergencia de los Tres Amigos

A comienzos de los años noventa había decenas de métodos de modelado orientado a objetos, cada uno con su notación, y eso dificultaba que los equipos se entendieran entre sí. Tres de los métodos más usados eran el de Grady Booch, la técnica de modelado de objetos (OMT) de James Rumbaugh y la ingeniería de software orientada a objetos de Ivar Jacobson, centrada en los casos de uso. Entre 1994 y 1995 los tres se reunieron en Rational Software y fusionaron sus métodos en una sola notación, por eso se los llama los **Tres Amigos**. El resultado, UML, fue adoptado como estándar por el Object Management Group en 1997 y desde entonces evoluciona en versiones, hasta la 2.5.1 de 2017 que usa este proyecto (Booch et al., 1999; Object Management Group, 2017).

### 1.5.2 Estructura y categorías de diagramas

UML 2.5.1 define catorce diagramas en dos categorías. Los **diagramas de estructura** muestran lo que el sistema es: de clases, de objetos, de componentes, de estructura compuesta, de paquetes, de despliegue y de perfil. Los **diagramas de comportamiento** muestran lo que hace: de casos de uso, de actividad, de máquina de estados y los de interacción (de secuencia, de comunicación, de visión general de interacción y de tiempo). Este documento usa los de casos de uso, comunicación, clases, paquetes, despliegue, secuencia y componentes. El **diagrama de clases** es el que describe la estructura estática de un sistema: las clases con sus atributos y operaciones, y las relaciones entre ellas: **asociación** (con sus multiplicidades), **agregación** y **composición** (todo-parte, la segunda con dependencia de vida), **generalización** (herencia), **dependencia** y la **clase asociativa**, que guarda los datos de una asociación. La herramienta de este proyecto edita diagramas de clases con esa notación, y el modelo se intercambia en XMI (Object Management Group, 2015).

### 1.5.3 El caso de uso como elemento central de Jacobson

Ivar Jacobson introdujo el **caso de uso** en su método de ingeniería de software orientada a objetos (Jacobson, 1992): un fragmento de funcionalidad del sistema que le da un resultado de valor a un usuario. Los actores, que son los roles de quienes usan el sistema, quedan fuera de él y cada caso de uso describe una secuencia de interacciones con ellos. Su importancia es que **dirige todo el proceso**: de los casos de uso salen los requisitos, el análisis y el diseño de las clases que los realizan, la implementación y los casos de prueba, y por eso el Proceso Unificado se dice «dirigido por casos de uso» (Jacobson et al., 2000).

### 1.5.4 Del diagrama de clases al modelo relacional

Un diagrama de clases se traslada a un modelo relacional con reglas conocidas (Elmasri & Navathe, 2016): cada clase persistente es una tabla y cada atributo una columna; una asociación «uno a muchos» es una clave foránea en el lado de «muchos»; una asociación «muchos a muchos» exige una **tabla intermedia** con las dos claves foráneas (y la clase asociativa, sus datos); una composición hace que la parte dependa de su todo y se borre con él; y la generalización puede resolverse con una tabla por clase, unidas por la clave. El editor aplica la regla de la tabla intermedia al dibujar: cuando una asociación queda con «muchos» en ambos extremos, crea la entidad intermedia con sus dos relaciones 1:N.

### 1.5.5 Del modelo a Spring Boot

Trasladar el modelo a Spring Boot es ordenado: el modelo ya trae los atributos y los métodos, y lo que debe generarse es el modelo (las entidades), los servicios, los controladores y los repositorios. El generador del proyecto produce, por cada clase, la **entidad** de JPA (con `@ManyToOne` y su columna de clave foránea, `@OneToMany` con cascada para la composición, `@OneToOne` e `@Inheritance` de tipo *joined* para la herencia), el **DTO**, el **repositorio** (Spring Data), el **servicio** y el **controlador** REST, más la configuración de PostgreSQL y una colección de Postman. El proyecto generado se compila de verdad en las pruebas del generador.

## 1.6 Inteligencia artificial e IA local

### 1.6.1 Modelos de lenguaje y su integración

Un **modelo de lenguaje grande** (LLM) es una red neuronal con arquitectura *transformer* (Vaswani et al., 2017) entrenada para predecir el siguiente fragmento de texto (*token*) a partir de lo anterior; con suficiente tamaño y datos aprende a seguir instrucciones, resumir, traducir y producir texto estructurado. No guarda memoria entre peticiones: lo único que «sabe» en cada una es el **contexto** que se le envía, es decir, las instrucciones, los datos y la pregunta. Eso define cómo se trabaja con él: se diseña el *prompt*, se le entrega el contexto necesario, se valida lo que devuelve y se decide qué hacer con la respuesta.

**Proceso para integrarla.** Integrar un modelo en un sistema sigue unos pasos: elegir el proveedor y aislarlo detrás de una interfaz; diseñar las instrucciones y el contexto; limitar lo que puede hacer (que solo actúe cuando una persona lo pide y que cada cambio sea revisable); validar la salida antes de usarla (un cambio enorme o con forma inválida se rechaza); controlar el costo y los fallos (topes de uso, mensajes claros si el proveedor falla); y medir con ejemplos que el modelo nunca vio.

### 1.6.2 IA local

Un modelo **local** corre en el propio computador, sin enviar datos a un tercero y sin depender de internet. Sus características son la privacidad, la ausencia de costo por petición y el control del modelo, a cambio de necesitar memoria y cómputo y de ser, por lo general, menos capaz que los modelos grandes de la nube. Para ajustarlo a una tarea se usa **LoRA** (*Low-Rank Adaptation*), que congela el modelo y entrena solo matrices de bajo rango añadidas a sus capas, con menos del 1 % de los parámetros (Hu et al., 2021), sobre un modelo cuantizado a 4 bits en la variante **QLoRA** (Dettmers et al., 2023); el resultado es un adaptador de unas decenas de megabytes que se fusiona con el modelo base y se sirve con herramientas como Ollama. Los datos de entrenamiento se generan de forma determinista y se reservan ejemplos de prueba que el modelo nunca ve, para medir con honestidad si mejoró.

### 1.6.3 La IA en el proyecto

La IA es un **integrante de la sala**: aparece en la lista de participantes, hay una sola instancia y una sola conversación para todos, y conoce el diagrama y la actividad de cada persona. Es un solo chat y la herramienta entiende lo que se escribe: una *pregunta* (solo responde), un *pedido de cambio* (la IA propone lo que haría y pide permiso; al aplicarlo, el cambio se aplica en el navegador de quien lo pidió y queda registrado como «IA, a pedido de X»), una *revisión* (deja ideas en la actividad que cualquiera puede aplicar) o un *historial* («¿qué hizo Beto?», que se responde del registro de actividad). Cada sala usa un solo modelo, que se elige entre la nube y el modelo local. Para que sea un integrante confiable y no un riesgo, no hace nada hasta que alguien se lo pide y, antes de cambiar el diagrama, pide permiso, atiende un pedido a la vez por sala, los cambios que eliminan elementos piden confirmación, hay topes de uso por persona, por sala y para todo el servicio, y si el proveedor falla el diagrama no cambia. El proveedor está detrás del puerto `AIProvider`: **Gemini** en la nube o **Ollama con Qwen** en el computador, y para los cambios al diagrama puede usarse el modelo que el equipo reentrenó con LoRA y MLX (Anexos A y B; Qwen Team, 2025). El **asistente de ayuda** usa el mismo proveedor con el manual de la herramienta como contexto: responde solo sobre su uso.

## 1.7 Desarrollo dirigido por especificaciones

### 1.7.1 El desarrollo dirigido por especificaciones

En el **desarrollo dirigido por especificaciones** (*spec-driven development*) la especificación es la fuente de verdad: primero se escribe, de forma precisa y revisable, qué debe hacer el sistema; después se produce el código a partir de ella y se comprueba contra ella (GitHub, 2025). Es especialmente útil cuando parte del código lo escribe una inteligencia artificial, porque una especificación clara es lo que le dice al asistente qué hacer, qué reglas respetar y cuándo está terminado. Se complementa con el desarrollo guiado por pruebas, en el que la prueba que falla se escribe antes que el código (Beck, 2002).

### 1.7.2 Cómo se aplica en el proyecto

Así se integra la IA al proceso de desarrollo, no solo al producto:

- **Reglas para quien programa.** `AGENTS.md`, en la raíz del repositorio, le dice a las personas y a los asistentes de IA cómo trabajar: leer el código antes de cambiarlo, no duplicar lo que existe, no tocar los puertos, no guardar secretos, escribir pruebas de lo crítico y terminar solo cuando compila y pasa. Un asistente lo lee al empezar y lo sigue.
- **Especificaciones escritas antes del código.** `docs/REQUIREMENTS.md` lista los requisitos, `docs/GAP_MATRIX.md` dice el estado de cada uno, y los planes de trabajo de `docs/` fijan el orden de trabajo, las decisiones y lo que queda fuera.
- **El modelo manda.** El análisis y el diseño del capítulo 2 no son dibujos aparte: son modelos en código (`informe/modelo/`) que se comprueban contra el repositorio. Lo que el diseño dice de una clase, una operación o un mensaje de secuencia tiene que existir en el código, y lo que no existe obliga a corregir el modelo o el software (sección 2.6). Donde faltaba algo, primero se diseñó y después se programó.
- **Pruebas primero.** Cada cambio del ciclo 4 empezó con una prueba que fallaba, y cada defecto que encontró la verificación se reprodujo con una prueba roja antes de corregirlo (secciones 2.4 y 2.5).
- **Revisión previa a cada commit.** Una revisión automática compara cada cambio con las reglas de `AGENTS.md` antes de aceptarlo.
