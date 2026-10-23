# Disciplina de Análisis

Artefactos: **clases de análisis**, **realización de casos de uso (análisis)** y **paquetes de análisis**. El modelo de análisis es conceptual: describe responsabilidades, no tecnología. El diseño ([`03-diseno.md`](03-diseno.md)) lo refina y lo adapta a Angular, Django y Spring.

Estereotipos usados (los del material de la cátedra): **interfaz** (frontera con el actor), **control** (coordina un caso de uso), **entidad** (información persistente o de larga vida).

## 1. Paquetes de análisis

El primer parcial identificó cinco paquetes. Los casos de uso nuevos no necesitaron un paquete nuevo: amplían dos de ellos.

| Paquete | Contenido | Casos de uso | Origen |
|---|---|---|---|
| **Gestión de lienzo** | Editor, Diagrama, Clase, Relación, Entidad intermedia, Clase asociativa | CU-01, CU-02, CU-05 | Primer parcial |
| **Colaboración** | Sala, Participante, Presencia, Operación, Respaldo, Evento de actividad | CU-03, CU-04; CU-14, CU-18, CU-19 | Se amplía |
| **Asistencia inteligente** | Pedido a la IA, Respuesta, Mensaje de chat, Sugerencia | CU-09; CU-15, CU-16, CU-17 | Se amplía |
| **Entrada multimodal** | Texto, imagen y voz como entrada del modelo | CU-06, CU-07, CU-08 | Primer parcial |
| **Exportación e integración** | Documento XMI, Esquema UML, Proyecto generado | CU-10, CU-11, CU-12, CU-13 | Primer parcial |

## 2. Clases de análisis

```mermaid
classDiagram
  class EditorDeDiagrama { <<interfaz>> }
  class PanelDeParticipantes { <<interfaz>> }
  class PanelDeActividad { <<interfaz>> }
  class ChatConIA { <<interfaz>> }
  class PanelLateral { <<interfaz>> }
  class VistaMovil { <<interfaz>> }

  class ControlDeEdicion { <<control>> }
  class ControlDeColaboracion { <<control>> }
  class ControlDeIdentidad { <<control>> }
  class ControlDeActividad { <<control>> }
  class ControlDeIA { <<control>> }
  class ControlDeXMI { <<control>> }
  class ControlDeGeneracion { <<control>> }

  class Diagrama { <<entidad>> }
  class Clase { <<entidad>> }
  class Relacion { <<entidad>> }
  class Sala { <<entidad>> }
  class Participante { <<entidad>> }
  class EventoDeActividad { <<entidad>> }
  class MensajeDeChat { <<entidad>> }
  class Sugerencia { <<entidad>> }
  class Respaldo { <<entidad>> }

  EditorDeDiagrama --> ControlDeEdicion
  PanelLateral --> ControlDeEdicion
  PanelDeParticipantes --> ControlDeColaboracion
  PanelDeActividad --> ControlDeActividad
  ChatConIA --> ControlDeIA
  VistaMovil --> ControlDeActividad
  ControlDeEdicion --> Diagrama
  ControlDeEdicion --> ControlDeColaboracion
  ControlDeColaboracion --> Sala
  ControlDeColaboracion --> Participante
  ControlDeColaboracion --> Respaldo
  ControlDeIdentidad --> Participante
  ControlDeActividad --> EventoDeActividad
  ControlDeIA --> MensajeDeChat
  ControlDeIA --> Sugerencia
  ControlDeIA --> ControlDeEdicion
  ControlDeIA --> ControlDeActividad
  ControlDeXMI --> Diagrama
  ControlDeGeneracion --> Diagrama
  Diagrama "1" o-- "*" Clase
  Diagrama "1" o-- "*" Relacion
  Sala "1" o-- "*" Participante
  Sala "1" o-- "*" EventoDeActividad
  Participante "1" --> "*" MensajeDeChat
```

### Responsabilidades

| Clase | Estereotipo | Responsabilidad |
|---|---|---|
| EditorDeDiagrama | interfaz | Lienzo donde el participante dibuja y mueve clases y relaciones |
| PanelLateral | interfaz | Edición de nombre, atributos, métodos y multiplicidades |
| PanelDeParticipantes | interfaz | Muestra nombre, rol y "(Tú)"; el host ve el botón de expulsar |
| PanelDeActividad | interfaz | Lista, de más nueva a más vieja, quién hizo qué |
| ChatConIA | interfaz | Chat privado con modos Preguntar y Pedir cambio *(📋)* |
| VistaMovil | interfaz | Seguimiento de solo lectura *(📋)* |
| ControlDeEdicion | control | Aplica cambios al diagrama, aplica la regla de entidad intermedia, guarda localmente y programa el respaldo |
| ControlDeColaboracion | control | Envía y recibe operaciones, pide y entrega el estado completo, aplica roles y expulsión |
| ControlDeIdentidad | control | Mantiene el identificador anónimo y el nombre visible; los envía al entrar |
| ControlDeActividad | control | Decide qué acciones se registran (solo las relevantes), fusiona ediciones repetidas y las difunde |
| ControlDeIA | control | Arma el contexto, llama al proveedor, valida las respuestas y las convierte en operaciones o sugerencias *(📋)* |
| ControlDeXMI | control | Convierte el diagrama a XMI y viceversa, rechazando entradas inseguras |
| ControlDeGeneracion | control | Convierte el diagrama en proyecto Spring/Postman o Flutter |
| Diagrama / Clase / Relación | entidad | El modelo UML: clases con atributos y métodos; relaciones con tipo y multiplicidades |
| Sala / Participante | entidad | Quién está en la sala y con qué rol (vivo); identificador anónimo y nombre (persistente) |
| EventoDeActividad | entidad | Autor, tipo, objetivo, resumen y fecha de una acción |
| MensajeDeChat / Sugerencia | entidad | Conversación privada con la IA; idea propuesta que nadie aplicó aún |
| Respaldo | entidad | Copia del diagrama de la sala para recuperar el estado |

## 3. Realización de casos de uso (análisis)

### CU-03 Colaborar en tiempo real

```mermaid
flowchart LR
  Part([Participante])
  UI[PanelDeParticipantes / EditorDeDiagrama]
  CC((ControlDeColaboracion))
  Sala[(Sala)]
  Resp[(Respaldo)]
  Part -->|1 abre la sala| UI
  UI -->|2 unirse| CC
  CC -->|3 registrar y asignar rol| Sala
  CC -->|4 avisar presencia| UI
  CC -->|5 pedir estado| Resp
  UI -->|6 editar| CC
  CC -->|7 difundir operación| Sala
  CC -->|8 guardar respaldo| Resp
```

### CU-14 Consultar la actividad del equipo

```mermaid
flowchart LR
  Part([Participante])
  PA[PanelDeActividad]
  CA((ControlDeActividad))
  Ev[(EventoDeActividad)]
  Part -->|1 abre el panel| PA
  PA -->|2 pedir historial| CA
  CA -->|3 leer eventos| Ev
  CA -->|4 devolver lista| PA
  CA -->|5 evento nuevo en vivo| PA
```

### CU-16 Pedirle a la IA un cambio en el diagrama

```mermaid
flowchart LR
  Part([Participante])
  Chat[ChatConIA]
  CI((ControlDeIA))
  CE((ControlDeEdicion))
  CA((ControlDeActividad))
  Prov([Servicio de IA])
  Part -->|1 pedido| Chat
  Chat -->|2 enviar| CI
  CI -->|3 contexto: diagrama + actividad + chat propio| Prov
  Prov -->|4 operaciones propuestas| CI
  CI -->|5 validar y aplicar| CE
  CE -->|6 difundir a todos| CE
  CI -->|7 registrar «IA, a pedido de X»| CA
```

## 4. Reglas de análisis que se derivan

| Regla | Origen |
|---|---|
| La IA no modifica el diagrama sin un pedido explícito de un participante | RF-28 |
| Los cambios de la IA entran por la misma ruta que los manuales, así que se propagan y respetan las reglas del editor | RF-29 |
| El texto de un chat solo lo ve su dueño; la actividad es visible para todos | RNF-04, RF-25 |
| Mover o redimensionar nunca se registra | RNF-06 |
| El rol de host no sobrevive a la desconexión ni a la reconexión | RF-16, RF-17 |
| Una relación no desaparece en silencio: si una entidad intermedia deja de ser válida, se restaura la asociación original | Revisión de la entidad intermedia (I0) |
