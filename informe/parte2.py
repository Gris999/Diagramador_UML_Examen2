"""Genera la Parte 2 del informe (registro del proceso PUDS) con la estructura de los informes modelo.

Devuelve Markdown con bloques ```plantuml: `generar_informe.py` los convierte a imágenes.
Todos los diagramas siguen la notación UML 2.5.1.
"""

import textwrap

from parte2_datos import ACTORES, CICLOS, CUS, DEPENDENCIAS_PAQUETES, NOMBRE_ACTOR, PAQUETES

ESTILO = """skinparam shadowing false
skinparam defaultFontName Arial
skinparam defaultFontSize 12
skinparam roundCorner 0
skinparam backgroundColor #FFFFFF
skinparam ArrowColor #000000
skinparam ArrowFontSize 11
skinparam ActorBorderColor #000000
skinparam ActorBackgroundColor #FFFFFF
skinparam UsecaseBorderColor #000000
skinparam UsecaseBackgroundColor #FFFFFF
skinparam RectangleBorderColor #000000
skinparam RectangleBackgroundColor #FFFFFF
skinparam PackageBorderColor #000000
skinparam PackageBackgroundColor #FFFFFF
skinparam ClassBorderColor #000000
skinparam ClassBackgroundColor #FFFFFF
skinparam ClassAttributeIconSize 0
skinparam NoteBackgroundColor #FFFFE1
skinparam NoteBorderColor #000000
skinparam ComponentBorderColor #000000
skinparam ComponentBackgroundColor #FFFFFF
skinparam NodeBorderColor #000000
skinparam NodeBackgroundColor #FFFFFF
skinparam DatabaseBorderColor #000000
skinparam DatabaseBackgroundColor #FFFFFF
skinparam ParticipantBorderColor #000000
skinparam ParticipantBackgroundColor #FFFFFF
skinparam SequenceLifeLineBorderColor #000000
skinparam SequenceBoxBorderColor #000000
skinparam BoundaryBackgroundColor #FFFFFF
skinparam ControlBackgroundColor #FFFFFF
skinparam EntityBackgroundColor #FFFFFF
skinparam packageStyle folder
"""


def uml(cuerpo, estilo=True, id_ea=None):
    """Bloque PlantUML. `id_ea` marca los diagramas que también existen en Enterprise Architect: el generador
    del informe usa la imagen de EA (`build/ea/<id>.png`) si existe y, si no, dibuja este bloque."""
    marca = f"' ea:{id_ea}\n" if id_ea else ""
    return f"```plantuml\n@startuml\n{marca}{ESTILO if estilo else ''}{cuerpo}\n@enduml\n```\n"


def _id(codigo):
    return codigo.replace("-", "")


def _envolver(texto, ancho=24):
    return "\\n".join(textwrap.wrap(texto, ancho)) or texto


def _actor(codigo):
    return f'actor "{codigo}\\n({NOMBRE_ACTOR[codigo]})" as {codigo}'


# ---- diagramas por caso de uso ---------------------------------------------------------------
def diagrama_casos_uso(codigos, titulo=None, id_ea=None):
    """Actores a la izquierda, casos de uso en el centro y actores secundarios a la derecha."""
    mostrados = list(codigos)
    for codigo in codigos:
        for inc in CUS[codigo]["incluye"]:
            if inc not in mostrados:
                mostrados.append(inc)
    primarios, secundarios = [], []
    for codigo in codigos:
        actores = CUS[codigo]["actores"]
        for indice, actor in enumerate(actores):
            destino = primarios if (indice == 0 or actor in ("A2",)) else secundarios
            if actor not in primarios and actor not in secundarios:
                destino.append(actor)
    lineas = ["left to right direction"]
    if titulo:
        lineas.append(f'title {titulo}')
    lineas += [_actor(a) for a in primarios + secundarios]
    lineas.append('rectangle "Plataforma CASE colaborativa" {')
    for codigo in mostrados:
        lineas.append(f'  usecase "{codigo}:\\n{_envolver(CUS[codigo]["nombre"])}" as {_id(codigo)}')
    lineas.append("}")
    for codigo in codigos:
        datos = CUS[codigo]
        for indice, actor in enumerate(datos["actores"]):
            if actor in primarios:
                lineas.append(f"{actor} --> {_id(codigo)}")
            else:
                lineas.append(f"{_id(codigo)} --> {actor}")
        for inc in datos["incluye"]:
            lineas.append(f"{_id(codigo)} .> {_id(inc)} : <<include>>")
    if "A2" in primarios and "A1" in primarios:
        lineas.append("A2 --|> A1")
    return uml("\n".join(lineas), id_ea=id_ea)


def _roles(cu):
    """(clave -> (palabra clave PlantUML, etiqueta)) para los roles que usa el caso de uso."""
    datos = CUS[cu]
    roles = {"U": ("actor", NOMBRE_ACTOR[datos["actores"][0]]),
             "IU": ("boundary", datos["iu"]), "CT": ("control", datos["control"])}
    for indice, entidad in enumerate(datos["entidades"], 1):
        roles[f"E{indice}"] = ("entity", entidad)
    if datos["externo"]:
        roles["EX"] = ("participant" if True else "actor", datos["externo"])
    return roles


def _mensajes(cu):
    return [(m[0], m[1], m[2], len(m) > 3 and m[3]) for m in CUS[cu]["mensajes"]]


def diagrama_comunicacion(cu):
    roles = _roles(cu)
    lineas = ["top to bottom direction", "skinparam nodesep 40", "skinparam ranksep 50"]
    for clave, (tipo, etiqueta) in roles.items():
        if clave == "EX":
            lineas.append(f'rectangle "{etiqueta}" as EX')
        else:
            lineas.append(f'{tipo} "{etiqueta}" as {clave}')
    for numero, (origen, destino, texto, retorno) in enumerate(_mensajes(cu), 1):
        flecha = "..>" if retorno else "-->"
        lineas.append(f"{origen} {flecha} {destino} : {numero}: {texto}")
    return uml("\n".join(lineas), id_ea=f"com-{cu.replace('-', '')}")


def diagrama_secuencia(cu):
    roles = _roles(cu)
    lineas = []
    for clave, (tipo, etiqueta) in roles.items():
        palabra = "participant" if clave == "EX" else tipo
        lineas.append(f'{palabra} "{etiqueta}" as {clave}')
    for origen, destino, texto, retorno in _mensajes(cu):
        flecha = "-->" if retorno else "->"
        lineas.append(f"{origen} {flecha} {destino} : {texto}")
    return uml("\n".join(lineas), id_ea=f"sec-{cu.replace('-', '')}")


def clases_analisis(codigos):
    """Clases de interfaz, control y entidad de los casos de uso de un ciclo, con sus operaciones.

    Devuelve (interfaces, controles, entidades, relaciones): los tres primeros son {nombre: {operaciones}}
    y `relaciones` un conjunto de (origen, destino) por nombre. Lo usan el diagrama PlantUML y el modelo de EA.
    """
    interfaces, controles, entidades, relaciones = {}, {}, {}, set()
    for cu in codigos:
        datos = CUS[cu]
        roles = _roles(cu)
        iu, ct = datos["iu"], datos["control"]
        interfaces.setdefault(iu, set())
        controles.setdefault(ct, set())
        relaciones.add((iu, ct))
        for origen, destino, texto, retorno in _mensajes(cu):
            if retorno or origen == destino:
                continue
            operacion = texto.split("(")[0] + "()"
            if destino == "IU":
                interfaces[iu].add(operacion)
            elif destino == "CT" and origen == "IU":
                controles[ct].add(operacion)
            elif destino.startswith("E"):
                nombre = roles[destino][1]
                entidades.setdefault(nombre, set()).add(operacion)
                relaciones.add((ct, nombre))
        for _, nombre in [(k, v[1]) for k, v in roles.items() if k.startswith("E")]:
            entidades.setdefault(nombre, set())
    return interfaces, controles, entidades, relaciones


def diagrama_clases_analisis(codigos, id_ea=None):
    """Clases de interfaz, control y entidad de los casos de uso de un ciclo, con sus operaciones."""
    interfaces, controles, entidades, relaciones = clases_analisis(codigos)
    alias = {}

    def declarar(nombre, estereotipo, operaciones, indice):
        clave = f"{estereotipo[:1].upper()}{indice}"
        alias[nombre] = clave
        cuerpo = "\n".join(f"  +{o}" for o in sorted(operaciones))
        return f'class "{nombre}" as {clave} <<{estereotipo}>> {{\n{cuerpo}\n}}'

    lineas = ["left to right direction"]
    for indice, (nombre, ops) in enumerate(interfaces.items(), 1):
        lineas.append(declarar(nombre, "interfaz", ops, indice))
    for indice, (nombre, ops) in enumerate(controles.items(), 1):
        lineas.append(declarar(nombre, "control", ops, indice))
    for indice, (nombre, ops) in enumerate(entidades.items(), 1):
        lineas.append(declarar(nombre, "entidad", ops, indice))
    for origen, destino in sorted(relaciones):
        lineas.append(f"{alias[origen]} --> {alias[destino]}")
    return uml("\n".join(lineas), id_ea=id_ea)


# ---- paquetes de análisis -----------------------------------------------------------------------
def diagrama_paquetes_identificados():
    lineas = ["left to right direction"]
    for indice, (nombre, contenido, cus) in enumerate(PAQUETES, 1):
        lineas.append(f'package "{nombre.upper()}" as P{indice} {{\n}}')
        lineas.append(f'note right of P{indice}\n{_envolver(contenido, 38)}\nend note')
    return uml("\n".join(lineas), id_ea="pk-identificados")


def diagrama_paquetes_y_cu():
    lineas = ["left to right direction"]
    for indice, (nombre, _, cus) in enumerate(PAQUETES, 1):
        lineas.append(f'package "{nombre.upper()}" as P{indice} {{')
        for cu in cus:
            lineas.append(f'  usecase "{cu}:\\n{_envolver(CUS[cu]["nombre"], 22)}" as {_id(cu)}')
        lineas.append("}")
    return uml("\n".join(lineas), id_ea="pk-cu")


def diagrama_vista_paquete(indice):
    nombre, _, cus = PAQUETES[indice]
    actores = []
    for cu in cus:
        for actor in CUS[cu]["actores"][:1]:
            if actor not in actores:
                actores.append(actor)
    lineas = ["left to right direction"] + [_actor(a) for a in actores]
    lineas.append(f'package "{nombre.upper()}" {{')
    for cu in cus:
        lineas.append(f'  usecase "{cu}:\\n{_envolver(CUS[cu]["nombre"], 22)}" as {_id(cu)}')
    lineas.append("}")
    for cu in cus:
        lineas.append(f"{CUS[cu]['actores'][0]} --> {_id(cu)}")
        for inc in CUS[cu]["incluye"]:
            if inc in cus:
                lineas.append(f"{_id(cu)} .> {_id(inc)} : <<include>>")
    return uml("\n".join(lineas), id_ea=f"pk-vista-{indice + 1}")


def diagrama_dependencias_paquetes():
    lineas = ["left to right direction"]
    for indice, (nombre, _, _) in enumerate(PAQUETES, 1):
        lineas.append(f'package "{nombre.upper()}" as P{indice} {{\n}}')
    indice_de = {nombre: i for i, (nombre, _, _) in enumerate(PAQUETES, 1)}
    for origen, destino in DEPENDENCIAS_PAQUETES:
        lineas.append(f"P{indice_de[origen]} ..> P{indice_de[destino]}")
    return uml("\n".join(lineas), id_ea="pk-dep")


# ---- diseño: C4, despliegue, capas, datos, componentes ----------------------------------------
C4_CONTEXTO = """!include <C4/C4_Context>
LAYOUT_WITH_LEGEND()
Person(participante, "Participante", "Diseña diagramas de clases UML en equipo")
Person(observador, "Observador", "Sigue la sala desde el celular, en solo lectura")
System(sistema, "Plataforma CASE colaborativa", "Modelado UML 2.5, IA como integrante de la sala, generación de código")
System_Ext(gemini, "Google Gemini", "IA en la nube")
System_Ext(ollama, "Ollama + modelo reentrenado", "IA local, sin internet")
System_Ext(ea, "Enterprise Architect", "Herramienta CASE (intercambio XMI)")
Rel(participante, sistema, "Edita y conversa con la IA", "HTTPS / WebSocket")
Rel(observador, sistema, "Sigue en vivo", "HTTPS")
Rel(sistema, gemini, "Pide respuestas", "HTTPS")
Rel(sistema, ollama, "Pide respuestas (opcional)", "HTTP")
Rel(sistema, ea, "Importa y exporta modelos", "XMI")
"""

C4_CONTENEDORES = """!include <C4/C4_Container>
LAYOUT_WITH_LEGEND()
Person(p, "Participante", "Edita el diagrama")
System_Boundary(s, "Plataforma CASE colaborativa") {
  Container(web, "Aplicación web", "Angular 20 (SSR) + JointJS", "Editor, chat con la IA, actividad, vista móvil")
  Container(api, "API y tiempo real", "Django 5 + Channels + Daphne", "REST, WebSocket, registro de actividad, proveedores de IA, XMI, generador Flutter")
  Container(gen, "Generador de backend", "Spring Boot 3.5 (Java 21)", "Proyecto Spring + PostgreSQL y colección Postman")
  ContainerDb(pg, "Base de datos", "PostgreSQL 17", "Respaldo, participantes, actividad y chats")
  ContainerDb(redis, "Estado de salas", "Redis 7", "Capa de canales y orden de conexión (host)")
}
System_Ext(gemini, "Google Gemini", "IA en la nube")
System_Ext(ollama, "Ollama", "IA local con modelo reentrenado")
Rel(p, web, "Usa", "HTTPS")
Rel(web, api, "Edición y chat", "REST + WebSocket")
Rel(web, gen, "Genera backend", "HTTPS")
Rel(api, pg, "Lee y escribe", "SQL")
Rel(api, redis, "Presencia y roles", "RESP")
Rel(api, gemini, "Pide respuestas", "HTTPS")
Rel(api, ollama, "Pide respuestas (opcional)", "HTTP")
"""

C4_COMPONENTES = """!include <C4/C4_Component>
LAYOUT_WITH_LEGEND()
Container(web, "Aplicación web", "Angular", "Editor y paneles")
ContainerDb(pg, "PostgreSQL", "", "")
ContainerDb(redis, "Redis", "", "")
System_Ext(prov, "Gemini / Ollama", "Proveedores de IA")
Container_Boundary(api, "API y tiempo real (Django)") {
  Component(canvas, "CanvasConsumer", "Channels", "Relé de operaciones, presencia, roles y observadores")
  Component(act, "Actividad e identidad", "collab", "Registra quién hizo qué y valida el nombre")
  Component(chat, "Chat con la IA", "DRF", "Preguntar, pedir cambio y revisar; topes de uso; reserva de ideas")
  Component(guard, "Guardia de cambios", "uml_api", "Valida tamaño y cuenta lo que se eliminaría")
  Component(provider, "Proveedores de IA", "uml_api", "Interfaz con Gemini y Ollama (modelo reentrenado)")
  Component(xmi, "XMI y generador Flutter", "uml_api", "Intercambio con Enterprise Architect y proyecto móvil")
}
Rel(web, canvas, "Operaciones", "WebSocket")
Rel(web, chat, "Pedidos", "REST")
Rel(canvas, act, "Registra")
Rel(canvas, redis, "Roles")
Rel(act, pg, "Guarda")
Rel(chat, guard, "Valida")
Rel(chat, provider, "Pide")
Rel(provider, prov, "HTTP")
Rel(chat, pg, "Guarda chats")
Rel(web, xmi, "Importa y exporta", "REST")
"""

CODIGO = """class AIProvider <<interface>> {
  +chat(prompt): str
  +change(instruction, uml): dict
}
class GeminiProvider {
  +chat(prompt): str
  +change(instruction, uml): dict
}
class OllamaProvider {
  -model: str
  -change_model: str
  +chat(prompt): str
  +change(instruction, uml): dict
}
class modelo_reentrenado <<módulo>> {
  +compactar(uml)
  +mensajes(uml, pedido)
  +restaurar(cambios, alias, uml)
  +quitar_razonamiento(texto)
}
class change_guard <<módulo>> {
  +validate_changes(cambios)
  +count_destructive(cambios, uml)
}
class ChatView <<vista>> {
  +ia_chat(request, room)
  +claim_suggestion(request, room, id, idx)
}
AIProvider <|.. GeminiProvider
AIProvider <|.. OllamaProvider
OllamaProvider ..> modelo_reentrenado : usa
ChatView ..> AIProvider
ChatView ..> change_guard
"""

DESPLIEGUE = """node "Navegador del usuario" <<device>> as N {
  artifact "Aplicación Angular" as A
}
node "AWS EC2 (Ubuntu 24.04, 2 vCPU, 2 GB)" <<device>> as EC2 {
  node "nginx + Let's Encrypt" <<execution environment>> as NG
  node "Docker Compose" <<execution environment>> as DK {
    artifact "angular_frontend\\n:4000 (publicado 4200)" as FE
    artifact "django_backend_UML\\n:8000 (Daphne)" as DJ
    artifact "spring_backend\\n:7001" as SP
    database "postgres_db\\n:5432" as PG
    database "redis_server\\n:6379" as RD
  }
}
cloud "Google Gemini API" as G
node "Equipo con Apple Silicon" <<device>> as MAC {
  artifact "Ollama + modelo reentrenado\\n:11434" as OL
}
N --> NG : HTTPS / WSS :443
NG --> FE : /
NG --> DJ : /api, /ws
NG --> SP : /generate
DJ --> PG
DJ --> RD
DJ --> G : HTTPS
DJ ..> OL : HTTP (opcional)
"""

CAPAS = """top to bottom direction
package "Capa de presentación" as C1 {
  [Componentes Angular\\n(editor, paneles, chat, vista móvil)] as ui
}
package "Capa de aplicación" as C2 {
  [Servicios Angular\\n(colaboración, IA, diagrama)] as sv
  [Vistas DRF y consumidores de WebSocket] as vw
}
package "Capa de dominio" as C3 {
  [Modelo del diagrama\\n(JointJS: clases y relaciones)] as dm
  [Modelos de datos Django\\n(participante, actividad, chat)] as md
}
package "Capa de infraestructura" as C4 {
  [PostgreSQL] as pg
  [Redis] as rd
  [Proveedores de IA\\n(Gemini, Ollama)] as pv
  [Generador Spring Boot] as gn
}
ui --> sv
sv --> vw
vw --> md
sv --> dm
md --> pg
vw --> rd
vw --> pv
vw --> gn
"""

TABLAS = [
    ("collab_participant", "Persona que entró a una sala (identificador anónimo y nombre visible)", [
        ("id", "bigint", "Identificador", "8 bytes", "NO", "PK"),
        ("room", "varchar(64)", "Código de la sala", "64", "NO", ""),
        ("token", "uuid", "Identificador anónimo del navegador", "16 bytes", "NO", "Único con room"),
        ("display_name", "varchar(40)", "Nombre visible", "40", "NO", ""),
        ("created_at", "timestamptz", "Primera vez que entró", "8 bytes", "NO", ""),
        ("last_seen", "timestamptz", "Última actividad", "8 bytes", "NO", "")]),
    ("collab_activityevent", "Registro de actividad de la sala", [
        ("id", "bigint", "Identificador", "8 bytes", "NO", "PK"),
        ("room", "varchar(64)", "Código de la sala", "64", "NO", "Índice con created_at"),
        ("actor_id", "bigint", "Quién lo hizo", "8 bytes", "SÍ", "FK a participante"),
        ("actor_name", "varchar(40)", "Nombre mostrado (incluye «IA»)", "40", "NO", ""),
        ("actor_kind", "varchar(16)", "Persona o IA", "16", "NO", ""),
        ("type", "varchar(32)", "Tipo de acción", "32", "NO", ""),
        ("target_id", "varchar(255)", "Elemento afectado", "255", "NO", ""),
        ("summary", "varchar(255)", "Texto que ve el equipo", "255", "NO", ""),
        ("data", "jsonb", "Detalles (por ejemplo, ideas de una revisión)", "≤ 8 KB", "NO", ""),
        ("created_at", "timestamptz", "Fecha y hora", "8 bytes", "NO", "")]),
    ("collab_chatmessage", "Conversación privada de cada persona con la IA", [
        ("id", "bigint", "Identificador", "8 bytes", "NO", "PK"),
        ("room", "varchar(64)", "Código de la sala", "64", "NO", ""),
        ("participant_id", "bigint", "Dueño de la conversación", "8 bytes", "NO", "FK; índice con id"),
        ("role", "varchar(8)", "Persona o IA", "8", "NO", ""),
        ("mode", "varchar(8)", "Preguntar, cambio o revisar", "8", "NO", ""),
        ("content", "text", "Mensaje", "≤ 2000 caracteres", "NO", ""),
        ("created_at", "timestamptz", "Fecha y hora", "8 bytes", "NO", "")]),
    ("collab_iaattempt", "Pedidos a la IA que ya reservaron cupo (topes de uso)", [
        ("id", "bigint", "Identificador", "8 bytes", "NO", "PK"),
        ("room", "varchar(64)", "Código de la sala", "64", "NO", ""),
        ("participant_id", "bigint", "Quién pidió", "8 bytes", "NO", "FK"),
        ("created_at", "timestamptz", "Fecha y hora", "8 bytes", "NO", "Índice")]),
    ("uml_api_backupuml", "Copia del diagrama de cada sala para recuperar el estado", [
        ("id", "bigint", "Identificador", "8 bytes", "NO", "PK"),
        ("room_id", "uuid", "Sala", "16 bytes", "NO", "Único"),
        ("data", "jsonb", "Diagrama completo", "hasta 1 GB (en la práctica, unos KB)", "NO", ""),
        ("created_at", "timestamptz", "Fecha y hora", "8 bytes", "NO", "")]),
]

DDL = """CREATE TABLE collab_participant (
    id            bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    room          varchar(64)  NOT NULL,
    token         uuid         NOT NULL,
    display_name  varchar(40)  NOT NULL,
    created_at    timestamptz  NOT NULL,
    last_seen     timestamptz  NOT NULL,
    CONSTRAINT unique_participant_room_token UNIQUE (room, token)
);

CREATE TABLE collab_activityevent (
    id          bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    room        varchar(64)  NOT NULL,
    actor_id    bigint REFERENCES collab_participant (id) ON DELETE SET NULL,
    actor_name  varchar(40)  NOT NULL,
    actor_kind  varchar(16)  NOT NULL DEFAULT 'user',
    type        varchar(32)  NOT NULL,
    target_id   varchar(255) NOT NULL,
    summary     varchar(255) NOT NULL,
    data        jsonb        NOT NULL,
    created_at  timestamptz  NOT NULL
);
CREATE INDEX activity_room_created_idx ON collab_activityevent (room, created_at);

CREATE TABLE collab_chatmessage (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    room            varchar(64) NOT NULL,
    participant_id  bigint      NOT NULL REFERENCES collab_participant (id) ON DELETE CASCADE,
    role            varchar(8)  NOT NULL,
    mode            varchar(8)  NOT NULL DEFAULT 'ask',
    content         text        NOT NULL,
    created_at      timestamptz NOT NULL
);
CREATE INDEX chat_participant_id_idx ON collab_chatmessage (participant_id, id);

CREATE TABLE collab_iaattempt (
    id              bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    room            varchar(64) NOT NULL,
    participant_id  bigint      NOT NULL REFERENCES collab_participant (id) ON DELETE CASCADE,
    created_at      timestamptz NOT NULL
);
CREATE INDEX collab_iaattempt_created_at_idx ON collab_iaattempt (created_at);

CREATE TABLE uml_api_backupuml (
    id          bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    room_id     uuid        NOT NULL UNIQUE,
    data        jsonb       NOT NULL,
    created_at  timestamptz NOT NULL
);"""

MODELO_DATOS = """left to right direction
hide circle
class collab_participant <<tabla>> {
  +id : bigint <<PK>>
  room : varchar(64)
  token : uuid
  display_name : varchar(40)
  created_at : timestamptz
  last_seen : timestamptz
}
class collab_activityevent <<tabla>> {
  +id : bigint <<PK>>
  room : varchar(64)
  actor_id : bigint <<FK>>
  actor_name : varchar(40)
  actor_kind : varchar(16)
  type : varchar(32)
  summary : varchar(255)
  data : jsonb
  created_at : timestamptz
}
class collab_chatmessage <<tabla>> {
  +id : bigint <<PK>>
  room : varchar(64)
  participant_id : bigint <<FK>>
  role : varchar(8)
  mode : varchar(8)
  content : text
  created_at : timestamptz
}
class collab_iaattempt <<tabla>> {
  +id : bigint <<PK>>
  room : varchar(64)
  participant_id : bigint <<FK>>
  created_at : timestamptz
}
class uml_api_backupuml <<tabla>> {
  +id : bigint <<PK>>
  room_id : uuid
  data : jsonb
  created_at : timestamptz
}
collab_participant "1" <-- "0..*" collab_activityevent
collab_participant "1" <-- "0..*" collab_chatmessage
collab_participant "1" <-- "0..*" collab_iaattempt
"""

COMPONENTES = """top to bottom direction
skinparam nodesep 30
skinparam componentStyle uml2
package "Cliente (navegador)" {
  [Editor de diagrama] as ED
  [Servicios de colaboración] as SC
  [Servicios de IA y chat] as SI
  [Exportaciones e importaciones] as SE
}
package "Servidor Django" {
  [collab: relé de WebSocket] as RW
  [collab: actividad e identidad] as AI
  [uml_api: chat con la IA] as CH
  [uml_api: proveedores de IA] as PR
  [uml_api: XMI y generador Flutter] as XF
}
[Generador Spring Boot] as GS
database "PostgreSQL" as PG
database "Redis" as RE
[Gemini] as GE
[Ollama (modelo reentrenado)] as OL
ED -- SC
SC --( RW : WebSocket
SI --( CH : REST
SE --( XF : REST
SE --( GS : HTTPS
RW ..> AI
RW ..> RE
AI ..> PG
CH ..> PR
CH ..> PG
PR ..> GE
PR ..> OL
"""

SUBSISTEMAS = """left to right direction
package "Subsistema de edición" <<subsistema>> as S1 {
  [Editor de diagrama]
  [Reglas del editor (entidad intermedia)]
}
package "Subsistema de colaboración" <<subsistema>> as S2 {
  [Relé de operaciones]
  [Roles y presencia]
  [Respaldo del diagrama]
}
package "Subsistema de actividad" <<subsistema>> as S3 {
  [Registro de actividad]
  [Identidad de participantes]
  [Vista móvil de seguimiento]
}
package "Subsistema de asistencia por IA" <<subsistema>> as S4 {
  [Chat privado]
  [Guardia de cambios]
  [Proveedores de IA]
  [Modelo reentrenado]
}
package "Subsistema de interoperabilidad y generación" <<subsistema>> as S5 {
  [XMI (Enterprise Architect)]
  [Generador Spring Boot]
  [Generador Flutter]
}
S2 ..> S1
S2 ..> S3
S4 ..> S1
S4 ..> S2
S4 ..> S3
S5 ..> S1
"""


# ---- texto -------------------------------------------------------------------------------------
def tabla_caso_uso(cu):
    datos = CUS[cu]
    actores = ", ".join(datos["actores"])
    pasos = " ".join(f"{i}. {p}" for i, p in enumerate(datos["flujo"], 1))
    return "\n".join([
        "| | |", "|---|---|",
        f"| **CASO DE USO** | {cu}: {datos['nombre']} |",
        f"| **PROPÓSITO** | {datos['proposito']} |",
        f"| **ACTORES** | {actores} |",
        f"| **INICIADOR** | {datos['iniciador']} |",
        f"| **PRECONDICIÓN** | {datos['precondicion']} |",
        f"| **FLUJO DE SUCESO PRINCIPAL** | {pasos} |",
        f"| **POSTCONDICIÓN** | {datos['postcondicion']} |",
        f"| **EXCEPCIÓN** | {datos['excepcion']} |",
    ]) + "\n"


def parte_requisitos():
    md = ["# 2. Registro del proceso de desarrollo de software (PUDS)\n",
          "Esta parte registra el proceso seguido con el Proceso Unificado de Desarrollo de Software: "
          "los cinco flujos de trabajo (requisitos, análisis, diseño, implementación y pruebas) aplicados en cuatro "
          "ciclos de vida. La etapa de despliegue se documenta de forma resumida en el Anexo C. Todos los diagramas "
          "siguen la notación UML 2.5.1; el modelo de clases del editor puede, además, exportarse a XMI y abrirse en "
          "Enterprise Architect (caso de uso CU16).\n",
          "## 2.1 Captura de requisitos\n",
          "**Visión del proyecto.** Modelar un sistema con UML suele hacerse de forma individual y en herramientas de "
          "escritorio, y pasar del modelo al código es un trabajo manual. Cuando varias personas diseñan a la vez se pierde "
          "la visión de quién cambió qué, y la inteligencia artificial suele vivir fuera del equipo, sin conocer el "
          "diagrama ni lo que hizo cada integrante.\n",
          "**Objetivo general.** Construir una plataforma CASE web para modelar diagramas de clases UML 2.5 de forma "
          "colaborativa, en la que la inteligencia artificial participe como un integrante más de la sala, y que genere a "
          "partir del modelo un backend Spring Boot con PostgreSQL, una colección de Postman y un proyecto Flutter.\n",
          "**Objetivos específicos.**\n",
          "- Crear y editar diagramas de clases manualmente, con importación y exportación XMI para Enterprise Architect.",
          "- Crear o modificar el diagrama a partir de texto, imágenes y voz.",
          "- Soportar sesiones colaborativas de 2 a 3 personas con *host* y participantes, expulsión, reconexión y "
          "recuperación del estado.",
          "- Incorporar la IA como integrante de la sala: no actúa hasta que se le pide, sus ideas son visibles, conoce lo "
          "que hizo cada persona, cada persona tiene su propio chat y las sesiones pueden retomarse.",
          "- Ofrecer una vista móvil de solo lectura, generar el backend, la colección de Postman y el proyecto Flutter, y "
          "ofrecer una IA local reentrenada como extra valorable.\n",
          "**Alcance.** Incluye todo lo anterior y el despliegue en AWS con HTTPS. No incluye cuentas de usuario con inicio "
          "de sesión (el código de la sala es la llave de acceso), edición desde la vista móvil, ni infraestructura como "
          "código.\n",
          "### 2.1.1 Actores\n"]
    for c, n, d in ACTORES:
        md += [f"**{c}: {n}**\n", f"{d}\n"]
    md += ["### 2.1.2 Casos de uso\n"]
    for numero, _, _, codigos in CICLOS:
        for cu in codigos:
            md.append(f"- ➢ {cu}: {CUS[cu]['nombre']}")
    md.append("")
    md += ["### 2.1.3 Priorizar casos de uso\n",
           "Los casos de uso se agruparon en cuatro ciclos de vida según su prioridad y el riesgo que reducen: "
           "primero los que fijan la arquitectura (colaboración en tiempo real, edición e intercambio XMI), después "
           "los que dan identidad y contexto a la IA, luego las acciones de la IA y, al final, lo opcional.\n"]
    prioridad = {"Alta": "Crítica", "Media": "Normal", "Baja": "Normal"}
    riesgo = {"Alta": "Alto", "Media": "Medio", "Baja": "Bajo"}
    for numero, nombre, iteraciones, codigos in CICLOS:
        md += [f"#### Ciclo de vida #{numero}\n",
               "| NRO | Casos de uso | Estado | Prioridad | Riesgo | Actor |", "|---|---|---|---|---|---|"]
        md += [f"| {cu} | {CUS[cu]['nombre']} | Aprobado | {prioridad[CUS[cu]['prioridad']]} | "
               f"{riesgo[CUS[cu]['prioridad']]} | {', '.join(CUS[cu]['actores'])} |" for cu in codigos]
        md.append("")
    md += ["### 2.1.4 Detallar casos de uso\n"]
    for numero, nombre, iteraciones, codigos in CICLOS:
        md.append(f"#### Ciclo de vida #{numero}\n")
        for cu in codigos:
            md += [f"**{CUS[cu]['nombre']}.**\n", diagrama_casos_uso([cu], id_ea=f"uc-{cu.replace('-', '')}"), tabla_caso_uso(cu)]
    md += ["### 2.1.5 Estructurar el modelo de caso de uso\n"]
    acumulado = []
    for numero, nombre, iteraciones, codigos in CICLOS:
        acumulado += codigos
        md += [f"#### Ciclo de vida #{numero}\n", diagrama_casos_uso(codigos, id_ea=f"uc-ciclo-{numero}")]
    md += ["#### Modelo completo (ciclos 1 a 4)\n", diagrama_casos_uso(acumulado, id_ea="uc-ciclo-todo")]
    return "\n".join(md)


def parte_analisis():
    md = ["## 2.2 Flujo de trabajo: análisis\n",
          "### 2.2.1 Análisis de arquitectura\n",
          "#### 2.2.1.1 Identificar paquetes\n",
          "Se agruparon los casos de uso por afinidad funcional en seis paquetes de análisis.\n",
          "| Paquete | Contenido | Casos de uso |", "|---|---|---|"]
    md += [f"| **{n}** | {c} | {', '.join(cus)} |" for n, c, cus in PAQUETES]
    md += ["", diagrama_paquetes_identificados(),
           "#### 2.2.1.2 Relacionar paquetes y casos de uso\n", diagrama_paquetes_y_cu(),
           "#### 2.2.1.3 Vista del paquete\n"]
    for indice, (nombre, _, _) in enumerate(PAQUETES):
        md += [f"**Paquete {nombre}**\n", diagrama_vista_paquete(indice)]
    md += ["### 2.2.2 Análisis de caso de uso\n", "#### 2.2.2.1 Diagrama de comunicación\n",
           "Cada caso de uso se realiza con tres tipos de clase: de **interfaz** (frontera con el actor), de **control** "
           "(coordina el caso de uso) y de **entidad** (información de larga vida). Los mensajes llevan el orden en que ocurren.\n"]
    for numero, _, _, codigos in CICLOS:
        md.append(f"##### Ciclo de vida #{numero}\n")
        for cu in codigos:
            md += [f"**{cu}: {CUS[cu]['nombre']}**\n", diagrama_comunicacion(cu)]
    md += ["### 2.2.3 Análisis de clases\n"]
    for numero, _, _, codigos in CICLOS:
        md += [f"#### Ciclo de vida #{numero}\n", diagrama_clases_analisis(codigos, id_ea=f"cla-ciclo-{numero}")]
    md += ["### 2.2.4 Análisis de paquete\n", diagrama_dependencias_paquetes()]
    return "\n".join(md)


def parte_diseno():
    md = ["## 2.3 Flujo de trabajo: diseño\n",
          "### 2.3.1 Patrón de desarrollo C4\n",
          "#### 2.3.1.1 Diagrama de contexto del sistema\n", uml(C4_CONTEXTO, estilo=False),
          "#### 2.3.1.2 Diagrama de contenedor\n", uml(C4_CONTENEDORES, estilo=False),
          "#### 2.3.1.3 Diagrama de componentes\n", uml(C4_COMPONENTES, estilo=False),
          "#### 2.3.1.4 Diagrama de código\n", uml(CODIGO, id_ea="codigo"),
          "### 2.3.2 Diseño de la arquitectura\n",
          "#### 2.3.2.1 Diseño físico (diagrama de despliegue)\n", uml(DESPLIEGUE, id_ea="despliegue"),
          "#### 2.3.2.2 Diseño lógico (diagrama de paquetes organizado en capas)\n", uml(CAPAS, id_ea="capas"),
          "#### 2.3.2.3 Diseño de datos\n",
          "El modelo de datos persistente es pequeño: el diagrama lo guarda como una copia JSON por sala y "
          "la IA y la colaboración añaden cuatro tablas. Lo efímero (orden de conexión y presencia) vive en Redis.\n",
          uml(MODELO_DATOS, id_ea="datos"), "**Tablas de volumen**\n"]
    for nombre, descripcion, filas in TABLAS:
        md += [f"**{nombre}**: {descripcion}.\n",
               "| Atributo | Tipo de dato | Descripción | Tamaño | Nulo | Clave |", "|---|---|---|---|---|---|"]
        md += [f"| {a} | {t} | {d} | {s} | {n} | {k} |" for a, t, d, s, n, k in filas]
        md.append("")
    md += ["**Script de creación (PostgreSQL)**\n", "```sql\n" + DDL + "\n```\n",
           "### 2.3.3 Diagrama de secuencia\n"]
    for numero, _, _, codigos in CICLOS:
        md.append(f"#### Ciclo de vida #{numero}\n")
        for cu in codigos:
            md += [f"**{cu}: {CUS[cu]['nombre']}**\n", diagrama_secuencia(cu)]
    return "\n".join(md)


def parte_implementacion():
    return "\n".join([
        "## 2.4 Flujo de trabajo: implementación\n",
        "### 2.4.1 Diagrama de componentes\n", uml(COMPONENTES, id_ea="componentes"),
        "### 2.4.2 Diagrama de subsistemas\n", uml(SUBSISTEMAS, id_ea="subsistemas"),
    ])


def generar():
    return parte_requisitos() + "\n" + parte_analisis() + "\n" + parte_diseno() + "\n" + parte_implementacion()
