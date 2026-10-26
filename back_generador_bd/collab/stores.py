"""Elige el adaptador de cada puerto según los ajustes del servidor (variables de entorno)."""

from functools import lru_cache

from django.conf import settings

from .activity import ORMActivityStore
from .conversation import ORMConversationStore
from .turn import InMemoryTurnStore, RedisTurnStore


def get_activity_store():
    return ORMActivityStore()


def get_conversation_store():
    return ORMConversationStore()


@lru_cache(maxsize=1)
def _redis_client():
    import redis

    return redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, socket_timeout=2, socket_connect_timeout=2)


def get_turn_store():
    if settings.TURN_STORE == "memory":
        return InMemoryTurnStore()
    return RedisTurnStore(_redis_client())
