"""Qué quiere la persona cuando escribe en el chat único de la sala con la IA.

Antes había tres pestañas (preguntar, pedir cambio, revisar) y la persona elegía una. Ahora hay una sola conversación y el servidor deduce la
intención del mensaje con reglas simples y predecibles (sin gastar una llamada a la IA y sin depender de que un modelo pequeño acierte):

- `history`: pide lo que hizo alguien («¿qué hizo Beto?», «historial de Ana»). Se contesta con el registro de actividad, sin IA.
- `review`: pide una revisión («revisa el diagrama»). Sus ideas quedan en el historial de la sala.
- `change`: pide un cambio al diagrama («agrega una clase Cliente»). La IA **propone** y espera permiso, salvo que la persona diga «directamente».
- `confirm` / `discard`: contestan una propuesta pendiente («sí», «aplícalo» / «no», «descártalo»).
- `ask`: todo lo demás es una pregunta y la IA solo responde.
"""

import re
import unicodedata

ASK = "ask"
CHANGE = "change"
REVIEW = "review"
HISTORY = "history"
CONFIRM = "confirm"
DISCARD = "discard"

# Mensajes cortos de respuesta a una propuesta: más largos que esto se tratan como un pedido nuevo.
MAX_ANSWER_WORDS = 4

_VERBS = frozenset("""
agrega agregar agregue agregues agregale anade anadir anadas anadele crea crear crees creale elimina eliminar elimines borra borrar borres
quita quitar quites quitale remueve remover saca sacar cambia cambiar cambies cambiale renombra renombrar renombres modifica modificar
modifiques edita editar edites actualiza actualizar actualices pon poner pongas ponle relaciona relacionar relaciones conecta conectar
conectes une unir unas vincula vincular mueve mover convierte convertir divide dividir separa separar reemplaza reemplazar sustituye
sustituir duplica duplicar copia copiar modela modelar disena disenar dibuja dibujar genera generar
""".split())

# Frases de cortesía o de intención que pueden ir antes del verbo: «por favor», «puedes», «quiero que», etc.
_PREFIX = re.compile(
    r"^(?:(?:hola|oye|bien|vale|ya|ahora|ademas|tambien|luego|despues|entonces|y|por favor|porfa|porfavor|puedes|podrias|podria|"
    r"me puedes|me podrias|quiero que|quisiera que|necesito que|me gustaria que|te pido que|quiero|necesito|quisiera)\s+)+"
)

_DIRECT = re.compile(
    r"\b(?:directamente|sin preguntar|sin confirmar|sin consultar|sin pedir permiso|de una vez|aplicalo ya|hazlo ya|no me preguntes)\b"
)

_REVIEW = re.compile(
    r"\b(?:revisa|revisar|revisame|revisalo|revision|revisemos|valida|validar|validame|audita|auditar|que mejorarias|que podria mejorar|"
    r"que se puede mejorar|ideas para mejorar|sugerencias|que le falta|que falta en|hay errores|errores del diagrama|errores en el diagrama)\b"
)

_HISTORY = re.compile(
    r"\b(?:historial|que hizo|que hicieron|que ha hecho|que han hecho|que cambio|que cambios hizo|que modifico|que agrego|que anadio|"
    r"que elimino|que borro|actividad de|acciones de|lo que hizo|que estuvo haciendo)\b"
)
# Pide el historial de todos, sin nombrar a nadie.
_HISTORY_ALL = re.compile(r"\b(?:historial|que hicieron|que han hecho|ultimos cambios)\b")

_YES = re.compile(
    r"^(?:si|sii|ok|okay|dale|aplicalo|aplicala|aplicalos|aplicalas|aplica|hazlo|adelante|confirmo|confirmado|de acuerdo|claro|esta bien|perfecto|va)\b"
)
_NO = re.compile(
    r"^(?:no|nop|cancela|cancelar|cancelalo|descarta|descartalo|descartar|olvidalo|dejalo|mejor no|nada|ninguno)\b"
)


# La IA de la sala se llama Uma (también se le dice «IA»): así se le habla en el chat.
AI_NAME = "Uma"
_AI_NAME = re.compile(r"^(?:uma|ia)\s+")


def normalize(text) -> str:
    """Minúsculas, sin tildes ni signos, con espacios simples: así «¿Qué hizo Beto?» y «que hizo beto» se leen igual."""
    if not isinstance(text, str):
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    plain = "".join(character for character in decomposed if not unicodedata.combining(character))
    plain = re.sub(r"[^a-z0-9ñ\s]", " ", plain)
    return " ".join(plain.split())


def _find_person(normalized, names):
    """La persona de la sala que nombra el mensaje (el nombre más largo gana), o `None`."""
    for name in sorted({n for n in names if isinstance(n, str) and n.strip()}, key=len, reverse=True):
        plain = normalize(name)
        if plain and re.search(rf"(?<![a-z0-9]){re.escape(plain)}(?![a-z0-9])", normalized):
            return name
    return None


def _is_change(normalized) -> bool:
    stripped = _PREFIX.sub("", normalized, count=1)
    first = stripped.split(" ", 1)[0] if stripped else ""
    return first in _VERBS


def classify(message, names=(), *, has_pending=False) -> dict:
    """Intención del mensaje: `{"intent", "person", "direct"}`.

    `names` son los nombres de las personas de la sala (y «IA»), para reconocer «¿qué hizo Beto?». `has_pending` dice si esa persona tiene una
    propuesta esperando permiso: solo entonces «sí» y «no» son respuestas a ella.
    """
    # «Uma, agrega una clase Cliente»: el nombre de la IA al principio no es parte del pedido.
    normalized = _AI_NAME.sub("", normalize(message), count=1)
    words = normalized.split()
    result = {"intent": ASK, "person": None, "direct": False}
    if not normalized:
        return result

    if has_pending and len(words) <= MAX_ANSWER_WORDS:
        if _YES.match(normalized):
            return {**result, "intent": CONFIRM}
        if _NO.match(normalized):
            return {**result, "intent": DISCARD}

    if _HISTORY.search(normalized):
        person = _find_person(normalized, names)
        if person is not None:
            return {**result, "intent": HISTORY, "person": person}
    if _HISTORY_ALL.search(normalized):
        return {**result, "intent": HISTORY}

    if _is_change(normalized):
        return {**result, "intent": CHANGE, "direct": bool(_DIRECT.search(normalized))}

    if _REVIEW.search(normalized):
        return {**result, "intent": REVIEW}

    return result
