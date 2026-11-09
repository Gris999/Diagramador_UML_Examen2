import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from collab import auth, rooms
from .chat_views import _forbidden, _participant_for

logger = logging.getLogger(__name__)

# Topes contra el abuso del envío de correos (cada código o invitación sale de nuestro dominio).
CODES_PER_EMAIL = (3, 600)
CODES_PER_IP = (10, 600)
CODES_GLOBAL = (60, 3600)
VERIFY_PER_IP = (30, 600)
INVITES_PER_SENDER = (20, 3600)
INVITES_PER_ROOM = (30, 3600)


def _bad_request(message):
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def _too_many(message="Demasiados intentos seguidos. Espera un momento."):
    return Response({"error": message}, status=status.HTTP_429_TOO_MANY_REQUESTS)


def _body(request):
    return request.data if hasattr(request.data, "get") else {}


@api_view(["GET"])
def auth_config(request):
    """Qué pide este servidor: si hay que iniciar sesión y si puede mandar correos (la interfaz decide con esto qué mostrar)."""
    return Response({"authRequired": settings.AUTH_REQUIRED, "mailConfigured": auth.mail_configured()})


@api_view(["POST"])
def auth_request_code(request):
    """Manda un código de 6 dígitos al correo. Responde lo mismo exista o no la persona: no revela nada de nadie."""
    email = auth.normalize_email(_body(request).get("email"))
    if email is None:
        return _bad_request("Escribe un correo válido.")
    if not auth.mail_configured():
        return Response(
            {"error": "Este servidor todavía no puede enviar correos."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    ip = auth.client_ip(request)
    if not (
        auth.allow(f"auth-code:{email}", *CODES_PER_EMAIL)
        and auth.allow(f"auth-code-ip:{ip}", *CODES_PER_IP)
        and auth.allow("auth-code:global", *CODES_GLOBAL)
    ):
        return _too_many("Pediste demasiados códigos. Espera unos minutos.")

    try:
        code = auth.issue_code(email)
        auth.send_code_email(email, code)
    except Exception as exc:
        logger.warning("No se pudo mandar el código de entrada (%s)", type(exc).__name__)
        return Response(
            {"error": "No pudimos mandar el correo ahora. Intenta de nuevo."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response({"sent": True})


@api_view(["POST"])
def auth_verify(request):
    """Cambia el código por una sesión firmada."""
    body = _body(request)
    email = auth.normalize_email(body.get("email"))
    if email is None:
        return _bad_request("Escribe un correo válido.")
    if not auth.allow(f"auth-verify-ip:{auth.client_ip(request)}", *VERIFY_PER_IP):
        return _too_many()
    try:
        valid = auth.check_code(email, body.get("code"))
    except Exception as exc:
        logger.warning("No se pudo comprobar el código de entrada (%s)", type(exc).__name__)
        return Response({"error": "No pudimos comprobar el código ahora. Intenta de nuevo."}, status=status.HTTP_502_BAD_GATEWAY)
    if not valid:
        return _bad_request("El código no es válido o ya venció. Pide uno nuevo.")
    return Response({
        "token": auth.make_session(email),
        "email": email,
        "name": auth.display_name_from_email(email),
    })


@api_view(["GET"])
def auth_me(request):
    email = getattr(request, "auth_email", None)
    if email is None:
        return Response({"error": "Inicia sesión con tu correo para continuar."}, status=status.HTTP_401_UNAUTHORIZED)
    # Cada vez que el navegador pregunta quién es, recibe una sesión nueva: quien sigue usando la herramienta no vuelve a pedir el código mientras
    # no pase un mes entero sin entrar (como GitHub o draw.io).
    return Response({"email": email, "name": auth.display_name_from_email(email), "token": auth.make_session(email)})


OFF = {"required": False, "email": None, "role": None, "is_owner": False, "can_edit": True, "title": "", "link_access": "restricted", "link_role": "viewer", "owner": None, "members": []}


def _off_response():
    return Response({"error": "El control de acceso está apagado en este servidor."}, status=status.HTTP_409_CONFLICT)


def _owner_only(request, room):
    """`None` si quien pide es el propietario de la sala; si no, la respuesta que se le da."""
    email = getattr(request, "auth_email", None)
    if email is None:
        return Response({"error": "Inicia sesión con tu correo para continuar."}, status=status.HTTP_401_UNAUTHORIZED)
    if rooms.effective_role(room, email) != rooms.OWNER:
        return Response({"error": "Solo el propietario puede hacer esto.", "code": "owner_only"}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(["GET", "POST"])
def room_access_view(request, room):
    """Quién tiene acceso a la sala y con qué rol. POST = entrar (la primera persona que abre una sala sin dueño queda como propietario; quien
    entra por un enlace público queda con la sala en su lista); GET = solo mirar.

    Con el interruptor apagado no hay control de acceso y la respuesta lo dice. Sin acceso, 403 con `code: not_invited`.
    """
    if not settings.AUTH_REQUIRED:
        return Response(OFF)
    email = getattr(request, "auth_email", None)
    if email is None:
        return Response({"error": "Inicia sesión con tu correo para continuar."}, status=status.HTTP_401_UNAUTHORIZED)
    if request.method == "POST":
        state, role = rooms.enter(room, email, claim=True)
    else:
        role = rooms.effective_role(room, email)
        state = "ok" if role else "denied"
    if state != "ok":
        return Response({"error": auth.NOT_INVITED_MESSAGE, "code": "not_invited", "email": email}, status=status.HTTP_403_FORBIDDEN)
    return Response(rooms.describe(room, email, role))


@api_view(["GET"])
def my_rooms_view(request):
    """«Mis diagramas»: las salas que creó esta persona, a las que la invitaron y las que abrió por un enlace público."""
    if not settings.AUTH_REQUIRED:
        return Response({"required": False, "rooms": []})
    email = getattr(request, "auth_email", None)
    if email is None:
        return Response({"error": "Inicia sesión con tu correo para continuar."}, status=status.HTTP_401_UNAUTHORIZED)
    return Response({"required": True, "rooms": rooms.my_rooms(email)})


@api_view(["PUT"])
def room_settings_view(request, room):
    """El propietario cambia el nombre y el acceso general (restringido o cualquiera con el enlace, y con qué rol entra quien llega por él)."""
    if not settings.AUTH_REQUIRED:
        return _off_response()
    refused = _owner_only(request, room)
    if refused is not None:
        return refused
    body = _body(request)
    try:
        rooms.update_settings(room, title=body.get("title"), link_access=body.get("link_access"), link_role=body.get("link_role"))
    except rooms.SharingError as exc:
        return _bad_request(str(exc))
    return Response(rooms.describe(room, request.auth_email, rooms.OWNER))


@api_view(["PUT", "DELETE"])
def room_members_view(request, room):
    """PUT: el propietario cambia el rol de alguien. DELETE: el propietario quita a alguien, o cualquiera se quita a sí mismo de su lista."""
    if not settings.AUTH_REQUIRED:
        return _off_response()
    me = getattr(request, "auth_email", None)
    body = _body(request)
    target = auth.normalize_email(body.get("email"))
    if target is None:
        return _bad_request("Escribe un correo válido.")
    leaving_myself = request.method == "DELETE" and target == me and rooms.effective_role(room, me) != rooms.OWNER
    if not leaving_myself:
        refused = _owner_only(request, room)
        if refused is not None:
            return refused
    if request.method == "PUT":
        try:
            changed = rooms.set_member_role(room, target, body.get("role"))
        except rooms.SharingError as exc:
            return _bad_request(str(exc))
    else:
        changed = rooms.remove_member(room, target)
    if not changed:
        return Response({"error": "Esa persona no está en la lista de la sala (o es el propietario)."}, status=status.HTTP_404_NOT_FOUND)
    if leaving_myself:
        return Response({"left": True})
    return Response(rooms.describe(room, me, rooms.OWNER))


@api_view(["DELETE"])
def room_delete_view(request, room):
    """El propietario borra el diagrama: nadie vuelve a entrar (los datos no se tocan)."""
    if not settings.AUTH_REQUIRED:
        return _off_response()
    refused = _owner_only(request, room)
    if refused is not None:
        return refused
    rooms.delete_room(room)
    return Response({"deleted": True})


@api_view(["POST"])
def room_invite(request, room):
    """Invita por correo a otras personas a esta sala: les llega el enlace y, si hay login, entran con ese mismo correo."""
    participant = _participant_for(request, room)
    if participant is None:
        return _forbidden()
    if not auth.mail_configured():
        return Response(
            {"error": "Este servidor todavía no puede enviar correos."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    body = _body(request)
    raw = body.get("emails")
    if not isinstance(raw, list) or not raw:
        return _bad_request("Escribe al menos un correo.")
    recipients = []
    for item in raw:
        email = auth.normalize_email(item)
        if email is None:
            return _bad_request("Revisa los correos: hay uno que no es válido.")
        if email not in recipients:
            recipients.append(email)
    if len(recipients) > auth.MAX_RECIPIENTS:
        return _bad_request(f"Puedes invitar a {auth.MAX_RECIPIENTS} personas a la vez.")

    role = body.get("role", rooms.EDITOR)
    if role not in rooms.ASSIGNABLE_ROLES:
        return _bad_request("La persona puede entrar como lector o como editor.")

    message = auth.clean_line(body.get("message"), auth.MAX_MESSAGE_CHARS)
    problem = auth.invitation_problem(message)
    if problem:
        return _bad_request(problem)

    sender_email = getattr(request, "auth_email", None)
    sender_key = sender_email or f"participante:{participant.id}"
    if not (
        auth.allow(f"invite:{sender_key}", *INVITES_PER_SENDER)
        and auth.allow(f"invite-room:{room}", *INVITES_PER_ROOM)
    ):
        return _too_many("Mandaste muchas invitaciones. Espera un rato.")

    # Con el control de acceso, invitar es dar acceso: el correo entra a la lista de la sala antes de mandarle el enlace.
    added = rooms.add_members(room, recipients, sender_email, role) if settings.AUTH_REQUIRED and sender_email else []
    sent, failed = auth.send_invitations(
        sender_name=participant.display_name,
        sender_email=sender_email,
        room=room,
        recipients=recipients,
        message=message,
        role=role if settings.AUTH_REQUIRED else None,
    )
    # Si el correo no salió, tampoco se deja dentro a quien no se avisó (y si invitan de nuevo, se vuelve a intentar).
    if added:
        rooms.remove_added(room, [email for email in failed if email in added])
    members = rooms.list_members(room) if settings.AUTH_REQUIRED else []
    if not sent:
        return Response(
            {"sent": [], "failed": failed, "members": members, "error": "No pudimos mandar las invitaciones ahora. Intenta de nuevo."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response({"sent": sent, "failed": failed, "members": members})
