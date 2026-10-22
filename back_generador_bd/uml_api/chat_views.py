import logging
import uuid
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from collab.activity import serialize_activity_event
from collab.groups import room_group_name, viewers_group_name
from collab.models import ActivityEvent, ChatMessage, IaAttempt, Participant
from .services.ai_provider import AIProviderError, describe_ai_provider, get_ai_provider
from .services.change_guard import count_destructive, validate_changes
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
# Topes de coste compartidos: un mismo participante, toda una sala y todo el
# servicio. Los dos últimos no dependen de identificadores que el cliente elige.
MAX_ROOM_REQUESTS_PER_MINUTE = 30
MAX_GLOBAL_REQUESTS_PER_MINUTE = 60
ATTEMPT_RETENTION = timedelta(hours=1)


def _participant_for(request, room):
    """El token anónimo del navegador identifica a quien pregunta en esa sala."""
    raw = request.headers.get("X-Participant-Token", "")
    try:
        token = uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        return None
    return Participant.objects.filter(room=room, token=token).first()


def _reserve_attempt(room, participant):
    """Reserva un cupo de IA antes de llamar al proveedor; False si no queda.

    Se inserta primero y se cuenta después: con pedidos simultáneos ninguno ve
    menos de lo que hay, así que el tope no se sobrepasa (en el límite pueden
    rechazarse de más, nunca aceptarse de más). Un pedido que falla conserva su
    cupo; uno rechazado lo devuelve para no vaciar el cupo de los demás.
    """
    now = timezone.now()
    IaAttempt.objects.filter(created_at__lt=now - ATTEMPT_RETENTION).delete()
    attempt = IaAttempt.objects.create(room=room, participant=participant)
    last_minute = IaAttempt.objects.filter(created_at__gte=now - timedelta(minutes=1))
    if (
        last_minute.filter(participant=participant).count() > MAX_REQUESTS_PER_MINUTE
        or last_minute.filter(room=room).count() > MAX_ROOM_REQUESTS_PER_MINUTE
        or last_minute.count() > MAX_GLOBAL_REQUESTS_PER_MINUTE
    ):
        attempt.delete()
        return False
    return True


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
    """Guarda pregunta y respuesta juntas: o quedan las dos o ninguna."""
    with transaction.atomic():
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
    validate_changes(changes)
    reply = "Listo, apliqué el cambio en el diagrama."
    _store_exchange(room, participant, "change", message, reply)
    return Response({
        "reply": reply,
        "changes": changes,
        # La interfaz pide confirmación antes de aplicar un cambio que elimina cosas.
        "destructive": count_destructive(changes, body.get("uml")),
    })


def _review(provider, room, participant, body, message):
    result = parse_review(provider.chat(build_review_prompt(uml=body.get("uml"))))
    findings = result["findings"]

    lines = [result["summary"]] if result["summary"] else []
    lines += [f"{number}. {finding['text']}" for number, finding in enumerate(findings, 1)]
    reply = "\n".join(lines) or "No encontré observaciones importantes."

    if not findings:
        count = "sin observaciones"
    elif len(findings) == 1:
        count = "1 observación"
    else:
        count = f"{len(findings)} observaciones"

    # La conversación y el evento público se guardan juntos.
    with transaction.atomic():
        _store_exchange(room, participant, "review", message, reply)
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

    if not _reserve_attempt(room, participant):
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


def _reviewable_event(room, event_id, index):
    """Evento de revisión de esa sala con una idea aplicable en `index`, o None."""
    event = ActivityEvent.objects.select_for_update().filter(
        id=event_id, room=room, type="ia_review"
    ).first()
    if event is None:
        return None
    findings = event.data.get("findings") if isinstance(event.data, dict) else None
    if (
        not isinstance(findings, list)
        or not 0 <= index < len(findings)
        or not isinstance(findings[index], dict)
        or not findings[index].get("prompt")
    ):
        return None
    return event


RESERVED = "reserved"
APPLIED = "applied"
# Un poco más que lo que tarda la IA en contestar (110 s en el navegador): si
# quien reservó cierra la pestaña o pierde la conexión, la idea vuelve a quedar libre.
RESERVATION_TTL = timedelta(seconds=150)


def _is_live(entry, now):
    """Una idea sigue tomada si ya se aplicó o si su reserva no venció."""
    if entry.get("state", APPLIED) != RESERVED:
        return True
    try:
        reserved_at = datetime.fromisoformat(entry["reserved_at"])
    except (KeyError, TypeError, ValueError):
        return False
    return now - reserved_at < RESERVATION_TTL


@api_view(["POST", "PUT", "DELETE"])
def claim_suggestion(request, room, event_id, index):
    """Ciclo de una idea de la IA: reservar (POST), confirmar (PUT) o liberar (DELETE).

    Reservar es atómico y queda guardado: dos personas no pueden aplicar la
    misma idea a la vez. La reserva vence sola si nadie la confirma. Confirmar
    marca la idea como aplicada para todos, incluso tras recargar la página.
    """
    participant = _participant_for(request, room)
    if participant is None:
        return _forbidden()

    with transaction.atomic():
        event = _reviewable_event(room, event_id, index)
        if event is None:
            return Response({"error": "Idea no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        entries = [a for a in event.data.get("applied", []) if isinstance(a, dict)]
        existing = next((a for a in entries if a.get("index") == index), None)
        others = [a for a in entries if a.get("index") != index]
        mine = existing is not None and existing.get("by_id") == participant.id
        taken = existing is not None and _is_live(existing, now)
        entry = {"index": index, "by": participant.display_name, "by_id": participant.id}

        if request.method == "POST":
            if taken and not (mine and existing.get("state") == RESERVED):
                return Response(
                    {"error": "Otra persona ya aplicó o está aplicando esta idea."},
                    status=status.HTTP_409_CONFLICT,
                )
            entries = others + [{**entry, "state": RESERVED, "reserved_at": now.isoformat()}]
        elif request.method == "PUT":
            if taken and not mine:
                return Response(
                    {"error": "Otra persona ya aplicó o está aplicando esta idea."},
                    status=status.HTTP_409_CONFLICT,
                )
            # Si la reserva venció pero nadie la tomó, el cambio ya se aplicó:
            # se registra igual para que no se pueda aplicar dos veces.
            entries = others + [{**entry, "state": APPLIED, "applied_at": now.isoformat()}]
        else:
            if existing is None:
                return Response({"event": serialize_activity_event(event)})
            if not mine:
                return _forbidden()
            if existing.get("state", APPLIED) != RESERVED:
                return Response(
                    {"error": "La idea ya está aplicada."},
                    status=status.HTTP_409_CONFLICT,
                )
            entries = others

        event.data = {**event.data, "applied": entries}
        event.save(update_fields=["data"])

    _publish_activity(room, event)
    return Response({"event": serialize_activity_event(event)})
