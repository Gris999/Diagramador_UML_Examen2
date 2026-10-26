"""Puertos de la conversación con la IA y del turno de la sala (arquitectura hexagonal).

Las vistas dependen de estas interfaces y no de PostgreSQL, MongoDB o Redis: el adaptador concreto lo elige `collab.stores` con una variable de
entorno. Están descritos en el diseño del informe (sección 2.3.1, «Interfaces entre subsistemas»).
"""

from abc import ABC, abstractmethod


class ConversationStore(ABC):
    """La conversación única de una sala con la IA: la ven y la alimentan todas las personas de la sala."""

    @abstractmethod
    def history(self, room, limit):
        """Los últimos `limit` mensajes de la sala, del más viejo al más nuevo.

        Cada mensaje es un diccionario con `id`, `role` (`user` o `ia`), `mode`, `content`, `author_name` y `created_at` (ISO 8601).
        """

    @abstractmethod
    def append_exchange(self, room, participant, mode, message, reply):
        """Guarda juntas la pregunta de `participant` y la respuesta de la IA; devuelve los identificadores de los dos mensajes."""

    @abstractmethod
    def discard_exchange(self, room, ids):
        """Deshace un `append_exchange` cuando lo que debía guardarse con él no se pudo guardar."""


class TurnStore(ABC):
    """El turno de la IA de una sala: atiende un pedido a la vez, y el turno vence solo si quien lo tiene se desconecta."""

    @abstractmethod
    def take(self, room, holder_id, holder_name, ttl_seconds):
        """Intenta tomar el turno. Devuelve `(True, None)` si lo tomó o `(False, nombre)` con el nombre de quien lo tiene."""

    @abstractmethod
    def release(self, room, holder_id):
        """Devuelve el turno; solo lo devuelve quien lo tiene."""

    @abstractmethod
    def current(self, room):
        """Nombre de quien tiene el turno, o `None`."""
