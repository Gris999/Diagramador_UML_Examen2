"""Flujo de diseño (PUDS, capítulo 9): arquitectura, subsistemas con interfaces, clases de diseño y datos.

Reglas que se siguen (Jacobson, Booch y Rumbaugh, cap. 9):

  * el diseño identifica nodos y su configuración de red, subsistemas e interfaces, clases activas y mecanismos genéricos (9.5.1);
  * los subsistemas de las capas superiores se obtienen de los paquetes del análisis, con una traza a cada uno (9.5.1.2.1); el software
    del sistema y la capa intermedia se tratan como subsistemas con interfaces explícitas (9.5.1.2.2);
  * una clase de diseño usa el lenguaje de programación y la misma sintaxis, con visibilidad, atributos tipados y operaciones que son
    los métodos del código (9.3.2): aquí los nombres no se escriben a mano, se comprueban contra el código (`modelo/codigo.py`);
  * una realización de caso de uso–diseño tiene una traza a su realización de análisis, el flujo de eventos del diseño, un diagrama de
    clases con las clases participantes y diagramas de secuencia por escenario (9.3.3); está en `modelo/realizaciones.py`.

Los cambios C1 a C4 de este parcial se diseñan primero: sus clases llevan `nuevo=True` y el validador no exige que existan en el código
hasta que se programan (`validar(..., exigir_nuevos=True)`).
"""

from modelo import codigo as C

F = "front_generador_bd/src/"
B = "back_generador_bd/"
J = "back_generator_uml/src/main/java/generator_uml/back_generator_uml/"


def _o(sub, archivo, clase, nuevo=False, ops=None, rotulo=None, est=None):
    """Clase de diseño que participa en alguna realización. `ops`: operaciones del módulo que corresponden a este subsistema."""
    return dict(sub=sub, archivo=archivo, clase=clase, nuevo=nuevo, ops=ops, rotulo=rotulo or clase.strip("<>").replace(".py", ""), est=est)


# ---- clases de diseño (clave -> archivo y clase del código) ------------------------------------------------
OBJETOS = {
    # núcleo de la sala
    "Participant": _o("nucleo", B + "collab/models.py", "Participant", est="entity"),
    "ActivityEvent": _o("nucleo", B + "collab/models.py", "ActivityEvent", est="entity"),
    "RedisGroupRoleStore": _o("nucleo", B + "collab/roles.py", "RedisGroupRoleStore"),
    "RedisGroupIdentityStore": _o("nucleo", B + "collab/identity.py", "RedisGroupIdentityStore"),
    "groups": _o("nucleo", B + "collab/groups.py", "<groups.py>", rotulo="groups", est="module"),
    "IdentityService": _o("nucleo", F + "services/colaboration/identity.service.ts", "IdentityService"),
    # edición del diagrama
    "Diagram": _o("carcasa", F + "app/diagram/diagram.ts", "Diagram"),
    "DiagramService": _o("edicion", F + "services/diagram/diagram.service.ts", "DiagramService"),
    "EditionService": _o("edicion", F + "services/diagram/edition.service.ts", "EditionService"),
    "RelationshipService": _o("edicion", F + "services/diagram/relationship.service.ts", "RelationshipService"),
    "CollaborationService": _o("edicion", F + "services/colaboration/collaboration.service.ts", "CollaborationService"),
    "P2PService": _o("edicion", F + "services/colaboration/p2p.service.ts", "P2PService"),
    "SignalingService": _o("edicion", F + "services/colaboration/signaling.service.ts", "SignalingService"),
    "RemoteApplicationService": _o("edicion", F + "services/colaboration/remote-application.service.ts", "RemoteApplicationService"),
    "BackupService": _o("edicion", F + "services/exports/backup.service.ts", "BackupService"),
    "CanvasConsumer": _o("edicion", B + "collab/consumers.py", "CanvasConsumer", est="active"),
    "BackupUML": _o("edicion", B + "uml_api/models.py", "BackupUML", est="entity"),
    "vistas_respaldo": _o("edicion", B + "uml_api/views.py", "<views.py>", ops=["set_backupUML", "get_backupUML"], rotulo="views (respaldo)",
                          est="module"),
    # actividad del equipo y seguimiento móvil
    "ActivityPanel": _o("actividad", F + "app/activity-panel/activity-panel.ts", "ActivityPanel"),
    "ORMActivityStore": _o("nucleo", B + "collab/activity.py", "ORMActivityStore"),
    "activity": _o("nucleo", B + "collab/activity.py", "<activity.py>", rotulo="activity", est="module"),
    "vistas_actividad": _o("actividad", B + "uml_api/views.py", "<views.py>", ops=["get_room_activity"], rotulo="views (actividad)", est="module"),
    "FollowView": _o("seguimiento", F + "app/follow-view/follow-view.ts", "FollowView"),
    "NotificationService": _o("seguimiento", F + "services/colaboration/notification.service.ts", "NotificationService", nuevo=True),
    # asistencia inteligente
    "IaChatPanel": _o("ia", F + "app/ia-chat-panel/ia-chat-panel.ts", "IaChatPanel"),
    "SidePanel": _o("carcasa", F + "app/side-panel/side-panel.ts", "SidePanel"),
    "IaChatService": _o("ia", F + "services/IA/ia-chat.service.ts", "IaChatService"),
    "IaActionsService": _o("ia", F + "services/IA/ia-actions.service.ts", "IaActionsService"),
    "ChatbotService": _o("ia", F + "services/IA/chatbot.service.ts", "ChatbotService"),
    "UmlImageServiceTs": _o("ia", F + "services/imports/uml-image.service.ts", "UmlImageServiceTs"),
    "chat_views": _o("ia", B + "uml_api/chat_views.py", "<chat_views.py>", rotulo="chat_views", est="module"),
    "ia_context": _o("ia", B + "uml_api/services/ia_context.py", "<ia_context.py>", rotulo="ia_context", est="module"),
    "change_guard": _o("ia", B + "uml_api/services/change_guard.py", "<change_guard.py>", rotulo="change_guard", est="module"),
    "ai_provider": _o("ia", B + "uml_api/services/ai_provider.py", "<ai_provider.py>", rotulo="ai_provider", est="module"),
    "AIProvider": _o("ia", B + "uml_api/services/ai_provider.py", "AIProvider", est="interface"),
    "GeminiProvider": _o("ia", B + "uml_api/services/ai_provider.py", "GeminiProvider"),
    "OllamaProvider": _o("ia", B + "uml_api/services/ai_provider.py", "OllamaProvider"),
    "services_gemini": _o("ia", B + "uml_api/services/services_gemini.py", "<services_gemini.py>", rotulo="services_gemini", est="module"),
    "ChatMessage": _o("ia", B + "collab/models.py", "ChatMessage", est="entity"),
    "IaAttempt": _o("ia", B + "collab/models.py", "IaAttempt", est="entity"),
    "vistas_ia": _o("ia", B + "uml_api/views.py", "<views.py>", ops=["analyze_uml_image", "analyze_uml_audio"], rotulo="views (IA)", est="module"),
    "UMLConsumer": _o("ia", B + "collab/consumers.py", "UMLConsumer", est="active"),
    # asistente de ayuda (C4)
    "HelpPanel": _o("ayuda", F + "app/help-panel/help-panel.ts", "HelpPanel", nuevo=True),
    "HelpService": _o("ayuda", F + "services/IA/help.service.ts", "HelpService", nuevo=True),
    "help_views": _o("ayuda", B + "uml_api/help_views.py", "<help_views.py>", nuevo=True, rotulo="help_views", est="module"),
    "help_knowledge": _o("ayuda", B + "uml_api/services/help_knowledge.py", "<help_knowledge.py>", nuevo=True, rotulo="help_knowledge", est="module"),
    "RedisRateLimiter": _o("ayuda", B + "collab/limits.py", "RedisRateLimiter", nuevo=True),
    # puertos y adaptadores de la conversación y la actividad (C1, C3)
    "ConversationStore": _o("ia", B + "collab/ports.py", "ConversationStore", est="interface"),
    "ActivityStore": _o("nucleo", B + "collab/ports.py", "ActivityStore", nuevo=True, est="interface"),
    "TurnStore": _o("ia", B + "collab/ports.py", "TurnStore", est="interface"),
    "ORMConversationStore": _o("ia", B + "collab/conversation.py", "ORMConversationStore"),
    "MongoConversationStore": _o("ia", B + "collab/mongo_stores.py", "MongoConversationStore", nuevo=True),
    "MongoActivityStore": _o("nucleo", B + "collab/mongo_stores.py", "MongoActivityStore", nuevo=True),
    "RedisTurnStore": _o("ia", B + "collab/turn.py", "RedisTurnStore"),
    "stores": _o("ia", B + "collab/stores.py", "<stores.py>", rotulo="stores", est="module"),
    # intercambio y generación
    "XmiService": _o("intercambio", F + "services/interop/xmi.service.ts", "XmiService"),
    "DiagramExportService": _o("intercambio", F + "services/exports/diagram-export.service.ts", "DiagramExportService"),
    "FrontendGeneratorService": _o("intercambio", F + "services/exports/frontend-generator.service.ts", "FrontendGeneratorService"),
    "BackendGeneratorService": _o("intercambio", F + "services/exports/backend-generator.service.ts", "BackendGeneratorService"),
    "SqlExportService": _o("intercambio", F + "services/exports/sql-export.service.ts", "SqlExportService"),
    "vistas_intercambio": _o("intercambio", B + "uml_api/views.py", "<views.py>", ops=["export_xmi", "import_xmi", "generar_flutter"],
                             rotulo="views (intercambio)", est="module"),
    "xmi_service": _o("intercambio", B + "uml_api/services/xmi_service.py", "<xmi_service.py>", rotulo="xmi_service", est="module"),
    "FlutterCRUDGenerator": _o("intercambio", B + "uml_api/services/flutter_generator.py", "FlutterCRUDGenerator"),
    "GenerateController": _o("intercambio", J + "controller/GenerateController.java", "GenerateController"),
    "ProjectGenerator": _o("intercambio", J + "service/ProjectGenerator.java", "ProjectGenerator"),
    "PostmanCollectionGenerator": _o("intercambio", J + "service/PostmanCollectionGenerator.java", "PostmanCollectionGenerator"),
    # gestión de la sala
    "LandinPage": _o("gestion", F + "app/landin-page/landin-page.ts", "LandinPage"),
    "ParticipantsPanel": _o("gestion", F + "app/participants-panel/participants-panel.ts", "ParticipantsPanel"),
}
for _k, _v in OBJETOS.items():
    _v["clave"] = _k

# ---- subsistemas de diseño (traza a los paquetes del análisis, 9.5.1.2.1) --------------------------------------
# capa: específica | general | intermedia | sistema. traza: paquete del análisis. servicio: subsistema de servicio.
SUBSISTEMAS = [
    dict(id="carcasa", nombre="Carcasa del editor", capa="específica", traza=None, servicio=False, lenguajes="TypeScript (Angular)"),
    dict(id="gestion", nombre="Gestión de la sala", capa="específica", traza="gestion", servicio=False,
         lenguajes="TypeScript (Angular) y Python (Channels)"),
    dict(id="actividad", nombre="Actividad del equipo", capa="específica", traza="actividad", servicio=False, lenguajes="TypeScript y Python"),
    dict(id="seguimiento", nombre="Seguimiento móvil", capa="específica", traza="seguimiento", servicio=True, lenguajes="TypeScript y Python"),
    dict(id="ia", nombre="Asistencia inteligente", capa="específica", traza="ia", servicio=False, lenguajes="TypeScript y Python"),
    dict(id="ayuda", nombre="Asistente de ayuda", capa="específica", traza="ayuda", servicio=True, lenguajes="TypeScript y Python"),
    dict(id="intercambio", nombre="Intercambio y generación", capa="específica", traza="intercambio", servicio=False,
         lenguajes="TypeScript, Python y Java"),
    dict(id="edicion", nombre="Edición del diagrama", capa="general", traza="edicion", servicio=False, lenguajes="TypeScript y Python"),
    dict(id="nucleo", nombre="Núcleo de la sala", capa="general", traza="nucleo", servicio=False, lenguajes="TypeScript y Python"),
]
NOMBRE_SUBSISTEMA = {s["id"]: s["nombre"] for s in SUBSISTEMAS}

# La carcasa del editor no sale de un paquete del análisis: es el componente de Angular (`Diagram`) y su panel lateral (`SidePanel`) que reúnen los botones y los
# paneles de varios subsistemas. Es la decisión de diseño que permite el libro (9.5.1.2.1: refinar los subsistemas «para tratar temas relativos al diseño, la
# implementación y la distribución»): depende de todos y nadie depende de ella; las clases de interfaz del análisis que muestra (el lienzo y los paneles
# de generar, importar, exportar y generar proyectos) se realizan en ella.

# Capas intermedia y de software del sistema: productos reutilizados que se encapsulan como subsistemas con interfaz explícita (9.5.1.2.2).
SOFTWARE_DEL_SISTEMA = [
    ("Angular 20 con JointJS", "intermedia", "Navegador", "Marco de la interfaz web y biblioteca de diagramas", "TypeScript"),
    ("Django 5, Django REST Framework y Channels (Daphne)", "intermedia", "django_backend_UML",
     "Vistas REST y consumidores WebSocket asíncronos", "Python"),
    ("Spring Boot 3.5 (Java 21)", "intermedia", "spring_backend", "Generador del proyecto del backend", "Java"),
    ("PostgreSQL 16", "sistema", "postgres_db", "Datos relacionales: participantes, topes de uso, respaldo del diagrama", "SQL"),
    ("Redis 7", "sistema", "redis_server", "Estado efímero de la sala (orden de quienes están) y canal de difusión", "—"),
    ("MongoDB 7", "sistema", "mongo_db", "Documentos que solo se agregan: conversación con la IA y actividad (C3)", "—"),
    ("Google Gemini API", "sistema", "Nube de Google", "Servicio de IA (actor externo A3)", "HTTPS"),
    ("Ollama con el modelo Qwen reentrenado", "sistema", "Equipo propio", "Servicio de IA local opcional (actor externo A3)", "HTTP"),
]

# ---- interfaces entre subsistemas (9.5.1.2.4) ---------------------------------------------------------------------
# Cada interfaz la proporciona un subsistema y la realizan una o más clases; `operaciones` son las del código (se comprueban).
INTERFACES = [
    dict(nombre="RoleStore", sub="nucleo", realiza=["RedisGroupRoleStore"], operaciones=["join", "members", "leave", "remove_by_host"],
         motivo="Quién está en la sala y en qué orden (el primero es el host); reemplazable sin tocar al consumidor."),
    dict(nombre="IdentityStore", sub="nucleo", realiza=["RedisGroupIdentityStore"], operaciones=["set", "names", "delete"],
         motivo="Nombre visible de cada conexión mientras la sala está viva."),
    dict(nombre="DiagramApi", sub="edicion", realiza=["DiagramService"], operaciones=["getGraph", "getJoint", "createUmlClass", "loadFromJson", "exportToJson"],
         archivo=F + "services/colaboration/diagram-api.ts", clase="DiagramApi",
         motivo="Lo que la colaboración necesita del diagrama; evita que el servicio de colaboración dependa del servicio del diagrama."),
    dict(nombre="ActivityStore", sub="nucleo", realiza=["ORMActivityStore", "MongoActivityStore"], operaciones=["identify", "record", "recent", "get", "update_data"],
         motivo="Guardar y leer la actividad de la sala; PostgreSQL hoy, MongoDB en C3, elegidos con una variable de entorno.", nuevo=True),
    dict(nombre="AIProvider", sub="ia", realiza=["GeminiProvider", "OllamaProvider"], operaciones=["chat", "change"],
         motivo="Servicio de IA intercambiable (nube o local) sin que el resto lo note."),
    dict(nombre="ConversationStore", sub="ia", realiza=["ORMConversationStore", "MongoConversationStore"], operaciones=["append_exchange", "history", "discard_exchange"],
         motivo="La conversación única de la sala con la IA (C1); PostgreSQL o MongoDB (C3).", nuevo=True),
    dict(nombre="TurnStore", sub="ia", realiza=["RedisTurnStore"], operaciones=["take", "release", "current"],
         motivo="Un solo pedido a la IA a la vez por sala (C1).", nuevo=True),
    dict(nombre="RateLimiter", sub="ayuda", realiza=["RedisRateLimiter"], operaciones=["allow"],
         motivo="Tope de uso del asistente de ayuda por persona y para todo el servicio (C4).", nuevo=True),
]

# Dependencias entre subsistemas: las mismas que entre paquetes del análisis (se comprueba en `validar`).

# ---- asociaciones entre clases de diseño (9.3.2: las asociaciones se corresponden con variables o referencias en el código) ----------------------
# (origen, destino, etiqueta[, cambio]). Con `cambio` la asociación la agrega ese cambio y no se comprueba todavía. `validar` comprueba que el código de la clase de origen nombra a la de destino (inyección, atributo o importación).
ASOCIACIONES = [
    ("Diagram", "DiagramService", "inyecta"), ("Diagram", "XmiService", "inyecta"), ("Diagram", "DiagramExportService", "inyecta"),
    ("Diagram", "BackendGeneratorService", "inyecta"), ("Diagram", "P2PService", "inyecta"),
    ("SidePanel", "DiagramService", "inyecta"), ("SidePanel", "SqlExportService", "inyecta"), ("SidePanel", "FrontendGeneratorService", "inyecta"),
    ("SidePanel", "ChatbotService", "inyecta"), ("SidePanel", "UmlImageServiceTs", "inyecta"), ("SidePanel", "IaActionsService", "inyecta", "C1"),
    ("DiagramService", "CollaborationService", "inyecta"), ("DiagramService", "BackupService", "inyecta"), ("DiagramService", "EditionService", "inyecta"),
    ("RelationshipService", "DiagramService", "inyecta"),
    ("CollaborationService", "P2PService", "inyecta"), ("CollaborationService", "BackupService", "inyecta"),
    ("P2PService", "SignalingService", "inyecta"), ("SignalingService", "IdentityService", "inyecta"),
    ("IaActionsService", "IaChatService", "inyecta"), ("IaActionsService", "DiagramService", "inyecta"),
    ("IaActionsService", "CollaborationService", "inyecta"), ("IaActionsService", "IdentityService", "inyecta"),
    ("IaChatService", "IdentityService", "inyecta"), ("IaChatPanel", "IaActionsService", "inyecta"), ("IaChatPanel", "IaChatService", "inyecta"),
    ("ActivityPanel", "IaActionsService", "inyecta"), ("ActivityPanel", "P2PService", "inyecta"),
    ("FollowView", "DiagramService", "inyecta"), ("FollowView", "CollaborationService", "inyecta"),
    ("FollowView", "P2PService", "inyecta", "C2"), ("FollowView", "NotificationService", "inyecta", "C2"),
    ("ParticipantsPanel", "P2PService", "inyecta"), ("ParticipantsPanel", "CollaborationService", "inyecta"),
    ("HelpPanel", "HelpService", "inyecta"),
    ("CanvasConsumer", "RedisGroupRoleStore", "usa (role_store_class)"), ("CanvasConsumer", "RedisGroupIdentityStore", "usa (identity_store_class)"),
    ("CanvasConsumer", "ORMActivityStore", "usa (activity_store_class)"), ("CanvasConsumer", "groups", "importa"),
    ("ORMActivityStore", "Participant", "importa"), ("ORMActivityStore", "ActivityEvent", "importa"),
    ("chat_views", "Participant", "importa"), ("chat_views", "ActivityEvent", "importa"), ("chat_views", "IaAttempt", "importa"), ("chat_views", "ai_provider", "importa"), ("chat_views", "change_guard", "importa"),
    ("chat_views", "ia_context", "importa"), ("chat_views", "activity", "importa"), ("chat_views", "groups", "importa"),
    ("GeminiProvider", "AIProvider", "hereda de"), ("OllamaProvider", "AIProvider", "hereda de"),
    ("ai_provider", "GeminiProvider", "crea"), ("ai_provider", "OllamaProvider", "crea"),
    ("vistas_respaldo", "BackupUML", "importa"), ("vistas_actividad", "ActivityEvent", "importa"), ("vistas_actividad", "activity", "importa"),
    ("vistas_intercambio", "xmi_service", "importa"), ("vistas_intercambio", "FlutterCRUDGenerator", "importa"),
    ("vistas_ia", "services_gemini", "importa"),
    ("GenerateController", "ProjectGenerator", "inyecta"), ("ProjectGenerator", "PostmanCollectionGenerator", "usa"),
    # clases nuevas (C1 a C4): no se comprueban hasta que existan
    ("CanvasConsumer", "ActivityStore", "usa"), ("ORMActivityStore", "ActivityStore", "realiza"), ("MongoActivityStore", "ActivityStore", "realiza"),
    ("chat_views", "stores", "importa"), ("chat_views", "ActivityStore", "usa"),
    ("ORMConversationStore", "ConversationStore", "realiza"), ("MongoConversationStore", "ConversationStore", "realiza"),
    ("RedisTurnStore", "TurnStore", "realiza"), ("stores", "ActivityStore", "crea"), ("stores", "ConversationStore", "crea"), ("stores", "TurnStore", "crea"),
    ("help_views", "RedisRateLimiter", "usa"), ("help_views", "help_knowledge", "importa"), ("help_views", "AIProvider", "usa"),
    ("HelpService", "help_views", "llama a"),
]

# ---- clases activas (9.5.1.3.2) ----------------------------------------------------------------------------
ACTIVAS = [
    ("CanvasConsumer", "Una por conexión WebSocket de la sala: recibe operaciones, presencia y expulsiones y las difunde al grupo de Redis. "
                       "Corre como corrutina en el único bucle de eventos de Daphne; por eso no bloquea (la IA y la base de datos se llaman con "
                       "hilos auxiliares)."),
    ("UMLConsumer", "Una por conexión de validación del modelo: junta una ráfaga de pedidos en dos validaciones como máximo y llama a la IA en un hilo "
                    "(`asyncio.to_thread`) para no congelar el bucle."),
    ("ValidationBudget", "Estado compartido del tope de validaciones con IA (3 simultáneas y 20 por minuto en todo el servicio)."),
]

# ---- mecanismos genéricos de diseño (9.5.1.4): cómo se resuelven los requisitos especiales comunes del análisis ---
MECANISMOS = [
    ("REC-1", "Persistencia", "Puertos y adaptadores",
     "La actividad y la conversación se guardan detrás de los puertos ActivityStore y ConversationStore: el adaptador de PostgreSQL (Django ORM) o el "
     "de MongoDB se elige con las variables ACTIVITY_STORE y CONVERSATION_STORE. El respaldo del diagrama y los topes de uso siguen en PostgreSQL. "
     "El diagrama se respalda 1,5 s después de la última edición (`DiagramService.AUTOSAVE_DEBOUNCE_MS`).",
     ["ORMActivityStore", "MongoActivityStore", "ORMConversationStore", "MongoConversationStore", "BackupUML"]),
    ("REC-2", "Distribución y concurrencia", "Difusión por grupos de Redis y turno por sala",
     "Cada sala es un grupo de canales (`room_group_name`); las operaciones viajan por WebSocket y el orden de quienes están lo da un conjunto "
     "ordenado de Redis (el primero es el host). La IA atiende un pedido a la vez por sala con un cerrojo de Redis con vencimiento (TurnStore).",
     ["CanvasConsumer", "RedisGroupRoleStore", "RedisTurnStore", "groups"]),
    ("REC-3", "Seguridad", "Autorización en el servidor y entrada no confiable",
     "Expulsar se decide en un guion atómico de Redis que comprueba que quien pide es el host. El XMI se lee sin DOCTYPE ni entidades externas. "
     "A las rutas de una sala solo entra quien se identificó con su token anónimo (`X-Participant-Token`).",
     ["RedisGroupRoleStore", "xmi_service", "chat_views"]),
    ("REC-4", "Tolerancia a fallos", "Fallar sin romper la edición",
     "El registro de actividad y la identidad se envuelven en `try/except`: si fallan, la edición sigue. Una respuesta inválida o un fallo del proveedor "
     "de IA devuelve un mensaje claro y no cambia el diagrama (`AIProviderError`, `validate_changes`).",
     ["CanvasConsumer", "change_guard", "ai_provider"]),
    ("REC-5", "Costo y límites de uso", "Topes que se reservan antes de gastar",
     "`_reserve_attempt` inserta el pedido y cuenta después, con topes por persona, por sala y para todo el servicio; el asistente de ayuda usa "
     "RateLimiter. Hay tamaños máximos de mensaje, de contexto y de cambio (`MAX_MESSAGE_CHARS`, `MAX_UML_CHARS`, `MAX_CLASSES_PER_CHANGE`).",
     ["chat_views", "IaAttempt", "RedisRateLimiter", "ia_context", "change_guard"]),
    ("RA-01", "IA local intercambiable", "Proveedor detrás de un puerto",
     "`get_ai_provider()` entrega GeminiProvider u OllamaProvider según la variable AI_PROVIDER; ambos cumplen AIProvider.",
     ["AIProvider", "GeminiProvider", "OllamaProvider", "ai_provider"]),
]

# ---- traza de las clases del análisis a las de diseño (9.3.3 y 9.5.1.3.1) ----------------------------------------
# clase del análisis -> [(clave de la clase de diseño, [operaciones relevantes]), ...]
TRAZA = {
    "Sala": [("groups", ["room_group_name", "viewers_group_name"])],
    "Participante": [("Participant", []), ("RedisGroupRoleStore", ["join", "members"]), ("RedisGroupIdentityStore", ["set", "names"]),
                     ("IdentityService", ["getIdentity"])],
    "EventoActividad": [("ActivityEvent", []), ("MongoActivityStore", ["record"])],
    "Lienzo": [("Diagram", ["ngAfterViewInit", "onDragEnded"])],
    "ControlModelado": [("DiagramService", ["createUmlClass", "createTypedRelationship", "loadFromJson"]),
                        ("EditionService", ["scheduleAutoResize"]), ("RelationshipService", ["createTypedRelationship"])],
    "ControlSincronizacion": [("CollaborationService", ["init", "broadcast"]), ("P2PService", ["sendToAll"]), ("SignalingService", ["broadcast"]),
                              ("RemoteApplicationService", []), ("CanvasConsumer", ["receive"])],
    "Diagrama": [("DiagramService", ["exportToJson", "loadFromJson"]), ("DiagramExportService", ["export"])],
    "ClaseUML": [("DiagramService", ["createUmlClass"]), ("DiagramExportService", ["parseAttributesFromText", "parseMethodsFromText"])],
    "RelacionUML": [("RelationshipService", ["createTypedRelationship"]), ("DiagramService", ["buildRelationship"])],
    "OperacionEdicion": [("CollaborationService", ["broadcast", "applyRemoteOp"])],
    "RespaldoDiagrama": [("BackupUML", []), ("BackupService", ["setBackupUml", "getBackup"]), ("vistas_respaldo", ["set_backupUML", "get_backupUML"])],
    "PanelActividad": [("ActivityPanel", ["ngOnInit", "apply"])],
    "ControlActividad": [("CanvasConsumer", ["_record_activity"]), ("ORMActivityStore", ["record"]), ("vistas_actividad", ["get_room_activity"]),
                         ("activity", ["serialize_activity_event"])],
    "VistaSeguimiento": [("FollowView", ["ngAfterViewInit"]), ("NotificationService", ["requestPermission", "notifyChange", "notifyIdea"])],
    "ControlSeguimiento": [("CanvasConsumer", ["_connect_viewer", "_allow_viewer_state_request"])],
    "PanelChatIA": [("IaChatPanel", ["send", "loadHistory"])],
    "PanelGenerarModelo": [("SidePanel", ["onGenerate", "toggleVoiceInput"])],
    "PanelImportacionImagen": [("SidePanel", ["onImportImage", "replaceImageImport", "mergeImageImport"])],
    "InterfazServicioIA": [("AIProvider", ["chat", "change"]), ("GeminiProvider", []), ("OllamaProvider", []), ("services_gemini", [])],
    "ControlIA": [("chat_views", ["ia_chat", "claim_suggestion"]), ("ia_context", ["build_chat_prompt"]), ("change_guard", ["validate_changes"]),
                  ("IaChatService", ["send"]), ("IaActionsService", ["request", "applySuggestion"])],
    "ControlImportacionImagen": [("vistas_ia", ["analyze_uml_image"]), ("UmlImageServiceTs", ["analyzeImage"])],
    "ConversacionSala": [("ChatMessage", []), ("ORMConversationStore", ["history", "append_exchange"]),
                         ("MongoConversationStore", ["history", "append_exchange"]), ("RedisTurnStore", ["take", "release"])],
    "MensajeConversacion": [("ChatMessage", [])],
    "IdeaRevision": [("ActivityEvent", []), ("chat_views", ["claim_suggestion"])],
    "PedidoIA": [("IaAttempt", [])],
    "CambioPropuesto": [("change_guard", ["validate_changes", "count_destructive"])],
    "ModeloReconocido": [("vistas_ia", ["analyze_uml_image"])],
    "PanelAyuda": [("HelpPanel", ["send"])],
    "ControlAyuda": [("help_views", ["ia_help"]), ("HelpService", ["ask"])],
    "ConocimientoAyuda": [("help_knowledge", ["load_knowledge", "build_help_prompt"])],
    "PanelIntercambio": [("SidePanel", ["exportImage"]), ("Diagram", ["exportXmi", "importXmi"])],
    "PanelGeneracion": [("SidePanel", ["onGenerateFrontend", "exportSql"]), ("Diagram", ["saveDiagram"]), ("FrontendGeneratorService", ["generateFrontend"])],
    "ControlIntercambio": [("XmiService", ["exportXmi", "importXmi"]), ("vistas_intercambio", ["export_xmi", "import_xmi"]),
                           ("xmi_service", ["export_uml_to_xmi", "import_xmi_to_uml"])],
    "ControlGeneracion": [("BackendGeneratorService", ["generateBackend"]), ("SqlExportService", ["exportToSql"]),
                          ("vistas_intercambio", ["generar_flutter"]), ("GenerateController", ["generate"])],
    "ArchivoIntercambio": [("xmi_service", ["export_uml_to_xmi", "import_xmi_to_uml"])],
    "ProyectoGenerado": [("ProjectGenerator", ["generate"]), ("FlutterCRUDGenerator", ["generate_project"])],
    "PantallaInicio": [("LandinPage", ["crearNuevoLienzo", "unirseAlLienzo"]), ("IdentityService", ["getIdentity"])],
    "PanelParticipantes": [("ParticipantsPanel", ["remove", "isCurrent"])],
    "ControlIngreso": [("CanvasConsumer", ["connect", "_handle_hello"]), ("RedisGroupRoleStore", ["join"]), ("ORMActivityStore", ["identify"])],
    "ControlExpulsion": [("P2PService", ["removeParticipant"]), ("SignalingService", ["removeParticipant"]), ("CanvasConsumer", ["receive", "force_disconnect"]),
                         ("RedisGroupRoleStore", ["remove_by_host"])],
    "ControlRecuperacion": [("Diagram", ["ngAfterViewInit"]), ("CollaborationService", ["init"]), ("BackupService", ["getBackup"]),
                            ("ActivityPanel", ["ngOnInit"]), ("IaChatPanel", ["loadHistory"])],
}

# ---- cambios de este parcial, diseñados antes de programarse -----------------------------------------------------
CAMBIOS = [
    dict(id="C1", nombre="Conversación única de la sala con la IA", casos=["CU7", "CU9"], rf="RF-26, RNF-04",
         motivo="Hoy cada participante tiene su chat privado (`chat_history` y `_answer` filtran por participante) y «Generar modelo» llega a la IA por una ruta "
                "antigua (`ChatbotService.generateDiagram` → `GenerateUMLView`) que no pasa por los topes, ni por el contexto de la sala, ni por la actividad. El "
                "docente pidió una sola instancia de IA y una conversación de la sala, y el caso de uso CU7 dice que todo pedido pasa por el control de IA.",
         nuevas=["ConversationStore", "ORMConversationStore", "TurnStore", "RedisTurnStore", "stores"],
         cambian=["chat_views", "ChatMessage", "IaChatPanel", "IaChatService", "IaActionsService", "Diagram", "SidePanel"],
         decisiones=["`ChatMessage` guarda `author_name` y el historial de `_answer` y de `chat_history` es el de la sala, no el de un participante.",
                     "`ia_chat` toma el turno de la sala con `TurnStore.take` y responde 409 «La IA está atendiendo a X» si ya hay un pedido en curso; lo libera siempre "
                     "(`release`), también si el proveedor falla. El turno vence solo a los 130 s.",
                     "«Generar modelo», con texto o con voz, usa `IaActionsService.request(roomId, 'change', texto)`: la voz solo transcribe "
                     "(`analyze_uml_audio` con `transcribe_only`) y la instrucción sigue el mismo camino que el chat. Así toda acción de la IA queda en la conversación y en la actividad.",
                     "`Diagram.generateFromPrompt` desaparece (solo reenviaba): `SidePanel.onGenerate` llama directamente a `IaActionsService.request`. "
                     "`IaChatPanel` muestra el autor de cada pregunta y recibe los mensajes nuevos de los demás al abrir y al responder."],
         pruebas=["El historial de una sala trae las preguntas de todos y el autor de cada una.",
                  "Dos pedidos simultáneos a la misma sala: uno se atiende y el otro recibe 409; el turno se libera si el proveedor falla.",
                  "«Generar modelo» llama a `ia_chat` en modo `change` y registra «IA, a pedido de X»."]),
    dict(id="C2", nombre="Avisos en la vista del celular", casos=["CU13"], rf="RF-32",
         motivo="El docente quiere que el celular sea informativo y avise de lo que pasa; hoy `FollowView` solo muestra el diagrama y no pide permiso de avisos.",
         nuevas=["NotificationService"], cambian=["FollowView"],
         decisiones=["`NotificationService` usa la API de notificaciones del navegador (`Notification.requestPermission`) y solo avisa con la página abierta.",
                     "`FollowView` pide el permiso con un botón (no al cargar) y notifica cuando llega un evento de actividad nuevo de otra persona o de la IA "
                     "(`P2PService.liveActivityEvents`): «Ana añadió una clase» o «La IA publicó una revisión con 3 ideas».",
                     "No hay servidor de avisos ni suscripción push: es solo lectura y sin cuenta."],
         pruebas=["Sin permiso concedido no se crea ninguna notificación.",
                  "Con permiso, un evento nuevo de otro autor crea una notificación y uno propio no."]),
    dict(id="C3", nombre="MongoDB para la conversación y la actividad", casos=["CU5", "CU6", "CU9"], rf="RNF-03",
         motivo="La conversación y la actividad son documentos que solo se agregan, con un `data` que cambia según el tipo, y se consultan por sala y por tiempo: encajan en una "
                "base documental. El ingeniero pidió una base NoSQL. PostgreSQL conserva lo relacional y Redis lo efímero.",
         nuevas=["ActivityStore", "MongoActivityStore", "MongoConversationStore", "stores"], cambian=["ORMActivityStore", "CanvasConsumer", "chat_views", "vistas_actividad"],
         decisiones=["`ActivityStore` y `ConversationStore` son los puertos; `ORMActivityStore` y `ORMConversationStore` (PostgreSQL) y `MongoActivityStore` y "
                     "`MongoConversationStore` (MongoDB) son los adaptadores; `stores.get_activity_store()` y `get_conversation_store()` eligen con ACTIVITY_STORE y "
                     "CONVERSATION_STORE (`postgres` por omisión).",
                     "Los eventos conservan su identificador entero (la API y el navegador lo usan): `MongoActivityStore` lo toma de una colección `counters` con `$inc` atómico.",
                     "`claim_suggestion` pasa a `ActivityStore.update_data(room, event_id, mutate)`: PostgreSQL con `select_for_update`, MongoDB con un campo de versión y reintento.",
                     "El servicio `mongo_db` se agrega a Docker Compose con `--wiredTigerCacheSizeGB 0.25` y volumen propio; sus credenciales van en variables de entorno.",
                     "Un comando de una sola vez (`migrar_a_mongo`) copia el historial existente; el adaptador de PostgreSQL queda como respaldo."],
         pruebas=["Los dos adaptadores de cada puerto pasan las mismas pruebas de contrato (un adaptador en memoria sirve de referencia).",
                  "Prueba de integración con un MongoDB real en Docker.",
                  "Con ACTIVITY_STORE=mongo, `CanvasConsumer` registra y `get_room_activity` lee del mismo lugar."]),
    dict(id="C4", nombre="Asistente de ayuda", casos=["CU14"], rf="DOC2P punto 3",
         motivo="El docente pidió un mecanismo para que el usuario aprenda a usar la herramienta: un asistente de IA que conozca el proyecto.",
         nuevas=["HelpPanel", "HelpService", "help_views", "help_knowledge", "RedisRateLimiter"], cambian=["ai_provider"],
         decisiones=["`POST /api/ia/help/` (`ia_help`) no depende de una sala: sirve desde la página principal. Recibe la pregunta y hasta 6 mensajes anteriores, "
                     "que guarda el navegador: la conversación es personal y no se almacena en el servidor.",
                     "`help_knowledge.load_knowledge()` lee `docs/AYUDA.md` (el manual y la lista de funciones) y `build_help_prompt` le dice a la IA que responda solo "
                     "sobre la herramienta.",
                     "Tope de uso: `RateLimiter.allow` con 6 preguntas por minuto por persona (token) y 30 por minuto en todo el servicio.",
                     "Usa el mismo `AIProvider` que el chat: nube o local según la variable de entorno."],
         pruebas=["Una pregunta fuera de tema recibe la respuesta de «solo contesto sobre la herramienta».",
                  "La séptima pregunta en un minuto recibe 429.",
                  "El manual cargado menciona las funciones que están en el menú de la aplicación."]),
]

# ---- diseño de datos ------------------------------------------------------------------------------------------
# PostgreSQL: tablas de los modelos de Django (migraciones). Marca: existe | cambia (C1) | nuevo.
TABLAS = [
    ("collab_participant", "existe", [("id", "bigint", "PK"), ("room", "varchar(64)", ""), ("token", "uuid", "único con room"),
                                      ("display_name", "varchar(40)", ""), ("created_at", "timestamptz", ""), ("last_seen", "timestamptz", "")]),
    ("collab_activityevent", "existe (solo con ACTIVITY_STORE=postgres)",
     [("id", "bigint", "PK"), ("room", "varchar(64)", "índice con created_at"), ("actor_id", "bigint", "FK a participante, nulo"),
      ("actor_name", "varchar(40)", ""), ("actor_kind", "varchar(16)", "user o ia"), ("type", "varchar(32)", ""), ("target_id", "varchar(255)", ""),
      ("summary", "varchar(255)", ""), ("data", "jsonb", ""), ("created_at", "timestamptz", "")]),
    ("collab_chatmessage", "cambia (C1)",
     [("id", "bigint", "PK"), ("room", "varchar(64)", ""), ("participant_id", "bigint", "FK a participante"), ("author_name", "varchar(40)", "nuevo en C1"),
      ("role", "varchar(8)", "user o ia"), ("mode", "varchar(8)", "ask, change o review"), ("content", "text", ""), ("created_at", "timestamptz", "")]),
    ("collab_iaattempt", "existe", [("id", "bigint", "PK"), ("room", "varchar(64)", ""), ("participant_id", "bigint", "FK a participante"),
                                    ("created_at", "timestamptz", "índice")]),
    ("uml_api_backupuml", "existe", [("id", "bigint", "PK"), ("room_id", "uuid", "único"), ("data", "jsonb", ""), ("created_at", "timestamptz", "")]),
]
# MongoDB (C3): colecciones; los documentos conservan un identificador entero por sala para no cambiar la API.
COLECCIONES = [
    ("activity_events", [("_id", "ObjectId", ""), ("id", "int", "único, de la colección counters"), ("room", "string", "índice con created_at"),
                         ("actor_id", "int", "id del participante en PostgreSQL, sin clave foránea"), ("actor_name", "string", ""), ("actor_kind", "string", ""),
                         ("type", "string", ""), ("target_id", "string", ""), ("summary", "string", ""), ("data", "document", "según el tipo"),
                         ("v", "int", "versión para actualizar `data` sin pisar a otro"), ("created_at", "date", "")]),
    ("conversation_messages", [("_id", "ObjectId", ""), ("id", "int", "único, de la colección counters"), ("room", "string", "índice con id"),
                               ("participant_id", "int", ""), ("author_name", "string", ""), ("role", "string", ""), ("mode", "string", ""),
                               ("content", "string", ""), ("created_at", "date", "")]),
    ("counters", [("_id", "string", "activity_events o conversation_messages"), ("seq", "int", "último identificador entregado")]),
]

# ---- nodos y despliegue (9.5.1.1) ---------------------------------------------------------------------------
NODOS = [
    ("Navegador del usuario", "dispositivo", "Computador de escritorio (Chrome, Safari o Edge)", "Aplicación Angular 20; WebSocket y HTTPS",
     "Cualquiera con WebSocket; el dictado exige Chrome con HTTPS"),
    ("Navegador del celular", "dispositivo", "Teléfono con navegador", "Vista de seguimiento de solo lectura y avisos (C2)", "Con la página abierta"),
    ("AWS EC2", "dispositivo", "Ubuntu 24.04, 2 vCPU y 2 GB de memoria", "nginx con Let's Encrypt y Docker Compose", "diagramador.dev; HTTPS 443"),
    ("angular_frontend", "contenedor", "Node con Angular SSR, puerto 4000 (publicado 4200)", "Sirve la aplicación", "nginx → /"),
    ("django_backend_UML", "contenedor", "Python 3 con Daphne, puerto 8000", "Vistas REST y consumidores WebSocket", "nginx → /api y /ws"),
    ("spring_backend", "contenedor", "Java 21 con Spring Boot, puerto 7001", "Generador del backend", "nginx → /generate"),
    ("postgres_db", "contenedor", "PostgreSQL, puerto 5432 (5433 en el equipo local)", "Datos relacionales", "solo desde Django"),
    ("redis_server", "contenedor", "Redis, puerto 6379", "Presencia, orden de roles y difusión", "solo desde Django"),
    ("mongo_db", "contenedor", "MongoDB con 0,25 GB de caché, puerto 27017 (C3)", "Conversación y actividad", "solo desde Django"),
    ("Google Gemini", "servicio externo", "API en la nube", "Servicio de IA (A3)", "HTTPS desde Django"),
    ("Ollama", "servicio externo", "Equipo con Apple Silicon, puerto 11434", "IA local con el modelo reentrenado (A3, opcional)", "HTTP desde Django"),
]
CONEXIONES = [
    ("Navegador del usuario", "AWS EC2", "HTTPS y WSS, puerto 443"),
    ("Navegador del celular", "AWS EC2", "HTTPS y WSS, puerto 443"),
    ("django_backend_UML", "postgres_db", "PostgreSQL (psycopg)"),
    ("django_backend_UML", "redis_server", "Redis (canales de Channels)"),
    ("django_backend_UML", "mongo_db", "MongoDB (pymongo), C3"),
    ("django_backend_UML", "spring_backend", "HTTP interno (el navegador llama a /generate por nginx)"),
    ("django_backend_UML", "Google Gemini", "HTTPS"),
    ("django_backend_UML", "Ollama", "HTTP, opcional"),
]


# ---- consultas y validación ---------------------------------------------------------------------------------
def objetos_de(sub):
    return [o for o in OBJETOS.values() if o["sub"] == sub]


def operaciones_validas(obj):
    """Operaciones (y atributos invocables) de la clase en el código, acotadas a `ops` si la clase es un módulo compartido."""
    c = C.buscar(obj["archivo"], obj["clase"])
    if c is None:
        return None
    todas = set(c["metodos"]) | set(c["atributos"])
    return todas if obj["ops"] is None else todas & set(obj["ops"])


def validar(exigir_nuevos=False, analisis=None):
    """Comprueba el diseño contra el código y contra el análisis. `analisis`: el módulo modelo.analisis."""
    errores = []
    for clave, o in OBJETOS.items():
        if o["sub"] not in NOMBRE_SUBSISTEMA:
            errores.append(f"{clave}: subsistema desconocido {o['sub']}")
        existe = C.existe(o["archivo"], o["clase"])
        if o["nuevo"]:
            if exigir_nuevos and not existe:
                errores.append(f"{clave}: está marcada como nueva y todavía no existe en {o['archivo']}")
            if existe:
                errores.append(f"{clave}: ya existe en el código; quitar `nuevo=True`")
        elif not existe:
            errores.append(f"{clave}: no existe {o['clase']} en {o['archivo']}")
        elif o["ops"]:
            faltan = [op for op in o["ops"] if not C.existe(o["archivo"], o["clase"], op)]
            if faltan:
                errores.append(f"{clave}: las operaciones {faltan} no existen en el código")
    for i in INTERFACES:
        for k in i["realiza"]:
            if k not in OBJETOS:
                errores.append(f"interfaz {i['nombre']}: la clase {k} no está entre las de diseño")
        if not i.get("nuevo") and i.get("archivo"):
            for op in i["operaciones"]:
                if not C.existe(i["archivo"], i["clase"], op):
                    errores.append(f"interfaz {i['nombre']}: la operación {op} no existe en el código")
    for nombre_analisis, lista in TRAZA.items():
        for clave, ops in lista:
            if clave not in OBJETOS:
                errores.append(f"traza de {nombre_analisis}: {clave} no es una clase de diseño")
                continue
            o = OBJETOS[clave]
            if o["nuevo"]:
                continue
            c = C.buscar(o["archivo"], o["clase"])
            for op in ops:
                if c is not None and op not in c["metodos"] and op not in c["atributos"]:
                    errores.append(f"traza de {nombre_analisis}: {clave} no tiene la operación {op}")
    from modelo import realizaciones as _R

    for clave, ops in _R.OPERACIONES_NUEVAS.items():
        o = OBJETOS.get(clave)
        if o is None:
            errores.append(f"OPERACIONES_NUEVAS: {clave} no es una clase de diseño")
        elif C.existe(o["archivo"], o["clase"]) and exigir_nuevos:
            faltan = [op for op in ops if not C.existe(o["archivo"], o["clase"], op)]
            if faltan:
                errores.append(f"{clave}: las operaciones {faltan} se diseñaron como nuevas y todavía no existen")
    if analisis is not None:
        for clave in analisis.CLASES:
            if clave not in TRAZA:
                errores.append(f"la clase del análisis {clave} no tiene traza a una clase de diseño")
        for s in SUBSISTEMAS:
            if s["traza"] is not None and s["traza"] not in analisis.NOMBRE_PAQUETE:
                errores.append(f"subsistema {s['id']}: el paquete del análisis {s['traza']} no existe")
        if {s["traza"] for s in SUBSISTEMAS if s["traza"]} != set(analisis.NOMBRE_PAQUETE):
            errores.append("cada paquete del análisis debe tener su subsistema de diseño")
    from pathlib import Path

    for origen, destino, etiqueta, *cambio in ASOCIACIONES:
        if cambio:
            continue
        if origen not in OBJETOS or destino not in OBJETOS:
            errores.append(f"asociación {origen} → {destino}: falta una de las dos clases de diseño")
            continue
        o, d = OBJETOS[origen], OBJETOS[destino]
        if o["nuevo"] or d["nuevo"]:
            continue
        ruta = C.RAIZ / o["archivo"]
        texto = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
        nombre = d["clase"].strip("<>").replace(".py", "")
        if nombre not in texto:
            errores.append(f"asociación {origen} → {destino}: el código de {o['archivo']} no nombra a {nombre}")
    for cambio in CAMBIOS:
        for k in cambio["nuevas"] + cambio["cambian"]:
            if k not in OBJETOS:
                errores.append(f"{cambio['id']}: {k} no es una clase de diseño")
    if errores:
        raise ValueError("Modelo de diseño inconsistente:\n  " + "\n  ".join(errores))


def usuarios_de_interfaces(analisis=None):
    """{interfaz: {subsistemas que la usan}}: quienes mandan mensajes a una clase que la realiza (o a la interfaz) desde otro subsistema."""
    from modelo import realizaciones as R

    quien = {}
    for i in INTERFACES:
        for k in i["realiza"] + [i["nombre"]]:
            quien[k] = i
    usuarios = {i["nombre"]: set() for i in INTERFACES}
    for r in R.REALIZACIONES:
        for e in r["escenarios"]:
            for origen, destino, _, _ in e["mensajes"]:
                bo, bd = origen.split("#")[0], destino.split("#")[0]
                if bd in quien and bo in OBJETOS and OBJETOS[bo]["sub"] != quien[bd]["sub"]:
                    usuarios[quien[bd]["nombre"]].add(OBJETOS[bo]["sub"])
    return usuarios


def analisis_de(clave_objeto):
    """Clases del análisis que realiza una clase de diseño (la traza al revés)."""
    return [a for a, lista in TRAZA.items() if any(k == clave_objeto for k, _ in lista)]


# ---- validación de las realizaciones ---------------------------------------------------------------------------
ACTORES_SECUENCIA = {"U", "D", "X", "A", "B", "S"}


def _clave(vida):
    return vida.split("#")[0]


def _raiz_analisis(analisis, sub):
    if sub == "carcasa":
        return "carcasa"
    return next((p["padre"] or p["id"]) for p in analisis.PAQUETES if p["id"] == sub)


def validar_realizaciones(analisis, realizaciones=None, nuevas=None):
    """Cada colaboración del análisis tiene su realización, y cada mensaje es una operación real (o declarada como nueva) de la clase que lo recibe."""
    from modelo import realizaciones as R

    realizaciones = realizaciones or R.REALIZACIONES
    nuevas = nuevas or R.OPERACIONES_NUEVAS
    errores = []
    ids = [r["col"] for r in realizaciones]
    if sorted(ids) != sorted(c["id"] for c in analisis.COLABORACIONES):
        errores.append("cada colaboración del análisis necesita exactamente una realización del diseño")
    permitidas = {tuple(d) for d in analisis.DEPENDENCIAS}
    cruces = {}
    for r in realizaciones:
        if not r["flujo"] or not r["escenarios"]:
            errores.append(f"{r['col']}: falta el flujo o los escenarios")
        for e in r["escenarios"]:
            for numero, (origen, destino, op, args) in enumerate(e["mensajes"], 1):
                for vida in (origen, destino):
                    if _clave(vida) not in ACTORES_SECUENCIA and _clave(vida) not in OBJETOS:
                        errores.append(f"{r['col']}-{e['id']} mensaje {numero}: {vida} no es una clase de diseño")
                c_dest = _clave(destino)
                if c_dest in ACTORES_SECUENCIA or c_dest not in OBJETOS or op.startswith("·"):
                    continue
                obj = OBJETOS[c_dest]
                validas = set(nuevas.get(c_dest, []))
                if not obj["nuevo"]:
                    validas |= (operaciones_validas(obj) or set())
                if op not in validas:
                    errores.append(f"{r['col']}-{e['id']} mensaje {numero}: {obj['clase']} no tiene la operación {op}")
                c_orig = _clave(origen)
                if c_orig in OBJETOS:
                    a, b = _raiz_analisis(analisis, OBJETOS[c_orig]["sub"]), _raiz_analisis(analisis, obj["sub"])
                    if a != b:
                        cruces.setdefault((a, b), []).append(f"{r['col']}-{e['id']}: {c_orig} → {c_dest}.{op}")
    for (a, b), ejemplos in cruces.items():
        if a != "carcasa" and (a, b) not in permitidas:
            errores.append(f"el diseño hace depender a {a} de {b} y el análisis no lo permite ({ejemplos[0]})")
    if errores:
        raise ValueError("Realizaciones del diseño inconsistentes:\n  " + "\n  ".join(errores))
    return cruces


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from modelo import analisis
    validar(analisis=analisis)
    validar_realizaciones(analisis)
    print(len(OBJETOS), "clases de diseño;", len(SUBSISTEMAS), "subsistemas;", len(INTERFACES), "interfaces")
