from django.db import transaction
from django.utils import timezone

from .models import ActivityEvent, Participant
from .ports import ActivityStore


def serialize_activity_event(event):
    return {
        "id": event.id,
        "room": event.room,
        "actor": event.actor_id,
        "actor_name": event.actor_name,
        "actor_kind": event.actor_kind,
        "type": event.type,
        "target_id": event.target_id,
        "summary": event.summary,
        "data": event.data,
        "created_at": event.created_at.isoformat(),
    }


def register_participant(room, token, name):
    """Los participantes son relacionales: viven en PostgreSQL con cualquier adaptador de actividad."""
    participant, _ = Participant.objects.update_or_create(
        room=room,
        token=token,
        defaults={
            "display_name": name,
            "last_seen": timezone.now(),
        },
    )
    return participant.id


class ORMActivityStore(ActivityStore):
    """Adaptador de PostgreSQL (Django ORM)."""

    def identify_now(self, room, token, name):
        return register_participant(room, token, name)

    def create(self, *, room, actor_id, actor_name, event_type, summary, data, target_id="", actor_kind="user"):
        event = ActivityEvent.objects.create(
            room=room,
            actor_id=actor_id,
            actor_name=actor_name,
            actor_kind=actor_kind,
            type=event_type,
            target_id=target_id,
            summary=summary,
            data=data,
        )
        return serialize_activity_event(event)

    def recent(self, room, limit):
        rows = ActivityEvent.objects.filter(room=room).order_by("-id")[:limit]
        return [serialize_activity_event(event) for event in reversed(list(rows))]

    def since(self, room, after_id, limit):
        rows = ActivityEvent.objects.filter(room=room, id__gt=after_id).order_by("id")[:limit]
        return [serialize_activity_event(event) for event in rows]

    def get(self, room, event_id):
        event = ActivityEvent.objects.filter(room=room, id=event_id).first()
        return serialize_activity_event(event) if event else None

    def update_data(self, room, event_id, mutate):
        with transaction.atomic():
            event = ActivityEvent.objects.select_for_update().filter(room=room, id=event_id).first()
            if event is None:
                raise LookupError(f"No hay un evento {event_id} en la sala {room}.")
            event.data = mutate(event.data)
            event.save(update_fields=["data"])
        return serialize_activity_event(event)
