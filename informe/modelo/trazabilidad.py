"""Validación, verificación y auditoría (sección 2.6): la matriz de trazabilidad y las comprobaciones de que el documento y el software coinciden.

El docente pidió cuatro pasos: 1) la documentación; 2) la **validación**, que todo lo que está en el documento esté en el software y en dos niveles, producto y
calidad; 3) la **verificación** (control de calidad), que todo lo registrado en el documento esté en el software **o al revés**, y que el diagrama de secuencia esté
relacionado con el software; 4) la **auditoría**, que el proceso sea correcto y tenga sus versiones. Este módulo reúne los datos de esos pasos leyéndolos de los modelos y
del repositorio, y `validar()` falla si algo no coincide, de modo que el informe no se puede generar con una matriz que tenga celdas vacías.
"""

import re
import subprocess
from pathlib import Path

from modelo import analisis as A
from modelo import codigo
from modelo import diseno as D
from modelo import implementacion as I
from modelo import pruebas as P
from modelo import realizaciones as RZ
from modelo import requisitos as R

RAIZ = Path(__file__).resolve().parents[2]


# ---- matriz de trazabilidad ------------------------------------------------------------------------------------
def _colaboraciones_de(cu):
    return [c for c in A.COLABORACIONES if cu in [x.strip() for x in c["cu"].split(",")]]


def _realizacion(col):
    return next(r for r in RZ.REALIZACIONES if r["col"] == col)


def matriz():
    """Una fila por caso de uso: requisitos, análisis, diseño, componentes, pruebas y resultado. Ninguna celda puede quedar vacía."""
    filas = []
    for cu in sorted(R.CASOS, key=R.numero):
        caso = R.CASOS[cu]
        cols = _colaboraciones_de(cu)
        reals = [_realizacion(c["id"]) for c in cols]
        escenarios = [e for r in reals for e in r["escenarios"]]
        clases = []
        for e in escenarios:
            for origen, destino, _, _ in e["mensajes"]:
                for vida in (origen, destino):
                    k = D._clave(vida)
                    if k in D.OBJETOS and k not in clases:
                        clases.append(k)
        archivos = sorted({D.OBJETOS[k]["archivo"] for k in clases})
        subsistemas = sorted({D.NOMBRE_SUBSISTEMA[D.OBJETOS[k]["sub"]] for k in clases})
        casos = P.casos_de_prueba(cu)
        automaticas = {ref for c in casos for ref in c["auto"]}
        manuales = [c for c in casos if c["manual"]]
        fallo = [c for c in manuales if P.EJECUCIONES[(c["cu"], c["camino"])][0] not in ("pasó", "pasó con observación")]
        filas.append(dict(
            cu=cu, nombre=caso["nombre"], rf=list(caso["rf"]),
            analisis=[c["id"] for c in cols],
            diseno=[r["col"] for r in reals], escenarios=len(escenarios), mensajes=sum(len(e["mensajes"]) for e in escenarios),
            clases=clases, archivos=archivos, subsistemas=subsistemas,
            casos=[P.id_caso(c) for c in casos], automaticas=len(automaticas), manuales=len(manuales), fallidos=len(fallo),
        ))
    return filas


# ---- cobertura de los requisitos del proyecto ---------------------------------------------------------------------------
# Los requisitos que no cubre un caso de uso (`rf` de cada caso) los cubre un requisito adicional o el propio documento.
RF_POR_REQUISITO_ADICIONAL = {
    "RF-33": "RA-01", "RNF-02": "RA-05", "RNF-04": "RA-02", "RNF-05": "RA-03", "RNF-07": "RA-05", "RNF-08": "RA-06",
    "RNF-03": "este documento y la carpeta `docs/`",
}


RF_GLOSA = {
    "RF-01": "Modelado UML 2.5 de clases y datos", "RF-02": "Crear y editar diagramas a mano", "RF-03": "Crear o modificar el UML con texto",
    "RF-04": "Crear o modificar el UML con una imagen o foto", "RF-05": "Crear o modificar el UML con voz", "RF-06": "Sesiones colaborativas de 2 o 3 personas",
    "RF-07": "Distinguir host y participantes", "RF-08": "Sincronización entre las pantallas", "RF-09": "Permisos verificados en el servidor",
    "RF-10": "Reconexión", "RF-11": "Recuperación del estado", "RF-12": "La primera conexión de la sala es el host", "RF-13": "Host y participantes editan por igual",
    "RF-14": "Solo el host expulsa", "RF-15": "Si el host sale, lo es quien lleva más tiempo", "RF-16": "Una reconexión es una conexión nueva",
    "RF-17": "Los roles solo existen mientras la sala está viva", "RF-18": "Intercambio XMI con Enterprise Architect", "RF-19": "Backend Spring Boot con PostgreSQL",
    "RF-20": "Colección de Postman", "RF-21": "Proyecto Flutter", "RF-22": "IA local o en el dispositivo", "RF-23": "Nombre visible e identificador anónimo",
    "RF-24": "La IA aparece como integrante de la sala", "RF-25": "Registro de actividad de la sala", "RF-26": "Una conversación con la IA por sala",
    "RF-27": "La IA responde sobre la actividad de cualquiera", "RF-28": "La IA cambia el diagrama solo si se lo piden", "RF-29": "Cambios de la IA a nombre de «IA, a pedido de X»",
    "RF-30": "Revisión del diagrama por la IA", "RF-31": "Retomar la sesión", "RF-32": "Vista de seguimiento en el celular", "RF-33": "Proveedor de IA configurable",
    "RF-34": "Avisos en la vista del celular", "RF-35": "Asistente de ayuda", "RNF-01": "Persistencia local sin conexión en la aplicación móvil",
    "RNF-02": "Arquitectura desplegable en AWS", "RNF-03": "Documentación de ingeniería", "RNF-04": "Un pedido a la IA a la vez por sala",
    "RNF-05": "Resiliencia ante los fallos de la IA", "RNF-06": "La actividad no estorba la edición", "RNF-07": "Despliegue reproducible con prueba de humo",
    "RNF-08": "Actividad y conversación en una base documental",
}


def requisitos_del_proyecto():
    """Cada requisito de `docs/REQUIREMENTS.md` con lo que lo cubre: [(id, descripción, cubierto por)]."""
    texto = (RAIZ / "docs" / "REQUIREMENTS.md").read_text(encoding="utf-8")
    ids = re.findall(r"^(?:- )?\*\*(RN?F-\d+)\*\*", texto, re.M)
    por_cu = {}
    for cu in sorted(R.CASOS, key=R.numero):
        for rf in R.CASOS[cu]["rf"]:
            por_cu.setdefault(rf, []).append(cu)
    salida = []
    for ident in ids:
        cubierto = ", ".join(por_cu[ident]) if ident in por_cu else RF_POR_REQUISITO_ADICIONAL.get(ident, "")
        salida.append((ident, RF_GLOSA.get(ident, ""), cubierto))
    return salida


# ---- el software que el documento no nombra (la otra dirección de la verificación) -------------------------------------
C_TIPO = "Tipo auxiliar sin comportamiento de negocio (excepción, DTO o interfaz de datos)"
C_MEMORIA = "Adaptador en memoria de un puerto modelado: sirve a las pruebas y a un solo proceso"
C_APOYO = "Módulo de apoyo de un componente modelado (funciones sueltas, sin estado)"
C_GENERADOR = "Utilidad o configuración interna del generador Spring Boot"
C_UI = "Componente de arranque o de presentación mínima, sin lógica de negocio"
C_CLIENTE = "Cliente de un servidor modelado: abre la conexión y entrega el resultado"

# (sufijo de la ruta, clase o módulo, categoría). `validar()` exige que sean exactamente las clases del código que el diseño no modela.
EXCLUIDAS = [
    ("collab/consumers.py", "ValidationBudget", C_TIPO),
    ("collab/conversation.py", "<conversation.py>", C_APOYO),
    ("collab/limits.py", "InMemoryRateLimiter", C_MEMORIA),
    ("collab/mongo.py", "<mongo.py>", C_APOYO),
    ("collab/mongo_stores.py", "<mongo_stores.py>", C_APOYO),
    ("collab/turn.py", "InMemoryTurnStore", C_MEMORIA),
    ("uml_api/chat_views.py", "_Refused", C_TIPO),
    ("uml_api/services/ai_provider.py", "AIProviderError", C_TIPO),
    ("uml_api/services/modelo_reentrenado.py", "<modelo_reentrenado.py>", C_APOYO),
    ("uml_api/services/xmi_service.py", "XMIError", C_TIPO),
    ("uml_api/utils/zip_utils.py", "<zip_utils.py>", C_APOYO),
    ("services/colaboration/uml-validation.service.ts", "UmlValidationService", None),  # se modeló en F6 (sección 2.3): no debe estar aquí
    ("services/diagram/association-class.util.ts", "RelationshipLike", C_TIPO),
    ("services/diagram/association-class.util.ts", "AssociationClassAttachment", C_TIPO),
    ("services/diagram/fallback.service.ts", "FallbackService", C_UI),
    ("services/exports/diagram-export.service.ts", "UmlClassDTO", C_TIPO),
    ("services/exports/diagram-export.service.ts", "UmlRelationshipDTO", C_TIPO),
    ("services/exports/diagram-export.service.ts", "UmlExportDTO", C_TIPO),
    ("app/app.ts", "App", C_UI),
    ("app/components/diagram/spinner/spinner.ts", "Spinner", C_UI),
    ("BackGeneratorUmlApplication.java", "BackGeneratorUmlApplication", C_GENERADOR),
    ("configuration/MustacheConfig.java", "MustacheConfig", C_GENERADOR),
    ("configuration/SecurityConfiguration.java", "SecurityConfiguration", C_GENERADOR),
    ("entity/UmlAttribute.java", "UmlAttribute", C_GENERADOR),
    ("entity/UmlClass.java", "UmlClass", C_GENERADOR),
    ("entity/UmlMethod.java", "UmlMethod", C_GENERADOR),
    ("entity/UmlRelationship.java", "UmlRelationship", C_GENERADOR),
    ("entity/UmlSchema.java", "UmlSchema", C_GENERADOR),
    ("service/JsonNormalizer.java", "JsonNormalizer", C_GENERADOR),
    ("service/NamingUtil.java", "NamingUtil", C_GENERADOR),
    ("service/TypeMapper.java", "TypeMapper", C_GENERADOR),
]
EXCLUIDAS = [e for e in EXCLUIDAS if e[2] is not None]


def cobertura_del_codigo():
    """El código indexado frente al diseño: cuántas clases y módulos están modelados y cuáles no (con su razón)."""
    ix = codigo.indice()
    modeladas = {(o["archivo"], o["clase"]) for o in D.OBJETOS.values()}
    interfaces = {i["nombre"] for i in D.INTERFACES}
    total = 0
    en_diseno = []
    sin_modelar = []
    for archivo, clases in ix.items():
        for clase in clases:
            total += 1
            if (archivo, clase) in modeladas or clase in interfaces:
                en_diseno.append((archivo, clase))
            else:
                sin_modelar.append((archivo, clase))
    razones = {}
    for sufijo, clase, categoria in EXCLUIDAS:
        coincidencias = [(a, c) for a, c in sin_modelar if a.endswith(sufijo) and c == clase]
        razones[(sufijo, clase)] = (categoria, coincidencias)
    return dict(total=total, modeladas=len(en_diseno), sin_modelar=sin_modelar, razones=razones)


# ---- verificación del diseño contra el código ------------------------------------------------------------------------
def verificacion():
    """Comprueba el diseño contra el código y devuelve las cuentas. Falla si algo del diseño no está en el código."""
    D.validar(exigir_nuevos=True, analisis=A)
    D.validar_realizaciones(A, nuevas={"_": []})
    mensajes = sum(len(e["mensajes"]) for r in RZ.REALIZACIONES for e in r["escenarios"])
    operaciones = {(D._clave(d), op) for r in RZ.REALIZACIONES for e in r["escenarios"] for o, d, op, _ in e["mensajes"] if not op.startswith("·") and D._clave(d) in D.OBJETOS}
    internos = sum(1 for r in RZ.REALIZACIONES for e in r["escenarios"] for _, _, op, _ in e["mensajes"] if op.startswith("·"))
    return dict(clases=len(D.OBJETOS), interfaces=len(D.INTERFACES), asociaciones=len(D.ASOCIACIONES), subsistemas=len(D.SUBSISTEMAS),
                realizaciones=len(RZ.REALIZACIONES), escenarios=sum(len(r["escenarios"]) for r in RZ.REALIZACIONES), mensajes=mensajes,
                operaciones=len(operaciones), externos=internos)


# ---- validación: nivel calidad ----------------------------------------------------------------------------------------
def f(archivo, nombre):
    return P.f(archivo, nombre)


def b(archivo, nombre):
    return P.b(archivo, nombre)


def j(archivo, nombre):
    return P.j(archivo, nombre)


# (atributo de calidad, qué se exige, evidencia en palabras, pruebas que lo demuestran). Cada prueba citada existe en el repositorio (`validar()` lo comprueba).
CALIDAD = [
    ("Seguridad: permisos", "Los permisos se verifican en el servidor, no en la pantalla (expulsar, editar desde el celular, aplicar una idea ajena).",
     "El servidor rechaza al no-host que expulsa, ignora lo que mande un observador y no deja a otra persona confirmar o liberar una idea reservada.",
     [b("collab/tests/test_roles.py", "CanvasRoleTests.test_participant_cannot_remove_another_participant"),
      b("collab/tests/test_viewer.py", "ViewerModeTests.test_viewers_cannot_send_operations_or_other_messages"),
      b("uml_api/tests/test_ia_chat_api.py", "ClaimSuggestionApiTests.test_only_who_claimed_it_can_release_it")]),
    ("Seguridad: entradas y secretos", "Los archivos que llegan no abren archivos ni conexiones y los errores no revelan datos internos ni claves.",
     "Un XMI con entidades externas se rechaza; los errores de la IA llegan al navegador sin detalles ni claves; el navegador solo puede mandar las cabeceras previstas.",
     [b("uml_api/tests/test_xmi_service.py", "XmiImportTests.test_rejects_doctype_and_entities"),
      b("uml_api/tests/test_ia_chat_api.py", "GeminiProviderTests.test_errors_never_leak_the_api_key"),
      b("uml_api/tests/test_ai_endpoints.py", "AIEndpointTests.test_image_service_error_is_sanitized_502"),
      b("uml_api/tests/test_ia_help_api.py", "HelpCorsTests.test_the_browser_may_send_the_help_token_header_from_the_frontend_origin"),
      b("uml_api/tests/test_ai_endpoints.py", "AIEndpointTests.test_the_old_unprotected_text_to_model_endpoint_is_gone")]),
    ("Fiabilidad: resiliencia", "Si algo falla (la IA, la base de datos, la red) el diagrama no se pierde ni queda a medias y la persona sabe qué pasó.",
     "Un fallo de la IA no guarda nada; un fallo al guardar la actividad no corta la edición; un fallo a mitad de guardar una revisión no deja mensajes sueltos.",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_provider_failure_returns_502_and_stores_nothing"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_activity_persistence_failure_does_not_break_relay"),
      b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_a_failure_while_publishing_a_review_leaves_nothing_half_saved"),
      f("services/exports/backend-generator.service.spec.ts", "tells the person when the generator does not answer, downloads nothing and stops the spinner")]),
    ("Costo y rendimiento", "El uso de la IA tiene topes por persona, por sala y para todo el servicio, y registrar la actividad no estorba la edición.",
     "12 pedidos por minuto por persona, 30 por sala y 60 en total (6 y 30 en la ayuda); mover o cambiar el tamaño no se registra; una ráfaga de validaciones cuesta una llamada.",
     [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_too_many_requests_in_a_minute_are_throttled"),
      b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_the_whole_service_shares_a_request_budget_across_rooms"),
      b("uml_api/tests/test_ia_help_api.py", "HelpLimitTests.test_the_seventh_question_in_a_minute_gets_429"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_only_meaningful_operations_create_activity"),
      b("collab/tests/test_uml_validation.py", "UmlValidationDoesNotBlockTheServerTests.test_a_burst_of_requests_costs_a_single_ai_call")]),
    ("Disponibilidad y recuperación", "Después de una desconexión o de cerrar todas las pestañas, la persona recupera el diagrama, la actividad y la conversación.",
     "El respaldo se guarda y se restaura; un respaldo atrasado no pisa el estado de la sala; una conexión nueva sabe quién es y recupera el estado.",
     [b("uml_api/tests/test_backup_uml_api.py", "BackupUmlApiTests.test_set_backup_persists_and_get_backup_restores_it"),
      f("services/colaboration/collaboration.service.spec.ts", "ignores a backup that arrives after the room already sent its state"),
      b("collab/tests/test_identity_activity.py", "CanvasIdentityActivityTests.test_a_new_connection_is_told_its_own_peer_id_before_anything_else")]),
    ("Mantenibilidad y portabilidad", "Las bases de datos se pueden cambiar sin tocar el resto: PostgreSQL o MongoDB con una variable de entorno, con el mismo comportamiento.",
     "Las mismas pruebas de contrato se ejecutan contra cada adaptador (PostgreSQL, MongoDB simulado y MongoDB real) y las de turno y tope contra Redis y la memoria.",
     [b("collab/tests/test_activity_store.py", "ActivityStoreContract.test_update_data_applies_the_change_and_returns_the_event"),
      b("collab/tests/test_conversation_store.py", "ConversationStoreContract.test_the_conversation_is_shared_by_everyone_in_the_room"),
      b("collab/tests/test_turn_store.py", "TurnStoreContract.test_a_second_request_in_the_same_room_waits_and_learns_who_has_the_turn"),
      b("collab/tests/test_rate_limiter.py", "RateLimiterContract.test_it_allows_up_to_the_limit_and_then_refuses"),
      b("collab/tests/test_mongo_stores.py", "StoreSelectionTests.test_a_setting_chooses_mongo_for_each_port")]),
    ("Interoperabilidad", "El modelo viaja a Enterprise Architect y vuelve sin perder clases, atributos, relaciones ni multiplicidades.",
     "El viaje ida y vuelta conserva el modelo y el importador entiende la forma en que Enterprise Architect escribe el XMI.",
     [b("uml_api/tests/test_xmi_service.py", "XmiImportTests.test_json_xmi_json_round_trip"),
      b("uml_api/tests/test_xmi_enterprise_architect.py", "EnterpriseArchitectXMITests.test_imports_ea_association_type_references_and_multiplicity"),
      b("uml_api/tests/test_xmi_layout.py", "XMILayoutTests.test_round_trip_preserves_class_position_and_size")]),
    ("Usabilidad", "La persona aprende a usar la herramienta sin ayuda externa y entiende los mensajes de error.",
     "El asistente de ayuda responde sobre el manual y se limita a la herramienta; cada error de la IA o de un generador dice qué pasó y qué hacer.",
     [b("uml_api/tests/test_ia_help_api.py", "HelpKnowledgeTests.test_the_manual_mentions_every_function_of_the_menu"),
      b("uml_api/tests/test_ia_help_api.py", "HelpPromptTests.test_the_prompt_limits_the_assistant_to_the_tool_and_gives_the_refusal_sentence"),
      f("app/ia-chat-panel/ia-chat-panel.spec.ts", "shows a clear message when the AI fails and keeps the chat usable"),
      f("app/landin-page/landin-page.spec.ts", "does not join with something that is not a room code and tells the person why")]),
]

# Requisitos adicionales (RA) del modelo de requisitos y dónde se demuestra cada uno: (evidencia en palabras, pruebas, archivos del repositorio que deben existir).
EVIDENCIA_RA = {
    "RA-01": ("El modelo local se evaluó con pedidos fijos y verificaciones estrictas, y el reentrenamiento (LoRA con MLX) tiene su propia evidencia: Anexos A y B.",
              [b("uml_api/tests/test_modelo_reentrenado.py", "MismoFormatoQueElEntrenamientoTests.test_the_system_prompt_is_identical_to_the_one_the_model_was_trained_with"),
               b("uml_api/tests/test_modelo_reentrenado.py", "CompactarYRestaurarTests.test_changes_go_back_to_the_real_ids"),
               b("uml_api/tests/test_ia_chat_api.py", "OllamaProviderTests.test_provider_selection_follows_the_settings")],
              ["docs/IA_LOCAL.md", "docs/REENTRENAMIENTO_IA.md", "scripts/evaluar_ia.py"]),
    "RA-02": ("Una sola conversación por sala: el servidor la entrega a todos y la IA la usa como contexto.",
              [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_the_conversation_belongs_to_the_whole_room"),
               b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_the_prompt_carries_the_conversation_of_the_room_with_who_said_what"),
               f("app/ia-chat-panel/ia-chat-panel.spec.ts", "says that the conversation belongs to the whole room")], []),
    "RA-03": ("Topes de uso, confirmación antes de eliminar y fallo seguro de la IA.",
              [b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_too_many_requests_in_a_minute_are_throttled"),
               b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_the_whole_room_shares_a_request_budget"),
               b("uml_api/tests/test_ia_chat_api.py", "ChatReliabilityTests.test_change_mode_asks_for_confirmation_when_the_model_returns_less_than_there_was"),
               b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_provider_failure_returns_502_and_stores_nothing")], []),
    "RA-04": ("El diagrama, la actividad y la conversación se recuperan al volver a la sala (CU5).",
              [b("uml_api/tests/test_backup_uml_api.py", "BackupUmlApiTests.test_set_backup_persists_and_get_backup_restores_it"),
               b("uml_api/tests/test_activity_api.py", "RoomActivityApiTests.test_history_is_room_scoped_and_oldest_first"),
               b("uml_api/tests/test_ia_chat_api.py", "IaChatApiTests.test_history_returns_the_latest_messages_oldest_first")], []),
    "RA-05": ("El sitio está en AWS con HTTPS y la prueba de humo comprueba lo que se puede ver desde afuera; la configuración del generador Spring tiene sus pruebas de orígenes permitidos.",
              [j("configuration/SecurityConfigurationCorsIntegrationTest.java", "preflightDeUnOrigenDesconocidoEsRechazado"),
               j("configuration/SecurityConfigurationTest.java", "conVariable_sumaLosNuevosSinQuitarLosExistentes")],
              ["docs/DESPLIEGUE.md", "scripts/smoke-test.sh", "docker-compose.app.yml", "docker-compose.db.yml"]),
    "RA-06": ("Cada dato en la base que le corresponde: PostgreSQL lo relacional, MongoDB los documentos que solo se agregan y Redis lo efímero; las pruebas de contrato lo comprueban en cada una.",
              [b("collab/tests/test_activity_store.py", "ActivityStoreContract.test_update_data_applies_the_change_and_returns_the_event"),
               b("collab/tests/test_turn_store.py", "TurnStoreContract.test_a_second_request_in_the_same_room_waits_and_learns_who_has_the_turn"),
               b("collab/tests/test_migrar_a_mongo.py", "MigrarAMongoTests.test_the_existing_history_is_copied_with_the_same_ids_and_content")],
              ["back_generador_bd/collab/mongo_stores.py"]),
}


def calidad():
    return CALIDAD


# ---- auditoría --------------------------------------------------------------------------------------------------------
def _git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True, check=True).stdout.strip()


PATRONES_SECRETOS = [
    ("Clave de API de Google (AIza…)", re.compile(r"AIza[0-9A-Za-z_\-]{35}")),
    ("Clave de acceso de AWS (AKIA…)", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("Token de GitHub (ghp_…, github_pat_…)", re.compile(r"gh[pousr]_[0-9A-Za-z]{36,}|github_pat_[0-9A-Za-z_]{40,}")),
    ("Llave privada", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("Contraseña o token escritos en una asignación", re.compile(r"""(?i)\b(?:password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*['"]([^'"\s$<{][^'"\s]{11,})['"]""")),
    ("URL con usuario y contraseña", re.compile(r"[a-z][a-z0-9+.\-]*://[^/\s:@]+:[^/\s:@]{3,}@(?!localhost|mongo_db|postgres)")),
]
UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
PLACEHOLDERS = re.compile(r"(?i)change-?me|example|your|xxxx|placeholder|dummy|fake|secreta|prueba|test|\.\.\.|<")


def escanear_secretos():
    """Busca secretos en todos los archivos de texto que Git rastrea. Devuelve (archivos revisados, hallazgos sin marcador de ejemplo, hallazgos descartados)."""
    revisados = 0
    reales, descartados = [], []
    for ruta in _git("ls-files").splitlines():
        archivo = RAIZ / ruta
        if not archivo.is_file() or archivo.stat().st_size > 2_000_000:
            continue
        try:
            texto = archivo.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        revisados += 1
        for nombre, patron in PATRONES_SECRETOS:
            for m in patron.finditer(texto):
                dato = m.group(0)
                valor = m.group(m.lastindex) if m.lastindex else dato
                # Un UUID no es un secreto: el «token» del navegador es un identificador anónimo y las pruebas lo escriben a mano.
                if UUID.fullmatch(valor) or PLACEHOLDERS.search(dato) or PLACEHOLDERS.search(ruta):
                    descartados.append((ruta, nombre))
                else:
                    reales.append((ruta, nombre))
    return revisados, reales, descartados


def dependencias():
    """Versiones de las dependencias principales leídas de requirements.txt (UTF-16), package.json y pom.xml."""
    reqs = (RAIZ / "back_generador_bd" / "requirements.txt").read_bytes().decode("utf-16").split()
    pines = dict(r.split("==") for r in reqs if "==" in r)
    paquete = __import__("json").loads((RAIZ / "front_generador_bd" / "package.json").read_text(encoding="utf-8"))
    deps = {**paquete.get("dependencies", {}), **paquete.get("devDependencies", {})}
    pom = (RAIZ / "back_generator_uml" / "pom.xml").read_text(encoding="utf-8")
    spring = re.search(r"<parent>.*?<version>([^<]+)</version>", pom, re.S).group(1)
    java = re.search(r"<java.version>([^<]+)</java.version>", pom).group(1)
    return dict(
        python=[(n, pines[n]) for n in ("Django", "djangorestframework", "channels", "channels_redis", "redis", "psycopg", "pymongo") if n in pines or n.lower() in {k.lower() for k in pines}],
        python_total=len(reqs),
        front=[(n, deps[n]) for n in ("@angular/core", "jointjs", "tailwindcss", "typescript", "rxjs") if n in deps],
        front_total=len(deps),
        java=[("Spring Boot", spring), ("Java", java)],
    )


def auditoria():
    """Estado del repositorio: ramas, etiquetas, commits y reglas de calidad."""
    base = I.linea_base()
    commits_total = int(_git("rev-list", "--count", "HEAD"))
    desde_base = int(_git("rev-list", "--count", f"{base['etiqueta']}..HEAD"))
    tipos = {}
    for asunto in _git("log", f"{base['etiqueta']}..HEAD", "--format=%s").splitlines():
        m = re.match(r"([a-z]+)(?:\([^)]*\))?:", asunto)
        tipos[m.group(1) if m else "otro"] = tipos.get(m.group(1) if m else "otro", 0) + 1
    autores = {}
    for nombre in _git("log", "--format=%an").splitlines():
        autores[nombre] = autores.get(nombre, 0) + 1
    ramas = [r.strip().lstrip("* ") for r in _git("branch", "--format=%(refname:short)").splitlines()]
    remotos = {}
    for linea in _git("remote", "-v").splitlines():
        nombre, url, _ = linea.split(None, 2)
        remotos[nombre] = url
    rastreados = _git("ls-files").splitlines()
    por_tipo = {}
    for ruta in rastreados:
        ext = Path(ruta).suffix
        if ext in (".py", ".ts", ".java", ".html", ".md", ".yml", ".sh"):
            por_tipo[ext] = por_tipo.get(ext, 0) + 1
    env_rastreado = [r for r in rastreados if Path(r).name == ".env"]
    gitignore = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    return dict(
        base=base, commits_total=commits_total, desde_base=desde_base, tipos=tipos, autores=autores,
        ramas=ramas, etiquetas=_git("tag").splitlines(), remotos=remotos,
        cabeza=_git("rev-parse", "--short", "HEAD"), fecha=_git("log", "-1", "--date=short", "--format=%ad"), rama=_git("rev-parse", "--abbrev-ref", "HEAD"),
        archivos=len(rastreados), por_tipo=por_tipo, env_rastreado=env_rastreado, env_ignorado=".env" in gitignore,
    )


# ---- validación general ------------------------------------------------------------------------------------------------
def validar():
    errores = []
    for fila in matriz():
        for campo in ("rf", "analisis", "diseno", "clases", "archivos", "subsistemas", "casos"):
            if not fila[campo] and not (campo == "rf" and fila["cu"] == "CU14"):
                errores.append(f"{fila['cu']}: la matriz de trazabilidad no tiene {campo}")
        if fila["escenarios"] < 1 or fila["automaticas"] < 1:
            errores.append(f"{fila['cu']}: sin escenarios de secuencia o sin pruebas automáticas")
        if fila["fallidos"]:
            errores.append(f"{fila['cu']}: tiene procedimientos manuales que no pasaron")
    for ident, _, cubierto in requisitos_del_proyecto():
        if not cubierto:
            errores.append(f"el requisito {ident} no lo cubre ningún caso de uso ni requisito adicional")
    for ident, glosa, _ in requisitos_del_proyecto():
        if not glosa:
            errores.append(f"el requisito {ident} no tiene descripción en español")
    cob = cobertura_del_codigo()
    sin_razon = [x for x in cob["sin_modelar"] if not any(x in coincidencias for _, coincidencias in cob["razones"].values())]
    for archivo, clase in sin_razon:
        errores.append(f"el código tiene {clase} en {archivo} y el diseño no lo modela ni se explica por qué")
    for (sufijo, clase), (_, coincidencias) in cob["razones"].items():
        if not coincidencias:
            errores.append(f"la exclusión {clase} de {sufijo} ya no corresponde a código sin modelar")
    indice = P.indice_pruebas()
    for atributo, _, _, refs in CALIDAD:
        if not refs:
            errores.append(f"{atributo}: sin pruebas que lo demuestren")
        for ref in refs:
            if ref not in indice:
                errores.append(f"{atributo}: la prueba {ref[0]}:{ref[1]}::{ref[2]} no existe en el repositorio")
    ra = {x[0] for x in R.REQUISITOS_ADICIONALES}
    if ra != set(EVIDENCIA_RA):
        errores.append(f"los requisitos adicionales sin evidencia son {sorted(ra - set(EVIDENCIA_RA))}")
    for codigo_ra, (_, refs, archivos) in EVIDENCIA_RA.items():
        if not refs:
            errores.append(f"{codigo_ra}: sin pruebas que lo demuestren")
        for ref in refs:
            if ref not in indice:
                errores.append(f"{codigo_ra}: la prueba {ref[0]}:{ref[1]}::{ref[2]} no existe en el repositorio")
        for archivo in archivos:
            if not (RAIZ / archivo).exists():
                errores.append(f"{codigo_ra}: el archivo {archivo} no existe")
    revisados, reales, _ = escanear_secretos()
    for ruta, nombre in reales:
        errores.append(f"posible secreto en {ruta}: {nombre}")
    if errores:
        raise ValueError("Validación inconsistente:\n  " + "\n  ".join(errores))
    return dict(verificacion=verificacion(), cobertura=dict(total=cob["total"], modeladas=cob["modeladas"], excluidas=len(EXCLUIDAS)), secretos_revisados=revisados)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    print(validar())
