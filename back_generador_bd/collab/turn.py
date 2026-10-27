import logging
import threading
import time

from .ports import TurnStore

logger = logging.getLogger(__name__)

# El turno se guarda en una sola clave, `id|nombre`, para que quien lo tiene y su nombre nunca queden desfasados.
# Se devuelve solo si quien lo pide es quien lo tiene: compara el identificador y borra en un solo paso.
_RELEASE_SCRIPT = """
    local value = redis.call('GET', KEYS[1])
    if value and string.sub(value, 1, string.len(ARGV[1]) + 1) == ARGV[1] .. '|' then
        return redis.call('DEL', KEYS[1])
    end
    return 0
"""


class InMemoryTurnStore(TurnStore):
    """Turno en la memoria del proceso: sirve para las pruebas y para un solo proceso; con varios procesos hace falta Redis."""

    _turns = {}
    _lock = threading.Lock()

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._turns.clear()

    def _live(self, room):
        turn = self._turns.get(room)
        if turn and turn["expires"] <= time.monotonic():
            del self._turns[room]
            return None
        return turn

    def take(self, room, holder_id, holder_name, ttl_seconds):
        with self._lock:
            turn = self._live(room)
            if turn:
                return False, turn["name"]
            self._turns[room] = {"id": holder_id, "name": holder_name, "expires": time.monotonic() + ttl_seconds}
            return True, None

    def release(self, room, holder_id):
        with self._lock:
            turn = self._live(room)
            if turn and turn["id"] == holder_id:
                del self._turns[room]

    def current(self, room):
        with self._lock:
            turn = self._live(room)
            return turn["name"] if turn else None


class RedisTurnStore(TurnStore):
    """Adaptador de Redis: un cerrojo por sala con vencimiento, compartido por todos los procesos del servidor."""

    def __init__(self, client):
        self.client = client

    @staticmethod
    def _key(room):
        return f"ia-turn:{room}"

    @staticmethod
    def _holder_name(value):
        text = value.decode("utf-8") if isinstance(value, bytes) else str(value)
        return text.split("|", 1)[1] if "|" in text else "otra persona"

    def take(self, room, holder_id, holder_name, ttl_seconds):
        if self.client.set(self._key(room), f"{holder_id}|{holder_name}", nx=True, ex=ttl_seconds):
            return True, None
        value = self.client.get(self._key(room))
        return False, self._holder_name(value) if value is not None else "otra persona"

    def release(self, room, holder_id):
        self.client.eval(_RELEASE_SCRIPT, 1, self._key(room), str(holder_id))

    def current(self, room):
        value = self.client.get(self._key(room))
        return None if value is None else self._holder_name(value)
