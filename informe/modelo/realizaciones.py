"""Realizaciones de los casos de uso en el diseño (PUDS 9.3.3): una por cada colaboración del análisis.

Cada realización tiene una traza a su colaboración del análisis (`col`), el flujo de eventos del diseño, los requisitos de implementación y uno o más
escenarios; cada escenario es un diagrama de secuencia (9.3.3.2: «un flujo o escenario concreto»). Los mensajes son
(origen, destino, operación, argumentos): la operación es un método real de la clase de destino, y `modelo/diseno.py::validar_realizaciones` lo
comprueba contra el código. Las clases se identifican con la clave de `diseno.OBJETOS`; `Clase#2` es otra instancia de la misma clase (por ejemplo,
el navegador de otra persona) y `U`, `D`, `X` son los actores de la colaboración del análisis. Una operación que empieza con «·» pertenece al navegador o a
un producto externo (no se comprueba). Las operaciones de las clases nuevas (cambios C1 a C4) se declaran en `OPERACIONES_NUEVAS`.
"""

# Operaciones de las clases que se programan en los cambios C1 a C4 (el diseño las fija antes de que existan) y operaciones nuevas de clases que ya existen.
OPERACIONES_NUEVAS = {
    "ActivityStore": ["identify_now", "create", "recent", "since", "get", "update_data", "identify", "record"],
    "ORMActivityStore": ["identify_now", "create", "recent", "since", "get", "update_data"],
    "ConversationStore": ["append_exchange", "history", "discard_exchange"],
    "TurnStore": ["take", "release", "current"],
    "ORMConversationStore": ["append_exchange", "history", "discard_exchange"],
    "MongoConversationStore": ["append_exchange", "history", "discard_exchange"],
    "MongoActivityStore": ["identify_now", "create", "recent", "since", "get", "update_data"],
    "RedisTurnStore": ["take", "release", "current"],
    "stores": ["get_activity_store", "get_conversation_store", "get_turn_store", "get_rate_limiter"],
    "NotificationService": ["requestPermission", "notifyChange", "notifyIdea"],
    "HelpPanel": ["toggle", "send"],
    "HelpService": ["ask"],
    "help_views": ["ia_help"],
    "help_knowledge": ["load_knowledge", "build_help_prompt"],
    "RedisRateLimiter": ["allow"],
    # clases que ya existen y ganan una operación en un cambio
    "FollowView": ["enableNotifications", "notifyNewActivity"],
    "ChatbotService": ["transcribeAudio"],
    "vistas_ia": ["analyze_uml_audio"],
}


def _r(col, flujo, escenarios, implementacion=()):
    return dict(col=col, flujo=flujo, escenarios=escenarios, implementacion=list(implementacion))


def _e(id_, nombre, mensajes):
    return dict(id=id_, nombre=nombre, mensajes=mensajes)


REALIZACIONES = [
    _r("COL-01",
       ["`LandinPage` crea el identificador de la sala (`uuid`) o toma el código escrito y navega al editor; `Diagram` pide a `DiagramService` inicializar la sala y este a "
        "`CollaborationService.init`, que abre el WebSocket por `P2PService` y `SignalingService`.",
        "Al conectar, `CanvasConsumer.connect` mete la conexión en el grupo de la sala con `RedisGroupRoleStore.join` (el primero del orden es el host). `SignalingService` pide "
        "la identidad a `IdentityService.getIdentity`, que pregunta el nombre si no lo tiene, y envía `hello`; `CanvasConsumer._handle_hello` valida el nombre, lo guarda en "
        "`RedisGroupIdentityStore`, registra al participante con el puerto `ActivityStore.identify` y difunde la presencia con los nombres y roles."],
       [_e("a", "Abrir la sala", [
           ("U", "LandinPage", "crearNuevoLienzo", ""),
           ("LandinPage", "Diagram", "·router.navigate", "'/diagram', roomId"),
           ("Diagram", "Diagram", "ngAfterViewInit", ""),
           ("Diagram", "DiagramService", "initialize", "contenedor, roomId"),
           ("DiagramService", "CollaborationService", "init", "roomId, options"),
           ("CollaborationService", "P2PService", "init", "roomId, viewer"),
           ("P2PService", "SignalingService", "connect", "roomId, viewer")]),
        _e("b", "Identificarse y asignar el rol", [
            ("SignalingService", "CanvasConsumer", "connect", ""),
            ("CanvasConsumer", "RedisGroupRoleStore", "join", "channel_name"),
            ("SignalingService", "IdentityService", "getIdentity", ""),
            ("IdentityService", "IdentityService", "requestName", ""),
            ("SignalingService", "CanvasConsumer", "receive", "hello{token, name}"),
            ("CanvasConsumer", "CanvasConsumer", "_handle_hello", "data"),
            ("CanvasConsumer", "RedisGroupIdentityStore", "set", "channel_name, token, name"),
            ("CanvasConsumer", "ActivityStore", "identify", "room, token, name"),
            ("CanvasConsumer", "RedisGroupRoleStore", "members", ""),
            ("CanvasConsumer", "CanvasConsumer", "_broadcast_presence_state", "members")])],
       ["El nombre se limpia de caracteres de control y no pasa de 40 caracteres.", "Cada conexión puede cambiar de identidad como máximo cinco veces."]),
    _r("COL-02",
       ["`Diagram.onDragEnded` crea la clase con `DiagramService.createUmlClass`, que le agrega sus interacciones y pide a `EditionService.scheduleAutoResize` que ajuste el "
        "tamaño. Para unir dos clases, `RelationshipService.startLinkCreation` espera dos clics y llama a `createTypedRelationship`; si la unión queda «muchos a muchos», "
        "`DiagramService.reconcileGeneratedJunctions` crea la clase intermedia con dos relaciones 1:N. Todo cambio termina en `persist` y `scheduleBackendBackup`."],
       [_e("a", "Agregar una clase y editarla", [
           ("U", "Diagram", "onDragEnded", "evento"),
           ("Diagram", "DiagramService", "createUmlClass", "classModel"),
           ("DiagramService", "DiagramService", "setupClassInteraction", "elemento"),
           ("DiagramService", "EditionService", "scheduleAutoResize", "modelo, paper"),
           ("DiagramService", "DiagramService", "persist", "")]),
        _e("b", "Unir dos clases y resolver «muchos a muchos»", [
            ("U", "RelationshipService", "startLinkCreation", "paper, contenedor, tipo"),
            ("RelationshipService", "RelationshipService", "createTypedRelationship", "sourceId, targetId, tipo"),
            ("RelationshipService", "DiagramService", "createTypedRelationship", "sourceId, targetId, tipo"),
            ("DiagramService", "DiagramService", "reconcileGeneratedJunctions", ""),
            ("DiagramService", "DiagramService", "persist", "")])],
       ["El lienzo vive en el navegador (JointJS): editar no espera al servidor.", "Los tipos de relación y las multiplicidades siguen UML 2.5."]),
    _r("COL-03",
       ["`DiagramService` avisa a `CollaborationService.broadcast` de cada operación pequeña; esta la manda por `P2PService.sendToAll` y `SignalingService.broadcast` al "
        "WebSocket. `CanvasConsumer.receive` la difunde al grupo de la sala (`_send_to_room`) y, si es una operación que se registra, `_record_activity` la guarda con el puerto "
        "`ActivityStore.record` y avisa a la sala. En la otra pantalla `P2PService.handleSignaling` entrega la operación a `CollaborationService.applyRemoteOp`, que la aplica por "
        "`DiagramService.createUmlClass(…, remote)` sin volver a emitirla. Cada cierto tiempo `DiagramService.scheduleBackendBackup` respalda el diagrama."],
       [_e("a", "Editar y propagar un cambio", [
           ("U", "DiagramService", "createUmlClass", "classModel"),
           ("DiagramService", "CollaborationService", "broadcast", "op"),
           ("CollaborationService", "P2PService", "sendToAll", "op"),
           ("P2PService", "SignalingService", "broadcast", "op"),
           ("SignalingService", "CanvasConsumer", "receive", "broadcast{payload}"),
           ("CanvasConsumer", "CanvasConsumer", "_send_to_room", "mensaje"),
           ("CanvasConsumer", "CanvasConsumer", "_record_activity", "payload"),
           ("CanvasConsumer", "ActivityStore", "record", "room, actor, tipo, resumen, data")]),
        _e("b", "Aplicarlo en la otra pantalla y respaldar", [
            ("CanvasConsumer", "CanvasConsumer#2", "broadcast_message", "evento"),
            ("CanvasConsumer#2", "SignalingService#2", "onMessage", "mensaje"),
            ("SignalingService#2", "P2PService#2", "handleSignaling", "mensaje"),
            ("P2PService#2", "CollaborationService#2", "applyRemoteOp", "op"),
            ("CollaborationService#2", "DiagramService#2", "createUmlClass", "payload, remote=true"),
            ("DiagramService#2", "BackupService", "setBackupUml", "roomId, umlJson"),
            ("BackupService", "vistas_respaldo", "set_backupUML", "request, room_id"),
            ("vistas_respaldo", "BackupUML", "·update_or_create", "room_id, defaults")]),
        ],
       ["Una operación es pequeña y no espera al servidor para mostrarse en la pantalla de quien edita.", "El respaldo se pide 1,5 s después de la última edición."]),
    _r("COL-04",
       ["Al conectar, `P2PService` recibe su identificador (`presence self`) y, si el lienzo está vacío, `CollaborationService` difunde `request_full_state`. Quien está conectado "
        "contesta con `exportToJson` y `full_state`, y el recién llegado carga el diagrama con `DiagramService.loadFromJson`. Si nadie contesta en 3 s, `init` lee el último "
        "respaldo con `BackupService.getBackup` (vista `get_backupUML`)."],
       [_e("a", "Pedir el estado a quien está conectado", [
           ("P2PService", "P2PService", "handleSignaling", "presence{self}"),
           ("P2PService", "CollaborationService", "broadcast", "{t: request_full_state}"),
           ("CollaborationService", "P2PService", "sendToAll", "op"),
           ("P2PService", "SignalingService", "broadcast", "op"),
           ("SignalingService", "CanvasConsumer", "receive", "broadcast"),
           ("CanvasConsumer", "CanvasConsumer#2", "broadcast_message", "request_full_state"),
           ("CanvasConsumer#2", "SignalingService#2", "onMessage", "mensaje"),
           ("SignalingService#2", "P2PService#2", "handleSignaling", "mensaje"),
           ("P2PService#2", "CollaborationService#2", "applyRemoteOp", "request_full_state"),
           ("CollaborationService#2", "DiagramService#2", "exportToJson", ""),
           ("CollaborationService#2", "CollaborationService#2", "broadcast", "{t: full_state, payload}")]),
        _e("b", "Sala vacía: usar el último respaldo", [
            ("CollaborationService", "CollaborationService", "init", "roomId, options"),
            ("CollaborationService", "BackupService", "getBackup", "roomId"),
            ("BackupService", "vistas_respaldo", "get_backupUML", "request, room_id"),
            ("vistas_respaldo", "BackupUML", "·get", "room_id"),
            ("CollaborationService", "DiagramService", "loadFromJson", "snapshot, true, true")])],
       ["Si la sala se llenó mientras llegaba el respaldo, no se carga: pisaría lo que tienen quienes sí están conectados."]),
    _r("COL-05",
       ["`ParticipantsPanel.remove` pide a `P2PService.removeParticipant` (solo el host puede) y este a `SignalingService.removeParticipant`; `CanvasConsumer.receive` ejecuta "
        "`RedisGroupRoleStore.remove_by_host`, un guion atómico de Redis que comprueba que quien lo pide es el host. Si lo es, borra la identidad, le manda `force_disconnect` al "
        "expulsado y difunde la presencia; si no, `_reject_removal`. En el navegador del expulsado `P2PService` marca `removed` y `Diagram.leaveAfterRemoval` lo saca de la sala."],
       [_e("a", "El host expulsa a un participante", [
           ("D", "ParticipantsPanel", "remove", "peer"),
           ("ParticipantsPanel", "P2PService", "removeParticipant", "peer"),
           ("P2PService", "SignalingService", "removeParticipant", "peer"),
           ("SignalingService", "CanvasConsumer", "receive", "remove_participant{peer}"),
           ("CanvasConsumer", "RedisGroupRoleStore", "remove_by_host", "requester, target"),
           ("CanvasConsumer", "CanvasConsumer", "_delete_identity", "target"),
           ("CanvasConsumer", "RedisGroupIdentityStore", "delete", "channel_name"),
           ("CanvasConsumer", "CanvasConsumer#2", "force_disconnect", "evento"),
           ("CanvasConsumer", "CanvasConsumer", "_broadcast_presence_state", "members")]),
        _e("b", "El expulsado vuelve al inicio", [
            ("CanvasConsumer#2", "SignalingService#2", "onMessage", "{type: removed}"),
            ("SignalingService#2", "P2PService#2", "handleSignaling", "mensaje"),
            ("Diagram", "Diagram", "leaveAfterRemoval", ""),
            ("Diagram", "DiagramService", "closeDiagram", "roomId, {saveBackup: false}")]),
        _e("c", "Alterno: quien lo pide no es el host", [
            ("SignalingService", "CanvasConsumer", "receive", "remove_participant{peer}"),
            ("CanvasConsumer", "RedisGroupRoleStore", "remove_by_host", "requester, target"),
            ("CanvasConsumer", "CanvasConsumer", "_reject_removal", "")])],
       ["La autorización se decide en el servidor con un guion atómico de Redis; el navegador solo oculta el botón."]),
    _r("COL-06",
       ["`LandinPage.unirseAlLienzo` abre el editor con el código; la identidad anónima sale de `IdentityService.getIdentity` (la misma de antes, guardada en el navegador) y "
        "`ActivityStore.identify` actualiza al mismo participante por su token. El diagrama llega como en COL-04; el historial de actividad lo pide `ActivityPanel.ngOnInit` a "
        "`get_room_activity` y la conversación, `IaChatPanel.loadHistory` a `chat_history`, que con C1 devuelve la conversación de la sala por `ConversationStore.history`."],
       [_e("a", "Reabrir la sala y recuperar el diagrama", [
           ("U", "LandinPage", "unirseAlLienzo", ""),
           ("LandinPage", "Diagram", "·router.navigate", "'/diagram', código"),
           ("Diagram", "Diagram", "ngAfterViewInit", ""),
           ("Diagram", "DiagramService", "initialize", "contenedor, roomId"),
           ("DiagramService", "CollaborationService", "init", "roomId, options"),
           ("CollaborationService", "BackupService", "getBackup", "roomId"),
           ("BackupService", "vistas_respaldo", "get_backupUML", "request, room_id")]),
        _e("b", "Recuperar la actividad y la conversación", [
            ("ActivityPanel", "vistas_actividad", "get_room_activity", "request, room"),
            ("vistas_actividad", "ActivityStore", "recent", "room, limit"),
            ("IaChatPanel", "IaChatService", "history", "roomId"),
            ("IaChatService", "chat_views", "chat_history", "request, room"),
            ("chat_views", "ConversationStore", "history", "room, limit")])],
       ["La identidad es el token guardado en el navegador: desde otro navegador la persona es nueva."]),
    _r("COL-07",
       ["`ActivityPanel.ngOnInit` pide el historial con `get_room_activity`, que lo lee con `ActivityStore.recent`/`since` y lo serializa con `serialize_activity_event`. Los eventos "
        "nuevos llegan por el WebSocket: `CanvasConsumer._record_activity` descarta lo que no se registra (mover, cambiar tamaño), junta las ediciones seguidas (`_coalesce_edit`), "
        "respeta el tope por conexión (`_within_activity_rate_limit`), guarda con `ActivityStore.record` y avisa a la sala; `P2PService.handleSignaling` los agrega a "
        "`liveActivityEvents` y `ActivityPanel.mergeEvents` los junta con el historial."],
       [_e("a", "Abrir el panel y leer el historial", [
           ("U", "ActivityPanel", "ngOnInit", ""),
           ("ActivityPanel", "vistas_actividad", "get_room_activity", "request, room"),
           ("vistas_actividad", "ActivityStore", "recent", "room, limit"),
           ("vistas_actividad", "activity", "serialize_activity_event", "evento")]),
        _e("b", "Recibir y registrar una acción nueva", [
            ("SignalingService", "CanvasConsumer", "receive", "broadcast{payload}"),
            ("CanvasConsumer", "CanvasConsumer", "_record_activity", "payload"),
            ("CanvasConsumer", "CanvasConsumer", "_coalesce_edit", "payload"),
            ("CanvasConsumer", "CanvasConsumer", "_within_activity_rate_limit", ""),
            ("CanvasConsumer", "ActivityStore", "record", "room, actor, tipo, resumen, data"),
            ("CanvasConsumer", "CanvasConsumer", "_send_to_room", "{type: activity, event}"),
            ("CanvasConsumer", "SignalingService#2", "onMessage", "{type: activity}"),
            ("SignalingService#2", "P2PService#2", "handleSignaling", "mensaje"),
            ("ActivityPanel#2", "ActivityPanel#2", "mergeEvents", "history, live")])],
       ["Si falla el registro, la edición sigue (`try/except` en `_record_activity`).", "Los datos de un evento no pasan de 8 KB y se limitan 60 eventos por 10 s por conexión."]),
    _r("COL-08",
       ["`IaActionsService.request` avisa a la sala que la IA empieza (`CollaborationService.startIaRequest`) y llama a `IaChatService.send`, que hace `POST /api/rooms/<sala>/ia/chat/` con "
        "el token. `ia_chat` identifica a la persona (`_participant_for`), toma el turno de la sala con `TurnStore.take` (409 si la IA atiende a otra persona), reserva el cupo con "
        "`_reserve_attempt` (429 si se pasó de los topes), arma el contexto con el diagrama, la actividad (`ActivityStore.recent`) y la conversación de la sala "
        "(`ConversationStore.history`) y pide la respuesta a `AIProvider`. Al final libera el turno."],
       [_e("a", "Reservar el cupo y el turno de la sala", [
           ("IaActionsService", "CollaborationService", "startIaRequest", "by"),
           ("IaActionsService", "IaChatService", "send", "roomId, mode, message, uml"),
           ("IaChatService", "chat_views", "ia_chat", "request, room"),
           ("chat_views", "chat_views", "_participant_for", "request, room"),
           ("chat_views", "TurnStore", "take", "room, participant_id"),
           ("chat_views", "chat_views", "_reserve_attempt", "room, participant"),
           ("chat_views", "IaAttempt", "·objects.create", "room, participant")]),
        _e("b", "Armar el contexto y consultar al servicio de IA", [
            ("chat_views", "ai_provider", "get_ai_provider", ""),
            ("chat_views", "ActivityStore", "recent", "room, MAX_EVENTS"),
            ("chat_views", "ConversationStore", "history", "room, MAX_HISTORY"),
            ("chat_views", "ia_context", "build_chat_prompt", "participant_name, uml, events, history, message"),
            ("chat_views", "GeminiProvider", "chat", "prompt"),
            ("GeminiProvider", "services_gemini", "·HTTPS generateContent", "prompt")])],
       ["La IA no actúa por su cuenta: toda llamada nace de `ia_chat`, con un participante identificado.",
        "Topes: 12 por minuto por persona, 30 por sala, 60 en todo el servicio; mensajes de hasta 2000 caracteres; contexto de hasta 12 000 caracteres."]),
    _r("COL-09",
       ["En modo «Pedir cambio», `ia_chat` llama a `_change`: el proveedor devuelve los cambios (`AIProvider.change`), `validate_changes` los revisa (60 clases y 150 relaciones como "
        "máximo) y `count_destructive` cuenta cuántos elementos eliminarían; `ConversationStore.append_exchange` guarda el pedido y la respuesta. En el navegador de quien pidió, "
        "`IaActionsService.request` pide confirmación si eliminan algo y aplica los cambios con `CollaborationService.runAsIa` y `DiagramService.loadFromJson`: se propagan y se "
        "registran como «IA, a pedido de X»."],
       [_e("a", "El servidor valida los cambios", [
           ("chat_views", "chat_views", "_change", "provider, room, participant, body, message"),
           ("chat_views", "GeminiProvider", "change", "message, uml"),
           ("chat_views", "change_guard", "validate_changes", "changes"),
           ("chat_views", "change_guard", "count_destructive", "changes, uml"),
           ("chat_views", "ConversationStore", "append_exchange", "room, participant, mode, message, reply"),
           ("chat_views", "TurnStore", "release", "room")]),
        _e("b", "El navegador confirma y aplica", [
            ("IaChatService", "IaActionsService", "request", "roomId, 'change', message"),
            ("IaActionsService", "IaActionsService", "confirmDeletions", "count"),
            ("IaActionsService", "IaActionsService", "applyChanges", "changes"),
            ("IaActionsService", "CollaborationService", "runAsIa", "acción"),
            ("CollaborationService", "DiagramService", "loadFromJson", "changes, true"),
            ("DiagramService", "CollaborationService", "broadcast", "op{via_ia}"),
            ("IaActionsService", "CollaborationService", "finishIaRequest", "requestId")]),
        _e("c", "Alterno: «Generar modelo» y la voz usan el mismo camino (C1)", [
            ("U", "SidePanel", "onGenerate", "prompt"),
            ("SidePanel", "IaActionsService", "request", "roomId, 'change', prompt"),
            ("U", "SidePanel", "toggleVoiceInput", ""),
            ("SidePanel", "SidePanel", "processVoiceAudio", "audio"),
            ("SidePanel", "ChatbotService", "transcribeAudio", "audio"),
            ("ChatbotService", "vistas_ia", "analyze_uml_audio", "request{transcribe_only}"),
            ("SidePanel", "SidePanel", "onGenerate", "transcripción")])],
       ["Antes de aplicar un cambio que elimina elementos se pide confirmación al actor.", "Los cambios enormes se rechazan en el servidor (`validate_changes`).",
        "Si el proveedor falla, `AIProviderError` produce un 502 con un mensaje claro y el diagrama no cambia."]),
    _r("COL-10",
       ["`SidePanel.onImportImage` envía la imagen a `UmlImageServiceTs.analyzeImage` y esta a `analyze_uml_image`, que comprueba tamaño (10 MB) y tipo, la pasa a Base64 y la envía al "
        "proveedor de visión (`call_gemini_from_image`). El modelo reconocido vuelve al navegador, que lo muestra; quien decide elige `replaceImageImport` o `mergeImageImport`, y "
        "`DiagramService.loadFromJson` lo aplica y lo propaga."],
       [_e("a", "Reconocer el diagrama de la imagen", [
           ("U", "SidePanel", "onImportImage", "evento"),
           ("SidePanel", "UmlImageServiceTs", "analyzeImage", "archivo"),
           ("UmlImageServiceTs", "vistas_ia", "analyze_uml_image", "request{image}"),
           ("vistas_ia", "services_gemini", "call_gemini_from_image", "image_base64, mime_type")]),
        _e("b", "Reemplazar o combinar con el diagrama actual", [
            ("U", "SidePanel", "replaceImageImport", ""),
            ("SidePanel", "SidePanel", "consumePendingImageImport", ""),
            ("SidePanel", "DiagramService", "replaceDiagramFromImage", "json"),
            ("DiagramService", "DiagramService", "loadFromJson", "json, true"),
            ("DiagramService", "CollaborationService", "broadcast", "op")])],
       ["La imagen viaja al servicio de IA: no se guarda en el servidor.", "Solo PNG, JPG o WebP de hasta 10 MB."]),
    _r("COL-11",
       ["`ia_chat` en modo `ask` o `review`: `_answer` arma el contexto y responde por `AIProvider.chat`; `_review` pide hasta cinco ideas, las interpreta con `parse_review` y publica "
        "un evento `ia_review` con ellas (`ActivityStore.create`) que difunde `_publish_activity`. La pregunta y la respuesta se guardan juntas con "
        "`ConversationStore.append_exchange` y `IaChatPanel` las muestra a toda la sala."],
       [_e("a", "Preguntar a la IA", [
           ("U", "IaChatPanel", "send", ""),
           ("IaChatPanel", "IaActionsService", "request", "roomId, mode, text"),
           ("IaActionsService", "IaChatService", "send", "roomId, mode, message, uml"),
           ("IaChatService", "chat_views", "ia_chat", "request, room"),
           ("chat_views", "chat_views", "_answer", "provider, room, participant, body, message"),
           ("chat_views", "GeminiProvider", "chat", "prompt"),
           ("chat_views", "ConversationStore", "append_exchange", "room, participant, mode, message, reply"),
           ("chat_views", "TurnStore", "release", "room")]),
        _e("b", "Pedir una revisión con ideas", [
            ("chat_views", "chat_views", "_review", "provider, room, participant, body, message"),
            ("chat_views", "ia_context", "build_review_prompt", "uml"),
            ("chat_views", "GeminiProvider", "chat", "prompt"),
            ("chat_views", "ia_context", "parse_review", "raw"),
            ("chat_views", "ActivityStore", "create", "room, actor='IA', type='ia_review', data{findings}"),
            ("chat_views", "chat_views", "_publish_activity", "room, event"),
            ("chat_views", "ConversationStore", "append_exchange", "room, participant, 'review', message, reply")])],
       ["Hay una sola instancia de IA por sala: el turno (`TurnStore`) evita que dos pedidos se mezclen.", "Cada idea es un texto y una instrucción; ninguna se aplica sola."]),
    _r("COL-12",
       ["`ActivityPanel.apply` pide a `IaActionsService.applySuggestion` aplicar una idea: primero la reserva (`IaChatService.claimSuggestion`, POST de `claim_suggestion`), que responde "
        "409 si otra persona la tomó; si la reserva queda, ejecuta la instrucción como un pedido de cambio (COL-08 y COL-09) y, cuando el cambio llegó al diagrama, la confirma "
        "(`confirmSuggestion`, PUT). Si se cancela o falla, la libera (`releaseSuggestion`, DELETE); una reserva que nadie confirma vence a los 150 s. Los cambios de la idea se "
        "guardan con `ActivityStore.update_data`, atómico."],
       [_e("a", "Reservar, aplicar y confirmar una idea", [
           ("U", "ActivityPanel", "apply", "event, index, finding"),
           ("ActivityPanel", "IaActionsService", "applySuggestion", "roomId, eventId, index, prompt"),
           ("IaActionsService", "IaChatService", "claimSuggestion", "roomId, eventId, index"),
           ("IaChatService", "chat_views", "claim_suggestion", "request, room, event_id, index"),
           ("chat_views", "ActivityStore", "update_data", "room, event_id, mutate"),
           ("IaActionsService", "IaActionsService", "request", "roomId, 'change', prompt"),
           ("IaActionsService", "IaChatService", "confirmSuggestion", "roomId, eventId, index"),
           ("chat_views", "ActivityStore", "update_data", "room, event_id, mutate")]),
        _e("b", "Alterno: otra persona ya la tomó, o se cancela", [
            ("IaActionsService", "IaChatService", "claimSuggestion", "roomId, eventId, index"),
            ("chat_views", "chat_views", "_is_live", "entry, now"),
            ("IaActionsService", "IaActionsService", "release", "roomId, eventId, index"),
            ("IaActionsService", "IaChatService", "releaseSuggestion", "roomId, eventId, index")])],
       ["Reservar es atómico: dos personas no pueden aplicar la misma idea a la vez.", "La reserva vence sola a los 150 s si nadie la confirma ni la libera."]),
    _r("COL-13",
       ["`SidePanel.exportImage` genera el PNG en el navegador y `Diagram.exportXmi` arma el diagrama con `DiagramExportService.export` y lo manda a `XmiService.exportXmi`; "
        "`export_xmi` lo convierte con `export_uml_to_xmi` en un XMI 2.1 con posición y tamaño de cada clase y el navegador lo descarga."],
       [_e("a", "Exportar a XMI", [
           ("U", "Diagram", "exportXmi", ""),
           ("Diagram", "DiagramExportService", "export", "graph"),
           ("Diagram", "XmiService", "exportXmi", "umlJson"),
           ("XmiService", "vistas_intercambio", "export_xmi", "request"),
           ("vistas_intercambio", "xmi_service", "export_uml_to_xmi", "uml_json")]),
        _e("b", "Exportar como imagen", [
            ("U", "SidePanel", "exportImage", ""),
            ("SidePanel", "DiagramService", "exportToImage", "'diagrama.png'")])],
       ["La ida y la vuelta con Enterprise Architect 17.2 se probó: clases, atributos, operaciones, asociaciones y multiplicidades se conservan."]),
    _r("COL-14",
       ["`Diagram.importXmi` envía el archivo a `XmiService.importXmi` y este a `import_xmi`; `import_xmi_to_uml` lo valida (sin DOCTYPE ni entidades externas), lo convierte al "
        "diagrama y lo devuelve; `Diagram.applyDefaultXmiLayout` coloca las clases que no traen posición y `DiagramService.loadFromJson` las dibuja y propaga."],
       [_e("a", "Importar un archivo XMI", [
           ("U", "Diagram", "importXmi", "evento"),
           ("Diagram", "XmiService", "importXmi", "archivo"),
           ("XmiService", "vistas_intercambio", "import_xmi", "request{file}"),
           ("vistas_intercambio", "xmi_service", "import_xmi_to_uml", "archivo"),
           ("Diagram", "Diagram", "applyDefaultXmiLayout", "umlJson"),
           ("Diagram", "DiagramService", "loadFromJson", "umlJson, true"),
           ("DiagramService", "CollaborationService", "broadcast", "op")])],
       ["Al importar no se leen archivos locales ni se abren conexiones (XXE).", "Un archivo mal formado devuelve un error 400 y el diagrama no cambia."]),
    _r("COL-15",
       ["`Diagram.saveDiagram` obtiene el diagrama para los generadores (`DiagramService.exportForGenerators`) y lo manda a `BackendGeneratorService.generateBackend`, que llama "
        "a `GenerateController.generate` (Spring Boot); `ProjectGenerator.generate` crea el proyecto con las capas, la base PostgreSQL y la colección de Postman "
        "(`PostmanCollectionGenerator`) y lo devuelve en un .zip. El SQL se genera en el navegador con `SqlExportService.exportToSql`."],
       [_e("a", "Generar el backend", [
           ("D", "Diagram", "saveDiagram", ""),
           ("Diagram", "DiagramService", "exportForGenerators", ""),
           ("Diagram", "BackendGeneratorService", "generateBackend", "json, 'mi-backend.zip'"),
           ("BackendGeneratorService", "GenerateController", "generate", "schema, basePackage, artifactId"),
           ("GenerateController", "ProjectGenerator", "generate", "schema, basePackage, artifactId")]),
        _e("b", "Exportar el SQL", [
            ("D", "SidePanel", "exportSql", ""),
            ("SidePanel", "SqlExportService", "downloadSql", "umlJson, fileName"),
            ("SqlExportService", "SqlExportService", "exportToSql", "umlJson, dbName")])],
       ["Java 21 y Spring Boot 3.5; el generador compila de verdad el proyecto en sus pruebas.", "Si el generador no responde, no se descarga nada."]),
    _r("COL-16",
       ["`SidePanel.onGenerateFrontend` envía el diagrama a `generar_flutter`, que crea el proyecto con `FlutterCRUDGenerator.generate_project` (modelos, SQLite local, pantallas "
        "CRUD y asistente de comandos), lo comprime y lo devuelve."],
       [_e("a", "Generar la aplicación móvil", [
           ("D", "SidePanel", "onGenerateFrontend", ""),
           ("SidePanel", "DiagramService", "exportForGenerators", ""),
           ("SidePanel", "FrontendGeneratorService", "generateFrontend", "umlJson"),
           ("FrontendGeneratorService", "vistas_intercambio", "generar_flutter", "request{uml_json}"),
           ("vistas_intercambio", "FlutterCRUDGenerator", "generate_project", "output_dir")])],
       ["El CRUD generado funciona sin red: los datos persisten en SQLite."]),
    _r("COL-17",
       ["`SidePanel.copyFollowLink` da el enlace de seguimiento; `FollowView.ngAfterViewInit` inicializa el diagrama en solo lectura y `SignalingService.connect` se conecta con "
        "`viewer`. `CanvasConsumer._connect_viewer` lo admite (hasta 10 por sala), sin entrar al orden de roles. El estado lo pide `_receive_from_viewer` al host con "
        "`_ask_host_for_state`; si nadie contesta se usa el respaldo (COL-04). Con C2, `FollowView.enableNotifications` pide el permiso y `notifyNewActivity` avisa de cada evento nuevo."],
       [_e("a", "Seguir la sala en solo lectura", [
           ("U", "FollowView", "ngAfterViewInit", ""),
           ("FollowView", "DiagramService", "initialize", "contenedor, roomId, {readOnly: true}"),
           ("DiagramService", "CollaborationService", "init", "roomId, {viewer: true}"),
           ("CollaborationService", "P2PService", "init", "roomId, viewer"),
           ("P2PService", "SignalingService", "connect", "roomId, viewer"),
           ("SignalingService", "CanvasConsumer", "_connect_viewer", ""),
           ("SignalingService", "CanvasConsumer", "_receive_from_viewer", "{t: request_full_state}"),
           ("CanvasConsumer", "CanvasConsumer", "_allow_viewer_state_request", ""),
           ("CanvasConsumer", "CanvasConsumer", "_ask_host_for_state", "")]),
        _e("b", "Recibir avisos (C2)", [
            ("U", "FollowView", "enableNotifications", ""),
            ("FollowView", "NotificationService", "requestPermission", ""),
            ("FollowView", "P2PService", "liveActivityEvents", "efecto"),
            ("FollowView", "FollowView", "notifyNewActivity", "evento"),
            ("FollowView", "NotificationService", "notifyChange", "autor, resumen"),
            ("FollowView", "NotificationService", "notifyIdea", "texto")])],
       ["Es de solo lectura: el servidor ignora todo lo que no sea pedir el estado.", "Los avisos solo funcionan con la página abierta."]),
    _r("COL-18",
       ["`HelpPanel.send` llama a `HelpService.ask`, que hace `POST /api/ia/help/`; `ia_help` comprueba el tope con `RateLimiter.allow` (6 por minuto por persona), arma el contexto "
        "con `help_knowledge.load_knowledge` y `build_help_prompt` y pide la respuesta a `AIProvider.chat`. La conversación es personal: la guarda el navegador."],
       [_e("a", "Preguntar cómo usar la herramienta", [
           ("U", "HelpPanel", "send", ""),
           ("HelpPanel", "HelpService", "ask", "message, history"),
           ("HelpService", "help_views", "ia_help", "request"),
           ("help_views", "RedisRateLimiter", "allow", "token, limit, window"),
           ("help_views", "help_knowledge", "load_knowledge", ""),
           ("help_views", "help_knowledge", "build_help_prompt", "knowledge, history, message"),
           ("help_views", "GeminiProvider", "chat", "prompt")])],
       ["Solo responde sobre la herramienta.", "Séptima pregunta en un minuto: 429.", "No depende de una sala."]),
]
