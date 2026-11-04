from django.db import transaction

from .models import ChatMessage
from .ports import ConversationStore

IA_AUTHOR = "IA"


def serialize_message(message):
    """Mensaje del chat como lo entrega la API y como lo lee el contexto de la IA."""
    if message.role == ChatMessage.ROLE_IA:
        author = IA_AUTHOR
    else:
        # Los mensajes guardados antes de que existiera `author_name` toman el nombre del participante.
        author = message.author_name or message.participant.display_name
    return {
        "id": message.id,
        "role": message.role,
        "mode": message.mode,
        "content": message.content,
        "author_name": author,
        "created_at": message.created_at.isoformat(),
    }


class ORMConversationStore(ConversationStore):
    """Adaptador de PostgreSQL (Django ORM): la conversación de la sala, sin filtrar por quién preguntó."""

    def history(self, room, limit):
        rows = ChatMessage.objects.filter(room=room).select_related("participant").order_by("-id")[:limit]
        return [serialize_message(message) for message in reversed(list(rows))]

    def append_exchange(self, room, participant, mode, message, reply):
        with transaction.atomic():
            asked = ChatMessage.objects.create(
                room=room,
                participant=participant,
                author_name=participant.display_name,
                role=ChatMessage.ROLE_USER,
                mode=mode,
                content=message,
            )
            answered = ChatMessage.objects.create(
                room=room,
                participant=participant,
                author_name=IA_AUTHOR,
                role=ChatMessage.ROLE_IA,
                mode=mode,
                content=reply,
            )
        return [asked.id, answered.id]

    def discard_exchange(self, room, ids):
        ChatMessage.objects.filter(room=room, id__in=ids).delete()
