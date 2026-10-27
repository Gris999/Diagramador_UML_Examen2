"""Flujo de trabajo de requisitos (PUDS): actores, casos de uso, ciclos de vida, priorización y glosario.

Reglas que se siguen (material de la cátedra, síntesis de A.U.S. Gustavo Torossi del Proceso Unificado de Desarrollo
de Software de Jacobson, Booch y Rumbaugh; y guías públicas de RUP):

  * un actor es un rol de quien interactúa con el sistema desde fuera; se incluyen los sistemas externos (p. 31);
  * un caso de uso es un fragmento de funcionalidad que da un resultado de valor a un actor; crear, leer, modificar
    y borrar un mismo objeto es un solo caso de uso; se nombra con una frase verbal activa que dice el objetivo;
  * cada caso de uso lo inicia un solo actor (A2; A1 lo hereda por generalización); los demás son secundarios;
  * se detalla con: precondición, cómo empieza y termina, camino básico, caminos alternativos, postcondición,
    caminos no permitidos y requisitos especiales (p. 32);
  * include y extend solo cuando hay comportamiento común u opcional que justifique (guía de RUP: evitarlos al inicio);
    "estar en una sala" es precondición, no include; toda extensión lleva condición y punto de extensión (PUDS 7.4.5.2).

Cotejado con el libro (Jacobson, Booch y Rumbaugh, cap. 7): los sistemas externos son actores (7.2.2); los actores que se solapan se
generalizan (7.4.1.1); un caso de uso da un resultado de valor observable a un actor concreto y no se parte en pasos que no dan valor
por sí solos (7.4.1.2: «Planificación de Pagos no añadiría valor»); no se descompone funcionalmente en el modelo de casos de uso (7.4.5.3).

Las escalas de prioridad, riesgo y estado son las del material (p. 26): prioridad crítico, importante o secundario;
riesgo crítico, significativo u ordinario; estado propuesto, aprobado, incluido o validado.
"""

# ---- actores -----------------------------------------------------------------------------------------------
ACTORES = [
    ("A1", "Diseñador",
     "Persona que crea una sala o es la primera en conectarse a una sala que ya está viva (el *host*). Hace todo lo que hace un "
     "Colaborador y, además, puede expulsar a otros participantes. Es un rol temporal de la sala, no una cuenta: es una "
     "especialización de A2."),
    ("A2", "Colaborador",
     "Persona que se incorpora a una sala con su código y trabaja sobre el diagrama con las mismas capacidades de edición que el "
     "Diseñador. No tiene cuenta: se identifica con un nombre y un identificador anónimo guardados en su navegador."),
    ("A3", "Servicio de IA",
     "Sistema externo que genera las respuestas de la inteligencia artificial: Google Gemini (en la nube) u Ollama con un modelo Qwen "
     "(local). Recibe del sistema el pedido, el diagrama y la actividad, y devuelve texto o cambios al diagrama. Es un actor secundario: "
     "nunca inicia un caso de uso."),
]
NOMBRE_ACTOR = {codigo: nombre for codigo, nombre, _ in ACTORES}

# Quién no es actor, y por qué (se explica en el informe).
NO_SON_ACTORES = [
    ("La IA integrante de la sala",
     "se muestra como un integrante más, pero es una función del propio sistema: nunca inicia nada y solo actúa cuando A1 o A2 se lo piden."),
    ("El administrador",
     "elegir el proveedor de IA y el modelo local se hace con variables del servidor y scripts, no con una función que el sistema ofrezca; "
     "queda como requisito adicional (RA-01)."),
    ("El seguidor del celular",
     "son las mismas personas A1 y A2 usando la vista de solo lectura (CU13)."),
    ("Enterprise Architect",
     "herramienta externa con la que se intercambia un archivo XMI: el sistema no se comunica con ella, quien mueve el archivo es A1 o A2 (CU10)."),
]

# ---- casos de uso ------------------------------------------------------------------------------------------
# Campos: nombre, actores (el primero que no es A3 inicia; A1 hereda de A2), ciclo, origen, prioridad, riesgo, estado, motivo (por qué esa
# prioridad), rf (requisitos funcionales del proyecto), proposito, precondicion, flujo (camino básico, numerado), alternos [(condición, [pasos])],
# postcondicion, excepciones, especiales (requisitos no funcionales propios del caso), no_permitido, pantalla (captura del prototipo).
CASOS = {
    "CU1": dict(
        nombre="Ingresar a una sala de trabajo", actores=["A1", "A2"], ciclo=1, origen="Primer parcial (se agrega el nombre visible)",
        prioridad="crítico", riesgo="significativo", estado="validado", rf=["RF-06", "RF-12", "RF-23"],
        motivo="Es la puerta de entrada de todo lo demás: sin sala no hay edición, colaboración ni IA.",
        proposito="Entrar al lienzo compartido de un equipo, ya sea creando una sala nueva o uniéndose a una con su código, "
                  "identificándose con un nombre que los demás ven.",
        precondicion="El actor abre la página principal. Para unirse a una sala, conoce el código que le dio quien la creó.",
        flujo=["El actor elige «Crear Nuevo Lienzo», o escribe el código de una sala y elige «Unirse al Lienzo».",
               "El sistema genera un identificador único de sala (o comprueba el del código escrito).",
               "El sistema lee del navegador el identificador anónimo del actor, o crea uno nuevo.",
               "Si el actor aún no tiene un nombre guardado, el sistema pregunta «¿Cómo deseas que te vean en la sala?» y el actor lo escribe.",
               "El sistema valida el nombre, registra al actor en la sala y le asigna el rol: Diseñador si es el primero en la sala viva, Colaborador si no.",
               "El sistema abre el editor y muestra la lista de participantes con el nombre y el rol de cada uno."],
        alternos=[("El código escrito no es un código de sala (no tiene el formato que genera «Crear Nuevo Lienzo»)",
                   ["El sistema avisa «El código no es válido» y el actor permanece en la página principal."]),
                  ("El código tiene el formato correcto pero nadie ha trabajado todavía en esa sala",
                   ["El sistema abre una sala vacía con ese código."])],
        postcondicion="El actor está en la sala con su nombre y su rol, y los demás lo ven en la lista de participantes.",
        excepciones=["Si el nombre o el identificador no son válidos, el sistema los ignora y el actor figura con un nombre genérico; no se rechaza."],
        especiales=["No hay cuentas ni contraseñas: el código de la sala es la llave de acceso.",
                    "El identificador anónimo y el nombre se guardan en el navegador del actor.",
                    "El rol existe solo mientras la sala está viva: al reconectarse, el actor entra como una conexión nueva (RF-16, RF-17)."],
        no_permitido=["Entrar al editor sin haber pasado por la sala."],
        pantalla="01-inicio.png"),
    "CU2": dict(
        nombre="Modelar el diagrama de clases UML", actores=["A1", "A2"], ciclo=1, origen="Primer parcial",
        prioridad="crítico", riesgo="crítico", estado="validado", rf=["RF-01", "RF-02"],
        motivo="Fija el modelo del diagrama (grafo de JointJS) del que cuelgan la colaboración, la IA, el intercambio y los generadores.",
        proposito="Dibujar y editar el diagrama de clases: clases, atributos, métodos, relaciones y multiplicidades.",
        precondicion="El actor está en una sala (CU1).",
        flujo=["El actor arrastra una «Clase UML» de la paleta al lienzo.",
               "El actor edita con doble clic el nombre, los atributos y los métodos de la clase.",
               "El actor une dos clases arrastrando desde un círculo de conexión y elige el tipo de relación: asociación, agregación, composición, "
               "generalización o dependencia.",
               "El actor edita las multiplicidades y las etiquetas de la relación.",
               "Si una asociación queda con «muchos» en ambos extremos, el sistema crea la entidad intermedia con sus dos relaciones 1:N.",
               "El sistema actualiza el lienzo y guarda el estado local."],
        alternos=[("El actor elimina un elemento",
                   ["El sistema elimina el elemento y sus relaciones; las demás se conservan."]),
                  ("El actor edita una relación generada para que deje de ser «muchos»",
                   ["El sistema restaura la asociación original: ninguna relación desaparece."]),
                  ("El actor une una clase con una asociación «muchos a muchos»",
                   ["El sistema crea una clase asociativa que se resuelve como dos relaciones 1:N."])],
        postcondicion="El diagrama refleja los cambios del actor.",
        excepciones=["Agregación, composición, dependencia y generalización con «muchos» en ambos extremos no se transforman."],
        especiales=["Los tipos de relación y las multiplicidades siguen UML 2.5.",
                    "La edición responde sin esperar al servidor: el lienzo vive en el navegador."],
        no_permitido=["Relaciones sin clase de origen o de destino."],
        pantalla="03-editor.png"),
    "CU5": dict(
        nombre="Retomar el trabajo en otra sesión", actores=["A1", "A2"], ciclo=1, origen="Primer parcial (guardar y recuperar), ampliado",
        prioridad="crítico", riesgo="significativo", estado="validado", rf=["RF-10", "RF-11", "RF-31"],
        motivo="El ingeniero exigió persistencia obligatoria: lo avanzado hoy se continúa mañana con todo registrado.",
        proposito="Continuar el trabajo donde se quedó, con el diagrama, la actividad de la sala y la conversación con la IA.",
        precondicion="El actor ya participó en esa sala desde el mismo navegador.",
        flujo=["El actor vuelve a abrir la sala con su código (CU1).",
               "El sistema reconoce al actor por su identificador anónimo.",
               "El sistema recupera el diagrama: del estado de la sala viva o, si no hay nadie conectado, del último respaldo.",
               "El sistema recupera el historial de actividad de la sala (CU6).",
               "El sistema recupera la conversación de la sala con la IA (CU9)."],
        alternos=[("No existe respaldo de la sala", ["El sistema muestra el lienzo vacío."]),
                  ("El actor abre la sala desde otro navegador", ["El sistema lo trata como una persona nueva: debe indicar su nombre."])],
        postcondicion="El actor continúa donde se quedó.",
        excepciones=["Un respaldo atrasado no pisa lo que ya envió la sala."],
        especiales=["El respaldo se guarda solo, cada cierto tiempo, mientras la sala está viva.",
                    "La actividad y la conversación se guardan en MongoDB; el respaldo del diagrama, en PostgreSQL (RA-06)."],
        no_permitido=[],
        pantalla="03-editor.png"),
    "CU3": dict(
        nombre="Colaborar en la edición del diagrama", actores=["A1", "A2"], ciclo=2, origen="Primer parcial",
        prioridad="crítico", riesgo="crítico", estado="validado", rf=["RF-06", "RF-08", "RF-09", "RF-10", "RF-13", "RF-15", "RF-16", "RF-17"],
        motivo="Fija el canal de tiempo real, los roles y la recuperación de estado; la arquitectura entera depende de él.",
        proposito="Que dos o tres personas editen el mismo diagrama a la vez y vean al instante lo que hacen las demás.",
        precondicion="Los actores están en la misma sala (CU1).",
        flujo=["Un actor edita el diagrama (CU2).",
               "El sistema envía el cambio, como una operación pequeña, a los demás participantes de la sala.",
               "El sistema de cada participante aplica la operación y actualiza su lienzo.",
               "Cada cierto tiempo, el sistema guarda un respaldo del diagrama en el servidor."],
        alternos=[("Un actor entra a una sala que ya tiene a alguien",
                   ["El sistema pide el estado completo a un participante.", "El participante lo envía y el diagrama aparece."]),
                  ("Un actor entra a una sala vacía", ["El sistema carga el último respaldo."]),
                  ("Un actor se desconecta y vuelve", ["Entra como una conexión nueva y recupera el diagrama; no recupera su rol anterior."]),
                  ("El Diseñador se desconecta", ["El participante más antiguo pasa a ser Diseñador."])],
        postcondicion="Todos los participantes ven el mismo diagrama.",
        excepciones=["Lo que un actor borró no reaparece en la pantalla de otro que recarga."],
        especiales=["Funciona con dos o tres personas a la vez.",
                    "Todos los participantes tienen los mismos permisos de edición (RF-13)."],
        no_permitido=["Que el diagrama de un participante quede distinto al de los demás tras sincronizar."],
        pantalla="04-colaboracion.png"),
    "CU4": dict(
        nombre="Expulsar a un participante", actores=["A1"], ciclo=2, origen="Primer parcial",
        prioridad="importante", riesgo="ordinario", estado="validado", rf=["RF-07", "RF-09", "RF-14"],
        motivo="Es el único permiso que distingue al Diseñador de un Colaborador; el servidor lo verifica.",
        proposito="Sacar a otro participante de la sala activa.",
        precondicion="El actor es el Diseñador (el host actual) y hay otro participante conectado.",
        flujo=["El actor pulsa «Expulsar» junto a un participante.",
               "El sistema verifica que quien lo pide es el host actual.",
               "El sistema cierra la conexión del expulsado y actualiza la presencia de todos.",
               "El expulsado ve el aviso «El host te expulsó de la sala»."],
        alternos=[("Quien lo pide no es el host", ["El sistema rechaza el pedido y no pasa nada."]),
                  ("El expulsado vuelve a entrar", ["Entra como un participante nuevo, sin rol previo."])],
        postcondicion="El participante deja de recibir y de enviar cambios.",
        excepciones=["Si el expulsado cierra la pestaña a mitad del aviso, no se guarda un respaldo suyo."],
        especiales=["El permiso lo verifica el servidor, no el navegador."],
        no_permitido=["Que un Colaborador expulse a alguien."],
        pantalla="04-colaboracion.png"),
    "CU7": dict(
        nombre="Modificar el modelo con la IA", actores=["A1", "A2", "A3"], ciclo=2, origen="Primer parcial (texto y voz), ampliado: la IA como integrante",
        prioridad="crítico", riesgo="crítico", estado="validado", rf=["RF-03", "RF-05", "RF-28", "RF-29"],
        motivo="Atraviesa identidad, actividad, IA y colaboración: valida la arquitectura de punta a punta y es lo que más reduce el tiempo de desarrollo.",
        proposito="Que la IA, como un desarrollador más de la sala, agregue, cambie o elimine clases, atributos, métodos y relaciones a partir de una "
                  "instrucción escrita o dictada, y solo cuando alguien se lo pide.",
        precondicion="El actor está en una sala con su nombre visible (CU1). Para dictar, usa Google Chrome con HTTPS.",
        flujo=["El actor escribe la instrucción en «Generar modelo» o en el chat con la IA, en modo «Pedir cambio» (o la dicta con el micrófono).",
               "El sistema comprueba los topes de uso y arma el contexto: el diagrama actual, la actividad y la conversación de la sala.",
               "El sistema envía el pedido al servicio de IA.",
               "El servicio de IA devuelve los cambios.",
               "El sistema valida los cambios y cuenta cuántos elementos eliminarían.",
               "El sistema aplica los cambios al diagrama por la misma ruta de la edición manual (CU2) y los propaga a todos (CU3).",
               "El sistema registra en la actividad «IA, a pedido de X» (CU6) y guarda la conversación."],
        alternos=[("Los cambios eliminan elementos", ["El sistema pide confirmación al actor.", "Si el actor la rechaza, no cambia nada."]),
                  ("Los cambios son enormes", ["El sistema los rechaza."]),
                  ("El actor aplica una idea publicada por la IA en una revisión (CU9)",
                   ["El sistema ejecuta la idea como un pedido de cambio a nombre de quien la aplica."])],
        postcondicion="El diagrama cambia en todas las pantallas y queda registrado quién lo pidió.",
        excepciones=["Si el servicio de IA falla o devuelve algo inválido, el sistema muestra un mensaje claro y el diagrama no cambia."],
        especiales=["La IA no hace nada hasta que alguien se lo pide.",
                    "Hay topes de uso por persona, por sala y para todo el servicio (RA-03).",
                    "El proveedor es intercambiable: Gemini o el modelo local reentrenado (RA-01)."],
        no_permitido=["Que la IA modifique el diagrama por iniciativa propia."],
        pantalla="02-generar-modelo.png"),
    "CU8": dict(
        nombre="Crear el modelo desde una imagen", actores=["A1", "A2", "A3"], ciclo=2, origen="Primer parcial",
        prioridad="importante", riesgo="significativo", estado="validado", rf=["RF-04"],
        motivo="Aprovecha diagramas dibujados a mano o impresos y acorta el arranque de un proyecto.",
        proposito="Obtener un diagrama de clases a partir de la foto o captura de uno existente.",
        precondicion="El actor está en una sala (CU1) y tiene la imagen.",
        flujo=["El actor elige «Importar Imagen» y sube la imagen.",
               "El sistema envía la imagen al servicio de IA con capacidad de visión.",
               "El servicio devuelve las clases, atributos, métodos y relaciones que reconoce.",
               "El sistema muestra el modelo reconocido.",
               "El actor elige «Reemplazar» el diagrama actual o «Combinar» con él.",
               "El sistema aplica el modelo y lo propaga a la sala (CU3)."],
        alternos=[("El actor cancela o pulsa Escape", ["No cambia nada."])],
        postcondicion="El diagrama contiene las clases y relaciones reconocidas.",
        excepciones=["Si la imagen no es legible, el sistema muestra un error y el diagrama no cambia."],
        especiales=["La imagen se envía al servicio de IA: los datos viajan fuera del sistema."],
        no_permitido=[],
        pantalla=None),
    "CU10": dict(
        nombre="Intercambiar el diagrama con otras herramientas", actores=["A1", "A2"], ciclo=3, origen="Primer parcial",
        prioridad="importante", riesgo="crítico", estado="validado", rf=["RF-18"],
        motivo="Fija el formato de intercambio con una herramienta externa, Enterprise Architect, y el riesgo de seguridad de leer archivos de afuera.",
        proposito="Llevar el diagrama a Enterprise Architect y traer un modelo hecho allí (XMI), o exportar el diagrama como imagen.",
        precondicion="El actor está en una sala (CU1). Para exportar, el diagrama tiene al menos una clase; para importar, tiene un archivo .xmi.",
        flujo=["El actor elige «Exportar XMI».",
               "El sistema envía el diagrama al servidor.",
               "El servidor genera el archivo XMI 2.1, con la posición y el tamaño de cada clase.",
               "El navegador descarga el archivo y Enterprise Architect puede abrirlo."],
        alternos=[("El actor elige «Importar XMI»",
                   ["El actor elige el archivo.", "El servidor lo valida: rechaza declaraciones DOCTYPE y entidades externas.",
                    "El servidor convierte el modelo en diagrama, con posición y tamaño si el archivo trae los metadatos del editor.",
                    "El editor muestra el diagrama y lo propaga a la sala (CU3)."]),
                  ("El actor elige «Exportar como Imagen»", ["El sistema genera un PNG de fondo claro y sin los elementos de la aplicación."])],
        postcondicion="Existe el archivo pedido, o el diagrama importado está en la sala.",
        excepciones=["Un archivo mal formado o con construcciones inseguras produce un error claro y el diagrama actual no cambia."],
        especiales=["Al importar no se leen archivos locales ni se abren conexiones (seguridad XXE).",
                    "La ida y la vuelta se probaron con Enterprise Architect 17.2: clases, atributos, operaciones, asociaciones y multiplicidades se conservan."],
        no_permitido=["Importar un archivo con entidades externas."],
        pantalla="08-exportaciones.png"),
    "CU11": dict(
        nombre="Generar el backend del sistema", actores=["A1"], ciclo=3, origen="Primer parcial",
        prioridad="crítico", riesgo="significativo", estado="validado", rf=["RF-19", "RF-20"],
        motivo="Es uno de los productos principales de la herramienta CASE y la razón de que reduzca el tiempo de desarrollo.",
        proposito="Obtener un proyecto Spring Boot con PostgreSQL, en capas (entidad, DTO, repositorio, servicio y controlador), con su colección "
                  "de Postman y el script SQL de las tablas.",
        precondicion="El diagrama tiene clases (CU2).",
        flujo=["El actor elige «Exportar a Backend».",
               "El sistema envía el diagrama al generador.",
               "El generador crea el proyecto Spring Boot con persistencia PostgreSQL y la colección de Postman.",
               "El navegador descarga el archivo .zip."],
        alternos=[("El actor elige «Exportar como SQL»", ["El sistema genera el guion de creación de las tablas a partir del diagrama."])],
        postcondicion="El proyecto descomprimido compila con el Maven Wrapper incluido.",
        excepciones=["Si el generador no responde, el sistema avisa y no descarga nada."],
        especiales=["El proyecto usa Java 21 y Spring Boot 3.5.", "El generador compila de verdad el proyecto en sus pruebas."],
        no_permitido=[],
        pantalla="08-exportaciones.png"),
    "CU12": dict(
        nombre="Generar la aplicación móvil", actores=["A1"], ciclo=3, origen="Primer parcial",
        prioridad="importante", riesgo="significativo", estado="validado", rf=["RF-21", "RF-22", "RNF-01"],
        motivo="Cubre la salida móvil con persistencia sin conexión.",
        proposito="Obtener un proyecto Flutter con base de datos local SQLite, para que la aplicación funcione sin conexión.",
        precondicion="El diagrama tiene clases (CU2).",
        flujo=["El actor elige «Exportar Flutter».",
               "El sistema genera el proyecto con los modelos, la base SQLite local, las pantallas CRUD y un asistente de comandos.",
               "El navegador descarga el archivo .zip."],
        alternos=[],
        postcondicion="Existe un proyecto Flutter que guarda sus datos localmente.",
        excepciones=["Un diagrama inválido produce un error claro."],
        especiales=["El CRUD generado funciona sin red y los datos persisten (validado en un dispositivo)."],
        no_permitido=[],
        pantalla="08-exportaciones.png"),
    "CU6": dict(
        nombre="Consultar la actividad del equipo", actores=["A1", "A2"], ciclo=4, origen="Nuevo",
        prioridad="importante", riesgo="significativo", estado="validado", rf=["RF-23", "RF-25", "RNF-06"],
        motivo="Es el contexto que usa la IA para saber quién hizo qué, y lo que usa una persona que llega tarde para ponerse al día.",
        proposito="Ver, en tiempo real, quién está en la sala y qué hizo cada integrante, incluida la IA.",
        precondicion="El actor está en una sala con su nombre visible (CU1).",
        flujo=["El actor abre el panel de actividad.",
               "El sistema pide el historial reciente de la sala.",
               "El sistema muestra los eventos, del más nuevo al más viejo, con el autor, el tipo de acción y un resumen.",
               "Cada acción nueva de cualquier integrante llega en vivo y se agrega arriba."],
        alternos=[("Mover o cambiar el tamaño de un elemento", ["El sistema no lo registra, a propósito."]),
                  ("Un integrante edita varias veces el mismo texto en pocos segundos", ["El sistema lo registra como un solo evento."])],
        postcondicion="El panel muestra quién hizo qué y cuándo.",
        excepciones=["Si falla el registro de la actividad, la edición del diagrama sigue funcionando."],
        especiales=["El registro no degrada la edición: las acciones continuas no se registran y hay topes de tamaño y de frecuencia (RNF-06)."],
        no_permitido=[],
        pantalla="03-editor.png"),
    "CU9": dict(
        nombre="Consultar a la IA", actores=["A1", "A2", "A3"], ciclo=4, origen="Primer parcial (analizar y validar), ampliado",
        prioridad="importante", riesgo="significativo", estado="aprobado", rf=["RF-24", "RF-26", "RF-27", "RF-30"],
        motivo="Es la forma de usar a la IA como asesora del equipo: conoce el diagrama y lo que hizo cada persona.",
        proposito="Obtener la opinión de la IA sobre el diagrama o sobre lo que hizo el equipo, sin modificar nada: preguntar, pedir una revisión con "
                  "ideas que cualquiera puede aplicar, o validar la consistencia del modelo.",
        precondicion="El actor está en una sala con su nombre visible (CU1).",
        flujo=["El actor abre el chat con la IA de la sala, elige el modo «Preguntar» (o «Revisar») y escribe su mensaje.",
               "El sistema comprueba los topes de uso y arma el contexto: el diagrama, la actividad y la conversación de la sala.",
               "El sistema envía el pedido al servicio de IA.",
               "El servicio de IA responde.",
               "El sistema guarda la pregunta y la respuesta en la conversación de la sala y las muestra a todos.",
               "En modo «Revisar», el sistema además publica en la actividad una revisión con hasta cinco ideas, cada una con un botón «Aplicar»."],
        alternos=[("Un actor pulsa «Aplicar» en una idea",
                   ["El sistema reserva la idea para esa persona.", "El sistema la ejecuta como un pedido de cambio a su nombre (CU7).",
                    "El sistema la marca como aplicada para toda la sala."]),
                  ("Otra persona ya tomó la idea", ["El sistema avisa y no la repite; una reserva que nadie confirma vence a los 150 segundos."]),
                  ("El actor pide analizar la consistencia del modelo", ["El sistema devuelve observaciones sobre las relaciones del diagrama."])],
        postcondicion="La sala ve la respuesta o las ideas de la IA; ninguna idea se aplica sola y cada una se aplica una sola vez.",
        excepciones=["Si el servicio de IA falla, el sistema muestra un mensaje claro y no guarda nada.",
                     "Si se supera el tope de pedidos, el sistema pide esperar un momento.",
                     "Si la respuesta de una revisión no tiene el formato esperado, se muestra como texto y sin botones."],
        especiales=["Hay una sola instancia de IA para toda la sala: atiende un pedido a la vez y su conversación es la de todos (RA-02).",
                    "El estado «Pensando (a pedido de X)» se comparte con la sala."],
        no_permitido=["Que una revisión cambie el diagrama sin que alguien pulse «Aplicar»."],
        pantalla="07-revision-ideas.png"),
    "CU13": dict(
        nombre="Mantenerse informado desde el celular", actores=["A1", "A2"], ciclo=4, origen="Nuevo",
        prioridad="importante", riesgo="ordinario", estado="aprobado", rf=["RF-32", "RF-34"],
        motivo="Lo pidió el ingeniero para quien está viajando: informarse de lo que pasa sin tener que editar.",
        proposito="Ver en vivo cómo cambia el diagrama y qué hace el equipo desde el celular, en solo lectura, y recibir avisos de lo importante.",
        precondicion="El actor tiene el enlace de seguimiento de la sala.",
        flujo=["En el editor, el actor pulsa «Copiar enlace para seguir desde el celular» y lo abre en el teléfono.",
               "El sistema lo conecta en modo de solo lectura: no cuenta como participante ni como host.",
               "El sistema le entrega el estado del diagrama y la actividad reciente.",
               "El actor ve el diagrama actualizándose y, debajo, la actividad.",
               "Si el actor autorizó los avisos, el sistema le notifica cuando alguien cambia el diagrama o la IA publica una idea."],
        alternos=[("El actor no autoriza los avisos", ["Solo ve la pantalla."]),
                  ("No hay nadie que entregue el estado", ["El sistema muestra el diagrama desde el último respaldo."])],
        postcondicion="El actor sigue la sala sin poder editar.",
        excepciones=["Si ya hay diez seguidores en la sala, el sistema rechaza a uno más."],
        especiales=["Es de solo lectura: no tiene controles de edición.",
                    "Los avisos funcionan con la página abierta en el navegador del celular."],
        no_permitido=["Editar el diagrama desde la vista del celular."],
        pantalla="09-vista-movil.png"),
    "CU14": dict(
        nombre="Aprender a usar la herramienta con el asistente de ayuda", actores=["A1", "A2", "A3"], ciclo=4, origen="Nuevo",
        prioridad="secundario", riesgo="ordinario", estado="aprobado", rf=["RF-35"],
        motivo="El ingeniero pidió un mecanismo para que el usuario aprenda a usar la herramienta sin problema: un asistente de IA que conozca el proyecto.",
        proposito="Resolver una duda de uso («¿cómo exporto el diagrama?») preguntándole a un asistente de IA que conoce el manual y las funciones.",
        precondicion="Ninguna: está disponible desde la página principal y dentro de la sala.",
        flujo=["El actor abre «Ayuda».",
               "El actor escribe su pregunta.",
               "El sistema arma el contexto con el manual de usuario y la lista de funciones.",
               "El sistema envía la pregunta al servicio de IA.",
               "El sistema muestra la respuesta, paso a paso."],
        alternos=[("La pregunta no trata de la herramienta", ["El asistente lo indica y propone preguntar sobre su uso."])],
        postcondicion="El actor sabe cómo hacer lo que preguntó.",
        excepciones=["Si el servicio de IA falla, el sistema muestra un mensaje claro («La IA no pudo responder ahora. Intenta de nuevo.»); la pregunta queda en la conversación y la persona puede volver a intentar."],
        especiales=["Solo responde sobre la herramienta.", "Tiene tope de uso (RA-03). La conversación es personal, no de la sala."],
        no_permitido=[],
        pantalla=None),
}

# Orden de presentación dentro de cada ciclo (prioridad, como en los informes de referencia).
CICLOS = [
    (1, "Base del lienzo: entrar, modelar y retomar", ["CU1", "CU2", "CU5"]),
    (2, "Colaboración, control de la sala y entrada con IA", ["CU3", "CU4", "CU7", "CU8"]),
    (3, "Intercambio y generación de código", ["CU10", "CU11", "CU12"]),
    (4, "La IA como integrante, actividad, celular y ayuda (nuevo en el segundo parcial)", ["CU6", "CU9", "CU13", "CU14"]),
]

# Relaciones entre casos de uso. Solo se declara lo que cumple la regla: extend = comportamiento opcional de otro caso.
RELACIONES = [
    ("CU7", "CU9", "extend", "Aplicar una idea de la IA"),
]
# Una extensión lleva una condición y un punto de extensión en el caso destino (PUDS, sección 7.4.5.2). El punto está en el alterno de CU9
# «Un actor pulsa Aplicar en una idea».
CONDICION_EXTENSION = {
    ("CU7", "CU9"): "el actor pulsa «Aplicar» en una de las ideas que la IA publicó en la revisión y nadie la tomó antes",
}

# Vista de la arquitectura del modelo de casos de uso: los significativos para la arquitectura (PUDS p. 29 y 32).
SIGNIFICATIVOS = ["CU1", "CU2", "CU3", "CU5", "CU7"]
PORQUE_SIGNIFICATIVOS = {
    "CU1": "define la sala, la identidad y los roles",
    "CU2": "fija el modelo del diagrama del que cuelga todo",
    "CU3": "fija el canal de tiempo real y la recuperación de estado",
    "CU5": "obliga a la persistencia de la sesión",
    "CU7": "atraviesa identidad, actividad, IA y colaboración",
}

# ---- requisitos adicionales (no asociables a un caso de uso: PUDS p. 28) -------------------------------------
REQUISITOS_ADICIONALES = [
    ("RA-01", "IA local reentrenada",
     "El ingeniero la pidió como extra valorable, no obligatoria. Un modelo abierto (Qwen) reentrenado con LoRA se sirve con Ollama y reemplaza "
     "a Gemini sin cambiar lo que ve el usuario; el proveedor se elige con una variable del servidor.",
     "Anexos A y B"),
    ("RA-02", "Conversación única de la sala",
     "La IA es una sola instancia que atiende a todos y guarda el contexto de la conversación de todos: no hay conversaciones privadas.",
     "Prueba de la conversación compartida (CP de CU9)"),
    ("RA-03", "Control del costo y resiliencia de la IA",
     "Hay topes de uso por persona, por sala y para todo el servicio; una respuesta que eliminaría elementos pide confirmación; y si la IA falla "
     "el diagrama no se pierde ni se corrompe.",
     "Pruebas de topes y de fallo del proveedor"),
    ("RA-04", "Persistencia continua",
     "Todo lo que se hace en una sala (diagrama, actividad y conversación) queda guardado para continuar en otra sesión.",
     "Pruebas de CU5"),
    ("RA-05", "Despliegue seguro y reproducible",
     "Sitio en AWS con HTTPS, sin puertos internos expuestos, y con una prueba de humo.",
     "Anexo C"),
    ("RA-06", "Bases de datos adecuadas a cada dato",
     "PostgreSQL guarda lo relacional (participantes, topes de uso, respaldo del diagrama); MongoDB, la conversación y la actividad, que son "
     "documentos que solo se agregan; Redis, el estado efímero de la sala (quién está y en qué orden).",
     "Diseño de datos y pruebas de las tres capas"),
]

# ---- glosario (PUDS p. 30) -----------------------------------------------------------------------------------
GLOSARIO = [
    ("Sala", "Espacio compartido, identificado por un código, donde varias personas editan un mismo diagrama."),
    ("Diseñador (host)", "Rol temporal del participante que lleva más tiempo conectado en la sala viva; puede expulsar a otros."),
    ("Colaborador", "Participante de la sala que edita el diagrama; no tiene cuenta."),
    ("Presencia", "Lista en vivo de quién está en la sala, con su nombre y su rol."),
    ("Operación", "Mensaje pequeño que describe un cambio del diagrama (agregar una clase, editar un texto, enlazar, borrar)."),
    ("Respaldo", "Copia del diagrama de una sala guardada en el servidor para recuperar el estado."),
    ("Entidad intermedia", "Clase que el editor crea para representar una relación muchos a muchos."),
    ("Clase asociativa", "Clase UML unida a una asociación para describirla; se resuelve como dos relaciones 1:N."),
    ("XMI", "Formato XML para intercambiar modelos UML entre herramientas."),
    ("Registro de actividad", "Lista, visible para todos, de las acciones relevantes de la sala: quién hizo qué."),
    ("Servicio de IA", "Sistema externo que genera las respuestas de la IA: Gemini en la nube u Ollama con un modelo local."),
    ("Conversación de la sala", "Historial de preguntas y respuestas con la IA, compartido por todos los integrantes."),
    ("Idea", "Sugerencia de una revisión de la IA que no cambia nada hasta que una persona pulsa «Aplicar»."),
    ("Modelo reentrenado", "Modelo abierto (Qwen) ajustado con LoRA para modificar diagramas; funciona sin internet."),
    ("Vista del celular", "Página de solo lectura para seguir una sala en vivo."),
    ("Asistente de ayuda", "Modo de la IA que conoce el manual y responde cómo usar la herramienta."),
]


# ---- consultas -------------------------------------------------------------------------------------------------
def numero(codigo):
    """CU14 -> 14: sirve para ordenar."""
    return int(codigo[2:])


def inicia(codigo):
    """Actor que inicia el caso de uso: A2 (A1 lo hereda por generalización), o A1 si solo A1 lo puede hacer."""
    actores = CASOS[codigo]["actores"]
    return "A2" if "A2" in actores else actores[0]


def actores_dibujados(codigo):
    """Si están A1 y A2, solo se une A2: la generalización A1 -> A2 dice que el Diseñador también lo hace."""
    actores = CASOS[codigo]["actores"]
    return [a for a in actores if not (a == "A1" and "A2" in actores)]


def casos_del_ciclo(ciclo):
    return next(codigos for numero_ciclo, _, codigos in CICLOS if numero_ciclo == ciclo)


def validar():
    """Comprobaciones del modelo: se corren al generar el informe."""
    errores = []
    en_ciclos = [c for _, _, codigos in CICLOS for c in codigos]
    if sorted(en_ciclos, key=numero) != sorted(CASOS, key=numero) or len(en_ciclos) != len(set(en_ciclos)):
        errores.append("cada caso de uso debe estar en exactamente un ciclo")
    for codigo, caso in CASOS.items():
        if not set(caso["actores"]) <= set(NOMBRE_ACTOR):
            errores.append(f"{codigo}: actor desconocido")
        if caso["actores"][0] == "A3":
            errores.append(f"{codigo}: un actor secundario no inicia un caso de uso")
        if not caso["flujo"]:
            errores.append(f"{codigo}: sin camino básico")
        for campo in ("proposito", "precondicion", "postcondicion", "motivo"):
            if not caso[campo]:
                errores.append(f"{codigo}: falta {campo}")
    for origen, destino, tipo, _ in RELACIONES:
        if origen not in CASOS or destino not in CASOS or tipo not in ("include", "extend"):
            errores.append(f"relación inválida {origen}->{destino}")
        if tipo == "extend" and not CONDICION_EXTENSION.get((origen, destino)):
            errores.append(f"extensión {origen}->{destino} sin condición")
    if errores:
        raise ValueError("; ".join(errores))
    return True
