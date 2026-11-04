"""Adaptadores de MongoDB de los puertos `ActivityStore` y `ConversationStore`.

La actividad y la conversación son documentos que solo se agregan, con un `data` que cambia según el tipo y que se consultan por sala y orden:
encaje de una base documental. Los participantes siguen siendo relacionales (PostgreSQL). Los identificadores siguen siendo enteros que crecen,
porque la API y el navegador los usan: salen de la colección `counters` con un `$inc` atómico.
"""

from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, ReturnDocument

from .activity import register_participant
from .conversation import IA_AUTHOR, serialize_message
from .ports import ActivityStore, ConversationStore

# Cuántas veces se reintenta un cambio que otra persona pisó entre la lectura y la escritura.
MAX_UPDATE_ATTEMPTS = 5


def ensure_indexes(database):
    """Las consultas de la API son siempre por sala y orden de identificador."""
    for collection in ("activity_events", "chat_messages"):
        database[collection].create_index([("room", ASCENDING), ("_id", ASCENDING)])


def _next_id(database, name):
    counter = database["counters"].find_one_and_update(
        {"_id": name}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return counter["seq"]


def _iso(moment):
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.isoformat()


def _serialize_event(document):
    return {
        "id": document["_id"],
        "room": document["room"],
        "actor": document["actor"],
        "actor_name": document["actor_name"],
        "actor_kind": document["actor_kind"],
        "type": document["type"],
        "target_id": document["target_id"],
        "summary": document["summary"],
        "data": document["data"],
        "created_at": _iso(document["created_at"]),
    }


class MongoActivityStore(ActivityStore):
    """Adaptador de MongoDB: colección `activity_events`, un documento por evento."""

    def __init__(self, database):
        self.database = database
        self.events = database["activity_events"]

    def identify_now(self, room, token, name):
        return register_participant(room, token, name)

    def create(self, *, room, actor_id, actor_name, event_type, summary, data, target_id="", actor_kind="user"):
        document = {
            "_id": _next_id(self.database, "activity_events"),
            "room": room,
            "actor": actor_id,
            "actor_name": actor_name,
            "actor_kind": actor_kind,
            "type": event_type,
            "target_id": target_id,
            "summary": summary,
            "data": data,
            "created_at": datetime.now(timezone.utc),
            "v": 0,
        }
        self.events.insert_one(document)
        return _serialize_event(document)

    def recent(self, room, limit):
        rows = self.events.find({"room": room}).sort("_id", DESCENDING).limit(limit)
        return [_serialize_event(document) for document in reversed(list(rows))]

    def since(self, room, after_id, limit):
        rows = self.events.find({"room": room, "_id": {"$gt": after_id}}).sort("_id", ASCENDING).limit(limit)
        return [_serialize_event(document) for document in rows]

    def get(self, room, event_id):
        document = self.events.find_one({"_id": event_id, "room": room})
        return _serialize_event(document) if document else None

    def update_data(self, room, event_id, mutate):
        """Escribe solo si nadie cambió el evento desde que se leyó (campo `v`); si lo cambiaron, vuelve a leer y a aplicar `mutate`."""
        for _ in range(MAX_UPDATE_ATTEMPTS):
            document = self.events.find_one({"_id": event_id, "room": room})
            if document is None:
                raise LookupError(f"No hay un evento {event_id} en la sala {room}.")
            data = mutate(document["data"])
            written = self.events.find_one_and_update(
                {"_id": event_id, "v": document["v"]},
                {"$set": {"data": data}, "$inc": {"v": 1}},
                return_document=ReturnDocument.AFTER,
            )
            if written is not None:
                return _serialize_event(written)
        raise RuntimeError(f"El evento {event_id} cambió {MAX_UPDATE_ATTEMPTS} veces mientras se guardaba.")


class MongoConversationStore(ConversationStore):
    """Adaptador de MongoDB: colección `chat_messages`, un documento por mensaje."""

    def __init__(self, database):
        self.database = database
        self.messages = database["chat_messages"]

    def history(self, room, limit):
        rows = self.messages.find({"room": room}).sort("_id", DESCENDING).limit(limit)
        return [self._serialize(document) for document in reversed(list(rows))]

    def append_exchange(self, room, participant, mode, message, reply):
        asked = self._document(room, participant, participant.display_name, "user", mode, message)
        answered = self._document(room, participant, IA_AUTHOR, "ia", mode, reply)
        self.messages.insert_one(asked)
        try:
            self.messages.insert_one(answered)
        except Exception:
            # MongoDB no ofrece una transacción entre documentos aquí: si falla la segunda, se retira la primera.
            self.messages.delete_one({"_id": asked["_id"]})
            raise
        return [asked["_id"], answered["_id"]]

    def discard_exchange(self, room, ids):
        self.messages.delete_many({"room": room, "_id": {"$in": list(ids)}})

    def _document(self, room, participant, author, role, mode, content):
        return {
            "_id": _next_id(self.database, "chat_messages"),
            "room": room,
            "participant": participant.id,
            "author_name": author,
            "role": role,
            "mode": mode,
            "content": content,
            "created_at": datetime.now(timezone.utc),
        }

    @staticmethod
    def _serialize(document):
        return {
            "id": document["_id"],
            "role": document["role"],
            "mode": document["mode"],
            "content": document["content"],
            "author_name": document["author_name"],
            "created_at": _iso(document["created_at"]),
        }


def _keep_counter_ahead(database, name, last_id):
    database["counters"].update_one({"_id": name}, {"$max": {"seq": last_id}}, upsert=True)


def import_activity(database, rows):
    """Copia eventos de PostgreSQL con su mismo id. Lo que ya existe en Mongo no se pisa: ahí pudo haber cambiado después."""
    count = 0
    last_id = 0
    for event in rows:
        document = {
            "room": event.room,
            "actor": event.actor_id,
            "actor_name": event.actor_name,
            "actor_kind": event.actor_kind,
            "type": event.type,
            "target_id": event.target_id,
            "summary": event.summary,
            "data": event.data,
            "created_at": event.created_at,
            "v": 0,
        }
        database["activity_events"].update_one({"_id": event.id}, {"$setOnInsert": document}, upsert=True)
        count += 1
        last_id = max(last_id, event.id)
    if count:
        _keep_counter_ahead(database, "activity_events", last_id)
    return count


def import_conversation(database, rows):
    """Copia mensajes de PostgreSQL con su mismo id; los guardados antes de `author_name` toman el nombre del participante."""
    count = 0
    last_id = 0
    for message in rows:
        document = {
            "room": message.room,
            "participant": message.participant_id,
            "author_name": serialize_message(message)["author_name"],
            "role": message.role,
            "mode": message.mode,
            "content": message.content,
            "created_at": message.created_at,
        }
        database["chat_messages"].update_one({"_id": message.id}, {"$setOnInsert": document}, upsert=True)
        count += 1
        last_id = max(last_id, message.id)
    if count:
        _keep_counter_ahead(database, "chat_messages", last_id)
    return count
