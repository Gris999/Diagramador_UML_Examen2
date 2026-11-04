"""Flujo de trabajo de pruebas (PUDS cap. 12): un caso de prueba por cada camino de cada caso de uso.

Reglas que se siguen (Jacobson, Booch y Rumbaugh, cap. 12; material de la cátedra):

  * el modelo de casos de prueba se saca del modelo de casos de uso: cada camino de cada caso de uso (el básico, cada alternativo, cada
    excepción y cada camino no permitido) tiene al menos un caso de prueba con sus entradas, sus condiciones y su resultado esperado;
  * un caso de prueba se ejecuta con un componente de prueba automático (una prueba de la aplicación) o con un procedimiento de prueba
    manual (pasos que una persona repite en el navegador); lo que se puede automatizar se automatiza;
  * `validar()` comprueba que el documento coincide con el software y al revés: cada camino del modelo de requisitos tiene su caso y cada caso
    pertenece a un camino; cada prueba automática que un caso cita existe de verdad en el repositorio (se busca por archivo y nombre).

El índice de pruebas se arma leyendo los archivos de prueba del repositorio: Django (`def test_*`), Angular (`it('…')`) y Spring (`@Test`).
"""

import re
from pathlib import Path

from modelo import requisitos as R

RAIZ = Path(__file__).resolve().parents[2]
CODIGO = {
    "back": RAIZ / "back_generador_bd",
    "front": RAIZ / "front_generador_bd" / "src",
    "java": RAIZ / "back_generator_uml" / "src" / "test" / "java" / "generator_uml" / "back_generator_uml",
}
NOMBRE_PILA = {"back": "Django", "front": "Angular", "java": "Spring Boot"}


def indice_pruebas():
    """Todas las pruebas automáticas del repositorio: {(pila, archivo relativo, nombre)}."""
    indice = set()
    for archivo in sorted(CODIGO["back"].glob("**/test_*.py")):
        if ".venv" in archivo.parts:
            continue
        clase = None
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            m = re.match(r"class (\w+)[(:]", linea)
            if m:
                clase = m.group(1)
            m = re.match(r"\s+(?:async\s+)?def (test_\w+)\(", linea)
            if m:
                indice.add(("back", archivo.relative_to(CODIGO["back"]).as_posix(), f"{clase}.{m.group(1)}"))
    for archivo in sorted(CODIGO["front"].glob("**/*.spec.ts")):
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*it\((?:'([^']*)'|\"([^\"]*)\"|`([^`]*)`)", linea)
            if m:
                indice.add(("front", archivo.relative_to(CODIGO["front"]).as_posix(), m.group(1) or m.group(2) or m.group(3)))
    for archivo in sorted(CODIGO["java"].glob("**/*.java")):
        texto = archivo.read_text(encoding="utf-8")
        for m in re.finditer(r"@(?:Test|ParameterizedTest)[^\n]*\n(?:\s*@[^\n]*\n)*\s*(?:public\s+)?void\s+(\w+)", texto):
            indice.add(("java", archivo.relative_to(CODIGO["java"]).as_posix(), m.group(1)))
    return indice


def b(archivo, nombre):
    return ("back", archivo, nombre)


def f(archivo, nombre):
    return ("front", archivo, nombre)


def j(archivo, nombre):
    return ("java", archivo, nombre)


CASOS_DE_PRUEBA = []


def caso(cu, camino, entrada, esperado, nivel="unidad", auto=(), manual=None):
    """`manual`: pasos de un procedimiento de prueba que una persona repite en el navegador (o None si no hace falta)."""
    CASOS_DE_PRUEBA.append(dict(cu=cu, camino=camino, entrada=entrada, esperado=esperado, nivel=nivel, auto=list(auto), manual=manual))


# ---- Ciclo 1 -------------------------------------------------------------------------------------------------
caso("CU1", "B",
     "Una persona abre la página principal y pulsa «Crear Nuevo Lienzo» (o escribe un código válido y pulsa «Unirse al Lienzo»); su navegador ya guarda un "
     "identificador y un nombre (o se los pide).",
     "Se abre el editor en la dirección /diagram/<código>; el código nuevo es único; el servidor registra a la persona con su nombre y le da el rol: Host si "
     "es la primera de la sala viva, Participante si no; la lista de participantes muestra el nombre y el rol de cada uno.",
     "integración",
     [f("app/landin-page/landin-page.spec.ts", "creates a new room with a unique code and opens its editor"),
      f("app/landin-page/landin-page.spec.ts", "joins the room whose code is typed, ignoring spaces and capital letters"),
      f("services/colaboration/identity.service.spec.ts", "remembers a UUID token and sanitized display name in browser storage"),
      f("services/colaboration/signaling.service.spec.ts", "sends the remembered identity only after the socket opens"),
      b("collab/tests/test_roles.py", "CanvasRoleTests.test_join_order_assigns_roles_and_empty_room_resets_host"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_hello_adds_sanitized_names_and_late_joiner_sees_them"),
      f("app/participants-panel/participants-panel.spec.ts", "shows host role, current client, and removal action to the host")],
     manual=["Abrir la página principal y pulsar «Crear Nuevo Lienzo»: el navegador pregunta el nombre y abre el editor.",
             "Copiar el código de la sala y, en otra ventana de incógnito, escribirlo en «Unirse al Lienzo» con otro nombre.",
             "Comprobar que el panel «Participantes» muestra a las dos personas, la primera como Host y la segunda como Participante."])
caso("CU1", "A1",
     "Se escribe «mi-sala» (o cualquier texto que no sea un identificador de sala) en «Unirse al Lienzo».",
     "No se entra; debajo del cuadro aparece «El código no es válido…»; el aviso desaparece al editar el código; sin código el botón está desactivado.",
     "unidad",
     [f("app/landin-page/landin-page.spec.ts", "does not join with something that is not a room code and tells the person why"),
      f("app/landin-page/landin-page.spec.ts", "clears the warning when the person edits the code again"),
      f("app/landin-page/landin-page.spec.ts", "does not let a person join without typing a code")])
caso("CU1", "A2",
     "Se escribe un código con el formato correcto que nadie ha usado todavía.",
     "Se abre el editor con una sala vacía con ese código: no hay respaldo (el servidor responde 404) y el lienzo queda en blanco.",
     "integración",
     [b("uml_api/tests/test_backup_uml_api.py", "BackupUmlApiTests.test_get_backup_for_unknown_room_returns_404"),
      f("services/colaboration/collaboration.service.spec.ts", "ignores a missing backup")])
caso("CU1", "E1",
     "El navegador manda un nombre vacío, con caracteres de control o larguísimo, o un identificador que no es un UUID.",
     "El servidor limpia el nombre o lo ignora; la persona figura con un nombre genérico («Usuario anónimo») y nunca se le cierra la conexión.",
     "integración",
     [b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_invalid_hello_is_ignored_and_legacy_activity_is_anonymous"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_one_connection_cannot_mint_unlimited_identities"),
      f("services/colaboration/identity.service.spec.ts", "does not persist the fallback name when the prompt is cancelled")])
caso("CU1", "N1",
     "Se va a la dirección /diagram sin código de sala, o a una dirección que no existe.",
     "La aplicación vuelve a la página principal; el editor solo se abre con un código de sala en la dirección.",
     "unidad",
     [f("app/app.routes.spec.ts", "opens the editor only for a room: it takes the code from the address"),
      f("app/app.routes.spec.ts", "sends whoever goes to the editor without a room back to the start page"),
      f("app/app.routes.spec.ts", "sends any unknown address back to the start page")])

caso("CU2", "B",
     "En una sala: se arrastra «Clase UML» al lienzo, se edita con doble clic el nombre, los atributos y los métodos, se une con otra clase arrastrando "
     "desde un círculo de conexión y se editan las multiplicidades y etiquetas.",
     "La clase aparece y crece si el texto es largo; la relación se dibuja con ruteo ortogonal y esquinas redondeadas; cada cambio se guarda en el navegador y, "
     "pasados unos segundos sin editar, en el servidor (sin inundarlo).",
     "sistema",
     [f("services/diagram/diagram.service.spec.ts", "uses Manhattan routing and a rounded connector for every relationship type"),
      f("services/diagram/edition.service.spec.ts", "grows width for a long method and keeps textWrap and position aligned"),
      f("services/diagram/edition.service.spec.ts", "grows width for a long attribute without shrinking an existing class"),
      f("services/diagram/diagram.service.spec.ts", "debounces backend autosave so rapid diagram edits do not flood the backend"),
      f("services/diagram/diagram.service.spec.ts", "does not autosave before the debounce window elapses")],
     manual=["Arrastrar «Clase UML» al lienzo dos veces; renombrarlas con doble clic (seleccionar todo, escribir, Enter).",
             "Hacer clic en una clase y arrastrar desde un círculo hasta la otra: aparece una asociación con multiplicidades 0..1 y 1.",
             "Doble clic sobre la multiplicidad y cambiarla; recargar la página y comprobar que todo sigue ahí."])
caso("CU2", "A1",
     "Se selecciona una clase con relaciones (o una relación) y se elimina.",
     "Se elimina el elemento y sus relaciones; las demás se conservan; solo se elimina la relación del sentido pedido; la entidad intermedia generada se retira con sus patas.",
     "unidad",
     [f("services/diagram/diagram.service.spec.ts", "deletes only the relationship in the requested direction"),
      f("services/diagram/diagram.service.spec.ts", "does not directly broadcast when deleting a selected cell"),
      f("services/diagram/diagram.service.junction.spec.ts", "caso 3: eliminar una relación generada retira también la entidad intermedia y la otra pata")])
caso("CU2", "A2",
     "Se edita una de las dos patas 1:N generadas para que deje de ser «muchos».",
     "El sistema restaura la asociación original muchos-a-muchos antes de retirar la entidad intermedia: no desaparece ninguna relación.",
     "unidad",
     [f("services/diagram/diagram.service.junction.spec.ts", "editar una pata generada restaura la asociación original antes de retirar la junction"),
      f("services/diagram/diagram.service.junction.spec.ts", "caso 4: una relación editada para dejar de ser M:N no genera entidad intermedia")])
caso("CU2", "A3",
     "Se une una clase con una asociación «muchos a muchos» y se la enlaza a una clase asociativa.",
     "La clase asociativa se resuelve como dos relaciones 1:N conservando sus atributos; sin clase asociativa la M:N se transforma sola; el guion SQL no duplica la tabla.",
     "unidad",
     [f("services/diagram/association-class.util.spec.ts", "reemplaza la M:N + clase asociativa por 2 relaciones 1:N, preservando los atributos de la clase"),
      f("services/diagram/diagram.service.junction.spec.ts", "una M:N con clase asociativa ya enlazada permanece directa, sin auto-junction"),
      f("services/diagram/diagram.service.junction.spec.ts", "caso 1: transforma una asociación M:N en una entidad intermedia + 2 relaciones 1:N"),
      f("services/exports/sql-export.service.spec.ts", "no duplica la tabla intermedia cuando la M:N ya llega pre-dividida en 2 relaciones 1:N")])
caso("CU2", "E1",
     "Se dibuja una agregación, composición, dependencia o generalización con «*» en ambos extremos.",
     "No se transforman: no se crea entidad intermedia.",
     "unidad",
     [f("services/diagram/diagram.service.junction.spec.ts", "no transforma agregación, composición ni dependencia aunque ambas multiplicidades sean many"),
      f("services/diagram/diagram.service.junction.spec.ts", 'no transforma una generalización (herencia) aunque tenga labels con "*"')])
caso("CU2", "N1",
     "Se arrastra una relación desde un círculo de conexión y se suelta sobre el lienzo vacío, o llega una relación a la que le falta un extremo.",
     "La relación no queda colgada en el lienzo; si llegara a existir, no se guarda, no se comparte con la sala ni se exporta.",
     "integración",
     [f("services/diagram/diagram.service.spec.ts", "does not let a relationship end on the empty canvas: it must join two classes"),
      f("services/exports/diagram-export.service.spec.ts", "leaves out a relationship that has no class at its target, so it is never saved, shared or exported"),
      f("services/exports/diagram-export.service.spec.ts", "leaves out a relationship that has no class at its origin"),
      f("services/exports/diagram-export.service.spec.ts", "keeps the complete relationships when another one is loose")],
     manual=["Hacer clic en una clase, arrastrar desde un círculo de conexión y soltar sobre una zona vacía del lienzo.",
             "Comprobar que no queda ninguna línea suelta."])

caso("CU5", "B",
     "Todas las personas salieron de la sala; una de ellas vuelve a abrirla con su código desde el mismo navegador.",
     "Se la reconoce por su identificador anónimo; el diagrama vuelve del estado de la sala viva o, si no hay nadie, del último respaldo (sin retransmitirlo); "
     "reaparecen el historial de actividad y la conversación de la sala con la IA.",
     "sistema",
     [f("services/colaboration/collaboration.service.spec.ts", "loads the backup locally, without broadcasting it, when nobody answers"),
      f("services/colaboration/collaboration.service.spec.ts", "requests full state through the room after an empty graph becomes ready"),
      b("uml_api/tests/test_backup_uml_api.py", "BackupUmlApiTests.test_set_backup_persists_and_get_backup_restores_it"),
      b("uml_api/tests/test_backup_uml_api.py", "BackupUmlApiTests.test_set_backup_twice_updates_the_same_room_instead_of_duplicating"),
      b("uml_api/tests/test_activity_api.py", "RoomActivityApiTests.test_history_is_room_scoped_and_oldest_first"),
      b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_history_returns_the_latest_messages_oldest_first"),
      f("app/ia-chat-panel/ia-chat-panel.spec.ts", "loads the conversation of the room when opened and shows it as text"),
      f("services/colaboration/identity.service.spec.ts", "remembers a UUID token and sanitized display name in browser storage")],
     manual=["Con una sala con clases, actividad y una pregunta a la IA, cerrar todas las pestañas.",
             "Volver a abrir la sala con el mismo código desde el mismo navegador.",
             "Comprobar que el diagrama, el panel «Actividad» y el chat con la IA siguen como estaban, sin que pregunte el nombre otra vez."])
caso("CU5", "A1",
     "Se abre una sala de la que no hay ningún respaldo.",
     "El servidor responde 404 al pedir el respaldo y el cliente lo ignora: el lienzo queda vacío.",
     "integración",
     [b("uml_api/tests/test_backup_uml_api.py", "BackupUmlApiTests.test_get_backup_for_unknown_room_returns_404"),
      f("services/colaboration/collaboration.service.spec.ts", "ignores a missing backup")])
caso("CU5", "A2",
     "La persona abre la sala desde otro navegador (otro almacenamiento local).",
     "No hay identificador ni nombre guardados: es una persona nueva y el sistema le pregunta su nombre; con el almacenamiento bloqueado la identidad se mantiene en memoria.",
     "unidad",
     [f("services/colaboration/identity.service.spec.ts", "remembers a UUID token and sanitized display name in browser storage"),
      f("services/colaboration/identity.service.spec.ts", "keeps a stable in-memory identity when storage is unavailable")],
     manual=["Abrir la misma sala en una ventana de incógnito: pregunta «¿Cómo deseas que te vean en la sala?».",
             "Comprobar en «Participantes» que aparece como otra persona."])
caso("CU5", "E1",
     "Llega el respaldo del servidor después de que la sala ya mandó su estado, o después de salir de la sala.",
     "El respaldo atrasado se descarta: no pisa lo que ya envió la sala ni se aplica a otra sala.",
     "unidad",
     [f("services/colaboration/collaboration.service.spec.ts", "ignores a backup that arrives after the room already sent its state"),
      f("services/colaboration/collaboration.service.spec.ts", "drops a backup requested for a room that was already left"),
      f("services/colaboration/collaboration.service.spec.ts", "does not even ask for the backup when the room answered in time")])

# ---- Ciclo 2 -------------------------------------------------------------------------------------------------
caso("CU3", "B",
     "Una persona edita el diagrama (agrega, cambia, mueve o elimina) estando otra conectada a la misma sala.",
     "El cambio viaja como una operación pequeña por el WebSocket; el servidor la retransmite sin alterarla a los demás; cada navegador la aplica y no la reenvía; "
     "cada cierto tiempo se respalda el diagrama en el servidor.",
     "sistema",
     [f("services/colaboration/p2p.websocket-sync.spec.ts", "broadcasts create, update, delete, and move through the signaling WebSocket"),
      f("services/colaboration/p2p.websocket-sync.spec.ts", "delivers remote WebSocket operations to the collaboration handler"),
      f("services/colaboration/p2p.websocket-sync.spec.ts", "ignores WebSocket broadcasts echoed from the current client"),
      f("services/diagram/diagram.service.spec.ts", "never re-broadcasts what arrived from the room"),
      b("collab/tests/test_roles.py", "CanvasRoleTests.test_room_broadcast_payload_reaches_other_client_unchanged"),
      b("collab/tests/test_roles.py", "CanvasRoleTests.test_direct_signaling_payload_remains_unchanged")],
     manual=["Abrir la misma sala en dos ventanas (identidades distintas).",
             "Agregar una clase y una relación en una ventana y renombrar la clase: comprobar que aparecen igual en la otra.",
             "Mover una clase: comprobar que se mueve en la otra."])
caso("CU3", "A1",
     "Una persona entra a una sala en la que ya hay alguien.",
     "Pide el estado completo a la sala; quien está conectado lo envía y el diagrama aparece sin duplicar clases ni relaciones ni retransmitirlas.",
     "integración",
     [f("services/colaboration/collaboration.service.spec.ts", "requests full state through the room after an empty graph becomes ready"),
      f("services/colaboration/collaboration.service.spec.ts", "does not request full state when local room state already exists"),
      f("services/diagram/diagram.service.spec.ts", "loadFromJson remote/full_state load does NOT broadcast add_class or duplicate relationship"),
      f("services/diagram/diagram.service.spec.ts", "B) registered loadFromJson forwards (false, true), and remote full_state does not rebroadcast")])
caso("CU3", "A2",
     "Una persona entra a una sala vacía que ya tuvo trabajo.",
     "Como nadie contesta, carga el último respaldo del servidor solo en su pantalla, sin retransmitirlo.",
     "unidad",
     [f("services/colaboration/collaboration.service.spec.ts", "loads the backup locally, without broadcasting it, when nobody answers"),
      f("services/colaboration/collaboration.service.spec.ts", "does not ask for a backup after leaving before the 3 seconds passed")])
caso("CU3", "A3",
     "Una persona se desconecta y vuelve a conectarse.",
     "Entra como una conexión nueva: el servidor le dice quién es antes que cualquier otra cosa, no queda marcada como expulsada, recupera el diagrama y no recupera su rol anterior.",
     "integración",
     [f("services/colaboration/p2p.roles.spec.ts", "starts every new connection as not expelled"),
      f("services/colaboration/p2p.roles.spec.ts", "takes its own id from the server welcome even when another peer joined first"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_a_new_connection_is_told_its_own_peer_id_before_anything_else"),
      b("collab/tests/test_roles.py", "CanvasRoleTests.test_join_order_assigns_roles_and_empty_room_resets_host")])
caso("CU3", "A4",
     "El Host se desconecta de la sala.",
     "La persona conectada desde hace más tiempo pasa a ser Host y todos los navegadores lo ven; el que se fue, si vuelve, entra como Participante.",
     "integración",
     [b("collab/tests/test_roles.py", "CanvasRoleTests.test_host_disconnect_promotes_longest_connected_participant"),
      f("services/colaboration/p2p.roles.spec.ts", "reflects promotion when a later snapshot makes the local peer host"),
      f("app/participants-panel/participants-panel.spec.ts", "updates the UI when the current participant is promoted")],
     manual=["Con dos ventanas en la sala, pulsar «Salir» en la del Host.",
             "En la otra, comprobar en «Participantes» que ahora figura como Host."])
caso("CU3", "E1",
     "Una persona borra una clase y otra recarga la página.",
     "La clase borrada no reaparece al recargar: el respaldo ya no la tiene, y sus relaciones desaparecen con ella.",
     "sistema",
     [f("services/diagram/diagram.service.spec.ts", "debounces backend autosave so rapid diagram edits do not flood the backend"),
      b("uml_api/tests/test_backup_uml_api.py", "BackupUmlApiTests.test_set_backup_twice_updates_the_same_room_instead_of_duplicating")],
     manual=["Con dos ventanas en la sala y dos clases unidas, borrar una de las clases en la primera.",
             "Esperar unos segundos y recargar la segunda ventana: la clase borrada y su relación no reaparecen."])
caso("CU3", "N1",
     "Dos o más personas editan a la vez y luego se compara su diagrama.",
     "El diagrama de todas las pantallas es el mismo: las operaciones llegan sin cambios, las entidades intermedias generadas se aplican sin duplicarse.",
     "sistema",
     [b("collab/tests/test_roles.py", "CanvasRoleTests.test_room_broadcast_payload_reaches_other_client_unchanged"),
      f("services/colaboration/collaboration.service.spec.ts", "applies generated junction metadata idempotently for remote classes and links"),
      f("services/colaboration/p2p.websocket-sync.spec.ts", "delivers remote WebSocket operations to the collaboration handler")],
     manual=["Con tres ventanas en la sala, editar en cada una (agregar, renombrar, relacionar).",
             "En cada ventana ejecutar exportToJson del diagrama y comparar: las tres salidas son iguales."])
caso("CU4", "B",
     "El Host pulsa «Expulsar» junto a un participante.",
     "El servidor verifica que quien pide es el Host actual, cierra la conexión del expulsado y actualiza la presencia de todos; el expulsado ve «El host te expulsó de la sala» y vuelve al inicio.",
     "integración",
     [b("collab/tests/test_roles.py", "CanvasRoleTests.test_host_can_remove_participant"),
      f("services/colaboration/p2p.roles.spec.ts", "marks the client as removed when the host expels it"),
      f("app/participants-panel/participants-panel.spec.ts", "shows host role, current client, and removal action to the host"),
      f("app/diagram/diagram.spec.ts", "tells an expelled participant and sends them back to the start page")],
     manual=["Con dos ventanas, pulsar «Expulsar» junto al segundo participante desde la ventana del Host.",
             "Comprobar que la segunda ventana muestra «El host te expulsó de la sala» y vuelve a la página principal."])
caso("CU4", "A1",
     "Un participante que no es el Host intenta expulsar a alguien (el botón o un mensaje armado a mano).",
     "El servidor rechaza el pedido y no pasa nada; en pantalla el botón «Expulsar» solo aparece (y solo está activo) para el Host.",
     "integración",
     [b("collab/tests/test_roles.py", "CanvasRoleTests.test_participant_cannot_remove_another_participant"),
      f("services/colaboration/p2p.roles.spec.ts", "only sends removal requests when the local peer is host"),
      f("app/participants-panel/participants-panel.spec.ts", "does not render an enabled removal action for a participant")])
caso("CU4", "A2",
     "La persona expulsada vuelve a entrar a la sala.",
     "Entra como un participante nuevo, sin el rol ni la expulsión anteriores.",
     "integración",
     [f("services/colaboration/p2p.roles.spec.ts", "starts every new connection as not expelled"),
      b("collab/tests/test_roles.py", "CanvasRoleTests.test_join_order_assigns_roles_and_empty_room_resets_host")])
caso("CU4", "E1",
     "La persona expulsada ve el aviso y su copia del diagrama estaba atrasada.",
     "No guarda un respaldo final (su copia podría pisar la de la sala), pero sí cierra su conexión.",
     "unidad",
     [f("services/diagram/diagram.service.spec.ts", "leaves without saving a backup when asked to (an expelled participant), but still closes the socket"),
      f("services/diagram/diagram.service.spec.ts", "does not save a backup on the later automatic leave either once it left without one")])
caso("CU4", "N1",
     "Un Colaborador (no Host) expulsa a alguien.",
     "No es posible: el servidor lo rechaza y la persona sigue en la sala.",
     "integración",
     [b("collab/tests/test_roles.py", "CanvasRoleTests.test_participant_cannot_remove_another_participant"),
      f("app/participants-panel/participants-panel.spec.ts", "does not render an enabled removal action for a participant")])

caso("CU7", "B",
     "Una persona escribe «Agrega una clase Factura con total y fecha» en «Generar modelo» (o en el chat en modo «Pedir cambio», o la dicta).",
     "El servidor comprueba los topes y el turno de la sala, arma el contexto, pide los cambios a la IA y los valida; el navegador de quien pidió los aplica por la ruta de la edición manual marcados "
     "como de la IA; la actividad dice «IA, a pedido de X» y la pregunta y la respuesta quedan en la conversación de la sala.",
     "sistema",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_change_mode_returns_the_changes_for_the_client_to_apply"),
      f("services/IA/ia-actions.service.spec.ts", "applies the changes of change mode marked as IA"),
      f("services/IA/ia-actions.service.spec.ts", "sends the current diagram and announces that the IA is working for the requester"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_operations_applied_by_the_ia_are_logged_on_behalf_of_the_requester"),
      f("app/side-panel/side-panel.spec.ts", "sends the instruction to the AI as a change request for this room and clears the box when it works"),
      f("app/side-panel/side-panel.spec.ts", "dictation only transcribes and then follows the same path as the typed instruction"),
      b("uml_api/tests/test_ai_endpoints.py", "AIEndpointTests.test_transcribe_only_returns_the_text_and_does_not_model_it"),
      b("uml_api/tests/test_ia_chat_api.py", "ShareTurnTests.test_a_request_while_the_ai_is_busy_is_refused_with_who_is_being_served")],
     manual=["Con dos ventanas en la sala, escribir en «Generar modelo» «Agrega una clase Factura con total y fecha» y pulsar «Generar».",
             "Comprobar que en la otra ventana se lee «Pensando (a pedido de X)…» y después aparece la clase Factura.",
             "Comprobar en «Actividad» «IA añadió la clase Factura (a pedido de X)»."])
caso("CU7", "A1",
     "La IA devuelve un cambio que elimina elementos (o devuelve menos miembros de los que la clase tenía).",
     "El sistema cuenta lo que se eliminaría y le pide confirmación a quien pidió; si la rechaza, el diagrama no cambia.",
     "integración",
     [b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_change_mode_reports_how_many_deletions_the_ai_proposes"),
      b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_change_mode_asks_for_confirmation_when_the_model_returns_less_than_there_was"),
      f("services/IA/ia-actions.service.spec.ts", "asks for confirmation before applying a change that deletes things, and applies it if accepted"),
      f("services/IA/ia-actions.service.spec.ts", "leaves the diagram alone and says so when the user refuses a destructive change")])
caso("CU7", "A2",
     "La IA devuelve un cambio enorme o con una forma inválida.",
     "El servidor lo rechaza entero (502 con un mensaje claro) y no guarda nada.",
     "unidad",
     [b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_an_oversized_change_from_the_model_is_rejected_whole"),
      b("uml_api/tests/test_ia_chat_api.py", "ChangeGuardTests.test_validation_rejects_huge_or_non_dict_changes")])
caso("CU7", "A3",
     "Una persona pulsa «Aplicar» en una idea que la IA publicó en una revisión.",
     "El sistema reserva la idea para esa persona, la ejecuta como un pedido de cambio a su nombre y, cuando el cambio llegó al diagrama, la marca como aplicada para todos.",
     "integración",
     [f("services/IA/ia-actions.service.spec.ts", "claims a suggestion before applying it, as a change request on behalf of the clicker"),
      f("services/IA/ia-actions.service.spec.ts", "confirms the suggestion once the change reached the diagram, and not before"),
      b("uml_api/tests/test_ia_chat_api.py", "ClaimSuggestionApiTests.test_the_first_person_claims_it_and_the_room_is_told"),
      b("uml_api/tests/test_ia_chat_api.py", "ClaimSuggestionApiTests.test_confirming_marks_the_idea_as_applied_for_good")])
caso("CU7", "E1",
     "El servicio de IA falla (no responde, devuelve basura o se cae).",
     "Se muestra un mensaje claro («La IA no pudo responder ahora»); el diagrama no cambia, no se guarda nada a medias, se devuelve el turno y la sala vuelve a «Disponible».",
     "integración",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_change_mode_failure_returns_502_and_stores_nothing"),
      b("uml_api/tests/test_ia_chat_api.py", "ShareTurnTests.test_the_turn_is_given_back_when_the_provider_fails"),
      f("services/IA/ia-actions.service.spec.ts", "reports the request as finished when it fails or is abandoned"),
      f("app/side-panel/side-panel.spec.ts", "keeps the text and tells the user when the AI fails"),
      f("app/ia-chat-panel/ia-chat-panel.spec.ts", "shows a clear message when the AI fails and keeps the chat usable")])
caso("CU7", "N1",
     "Se pregunta o se pide revisar en el chat, aunque el proveedor devuelva un diagrama nuevo.",
     "El diagrama no cambia: solo el modo «Pedir cambio» devuelve cambios, y los aplica el navegador de quien lo pidió.",
     "integración",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_ask_and_review_never_return_changes_to_apply"),
      f("services/IA/ia-actions.service.spec.ts", "never touches the diagram in ask or review mode, even if the server returned one"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_only_a_literal_true_marks_an_operation_as_ia")])
caso("CU8", "B",
     "Se elige «Importar Imagen» y se sube la foto de un diagrama de clases.",
     "El servidor manda la imagen a la IA con visión y devuelve clases, atributos, métodos y relaciones; si la sala está vacía se aplican directo, si no se muestra el diálogo para reemplazar o combinar, y el modelo se propaga a la sala.",
     "integración",
     [f("app/side-panel/side-panel.spec.ts", "imports immediately without a dialog when the diagram is empty"),
      f("app/side-panel/side-panel.spec.ts", "opens the dialog without applying a valid result to a non-empty diagram"),
      f("app/side-panel/side-panel.spec.ts", "replaces the existing diagram and clears the pending result"),
      f("app/side-panel/side-panel.spec.ts", "merges into the existing diagram and clears the pending result"),
      f("services/diagram/diagram.service.spec.ts", "replaces image UML through per-cell removal before loading the generated result"),
      b("uml_api/tests/test_services_gemini.py", "MapEdgesToRelationshipsTests.test_aggregation_with_diamond_in_head_reverses_direction"),
      b("uml_api/tests/test_services_gemini.py", "EdgeRelationshipTypeTests.test_black_diamond_in_tail_is_composition")],
     manual=["En «Importaciones» → «Importar Imagen» elegir la captura de un diagrama de clases.",
             "Con el lienzo con elementos, elegir «Reemplazar diagrama» y comprobar que el diagrama de la imagen aparece también en la otra ventana."])
caso("CU8", "A1",
     "Con el diálogo abierto, se pulsa «Cancelar» o la tecla Escape.",
     "No cambia nada en el diagrama y se descarta el resultado pendiente.",
     "unidad",
     [f("app/side-panel/side-panel.spec.ts", "cancels without changing the graph and clears the pending result"),
      f("app/side-panel/side-panel.spec.ts", "cancels the pending import on Escape")])
caso("CU8", "E1",
     "La imagen no es legible o el servicio de IA falla.",
     "El sistema muestra un error claro (sin datos internos) y el diagrama no cambia.",
     "integración",
     [b("uml_api/tests/test_ai_endpoints.py", "AIEndpointTests.test_image_service_error_is_sanitized_502"),
      f("app/side-panel/side-panel.spec.ts", "preserves the existing invalid-response handling"),
      f("app/side-panel/side-panel.spec.ts", "preserves the existing provider-error handling")])

# ---- Ciclo 3 -------------------------------------------------------------------------------------------------
caso("CU10", "B",
     "Se pulsa «Exportar XMI» con un diagrama con clases, atributos, métodos y relaciones.",
     "El servidor genera un archivo XMI 2.1 determinista con posición y tamaño de cada clase, tipos primitivos de UML y las relaciones con sus multiplicidades; el navegador lo descarga y Enterprise Architect lo abre.",
     "integración",
     [b("uml_api/tests/test_xmi_api.py", "XmiApiTests.test_export_endpoint_returns_xmi_file"),
      b("uml_api/tests/test_xmi_service.py", "XmiExportTests.test_exports_association_and_multiplicities"),
      b("uml_api/tests/test_xmi_service.py", "XmiExportTests.test_export_is_deterministic_and_generated_ids_are_unique"),
      b("uml_api/tests/test_xmi_layout.py", "XMILayoutTests.test_round_trip_preserves_class_position_and_size"),
      b("uml_api/tests/test_xmi_enterprise_architect.py", "EnterpriseArchitectXMITests.test_export_uses_uml_primitive_type_hrefs"),
      f("services/interop/xmi.service.spec.ts", "omits association-class connectors while preserving supported relationships")],
     manual=["Exportar el XMI de un diagrama con clases y relaciones y abrirlo en Enterprise Architect 17.2: clases, atributos, relaciones y multiplicidades intactos (prueba del primer parcial, ver nota)."])
caso("CU10", "A1",
     "Se elige «Importar XMI» y se sube un archivo exportado por Enterprise Architect.",
     "El servidor lo valida y lo convierte en un diagrama con sus clases, atributos, relaciones y multiplicidades (con o sin prefijo de espacio de nombres); el viaje ida y vuelta conserva el modelo.",
     "integración",
     [b("uml_api/tests/test_xmi_api.py", "XmiApiTests.test_import_endpoint_returns_internal_uml_json"),
      b("uml_api/tests/test_xmi_service.py", "XmiImportTests.test_json_xmi_json_round_trip"),
      b("uml_api/tests/test_xmi_service.py", "EnterpriseArchitectStyleImportTests.test_imports_external_xmi_supported_subset"),
      b("uml_api/tests/test_xmi_service.py", "EnterpriseArchitectStyleImportTests.test_importer_does_not_depend_on_namespace_prefix"),
      b("uml_api/tests/test_xmi_enterprise_architect.py", "EnterpriseArchitectXMITests.test_imports_ea_association_type_references_and_multiplicity")])
caso("CU10", "A2",
     "Se elige «Exportar como Imagen».",
     "Se genera un PNG con fondo claro, el diagrama completo y sin los elementos de la aplicación.",
     "sistema",
     [f("services/diagram/diagram.service.spec.ts", "fills the export canvas before drawing the diagram image")],
     manual=["Pulsar «Exportaciones» → «Exportar como Imagen» con un diagrama con varias clases.",
             "Abrir el PNG descargado: fondo claro, diagrama completo y sin la paleta ni los paneles."])
caso("CU10", "E1",
     "Se importa un archivo que no es XML, está mal formado o no se manda archivo.",
     "El servidor responde con un error claro y el diagrama actual no cambia; un modelo inválido tampoco se exporta.",
     "integración",
     [b("uml_api/tests/test_xmi_api.py", "XmiApiTests.test_import_endpoint_rejects_malformed_xmi"),
      b("uml_api/tests/test_xmi_api.py", "XmiApiTests.test_import_endpoint_requires_file"),
      b("uml_api/tests/test_xmi_api.py", "XmiApiTests.test_export_endpoint_rejects_invalid_model"),
      b("uml_api/tests/test_xmi_service.py", "XmiImportTests.test_rejects_malformed_xml")])
caso("CU10", "N1",
     "Se importa un XMI con una declaración DOCTYPE o una entidad externa.",
     "Se rechaza sin leer archivos ni abrir conexiones.",
     "unidad",
     [b("uml_api/tests/test_xmi_service.py", "XmiImportTests.test_rejects_doctype_and_entities")])
caso("CU11", "B",
     "Se pulsa «Exportar a Backend» con un diagrama con clases.",
     "El navegador manda el diagrama al generador en el puerto 7001 del mismo host; el generador crea el proyecto Spring Boot con PostgreSQL y la colección de Postman, que compila con el Maven Wrapper, y se descarga el .zip.",
     "integración",
     [j("service/ProjectGeneratorCompileTest.java", "generatedProjectCompilesAndPostmanCollectionMatches"),
      j("service/ProjectGeneratorCompileTest.java", "generatedProjectWithMissingPkAndStringPkCompiles"),
      f("services/exports/backend-generator.service.spec.ts", "builds the Spring generator URL from the current window.location and fixed port 7001"),
      f("services/exports/backend-generator.service.spec.ts", "does not show any error when the generator answers")],
     manual=["Con un diagrama con clases, pulsar «Exportaciones» → «Exportar a Backend» y descargar el .zip.",
             "Descomprimirlo y ejecutar ./mvnw -q -DskipTests package: debe compilar."])
caso("CU11", "A1",
     "Se pulsa «Exportar como SQL».",
     "El sistema genera el guion de creación de las tablas, con la tabla intermedia una sola vez aunque la M:N llegue cruda o ya dividida.",
     "unidad",
     [f("services/exports/sql-export.service.spec.ts", "no duplica la tabla intermedia cuando la M:N ya llega pre-dividida en 2 relaciones 1:N"),
      f("services/exports/sql-export.service.spec.ts", "sigue generando la tabla intermedia por su propia detección M:N cuando la relación llega cruda")])
caso("CU11", "E1",
     "El generador no responde o falla.",
     "El sistema avisa «No se pudo generar el backend…», no descarga nada y detiene el indicador de espera.",
     "unidad",
     [f("services/exports/backend-generator.service.spec.ts", "tells the person when the generator does not answer, downloads nothing and stops the spinner")])
caso("CU12", "B",
     "Se pulsa «Exportar Flutter» con un diagrama con clases.",
     "Se descarga un .zip con los modelos, la base SQLite local (sqflite), las pantallas CRUD y el asistente de comandos; es determinista, sin duplicar la tabla intermedia, y los booleanos se normalizan.",
     "integración",
     [b("uml_api/tests/test_flutter_generator.py", "FlutterGeneratorApiTests.test_valid_uml_returns_generated_zip"),
      b("uml_api/tests/test_flutter_generator.py", "FlutterGeneratorApiTests.test_database_helper_generated"),
      b("uml_api/tests/test_flutter_generator.py", "FlutterGeneratorApiTests.test_pubspec_contains_sqflite"),
      b("uml_api/tests/test_flutter_generator.py", "FlutterGeneratorApiTests.test_database_schema"),
      b("uml_api/tests/test_flutter_generator.py", "FlutterGeneratorApiTests.test_local_db_fallback_in_service"),
      b("uml_api/tests/test_flutter_generator.py", "FlutterGeneratorApiTests.test_pre_split_many_to_many_does_not_duplicate_intermediate_table"),
      b("uml_api/tests/test_flutter_generator.py", "FlutterGeneratorTests.test_representative_project_is_unique_complete_and_deterministic"),
      b("uml_api/tests/test_flutter_generator.py", "AssistantSchemaGeneratorTests.test_main_exposes_assistant_entry_point")],
     manual=["Generar el proyecto Flutter, abrirlo y ejecutarlo sin red: el CRUD funciona y los datos persisten (prueba física del primer parcial, ver nota)."])
caso("CU12", "E1",
     "Se pide generar la aplicación con un diagrama sin clases.",
     "El servidor responde con un error de cliente y el navegador muestra «No se pudo generar la aplicación móvil…» sin descargar nada.",
     "integración",
     [b("uml_api/tests/test_flutter_generator.py", "FlutterGeneratorApiTests.test_empty_classes_returns_client_error"),
      f("services/exports/frontend-generator.service.spec.ts", "tells the person when the diagram cannot be generated, and stops the spinner")])

# ---- Ciclo 4 -------------------------------------------------------------------------------------------------
caso("CU6", "B",
     "Una persona abre el panel «Actividad» de una sala en la que otras ya hicieron cambios; luego una de ellas agrega una clase.",
     "El servidor entrega el historial reciente de la sala (solo la suya), la pantalla lo muestra del más nuevo al más viejo con autor, tipo y resumen, y el evento nuevo llega en vivo a todas las pantallas arriba de la lista sin duplicarse.",
     "integración",
     [b("uml_api/tests/test_activity_api.py", "RoomActivityApiTests.test_history_is_room_scoped_and_oldest_first"),
      b("uml_api/tests/test_activity_api.py", "RoomActivityApiTests.test_since_returns_only_newer_event_ids"),
      b("collab/tests/test_activity_store.py", "ActivityStoreContract.test_recent_returns_the_latest_events_of_the_room_oldest_first"),
      f("app/activity-panel/activity-panel.spec.ts", "loads history and renders it newest first"),
      f("app/activity-panel/activity-panel.spec.ts", "merges live events with history and deduplicates by event id"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_named_activity_reaches_all_three_clients")],
     manual=["Con dos ventanas, agregar una clase en una: en la otra aparece «<nombre> añadió una clase…» en «Actividad».",
             "Recargar: el historial vuelve."])
caso("CU6", "A1",
     "Una persona mueve o cambia el tamaño de una clase.",
     "No se registra: solo agregar, eliminar, relacionar y editar texto generan eventos.",
     "integración",
     [b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_only_meaningful_operations_create_activity")])
caso("CU6", "A2",
     "Una persona edita varias veces el mismo texto en pocos segundos.",
     "Se registra como un solo evento (la edición repetida se fusiona).",
     "integración",
     [b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_repeated_edit_for_same_target_and_field_is_coalesced"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_activity_flood_is_capped_but_relay_keeps_working")])
caso("CU6", "E1",
     "Falla el guardado de la actividad (la base de datos no responde).",
     "La edición del diagrama sigue funcionando y se retransmite a la sala.",
     "integración",
     [b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_activity_persistence_failure_does_not_break_relay")])
caso("CU9", "B",
     "Una persona abre el chat con la IA de la sala, elige «Preguntar» (o «Revisar») y escribe su mensaje.",
     "El servidor comprueba los topes y el turno, arma el contexto con el diagrama, la actividad de todos y la conversación de la sala, pide la respuesta a la IA, guarda la pregunta y la respuesta con su autor "
     "y todas las personas de la sala las ven; en «Revisar» publica además una revisión con hasta cinco ideas con su botón «Aplicar».",
     "sistema",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_ask_answers_and_stores_both_messages"),
      b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_prompt_includes_the_activity_of_every_participant"),
      b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_prompt_includes_a_summary_of_the_current_diagram"),
      b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_the_conversation_belongs_to_the_whole_room"),
      b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_the_prompt_carries_the_conversation_of_the_room_with_who_said_what"),
      b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_review_returns_suggestions_and_publishes_an_event_for_the_room"),
      b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_review_keeps_at_most_five_suggestions_and_skips_empty_ones"),
      f("app/ia-chat-panel/ia-chat-panel.spec.ts", "sends the question with the current diagram and shows the reply"),
      f("app/ia-chat-panel/ia-chat-panel.spec.ts", "shows who wrote each message and tells mine from the others")],
     manual=["Con dos ventanas, abrir «Chat con la IA» en cada una; preguntar «¿Qué hizo <nombre>?» en la primera.",
             "Comprobar que la pregunta y la respuesta aparecen en las dos ventanas, cada mensaje con su autor.",
             "En modo «Revisar», comprobar que la revisión aparece en «Actividad» de las dos con botones «Aplicar»."])
caso("CU9", "A1",
     "Una persona pulsa «Aplicar» en una idea de la revisión.",
     "El sistema reserva la idea para esa persona, la ejecuta como un pedido de cambio a su nombre y la marca como aplicada para todos, también tras recargar.",
     "integración",
     [b("uml_api/tests/test_ia_chat_api.py", "ClaimSuggestionApiTests.test_the_first_person_claims_it_and_the_room_is_told"),
      b("uml_api/tests/test_ia_chat_api.py", "ClaimSuggestionApiTests.test_confirming_marks_the_idea_as_applied_for_good"),
      f("app/activity-panel/activity-panel.spec.ts", "applies a suggestion through the IA on behalf of whoever clicks it"),
      f("app/activity-panel/activity-panel.spec.ts", "shows an idea as applied, for everyone, once the server says someone took it"),
      f("app/activity-panel/activity-panel.spec.ts", "survives a reload: the applied state comes with the event, not from memory")])
caso("CU9", "A2",
     "Otra persona ya tomó la idea (o la reserva venció sin confirmarse).",
     "El sistema avisa y no la repite: responde 409 al segundo; una reserva que nadie confirma vence a los 150 segundos y la idea queda libre.",
     "integración",
     [b("uml_api/tests/test_ia_chat_api.py", "ClaimSuggestionApiTests.test_a_second_claim_of_the_same_idea_is_refused"),
      b("uml_api/tests/test_ia_chat_api.py", "ClaimSuggestionApiTests.test_an_expired_reservation_can_be_taken_by_someone_else"),
      b("uml_api/tests/test_ia_chat_api.py", "ClaimSuggestionApiTests.test_a_reservation_that_has_not_expired_still_blocks_others"),
      f("app/activity-panel/activity-panel.spec.ts", "shows who is applying an idea right now and blocks it for everybody else"),
      f("app/activity-panel/activity-panel.spec.ts", "lets the idea be applied again once an unconfirmed reservation expired"),
      f("app/activity-panel/activity-panel.spec.ts", "tells the user when somebody else took the idea first")])
caso("CU9", "A3",
     "Cambia el diagrama y el sistema analiza su consistencia (relaciones del modelo).",
     "El análisis no bloquea el servidor, se agrupa en una sola llamada por ráfaga, respeta los topes por conexión y por minuto, y un fallo de la IA no cierra la conexión.",
     "integración",
     [b("collab/tests/test_uml_validation.py", "UmlValidationDoesNotBlockTheServerTests.test_a_slow_ai_call_does_not_block_the_event_loop"),
      b("collab/tests/test_uml_validation.py", "UmlValidationDoesNotBlockTheServerTests.test_a_burst_of_requests_costs_a_single_ai_call"),
      b("collab/tests/test_uml_validation.py", "UmlValidationDoesNotBlockTheServerTests.test_a_failing_ai_call_is_reported_without_closing_the_socket"),
      b("collab/tests/test_uml_validation.py", "UmlValidationLimitsTests.test_validations_per_minute_are_limited_across_connections")])
caso("CU9", "E1",
     "El servicio de IA falla al responder una pregunta o una revisión.",
     "El sistema muestra «La IA no pudo responder ahora» y no guarda nada: ni la conversación ni un evento a medias.",
     "integración",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_provider_failure_returns_502_and_stores_nothing"),
      b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_a_failure_while_publishing_a_review_leaves_nothing_half_saved"),
      b("uml_api/tests/test_ia_chat_api.py", "GeminiProviderTests.test_errors_never_leak_the_api_key"),
      f("app/ia-chat-panel/ia-chat-panel.spec.ts", "shows a clear message when the AI fails and keeps the chat usable")])
caso("CU9", "E2",
     "Se superan los topes de pedidos (12 por minuto por persona, 30 por sala, 60 en total) o la IA está atendiendo a otra persona.",
     "El servidor responde 429 («Demasiadas preguntas seguidas») o 409 con el nombre de quien la tiene; el pedido rechazado no gasta cupo y el turno se devuelve siempre.",
     "integración",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_too_many_requests_in_a_minute_are_throttled"),
      b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_the_whole_room_shares_a_request_budget"),
      b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_the_whole_service_shares_a_request_budget_across_rooms"),
      b("uml_api/tests/test_ia_chat_api.py", "ShareTurnTests.test_a_refused_request_does_not_spend_the_budget"),
      f("app/ia-chat-panel/ia-chat-panel.spec.ts", "explains when the participant is not identified or is throttled"),
      f("app/ia-chat-panel/ia-chat-panel.spec.ts", "tells who is being served when the AI is busy with another person")])
caso("CU9", "E3",
     "La respuesta de una revisión no tiene el formato esperado (texto plano, o JSON dentro de un bloque Markdown).",
     "Con bloque Markdown se interpreta igual; con texto plano se muestra como texto y sin botones «Aplicar»; las ideas mal formadas se ignoran.",
     "unidad",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_review_accepts_an_answer_wrapped_in_a_markdown_fence"),
      b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_review_with_a_plain_text_answer_has_no_suggestions"),
      f("app/activity-panel/activity-panel.spec.ts", "ignores malformed findings instead of failing")])
caso("CU9", "N1",
     "Se pide una revisión y nadie pulsa «Aplicar».",
     "El diagrama no cambia: una revisión solo publica ideas; cambiar el diagrama exige que una persona pulse «Aplicar».",
     "integración",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_ask_and_review_never_return_changes_to_apply"),
      f("services/IA/ia-actions.service.spec.ts", "never touches the diagram in ask or review mode, even if the server returned one"),
      f("app/activity-panel/activity-panel.spec.ts", "lists the review findings as plain text and only offers Apply when there is something to apply")])
caso("CU13", "B",
     "Se abre en el celular el enlace /sala/<código>/seguir (con «Copiar enlace para seguir desde el celular»).",
     "El servidor lo conecta como observador (no cuenta como participante ni como Host), le entrega el estado y la actividad; el celular muestra el diagrama actualizándose y debajo la actividad; "
     "con los avisos autorizados, el navegador notifica cada evento nuevo una sola vez.",
     "sistema",
     [f("services/colaboration/signaling.service.spec.ts", "opens a read-only connection for viewers, without introducing itself"),
      b("collab/tests/test_viewer.py", "ViewerModeTests.test_a_viewer_never_becomes_host_even_if_it_connects_first"),
      b("collab/tests/test_viewer.py", "ViewerModeTests.test_viewers_receive_operations_and_activity_but_no_presence"),
      f("app/follow-view/follow-view.spec.ts", "opens the room as a read-only viewer"),
      f("app/follow-view/follow-view.spec.ts", "notifies a new change from another person once the permission is granted"),
      f("app/follow-view/follow-view.spec.ts", "does not repeat a notification when the list changes but the event is the same"),
      f("app/follow-view/follow-view.spec.ts", "announces an AI review as an idea with how many ideas it has"),
      f("services/colaboration/notification.service.spec.ts", "notifies a change with the author as title and the summary as body")],
     manual=["En la ventana del editor pulsar «Copiar enlace para seguir desde el celular» y abrirlo en una ventana del tamaño de un celular (o en el celular).",
             "Comprobar que muestra el diagrama y la actividad, que no figura en «Participantes» y que el editor sigue siendo Host.",
             "Editar en el editor: el celular se actualiza solo."])
caso("CU13", "A1",
     "La persona no autoriza los avisos (o el navegador los bloqueó o no los ofrece).",
     "No se crea ninguna notificación: solo ve la pantalla; si están bloqueados lo dice y si no hay soporte no muestra nada.",
     "unidad",
     [f("app/follow-view/follow-view.spec.ts", "does not notify anything without the permission"),
      f("app/follow-view/follow-view.spec.ts", "says the notifications are blocked when the browser refuses them"),
      f("app/follow-view/follow-view.spec.ts", "shows nothing about notifications where the browser cannot show them"),
      f("services/colaboration/notification.service.spec.ts", "never creates a notification without a granted permission")])
caso("CU13", "A2",
     "Se abre la vista del celular y nadie conectado entrega el estado.",
     "El observador solo pide el estado al Host, con un tope por intervalo (muchos observadores cuestan una sola petición), y si nadie contesta carga el diagrama del último respaldo.",
     "integración",
     [b("collab/tests/test_viewer.py", "ViewerModeTests.test_only_the_host_is_asked_for_the_full_state"),
      b("collab/tests/test_viewer.py", "ViewerModeTests.test_many_viewers_together_cost_one_state_request_per_interval"),
      b("collab/tests/test_viewer.py", "ViewerModeTests.test_a_viewer_cannot_flood_the_room_with_full_state_requests"),
      f("services/colaboration/collaboration.service.spec.ts", "loads the backup locally, without broadcasting it, when nobody answers")])
caso("CU13", "E1",
     "Ya hay diez seguidores en la sala y entra uno más.",
     "El servidor rechaza al undécimo; los editores no tienen ese límite.",
     "integración",
     [b("collab/tests/test_viewer.py", "ViewerModeTests.test_a_room_accepts_a_limited_number_of_viewers"),
      b("collab/tests/test_viewer.py", "ViewerModeTests.test_the_viewer_limit_does_not_apply_to_editors")])
caso("CU13", "N1",
     "Desde la vista del celular se intenta editar el diagrama (tocar el lienzo o mandar operaciones al servidor).",
     "No es posible: el lienzo no recibe toques, no hay controles de edición, el cliente no envía operaciones y el servidor las ignora; la vista tampoco guarda nada.",
     "integración",
     [b("collab/tests/test_viewer.py", "ViewerModeTests.test_viewers_cannot_send_operations_or_other_messages"),
      b("collab/tests/test_viewer.py", "ViewerModeTests.test_a_viewer_can_only_ask_the_room_for_the_full_state"),
      f("services/colaboration/collaboration.service.spec.ts", "never sends operations as a viewer, except asking for the full state"),
      f("app/follow-view/follow-view.spec.ts", "offers no editing controls and keeps the canvas from receiving touches"),
      f("services/diagram/diagram.service.spec.ts", "never saves locally or to the server, even after changes")])
caso("CU14", "B",
     "Una persona abre «Ayuda» (en la página principal o en la sala), escribe «¿Cómo invito a un compañero?» y envía.",
     "El servidor comprueba el tope de uso, arma el contexto con el manual de la herramienta y los últimos mensajes de la conversación, pide la respuesta a la IA y el navegador la muestra paso a paso; la conversación es personal.",
     "sistema",
     [b("uml_api/tests/test_ia_help_api.py", "HelpAnswerTests.test_it_answers_without_any_room"),
      b("uml_api/tests/test_ia_help_api.py", "HelpAnswerTests.test_the_prompt_carries_the_manual_and_the_question"),
      b("uml_api/tests/test_ia_help_api.py", "HelpAnswerTests.test_the_previous_messages_of_the_conversation_reach_the_prompt"),
      b("uml_api/tests/test_ia_help_api.py", "HelpKnowledgeTests.test_the_manual_mentions_every_function_of_the_menu"),
      f("services/IA/help.service.spec.ts", "asks the help endpoint with the question and gives back only the reply"),
      f("app/help-panel/help-panel.spec.ts", "shows the question and the answer, with who said each"),
      f("app/help-panel/help-panel.spec.ts", "sends the earlier messages with the next question so the assistant keeps the thread"),
      f("app/landin-page/landin-page.spec.ts", "offers the help assistant before entering any room")],
     manual=["En la página principal pulsar «Ayuda» y preguntar «¿Cómo invito a un compañero a mi sala y cómo la sigo desde el celular?».",
             "Comprobar que la respuesta describe «Copiar código de sala» y «Copiar enlace para seguir desde el celular» (prueba con Gemini real el 2026-10-26)."])
caso("CU14", "A1",
     "Se pregunta algo que no trata de la herramienta (por ejemplo, «¿Quién ganó el mundial de 2018?»).",
     "El asistente responde «Solo puedo ayudarte con el uso de esta herramienta.»: las instrucciones del asistente lo limitan al manual y los textos de la persona se tratan como datos, no como instrucciones.",
     "sistema",
     [b("uml_api/tests/test_ia_help_api.py", "HelpPromptTests.test_the_prompt_limits_the_assistant_to_the_tool_and_gives_the_refusal_sentence"),
      b("uml_api/tests/test_ia_help_api.py", "HelpPromptTests.test_text_inside_the_data_sections_is_not_an_instruction")],
     manual=["En «Ayuda» preguntar «¿Quién ganó el mundial de fútbol de 2018?»: responde «Solo puedo ayudarte con el uso de esta herramienta.» (verificado con Gemini real el 2026-10-26)."])
caso("CU14", "E1",
     "El servicio de IA falla, o la persona se pasa del tope (6 preguntas por minuto, 30 en total), o escribe más de 2000 caracteres.",
     "Se muestra un mensaje claro («La IA no pudo responder ahora», «Demasiadas preguntas seguidas» o el límite de caracteres); la pregunta queda en la conversación y se puede volver a intentar; nada interno se filtra.",
     "integración",
     [b("uml_api/tests/test_ia_help_api.py", "HelpProviderFailureTests.test_a_provider_failure_shows_a_clear_message"),
      b("uml_api/tests/test_ia_help_api.py", "HelpProviderFailureTests.test_an_unexpected_failure_is_not_leaked"),
      b("uml_api/tests/test_ia_help_api.py", "HelpLimitTests.test_the_seventh_question_in_a_minute_gets_429"),
      b("uml_api/tests/test_ia_help_api.py", "HelpLimitTests.test_the_whole_service_shares_a_budget_even_if_each_person_stays_under_theirs"),
      b("uml_api/tests/test_ia_help_api.py", "HelpValidationTests.test_a_question_that_is_too_long_is_refused"),
      b("uml_api/tests/test_ia_help_api.py", "HelpCorsTests.test_the_browser_may_send_the_help_token_header_from_the_frontend_origin"),
      f("app/help-panel/help-panel.spec.ts", "shows a clear message when the AI cannot answer and keeps what the person wrote visible"),
      f("app/help-panel/help-panel.spec.ts", "explains the wait when the person asked too many questions")])


# ---- ejecución de los procedimientos manuales ------------------------------------------------------------------
# Cada procedimiento manual de un caso se ejecutó (o no) en la fecha indicada. Resultado: «pasó», «pasó con observación» o «no ejecutado».
# Entorno de las ejecuciones del 2026-10-26: aplicación local (Angular 20 en el puerto 4200, Django con Daphne en el 8000, PostgreSQL, Redis y, cuando
# hizo falta, el generador Spring en el 7001) y el navegador integrado de la herramienta de desarrollo. Como las pestañas de un mismo navegador comparten
# el almacenamiento local, cada «persona» se creó fijando su nombre y su identificador antes de abrir su pestaña; la IA fue Google Gemini real.
FECHA_EJECUCION = "2026-10-26"
EJECUCIONES = {
    ("CU1", "B"): ("pasó", "Se creó la sala desde la portada; el navegador preguntó «¿Cómo deseas que te vean en la sala?» y guardó el nombre; una segunda persona entró con "
                           "el código en mayúsculas y con espacios y quedó como Participante; Ana figuró como Host y solo ella vio «Expulsar»."),
    ("CU2", "B"): ("pasó con observación", "Se arrastraron dos clases, se renombró una y se unieron con una asociación 0..1 y 1. Observación: al renombrar, el atajo Cmd+A "
                                           "no seleccionó el texto del cuadro en este navegador y el nombre nuevo se agregó al final («EntidadCliente»); es la advertencia "
                                           "que ya trae el manual (seleccionar todo antes de escribir)."),
    ("CU2", "N1"): ("pasó", "Se soltó una relación sobre el lienzo vacío: no quedó ninguna relación y la otra pantalla no recibió ningún evento. Esta prueba encontró el "
                            "defecto D-03 (la versión anterior registraba «eliminó un elemento» en la actividad de todos)."),
    ("CU5", "B"): ("pasó", "Se cerró la última pestaña, se comprobó que el servidor tenía el respaldo (2 clases) y se volvió a entrar con el código: reaparecieron el diagrama "
                           "(sin la clase eliminada), 34 líneas de actividad y los 8 mensajes de la conversación con la IA, sin que preguntara el nombre."),
    ("CU5", "A2"): ("pasó", "Un navegador sin almacenamiento local pregunta el nombre y entra como otra persona (visto al crear la sala en CU1)."),
    ("CU3", "B"): ("pasó", "Con dos personas en la sala, la clase, su nombre y la relación creados por una aparecieron en la otra pantalla y en «Actividad»."),
    ("CU3", "A4"): ("pasó", "Cuando Ana salió, Beto pasó a ser Host; al volver, Ana entró como Participante."),
    ("CU3", "E1"): ("pasó", "Se eliminó una clase; tras unos segundos el respaldo del servidor ya no la tenía y al recargar la otra pantalla no reapareció."),
    ("CU3", "N1"): ("pasó", "Después de editar a mano y con la IA, el diagrama exportado de las dos pantallas dio el mismo resumen (mismas clases, atributos, posiciones y relaciones)."),
    ("CU4", "B"): ("pasó", "El Host pulsó «Expulsar»; la otra persona vio «El host te expulsó de la sala.», volvió a la portada y el Host quedó solo en «Participantes». "
                           "Esta prueba encontró el defecto D-05 (ver CU4 A2)."),
    ("CU7", "B"): ("pasó", "Con Gemini real: «Agrega una clase Factura con total y fecha» desde «Generar modelo». La otra pantalla leyó «Pensando (a pedido de Beto)…», apareció "
                           "la clase Factura con id, total y fecha, la actividad dijo «IA añadió la clase Factura (a pedido de Beto)» y la conversación guardó el pedido."),
    ("CU8", "B"): ("pasó", "Con Gemini real y una imagen de dos clases (Libro y Autor): como el diagrama ya tenía elementos apareció el diálogo; con «Combinar con actual» se "
                           "agregaron Libro, Autor y su relación 1..* a 1, también en la vista del celular."),
    ("CU10", "B"): ("pasó con observación", "Desde la aplicación se exportó el XMI (con las clases y su tipo uml:Class) y se volvió a importar: el diagrama quedó idéntico. No se repitió la "
                                            "prueba con Enterprise Architect 17.2, que es del primer parcial."),
    ("CU10", "A2"): ("pasó", "El PNG exportado tiene fondo claro (RGB 248, 249, 250) y solo el diagrama."),
    ("CU11", "B"): ("pasó con observación", "Con el generador Spring en el puerto 7001, «Exportar a Backend» descargó un .zip de 17 KB. La compilación del proyecto generado la hace la "
                                            "prueba automática ProjectGeneratorCompileTest (no se repitió a mano)."),
    ("CU12", "B"): ("pasó con observación", "«Exportar Flutter» descargó un .zip de 53 KB. No se repitió la ejecución de la aplicación sin red en un dispositivo (prueba del primer parcial)."),
    ("CU6", "B"): ("pasó", "Cada clase, renombre y relación hechos por una persona aparecieron al instante en «Actividad» de las demás, y al reabrir la sala el historial volvió."),
    ("CU9", "B"): ("pasó", "Con Gemini real: Ana preguntó qué clases había y qué había hecho; la IA contestó con el diagrama y la actividad y Beto vio la misma conversación con el autor de "
                           "cada mensaje. En modo «Revisar» publicó 3 ideas con su botón «Aplicar» en las dos pantallas; Beto aplicó la primera (la clase Factura no tenía "
                           "identificador): mientras tanto la otra pantalla leyó «Aplicando (Beto)…», después la idea quedó «Aplicada» y la clase ganó id: int."),
    ("CU13", "B"): ("pasó con observación", "La vista de seguimiento mostró el diagrama y la actividad, no tenía ningún botón ni cuadro de texto, no figuró en «Participantes» ni quitó el "
                                            "rol de Host, y recibió en vivo una clase nueva. El panel del navegador tiene los avisos bloqueados, así que no se pudo ver una notificación "
                                            "real (la lógica está cubierta por pruebas automáticas); falta probarlo en un celular."),
    ("CU14", "B"): ("pasó", "Con Gemini real, «¿Cómo invito a un compañero a mi sala y cómo la sigo desde el celular?» se respondió con los pasos de «Copiar código de sala» y "
                            "«Copiar enlace para seguir desde el celular»."),
    ("CU14", "A1"): ("pasó", "Con Gemini real, «¿Quién ganó el mundial de fútbol de 2018?» se respondió con «Solo puedo ayudarte con el uso de esta herramienta.»"),
}
# Caminos con prueba manual que el mismo día se comprobaron sin el procedimiento escrito (otra forma, mismo resultado esperado)
EJECUCIONES_ADICIONALES = {
    ("CU1", "A1"): "«mi-sala» en «Unirse al Lienzo»: apareció «El código no es válido…» y no se entró.",
    ("CU4", "A2"): "Tras ser expulsada, la persona volvió a entrar con el código sin recargar la página y se quedó en la sala como Participante nueva (antes de la corrección volvía a ser expulsada).",
    ("CU11", "E1"): "Con el generador Spring apagado, «Exportar a Backend» mostró «No se pudo generar el backend…» y no descargó nada.",
    ("CU10", "E1"): "Un XMI mal formado mostró «No se pudo importar el archivo XMI.» y dejó el diagrama igual.",
    ("CU10", "N1"): "Un XMI con una entidad externa se rechazó con el mismo aviso y el diagrama no cambió.",
    ("CU9", "A1"): "Beto aplicó una idea de la revisión de Ana: quedó a su nombre en «Actividad» («IA editó los atributos (a pedido de Beto)»).",
    ("CU9", "A2"): "Mientras Beto aplicaba la idea, la pantalla de Ana mostró «Aplicando (Beto)…» y no ofreció aplicarla.",
}

# ---- defectos ------------------------------------------------------------------------------------------------------
# Defectos que encontró la preparación de las pruebas (al trazar cada camino contra el software y al ejecutar los procedimientos). Todos se reprodujeron con una
# prueba automática que fallaba antes de la corrección (ver el commit de cada una) y se corrigieron.
DEFECTOS = [
    dict(id="D-01", cu="CU1", camino="A1", como="Al trazar el camino contra el código: la ficha decía que un código mal escrito avisa y vuelve a la portada, pero «Unirse al Lienzo» abría "
                                              "cualquier texto como si fuera una sala.",
         efecto="Una sala con un código que no era un identificador funcionaba en vivo pero el servidor no la podía respaldar ni retomar (los respaldos se guardan por identificador).",
         correccion="La portada solo entra con un código válido (sin espacios ni mayúsculas de más) y, si no, explica por qué; la ficha ahora distingue el código mal formado (A1) del código "
                    "válido sin trabajo guardado, que abre una sala vacía (A2).",
         pruebas=[f("app/landin-page/landin-page.spec.ts", "does not join with something that is not a room code and tells the person why"),
                  f("app/landin-page/landin-page.spec.ts", "joins the room whose code is typed, ignoring spaces and capital letters")]),
    dict(id="D-02", cu="CU2", camino="N1", como="Al trazar el camino contra el código: nada impedía soltar una relación sobre el lienzo vacío.",
         efecto="La relación quedaba colgada y se guardaba y se exportaba con extremos vacíos (a los generadores les llegaban relaciones sin origen o sin destino).",
         correccion="El lienzo ya no admite relaciones sin una clase en cada extremo y, si una llegara así, no se guarda, no se comparte ni se exporta.",
         pruebas=[f("services/diagram/diagram.service.spec.ts", "does not let a relationship end on the empty canvas: it must join two classes"),
                  f("services/exports/diagram-export.service.spec.ts", "leaves out a relationship that has no class at its target, so it is never saved, shared or exported")]),
    dict(id="D-03", cu="CU2 y CU6", camino="N1 y A1", como="Prueba física de CU2 N1: al soltar una relación sobre el lienzo vacío, la actividad de la otra pantalla decía «eliminó un elemento».",
         efecto="Un evento falso en la actividad de todos y una validación del modelo de más, por una relación que nunca se había compartido.",
         correccion="Eliminar una relación que no tenía una clase en cada extremo ya no se avisa a la sala.",
         pruebas=[f("services/diagram/diagram.service.spec.ts", "does not tell the room that a relationship was deleted when it was dropped on the empty canvas and never shared"),
                  f("services/diagram/diagram.service.spec.ts", "still tells the room when a relationship between two classes is deleted")]),
    dict(id="D-04", cu="CU11 y CU12", camino="E1", como="Al trazar el camino contra el código: la ficha decía que se avisa cuando el generador falla, pero el error solo se escribía en la consola.",
         efecto="La persona pulsaba «Exportar a Backend» o «Exportar Flutter» y no pasaba nada, sin saber por qué.",
         correccion="Se muestra «No se pudo generar el backend…» o «No se pudo generar la aplicación móvil…» y se detiene el indicador de espera.",
         pruebas=[f("services/exports/backend-generator.service.spec.ts", "tells the person when the generator does not answer, downloads nothing and stops the spinner"),
                  f("services/exports/frontend-generator.service.spec.ts", "tells the person when the diagram cannot be generated, and stops the spinner")]),
    dict(id="D-05", cu="CU4", camino="A2", como="Prueba física de CU4: una persona expulsada volvió a entrar con el código sin recargar la página.",
         efecto="Se la expulsaba otra vez de inmediato, con el mismo aviso, y no podía volver a la sala.",
         correccion="Cada vez que se abre el editor, la expulsión anterior deja de contar (el servicio de colaboración vive toda la sesión y la conservaba).",
         pruebas=[f("app/diagram/diagram.spec.ts", "does not treat a person expelled earlier as expelled again when they come back to the room"),
                  f("app/diagram/diagram.spec.ts", "still expels the person when the host removes them while they are in the new visit")]),
    dict(id="D-06", cu="CU14", camino="B", como="Prueba física de C4 en el navegador: el asistente de ayuda no respondía.",
         efecto="El navegador bloqueaba el pedido: el servidor no incluía la cabecera propia X-Help-Token entre las que acepta (la respuesta previa daba 200 pero el pedido fallaba).",
         correccion="La cabecera se agregó a las permitidas y una prueba verifica la respuesta previa del navegador.",
         pruebas=[b("uml_api/tests/test_ia_help_api.py", "HelpCorsTests.test_the_browser_may_send_the_help_token_header_from_the_frontend_origin")]),
    dict(id="D-07", cu="CU14", camino="E1", como="Al trazar el camino contra el software: la ficha decía que ante un fallo de la IA el sistema «remite al manual», pero solo muestra un mensaje.",
         efecto="Diferencia entre el documento y el software.",
         correccion="Se corrigió la ficha: muestra el mensaje «La IA no pudo responder ahora» y la pregunta queda en la conversación para volver a intentar (lo que el software ya hacía).",
         pruebas=[f("app/help-panel/help-panel.spec.ts", "shows a clear message when the AI cannot answer and keeps what the person wrote visible")]),
]

# ---- resultados de la ejecución completa -------------------------------------------------------------------------------
RESULTADOS = [
    ("Django (API y colaboración)", "back_generador_bd/.venv/bin/python manage.py test", "350 pruebas: todas pasaron (19 más, contra un MongoDB 7 real, se saltan sin MONGO_TEST_URL)", "pasó"),
    ("Django, adaptadores de MongoDB contra un servidor real", "MONGO_TEST_URL=mongodb://127.0.0.1:27018 manage.py test collab.tests.test_mongo_integration", "19 pruebas: todas pasaron", "pasó"),
    ("Angular (servicios, componentes y vistas)", "ng test --watch=false --browsers=ChromeHeadless", "288 pruebas: todas pasaron", "pasó"),
    ("Angular, compilación de producción", "ng build", "compiló sin errores (con las advertencias habituales de JointJS y file-saver)", "pasó"),
    ("Spring Boot (generador de backend)", "back_generator_uml/mvnw test", "pasó, incluida la compilación real del proyecto generado y la colección de Postman", "pasó"),
]
PENDIENTES = [
    "Probar la exportación XMI con Enterprise Architect 17.2 después de los cambios del segundo parcial (la prueba del primer parcial no se repitió).",
    "Ejecutar sin red la aplicación Flutter generada en un dispositivo (prueba del primer parcial).",
    "Ver una notificación real en un celular (el navegador de las pruebas tiene los avisos bloqueados).",
    "Repetir la prueba de colaboración con tres personas en navegadores distintos y con la medición de memoria de MongoDB en el servidor de AWS (queda para el despliegue).",
]


# ---- consultas y validación ------------------------------------------------------------------------------------
def caminos_del_modelo():
    """Los caminos de cada caso de uso, con su texto: [(cu, camino, texto)]. B = básico, A = alternativo, E = excepción, N = no permitido."""
    salida = []
    for cu in sorted(R.CASOS, key=R.numero):
        c = R.CASOS[cu]
        salida.append((cu, "B", "Camino básico: " + " ".join(c["flujo"])))
        for n, (condicion, pasos) in enumerate(c["alternos"], 1):
            salida.append((cu, f"A{n}", f"{condicion}: {' '.join(pasos)}"))
        for n, texto in enumerate(c["excepciones"], 1):
            salida.append((cu, f"E{n}", texto))
        for n, texto in enumerate(c.get("no_permitido", []), 1):
            salida.append((cu, f"N{n}", texto))
    return salida


def id_caso(c):
    return f"CP-{c['cu'][2:]}.{c['camino']}"


def casos_de_prueba(cu=None):
    ordenados = sorted(CASOS_DE_PRUEBA, key=lambda c: (R.numero(c["cu"]), "BAEN".index(c["camino"][0]), int(c["camino"][1:] or 0)))
    return [c for c in ordenados if cu is None or c["cu"] == cu]


def validar():
    """El documento coincide con el software y al revés: cada camino tiene su caso, cada caso su camino y cada prueba citada existe."""
    errores = []
    caminos = {(cu, camino) for cu, camino, _ in caminos_del_modelo()}
    casos = [(c["cu"], c["camino"]) for c in CASOS_DE_PRUEBA]
    for clave in sorted(caminos - set(casos), key=lambda k: (R.numero(k[0]), k[1])):
        errores.append(f"{clave[0]} {clave[1]}: el camino no tiene caso de prueba")
    for clave in sorted(set(casos) - caminos, key=lambda k: (R.numero(k[0]), k[1])):
        errores.append(f"{clave[0]} {clave[1]}: el caso de prueba no corresponde a ningún camino del caso de uso")
    for clave in {k for k in casos if casos.count(k) > 1}:
        errores.append(f"{clave[0]} {clave[1]}: hay más de un caso para el mismo camino")
    indice = indice_pruebas()
    for c in CASOS_DE_PRUEBA:
        if not c["auto"] and not c["manual"]:
            errores.append(f"{id_caso(c)}: no tiene prueba automática ni procedimiento manual")
        if c["nivel"] not in ("unidad", "integración", "sistema"):
            errores.append(f"{id_caso(c)}: nivel {c['nivel']!r} desconocido")
        for ref in c["auto"]:
            if ref not in indice:
                errores.append(f"{id_caso(c)}: la prueba {ref[0]}:{ref[1]}::{ref[2]} no existe en el repositorio")
        if len(set(c["auto"])) != len(c["auto"]):
            errores.append(f"{id_caso(c)}: cita dos veces la misma prueba")
    por_camino = {(c["cu"], c["camino"]): c for c in CASOS_DE_PRUEBA}
    for clave, (resultado, nota) in EJECUCIONES.items():
        if clave not in por_camino or not por_camino[clave]["manual"]:
            errores.append(f"{clave}: se registra una ejecución manual de un caso que no tiene procedimiento manual")
        if resultado not in ("pasó", "pasó con observación"):
            errores.append(f"{clave}: resultado {resultado!r} desconocido")
    for c in CASOS_DE_PRUEBA:
        if c["manual"] and (c["cu"], c["camino"]) not in EJECUCIONES:
            errores.append(f"{id_caso(c)}: tiene un procedimiento manual y no se registró su ejecución")
    for clave in EJECUCIONES_ADICIONALES:
        if clave not in por_camino:
            errores.append(f"{clave}: ejecución adicional de un camino que no existe")
    for d in DEFECTOS:
        for ref in d["pruebas"]:
            if ref not in indice:
                errores.append(f"{d['id']}: la prueba {ref[0]}:{ref[1]}::{ref[2]} no existe en el repositorio")
    if errores:
        raise ValueError("Modelo de pruebas inconsistente:\n  " + "\n  ".join(errores))
    return resumen()


def resumen():
    casos = CASOS_DE_PRUEBA
    citadas = {ref for c in casos for ref in c["auto"]}
    return dict(
        caminos=len(caminos_del_modelo()),
        casos=len(casos),
        con_automatica=sum(1 for c in casos if c["auto"]),
        con_manual=sum(1 for c in casos if c["manual"]),
        solo_manual=sum(1 for c in casos if c["manual"] and not c["auto"]),
        pruebas_citadas=len(citadas),
        pruebas_del_repositorio=len(indice_pruebas()),
    )


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    print(validar())
