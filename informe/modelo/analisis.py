"""Flujo de trabajo de análisis (PUDS, capítulo 8): paquetes, clases del análisis y realizaciones de los casos de uso.

Reglas que se siguen (Jacobson, Booch y Rumbaugh, *El Proceso Unificado de Desarrollo de Software*, cap. 8):

  * una clase del análisis tiene responsabilidades (no operaciones con firma), atributos de alto nivel con tipos conceptuales,
    relaciones y requisitos especiales, y es de interfaz, de control o de entidad (8.4.2);
  * una clase de interfaz central por cada actor humano y otra por cada actor que es un sistema externo (8.6.2); una clase de
    entidad que no participa en ninguna realización no es necesaria (8.6.1.2);
  * una realización de caso de uso–análisis lleva el flujo de sucesos, el diagrama de clases participantes, el diagrama de
    colaboración y los requisitos especiales (8.4.3); el caso de uso se invoca con un mensaje de un actor a un objeto de interfaz;
    los mensajes no son operaciones: dicen para qué un objeto invoca a otro y son el origen de una responsabilidad del receptor;
    los enlaces son instancias de asociaciones entre clases (8.6.2.2);
  * los paquetes agrupan casos de uso por actor, por proceso o por relación entre ellos; las clases compartidas se extraen a su
    propio paquete; un paquete de servicio agrupa lo opcional; cohesión alta y acoplamiento bajo, sin ciclos (8.4.4, 8.6.1.1).

Las responsabilidades de cada clase NO se escriben a mano: salen de los mensajes que recibe en las colaboraciones, que es como
las define el libro. Así toda responsabilidad tiene una colaboración que la origina.
"""

# ---- paquetes del análisis ---------------------------------------------------------------------------------
# id, nombre, tipo ("paquete" | "servicio"), capa, padre, casos de uso que realiza, por qué existe
PAQUETES = [
    dict(id="nucleo", nombre="Núcleo de la sala", tipo="paquete", capa="general", padre=None, casos=[],
         por_que="Reúne las clases de entidad que casi todos los demás paquetes necesitan (la sala, quien participa y lo que se registra de "
                 "lo que hacen); se extraen a su propio paquete para que los demás dependan de él y no entre sí (8.6.1.1.1)."),
    dict(id="edicion", nombre="Edición del diagrama", tipo="paquete", capa="general", padre=None, casos=["CU2", "CU3"],
         por_que="CU3 empieza donde termina CU2 («un actor edita el diagrama»): son casos de uso relacionados y se realizan con las mismas "
                 "clases (el lienzo, el diagrama y su sincronización)."),
    dict(id="actividad", nombre="Actividad del equipo", tipo="paquete", capa="aplicación", padre=None, casos=["CU6"],
         por_que="Aísla los cambios en lo que se muestra de la actividad de la sala."),
    dict(id="seguimiento", nombre="Seguimiento móvil", tipo="servicio", capa="aplicación", padre="actividad", casos=["CU13"],
         por_que="Es un servicio opcional y de solo lectura: quien no lo necesita no pierde nada, y se entrega o se quita entero (8.4.4.1)."),
    dict(id="ia", nombre="Asistencia inteligente", tipo="paquete", capa="aplicación", padre=None, casos=["CU7", "CU8", "CU9"],
         por_que="CU9 es extendido por CU7 (aplicar una idea ejecuta un cambio) y los tres usan el servicio de IA: se agrupan por la "
                 "relación de extensión entre ellos (8.6.1.1)."),
    dict(id="ayuda", nombre="Asistente de ayuda", tipo="servicio", capa="aplicación", padre="ia", casos=["CU14"],
         por_que="Es un servicio opcional que solo contesta dudas de uso, con su propio conocimiento y sin tocar el diagrama."),
    dict(id="intercambio", nombre="Intercambio y generación", tipo="paquete", capa="aplicación", padre=None, casos=["CU10", "CU11", "CU12"],
         por_que="Lo que sale del diagrama o entra a él hacia otras herramientas y generadores: un mismo proceso (del modelo al código) y "
                 "el mismo cambio cuando evolucionan los formatos."),
    dict(id="gestion", nombre="Gestión de la sala", tipo="paquete", capa="aplicación", padre=None, casos=["CU1", "CU4", "CU5"],
         por_que="Son los casos de uso del ciclo de vida de la sala (entrar, expulsar, retomar): un mismo proceso y el mismo actor; está "
                 "arriba porque para retomar una sesión usa a los demás paquetes."),
]
NOMBRE_PAQUETE = {p["id"]: p["nombre"] for p in PAQUETES}

# Dependencias declaradas (origen depende de destino). `validar()` comprueba que cubren todas las que producen las colaboraciones
# y que no hay ciclos.
DEPENDENCIAS = [
    ("edicion", "nucleo"),
    ("actividad", "nucleo"), ("actividad", "edicion"), ("actividad", "ia"),
    ("ia", "nucleo"), ("ia", "edicion"),
    ("intercambio", "edicion"),
    ("gestion", "nucleo"), ("gestion", "edicion"), ("gestion", "ia"),
]

# ---- clases del análisis -----------------------------------------------------------------------------------
# est: interfaz | control | entidad. atrib: [(nombre, tipo conceptual)]. espec: requisitos especiales (se detallan en la fase de diseño).
# codigo: dónde vive hoy en el software y su estado: existe | cambia (con el cambio C1..C4 del plan) | nuevo.
def _c(nombre, est, paquete, desc, atrib, espec, estado, donde):
    return dict(nombre=nombre, est=est, paquete=paquete, desc=desc, atrib=atrib, espec=espec, estado=estado, donde=donde)


CLASES = {
    # -- núcleo de la sala
    "Sala": _c("Sala", "entidad", "nucleo",
               "El espacio de trabajo compartido que se identifica con un código.",
               [("código", "Texto único"), ("estado", "Viva o sin conexiones"), ("host actual", "Participante")],
               ["El código es la llave de acceso: no hay cuentas."],
               "existe", "Grupo de canal de la sala (collab/groups.py) y código en la dirección del lienzo"),
    "Participante": _c("Participante", "entidad", "nucleo",
                       "Quien trabaja en una sala, identificado por un código anónimo y un nombre visible.",
                       [("identificador anónimo", "Código único"), ("nombre visible", "Texto"), ("rol", "Diseñador o Colaborador"),
                        ("última actividad", "Fecha y hora")],
                       ["El nombre no pasa de 40 caracteres.", "El rol existe solo mientras la sala está viva."],
                       "existe", "collab/models.py Participant; collab/roles.py y collab/identity.py (Redis); identity.service.ts"),
    "EventoActividad": _c("Evento de Actividad", "entidad", "nucleo",
                          "Lo que alguien (o la IA) hizo en la sala, para saber quién hizo qué.",
                          [("autor", "Nombre y tipo (persona o IA)"), ("tipo de acción", "Texto"), ("resumen", "Texto"),
                           ("datos", "Texto estructurado"), ("momento", "Fecha y hora")],
                          ["Persistente. Los datos no pasan de 8 KB y el resumen de 255 caracteres.",
                           "No se registran los movimientos ni los cambios de tamaño."],
                          "cambia (C3)", "collab/models.py ActivityEvent; collab/activity.py ORMActivityStore"),
    # -- edición del diagrama
    "Lienzo": _c("Lienzo", "interfaz", "edicion",
                 "La ventana principal del editor: donde A1 y A2 dibujan y ven el diagrama.",
                 [("elemento seleccionado", "Clase UML o Relación UML"), ("ampliación", "Número"), ("aviso", "Texto")],
                 ["Responde sin esperar al servidor: el diagrama vive en el navegador."],
                 "existe", "app/diagram/diagram.ts y joint-setup.ts (componente Diagram)"),
    "ControlModelado": _c("Control de Modelado", "control", "edicion",
                          "Coordina los cambios que una persona o la IA hacen al diagrama.",
                          [], ["Los tipos de relación y las multiplicidades siguen UML 2.5."],
                          "existe", "services/diagram/diagram.service.ts, edition.service.ts, relationship.service.ts"),
    "ControlSincronizacion": _c("Control de Sincronización", "control", "edicion",
                                "Mantiene el mismo diagrama en todas las pantallas de la sala y lo respalda.",
                                [("pantallas conectadas", "Número")],
                                ["Tiempo real con dos o tres personas.", "Un diagrama que se carga de nuevo no revive lo borrado."],
                                "existe", "services/colaboration/collaboration.service.ts, remote-application.service.ts, p2p.service.ts; "
                                          "collab/consumers.py CanvasConsumer"),
    "Diagrama": _c("Diagrama", "entidad", "edicion",
                   "El diagrama de clases UML de la sala.",
                   [("clases", "Lista de Clase UML"), ("relaciones", "Lista de Relación UML"), ("último cambio", "Fecha y hora")],
                   ["Tiene como máximo 60 clases y 150 relaciones por cada cambio de la IA."],
                   "existe", "Grafo de JointJS en diagram.service.ts; DTO en services/exports/diagram-export.service.ts"),
    "ClaseUML": _c("Clase UML", "entidad", "edicion",
                   "Una clase del diagrama con su nombre, atributos y métodos.",
                   [("nombre", "Texto"), ("atributos", "Lista de texto"), ("métodos", "Lista de texto"), ("posición", "Coordenadas"),
                    ("tamaño", "Medidas")],
                   [], "existe", "UmlClass en diagram.service.ts; UmlClassDTO"),
    "RelacionUML": _c("Relación UML", "entidad", "edicion",
                      "La unión entre dos clases: asociación, agregación, composición, generalización o dependencia.",
                      [("tipo", "Tipo de relación UML"), ("multiplicidad de origen", "Texto"), ("multiplicidad de destino", "Texto"),
                       ("etiqueta", "Texto")],
                      [], "existe", "buildRelationship en diagram.service.ts; UmlRelationshipDTO"),
    "OperacionEdicion": _c("Operación de Edición", "entidad", "edicion",
                           "Un cambio pequeño al diagrama (agregar, editar, mover, eliminar) que viaja a las demás pantallas.",
                           [("tipo", "Texto"), ("elemento afectado", "Clase UML o Relación UML"), ("valor", "Texto"),
                            ("autor", "Participante"), ("momento", "Fecha y hora")],
                           ["Es efímera: no se guarda; lo que se guarda es su resumen en la actividad."],
                           "existe", "Op en collaboration.service.ts; mensajes de CanvasConsumer"),
    "RespaldoDiagrama": _c("Respaldo del Diagrama", "entidad", "edicion",
                           "La última copia del diagrama de la sala, guardada en el servidor.",
                           [("sala", "Código de sala"), ("contenido", "Diagrama completo"), ("guardado en", "Fecha y hora")],
                           ["Persistente: una copia por sala, que se reemplaza 1,5 s después de la última edición y sobrevive a reinicios.",
                            "Un respaldo atrasado no pisa lo que ya envió la sala."],
                           "existe", "uml_api/models.py BackupUML; backup.service.ts; views.set_backupUML y get_backupUML"),
    # -- actividad del equipo y seguimiento móvil
    "PanelActividad": _c("Panel de Actividad", "interfaz", "actividad",
                         "El panel donde A1 y A2 ven quién hizo qué y aplican las ideas de la IA.",
                         [("eventos mostrados", "Lista de Evento de Actividad"), ("idea en aplicación", "Idea de Revisión")],
                         [], "cambia (C2)", "app/activity-panel/activity-panel.ts"),
    "ControlActividad": _c("Control de Actividad", "control", "actividad",
                           "Registra lo que pasa en la sala y entrega el historial reciente.",
                           [("eventos por minuto", "Número")],
                           ["Un fallo al registrar no frena la edición.", "Hasta 60 eventos por minuto por conexión; las ediciones seguidas del mismo "
                                                                          "texto se juntan en un solo evento."],
                           "existe", "collab/consumers.py _record_activity; collab/activity.py; uml_api/views.py get_room_activity"),
    "VistaSeguimiento": _c("Vista de Seguimiento", "interfaz", "seguimiento",
                           "La pantalla de solo lectura para seguir la sala desde el celular.",
                           [("avisos autorizados", "Sí o no"), ("estado de la conexión", "Texto")],
                           ["No tiene controles de edición.", "Los avisos funcionan con la página abierta."],
                           "cambia (C2)", "app/follow-view/follow-view.ts"),
    "ControlSeguimiento": _c("Control de Seguimiento", "control", "seguimiento",
                             "Conecta a quien sigue la sala en solo lectura y le entrega el estado.",
                             [("seguidores conectados", "Número")],
                             ["Hasta diez seguidores por sala.", "Un seguidor no cuenta como participante ni como host."],
                             "existe", "collab/consumers.py _connect_viewer y _allow_viewer_state_request"),
    # -- asistencia inteligente
    "PanelChatIA": _c("Panel de Chat con la IA", "interfaz", "ia",
                      "El chat de la sala con la IA, donde se pregunta, se pide una revisión o se pide un cambio.",
                      [("modo", "Preguntar, Pedir cambio o Revisar"), ("mensaje escrito", "Texto"), ("esperando respuesta", "Sí o no")],
                      ["El mensaje no pasa de 2000 caracteres.", "Muestra «Pensando (a pedido de X)» a toda la sala."],
                      "cambia (C1)", "app/ia-chat-panel/ia-chat-panel.ts"),
    "PanelGenerarModelo": _c("Panel Generar Modelo", "interfaz", "ia",
                             "El cuadro donde se escribe o se dicta lo que la IA debe hacer con el diagrama.",
                             [("instrucción", "Texto"), ("dictado activo", "Sí o no")],
                             ["Para dictar hace falta Google Chrome con HTTPS."],
                             "existe", "app/side-panel/side-panel.ts y diagram.ts generateFromPrompt"),
    "PanelImportacionImagen": _c("Panel de Importación de Imagen", "interfaz", "ia",
                                 "Donde se elige la imagen de un diagrama y se decide si reemplaza o se combina con el actual.",
                                 [("imagen elegida", "Imagen"), ("decisión", "Reemplazar o Combinar")],
                                 [], "existe", "app/side-panel/side-panel.ts onImportImage"),
    "InterfazServicioIA": _c("Interfaz del Servicio de IA", "interfaz", "ia",
                             "La comunicación con el servicio de IA (el actor A3): le envía pedidos y recibe sus respuestas.",
                             [("proveedor", "Nube o local"), ("tiempo máximo de espera", "Duración")],
                             ["El proveedor es intercambiable sin que el resto lo note.",
                              "Con el proveedor en la nube los datos viajan fuera del sistema."],
                             "existe", "uml_api/services/ai_provider.py (AIProvider, GeminiProvider, OllamaProvider) y services_gemini.py"),
    "ControlIA": _c("Control de IA", "control", "ia",
                    "Coordina cada pedido a la IA: comprueba los topes, arma el contexto, valida lo que devuelve y lo aplica.",
                    [("solicitante", "Participante"), ("eliminaciones pendientes", "Número")],
                    ["Atiende un pedido a la vez por sala.", "Topes: 12 pedidos por minuto por persona, 30 por sala y 60 en todo el servicio.",
                     "La IA no hace nada hasta que alguien se lo pide."],
                    "cambia (C1)", "uml_api/chat_views.py ia_chat; services/ia_context.py y change_guard.py; "
                                   "ia-chat.service.ts e ia-actions.service.ts"),
    "ControlImportacionImagen": _c("Control de Importación de Imagen", "control", "ia",
                                   "Coordina el reconocimiento de un diagrama a partir de una imagen.",
                                   [], ["La imagen se envía al servicio de IA: los datos viajan fuera del sistema."],
                                   "existe", "uml_api/views.py analyze_uml_image; uml-image.service.ts"),
    "ConversacionSala": _c("Conversación de la Sala", "entidad", "ia",
                           "La conversación única de la sala con la IA: la ven y la alimentan todos.",
                           [("sala", "Código de sala"), ("estado", "Libre o pensando"), ("solicitante en curso", "Participante")],
                           ["Persistente. No hay conversaciones privadas: es una sola instancia de IA para toda la sala (RA-02)."],
                           "cambia (C1, C3)", "Hoy: uml_api/models de collab ChatMessage, una conversación por participante"),
    "MensajeConversacion": _c("Mensaje de Conversación", "entidad", "ia",
                              "Una pregunta de una persona o una respuesta de la IA.",
                              [("autor", "Participante o IA"), ("modo", "Texto"), ("contenido", "Texto"), ("momento", "Fecha y hora")],
                              ["Persistente. Cada mensaje no pasa de 2000 caracteres."],
                              "cambia (C1, C3)", "collab/models.py ChatMessage"),
    "IdeaRevision": _c("Idea de Revisión", "entidad", "ia",
                       "Una sugerencia que la IA publica en una revisión y que cualquiera puede aplicar una sola vez.",
                       [("descripción", "Texto"), ("instrucción", "Texto"), ("estado", "Libre, reservada o aplicada"),
                        ("reservada por", "Participante"), ("reservada desde", "Fecha y hora")],
                       ["Hasta cinco por revisión.", "Una reserva que nadie confirma vence a los 150 segundos."],
                       "existe", "ActivityEvent.data y uml_api/chat_views.py claim_suggestion (RESERVATION_TTL)"),
    "PedidoIA": _c("Pedido a la IA", "entidad", "ia",
                   "Cada pedido que una persona le hace a la IA, con su resultado; sirve para contar los topes de uso.",
                   [("solicitante", "Participante"), ("momento", "Fecha y hora"), ("modo", "Texto"), ("resultado", "Bien o falló")],
                   ["Persistente, y cuenta aunque el pedido falle: un proveedor caído también gasta cupo."],
                   "existe", "collab/models.py IaAttempt; chat_views._reserve_attempt"),
    "CambioPropuesto": _c("Cambio Propuesto", "entidad", "ia",
                          "Los cambios que la IA propone al diagrama, antes de aplicarse.",
                          [("clases afectadas", "Lista de Clase UML"), ("relaciones afectadas", "Lista de Relación UML"),
                           ("elementos que eliminaría", "Número")],
                          ["Efímero. Se rechaza si pasa de 60 clases o 150 relaciones."],
                          "existe", "JSON de cambios; uml_api/services/change_guard.py validate_changes y count_destructive"),
    "ModeloReconocido": _c("Modelo Reconocido", "entidad", "ia",
                           "Las clases y relaciones que el servicio de IA reconoce en una imagen.",
                           [("clases", "Lista de Clase UML"), ("relaciones", "Lista de Relación UML")],
                           ["Efímero."], "existe", "Respuesta de analyze_uml_image"),
    # -- asistente de ayuda
    "PanelAyuda": _c("Panel de Ayuda", "interfaz", "ayuda",
                     "Donde se pregunta cómo usar la herramienta y se lee la respuesta paso a paso.",
                     [("pregunta", "Texto"), ("respuesta", "Texto")],
                     ["Está disponible desde la página principal y dentro de la sala."],
                     "nuevo (C4)", "Por crear en el frontend"),
    "ControlAyuda": _c("Control de Ayuda", "control", "ayuda",
                       "Responde una duda de uso con el conocimiento de la herramienta, sin tocar el diagrama.",
                       [], ["Solo responde sobre la herramienta.", "Tiene el mismo tope de uso que la IA (RA-03).",
                            "La conversación es personal, no de la sala."],
                       "nuevo (C4)", "Por crear en uml_api"),
    "ConocimientoAyuda": _c("Conocimiento de Ayuda", "entidad", "ayuda",
                            "El manual de usuario y la lista de funciones en que se apoya el asistente.",
                            [("manual", "Texto"), ("funciones", "Lista de texto")],
                            ["Solo lectura. Debe coincidir con la versión de la herramienta."],
                            "nuevo (C4)", "Por crear: el manual del informe y la lista de funciones"),
    # -- intercambio y generación
    "PanelIntercambio": _c("Panel de Intercambio", "interfaz", "intercambio",
                           "Donde se exporta el diagrama (XMI, imagen) o se importa un archivo XMI.",
                           [("formato", "XMI o imagen"), ("archivo elegido", "Archivo")],
                           [], "existe", "app/side-panel/side-panel.ts; diagram.ts exportXmi e importXmi"),
    "PanelGeneracion": _c("Panel de Generación", "interfaz", "intercambio",
                          "Donde se pide el backend, el SQL o el proyecto Flutter.",
                          [("destino", "Backend, SQL o Flutter"), ("nombre del archivo", "Texto")],
                          [], "existe", "app/side-panel/side-panel.ts onGenerate y exportSql"),
    "ControlIntercambio": _c("Control de Intercambio", "control", "intercambio",
                             "Convierte el diagrama a XMI o a imagen y el XMI a diagrama.",
                             [], ["Al importar no se leen archivos locales ni se abren conexiones (XXE)."],
                             "existe", "uml_api/views.py export_xmi e import_xmi; xmi_service.py; xmi.service.ts"),
    "ControlGeneracion": _c("Control de Generación", "control", "intercambio",
                            "Pide a los generadores el proyecto que sale del diagrama.",
                            [], ["Si el generador no responde, no se descarga nada."],
                            "existe", "backend-generator.service.ts; sql-export.service.ts; uml_api/views.py generar_flutter y "
                                      "services/flutter_generator.py; back_generator_uml (Spring Boot)"),
    "ArchivoIntercambio": _c("Archivo de Intercambio", "entidad", "intercambio",
                             "El archivo que sale o entra: XMI 2.1 o una imagen del diagrama.",
                             [("formato", "XMI 2.1 o imagen PNG"), ("contenido", "Texto o imagen"), ("nombre", "Texto")],
                             ["Efímero. Se rechazan las declaraciones DOCTYPE y las entidades externas."],
                             "existe", "Respuesta de export_xmi; archivo recibido por import_xmi"),
    "ProyectoGenerado": _c("Proyecto Generado", "entidad", "intercambio",
                           "El proyecto que produce un generador: Spring Boot con PostgreSQL y Postman, o Flutter con SQLite.",
                           [("tipo", "Backend Spring Boot o Flutter"), ("nombre", "Texto"), ("contenido", "Archivo comprimido")],
                           ["Efímero. El proyecto compila con el Maven Wrapper incluido."],
                           "existe", "Archivo .zip que devuelven los generadores"),
    # -- gestión de la sala
    "PantallaInicio": _c("Pantalla de Inicio", "interfaz", "gestion",
                         "La página principal: crear una sala o unirse con un código, e identificarse con un nombre.",
                         [("código de sala", "Texto"), ("nombre visible", "Texto")],
                         [], "existe", "app/landin-page/landin-page.ts; identity.service.ts"),
    "PanelParticipantes": _c("Panel de Participantes", "interfaz", "gestion",
                             "La lista de quienes están en la sala, con su rol; el Diseñador puede expulsar desde ella.",
                             [("participantes", "Lista de Participante"), ("participante elegido", "Participante")],
                             [], "existe", "app/participants-panel/participants-panel.ts"),
    "ControlIngreso": _c("Control de Ingreso", "control", "gestion",
                         "Lleva a una persona a la sala: la reconoce, le pide un nombre y le asigna un rol.",
                         [], ["Un nombre o identificador inválido no se rechaza: la persona figura con un nombre genérico."],
                         "existe", "collab/consumers.py _handle_hello; roles.py join; identity.service.ts"),
    "ControlExpulsion": _c("Control de Expulsión", "control", "gestion",
                           "Saca a un participante de la sala, solo si lo pide el host.",
                           [], ["El permiso lo verifica el servidor, no el navegador."],
                           "existe", "collab/roles.py remove_by_host; consumers.py force_disconnect"),
    "ControlRecuperacion": _c("Control de Recuperación", "control", "gestion",
                              "Devuelve a la persona el diagrama, la actividad y la conversación de la sala al volver.",
                              [], ["Lo que se guardó antes se recupera aunque la sala haya quedado sin nadie."],
                              "existe", "diagram.ts ngAfterViewInit; collaboration.service.ts init; backup.service.ts getBackup; "
                                        "activity-panel.ts ngOnInit; ia-chat-panel.ts loadHistory"),
}
for _clave, _c_ in CLASES.items():
    _c_["clave"] = _clave

ESTEREOTIPO = {"interfaz": "boundary", "control": "control", "entidad": "entity"}

# ---- relaciones (asociaciones) entre clases del análisis ---------------------------------------------------
# (origen, destino, nombre, multiplicidad en el origen, multiplicidad en el destino, tipo)  tipo: asoc | agr | comp
RELACIONES = [
    # entidades
    ("Diagrama", "ClaseUML", "contiene", "1", "0..*", "comp"),
    ("Diagrama", "RelacionUML", "contiene", "1", "0..*", "comp"),
    ("RelacionUML", "ClaseUML", "une", "0..*", "1..2", "asoc"),
    ("RespaldoDiagrama", "Diagrama", "guarda", "0..1", "1", "asoc"),
    ("OperacionEdicion", "Participante", "la hace", "0..*", "1", "asoc"),
    ("OperacionEdicion", "Diagrama", "cambia", "0..*", "1", "asoc"),
    ("EventoActividad", "Participante", "es de", "0..*", "0..1", "asoc"),
    ("Sala", "Participante", "reúne a", "1", "0..*", "agr"),
    ("EventoActividad", "Sala", "ocurre en", "0..*", "1", "asoc"),
    ("ConversacionSala", "MensajeConversacion", "contiene", "1", "0..*", "comp"),
    ("ConversacionSala", "Sala", "es de", "0..1", "1", "asoc"),
    ("IdeaRevision", "EventoActividad", "viene en", "0..5", "1", "comp"),
    ("PedidoIA", "Participante", "lo pide", "0..*", "1", "asoc"),
    ("MensajeConversacion", "Participante", "lo escribe", "0..*", "0..1", "asoc"),
    ("CambioPropuesto", "Diagrama", "propone cambiar", "0..*", "1", "asoc"),
    ("ModeloReconocido", "Diagrama", "se convierte en", "0..1", "0..1", "asoc"),
    ("ArchivoIntercambio", "Diagrama", "representa a", "0..*", "1", "asoc"),
    ("ProyectoGenerado", "Diagrama", "sale de", "0..*", "1", "asoc"),
    # interfaz - control
    ("PantallaInicio", "ControlIngreso", "pide ingresar a", "1", "1", "asoc"),
    ("PantallaInicio", "ControlRecuperacion", "pide retomar", "1", "1", "asoc"),
    ("PanelParticipantes", "ControlExpulsion", "pide expulsar", "1", "1", "asoc"),
    ("Lienzo", "ControlModelado", "pide cambios", "1", "1", "asoc"),
    ("Lienzo", "ControlSincronizacion", "comparte cambios con", "0..*", "1", "asoc"),
    ("Lienzo", "Diagrama", "muestra", "1", "1", "asoc"),
    ("PanelActividad", "ControlActividad", "pide el historial a", "0..*", "1", "asoc"),
    ("PanelActividad", "ControlIA", "pide aplicar ideas", "1", "1", "asoc"),
    ("PanelActividad", "EventoActividad", "muestra", "1", "0..*", "asoc"),
    ("VistaSeguimiento", "ControlSeguimiento", "pide seguir a", "0..*", "1", "asoc"),
    ("VistaSeguimiento", "Diagrama", "muestra", "1", "1", "asoc"),
    ("PanelChatIA", "ControlIA", "pide consultar", "1", "1", "asoc"),
    ("PanelGenerarModelo", "ControlIA", "pide cambiar", "1", "1", "asoc"),
    ("PanelGenerarModelo", "ControlModelado", "aplica cambios", "1", "1", "asoc"),
    ("PanelImportacionImagen", "ControlImportacionImagen", "pide reconocer", "1", "1", "asoc"),
    ("PanelAyuda", "ControlAyuda", "pide ayuda", "1", "1", "asoc"),
    ("PanelIntercambio", "ControlIntercambio", "pide intercambiar", "1", "1", "asoc"),
    ("PanelGeneracion", "ControlGeneracion", "pide generar", "1", "1", "asoc"),
    # control - entidad, control - control
    ("ControlIngreso", "Sala", "crea o busca", "0..*", "1", "asoc"),
    ("ControlIngreso", "Participante", "registra", "0..*", "0..*", "asoc"),
    ("ControlIngreso", "Lienzo", "abre", "1", "1", "asoc"),
    ("ControlExpulsion", "Participante", "verifica y expulsa a", "1", "0..*", "asoc"),
    ("ControlExpulsion", "Sala", "saca de", "0..*", "1", "asoc"),
    ("ControlExpulsion", "Lienzo", "avisa al expulsado en", "1", "0..*", "asoc"),
    ("ControlRecuperacion", "Participante", "reconoce a", "1", "0..*", "asoc"),
    ("ControlRecuperacion", "ControlSincronizacion", "pide el diagrama a", "1", "1", "asoc"),
    ("ControlRecuperacion", "RespaldoDiagrama", "lee", "1", "0..1", "asoc"),
    ("ControlRecuperacion", "EventoActividad", "recupera", "1", "0..*", "asoc"),
    ("ControlRecuperacion", "ConversacionSala", "recupera", "1", "0..1", "asoc"),
    ("ControlRecuperacion", "Lienzo", "muestra en", "1", "1", "asoc"),
    ("ControlModelado", "Diagrama", "modifica", "1", "1", "asoc"),
    ("ControlModelado", "ClaseUML", "edita", "1", "0..*", "asoc"),
    ("ControlModelado", "RelacionUML", "edita", "1", "0..*", "asoc"),
    ("ControlModelado", "ControlSincronizacion", "avisa a", "1", "1", "asoc"),
    ("ControlSincronizacion", "OperacionEdicion", "reparte", "1", "0..*", "asoc"),
    ("ControlSincronizacion", "RespaldoDiagrama", "guarda", "1", "0..1", "asoc"),
    ("ControlSincronizacion", "Participante", "pide el estado a", "1", "0..*", "asoc"),
    ("VistaSeguimiento", "ControlSincronizacion", "recibe cambios de", "0..*", "1", "asoc"),
    ("ControlActividad", "OperacionEdicion", "escucha", "1", "0..*", "asoc"),
    ("ControlActividad", "Participante", "identifica a", "1", "0..*", "asoc"),
    ("ControlActividad", "EventoActividad", "registra", "1", "0..*", "asoc"),
    ("ControlSeguimiento", "ControlSincronizacion", "pide el diagrama a", "1", "1", "asoc"),
    ("ControlSeguimiento", "RespaldoDiagrama", "lee", "1", "0..1", "asoc"),
    ("ControlSeguimiento", "EventoActividad", "lee", "1", "0..*", "asoc"),
    ("ControlIA", "PedidoIA", "registra", "1", "0..*", "asoc"),
    ("ControlIA", "ConversacionSala", "usa", "1", "1", "asoc"),
    ("ControlIA", "MensajeConversacion", "guarda", "1", "0..*", "asoc"),
    ("ControlIA", "Diagrama", "lee", "1", "1", "asoc"),
    ("ControlIA", "EventoActividad", "lee y publica", "1", "0..*", "asoc"),
    ("ControlIA", "IdeaRevision", "crea y reserva", "1", "0..*", "asoc"),
    ("ControlIA", "CambioPropuesto", "valida", "1", "0..*", "asoc"),
    ("ControlIA", "InterfazServicioIA", "consulta por", "1", "1", "asoc"),
    ("ControlImportacionImagen", "InterfazServicioIA", "consulta por", "1", "1", "asoc"),
    ("ControlImportacionImagen", "ModeloReconocido", "arma", "1", "0..*", "asoc"),
    ("ControlImportacionImagen", "ControlModelado", "aplica por", "1", "1", "asoc"),
    ("PanelImportacionImagen", "ControlModelado", "aplica el modelo por", "1", "1", "asoc"),
    ("ControlAyuda", "PedidoIA", "registra", "1", "0..*", "asoc"),
    ("ControlAyuda", "ConocimientoAyuda", "consulta", "1", "1", "asoc"),
    ("ControlAyuda", "InterfazServicioIA", "consulta por", "1", "1", "asoc"),
    ("ControlIntercambio", "Diagrama", "lee y crea", "1", "1", "asoc"),
    ("ControlIntercambio", "ArchivoIntercambio", "genera y valida", "1", "0..*", "asoc"),
    ("ControlIntercambio", "ControlSincronizacion", "avisa a", "1", "1", "asoc"),
    ("ControlGeneracion", "Diagrama", "lee", "1", "1", "asoc"),
    ("ControlGeneracion", "ProyectoGenerado", "pide", "1", "0..*", "asoc"),
]

# ---- colaboraciones ----------------------------------------------------------------------------------------
# Un diagrama de colaboración por flujo diferenciado (8.6.2.2). `actores`: instancias de actor {clave: (actor, rótulo)}. Cada mensaje es
# (origen, destino, para qué): el texto es el propósito de quien invoca y origina una responsabilidad de quien recibe; no es una operación.
A_COL = ("A2", "Colaborador")


def _col(id_, cu, nombre, actores, mensajes, flujo, especiales=(), reutiliza=None, extiende=None, continuacion=False):
    objetos = []
    for origen, destino, _ in mensajes:
        for extremo in (origen, destino):
            if extremo in CLASES and extremo not in objetos:
                objetos.append(extremo)
    return dict(id=id_, cu=cu, nombre=nombre, actores=actores, mensajes=mensajes, objetos=objetos, flujo=flujo,
                especiales=list(especiales), reutiliza=reutiliza, extiende=extiende, continuacion=continuacion)


COLABORACIONES = [
    _col("COL-01", "CU1", "Ingresar a una sala de trabajo",
         {"U": A_COL},
         [("U", "PantallaInicio", "Crear una sala o unirse con un código"),
          ("PantallaInicio", "ControlIngreso", "Ingresar a la sala indicada"),
          ("ControlIngreso", "Sala", "Crear la sala o comprobar que existe"),
          ("ControlIngreso", "Participante", "Reconocer la identidad anónima o crearla"),
          ("ControlIngreso", "PantallaInicio", "Pedir el nombre visible si falta"),
          ("ControlIngreso", "Participante", "Registrar el nombre y asignar el rol"),
          ("ControlIngreso", "Lienzo", "Abrir el editor de la sala")],
         ["El Colaborador crea una sala o escribe un código en la **Pantalla de Inicio**, que se lo pasa al **Control de Ingreso**.",
          "El control pide a la **Sala** que se cree o se compruebe que existe, y reconoce al **Participante** por su identificador anónimo "
          "o le crea uno.",
          "Si todavía no tiene nombre, el control hace que la pantalla se lo pida; con el nombre, registra al participante y le asigna el rol "
          "(Diseñador si es el primero de una sala viva, Colaborador si no).",
          "Por último, el control abre el **Lienzo** de la sala."],
         ["El rol existe solo mientras la sala está viva (RF-16, RF-17)."]),
    _col("COL-02", "CU2", "Modelar el diagrama de clases UML",
         {"U": A_COL},
         [("U", "Lienzo", "Pedir una clase nueva y escribir sus miembros"),
          ("Lienzo", "ControlModelado", "Crear y editar la clase"),
          ("ControlModelado", "Diagrama", "Agregar la clase"),
          ("ControlModelado", "ClaseUML", "Definir el nombre, los atributos y los métodos"),
          ("ControlModelado", "RelacionUML", "Establecer el tipo y las multiplicidades de la unión"),
          ("ControlModelado", "Diagrama", "Resolver «muchos a muchos» con una clase asociativa"),
          ("ControlModelado", "Lienzo", "Mostrar el diagrama actualizado")],
         ["El Colaborador pide en el **Lienzo** una clase nueva y escribe su nombre, atributos y métodos, o une dos clases.",
          "El lienzo le pasa el pedido al **Control de Modelado**, que agrega la clase al **Diagrama** y le define sus miembros en la **Clase UML**.",
          "Al unir dos clases, el control fija en la **Relación UML** su tipo y sus multiplicidades; si queda «muchos» en ambos extremos, "
          "pide al diagrama que la resuelva con una clase asociativa.",
          "El control devuelve al lienzo el diagrama actualizado."],
         ["Los tipos de relación y las multiplicidades siguen UML 2.5.", "El lienzo vive en el navegador: no espera al servidor."]),
    _col("COL-03", "CU3", "Editar y compartir un cambio",
         {"A": ("A2", "Colaborador (autor)"), "B": ("A2", "Colaborador (observador)")},
         [("A", "Lienzo", "Hacer un cambio en el diagrama (CU2)"),
          ("Lienzo", "ControlSincronizacion", "Compartir el cambio con la sala"),
          ("ControlSincronizacion", "OperacionEdicion", "Crear la operación del cambio"),
          ("OperacionEdicion", "Diagrama", "Aplicarse al diagrama de cada pantalla"),
          ("ControlSincronizacion", "Lienzo", "Entregar la operación a las demás pantallas"),
          ("Lienzo", "B", "Mostrar el cambio"),
          ("ControlSincronizacion", "RespaldoDiagrama", "Guardar el estado cada cierto tiempo")],
         ["Cuando un Colaborador cambia el diagrama (CU2), su **Lienzo** se lo cuenta al **Control de Sincronización**.",
          "El control crea la **Operación de Edición** del cambio y se la entrega al lienzo de las demás pantallas, donde la operación se "
          "aplica al **Diagrama**.",
          "Cada Colaborador que mira ve el cambio al instante.",
          "Cada cierto tiempo el control guarda un **Respaldo del Diagrama** en el servidor."],
         ["Funciona con dos o tres personas a la vez.", "Los permisos de edición son iguales para todos (RF-13)."]),
    _col("COL-04", "CU3", "Entrar a una sala que ya tiene gente",
         {"U": ("A2", "Colaborador (recién llegado)")},
         [("U", "Lienzo", "Entrar a la sala (CU1)"),
          ("Lienzo", "ControlSincronizacion", "Pedir el diagrama de la sala"),
          ("ControlSincronizacion", "Participante", "Pedir el estado completo a un participante conectado"),
          ("ControlSincronizacion", "RespaldoDiagrama", "Usar el último respaldo si la sala está vacía"),
          ("ControlSincronizacion", "Lienzo", "Entregar el diagrama recibido"),
          ("Lienzo", "Diagrama", "Reconstruir el diagrama recibido"),
          ("Lienzo", "U", "Mostrar el diagrama")],
         ["Quien llega a la sala (CU1) abre el **Lienzo**, que le pide el diagrama de la sala al **Control de Sincronización**.",
          "Si hay alguien conectado, el control le pide el estado completo a ese **Participante**; si la sala está vacía, usa el último "
          "**Respaldo del Diagrama**.",
          "El control entrega el diagrama al lienzo, que reconstruye el **Diagrama** y se lo muestra al Colaborador."],
         ["Un diagrama que se carga de nuevo no revive lo que alguien borró."]),
    _col("COL-05", "CU4", "Expulsar a un participante",
         {"D": ("A1", "Diseñador"), "X": ("A2", "Colaborador (expulsado)")},
         [("D", "PanelParticipantes", "Pedir expulsar a un participante"),
          ("PanelParticipantes", "ControlExpulsion", "Expulsar al participante elegido"),
          ("ControlExpulsion", "Participante", "Verificar que quien lo pide es el host"),
          ("ControlExpulsion", "Sala", "Sacar al expulsado de la sala"),
          ("ControlExpulsion", "PanelParticipantes", "Actualizar la presencia de todos"),
          ("ControlExpulsion", "Lienzo", "Avisar al expulsado"),
          ("Lienzo", "X", "Mostrar «El host te expulsó de la sala»")],
         ["El Diseñador elige a alguien en el **Panel de Participantes**, que se lo pide al **Control de Expulsión**.",
          "El control verifica en el **Participante** que quien pide es el host actual; si no lo es, rechaza el pedido y no pasa nada.",
          "Si lo es, saca al expulsado de la **Sala** y actualiza la presencia de todos en el panel.",
          "Por último avisa al expulsado, cuyo **Lienzo** le muestra que el host lo sacó de la sala."],
         ["El permiso lo verifica el servidor, no el navegador."]),
    _col("COL-06", "CU5", "Retomar el trabajo en otra sesión",
         {"U": A_COL},
         [("U", "PantallaInicio", "Abrir la sala con su código (CU1)"),
          ("PantallaInicio", "ControlRecuperacion", "Retomar el trabajo en la sala"),
          ("ControlRecuperacion", "Participante", "Reconocer a la persona por su identificador"),
          ("ControlRecuperacion", "ControlSincronizacion", "Pedir el diagrama de la sala viva (CU3)"),
          ("ControlRecuperacion", "RespaldoDiagrama", "Leer el último respaldo si no hay nadie conectado"),
          ("ControlRecuperacion", "EventoActividad", "Recuperar el historial de actividad"),
          ("ControlRecuperacion", "ConversacionSala", "Recuperar la conversación con la IA"),
          ("ControlRecuperacion", "Lienzo", "Mostrar lo recuperado")],
         ["El Colaborador vuelve a abrir la sala con su código (CU1) y la **Pantalla de Inicio** le pide al **Control de Recuperación** "
          "que retome el trabajo.",
          "El control reconoce al **Participante** por su identificador anónimo y pide el diagrama a la sala viva (CU3) o, si no hay nadie "
          "conectado, lee el último **Respaldo del Diagrama**.",
          "Recupera también el historial de **Evento de Actividad** y la **Conversación de la Sala** con la IA.",
          "El **Lienzo** muestra al Colaborador lo recuperado."],
         ["Lo que se guardó se recupera aunque la sala haya quedado sin nadie."]),
    _col("COL-07", "CU6", "Consultar la actividad del equipo",
         {"U": A_COL},
         [("U", "PanelActividad", "Abrir el panel de actividad"),
          ("PanelActividad", "ControlActividad", "Pedir el historial reciente"),
          ("ControlActividad", "EventoActividad", "Leer los eventos más recientes de la sala"),
          ("ControlActividad", "PanelActividad", "Entregar los eventos del más nuevo al más viejo"),
          ("ControlActividad", "OperacionEdicion", "Escuchar las acciones nuevas de la sala"),
          ("ControlActividad", "Participante", "Identificar quién hizo la acción"),
          ("ControlActividad", "EventoActividad", "Registrar la acción, sin movimientos y juntando ediciones seguidas")],
         ["El Colaborador abre el **Panel de Actividad**, que le pide el historial reciente al **Control de Actividad**.",
          "El control lee los **Evento de Actividad** más recientes de la sala y se los entrega al panel, del más nuevo al más viejo.",
          "Mientras el panel está abierto, el control escucha las **Operación de Edición** de la sala, identifica al **Participante** que "
          "hizo cada una y la registra como un evento nuevo, que llega al panel en vivo."],
         ["El registro no degrada la edición: los movimientos no se registran y las ediciones seguidas se juntan."]),
    _col("COL-08", "CU7, CU9", "Consultar a la IA con el contexto de la sala (colaboración reutilizable)",
         {},
         [("ControlIA", "PedidoIA", "Reservar el cupo de la persona, de la sala y del servicio"),
          ("ControlIA", "ConversacionSala", "Tomar el turno de la sala y leer la conversación"),
          ("ControlIA", "Diagrama", "Obtener el diagrama actual"),
          ("ControlIA", "EventoActividad", "Obtener la actividad reciente"),
          ("ControlIA", "InterfazServicioIA", "Enviar el pedido con su contexto"),
          ("InterfazServicioIA", "S", "Pedir la respuesta o los cambios")],
         ["Cuando el **Control de IA** recibe un pedido, reserva el cupo en el **Pedido a la IA**; si se pasa de los topes, lo rechaza.",
          "Toma el turno de la **Conversación de la Sala** (la IA atiende un pedido a la vez) y arma el contexto con el **Diagrama** actual, "
          "la actividad reciente y la conversación.",
          "Envía el pedido por la **Interfaz del Servicio de IA**, que se lo pide al Servicio de IA."],
         ["La IA no hace nada hasta que alguien se lo pide.", "El proveedor es intercambiable (RA-01)."],
         reutiliza=["CU7", "CU9"]),
    _col("COL-09", "CU7", "Aplicar los cambios que devuelve la IA",
         {"U": A_COL},
         [("ControlIA", "CambioPropuesto", "Validar los cambios y contar lo que eliminarían"),
          ("ControlIA", "PanelGenerarModelo", "Pedir confirmación si eliminan elementos"),
          ("PanelGenerarModelo", "U", "Mostrar la confirmación"),
          ("U", "PanelGenerarModelo", "Confirmar o rechazar"),
          ("PanelGenerarModelo", "ControlModelado", "Aplicar los cambios por la ruta de la edición manual (CU2)"),
          ("ControlModelado", "Diagrama", "Agregar, cambiar o eliminar los elementos"),
          ("ControlModelado", "ControlSincronizacion", "Avisar a la sala del cambio (CU3)"),
          ("ControlIA", "EventoActividad", "Registrar «IA, a pedido de» quien lo pidió"),
          ("ControlIA", "MensajeConversacion", "Guardar el pedido y la respuesta")],
         ["Con los cambios que devolvió el servicio de IA (COL-08), el **Control de IA** crea el **Cambio Propuesto**, lo valida y cuenta "
          "cuántos elementos eliminaría.",
          "Si elimina elementos, el **Panel Generar Modelo** muestra la confirmación al Colaborador; si la rechaza, no cambia nada.",
          "Con su confirmación, el panel pide al **Control de Modelado** aplicar los cambios por la misma ruta de la edición manual (CU2); "
          "el control cambia el **Diagrama** y avisa al **Control de Sincronización** para que lo vea toda la sala (CU3).",
          "El Control de IA registra en un **Evento de Actividad** que la IA actuó a pedido de quien lo pidió y guarda el pedido y la "
          "respuesta como **Mensaje de Conversación**."],
         ["Los cambios enormes se rechazan.", "Si el servicio falla o devuelve algo inválido, el diagrama no cambia."],
         reutiliza=["COL-08"], continuacion=True),
    _col("COL-10", "CU8", "Crear el modelo desde una imagen",
         {"U": A_COL},
         [("U", "PanelImportacionImagen", "Elegir la imagen del diagrama"),
          ("PanelImportacionImagen", "ControlImportacionImagen", "Reconocer el diagrama de la imagen"),
          ("ControlImportacionImagen", "InterfazServicioIA", "Enviar la imagen"),
          ("InterfazServicioIA", "S", "Pedir las clases y relaciones que reconoce"),
          ("ControlImportacionImagen", "ModeloReconocido", "Armar el modelo reconocido"),
          ("ControlImportacionImagen", "PanelImportacionImagen", "Mostrar el modelo reconocido"),
          ("U", "PanelImportacionImagen", "Elegir reemplazar o combinar"),
          ("PanelImportacionImagen", "ControlModelado", "Aplicar el modelo elegido"),
          ("ControlModelado", "Diagrama", "Reemplazar el diagrama o combinarlo"),
          ("ControlModelado", "ControlSincronizacion", "Avisar a la sala del cambio (CU3)")],
         ["El Colaborador elige una imagen en el **Panel de Importación de Imagen**, que se la pasa al **Control de Importación de Imagen**.",
          "El control la envía por la **Interfaz del Servicio de IA**, que le pide al servicio las clases y relaciones que reconoce, y arma el "
          "**Modelo Reconocido**, que el panel muestra.",
          "El Colaborador elige reemplazar el diagrama actual o combinarlo; el panel pide al **Control de Modelado** aplicarlo al **Diagrama** "
          "y este avisa al **Control de Sincronización** para que lo vea la sala (CU3)."],
         ["La imagen se envía al servicio de IA: los datos viajan fuera del sistema.",
          "Si la imagen no es legible, el diagrama no cambia."]),
    _col("COL-11", "CU9", "Consultar a la IA y publicar una revisión",
         {"U": A_COL},
         [("U", "PanelChatIA", "Elegir el modo y escribir el mensaje"),
          ("PanelChatIA", "ControlIA", "Consultar a la IA (COL-08)"),
          ("ControlIA", "MensajeConversacion", "Guardar la pregunta y la respuesta en la conversación"),
          ("ControlIA", "PanelChatIA", "Mostrar la respuesta a toda la sala"),
          ("ControlIA", "IdeaRevision", "Crear hasta cinco ideas, en modo «Revisar»"),
          ("ControlIA", "EventoActividad", "Publicar la revisión con sus ideas"),
          ("ControlIA", "ConversacionSala", "Liberar el turno de la sala")],
         ["El Colaborador elige el modo y escribe su mensaje en el **Panel de Chat con la IA**, que se lo pasa al **Control de IA**, y este "
          "consulta al servicio de IA como se muestra en COL-08.",
          "Con la respuesta, el control guarda la pregunta y la respuesta como **Mensaje de Conversación** y las muestra en el panel de "
          "toda la sala.",
          "En modo «Revisar», el control crea hasta cinco **Idea de Revisión** y las publica en un **Evento de Actividad**; ninguna se "
          "aplica sola.",
          "Al final libera el turno de la **Conversación de la Sala**."],
         ["Hay una sola instancia de IA para toda la sala y su conversación es la de todos (RA-02).",
          "Si el servicio falla, no se guarda nada y el mensaje es claro."],
         reutiliza=["COL-08"]),
    _col("COL-12", "CU9", "Aplicar una idea de la revisión",
         {"U": A_COL},
         [("U", "PanelActividad", "Pulsar «Aplicar» en una idea"),
          ("PanelActividad", "ControlIA", "Aplicar la idea elegida"),
          ("ControlIA", "IdeaRevision", "Reservarla para esa persona si nadie la tomó"),
          ("ControlIA", "CambioPropuesto", "Obtener los cambios de la idea (CU7, COL-09)"),
          ("ControlIA", "IdeaRevision", "Marcarla como aplicada para toda la sala"),
          ("ControlIA", "EventoActividad", "Registrar quién la aplicó")],
         ["El Colaborador pulsa «Aplicar» en una idea del **Panel de Actividad**, que se lo pide al **Control de IA**.",
          "El control reserva la **Idea de Revisión** para esa persona (si otra ya la tomó, avisa y no la repite) y la ejecuta como un pedido "
          "de cambio a su nombre: ese es el punto de extensión que ejecuta CU7 (COL-08 y COL-09) y produce el **Cambio Propuesto**.",
          "Aplicada la idea, el control la marca como aplicada para toda la sala y registra quién lo hizo en un **Evento de Actividad**."],
         ["Una reserva que nadie confirma vence a los 150 segundos.", "Cada idea se aplica una sola vez."],
         extiende="CU7"),
    _col("COL-13", "CU10", "Exportar el diagrama",
         {"U": A_COL},
         [("U", "PanelIntercambio", "Elegir exportar el diagrama (XMI o imagen)"),
          ("PanelIntercambio", "ControlIntercambio", "Exportar el diagrama"),
          ("ControlIntercambio", "Diagrama", "Obtener clases, relaciones, posiciones y tamaños"),
          ("ControlIntercambio", "ArchivoIntercambio", "Generar el archivo XMI o la imagen"),
          ("ControlIntercambio", "PanelIntercambio", "Entregar el archivo para descargarlo")],
         ["El Colaborador elige exportar en el **Panel de Intercambio**, que se lo pide al **Control de Intercambio**.",
          "El control obtiene las clases y relaciones del **Diagrama**, con su posición y tamaño, y genera el **Archivo de Intercambio** "
          "(XMI 2.1 o imagen).",
          "El control entrega el archivo al panel, que lo descarga; Enterprise Architect puede abrirlo."],
         ["La ida y la vuelta se probaron con Enterprise Architect 17.2."]),
    _col("COL-14", "CU10", "Importar un archivo XMI",
         {"U": A_COL},
         [("U", "PanelIntercambio", "Elegir un archivo XMI"),
          ("PanelIntercambio", "ControlIntercambio", "Importar el archivo"),
          ("ControlIntercambio", "ArchivoIntercambio", "Validar y rechazar las construcciones inseguras"),
          ("ControlIntercambio", "Diagrama", "Construir las clases y relaciones del modelo"),
          ("ControlIntercambio", "ControlSincronizacion", "Avisar a la sala del cambio (CU3)"),
          ("ControlIntercambio", "PanelIntercambio", "Mostrar el diagrama importado")],
         ["El Colaborador elige un archivo XMI en el **Panel de Intercambio**, que se lo pasa al **Control de Intercambio**.",
          "El control valida el **Archivo de Intercambio**: rechaza las declaraciones DOCTYPE y las entidades externas.",
          "Si es válido, construye las clases y relaciones del **Diagrama**, avisa al **Control de Sincronización** para que lo vea la sala "
          "(CU3) y se lo muestra al Colaborador."],
         ["Al importar no se leen archivos locales ni se abren conexiones (XXE).", "Un archivo inválido no cambia el diagrama."]),
    _col("COL-15", "CU11", "Generar el backend del sistema",
         {"U": ("A1", "Diseñador")},
         [("U", "PanelGeneracion", "Elegir exportar el backend (o el SQL)"),
          ("PanelGeneracion", "ControlGeneracion", "Generar el backend"),
          ("ControlGeneracion", "Diagrama", "Obtener el diagrama para el generador"),
          ("ControlGeneracion", "ProyectoGenerado", "Pedir el proyecto Spring Boot con PostgreSQL y Postman"),
          ("ControlGeneracion", "PanelGeneracion", "Entregar el archivo para descargarlo")],
         ["El Diseñador elige exportar el backend en el **Panel de Generación**, que se lo pide al **Control de Generación**.",
          "El control toma el **Diagrama** y le pide al generador el **Proyecto Generado** (Spring Boot con PostgreSQL, la colección de "
          "Postman y el SQL).",
          "El control entrega el archivo al panel, que lo descarga."],
         ["Java 21 y Spring Boot 3.5.", "Si el generador no responde, no se descarga nada."]),
    _col("COL-16", "CU12", "Generar la aplicación móvil",
         {"U": ("A1", "Diseñador")},
         [("U", "PanelGeneracion", "Elegir exportar el proyecto Flutter"),
          ("PanelGeneracion", "ControlGeneracion", "Generar el proyecto móvil"),
          ("ControlGeneracion", "Diagrama", "Obtener el diagrama para el generador"),
          ("ControlGeneracion", "ProyectoGenerado", "Pedir el proyecto Flutter con SQLite local"),
          ("ControlGeneracion", "PanelGeneracion", "Entregar el archivo para descargarlo")],
         ["El Diseñador elige exportar Flutter en el **Panel de Generación**, que se lo pide al **Control de Generación**.",
          "El control toma el **Diagrama** y le pide el **Proyecto Generado** (Flutter con modelos, SQLite local y pantallas CRUD).",
          "El control entrega el archivo al panel, que lo descarga."],
         ["El CRUD generado funciona sin red y los datos persisten."]),
    _col("COL-17", "CU13", "Mantenerse informado desde el celular",
         {"U": A_COL},
         [("U", "VistaSeguimiento", "Abrir el enlace de seguimiento"),
          ("VistaSeguimiento", "ControlSeguimiento", "Seguir la sala en solo lectura"),
          ("ControlSeguimiento", "ControlSincronizacion", "Pedir el diagrama a un participante"),
          ("ControlSeguimiento", "RespaldoDiagrama", "Usar el último respaldo si no hay nadie"),
          ("ControlSeguimiento", "EventoActividad", "Obtener la actividad reciente"),
          ("ControlSeguimiento", "VistaSeguimiento", "Entregar el diagrama y la actividad"),
          ("VistaSeguimiento", "ControlSincronizacion", "Recibir cada cambio nuevo de la sala"),
          ("VistaSeguimiento", "Diagrama", "Mostrar el diagrama en solo lectura")],
         ["El Colaborador abre en el celular el enlace de seguimiento: la **Vista de Seguimiento** le pide al **Control de Seguimiento** "
          "seguir la sala en solo lectura (hasta diez seguidores).",
          "El control pide el diagrama a un participante a través del **Control de Sincronización** o, si no hay nadie, usa el último "
          "**Respaldo del Diagrama**, y obtiene la actividad reciente (**Evento de Actividad**).",
          "La vista muestra el **Diagrama** sin controles de edición, recibe cada cambio nuevo y, si el Colaborador autorizó los avisos, "
          "le notifica cuando alguien cambia el diagrama o la IA publica una idea."],
         ["Es de solo lectura.", "Los avisos funcionan con la página abierta en el navegador del celular."]),
    _col("COL-18", "CU14", "Aprender a usar la herramienta con el asistente de ayuda",
         {"U": A_COL},
         [("U", "PanelAyuda", "Preguntar cómo hacer algo"),
          ("PanelAyuda", "ControlAyuda", "Responder la duda de uso"),
          ("ControlAyuda", "PedidoIA", "Reservar el cupo de la persona"),
          ("ControlAyuda", "ConocimientoAyuda", "Tomar el manual y la lista de funciones"),
          ("ControlAyuda", "InterfazServicioIA", "Enviar la pregunta con ese conocimiento"),
          ("InterfazServicioIA", "S", "Pedir la respuesta"),
          ("ControlAyuda", "PanelAyuda", "Mostrar la respuesta paso a paso")],
         ["El Colaborador escribe su duda en el **Panel de Ayuda**, que se la pasa al **Control de Ayuda**.",
          "El control reserva el cupo en el **Pedido a la IA**, toma el **Conocimiento de Ayuda** (el manual y las funciones) y envía la "
          "pregunta por la **Interfaz del Servicio de IA**.",
          "Con la respuesta, el control la muestra en el panel, paso a paso; si la pregunta no trata de la herramienta, lo indica."],
         ["Solo responde sobre la herramienta.", "Tiene tope de uso y la conversación es personal, no de la sala."]),
]
ACTOR_EXTERNO = {"S": ("A3", "Servicio de IA")}  # instancia del actor secundario en las colaboraciones que lo usan

# ---- requisitos especiales comunes (los identifica el arquitecto, 8.6.1.3) -----------------------------------
ESPECIALES_COMUNES = [
    ("REC-1", "Persistencia", "Lo que debe sobrevivir a un reinicio: el respaldo del diagrama, la actividad y la conversación de la sala, y los "
                              "pedidos a la IA (para los topes). El resto es efímero."),
    ("REC-2", "Distribución y concurrencia", "Dos o tres personas editan a la vez y quien sigue desde el celular solo mira; la IA atiende un "
                                             "pedido a la vez por sala."),
    ("REC-3", "Seguridad", "Los permisos (expulsar) los verifica el servidor; los archivos recibidos no leen archivos locales ni abren conexiones."),
    ("REC-4", "Tolerancia a fallos", "Si falla el servicio de IA, el generador o el registro de actividad, el diagrama sigue editable y no "
                                     "cambia sin que alguien lo confirme."),
    ("REC-5", "Costo y límites de uso", "Topes de pedidos a la IA por persona, por sala y para todo el servicio; tamaños máximos de mensajes, "
                                        "contexto y cambios."),
]

# Características de persistencia (8.6.1.3): rango de tamaño, volumen, período, frecuencia de actualización y fiabilidad.
PERSISTENCIA = [
    ("Respaldo del Diagrama", "El diagrama completo de la sala", "Una copia por sala", "Mientras la sala exista", "1,5 s después de la última edición",
     "Debe sobrevivir a un reinicio del servidor"),
    ("Evento de Actividad", "Hasta 8 KB de datos y 255 caracteres de resumen", "Crece con la actividad de cada sala", "Mientras la sala exista",
     "Hasta 60 por minuto por conexión", "No debe perderse; si falla el registro, la edición sigue"),
    ("Mensaje de Conversación", "Hasta 2000 caracteres", "Crece con las consultas a la IA", "Mientras la sala exista",
     "Hasta 30 pedidos por minuto en una sala", "No debe perderse"),
    ("Pedido a la IA", "Una fila pequeña", "Uno por pedido", "Basta con el último minuto para los topes", "Uno por pedido",
     "Debe contar aunque el pedido falle"),
]


# ---- consultas ---------------------------------------------------------------------------------------------
def dependencias_reducidas():
    """Reducción transitiva de las dependencias: se quitan las que ya están implícitas por otra ruta (para dibujar el diagrama)."""
    deps = set(DEPENDENCIAS)

    def alcanza(origen, destino, sin):
        pila, vistos = [origen], set()
        while pila:
            n = pila.pop()
            for a, b in deps:
                if a == n and (a, b) != sin and b not in vistos:
                    if b == destino:
                        return True
                    vistos.add(b)
                    pila.append(b)
        return False

    return [(a, b) for a, b in DEPENDENCIAS if not alcanza(a, b, (a, b))]


def numero_cu(codigo):
    return int(codigo[2:])


def colaboraciones_de(codigo):
    return [c for c in COLABORACIONES if codigo in [x.strip() for x in c["cu"].split(",")]]


def clases_de_paquete(id_paquete):
    return [c for c in CLASES.values() if c["paquete"] == id_paquete]


def responsabilidades(clave):
    """[(responsabilidad, [colaboraciones que la originan])] de una clase: los mensajes que recibe, agrupados por texto."""
    resp = {}
    for col in COLABORACIONES:
        for _, destino, texto in col["mensajes"]:
            if destino == clave:
                resp.setdefault(texto, []).append(col["id"])
    return list(resp.items())


def relaciones_de(clave):
    return [r for r in RELACIONES if clave in (r[0], r[1])]


def dependencias_calculadas():
    """Dependencias entre paquetes que producen los mensajes y las asociaciones: {(origen, destino)}."""
    deps = set()
    for col in COLABORACIONES:
        for origen, destino, _ in col["mensajes"]:
            if origen in CLASES and destino in CLASES:
                a, b = CLASES[origen]["paquete"], CLASES[destino]["paquete"]
                if a != b:
                    deps.add((_raiz(a), _raiz(b)))
    return {(a, b) for a, b in deps if a != b}


def _raiz(id_paquete):
    """Un paquete de servicio cuenta como parte del paquete que lo contiene (el servicio se entrega dentro de él)."""
    padre = next(p["padre"] for p in PAQUETES if p["id"] == id_paquete)
    return padre or id_paquete


def _hay_ciclo(deps):
    grafo = {}
    for a, b in deps:
        grafo.setdefault(a, set()).add(b)
    visitados, pila = set(), set()

    def visita(n):
        if n in pila:
            return True
        if n in visitados:
            return False
        visitados.add(n)
        pila.add(n)
        if any(visita(m) for m in grafo.get(n, ())):
            return True
        pila.discard(n)
        return False

    return any(visita(n) for n in list(grafo))


def validar(requisitos):
    """Comprueba las reglas del libro sobre el modelo. `requisitos` es el módulo modelo.requisitos."""
    errores = []
    asociadas = {frozenset((a, b)) for a, b, *_ in RELACIONES}
    if len(asociadas) != len(RELACIONES):
        errores.append("hay dos asociaciones entre el mismo par de clases: una asociación une en los dos sentidos")
    for a, b, *_ in RELACIONES:
        for x in (a, b):
            if x not in CLASES:
                errores.append(f"relación con clase desconocida: {x}")
    # cada clase en un paquete que existe; interfaz/control/entidad
    for clave, c in CLASES.items():
        if c["paquete"] not in NOMBRE_PAQUETE:
            errores.append(f"{clave}: paquete desconocido")
        if c["est"] not in ESTEREOTIPO:
            errores.append(f"{clave}: estereotipo inválido")
        if not c["desc"]:
            errores.append(f"{clave}: sin descripción")
    # colaboraciones
    participantes = set()
    for col in COLABORACIONES:
        instancias = dict(col["actores"])
        if any(d == "S" or o == "S" for o, d, _ in col["mensajes"]):
            instancias["S"] = ACTOR_EXTERNO["S"]
        for cu in [x.strip() for x in col["cu"].split(",")]:
            if cu not in requisitos.CASOS:
                errores.append(f"{col['id']}: caso de uso desconocido {cu}")
        if col["mensajes"] and col["mensajes"][0][0] in CLASES and col["actores"] and not col["continuacion"]:
            errores.append(f"{col['id']}: el primer mensaje debe salir de un actor")
        if col["actores"] and col["mensajes"][0][0] in col["actores"]:
            destino = col["mensajes"][0][1]
            if destino not in CLASES or CLASES[destino]["est"] != "interfaz":
                errores.append(f"{col['id']}: el caso de uso se invoca sobre un objeto de interfaz")
        for origen, destino, texto in col["mensajes"]:
            if not texto or texto.endswith(")") and "(" not in texto:
                errores.append(f"{col['id']}: mensaje mal escrito {texto!r}")
            if "(" in texto and texto.rstrip().endswith("()"):
                errores.append(f"{col['id']}: un mensaje no es una operación: {texto!r}")
            for extremo in (origen, destino):
                if extremo not in CLASES and extremo not in instancias:
                    errores.append(f"{col['id']}: extremo desconocido {extremo}")
            if origen in CLASES and destino in CLASES and frozenset((origen, destino)) not in asociadas:
                errores.append(f"{col['id']}: el enlace {origen}-{destino} no es instancia de una asociación")
            if origen in CLASES and destino in CLASES and origen == destino:
                errores.append(f"{col['id']}: mensaje de una clase a sí misma")
        participantes.update(col["objetos"])
    # toda clase participa en alguna colaboración; toda entidad también (8.6.1.2)
    for clave in CLASES:
        if clave not in participantes:
            errores.append(f"{clave}: no participa en ninguna colaboración (no es necesaria)")
    # cada caso de uso tiene al menos una realización, con una interfaz para quien lo inicia y otra para cada actor sistema externo
    for cu, caso in requisitos.CASOS.items():
        cols = colaboraciones_de(cu)
        if not cols:
            errores.append(f"{cu}: sin realización")
            continue
        objetos = {o for c in cols for o in c["objetos"]}
        if not any(CLASES[o]["est"] == "interfaz" and o != "InterfazServicioIA" for o in objetos):
            errores.append(f"{cu}: ninguna clase de interfaz para quien lo inicia")
        if "A3" in caso["actores"] and "InterfazServicioIA" not in objetos:
            errores.append(f"{cu}: falta la interfaz del actor sistema externo (A3)")
        if not any(CLASES[o]["est"] == "control" for o in objetos):
            errores.append(f"{cu}: sin clase de control")
    # paquetes: cada caso de uso en uno, dependencias declaradas cubren las calculadas y sin ciclos
    asignados = [cu for p in PAQUETES for cu in p["casos"]]
    if sorted(asignados, key=numero_cu) != sorted(requisitos.CASOS, key=numero_cu):
        errores.append("cada caso de uso debe estar en exactamente un paquete")
    calculadas = dependencias_calculadas()
    faltan = calculadas - set(DEPENDENCIAS)
    if faltan:
        errores.append(f"dependencias que producen las colaboraciones y no están declaradas: {sorted(faltan)}")
    sobran = set(DEPENDENCIAS) - calculadas
    if sobran:
        errores.append(f"dependencias declaradas que ninguna colaboración produce: {sorted(sobran)}")
    if _hay_ciclo(set(DEPENDENCIAS)):
        errores.append("hay un ciclo de dependencias entre paquetes")
    if errores:
        raise ValueError("Modelo de análisis inconsistente:\n  " + "\n  ".join(errores))


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from modelo import requisitos
    validar(requisitos)
    print(len(CLASES), "clases;", len(COLABORACIONES), "colaboraciones;", len(RELACIONES), "relaciones")
