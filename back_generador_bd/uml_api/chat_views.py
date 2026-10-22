import logging
import uuid
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from collab.activity import serialize_activity_event
from collab.groups import room_group_name, viewers_group_name
from collab.models import ActivityEvent, ChatMessage, Participant
from .services.ai_provider import AIProviderError, describe_ai_provider, get_ai_provider
from .services.ia_context import (
    MAX_EVENTS,
    MAX_HISTORY,
    MAX_MESSAGE_CHARS,
    build_chat_prompt,
    build_review_prompt,
    parse_review,
)

logger = logging.getLogger(__name__)

SUPPORTED_MODES = {"ask", "change", "review"}
DEFAULT_REVIEW_MESSAGE = "Revisa el diagrama"
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
        "mode": message.mode,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


def _bad_request(message):
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def _ia_unavailable():
    return Response(
        {"error": "La IA no pudo responder ahora. Intenta de nuevo."},
        status=status.HTTP_502_BAD_GATEWAY,
    )


def _store_exchange(room, participant, mode, message, reply):
    ChatMessage.objects.create(
        room=room,
        participant=participant,
        role=ChatMessage.ROLE_USER,
        mode=mode,
        content=message,
    )
    ChatMessage.objects.create(
        room=room,
        participant=participant,
        role=ChatMessage.ROLE_IA,
        mode=mode,
        content=reply,
    )


def _publish_activity(room, event):
    """Avisa a la sala en vivo; si el canal falla, el evento igual queda guardado."""
    message = {"type": "activity", "event": serialize_activity_event(event)}
    try:
        layer = get_channel_layer()
        for group in (room_group_name(room), viewers_group_name(room)):
            async_to_sync(layer.group_send)(group, message)
    except Exception as exc:
        logger.warning("No se pudo difundir la actividad de la IA (%s)", type(exc).__name__)


def _answer(provider, room, participant, body, message):
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
    reply = provider.chat(prompt)
    _store_exchange(room, participant, "ask", message, reply)
    return Response({"reply": reply})


def _change(provider, room, participant, body, message):
    changes = provider.change(message, body.get("uml"))
    reply = "Listo, apliqué el cambio en el diagrama."
    _store_exchange(room, participant, "change", message, reply)
    return Response({"reply": reply, "changes": changes})


def _review(provider, room, participant, body, message):
    result = parse_review(provider.chat(build_review_prompt(uml=body.get("uml"))))
    findings = result["findings"]

    lines = [result["summary"]] if result["summary"] else []
    lines += [f"{number}. {finding['text']}" for number, finding in enumerate(findings, 1)]
    reply = "\n".join(lines) or "No encontré observaciones importantes."
    _store_exchange(room, participant, "review", message, reply)

    if not findings:
        count = "sin observaciones"
    elif len(findings) == 1:
        count = "1 observación"
    else:
        count = f"{len(findings)} observaciones"
    event = ActivityEvent.objects.create(
        room=room,
        actor=participant,
        actor_name="IA",
        actor_kind="ia",
        type="ia_review",
        summary=f"revisó el diagrama a pedido de {participant.display_name}: {count}"[:255],
        data={"findings": findings, "requested_by": participant.display_name},
    )
    _publish_activity(room, event)

    suggestions = [
        {"id": index, "text": finding["text"], "prompt": finding["prompt"]}
        for index, finding in enumerate(findings)
    ]
    return Response({"reply": reply, "suggestions": suggestions})


MODE_HANDLERS = {"ask": _answer, "change": _change, "review": _review}


@api_view(["POST"])
def ia_chat(request, room):
    participant = _participant_for(request, room)
    if participant is None:
        return _forbidden()

    body = request.data if hasattr(request.data, "get") else {}
    mode = body.get("mode", "ask")
    if mode not in SUPPORTED_MODES:
        return _bad_request("Modo no soportado.")

    message = body.get("message")
    if message is None and mode == "review":
        message = DEFAULT_REVIEW_MESSAGE
    if not isinstance(message, str) or not message.strip():
        return _bad_request("El mensaje es requerido.")
    message = message.strip()
    if len(message) > MAX_MESSAGE_CHARS:
        return _bad_request(
            f"El mensaje no puede superar {MAX_MESSAGE_CHARS} caracteres."
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

    try:
        return MODE_HANDLERS[mode](get_ai_provider(), room, participant, body, message)
    except AIProviderError as exc:
        logger.warning("La IA no pudo responder en la sala %s: %s", room, exc)
        return _ia_unavailable()
    except Exception as exc:
        logger.warning(
            "Fallo inesperado del proveedor de IA (%s)", type(exc).__name__
        )
        return _ia_unavailable()


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


@api_view(["GET"])
def ia_provider_info(request):
    return Response(describe_ai_provider())
