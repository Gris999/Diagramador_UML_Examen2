"""Puertos de la actividad, la conversación con la IA y el turno de la sala (arquitectura hexagonal).

Las vistas dependen de estas interfaces y no de PostgreSQL, MongoDB o Redis: el adaptador concreto lo elige `collab.stores` con una variable de
entorno. Están descritos en el diseño del informe (sección 2.3.1, «Interfaces entre subsistemas»).
"""

from abc import ABC, abstractmethod

from channels.db import database_sync_to_async


class ActivityStore(ABC):
    """El registro de actividad de una sala: eventos que solo se agregan, con un `data` que cambia según el tipo.

    Cada evento es un diccionario con `id` (entero que crece), `room`, `actor` (id del participante o `None`), `actor_name`, `actor_kind`
    (`user` o `ia`), `type`, `target_id`, `summary`, `data` y `created_at` (ISO 8601). Los participantes son relacionales y viven siempre en
    PostgreSQL; lo que cambia de un adaptador a otro es dónde se guardan los eventos.
    """

    @abstractmethod
    def identify_now(self, room, token, name):
        """Registra a la persona en la sala (una vez por token) con su último nombre; devuelve el id del participante."""

    @abstractmethod
    def create(self, *, room, actor_id, actor_name, event_type, summary, data, target_id="", actor_kind="user"):
        """Guarda un evento y lo devuelve como lo muestra la API."""

    @abstractmethod
    def recent(self, room, limit):
        """Los últimos `limit` eventos de la sala, del más viejo al más nuevo."""

    @abstractmethod
    def since(self, room, after_id, limit):
        """Hasta `limit` eventos de la sala más nuevos que `after_id`, del más viejo al más nuevo."""

    @abstractmethod
    def get(self, room, event_id):
        """El evento de esa sala, o `None`."""

    @abstractmethod
    def update_data(self, room, event_id, mutate):
        """Cambia el `data` del evento de forma atómica: `mutate(data)` devuelve el `data` nuevo.

        Devuelve el evento ya cambiado. Si el evento no existe levanta `LookupError`; si `mutate` levanta una excepción el evento queda como estaba.
        """

    async def identify(self, room, token, name):
        """Lo que usa el canal en vivo (WebSocket), que no puede bloquear el ciclo de eventos."""
        return await database_sync_to_async(self.identify_now)(room, token, name)

    async def record(self, **event):
        return await database_sync_to_async(self.create)(**event)


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
