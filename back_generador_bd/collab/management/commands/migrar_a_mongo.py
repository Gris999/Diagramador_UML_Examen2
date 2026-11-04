from django.core.management.base import BaseCommand

from collab import mongo
from collab.models import ActivityEvent, ChatMessage
from collab.mongo_stores import import_activity, import_conversation


class Command(BaseCommand):
    help = (
        "Copia a MongoDB la actividad y la conversación con la IA que ya están en PostgreSQL, con los mismos identificadores. Se corre una sola "
        "vez antes de poner ACTIVITY_STORE y CONVERSATION_STORE en 'mongo'; se puede repetir sin duplicar ni pisar lo que Mongo ya cambió. "
        "PostgreSQL no se toca: queda como respaldo."
    )

    def handle(self, *args, **options):
        database = mongo.get_database()
        events = import_activity(database, ActivityEvent.objects.order_by("id").iterator())
        messages = import_conversation(database, ChatMessage.objects.select_related("participant").order_by("id").iterator())
        self.stdout.write(f"Copiados a MongoDB: {events} eventos de actividad y {messages} mensajes de la conversación.")
