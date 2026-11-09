"""Entrar con el correo: un código de un solo uso que llega por correo, una sesión firmada y las invitaciones.

No hay contraseñas. Quien quiere entrar escribe su correo, recibe un código de 6 dígitos (vale 10 minutos y tiene 5 intentos) y, si lo escribe bien,
el servidor le da una sesión firmada (30 días) que el navegador manda en cada pedido a la API y al abrir el WebSocket. Una cuenta es un correo
comprobado: no se guarda nada de la persona en la base de datos.

Todo depende del interruptor `AUTH_REQUIRED`: apagado (por defecto) la API y el WebSocket funcionan como siempre, sin sesión; prendido, exigen una.
"""

import hashlib
import hmac
import logging
import re
import secrets

from django.conf import settings
from django.core import signing
from django.core.mail import EmailMessage, get_connection
from django.db import IntegrityError, transaction
from django.http import JsonResponse

from .models import RoomMember
from .stores import get_rate_limiter, get_room_state

logger = logging.getLogger(__name__)

CODE_TTL_SECONDS = 600
CODE_DIGITS = 6
MAX_CODE_ATTEMPTS = 5
MAX_EMAIL_CHARS = 254
MAX_RECIPIENTS = 10
MAX_MESSAGE_CHARS = 300
SESSION_SALT = "diagramador-sesion"
# Rutas de la API que se pueden usar sin sesión: las que sirven justamente para obtenerla.
PUBLIC_PREFIXES = ("/api/auth/",)

# Las rutas de la API que son de una sala (la sala es el primer dato de la ruta, o el código de los respaldos).
_ROOM_PATH = re.compile(r"^/api/(?:rooms/(?P<room>[^/]+)/|(?:set|get)_backup_uml/(?P<backup>[^/]+)/)")
NOT_INVITED_MESSAGE = "No tienes invitación para esta sala. Pide que te inviten con tu correo."

_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?\.[A-Za-z]{2,}$")
_LINK = re.compile(r"(?:://|www\.)", re.IGNORECASE)


def normalize_email(value):
    """El correo en minúsculas y sin espacios, o `None` si no parece un correo (sin saltos de línea ni comas que sirvan para colar cabeceras)."""
    if not isinstance(value, str):
        return None
    email = value.strip().lower()
    if not email or len(email) > MAX_EMAIL_CHARS or not _EMAIL.match(email) or ".." in email:
        return None
    return email


def display_name_from_email(email):
    """Un nombre para mostrar a partir del correo: «pedro.alaca@x.com» → «Pedro Alaca»."""
    local = email.split("@", 1)[0].split("+", 1)[0]
    name = " ".join(part for part in re.split(r"[._-]+", local) if part).title()
    return (name or "Usuario")[:40]


def mail_configured():
    """Hay con qué enviar correo: un servidor SMTP con clave, o un adaptador que no sale a internet (consola, pruebas)."""
    if "smtp" not in settings.EMAIL_BACKEND:
        return True
    return bool(settings.EMAIL_HOST and settings.EMAIL_HOST_PASSWORD)


# ---- código de un solo uso --------------------------------------------------------------------------------------
def _code_key(email):
    return f"login-code:{email}"


def _hash(email, code):
    return hmac.new(settings.SECRET_KEY.encode("utf-8"), f"{email}:{code}".encode("utf-8"), hashlib.sha256).hexdigest()


def issue_code(email):
    """Genera un código nuevo para el correo (reemplaza al anterior) y lo guarda solo como huella, con vencimiento."""
    code = f"{secrets.randbelow(10 ** CODE_DIGITS):0{CODE_DIGITS}d}"
    get_room_state().set(_code_key(email), {"h": _hash(email, code), "n": 0}, CODE_TTL_SECONDS)
    return code


def check_code(email, code):
    """El código es el que se mandó a ese correo. Acierta una sola vez; tras 5 errores el código deja de servir."""
    if not isinstance(code, str) or not re.fullmatch(rf"\d{{{CODE_DIGITS}}}", code.strip()):
        return False
    state = get_room_state()
    entry = state.get(_code_key(email))
    if not isinstance(entry, dict) or not isinstance(entry.get("h"), str):
        return False
    attempts = entry.get("n", 0) if isinstance(entry.get("n"), int) else MAX_CODE_ATTEMPTS
    if attempts >= MAX_CODE_ATTEMPTS:
        state.delete(_code_key(email))
        return False
    if hmac.compare_digest(entry["h"], _hash(email, code.strip())):
        state.delete(_code_key(email))
        return True
    state.set(_code_key(email), {"h": entry["h"], "n": attempts + 1}, CODE_TTL_SECONDS)
    return False


# ---- sesión firmada ---------------------------------------------------------------------------------------------
def _signer():
    return signing.TimestampSigner(salt=SESSION_SALT)


def make_session(email):
    return _signer().sign_object({"email": email})


def read_session(token):
    """El correo de una sesión válida (firmada por este servidor y sin vencer), o `None`."""
    if not isinstance(token, str) or not token or len(token) > 1024:
        return None
    try:
        data = _signer().unsign_object(token, max_age=settings.AUTH_SESSION_DAYS * 86400)
    except signing.BadSignature:  # incluye SignatureExpired
        return None
    email = data.get("email") if isinstance(data, dict) else None
    return normalize_email(email)


def session_from_header(value):
    """Lee `Authorization: Bearer <sesión>`."""
    if not isinstance(value, str) or not value.lower().startswith("bearer "):
        return None
    return read_session(value[7:].strip())


# ---- quién tiene acceso a cada sala ----------------------------------------------------------------------------
def room_of_path(path):
    """La sala a la que pertenece una ruta de la API, o `None` si la ruta no es de una sala."""
    match = _ROOM_PATH.match(path)
    return (match.group("room") or match.group("backup")) if match else None


def room_access(room, email, *, claim=False):
    """`ok` si el correo tiene acceso a la sala; `denied` si la sala ya tiene gente y él no está; `unclaimed` si todavía nadie la abrió.

    Con `claim=True` el primero que llega a una sala sin dueño queda como propietario. Si dos personas la abren a la vez, solo una gana
    (restricción de la base de datos) y la otra queda `denied`.
    """
    members = RoomMember.objects.filter(room=room)
    if members.filter(email=email).exists():
        return "ok"
    if members.exists():
        return "denied"
    if not claim:
        return "unclaimed"
    try:
        with transaction.atomic():
            RoomMember.objects.create(room=room, email=email, role=RoomMember.ROLE_OWNER)
    except IntegrityError:
        return room_access(room, email)
    return "ok"


def list_members(room):
    """Los correos con acceso a la sala, el propietario primero."""
    rows = RoomMember.objects.filter(room=room).order_by("created_at", "id")
    owners = [{"email": r.email, "role": r.role} for r in rows if r.role == RoomMember.ROLE_OWNER]
    others = [{"email": r.email, "role": r.role} for r in rows if r.role != RoomMember.ROLE_OWNER]
    return owners + others


def role_of(room, email):
    member = RoomMember.objects.filter(room=room, email=email).first()
    return member.role if member else None


def add_invited(room, emails, invited_by):
    """Da acceso a los correos y devuelve los que son nuevos (los que ya tenían acceso no cambian)."""
    added = []
    for email in emails:
        _, created = RoomMember.objects.get_or_create(
            room=room, email=email, defaults={"role": RoomMember.ROLE_INVITED, "invited_by": invited_by or ""}
        )
        if created:
            added.append(email)
    return added


def remove_invited(room, emails):
    """Quita el acceso de invitados (nunca del propietario): se usa si el correo de la invitación no salió."""
    RoomMember.objects.filter(room=room, email__in=emails, role=RoomMember.ROLE_INVITED).delete()


class EmailSessionMiddleware:
    """Deja en `request.auth_email` el correo de la sesión (o `None`) y, con `AUTH_REQUIRED`, exige sesión en toda la API menos en `/api/auth/`.

    En las rutas de una sala exige además que ese correo tenga acceso a ella (invitado por correo); la ruta `/access/` lo decide en su vista
    porque es la que reclama la sala para su primer propietario.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.auth_email = session_from_header(request.headers.get("Authorization", ""))
        guarded = (
            settings.AUTH_REQUIRED
            and request.method != "OPTIONS"
            and request.path.startswith("/api/")
            and not request.path.startswith(PUBLIC_PREFIXES)
        )
        if guarded:
            if request.auth_email is None:
                return JsonResponse({"error": "Inicia sesión con tu correo para continuar."}, status=401)
            room = room_of_path(request.path)
            if room and request.path != f"/api/rooms/{room}/access/" and room_access(room, request.auth_email) != "ok":
                return JsonResponse({"error": NOT_INVITED_MESSAGE, "code": "not_invited"}, status=403)
        return self.get_response(request)


# ---- topes de uso -----------------------------------------------------------------------------------------------
def allow(key, limit, window_seconds):
    """Cuenta un pedido de `key`; `False` si ya pasó el tope de la ventana. Si el contador falla, se rechaza (más vale pedir esperar que dejar mandar correos sin tope)."""
    try:
        return get_rate_limiter().allow(key, limit, window_seconds)
    except Exception as exc:
        logger.warning("No se pudo consultar un tope de correo (%s)", type(exc).__name__)
        return False


def client_ip(request):
    """La dirección de quien pide: la que anotó el proxy (la última de `X-Forwarded-For`) o, sin proxy, la de la conexión."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    last = forwarded.split(",")[-1].strip() if forwarded else ""
    return last or request.META.get("REMOTE_ADDR", "") or "?"


# ---- correos ----------------------------------------------------------------------------------------------------
def send_code_email(email, code):
    body = (
        f"Tu código para entrar a Diagramador UML es: {code}\n\n"
        f"Vale {CODE_TTL_SECONDS // 60} minutos y sirve una sola vez. Si no lo pediste, ignora este correo.\n"
    )
    EmailMessage(subject=f"Tu código para entrar: {code}", body=body, to=[email]).send(fail_silently=False)


def clean_line(value, limit):
    """Texto de una línea: sin caracteres de control y con largo acotado."""
    if not isinstance(value, str):
        return ""
    return " ".join("".join(c for c in value if c.isprintable()).split())[:limit]


def invitation_problem(message):
    """Por qué el mensaje de una invitación no sirve, o `None`. No se aceptan enlaces: el único enlace del correo es el de la sala."""
    if message and _LINK.search(message):
        return "El mensaje no puede llevar enlaces."
    return None


def send_invitations(*, sender_name, sender_email, room, recipients, message):
    """Manda una invitación a cada correo. Devuelve `(enviados, fallaron)`; el envío de uno que falla no impide el de los demás."""
    link = f"{settings.PUBLIC_APP_URL}/diagram/{room}"
    name = clean_line(sender_name, 40) or "Alguien"
    lines = [
        "Hola,",
        "",
        f"{name} te invitó a trabajar en equipo en un diagrama de clases UML en Diagramador UML.",
    ]
    if message:
        lines += ["", f"Mensaje de {name}: {message}"]
    lines += ["", f"Entra aquí: {link}"]
    if settings.AUTH_REQUIRED:
        lines += ["", "La página te pedirá tu correo y te mandará un código para entrar. Usa este mismo correo."]
    lines += ["", "Si no esperabas esta invitación, ignora este correo."]
    body = "\n".join(lines) + "\n"

    sent, failed = [], []
    with get_connection() as connection:
        for recipient in recipients:
            message_ = EmailMessage(
                subject=f"{name} te invitó a un diagrama UML",
                body=body,
                to=[recipient],
                reply_to=[sender_email] if sender_email else None,
                connection=connection,
            )
            try:
                message_.send(fail_silently=False)
                sent.append(recipient)
            except Exception as exc:
                logger.warning("No se pudo mandar una invitación (%s)", type(exc).__name__)
                failed.append(recipient)
    return sent, failed
