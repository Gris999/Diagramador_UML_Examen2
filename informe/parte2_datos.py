"""Datos del modelo del sistema para la Parte 2 del informe (segundo parcial, PUDS).

El segundo parcial continúa el primero: los ciclos 1 a 3 (CU-01 a CU-13) ya se entregaron y aquí solo se
registra lo nuevo, desde el ciclo 4 (CU-14 en adelante). De estos datos salen las tablas de casos de uso y
los diagramas por caso de uso (casos de uso, comunicación, clases de análisis y secuencia), de modo que el
modelo y los diagramas no se desincronizan.

Criterios de modelado (Jacobson, Booch y Rumbaugh, *El Proceso Unificado de Desarrollo de Software*; OMG, UML 2.5.1):
  * un actor es un rol de quien interactúa con el sistema desde fuera; la IA es una función del sistema (se muestra
    como un integrante más de la sala, pero no es un usuario) y el servicio de IA (Gemini u Ollama) es una pieza de
    la arquitectura, no un rol: ninguno es actor;
  * un caso de uso es un objetivo completo de un actor que le entrega un resultado observable; no se parte en
    pasos ni en operaciones de un CRUD;
  * lo que no es una interacción con un actor (modelo local de IA, privacidad, resiliencia) es un requisito adicional.

Roles de cada caso de uso para los diagramas de análisis (reglas de robustez):
  U  = actor que lo inicia (`inicia`)   IU = clase de interfaz (solo habla con U y con CT)
  CT = clase de control                 E1, E2, E3 = clases de entidad (solo las toca CT)
  EX = interfaz con un sistema externo (el servicio de IA; solo habla con CT)
"""

ACTORES = [
    ("A1", "Diseñador", "Actor que crea una sala o es el primero en conectarse a una que ya está viva (el *host*). Hace todo lo que "
     "hace un Colaborador y, además, puede expulsar a otros participantes. Es un rol temporal de la sala, no una cuenta: es una "
     "especialización de A2."),
    ("A2", "Colaborador", "Actor que se incorpora a una sala mediante su código y trabaja sobre el diagrama con las mismas "
     "capacidades de edición que el Diseñador. No tiene cuenta: se identifica con un nombre y un identificador anónimo guardado "
     "en su navegador."),
]
NOMBRE_ACTOR = {codigo: nombre for codigo, nombre, _ in ACTORES}
# No hay actores secundarios: la IA y su servicio no son actores (ver criterios de modelado).
ACTORES_SECUNDARIOS = set()

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
    (4, "Identidad, actividad y consulta a la IA", "I1 e I2", ["CU-14", "CU-15"]),
    (5, "La IA actúa a pedido y la sesión continúa", "I3 e I4", ["CU-16", "CU-17", "CU-18"]),
    (6, "Seguimiento desde el celular", "I5", ["CU-19"]),
]

# Paquetes de análisis: el primer parcial tenía cinco (Gestión de lienzo, Colaboración, Asistencia inteligente, Entrada
# multimodal y Exportación e integración); lo nuevo amplía dos de ellos.
PAQUETES = [
    ("Colaboración", "Sala, Participante, Presencia, Operación, Respaldo y Evento de actividad (se amplía con la actividad del equipo, "
     "retomar la sesión y el seguimiento móvil)", ["CU-14", "CU-18", "CU-19"]),
    ("Asistencia inteligente", "Pedido a la IA, Respuesta, Mensaje de chat y Sugerencia (se amplía: la IA como integrante de la sala)",
     ["CU-15", "CU-16", "CU-17"]),
]
DEPENDENCIAS_PAQUETES = [
    ("Asistencia inteligente", "Colaboración"), ("Asistencia inteligente", PAQUETE_LIENZO), ("Colaboración", PAQUETE_LIENZO),
]

# Requisitos adicionales (no son casos de uso: no los inicia un actor).
REQUISITOS_ADICIONALES = [
    ("RA-01", "IA local reentrenada", "El docente la pidió como extra valorable, no obligatoria. Un modelo abierto (Qwen) reentrenado con "
     "LoRA se sirve con Ollama y reemplaza a Gemini sin cambiar lo que ve el usuario; se elige con una variable del servidor.",
     "Anexos A y B (evaluación del modelo base contra el reentrenado)"),
    ("RA-02", "Privacidad de la conversación con la IA", "La conversación de cada persona con la IA solo la lee su dueño; la actividad "
     "de la sala sí es visible para todos.", "Pruebas CP-22 y CP-34"),
    ("RA-03", "Resiliencia ante fallos de la IA", "Si el servicio de IA falla o responde mal, el usuario ve un mensaje claro y el "
     "diagrama no se pierde ni se corrompe.", "Pruebas CP-23 y CP-43"),
    ("RA-04", "Control del costo de la IA", "Hay topes de uso por persona, por sala y para todo el servicio, y una respuesta que "
     "eliminaría elementos pide confirmación antes de aplicarse.", "Pruebas CP-33 y CP-34"),
    ("RA-05", "Persistencia continua", "Todo lo que se hace en una sala (diagrama, actividad y conversación propia) queda guardado "
     "para continuar en otra sesión.", "Prueba CP-05 y CU18"),
    ("RA-06", "Despliegue seguro y reproducible", "Sitio en AWS con HTTPS, sin puertos internos expuestos y con prueba de humo.",
     "Anexo C y prueba CP-26"),
]


# Nombre de cualquier caso de uso, del primer parcial o nuevo.
def nombre_cu(codigo):
    return CUS[codigo]["nombre"] if codigo in CUS else CUS_PARCIAL1[codigo][0]


# Cada caso de uso nuevo: nombre, actores, incluye, prioridad, motivo, propósito, iniciador, inicia, precondición,
# flujo, postcondición, excepción, IU, control, entidades, externo, mensajes (de, a, texto).
# Los mensajes siguen las reglas de robustez: U<->IU, IU<->CT, CT<->CT, CT->entidad y CT->EX (sin retornos).
CUS = {
    "CU-14": dict(
        nombre="Consultar la actividad del equipo", actores=["A1", "A2"], incluye=["CU-01"], prioridad="Alta",
        motivo="Es la base de todo lo demás: sin saber quién es cada persona y qué hizo, la IA no puede responder por el equipo.",
        proposito="Identificarse con un nombre visible y ver, en tiempo real, quién está en la sala y qué hizo cada integrante.",
        iniciador="A1 o A2", inicia="A2", precondicion="El actor ingresó a una sala (CU1).",
        flujo=["El sistema lee del navegador el identificador anónimo del actor o crea uno nuevo.",
               "Si el actor aún no tiene nombre, el sistema pregunta «¿Cómo deseas que te vean en la sala?» y el actor lo escribe.",
               "El sistema valida el nombre, registra al participante en la sala y muestra la lista de participantes, con la IA como un integrante más.",
               "El actor abre el panel de actividad.",
               "El sistema muestra el historial reciente, del más nuevo al más viejo, con autor, tipo de acción y resumen.",
               "Cada acción nueva de cualquier integrante llega en vivo y se agrega arriba."],
        postcondicion="El actor figura con su nombre y ve quién hizo qué.",
        excepcion="Si el nombre o el identificador no son válidos, el actor figura con un nombre genérico. Mover o redimensionar no se "
                  "registra a propósito. Si falla el registro de la actividad, la edición del diagrama sigue funcionando.",
        iu="Panel de actividad", control="Control de actividad", entidades=["Participante", "Evento de actividad"], externo=None,
        mensajes=[("U", "IU", "indicarNombre(nombre)"), ("IU", "CT", "registrarParticipante(token, nombre)"),
                  ("CT", "E1", "guardarParticipante()"), ("CT", "IU", "mostrarParticipantes()"),
                  ("U", "IU", "abrirPanel()"), ("IU", "CT", "pedirHistorial()"), ("CT", "E2", "leerEventos()"),
                  ("CT", "IU", "mostrarActividad()")]),
    "CU-15": dict(
        nombre="Consultar a la IA", actores=["A1", "A2"], incluye=["CU-01"], prioridad="Alta",
        motivo="Es la primera vez que la IA actúa como integrante de la sala: conoce el diagrama y lo que hizo cada persona.",
        proposito="Preguntarle a la IA sobre el diagrama o sobre lo que hizo cada integrante, sin modificar nada.",
        iniciador="A1 o A2", inicia="A2", precondicion="El actor está en una sala con su nombre visible (CU14).",
        flujo=["El actor abre el chat con la IA, elige el modo «Preguntar» y escribe su pregunta.",
               "El sistema identifica al actor y comprueba que no haya superado el tope de pedidos.",
               "El sistema arma el contexto: el diagrama actual, la actividad de todos los integrantes y la conversación del actor.",
               "La IA responde con ese contexto.",
               "El sistema guarda la pregunta y la respuesta y las muestra en el chat; solo su dueño puede leer esa conversación."],
        postcondicion="La conversación queda guardada y el diagrama no cambia.",
        excepcion="Si el servicio de IA falla, se muestra un mensaje claro y no se guarda nada. Si se supera el tope de pedidos, se pide "
                  "esperar un momento.",
        iu="Chat con la IA", control="Control de IA", entidades=["Mensaje de chat", "Evento de actividad"], externo="Servicio de IA",
        mensajes=[("U", "IU", "escribirPregunta(texto)"), ("IU", "CT", "enviarPregunta(texto)"), ("CT", "E2", "leerActividad()"),
                  ("CT", "EX", "responder(contexto)"), ("CT", "E1", "guardarMensajes()"), ("CT", "IU", "mostrarRespuesta()")]),
    "CU-16": dict(
        nombre="Pedirle a la IA un cambio en el diagrama", actores=["A1", "A2"], incluye=["CU-06"], prioridad="Alta",
        motivo="Atraviesa identidad, actividad, IA y colaboración: valida la arquitectura de punta a punta.",
        proposito="Que la IA, como un desarrollador más de la sala, agregue, modifique o elimine clases, atributos, métodos o relaciones, "
                  "pero solo cuando alguien se lo pide.",
        iniciador="A1 o A2", inicia="A2", precondicion="El actor está en una sala con su nombre visible (CU14).",
        flujo=["El actor abre el chat con la IA, elige el modo «Pedir cambio» y escribe el pedido.",
               "El sistema comprueba el tope de pedidos y entrega a la IA el pedido con el contexto de la sala (CU6 interpreta la instrucción).",
               "La IA devuelve los cambios en el formato que ya entiende el editor.",
               "El sistema valida los cambios y cuenta cuántos elementos eliminarían; si eliminan algo, pide confirmación.",
               "Los cambios se aplican al diagrama por la misma ruta de la edición manual y se propagan a todos los integrantes.",
               "La actividad registra «IA, a pedido de X» y el chat muestra el resultado."],
        postcondicion="El diagrama cambia en todas las pantallas y queda registrado quién lo pidió.",
        excepcion="Si el servicio de IA falla, el mensaje es claro y el diagrama no cambia. Si el actor rechaza una eliminación, no cambia "
                  "nada. Los cambios enormes se rechazan.",
        iu="Chat con la IA", control="Control de IA", entidades=["Diagrama", "Evento de actividad", "Mensaje de chat"], externo="Servicio de IA",
        mensajes=[("U", "IU", "escribirPedido(texto)"), ("IU", "CT", "enviarPedido(texto)"), ("CT", "EX", "generarCambios(contexto)"),
                  ("CT", "CT", "validarCambios()"), ("CT", "E3", "guardarMensajes()"), ("CT", "E1", "aplicarCambios()"),
                  ("CT", "E2", "registrar(«IA, a pedido de X»)"), ("CT", "IU", "mostrarResultado()")]),
    "CU-17": dict(
        nombre="Revisar el diagrama con la IA", actores=["A1", "A2"], incluye=["CU-09"], prioridad="Media",
        motivo="Es el segundo modo de la IA: publica sus ideas para toda la sala y cualquiera puede aplicarlas.",
        proposito="Pedirle a la IA una revisión de clases, atributos, métodos y relaciones, ver sus ideas en la sala y aplicar la que se quiera.",
        iniciador="A1 o A2", inicia="A2", precondicion="El actor está en una sala con su nombre visible (CU14).",
        flujo=["El actor elige el modo «Revisar» y, si quiere, indica qué revisar.",
               "El sistema pide la revisión a la IA con el diagrama actual (CU9 valida la consistencia del modelo).",
               "La IA responde con observaciones y, para cada una, el pedido que la aplicaría.",
               "El sistema guarda la conversación y publica una revisión visible para toda la sala, con un botón «Aplicar» en cada idea.",
               "Cualquier actor pulsa «Aplicar» en una idea; el sistema la reserva para esa persona, la ejecuta como un pedido de cambio "
               "a su nombre (CU16) y la marca como aplicada para todos."],
        postcondicion="La sala ve las ideas de la IA; ninguna se aplica sola y cada una se aplica una sola vez.",
        excepcion="Si otra persona ya tomó la idea, el sistema avisa y no la repite; una reserva que nadie confirma vence a los 150 segundos. "
                  "Si la respuesta no tiene el formato esperado, se muestra como texto y sin botones.",
        iu="Chat con la IA", control="Control de IA", entidades=["Mensaje de chat", "Evento de actividad", "Diagrama"], externo="Servicio de IA",
        mensajes=[("U", "IU", "pedirRevisión()"), ("IU", "CT", "enviarRevisión()"), ("CT", "EX", "revisar(diagrama)"),
                  ("CT", "E1", "guardarMensajes()"), ("CT", "E2", "publicarIdeas()"), ("CT", "IU", "mostrarIdeas()"),
                  ("U", "IU", "pulsarAplicar(idea)"), ("IU", "CT", "aplicarIdea(idea)"), ("CT", "E2", "reservarYMarcarAplicada()"),
                  ("CT", "E3", "aplicarCambios()")]),
    "CU-18": dict(
        nombre="Retomar una sesión anterior", actores=["A1", "A2"], incluye=["CU-01", "CU-05"], prioridad="Media",
        motivo="Las personas cierran y vuelven otro día: no deben perder el diagrama, la actividad ni su conversación.",
        proposito="Continuar el trabajo donde se quedó, con el diagrama, la actividad de la sala y la conversación propia con la IA.",
        iniciador="A1 o A2", inicia="A2", precondicion="Ya participó en esa sala desde el mismo navegador.",
        flujo=["El actor vuelve a abrir la sala con su código (CU1).",
               "El sistema reconoce al actor por su identificador anónimo.",
               "El sistema recupera el diagrama: del estado de la sala o, si no hay nadie conectado, del respaldo (CU5).",
               "El sistema recupera el historial de actividad de la sala.",
               "El sistema recupera la conversación propia del actor con la IA."],
        postcondicion="El actor continúa donde se quedó.",
        excepcion="Si no hay respaldo, el lienzo aparece vacío. Si el actor cambió de navegador, no recupera su conversación (el identificador "
                  "vive en el navegador).",
        iu="Editor de diagrama", control="Control de colaboración", entidades=["Respaldo", "Evento de actividad", "Mensaje de chat"], externo=None,
        mensajes=[("U", "IU", "volverASala(código)"), ("IU", "CT", "recuperarSesión()"), ("CT", "E1", "leerRespaldo()"),
                  ("CT", "E2", "leerActividad()"), ("CT", "E3", "leerChatPropio()"), ("CT", "IU", "mostrarSesión()")]),
    "CU-19": dict(
        nombre="Seguir la sala desde el celular", actores=["A1", "A2"], incluye=["CU-03"], prioridad="Media",
        motivo="Lo pidió el docente para quien está viajando: informarse sin editar.",
        proposito="Ver en vivo cómo cambia el diagrama y qué hace el equipo desde el celular, en solo lectura.",
        iniciador="A1 o A2", inicia="A2", precondicion="Tiene el enlace de seguimiento de la sala.",
        flujo=["El actor abre el enlace de seguimiento en el celular.",
               "El sistema lo conecta en modo de solo lectura: no cuenta como participante ni entra al orden que define al host.",
               "El sistema le entrega el estado completo del diagrama y la actividad reciente.",
               "El actor ve el diagrama actualizándose y, debajo, la actividad, con cada cambio del equipo (CU3)."],
        postcondicion="El actor sigue la sala sin poder editar.",
        excepcion="Si ya hay 10 seguidores en la sala, el sistema rechaza uno más. Si no hay nadie que le entregue el estado, el diagrama se "
                  "muestra desde el respaldo.",
        iu="Vista móvil", control="Control de seguimiento", entidades=["Respaldo", "Evento de actividad"], externo=None,
        mensajes=[("U", "IU", "abrirEnlace()"), ("IU", "CT", "conectarSoloLectura()"), ("CT", "E1", "leerEstadoDelDiagrama()"),
                  ("CT", "IU", "mostrarDiagrama()"), ("CT", "E2", "leerEventos()"), ("CT", "IU", "mostrarActividad()")]),
}
