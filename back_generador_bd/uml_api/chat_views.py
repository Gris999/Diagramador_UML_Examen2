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
from collab.stores import get_activity_store, get_conversation_store, get_rate_limiter, get_room_state, get_turn_store
from .services.ai_provider import AIProviderError, describe_ai_provider, get_ai_provider, provider_options
from .services.change_guard import count_destructive, validate_changes
from .services.change_summary import summarize_changes
from .services.chat_intent import ASK, CHANGE, CONFIRM, DISCARD, HISTORY, REVIEW, classify
from .services.ia_context import (
    MAX_EVENTS,
    MAX_HISTORY,
    MAX_MESSAGE_CHARS,
    build_chat_prompt,
    build_review_prompt,
    parse_review,
)

logger = logging.getLogger(__name__)

# `auto` es el chat único: el servidor deduce si es una pregunta, un cambio, una revisión o una consulta de historial (`chat_intent`).
# Los otros tres modos se conservan por compatibilidad y para las ideas de la IA, que se aplican con un clic.
SUPPORTED_MODES = {"auto", "ask", "change", "review"}
# Una propuesta de cambio espera permiso este tiempo; el modelo elegido para la sala se recuerda una semana.
PROPOSAL_TTL_SECONDS = 600
PROVIDER_TTL_SECONDS = 7 * 24 * 3600
HISTORY_LINES = 12
# Cambiar el modelo de la sala deja una actividad cada vez: el tope evita que alguien llene el registro alternando.
PROVIDER_CHANGES_PER_MINUTE = 6
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
    if findings:
        lines.append("Las ideas quedaron en Actividad: ahí se aplican con un clic.")
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


def _state_get(key):
    """Lee un dato pasajero de la sala; si el almacén falla se sigue como si no hubiera nada (la sala no se cae por esto)."""
    try:
        return get_room_state().get(key)
    except Exception as exc:
        logger.warning("No se pudo leer el estado de la sala (%s)", type(exc).__name__)
        return None


def _proposal_key(room, participant):
    return f"ia-proposal:{room}:{participant.id}"


def _provider_key(room):
    return f"ia-provider:{room}"


def _ago(iso):
    """«hace 5 min» a partir de la hora de un evento (ISO 8601)."""
    try:
        seconds = (timezone.now() - datetime.fromisoformat(iso)).total_seconds()
    except (TypeError, ValueError):
        return ""
    if seconds < 60:
        return "ahora"
    if seconds < 3600:
        return f"hace {int(seconds // 60)} min"
    if seconds < 86400:
        return f"hace {int(seconds // 3600)} h"
    return f"hace {int(seconds // 86400)} d"


def _done_by(event, person):
    """El evento es de `person`: lo hizo ella, o la IA lo hizo a pedido suyo (cambios aplicados con la IA y revisiones)."""
    wanted = person.strip().lower()
    if (event.get("actor_name") or "").strip().lower() == wanted:
        return True
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    if str(data.get("requested_by") or "").strip().lower() == wanted:
        return True
    return (event.get("summary") or "").strip().lower().endswith(f"(a pedido de {wanted})")


def _history_line(event, person):
    actor = event.get("actor_name") or "Alguien"
    # Lo que la IA hizo a pedido de la persona se dice como tal: «IA añadió la clase X (a pedido de Beto)».
    who = "" if person and actor.strip().lower() == person.strip().lower() else f"{actor} "
    when = _ago(event.get("created_at"))
    return f"• {who}{event.get('summary', '')}" + (f" · {when}" if when else "")


def _history_reply(room, participant, message, person, events):
    """Lo que hizo `person` (o toda la sala) según el registro de actividad: no usa la IA, así que siempre es exacto."""
    chosen = events if person is None else [event for event in events if _done_by(event, person)]
    subject = "la sala" if person is None else person
    if not chosen:
        reply = f"No veo actividad de {subject} en esta sala todavía."
    else:
        shown = chosen[-HISTORY_LINES:]
        lines = [_history_line(event, person) for event in shown]
        header = "Lo último que pasó en la sala:" if person is None else f"Lo último que hizo {person}:"
        if len(chosen) > len(shown):
            lines.append(f"… y {len(chosen) - len(shown)} acciones anteriores.")
        reply = "\n".join([header, *lines])
    get_conversation_store().append_exchange(room, participant, "ask", message, reply)
    return Response({"reply": reply, "intent": HISTORY})


def _propose(provider, room, participant, body, message):
    """Calcula el cambio pedido pero NO lo aplica: lo cuenta y espera el permiso de quien lo pidió."""
    changes = provider.change(message, body.get("uml"))
    validate_changes(changes)
    lines = summarize_changes(changes, body.get("uml"))
    destructive = count_destructive(changes, body.get("uml"))

    reply = "Esto es lo que haría:\n" + "\n".join(f"• {line}" for line in lines) if lines else "Haría el cambio que pediste en el diagrama."
    if destructive:
        reply += f"\nOjo: elimina {destructive} elemento{'s' if destructive != 1 else ''}."
    reply += "\n¿Lo aplico? Responde «sí» o «no», o usa los botones."

    ids = get_conversation_store().append_exchange(room, participant, "change", message, reply)
    try:
        get_room_state().set(
            _proposal_key(room, participant),
            {"changes": changes, "message": message},
            PROPOSAL_TTL_SECONDS,
        )
    except Exception:
        get_conversation_store().discard_exchange(room, ids)
        raise
    return Response({
        "reply": reply,
        "intent": CHANGE,
        "proposal": {"lines": lines, "destructive": destructive},
    })


def _confirm(room, participant, body, message, pending):
    """La persona dijo que sí: se entrega el cambio guardado para que su navegador lo aplique."""
    changes = pending["changes"]
    validate_changes(changes)
    reply = "Listo, apliqué el cambio en el diagrama."
    get_conversation_store().append_exchange(room, participant, "change", message, reply)
    get_room_state().delete(_proposal_key(room, participant))
    return Response({
        "reply": reply,
        "intent": CONFIRM,
        "changes": changes,
        # El diagrama pudo cambiar desde la propuesta: la confirmación de eliminaciones se calcula con el diagrama de ahora.
        "destructive": count_destructive(changes, body.get("uml")),
    })


def _discard(room, participant, message):
    reply = "Listo, descarté la propuesta. No cambié el diagrama."
    get_conversation_store().append_exchange(room, participant, "change", message, reply)
    get_room_state().delete(_proposal_key(room, participant))
    return Response({"reply": reply, "intent": DISCARD})


def _known_names(room, events):
    """Nombres que el chat reconoce en «¿qué hizo Beto?»: las personas de la sala, quienes aparecen en la actividad y la IA."""
    names = set(Participant.objects.filter(room=room).values_list("display_name", flat=True))
    names.update(event["actor_name"] for event in events if event.get("actor_name"))
    names.add("IA")
    return names


def _auto(provider, room, participant, body, message):
    """El chat único: deduce qué quiere la persona (`chat_intent`) y la IA solo cambia el diagrama con su permiso."""
    events = get_activity_store().recent(room, 200)
    pending = _state_get(_proposal_key(room, participant))
    if not (isinstance(pending, dict) and isinstance(pending.get("changes"), dict)):
        pending = None  # una propuesta guardada con otra forma no sirve: se trata como si no hubiera ninguna
    decision = classify(message, _known_names(room, events), has_pending=pending is not None)
    intent = decision["intent"]

    if intent == CONFIRM:
        return _confirm(room, participant, body, message, pending)
    if intent == DISCARD:
        return _discard(room, participant, message)
    if intent == HISTORY:
        return _history_reply(room, participant, message, decision["person"], events)
    if intent == REVIEW:
        return _tag(_review(provider, room, participant, body, message), REVIEW)
    if intent == CHANGE:
        if decision["direct"]:
            return _tag(_change(provider, room, participant, body, message), CHANGE)
        return _propose(provider, room, participant, body, message)
    return _tag(_answer(provider, room, participant, body, message), ASK)


def _tag(response, intent):
    """Agrega a la respuesta qué entendió el servidor, para que la interfaz sepa qué mostrar."""
    response.data["intent"] = intent
    return response


MODE_HANDLERS = {"auto": _auto, "ask": _answer, "change": _change, "review": _review}


@api_view(["POST"])
def ia_chat(request, room):
    participant = _participant_for(request, room)
    if participant is None:
        return _forbidden()

    body = request.data if hasattr(request.data, "get") else {}
    mode = body.get("mode", "ask")  # sin `mode` se conserva el comportamiento de siempre: preguntar
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
            return MODE_HANDLERS[mode](get_ai_provider(_state_get(_provider_key(room))), room, participant, body, message)
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


def _provider_change_allowed(room):
    """False si la sala ya cambió de modelo demasiadas veces en el último minuto; si no se puede consultar el tope, se deja pasar."""
    try:
        return get_rate_limiter().allow(f"ia-provider:{room}", PROVIDER_CHANGES_PER_MINUTE, 60)
    except Exception as exc:
        logger.warning("No se pudo consultar el tope de cambios de modelo (%s)", type(exc).__name__)
        return True


@api_view(["GET", "PUT"])
def room_ia_provider(request, room):
    """El modelo de IA de la sala (uno solo para todas las personas). GET lo dice y PUT lo cambia.

    La sala elige entre los modelos que este servidor tiene disponibles: en la nube (Gemini) o el local (Ollama). El cambio se avisa a la sala
    como una actividad, para que nadie se sorprenda con otro modelo.
    """
    participant = _participant_for(request, room)
    if participant is None:
        return _forbidden()

    options = provider_options()
    current = _state_get(_provider_key(room)) or None

    if request.method == "PUT":
        body = request.data if hasattr(request.data, "get") else {}
        option = next((item for item in options if item["id"] == body.get("provider")), None)
        if option is None:
            return _bad_request("Modelo de IA no soportado.")
        if not option["available"]:
            return Response(
                {"error": "Ese modelo no está disponible en este servidor."},
                status=status.HTTP_409_CONFLICT,
            )
        if option["id"] != current:
            if not _provider_change_allowed(room):
                return Response(
                    {"error": "Cambiaste el modelo muchas veces seguidas. Espera un momento."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            get_room_state().set(_provider_key(room), option["id"], PROVIDER_TTL_SECONDS)
            event = get_activity_store().create(
                room=room,
                actor_id=participant.id,
                actor_name=participant.display_name,
                event_type="ia_provider",
                summary=f"cambió la IA de la sala a {option['label']}"[:255],
                data={"provider": option["id"]},
            )
            _publish_activity(room, event)
        current = option["id"]

    return Response({**describe_ai_provider(current), "options": options})


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
