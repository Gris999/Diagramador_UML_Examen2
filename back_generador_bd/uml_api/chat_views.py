import logging
import uuid
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from collab.groups import room_group_name, viewers_group_name
from collab.models import IaAttempt, Participant
from collab.stores import get_activity_store, get_conversation_store, get_turn_store
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
# La IA atiende un pedido a la vez por sala: el turno vence solo a los 130 s, un poco más que lo que espera el navegador (110 s), para que si
# quien pidió se desconecta la sala no quede esperando para siempre.
TURN_TTL_SECONDS = 130


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


def _bad_request(message):
    return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)


def _ia_unavailable():
    return Response(
        {"error": "La IA no pudo responder ahora. Intenta de nuevo."},
        status=status.HTTP_502_BAD_GATEWAY,
    )


def _take_turn(room, participant):
    """Toma el turno de la sala. Devuelve `(turnos, respuesta)`: `respuesta` es el 409 si la IA está atendiendo a otra persona.

    Si Redis falla la sala sigue funcionando sin turno (se registra el fallo): los topes de uso siguen protegiendo el costo.
    """
    turnos = get_turn_store()
    try:
        taken, holder = turnos.take(room, participant.id, participant.display_name, TURN_TTL_SECONDS)
    except Exception as exc:
        logger.warning("No se pudo tomar el turno de la IA en la sala %s (%s)", room, type(exc).__name__)
        return None, None
    if not taken:
        return None, Response(
            {"error": f"La IA está atendiendo a {holder}. Espera a que termine."},
            status=status.HTTP_409_CONFLICT,
        )
    return turnos, None


def _release_turn(turnos, room, participant):
    if turnos is None:
        return
    try:
        turnos.release(room, participant.id)
    except Exception as exc:
        logger.warning("No se pudo devolver el turno de la IA en la sala %s (%s)", room, type(exc).__name__)


def _publish_activity(room, event):
    """Avisa a la sala en vivo; si el canal falla, el evento igual queda guardado."""
    message = {"type": "activity", "event": event}
    try:
        layer = get_channel_layer()
        for group in (room_group_name(room), viewers_group_name(room)):
            async_to_sync(layer.group_send)(group, message)
    except Exception as exc:
        logger.warning("No se pudo difundir la actividad de la IA (%s)", type(exc).__name__)


def _answer(provider, room, participant, body, message):
    events = get_activity_store().recent(room, MAX_EVENTS)
    history = get_conversation_store().history(room, MAX_HISTORY)
    prompt = build_chat_prompt(
        participant_name=participant.display_name,
        uml=body.get("uml"),
        events=events,
        history=history,
        message=message,
    )
    reply = provider.chat(prompt)
    get_conversation_store().append_exchange(room, participant, "ask", message, reply)
    return Response({"reply": reply})


def _change(provider, room, participant, body, message):
    changes = provider.change(message, body.get("uml"))
    validate_changes(changes)
    reply = "Listo, apliqué el cambio en el diagrama."
    get_conversation_store().append_exchange(room, participant, "change", message, reply)
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

    # La conversación y el evento público se guardan juntos: si el evento no se puede guardar, se deshace la conversación.
    conversation = get_conversation_store()
    ids = conversation.append_exchange(room, participant, "review", message, reply)
    try:
        event = get_activity_store().create(
            room=room,
            actor_id=participant.id,
            actor_name="IA",
            actor_kind="ia",
            event_type="ia_review",
            summary=f"revisó el diagrama a pedido de {participant.display_name}: {count}"[:255],
            data={"findings": findings, "requested_by": participant.display_name},
        )
    except Exception:
        conversation.discard_exchange(room, ids)
        raise
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

    turnos, busy = _take_turn(room, participant)
    if busy is not None:
        return busy
    try:
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
    finally:
        _release_turn(turnos, room, participant)


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

    # La conversación de la sala (la de todos), los mensajes más recientes, del más viejo al más nuevo.
    return Response({"messages": get_conversation_store().history(room, limit)})


@api_view(["GET"])
def ia_provider_info(request):
    return Response(describe_ai_provider())


def _has_idea(event, index):
    """El evento es una revisión de la IA con una idea aplicable en `index`."""
    if event is None or event["type"] != "ia_review":
        return False
    findings = event["data"].get("findings") if isinstance(event["data"], dict) else None
    return (
        isinstance(findings, list)
        and 0 <= index < len(findings)
        and isinstance(findings[index], dict)
        and bool(findings[index].get("prompt"))
    )


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


class _Refused(Exception):
    """El cambio a una idea no procede; lleva la respuesta que se le da a quien lo pidió."""

    def __init__(self, response):
        self.response = response


def _claim(data, method, index, participant):
    """Aplica reservar (POST), confirmar (PUT) o liberar (DELETE) a las ideas de una revisión; devuelve el `data` nuevo."""
    now = timezone.now()
    entries = [a for a in data.get("applied", []) if isinstance(a, dict)]
    existing = next((a for a in entries if a.get("index") == index), None)
    others = [a for a in entries if a.get("index") != index]
    mine = existing is not None and existing.get("by_id") == participant.id
    taken = existing is not None and _is_live(existing, now)
    entry = {"index": index, "by": participant.display_name, "by_id": participant.id}

    if method == "POST":
        if taken and not (mine and existing.get("state") == RESERVED):
            raise _Refused(Response(
                {"error": "Otra persona ya aplicó o está aplicando esta idea."},
                status=status.HTTP_409_CONFLICT,
            ))
        entries = others + [{**entry, "state": RESERVED, "reserved_at": now.isoformat()}]
    elif method == "PUT":
        if taken and not mine:
            raise _Refused(Response(
                {"error": "Otra persona ya aplicó o está aplicando esta idea."},
                status=status.HTTP_409_CONFLICT,
            ))
        # Si la reserva venció pero nadie la tomó, el cambio ya se aplicó:
        # se registra igual para que no se pueda aplicar dos veces.
        entries = others + [{**entry, "state": APPLIED, "applied_at": now.isoformat()}]
    else:
        if existing is None:
            raise _Refused(None)
        if not mine:
            raise _Refused(_forbidden())
        if existing.get("state", APPLIED) != RESERVED:
            raise _Refused(Response(
                {"error": "La idea ya está aplicada."},
                status=status.HTTP_409_CONFLICT,
            ))
        entries = others

    return {**data, "applied": entries}


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

    store = get_activity_store()
    event = store.get(room, event_id)
    if not _has_idea(event, index):
        return Response({"error": "Idea no encontrada."}, status=status.HTTP_404_NOT_FOUND)

    try:
        event = store.update_data(room, event_id, lambda data: _claim(data, request.method, index, participant))
    except _Refused as refused:
        # Liberar una idea que nadie reservó no cambia nada: se devuelve el evento tal cual.
        return refused.response or Response({"event": event})

    _publish_activity(room, event)
    return Response({"event": event})
