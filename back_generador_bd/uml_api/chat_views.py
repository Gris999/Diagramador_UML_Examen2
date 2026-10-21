import logging
import uuid
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from collab.models import ActivityEvent, ChatMessage, Participant
from .services.ai_provider import AIProviderError, get_ai_provider
from .services.ia_context import (
    MAX_EVENTS,
    MAX_HISTORY,
    MAX_MESSAGE_CHARS,
    build_chat_prompt,
)

logger = logging.getLogger(__name__)

SUPPORTED_MODES = {"ask"}
MAX_REQUESTS_PER_MINUTE = 12


def _participant_for(request, room):
    """El token anónimo del navegador identifica a quien pregunta en esa sala."""
    raw = request.headers.get("X-Participant-Token", "")
    try:
        token = uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        return None
    return Participant.objects.filter(room=room, token=token).first()


def _forbidden():
    return Response(
        {"error": "Participante no identificado en esta sala."},
        status=status.HTTP_403_FORBIDDEN,
    )


def serialize_chat_message(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


@api_view(["POST"])
def ia_chat(request, room):
    participant = _participant_for(request, room)
    if participant is None:
        return _forbidden()

    body = request.data if hasattr(request.data, "get") else {}
    mode = body.get("mode", "ask")
    if mode not in SUPPORTED_MODES:
        return Response(
            {"error": "Modo no soportado."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        return Response(
            {"error": "El mensaje es requerido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    message = message.strip()
    if len(message) > MAX_MESSAGE_CHARS:
        return Response(
            {"error": f"El mensaje no puede superar {MAX_MESSAGE_CHARS} caracteres."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    recent_requests = ChatMessage.objects.filter(
        participant=participant,
        role=ChatMessage.ROLE_USER,
        created_at__gte=timezone.now() - timedelta(minutes=1),
    ).count()
    if recent_requests >= MAX_REQUESTS_PER_MINUTE:
        return Response(
            {"error": "Demasiadas preguntas seguidas. Espera un momento."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    # Contexto: actividad de TODA la sala + solo el chat de quien pregunta.
    events = list(
        ActivityEvent.objects.filter(room=room).order_by("-id")[:MAX_EVENTS]
    )[::-1]
    history = list(
        ChatMessage.objects.filter(participant=participant).order_by("-id")[:MAX_HISTORY]
    )[::-1]
    prompt = build_chat_prompt(
        participant_name=participant.display_name,
        uml=body.get("uml"),
        events=events,
        history=history,
        message=message,
    )

    try:
        reply = get_ai_provider().chat(prompt)
    except AIProviderError as exc:
        logger.warning("La IA no pudo responder en la sala %s: %s", room, exc)
        return Response(
            {"error": "La IA no pudo responder ahora. Intenta de nuevo."},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as exc:
        logger.warning(
            "Fallo inesperado del proveedor de IA (%s)", type(exc).__name__
        )
        return Response(
            {"error": "La IA no pudo responder ahora. Intenta de nuevo."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    ChatMessage.objects.create(
        room=room,
        participant=participant,
        role=ChatMessage.ROLE_USER,
        content=message,
    )
    ChatMessage.objects.create(
        room=room,
        participant=participant,
        role=ChatMessage.ROLE_IA,
        content=reply,
    )
    return Response({"reply": reply})


@api_view(["GET"])
def chat_history(request, room):
    participant = _participant_for(request, room)
    if participant is None:
        return _forbidden()

    try:
        limit = int(request.query_params.get("limit", 50))
    except (TypeError, ValueError):
        limit = 50
    limit = min(max(limit, 1), 100)

    # Solo los mensajes de quien pregunta, los más recientes, del más viejo al más nuevo.
    messages = list(
        ChatMessage.objects.filter(participant=participant).order_by("-id")[:limit]
    )[::-1]
    return Response({"messages": [serialize_chat_message(m) for m in messages]})
