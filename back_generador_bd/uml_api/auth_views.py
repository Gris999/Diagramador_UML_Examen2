import logging

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from collab import auth
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
    return Response({"email": email, "name": auth.display_name_from_email(email)})


@api_view(["GET", "POST"])
def room_access_view(request, room):
    """Quién tiene acceso a la sala. POST = entrar (la primera persona que abre una sala sin dueño queda como propietario); GET = solo mirar.

    Con el interruptor apagado no hay control de acceso y la respuesta lo dice. Si el correo no está invitado, 403 con `code: not_invited`.
    """
    if not settings.AUTH_REQUIRED:
        return Response({"required": False, "email": None, "role": None, "members": []})
    email = getattr(request, "auth_email", None)
    if email is None:
        return Response({"error": "Inicia sesión con tu correo para continuar."}, status=status.HTTP_401_UNAUTHORIZED)
    if auth.room_access(room, email, claim=request.method == "POST") != "ok":
        return Response(
            {"error": auth.NOT_INVITED_MESSAGE, "code": "not_invited", "email": email},
            status=status.HTTP_403_FORBIDDEN,
        )
    return Response({"required": True, "email": email, "role": auth.role_of(room, email), "members": auth.list_members(room)})


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
    added = auth.add_invited(room, recipients, sender_email) if settings.AUTH_REQUIRED and sender_email else []
    sent, failed = auth.send_invitations(
        sender_name=participant.display_name,
        sender_email=sender_email,
        room=room,
        recipients=recipients,
        message=message,
    )
    # Si el correo no salió, tampoco se deja dentro a quien no se avisó (y si invitan de nuevo, se vuelve a intentar).
    if added:
        auth.remove_invited(room, [email for email in failed if email in added])
    members = auth.list_members(room) if settings.AUTH_REQUIRED else []
    if not sent:
        return Response(
            {"sent": [], "failed": failed, "members": members, "error": "No pudimos mandar las invitaciones ahora. Intenta de nuevo."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response({"sent": sent, "failed": failed, "members": members})
