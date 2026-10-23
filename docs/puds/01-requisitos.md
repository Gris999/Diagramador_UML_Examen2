# Disciplina de Requisitos

Artefactos: **modelo de casos de uso**, **casos de uso detallados**, **requisitos adicionales** y **glosario**. Los requisitos numerados (RF-xx / RNF-xx) viven en [`../REQUIREMENTS.md`](../REQUIREMENTS.md); el plan agrega RF-23…RF-33 y RNF-04…RNF-07 (sección 4 de [`../PLAN_PUDS_IA_PARTICIPANTE.md`](../PLAN_PUDS_IA_PARTICIPANTE.md)).

## 1. Actores

Son los mismos del primer parcial; este parcial no agrega actores.

| Código | Actor | Descripción |
|---|---|---|
| A1 | **Diseñador** | Persona que creó la sala o entró primero a la sala viva (el **host**). Hace todo lo que hace un Colaborador y además puede expulsar a otros (RF-12…RF-15). Es un **rol** temporal, no una cuenta: especialización de A2. |
| A2 | **Colaborador** | Persona que entra a una sala con su código y edita el diagrama. Sin cuentas: se identifica con un nombre y un identificador anónimo guardado en el navegador (RF-23). |

**Quién no es un actor** (criterio del Proceso Unificado: un actor es un rol de quien interactúa con el sistema desde fuera):

- **La IA** (RF-24): aunque se muestra como un integrante más de la sala, es una función del sistema y solo actúa cuando A1 o A2 se lo piden.
- **El servicio de IA** (Gemini u Ollama): es una pieza de la arquitectura (diagrama de contexto C4), no un rol.
- **El administrador** que elige el proveedor de IA: es una variable de configuración del servidor, no una función que el sistema ofrezca (requisito adicional RA-01).
- **El observador del celular** (RF-32): son las mismas personas A1 y A2 usando la vista de solo lectura.
- **Enterprise Architect**: herramienta externa del primer parcial (CU-10).

## 2. Modelo de casos de uso

La numeración continúa la del primer parcial: **CU-01 a CU-13** (ciclos 1 a 3, ya entregados) y **CU-14 a CU-19** (ciclos 4 a 6, este parcial). Cada caso de uso es un objetivo completo de un actor con un resultado observable: no se parten en pasos ni en operaciones de un CRUD.

```mermaid
flowchart LR
  C([Colaborador A2]) --- CU14(CU-14 Consultar la actividad del equipo)
  C --- CU15(CU-15 Consultar a la IA)
  C --- CU16(CU-16 Pedirle a la IA un cambio)
  C --- CU17(CU-17 Revisar el diagrama con la IA)
  C --- CU18(CU-18 Retomar una sesión anterior)
  C --- CU19(CU-19 Seguir la sala desde el celular)
  D([Diseñador A1]) -. es un .-> C
  CU14 -. include .-> CU01(CU-01 Gestionar salas)
  CU15 -. include .-> CU01
  CU16 -. include .-> CU06(CU-06 Modelo desde lenguaje natural)
  CU17 -. include .-> CU09(CU-09 Analizar y validar con IA)
  CU18 -. include .-> CU01
  CU18 -. include .-> CU05(CU-05 Guardar y recuperar estado)
  CU19 -. include .-> CU03(CU-03 Colaborar en tiempo real)
```

### Catálogo

| ID | Caso de uso | Requisitos | Parcial | Estado |
|---|---|---|---|---|
| CU-01 | Gestionar salas de trabajo (crear una o entrar con su código) | RF-06 | 1 | ✅ |
| CU-02 | Modelar el diagrama de clases UML | RF-01, RF-02 | 1 | ✅ |
| CU-03 | Colaborar en tiempo real sobre el diagrama | RF-06, RF-08, RF-10, RF-11 | 1 | ✅ |
| CU-04 | Gestionar participantes: expulsar a uno (solo el host) | RF-07, RF-09, RF-14 | 1 | ✅ |
| CU-05 | Guardar y recuperar el estado del diagrama | RF-10, RF-11 | 1 | ✅ |
| CU-06 | Crear o modificar el modelo mediante lenguaje natural | RF-03 | 1 | ✅ |
| CU-07 | Crear el modelo a partir de una imagen | RF-04 | 1 | ✅ |
| CU-08 | Editar el modelo mediante comandos de voz | RF-05 | 1 | ✅ |
| CU-09 | Analizar y validar el modelo UML con IA | — | 1 | ✅ |
| CU-10 | Exportar e importar el diagrama en XMI (Enterprise Architect) | RF-18 | 1 | ✅ |
| CU-11 | Generar el script SQL (y exportar a imagen) | RF-01 | 1 | ✅ |
| CU-12 | Generar backend Spring Boot + PostgreSQL y colección Postman | RF-19, RF-20 | 1 | ✅ |
| CU-13 | Generar proyecto Flutter con persistencia SQLite offline | RF-21, RNF-01, RF-22 (parcial) | 1 | ✅ |
| CU-14 | Consultar la actividad del equipo (identificarse con un nombre y ver quién hizo qué) | RF-23, RF-25 | 2 | ✅ I1 |
| CU-15 | Consultar a la IA (incluye «¿qué hizo X?») | RF-26, RF-27 | 2 | ✅ I2 |
| CU-16 | Pedirle a la IA un cambio en el diagrama | RF-28, RF-29 | 2 | ✅ I3 |
| CU-17 | Revisar el diagrama con la IA y aplicar sus ideas | RF-28, RF-30 | 2 | ✅ I3 |
| CU-18 | Retomar una sesión anterior | RF-31 | 2 | ✅ I4 |
| CU-19 | Seguir la sala desde el celular | RF-32 | 2 | ✅ I5 |

### Requisitos adicionales

No los inicia un actor, por eso no son casos de uso: la IA local reentrenada (**RA-01**, extra valorable que pidió el docente, RF-22 y RF-33), la privacidad de la conversación (RA-02), la resiliencia ante fallos de la IA (RA-03), el control del costo (RA-04), la persistencia continua (RA-05) y el despliegue seguro (RA-06). Se detallan en la sección 2.1.6 del informe.

### Casos de uso críticos para la arquitectura

Siguiendo el material de la cátedra (el arquitecto parte de un conjunto reducido de casos de uso fundamentales), se priorizan:

1. **CU-03 Colaborar en tiempo real:** fija el canal de tiempo real, los roles y la recuperación de estado.
2. **CU-02 Editar el diagrama:** fija el modelo del grafo (JointJS) del que cuelgan exportaciones y generadores.
3. **CU-16 Pedir cambio a la IA:** atraviesa identidad, actividad, IA y colaboración; se valida primero con el prototipo vertical de I1.
4. **CU-10 XMI:** fija el formato de intercambio con una herramienta externa.

## 3. Casos de uso detallados

### CU-03 — Colaborar en una sala *(✅)*

- **Actor:** Colaborador (A2; el Diseñador A1 hereda todo).
- **Precondición:** conoce el código de la sala.
- **Flujo básico:**
  1. Abre la sala. El navegador abre un WebSocket a `/ws/canvas/<sala>/`.
  2. El servidor lo registra, le asigna rol (host si es el primero, participante si no) y avisa la presencia a todos.
  3. El cliente pide el estado completo; otro participante lo envía (`full_state`) y el diagrama aparece.
  4. Cada cambio que hace el participante (agregar clase, editar texto, mover, enlazar, borrar) se envía como operación y los demás la aplican.
  5. Cada cierto tiempo el cliente guarda un respaldo del diagrama en el servidor.
- **Flujos alternos:**
  - *Primer participante:* no hay a quién pedir el estado; se carga el respaldo del servidor.
  - *Desconexión del host:* el participante más antiguo pasa a host (RF-15).
  - *Reconexión:* es una conexión nueva; recupera el diagrama pero **no** el rol anterior (RF-16, RF-17).
- **Postcondición:** todos los participantes ven el mismo diagrama.

### CU-04 — Expulsar a un participante *(✅)*

- **Actor:** Diseñador (A1, el host).
- **Flujo básico:** el host pulsa "expulsar" junto a un participante; el servidor verifica que quien lo pide es el host actual, cierra la conexión del expulsado y actualiza la presencia.
- **Alterno:** si lo pide un no-host, el servidor responde `remove_rejected` y no pasa nada.

### CU-02 — Editar el diagrama manualmente *(✅)*

- **Flujo básico:** el participante agrega clases, edita nombre/atributos/métodos, las mueve y las une con relaciones (asociación, agregación, composición, generalización, dependencia) y multiplicidades.
- **Regla de entidad intermedia:** si una **asociación** queda con `*` en ambos extremos, el editor la reemplaza por una clase intermedia y dos relaciones 1:N. Agregación, composición, dependencia y generalización no se transforman. Si el usuario edita una de las patas generadas y deja de ser "muchos", se restaura la asociación original (no desaparece ninguna relación).
- **Clase asociativa:** una clase puede unirse a una asociación M:N con un conector punteado; los generadores la resuelven a dos relaciones 1:N.

### CU-10 — Exportar e importar XMI *(✅)*

- **Flujo básico (exportar):** el cliente envía el diagrama a `POST /api/xmi/export/`; el servidor genera XMI 2.1 y el navegador lo descarga. Enterprise Architect lo abre.
- **Flujo básico (importar):** el participante sube un `.xmi`; `POST /api/xmi/import/` lo valida (rechaza `DOCTYPE`/entidades externas) y devuelve el diagrama, con posición y tamaño si el archivo trae los metadatos del editor.
- **Alterno:** archivo mal formado o con construcciones inseguras → error claro, el diagrama actual no cambia.

### CU-12 — Generar backend *(✅)*

- **Flujo básico:** el cliente envía el diagrama al generador (`POST /generate`); este devuelve un `.zip` con proyecto Spring Boot (Java 21) + PostgreSQL y una colección Postman.
- **Postcondición:** el proyecto descomprimido compila con el Maven Wrapper incluido.

### CU-16 — Pedirle a la IA un cambio en el diagrama *(✅ I3)*

- **Actor:** Colaborador (A2; el Diseñador A1 hereda todo). La IA no es un actor: es la función del sistema que atiende el pedido.
- **Incluye:** CU-06 (interpretar la instrucción en lenguaje natural).
- **Precondición:** el actor tiene nombre y está en la sala (CU-14).
- **Flujo básico:**
  1. En su chat, el actor elige el modo **Pedir cambio** y escribe el pedido.
  2. `POST /api/rooms/<sala>/ia/chat/` con `mode=change`: el servidor identifica al actor por su token, limita la tasa de pedidos y llama al servicio de IA.
  3. El servicio devuelve los cambios en el formato que ya entiende el editor (crear, editar o eliminar).
  4. El navegador del actor los aplica con la misma ruta de edición manual; cada operación viaja marcada `via_ia` y se propaga a todos.
  5. El servidor registra cada operación en la actividad como "IA … (a pedido de X)".
- **Alternos:** el servicio falla → mensaje claro y el diagrama no cambia (RNF-05). Si los cambios eliminan algo, se pide confirmación. Modo **Preguntar** (CU-15) → la IA responde sin tocar el diagrama (RF-28).

El detalle de los demás casos de uso nuevos (CU-14, CU-15, CU-17, CU-18 y CU-19) está en el informe, sección 2.1.4.

## 4. Requisitos adicionales (no funcionales)

| ID | Requisito | Verificación |
|---|---|---|
| RNF-01 | Persistencia local offline en el proyecto móvil generado (SQLite) | Prueba física con CRUD sin red |
| RNF-02 | Arquitectura desplegable, con documentación de AWS | [`../DESPLIEGUE.md`](../DESPLIEGUE.md); prueba de humo |
| RNF-03 | Documentación de ingeniería suficiente (arquitectura, requisitos, proceso, decisiones, trazabilidad, pruebas) | Este directorio |
| RNF-04 | Privacidad: el chat de una persona no es accesible por otras | ✅ Pruebas de privacidad, con comprobación de que fallan si se filtra (I2) |
| RNF-05 | Resiliencia: si la IA falla, el diagrama no se pierde | ✅ Pruebas con fallo del proveedor: 502, nada guardado, el diagrama no cambia (I2/I3) |
| RNF-06 | El registro de actividad no degrada la edición | ✅ Mover/redimensionar no se registra; tope de tasa y tamaño; un fallo de la base no frena el relé (I1) |
| RNF-07 | Despliegue reproducible con prueba de humo | ✅ Runbook; 📋 script (I7) |
| RNF-08 | Seguridad de XMI: sin lectura de archivos locales ni red al importar (XXE) | ✅ Pruebas dedicadas de XMI |
| RNF-09 | HTTPS y sin puertos internos expuestos al exterior | ✅ Solo 22, 80 y 443 abiertos (2026-10-21) |
| RNF-10 | El frontend no accede a `window`/`localStorage` sin protección (SSR) | ✅ Revisión en cada cambio |

## 5. Glosario

| Término | Significado |
|---|---|
| **Sala** | Espacio compartido, identificado por un código, donde varias personas editan un mismo diagrama. |
| **Host (Diseñador)** | Rol temporal del participante más antiguo de la sala viva. |
| **Participante (Colaborador)** | Cualquier persona conectada a la sala. |
| **Presencia** | Lista en vivo de quién está en la sala y con qué rol. |
| **Operación** | Mensaje pequeño que describe un cambio del diagrama (`add_class`, `edit_text`, `move`, …). |
| **Respaldo** | Copia JSON del diagrama guardada en el servidor para recuperar el estado. |
| **Entidad intermedia** | Clase que el editor crea para representar una relación muchos-a-muchos. |
| **Clase asociativa** | Clase UML unida a una asociación para describirla; los generadores la convierten en dos relaciones 1:N. |
| **Multiplicidad** | Cantidad de instancias que participan en un extremo de una relación (`1`, `0..1`, `*`, …). |
| **XMI** | Formato XML para intercambiar modelos UML entre herramientas. |
| **Enterprise Architect (EA)** | Herramienta CASE con la que se prueba el intercambio XMI. |
| **Registro de actividad** | Lista visible para todos de las acciones relevantes de la sala (quién hizo qué). |
| **Pedir cambio / Preguntar** | Los dos modos del chat con la IA: con modificación del diagrama o solo consulta. |
| **Sugerencia** | Idea de la IA que no cambia nada hasta que alguien la aplica. |
| **Artefacto** | Producto de trabajo del proceso (modelo, documento, plan). |
| **Hito** | Punto de cierre de una fase, definido por los artefactos disponibles. |
