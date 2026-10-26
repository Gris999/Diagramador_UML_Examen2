"""Elige el adaptador de cada puerto según los ajustes del servidor (variables de entorno)."""

from functools import lru_cache

from django.conf import settings

from .activity import ORMActivityStore
from .conversation import ORMConversationStore
from .turn import InMemoryTurnStore, RedisTurnStore


def _unknown(setting, value):
    return ValueError(f"{setting}={value!r} no es un adaptador conocido (postgres o mongo).")


def get_activity_store():
    if settings.ACTIVITY_STORE == "postgres":
        return ORMActivityStore()
    if settings.ACTIVITY_STORE == "mongo":
        from . import mongo
        from .mongo_stores import MongoActivityStore

        return MongoActivityStore(mongo.get_database())
    raise _unknown("ACTIVITY_STORE", settings.ACTIVITY_STORE)


def get_conversation_store():
    if settings.CONVERSATION_STORE == "postgres":
        return ORMConversationStore()
    if settings.CONVERSATION_STORE == "mongo":
        from . import mongo
        from .mongo_stores import MongoConversationStore

        return MongoConversationStore(mongo.get_database())
    raise _unknown("CONVERSATION_STORE", settings.CONVERSATION_STORE)


@lru_cache(maxsize=1)
def _redis_client():
    import redis

    return redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_timeout=2, socket_connect_timeout=2)


def get_turn_store():
    if settings.TURN_STORE == "memory":
        return InMemoryTurnStore()
    return RedisTurnStore(_redis_client())
