"""Conexión a MongoDB. Solo se usa si algún puerto se configura con el adaptador `mongo` (ver `collab.stores`)."""

import logging
from functools import lru_cache

import pymongo
from django.conf import settings

logger = logging.getLogger(__name__)

# Bases en las que ya se crearon los índices en este proceso: crearlos es una ida y vuelta al servidor y no hace falta repetirla por conexión.
_indexed = set()


@lru_cache(maxsize=1)
def get_client():
    # `tz_aware`: las fechas vuelven con zona horaria, como las que entrega PostgreSQL.
    return pymongo.MongoClient(settings.MONGO_URL, tz_aware=True, serverSelectionTimeoutMS=3000)


def get_database():
    from .mongo_stores import ensure_indexes

    database = get_client()[settings.MONGO_DB]
    key = (settings.MONGO_URL, settings.MONGO_DB)
    if key not in _indexed:
        try:
            ensure_indexes(database)
            _indexed.add(key)
        except pymongo.errors.PyMongoError as exc:
            # Sin servidor no se puede crear, pero tampoco hay que tumbar la conexión: cada operación informa su propio error.
            logger.warning("No se pudieron crear los índices de MongoDB (%s)", type(exc).__name__)
    return database
