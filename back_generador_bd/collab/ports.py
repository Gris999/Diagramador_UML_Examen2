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
    def append_message(self, room, participant, mode, message):
        """Guarda un mensaje de `participant` dirigido a las personas de la sala (no a la IA); devuelve su identificador."""

    @abstractmethod
    def discard_exchange(self, room, ids):
        """Deshace un `append_exchange` cuando lo que debía guardarse con él no se pudo guardar."""


class TurnStore(ABC):
    """Los turnos de la IA de una sala: la IA atiende hasta `slots` pedidos a la vez (uno por persona), en orden de llegada, y cada turno vence solo si quien lo tiene se desconecta."""

    @abstractmethod
    def take(self, room, holder_id, holder_name, ttl_seconds, slots=1):
        """Intenta tomar un turno. Devuelve `(True, None)` si lo tomó o `(False, nombres)` con los nombres de quienes están siendo atendidos.

        Se atiende a lo más `slots` personas a la vez en la sala, y a cada persona de a un pedido: si ya tiene un turno, no toma otro.
        """

    @abstractmethod
    def release(self, room, holder_id):
        """Devuelve el turno; solo lo devuelve quien lo tiene."""

    @abstractmethod
    def current(self, room):
        """Nombres de quienes están siendo atendidos (unidos con «,» y «y»), o `None` si la IA está libre."""

    # La fila de espera: cuando todos los cupos de la IA están ocupados, los demás pedidos se anotan y se atienden en el orden en que llegaron, apenas queda un cupo libre.
    @abstractmethod
    def line_up(self, room, holder_id, holder_name, ttl_seconds):
        """Se anota al final de la fila de espera de la sala (si ya estaba, conserva su lugar). La anotación vence sola a los `ttl_seconds`."""

    @abstractmethod
    def leave_line(self, room, holder_id):
        """Sale de la fila: porque ya tomó el turno o porque dejó de esperar."""

    @abstractmethod
    def place_in_line(self, room, holder_id):
        """Su lugar en la fila (0 es el primero), o `None` si no está anotado."""

    @abstractmethod
    def waiting(self, room):
        """Los nombres de quienes esperan, en orden."""


class RoomStateStore(ABC):
    """Datos pequeños y pasajeros de una sala que todos los procesos del servidor deben ver igual (vencen solos).

    Guarda la propuesta de la IA que espera permiso y el modelo de IA elegido para la sala. Los valores son JSON.
    """

    @abstractmethod
    def get(self, key):
        """El valor guardado en `key`, o `None` si no hay o ya venció."""

    @abstractmethod
    def set(self, key, value, ttl_seconds):
        """Guarda `value` en `key` durante `ttl_seconds`."""

    @abstractmethod
    def delete(self, key):
        """Borra `key` si existe."""


class RateLimiter(ABC):
    """Tope de pedidos por clave: a lo más `limit` en cada ventana de `window_seconds` (protege el gasto de la IA)."""

    @abstractmethod
    def allow(self, key, limit, window_seconds):
        """Cuenta un pedido de `key`; devuelve `False` si ya se pasó del tope de la ventana actual."""
