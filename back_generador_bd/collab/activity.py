from channels.db import database_sync_to_async
from django.utils import timezone

from .models import ActivityEvent, Participant


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


class ORMActivityStore:
    @database_sync_to_async
    def identify(self, room, token, name):
        participant, _ = Participant.objects.update_or_create(
            room=room,
            token=token,
            defaults={
                "display_name": name,
                "last_seen": timezone.now(),
            },
        )
        return participant.id

    @database_sync_to_async
    def record(
        self,
        *,
        room,
        actor_id,
        actor_name,
        event_type,
        target_id,
        summary,
        data,
        actor_kind="user",
    ):
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
