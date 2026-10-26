# Plan: segundo parcial hecho con el método (PUDS), con la aplicación a partir del modelo

## 1. Contexto

El segundo parcial **junta todo** (primer parcial + lo nuevo; "no puede faltar absolutamente nada") y se publica en la plataforma el **martes 10 de noviembre, máximo 8 a.m.** (tu archivo *DOCUMENTACION DEL 2DO PARCIAL.docx*).
Lo nuevo que pidió el ingeniero: la IA como un desarrollador más de la sala (un solo modelo para todos, solo actúa a pedido, revisa, da ideas visibles, sabe lo que hizo cada persona), sesiones que se retoman, celular informativo con notificaciones, IA local (extra valorable), **base de datos NoSQL**, y **un asistente de IA que enseñe a usar la herramienta**. Su criterio de valor: reducir el tiempo de desarrollo y mejorar la productividad.

Hasta hoy el trabajo fue al revés del método: la aplicación existía y los diagramas salieron del informe, sin comprobar que coincidan con el código. Su paso 3 lo dice: "todo lo que está registrado en el documento debe estar en el software, o al revés" y "el diagrama de secuencia debe estar relacionado con el software". Este plan lo resuelve: **el modelo manda; donde falta algo se diseña primero y se programa después; donde ya existe se demuestra con trazabilidad.**

## 2. Fuentes que se siguen

| Sigla | Fuente | Para qué |
|---|---|---|
| **PUDS** | `Material/puds (1).pdf` (síntesis de A.U.S. Gustavo Torossi del *Proceso Unificado de Desarrollo de Software*, Jacobson, Booch y Rumbaugh) | Reglas de cada artefacto y flujo |
| **APUNTES** | `Material/apuntesMartinezSW1.pdf` | Qué espera el ingeniero ("línea de código que se escribe, línea que se queda"; el diagrama de dominio no es diseñar) |
| **CLASES** | `Downloads/parcial 2.pdf`, `parcial 2.1.pdf` (transcripciones) | Qué pide para la aplicación |
| **DOC2P** | `Downloads/DOCUMENTACION DEL 2DO PARCIAL.docx` | Organización del documento, temas teóricos, validación/verificación/auditoría, portadas con QR |
| **REF1** | `Material/FRX/Segundo Parcial Ingenieria de Software 1.pdf`, `Doc Primer Parcial.pdf`, `todos los diagramas.pdf` | Formato aceptado |
| **REF2** | Google Doc de Organiflow (`1OmggGoZ9UToByE5mbSBZGqcg-C91XhVOiVh6tuyM2h4`) | Estructura completa de ejemplo: casos de uso con ficha, comunicación, "diseño de casos de uso" con fragmentos `alt`, componentes, subsistemas, reporte de prueba |
| **UML** | UML 2.5.1 (OMG), Cockburn, Larman | Notación y criterios (de memoria; irán a la bibliografía) |

## 3. Decisiones (las tomadas contigo y las que propongo)

**Tomadas por ti:** IA fuera de los actores (solo el servicio de IA es actor secundario); diagramas hechos en EA como hasta ahora (la regla "nada de IA" se refería a pedirle la imagen a una IA); **agregar MongoDB**; entrega el 10-nov 8 a.m.

**D1. Informe acumulativo** con los casos de uso en ciclos 1 a 3 (heredados) y un ciclo 4 nuevo, como REF1. Fundamento: CLASES y DOC2P.

**D2. Actores:** A1 Diseñador (host, especialización de A2), A2 Colaborador y A3 Servicio de IA (sistema externo: Gemini u Ollama), actor secundario. Fundamento: PUDS p.31 ("actores que representan sistemas externos"; "una clase de interfaz central para cada actor que sea un sistema externo"). La IA integrante de la sala **no** es actor: nunca inicia nada. El Administrador no es actor: el proveedor y el modelo local se eligen con variables del servidor.

**D3. Catorce casos de uso**, uno por objetivo con valor observable (PUDS: "fragmento de funcionalidad que proporciona un resultado de valor a un usuario"; el crear-leer-modificar-borrar de un objeto es **un** caso, como en REF2). Nombrados por el objetivo, no por el canal ni la tecnología:

| # | Caso de uso | Actores | Ciclo | Origen |
|---|---|---|---|---|
| 1 | Ingresar a una sala de trabajo (crear o entrar con código y nombre) | A1, A2 | 1 | Parcial 1, +nombre |
| 2 | Modelar el diagrama de clases UML | A1, A2 | 1 | Parcial 1 |
| 5 | Retomar el trabajo en otra sesión | A1, A2 | 1 | Parcial 1, ampliado |
| 3 | Colaborar en la edición del diagrama | A1, A2 | 2 | Parcial 1 |
| 4 | Expulsar a un participante | A1 | 2 | Parcial 1 |
| 7 | Modificar el modelo con la IA | A1, A2, A3 | 2 | Parcial 1, ampliado |
| 8 | Crear el modelo desde una imagen | A1, A2, A3 | 2 | Parcial 1 |
| 10 | Intercambiar el diagrama con otras herramientas (XMI e imagen) | A1, A2 | 3 | Parcial 1 |
| 11 | Generar el backend del sistema (Spring Boot, PostgreSQL, SQL, Postman) | A1 | 3 | Parcial 1 |
| 12 | Generar la aplicación móvil | A1 | 3 | Parcial 1 |
| 6 | Consultar la actividad del equipo | A1, A2 | 4 | **Nuevo** |
| 9 | Consultar a la IA (preguntar, revisión con ideas, validación) | A1, A2, A3 | 4 | Parcial 1 (validar), ampliado |
| 13 | Mantenerse informado desde el celular | A1, A2 | 4 | **Nuevo** |
| 14 | Aprender a usar la herramienta con el asistente de ayuda | A1, A2, A3 | 4 | **Nuevo** (DOC2P) |

Qué se juntó: texto+voz (otro canal, mismo objetivo); preguntar+revisar+validar con IA; guardar+recuperar (guardar es automático); SQL con backend; exportar+importar. 13 y 14 son casos propios porque el ingeniero pidió explícitamente ese uso del celular (informativo, con notificaciones) y ese mecanismo de aprendizaje.
`include`/`extend` solo donde ≥2 casos comparten una secuencia idéntica; "estar en una sala" es **precondición**, no `include`. La guía de RUP recomienda **evitar** `include` y `extend` al principio y usarlos después solo para factorizar comportamiento común. Cada caso lo inicia un solo actor: A2, y A1 lo hereda por la generalización (guía RUP); A3 es siempre secundario. Los nombres son una frase verbal activa que expresa el objetivo, a nivel de objetivo de usuario (Cockburn).

**D4. Conversación con la IA compartida por toda la sala** (CLASES: "un solo modelo, una sola instancia... no hay una conversación privada"). El chat privado fue decisión de diseño de Pedro del 14-oct, no del docente.

**D5. Notificaciones en la vista del celular**, alcance mínimo (CLASES).

**D6. MongoDB para la conversación con la IA y el registro de actividad.** Fundamento: son documentos que solo se agregan, con un `data` que cambia según el tipo, que se consultan por sala y tiempo y no necesitan integridad relacional: encaje clásico de una base documental. PostgreSQL conserva lo relacional (participantes, topes de uso de la IA, respaldo del diagrama); Redis conserva el estado efímero. Se hace con **puertos y adaptadores** (arquitectura hexagonal, que el ingeniero nombró para el backend): ya existen `AIProvider` (puerto) con `GeminiProvider` y `OllamaProvider` (adaptadores) y `ORMActivityStore` inyectable; se agregan los puertos `ConversationStore` y `ActivityStore` con adaptadores PostgreSQL y MongoDB, elegidos con una variable.

**D7. Asistente de ayuda.** Modo "Ayuda" del servicio de IA con conocimiento del proyecto (el manual y la lista de funciones como contexto): responde "¿cómo hago X?". Conversación personal (no compartida); disponible también antes de entrar a una sala. Es el "mecanismo para que el usuario aprenda a usar" (DOC2P punto 3); el manual del informe lo describe.

**D8. Valores de prioridad y riesgo** del material (PUDS): prioridad crítico/importante/secundario; riesgo crítico/significativo/ordinario; estado propuesto/aprobado/incluido/validado. Se mantienen las columnas de REF1.

## 4. Estructura del documento (DOC2P + REF1)

0 Justificación del stack · **1 Fundamentación teórica** (los seis temas de DOC2P: 1 CASE; 2 arquitectura con sus cuatro perspectivas —backend hexagonal, frontend, base de datos NoSQL/vectorial, despliegue monolito frente a microservicios, y por qué el monolito es difícil de escalar—; 3 desarrollo basado en componentes; 4 IA y IA local —características, cómo funciona, proceso, integración—; 5 desarrollo dirigido por especificaciones —cómo se integra la IA al proyecto y cómo se le instruye: nuestro `AGENTS.md`, los planes y las especificaciones—; 6 UML 2.5+ con el paso de clases a relacional a Spring Boot: modelo, servicios, controladores, repositorios) + PUDS · **2 Registro del proceso** (2.1 requisitos, 2.2 análisis, 2.3 diseño, 2.4 implementación, 2.5 pruebas, **2.6 validación, verificación y auditoría**: la matriz de trazabilidad, el control de calidad y las versiones en GitHub) · 3 Manual (con el asistente de ayuda) · 4 Conclusión · 5 Bibliografía en APA · Anexos A–C · **dos carátulas con códigos QR** del repositorio de GitHub y del sitio desplegado.

## 5. Reglas por artefacto (lo que se verifica en cada uno)

| Artefacto | Reglas (fuente) | Cómo se verifica |
|---|---|---|
| Actores y glosario | Roles, no personas; sistemas externos incluidos (PUDS p.31); glosario (PUDS p.30) | Lista contra los 14 casos |
| Diagrama de casos de uso | Actores fuera de la frontera; asociación actor–caso; generalización A1→A2; `include`/`extend` solo si proceden (PUDS p.32); líneas horizontales y verticales sin cruzar elementos | Lista por diagrama + mirar cada imagen |
| Priorización | Estado, prioridad y riesgo; el resultado es la **vista de la arquitectura del modelo de casos de uso** (PUDS p.32) | Criterio por caso |
| Detalle de caso de uso | Precondición, cómo empieza y termina, **camino básico numerado**, **alternos y excepciones**, postcondición, caminos no permitidos, **requisitos especiales** (PUDS p.32); formato de ficha de REF1/REF2; diagrama de actividad en los complejos (7 y 9) | Cada camino se vuelve un caso de prueba |
| Prototipo de interfaz | Capturas reales de la aplicación por caso (PUDS p.32) | Una por caso con pantalla |
| Requisitos adicionales | Solo los no asociables a un caso; los específicos van dentro del caso (PUDS p.27–28) | Cada RA con su verificación |
| Paquetes de análisis | Agrupar por proceso, actor o relación entre casos; acoplamiento bajo, cohesión alta; clase compartida en su paquete; paquete de servicio para lo opcional (la IA local) (PUDS p.35–38) | Dependencias sin ciclos |
| Realización de caso de uso – análisis | Una por caso: flujo textual + **clases participantes** + **diagrama de comunicación**; empieza con un mensaje del actor; cada clase participante tiene instancia; **los mensajes no son operaciones** (PUDS p.39); interfaz por actor humano y por actor externo, un control por caso, entidades; robustez (actor↔interfaz↔control↔entidad) | Revisión mensaje por mensaje |
| Clases de análisis | **Responsabilidades, atributos de alto nivel, relaciones conceptuales con multiplicidad**, estereotipo (PUDS p.34; RUP "Artifact: Analysis Class"). Las responsabilidades pueden nombrarse como operaciones **sin firma ni tipos** (Univ. de Cantabria). *Las mías hoy tienen operaciones pero no atributos, y los mensajes llevan parámetros: se corrigen.* Una clase de interfaz por cada pareja actor–caso de uso (guía RUP) | Cada responsabilidad sale de una colaboración |
| Análisis de paquete | Independencia, contenido, dependencias (PUDS p.39) | Un diagrama |
| Diseño de la arquitectura | Nodos y red; subsistemas con interfaces (círculo y `<<use>>`); clases activas; mecanismos genéricos (persistencia, tiempo real, proveedor de IA intercambiable, topes de costo); C4 en sus cuatro niveles (PUDS p.43–44; REF1) | Cada nodo y subsistema existe en el repositorio |
| Realización de caso de uso – diseño | **Clases de diseño con los nombres reales del código**; secuencia con operaciones reales y **fragmentos `alt`/`opt` para los caminos alternos** (REF2); `<<trace>>` a la realización de análisis; flujo de sucesos-diseño (PUDS p.41) | Cada mensaje se busca en el código |
| Clases de diseño | Lenguaje de implementación (Python/TypeScript), visibilidad, atributos tipados, operaciones, herencia, asociaciones como atributos, estados para clases con ciclo de vida (la reserva de una idea: libre → reservada → aplicada) (PUDS p.41, 44–45) | **Generadas del código** (análisis `ast` de Python y de TypeScript), no dibujadas |
| Diseño de datos | Clases persistentes → tablas (PostgreSQL) y colecciones (MongoDB); volumen; script (APUNTES) | Contra las migraciones y los esquemas |
| Modelo de implementación | Componentes `<<file>>`, `<<executable>>`, `<<table>>` con traza a las clases; subsistema de implementación 1:1 con el de diseño; ejecutables asignados a nodos; plan de integración por construcción (PUDS p.46–49) | Cada componente es un archivo real |
| Prueba | Plan; **casos de prueba (entradas, condiciones, resultado esperado) por cada camino de cada caso de uso**; procedimientos; componentes de prueba automáticos; defectos; evaluación con compleción y fiabilidad (PUDS p.15–16, 51–54; "reporte de prueba" de REF2) | Matriz caso de uso → camino → prueba |
| Validación, verificación, auditoría | Todo lo que está en el documento está en el software y al revés; control de calidad; versiones (etiquetas y commits) (DOC2P pasos 2 a 4) | Matriz de trazabilidad generada del repositorio sin celdas vacías |

Diagramas en Enterprise Architect (marca de agua de la prueba aceptada). La prueba de CrossOver vence cerca del **6-nov**: los diagramas se congelan el **4-nov** (los cambios de código posteriores solo tocan lo ya diagramado).

## 6. Cambios a la aplicación (modelo antes que código)

- **C1 Chat compartido.** `uml_api/chat_views.py` filtra el historial por participante (`_answer` ~l.134, `chat_history` ~l.254) y `ia-chat-panel.ts` muestra solo lo propio. Pasa a conversación de la sala con autor por mensaje; el contexto de la IA es la conversación de todos; una solicitud a la vez por sala; topes de costo se mantienen. Se actualizan RF-26 y RNF-04, CP-22 y CP-34 y `docs/PLAN_PUDS_IA_PARTICIPANTE.md`.
- **C2 Notificaciones** en `app/follow-view` (API de notificaciones del navegador, con la página abierta). Hoy no hay código de notificaciones.
- **C3 MongoDB.** Puertos `ConversationStore` y `ActivityStore` en `collab/` (reutilizando el patrón de `ORMActivityStore` en `collab/activity.py`), adaptador MongoDB con `pymongo`, servicio `mongo` en los `docker-compose` con la memoria acotada (`--wiredTigerCacheSizeGB 0.25`), credenciales por variables de entorno (solo nombres en el repositorio), orden de los eventos y topes de tamaño y tasa conservados, orden de prueba: adaptador en memoria para pruebas de unidad y una prueba de integración con Mongo real en Docker; comando de una sola vez para pasar el historial existente. Antes: medir la memoria libre de la máquina de AWS (2 GB) con tu autorización; si no alcanza, alternativa: MongoDB Atlas gratuito.
- **C4 Asistente de ayuda** (modo "Ayuda", D7), con el manual como contexto y un tope de uso.
- **C5 Alinear lo existente.** Sin cambiar comportamiento: tabla de realización de cada clase de análisis (p. ej. "Control de IA" = `chat_views.ia_chat` + `ia-chat.service` + `ia-actions.service` + `change_guard`; la entidad "Diagrama" vive en el navegador (JointJS) y se respalda en `BackupUML`).

Orden de cada cambio: realización de diseño y secuencia en EA → pruebas que fallan → código → pruebas en verde.

## 7. Fases, entregables y verificación

| Fase | Contenido | Entregable | Verificación |
|---|---|---|---|
| F0 | Aprobar este plan | Plan aprobado | Tu aprobación |
| F1 Requisitos | Actores, 14 casos, priorización, 14 fichas, estructura, glosario, prototipo (capturas), requisitos adicionales | Modelo en EA + tablas | Lista por artefacto |
| F2 Análisis | Paquetes, 14 realizaciones, clases con responsabilidades y atributos, análisis de paquete | Diagramas EA | Reglas de la sección 5 |
| F3 Diseño | Arquitectura (C4, despliegue, capas, subsistemas con interfaces), clases de diseño generadas del código, secuencias con `alt` por caso, datos (PostgreSQL + MongoDB), diseño de C1–C4 | Diagramas EA + tabla de realización | Cada elemento se encuentra en el repositorio |
| F4 Implementación | C1–C4 desde el diseño; componentes y subsistemas de implementación; plan de integración; matriz de trazabilidad | Código + pruebas + diagramas | Pruebas de Django, Angular y Spring en verde; diseño = código |
| F5 Pruebas | Casos por camino de cada caso de uso, procedimientos, ejecución completa, defectos, evaluación | Sección 2.5 | Resultados reales y prueba con 3 navegadores y un celular |
| F6 Documento | Fundamentación (los 6 temas), stack, 4 ciclos, 2.6 validación y auditoría, manual con el asistente de ayuda, conclusión, bibliografía APA, anexos, 2 carátulas con QR; PDF | `Informe.pdf`, `.docx`, `modelo.qea` | Revisión página por página |
| F7 Cierre | Despliegue en AWS (**solo con tu aprobación explícita**), prueba de humo, `GAP_MATRIX` y memoria del proyecto al día | Sitio actualizado | `scripts/smoke-test.sh` |

Se reutiliza: `informe/ea/` (constructor, layout, especificaciones), `informe/generar_informe.py`, `informe/exportar_pdf.sh`, `informe/parte2_datos.py`, `docs/puds/` (se alinea a esta numeración), `ml/` y los anexos A y B.

## 8. Calendario (entrega: martes 10-nov, 8 a.m.)

| Día | Trabajo |
|---|---|
| Dom 25 – Lun 26 | F0, F1 y F2 |
| Mar 27 | F3 (diseño de C1–C4) |
| Mié 28 – Sáb 31 | F4 (C1 a C4, trazabilidad) |
| Dom 1 | F5 |
| Lun 2 – Mié 4 | Diagramas finales y congelados el 4-nov; F6 |
| Jue 5 – Vie 6 | Documento, QR, PDF; revisión completa |
| Sáb 7 | F7: despliegue en AWS y prueba de humo (con tu aprobación) |
| Dom 8 – Lun 9 | Ensayo de la demo con celular real, impresión de las dos carátulas, colchón |
| Mar 10, 8 a.m. | Publicar en la plataforma (idealmente la noche del 9) |

## 9. Riesgos

- **Límite de uso:** ya me ha cortado antes; cada fase termina en commits pequeños.
- **MongoDB en una máquina de 2 GB:** mitigación por memoria acotada y, si no alcanza, Atlas gratuito.
- **Cambiar el chat y la base de datos de lo ya probado:** pruebas primero y adaptadores intercambiables por variable, con PostgreSQL como respaldo.
- **Prueba de CrossOver (6-nov):** por eso el congelamiento del 4-nov.
- **Reglas del libro:** vienen del material de la cátedra y de mi memoria de los libros; si tienes el PDF del *Proceso Unificado*, lo uso para cotejar.
- **Notas de DOC2P:** parecen apuntes de un compañero; los puntos NoSQL y "móvil para detectar…" (cortado) conviene confirmarlos con el docente.
- Fuera de alcance: más funciones nuevas (el ingeniero pidió no ensanchar la herramienta).

## 9 bis. Cotejo con fuentes públicas (consultadas en internet)

El libro de Jacobson, Booch y Rumbaugh no está disponible gratis y no descargué copias no autorizadas. Cotejé las reglas con documentación pública del proceso que describe y con material universitario: confirman lo de arriba y matizan lo marcado.

- RUP, lista de revisión de clases de análisis: toda interacción actor–sistema tiene una clase de interfaz; cada clase representa un conjunto cohesivo de responsabilidades. https://files.defcon.no/RUP/process/activity/chklists/ck_aclss.htm
- RUP, artefacto "Analysis Class": propiedades = nombre, descripción, responsabilidades y atributos (a alto nivel); estereotipos interfaz, control y entidad; una clase de interfaz por pareja actor–caso. https://files.defcon.no/RUP/process/artifact/ar_aclss.htm y https://home.iscte-iul.pt/~hro/RUPSmallProjects/core.base_rup/guidances/guidelines/analysis_class_7E97273E.html
- RUP, guías de modelado de casos de uso: evitar `include`/`extend` al inicio; la generalización de actores sirve para distinguir roles; cada caso lo inicia un solo actor. https://files.defcon.no/RUP/manuals/ucmgl/ucmgl.htm y https://swi.cs.vsb.cz/RUPSmall/core.base_rup/tasks/structure_use_case_model_93D8F44.html
- Universidad de Cantabria (Ingeniería del Software 1): en análisis el comportamiento se expresa con responsabilidades, que pueden plantearse como operaciones, y se crea un diagrama de interacción por flujo diferenciado. https://www.ctr.unican.es/asignaturas/is1/is1-p05-ficha.pdf
- Cockburn, *Writing Effective Use Cases* (borrador y plantilla): el nombre es el objetivo como frase verbal activa; el nivel útil es el de objetivo de usuario; los sistemas necesarios para terminar el caso son actores secundarios. https://courses.cs.duke.edu/spring23/compsci308/readings/cockburn_use_cases.pdf
- UTN-FRC (modelo de casos de uso frente a modelo de análisis; realización de caso de uso = análisis de un caso). https://www.institucional.frc.utn.edu.ar/SISTEMAS/NOTICIAS/HP/PROYECTOS/044_servtecanalisis.pdf

Si tienes el libro en PDF de forma legítima, lo cotejo página por página antes de cerrar F2.

## 9 ter. Cotejo con el libro (PDF que aportó Pedro, leído por OCR el 2026-10-25)

Libro: Jacobson, Booch y Rumbaugh, *El Proceso Unificado de Desarrollo de Software* (edición en español). Secciones citadas, no páginas, porque el OCR no conserva la paginación impresa.

| Regla | Dónde está en el libro | Estado en el plan |
|---|---|---|
| Los sistemas externos son actores; los actores que se solapan se generalizan | 7.2.2, 7.4.1.1 | Confirmado (A3; A1 especializa A2) |
| Hay que identificar actores de mantenimiento y operación **cuando existen** | 7.4.1.1, 7.4.1.2 | Pendiente de decidir: no hay función de operación dentro de la herramienta; se justifica en «Quién no es un actor» (RA-01) |
| Nombre de caso de uso con verbo que refleja el objetivo; resultado de valor observable para un actor concreto; evita casos demasiado pequeños («Planificación de Pagos no añadiría valor») | 7.4.1.2 | Confirmado (un CRUD = un caso) |
| El actor necesita casos para su trabajo de crear, cambiar, rastrear, eliminar o estudiar objetos | 7.4.1.2 | Confirmado |
| Priorizar produce la vista de la arquitectura del modelo de casos de uso | 7.4.2, 7.2.4 | Confirmado |
| Detalle: camino básico, caminos alternativos, precondición, postcondiciones, caminos no permitidos, requisitos especiales | 7.4.3 | Confirmado |
| Extensión: lleva condición y punto de extensión; `include` con cautela; no descomponer funcionalmente los casos de uso | 7.4.5.2, 7.4.5.3 | **Corregido**: se agregó condición y punto de extensión (`CONDICION_EXTENSION`) |
| Clase de análisis: responsabilidades (no operaciones con firma), atributos de alto nivel, relaciones conceptuales, estereotipo interfaz/control/entidad | 8.4.2 | Confirmado; es lo que F2 debe cumplir |
| Una clase de interfaz central por cada actor humano y por cada actor que es sistema externo | 8.6.2 | Confirmado |
| Realización de caso de uso – análisis: flujo de sucesos, diagramas de clases participantes, diagramas de interacción (colaboración), requisitos especiales; traza al caso de uso | 8.4.3 | Confirmado |
| Diagramas de colaboración con mensajes numerados en el análisis; secuencia solo cuando importa el orden | 8.4.3.2 | Confirmado |

## 9 quater. Estado (2026-10-25)

| Fase | Estado | Dónde |
|---|---|---|
| F0 Plan | Aprobado | este documento |
| F1 Requisitos | Hecha: 14 casos de uso, 3 actores, fichas, priorización, estructura, glosario, RA; 20 diagramas en EA | `informe/modelo/requisitos.py`, `informe/seccion_requisitos.py`, `informe/ea/casos_de_uso.py` |
| F2 Análisis | Hecha: 8 paquetes (2 de servicio), 41 clases, 18 colaboraciones, 44 diagramas en EA, sección 2.2 del informe; `validar()` comprueba las reglas del libro | `informe/modelo/analisis.py`, `informe/seccion_analisis.py`, `informe/ea/analisis.py` |
| F3 Diseño | Hecha: 9 subsistemas, 68 clases de diseño comprobadas contra el código, 8 interfaces, 35 secuencias, diseño de C1 a C4, 70 diagramas en EA y la sección 2.3 | `informe/modelo/codigo.py`, `informe/modelo/diseno.py`, `informe/modelo/realizaciones.py`, `informe/seccion_diseno.py`, `informe/ea/diseno.py` |
| F4 Implementación | Pendiente: programar C1 a C4 desde el diseño (las pruebas primero) | |
| F5–F7 | Pendientes | |

Herramientas que dejó F2 (para F3): los diagramas con mensajes en EA ubican sus etiquetas midiendo en dos pasadas (`informe/ea/etiquetas.py`); las posiciones se guardan en `informe/build/layout_cache.json`; `generar_diagramas.py --solo analisis[:COL-01,…]` genera solo el análisis.

## 10. Verificación de extremo a extremo

1. Cada diagrama: lista de la sección 5 y mirar la imagen completa.
2. `back_generador_bd/.venv/bin/python back_generador_bd/manage.py test` (sin base de datos), pruebas con base de datos en el contenedor de Django, `ng test`, `./mvnw test` en `back_generator_uml`, y la prueba de integración con MongoDB.
3. Matriz de trazabilidad sin celdas vacías (caso de uso → análisis → diseño → componente → prueba).
4. PDF: las imágenes del `.docx` coinciden con `informe/build/ea/` (el export ya cierra copias viejas de Word).
5. Prueba física: tres navegadores y un celular real (chat compartido, notificaciones, ayuda).
