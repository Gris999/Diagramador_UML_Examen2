import logging
import uuid

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from collab.stores import get_rate_limiter
from .services.ai_provider import AIProviderError, get_ai_provider
from .services.help_knowledge import build_help_prompt, load_knowledge
from .services.ia_context import MAX_MESSAGE_CHARS

logger = logging.getLogger(__name__)

# Topes de coste: cada persona (identificada por el token anónimo de su navegador) y todo el servicio. El segundo no depende de un
# identificador que el cliente elige.
HELP_PER_PERSON_PER_MINUTE = 6
HELP_GLOBAL_PER_MINUTE = 30
WINDOW_SECONDS = 60
# La conversación de ayuda la guarda el navegador y la manda completa en cada pregunta; el servidor solo usa lo más reciente.
MAX_HELP_HISTORY = 6


def _bad_request(message):
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def _help_token(request):
    try:
        return uuid.UUID(request.headers.get("X-Help-Token", ""))
    except (ValueError, AttributeError, TypeError):
        return None


def _within_limits(token):
    """False si la persona o el servicio ya se pasaron de su tope. Si no se puede consultar el tope, se responde igual (queda en el registro)."""
    try:
        limiter = get_rate_limiter()
        return limiter.allow(f"help:{token}", HELP_PER_PERSON_PER_MINUTE, WINDOW_SECONDS) and limiter.allow(
            "help:global", HELP_GLOBAL_PER_MINUTE, WINDOW_SECONDS
        )
    except Exception as exc:
        logger.warning("No se pudo consultar el tope del asistente de ayuda (%s)", type(exc).__name__)
        return True


def _previous_messages(raw):
    if not isinstance(raw, list):
        return []
    valid = [
        {"role": item["role"], "content": item["content"].strip()}
        for item in raw
        if isinstance(item, dict)
        and item.get("role") in ("user", "ia")
        and isinstance(item.get("content"), str)
        and item["content"].strip()
    ]
    return valid[-MAX_HELP_HISTORY:]


@api_view(["POST"])
def ia_help(request):
    """Asistente que enseña a usar la herramienta. No depende de una sala: sirve también desde la página principal."""
    token = _help_token(request)
    if token is None:
        return _bad_request("Falta el identificador de quien pregunta.")

    body = request.data if hasattr(request.data, "get") else {}
    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        return _bad_request("El mensaje es requerido.")
    message = message.strip()
    if len(message) > MAX_MESSAGE_CHARS:
        return _bad_request(f"El mensaje no puede superar {MAX_MESSAGE_CHARS} caracteres.")

    if not _within_limits(token):
        return Response(
            {"error": "Demasiadas preguntas seguidas. Espera un momento."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    prompt = build_help_prompt(
        knowledge=load_knowledge(), history=_previous_messages(body.get("history")), message=message
    )
    try:
        reply = get_ai_provider().chat(prompt)
    except AIProviderError as exc:
        logger.warning("El asistente de ayuda no pudo responder: %s", exc)
        return _unavailable()
    except Exception as exc:
        logger.warning("Fallo inesperado del proveedor de IA en la ayuda (%s)", type(exc).__name__)
        return _unavailable()
    return Response({"reply": reply})


def _unavailable():
    return Response(
        {"error": "La IA no pudo responder ahora. Intenta de nuevo."},
        status=status.HTTP_502_BAD_GATEWAY,
    )
