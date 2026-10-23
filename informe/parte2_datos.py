"""Datos del modelo del sistema para la Parte 2 del informe (segundo parcial, PUDS).

El segundo parcial continúa el primero: los ciclos 1 a 3 (CU-01 a CU-13) ya se entregaron y aquí solo se
registra lo nuevo, desde el ciclo 4 (CU-14 en adelante). De estos datos salen las tablas de casos de uso y
los diagramas por caso de uso (casos de uso, comunicación, clases de análisis y secuencia), de modo que el
modelo y los diagramas no se desincronizan.

Roles de cada caso de uso para los diagramas:
  U  = actor que lo inicia (`inicia`)   IU = clase de interfaz   CT = clase de control
  E1, E2, E3 = clases de entidad        EX = sistema o actor externo
"""

# Actores A1 y A2 son los del primer parcial; A3 a A6 son nuevos.
ACTORES = [
    ("A1", "Diseñador", "Actor que inicia una sala o es el primero en conectarse a una que ya está viva (el *host*). Hace todo lo que hace un Colaborador y, además, puede expulsar a otros participantes. Es un rol temporal de la sala, no una cuenta (especialización de A2)."),
    ("A2", "Colaborador", "Actor que se incorpora a una sala mediante su código y trabaja sobre el diagrama con las mismas capacidades de edición que el Diseñador. No tiene cuenta: se identifica con un nombre y un identificador anónimo guardado en su navegador."),
    ("A3", "IA", "Integrante automático de la sala. Solo actúa cuando alguien se lo pide, y sus ideas son visibles para todos."),
    ("A4", "Observador", "Persona que sigue la sala desde el celular, en solo lectura. No cuenta como participante ni puede ser *host*."),
    ("A5", "Administrador", "Configura la plataforma: el proveedor de IA y el modelo local reentrenado."),
    ("A6", "Proveedor de IA", "Servicio que genera las respuestas: Google Gemini (nube) o un modelo local servido por Ollama."),
]
NOMBRE_ACTOR = {codigo: nombre for codigo, nombre, _ in ACTORES}
# Actores que se dibujan a la derecha del sistema en los diagramas de casos de uso.
ACTORES_SECUNDARIOS = {"A3", "A6"}

# Casos de uso del primer parcial (ciclos 1 a 3): se citan como referencia y como destino de <<include>>.
CICLOS_PARCIAL1 = [
    (1, ["CU-01", "CU-02", "CU-05"]),
    (2, ["CU-03", "CU-04", "CU-06", "CU-07", "CU-08", "CU-09"]),
    (3, ["CU-10", "CU-11", "CU-12", "CU-13"]),
]
CUS_PARCIAL1 = {
    "CU-01": ("Gestionar salas de trabajo colaborativas", ["A1", "A2"]),
    "CU-02": ("Modelar diagrama de clases UML", ["A1", "A2"]),
    "CU-03": ("Colaborar en tiempo real sobre el diagrama", ["A1", "A2"]),
    "CU-04": ("Gestionar participantes de la sala", ["A1"]),
    "CU-05": ("Guardar y recuperar el estado del diagrama", ["A1", "A2"]),
    "CU-06": ("Crear o modificar el modelo mediante lenguaje natural", ["A1", "A2"]),
    "CU-07": ("Crear el modelo a partir de una imagen", ["A1", "A2"]),
    "CU-08": ("Editar el modelo mediante comandos de voz", ["A1", "A2"]),
    "CU-09": ("Analizar y validar el modelo UML con IA", ["A1", "A2"]),
    "CU-10": ("Exportar e importar el diagrama en formato XMI", ["A1", "A2"]),
    "CU-11": ("Generar script SQL desde el modelo", ["A1", "A2"]),
    "CU-12": ("Generar proyecto backend Spring Boot", ["A1"]),
    "CU-13": ("Generar proyecto de aplicación móvil Flutter", ["A1"]),
}
# Paquete de análisis del primer parcial al que se conecta lo nuevo.
PAQUETE_LIENZO = "Gestión de lienzo"

# Ciclos nuevos: continúan la numeración del primer parcial.
CICLOS = [
    (4, "Identidad, actividad y chat con la IA", "I1 e I2", ["CU-14", "CU-15", "CU-16"]),
    (5, "La IA actúa a pedido, revisa y la sesión continúa", "I3 e I4", ["CU-17", "CU-18", "CU-19", "CU-20"]),
    (6, "Vista móvil, IA local y reentrenamiento del modelo", "I5 a I8", ["CU-21", "CU-22", "CU-23"]),
]

# Paquetes de análisis nuevos o ampliados (el primer parcial tenía cinco: Gestión de lienzo, Colaboración,
# Asistencia inteligente, Entrada multimodal y Exportación e integración).
PAQUETES = [
    ("Identidad y actividad", "Participante, Identificador anónimo y Evento de actividad (paquete nuevo)", ["CU-14", "CU-15"]),
    ("Colaboración", "Sala, Participante, Presencia, Operación y Respaldo (se amplía con retomar sesión y seguimiento móvil)", ["CU-20", "CU-21"]),
    ("Asistencia inteligente", "Pedido a la IA, Respuesta, Mensaje de chat, Sugerencia, Configuración del proveedor y Modelo reentrenado (se amplía)",
     ["CU-16", "CU-17", "CU-18", "CU-19", "CU-22", "CU-23"]),
]
DEPENDENCIAS_PAQUETES = [
    ("Asistencia inteligente", "Identidad y actividad"), ("Asistencia inteligente", "Colaboración"),
    ("Asistencia inteligente", PAQUETE_LIENZO), ("Colaboración", "Identidad y actividad"),
    ("Colaboración", PAQUETE_LIENZO),
]

# Nombre de cualquier caso de uso, del primer parcial o nuevo.
def nombre_cu(codigo):
    return CUS[codigo]["nombre"] if codigo in CUS else CUS_PARCIAL1[codigo][0]


# Cada caso de uso nuevo: nombre, actores, incluye, prioridad, motivo, propósito, iniciador, inicia, precondición,
# flujo, postcondición, excepción, IU, control, entidades, externo, mensajes (de, a, texto[, es_retorno]).
CUS = {
    "CU-14": dict(
        nombre="Identificarse al entrar a una sala", actores=["A1", "A2"], incluye=["CU-01"], prioridad="Alta",
        motivo="Es la base de la actividad por persona y de los chats privados.",
        proposito="Que cada persona tenga un nombre visible y un identificador anónimo.",
        iniciador="A1 o A2", inicia="A2", precondicion="Entró a una sala.",
        flujo=["El navegador lee el identificador anónimo guardado o crea uno nuevo.",
               "Si no hay nombre, pregunta «¿Cómo deseas que te vean en la sala?».",
               "El navegador envía el identificador y el nombre al servidor.",
               "El servidor valida, registra al participante y lo asocia a su conexión.",
               "La presencia muestra el nombre a todos."],
        postcondicion="La persona figura con su nombre en la lista de participantes y en la actividad.",
        excepcion="Si el nombre o el identificador no son válidos, se ignoran y la persona figura con un nombre genérico.",
        iu="Editor de diagrama", control="Control de identidad", entidades=["Participante"], externo=None,
        mensajes=[("U", "IU", "indicarNombre(nombre)"), ("IU", "CT", "enviarIdentidad(token, nombre)"), ("CT", "E1", "registrarParticipante()"),
                  ("CT", "IU", "mostrarNombre()")]),
    "CU-15": dict(
        nombre="Ver la actividad del equipo", actores=["A1", "A2"], incluye=["CU-14"], prioridad="Alta",
        motivo="Es el contexto que la IA usa para saber quién hizo qué.",
        proposito="Ver, en orden, qué hizo cada integrante, incluida la IA.",
        iniciador="A1 o A2", inicia="A2", precondicion="CU-14",
        flujo=["El participante abre el panel de actividad.",
               "El cliente pide el historial reciente de la sala.",
               "El servidor devuelve los eventos, del más nuevo al más viejo.",
               "Cada acción nueva llega en vivo y se agrega arriba."],
        postcondicion="El panel muestra quién hizo qué y cuándo.",
        excepcion="Mover o redimensionar no se registra a propósito. Si falla la base de datos, la edición sigue funcionando.",
        iu="Panel de actividad", control="Control de actividad", entidades=["Evento de actividad"], externo=None,
        mensajes=[("U", "IU", "abrirPanel()"), ("IU", "CT", "pedirHistorial()"), ("CT", "E1", "leerEventos()"),
                  ("E1", "CT", "lista de eventos", True), ("CT", "IU", "mostrarLista()"), ("CT", "IU", "eventoNuevo()")]),
    "CU-16": dict(
        nombre="Preguntar a la IA", actores=["A1", "A2", "A3"], incluye=["CU-14"], prioridad="Alta",
        motivo="Es la primera interacción de la IA como integrante de la sala.",
        proposito="Consultar sobre el diagrama o sobre lo que hizo cada persona, sin modificar nada.",
        iniciador="A1 o A2", inicia="A2", precondicion="CU-14",
        flujo=["En su chat, el participante elige el modo «Preguntar» y escribe la pregunta.",
               "El servidor lo identifica por su token y limita la cantidad de pedidos.",
               "El servidor arma el contexto: diagrama actual, actividad de toda la sala y el chat propio.",
               "El proveedor de IA responde; el servidor guarda pregunta y respuesta juntas.",
               "El chat muestra la respuesta. Solo su dueño puede leer esa conversación."],
        postcondicion="La conversación queda guardada y el diagrama no cambia.",
        excepcion="Si el proveedor falla se muestra un mensaje claro y no se guarda nada. Si se supera el tope de pedidos, el servidor responde que se espere un momento.",
        iu="Chat con la IA", control="Control de IA", entidades=["Mensaje de chat", "Evento de actividad"], externo="Proveedor de IA",
        mensajes=[("U", "IU", "escribirPregunta(texto)"), ("IU", "CT", "enviar(modo=preguntar)"), ("CT", "E2", "leerActividad()"),
                  ("CT", "EX", "responder(contexto)"), ("EX", "CT", "respuesta", True), ("CT", "E1", "guardarMensajes()"),
                  ("CT", "IU", "mostrarRespuesta()")]),
    "CU-17": dict(
        nombre="Pedirle a la IA un cambio en el diagrama", actores=["A1", "A2", "A3"], incluye=["CU-14", "CU-02"], prioridad="Alta",
        motivo="Atraviesa identidad, actividad, IA y colaboración; valida la arquitectura de punta a punta.",
        proposito="Que la IA modifique el diagrama solo cuando alguien se lo pide explícitamente.",
        iniciador="A1 o A2", inicia="A2", precondicion="CU-14",
        flujo=["En su chat, el participante elige «Pedir cambio» y escribe el pedido.",
               "El servidor lo identifica, limita los pedidos y llama al proveedor de IA.",
               "El proveedor devuelve los cambios en el formato que ya entiende el editor.",
               "El servidor los valida y cuenta cuántos elementos eliminarían; si eliminan algo, el navegador pide confirmación.",
               "El navegador del participante los aplica por la misma ruta de la edición manual; cada operación viaja marcada como de la IA y se propaga a todos.",
               "La actividad registra «IA … (a pedido de X)»."],
        postcondicion="El diagrama cambia en todas las pantallas y queda registrado quién lo pidió.",
        excepcion="Si el proveedor falla, el mensaje es claro y el diagrama no cambia. En el modo «Preguntar» la IA responde sin tocar el diagrama.",
        iu="Chat con la IA", control="Control de IA", entidades=["Mensaje de chat", "Diagrama", "Evento de actividad"], externo="Proveedor de IA",
        mensajes=[("U", "IU", "escribirPedido(texto)"), ("IU", "CT", "enviar(modo=cambio)"), ("CT", "EX", "generarCambios(contexto)"),
                  ("EX", "CT", "cambios", True), ("CT", "CT", "validarCambios()"), ("CT", "E1", "guardarMensajes()"),
                  ("CT", "IU", "entregarCambios()"), ("IU", "E2", "aplicarCambios(vía IA)"), ("CT", "E3", "registrar(«IA, a pedido de X»)")]),
    "CU-18": dict(
        nombre="Pedirle a la IA una revisión", actores=["A1", "A2", "A3"], incluye=["CU-14", "CU-09"], prioridad="Media",
        motivo="Es el segundo modo de la IA y publica sus ideas para toda la sala.",
        proposito="Que la IA revise clases, atributos, métodos y relaciones y comparta sus observaciones con el equipo.",
        iniciador="A1 o A2", inicia="A2", precondicion="CU-14",
        flujo=["El participante elige «Revisar» y, si quiere, indica qué revisar.",
               "El servidor pide la revisión al proveedor de IA con el diagrama actual.",
               "El proveedor responde con observaciones y, para cada una, un pedido que la aplicaría.",
               "El servidor guarda la conversación y publica un evento de revisión visible para todos.",
               "Cada observación aparece con un botón «Aplicar»."],
        postcondicion="La sala ve las ideas de la IA; ninguna se aplica sola.",
        excepcion="Si la respuesta no tiene el formato esperado, se muestra como texto y sin botones.",
        iu="Chat con la IA", control="Control de IA", entidades=["Mensaje de chat", "Evento de actividad"], externo="Proveedor de IA",
        mensajes=[("U", "IU", "pedirRevisión()"), ("IU", "CT", "enviar(modo=revisar)"), ("CT", "EX", "revisar(diagrama)"),
                  ("EX", "CT", "observaciones", True), ("CT", "E1", "guardarMensajes()"), ("CT", "E2", "publicarRevisión()"),
                  ("CT", "IU", "mostrarIdeas()")]),
    "CU-19": dict(
        nombre="Aplicar una idea de la IA", actores=["A1", "A2"], incluye=["CU-17"], prioridad="Media",
        motivo="Cierra el ciclo de la revisión sin que la IA actúe por su cuenta.",
        proposito="Que cualquier persona aplique una idea de la revisión, una sola vez para toda la sala.",
        iniciador="A1 o A2", inicia="A2", precondicion="Existe una revisión publicada (CU-18).",
        flujo=["El participante pulsa «Aplicar» en una idea.",
               "El servidor reserva la idea para esa persona; si otra ya la tomó, responde con un conflicto.",
               "La idea se ejecuta como un pedido de cambio a nombre de quien la aplica (CU-17).",
               "El cliente confirma la idea; queda «Aplicada» para todos.",
               "Si el cambio no se aplica, la reserva se libera."],
        postcondicion="La idea queda marcada como aplicada para toda la sala.",
        excepcion="Una reserva que nadie confirma vence a los 150 segundos y la idea queda libre otra vez.",
        iu="Panel de actividad", control="Control de IA", entidades=["Evento de actividad"], externo=None,
        mensajes=[("U", "IU", "pulsarAplicar(idea)"), ("IU", "CT", "reservarIdea(idea)"), ("CT", "E1", "marcarReservada()"),
                  ("E1", "CT", "reserva concedida", True), ("CT", "IU", "ejecutarComoCambio()"), ("IU", "CT", "confirmarIdea()"),
                  ("CT", "E1", "marcarAplicada()")]),
    "CU-20": dict(
        nombre="Retomar una sesión anterior", actores=["A1", "A2"], incluye=["CU-05", "CU-14"], prioridad="Media",
        motivo="Las personas cierran y vuelven: no deben perder el contexto.",
        proposito="Recuperar el diagrama, la actividad y el chat propio al volver a una sala.",
        iniciador="A1 o A2", inicia="A2", precondicion="Ya participó en esa sala desde el mismo navegador.",
        flujo=["El participante vuelve a abrir la sala.",
               "La plataforma recupera el diagrama (del estado de la sala o, si no hay nadie, del respaldo).",
               "Recupera el historial de actividad de la sala.",
               "Recupera el chat propio, identificado por su token."],
        postcondicion="La persona continúa donde se quedó.",
        excepcion="Si no hay respaldo, el lienzo aparece vacío.",
        iu="Editor de diagrama", control="Control de colaboración", entidades=["Respaldo", "Evento de actividad", "Mensaje de chat"], externo=None,
        mensajes=[("U", "IU", "volverASala(código)"), ("IU", "CT", "recuperarSesión()"), ("CT", "E1", "leerRespaldo()"),
                  ("CT", "E2", "leerActividad()"), ("CT", "E3", "leerChatPropio()"), ("CT", "IU", "mostrarSesión()")]),
    "CU-21": dict(
        nombre="Seguir la sala desde el celular", actores=["A4"], incluye=["CU-03"], prioridad="Media",
        motivo="Lo pidió el docente para quien está viajando.",
        proposito="Ver en vivo las modificaciones y la actividad sin poder editar.",
        iniciador="A4", inicia="A4", precondicion="Tiene el enlace de seguimiento.",
        flujo=["El observador abre el enlace de seguimiento en el celular.",
               "La plataforma lo conecta en modo observador: separado de los participantes, sin entrar al orden que define al host.",
               "El servidor pide el estado completo al host (un pedido por segundo por sala).",
               "El observador ve el diagrama actualizándose y la actividad debajo."],
        postcondicion="El observador sigue la sala en solo lectura.",
        excepcion="Si hay 10 observadores en la sala, el servidor rechaza uno más.",
        iu="Vista móvil", control="Control de actividad", entidades=["Evento de actividad", "Respaldo"], externo=None,
        mensajes=[("U", "IU", "abrirEnlace()"), ("IU", "CT", "conectarComoObservador()"), ("CT", "E2", "leerRespaldo()"),
                  ("CT", "IU", "mostrarDiagrama()"), ("CT", "E1", "leerEventos()"), ("CT", "IU", "eventoNuevo()")]),
    "CU-22": dict(
        nombre="Configurar el proveedor de IA", actores=["A5", "A6"], incluye=[], prioridad="Baja",
        motivo="Es opcional y lo planteó el docente como valorable.",
        proposito="Elegir si responde Gemini (nube) o un modelo local, y qué modelo hace los cambios.",
        iniciador="A5", inicia="A5", precondicion="Tiene acceso a la configuración del servidor.",
        flujo=["El administrador define el proveedor (Gemini u Ollama) y, para Ollama, el modelo general y el modelo reentrenado para los cambios.",
               "Reinicia el servicio.",
               "El chat consulta qué proveedor responde y lo muestra («IA en la nube (Gemini)» o «IA local»)."],
        postcondicion="El chat usa el proveedor configurado.",
        excepcion="Si el modelo local no está disponible, el chat muestra un error claro; basta volver a Gemini cambiando la variable.",
        iu="Chat con la IA", control="Control de IA", entidades=["Configuración del proveedor"], externo="Proveedor de IA",
        mensajes=[("U", "IU", "definirProveedor(valor)"), ("IU", "CT", "guardarConfiguración()"), ("CT", "E1", "registrar(valor)"),
                  ("CT", "EX", "verificarDisponibilidad()"), ("EX", "CT", "disponible", True), ("CT", "IU", "mostrarProveedor()")]),
    "CU-23": dict(
        nombre="Reentrenar el modelo de IA local", actores=["A5"], incluye=["CU-22"], prioridad="Baja",
        motivo="Demuestra el reentrenamiento y el despliegue de un modelo abierto, como extra valorable.",
        proposito="Entrenar un adaptador LoRA sobre un modelo Qwen para que modifique diagramas, medir si mejora y desplegarlo.",
        iniciador="A5", inicia="A5", precondicion="Computador con Apple Silicon, MLX y Ollama.",
        flujo=["Se generan los datos de entrenamiento con semilla fija; se reservan ejemplos de prueba que el modelo no verá.",
               "Se mide el modelo base sin entrenar.",
               "Se entrena el adaptador LoRA y se guarda el registro de la pérdida.",
               "Se mide el modelo reentrenado sobre los ejemplos de prueba.",
               "Se fusiona el adaptador con el modelo y se importa a Ollama.",
               "Se mide el modelo desplegado y se conecta a la plataforma."],
        postcondicion="El modelo reentrenado atiende los cambios al diagrama.",
        excepcion="Si no mejora frente al modelo base, se reporta y se ajustan los datos.",
        iu="Consola de entrenamiento", control="Control de entrenamiento", entidades=["Conjunto de datos", "Adaptador LoRA", "Resultado de evaluación"], externo="Proveedor de IA",
        mensajes=[("U", "IU", "ejecutarCorrida(nombre)"), ("IU", "CT", "generarDatos()"), ("CT", "E1", "escribirConjunto()"),
                  ("CT", "E2", "entrenarAdaptador()"), ("CT", "E3", "medirModelos()"), ("CT", "EX", "importarModelo()"),
                  ("CT", "IU", "mostrarResultados()")]),
}
