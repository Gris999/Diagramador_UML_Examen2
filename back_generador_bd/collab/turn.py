import logging
import threading
import time

from .ports import TurnStore

logger = logging.getLogger(__name__)

# Los turnos de una sala viven en un conjunto ordenado de Redis: cada miembro es `id|nombre` y su puntaje es la hora en que vence, así que los
# turnos de quienes se desconectan desaparecen solos. Tomar un turno y devolverlo son guiones de Lua para que, aunque varios procesos del
# servidor pidan a la vez, nunca se atienda a más personas que los cupos de la sala ni a una misma persona dos veces.
_TAKE_SCRIPT = """
    local now = tonumber(ARGV[1])
    local slots = tonumber(ARGV[2])
    local id = ARGV[3]
    local expires = tonumber(ARGV[4])
    redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', now)
    local holders = redis.call('ZRANGE', KEYS[1], 0, -1)
    local mine = false
    for _, holder in ipairs(holders) do
        if string.sub(holder, 1, string.len(id) + 1) == id .. '|' then mine = true end
    end
    if mine or #holders >= slots then
        table.insert(holders, 1, 0)
        return holders
    end
    redis.call('ZADD', KEYS[1], expires, ARGV[5])
    redis.call('EXPIRE', KEYS[1], tonumber(ARGV[6]))
    return {1}
"""
# Se devuelve solo si quien lo pide es quien lo tiene.
_RELEASE_SCRIPT = """
    local holders = redis.call('ZRANGE', KEYS[1], 0, -1)
    for _, holder in ipairs(holders) do
        if string.sub(holder, 1, string.len(ARGV[1]) + 1) == ARGV[1] .. '|' then
            return redis.call('ZREM', KEYS[1], holder)
        end
    end
    return 0
"""
FREE_TEXT = "otra persona"


def join_names(names):
    """«Ana», «Ana y Beto» o «Ana, Beto y Carla»."""
    names = [name for name in names if name]
    if not names:
        return FREE_TEXT
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} y {names[-1]}"


class InMemoryTurnStore(TurnStore):
    """Turno en la memoria del proceso: sirve para las pruebas y para un solo proceso; con varios procesos hace falta Redis."""

    _turns = {}
    _lines = {}
    _lock = threading.Lock()

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._turns.clear()
            cls._lines.clear()

    def _live_line(self, room):
        now = time.monotonic()
        line = [entry for entry in self._lines.get(room, []) if entry["expires"] > now]
        self._lines[room] = line
        return line

    def _live(self, room):
        now = time.monotonic()
        turns = [turn for turn in self._turns.get(room, []) if turn["expires"] > now]
        self._turns[room] = turns
        return turns

    def take(self, room, holder_id, holder_name, ttl_seconds, slots=1):
        with self._lock:
            turns = self._live(room)
            if len(turns) >= slots or any(turn["id"] == holder_id for turn in turns):
                return False, join_names([turn["name"] for turn in turns])
            turns.append({"id": holder_id, "name": holder_name, "expires": time.monotonic() + ttl_seconds})
            return True, None

    def release(self, room, holder_id):
        with self._lock:
            self._turns[room] = [turn for turn in self._live(room) if turn["id"] != holder_id]

    def current(self, room):
        with self._lock:
            turns = self._live(room)
            return join_names([turn["name"] for turn in turns]) if turns else None

    def line_up(self, room, holder_id, holder_name, ttl_seconds):
        with self._lock:
            line = self._live_line(room)
            if not any(entry["id"] == holder_id for entry in line):
                line.append({"id": holder_id, "name": holder_name, "expires": time.monotonic() + ttl_seconds})

    def leave_line(self, room, holder_id):
        with self._lock:
            self._lines[room] = [entry for entry in self._live_line(room) if entry["id"] != holder_id]

    def place_in_line(self, room, holder_id):
        with self._lock:
            for place, entry in enumerate(self._live_line(room)):
                if entry["id"] == holder_id:
                    return place
            return None

    def waiting(self, room):
        with self._lock:
            return [entry["name"] for entry in self._live_line(room)]


class RedisTurnStore(TurnStore):
    """Adaptador de Redis: los turnos de cada sala con vencimiento, compartidos por todos los procesos del servidor."""

    def __init__(self, client):
        self.client = client

    @staticmethod
    def _key(room):
        return f"ia-slots:{room}"

    @staticmethod
    def _holder_name(value):
        text = value.decode("utf-8") if isinstance(value, bytes) else str(value)
        return text.split("|", 1)[1] if "|" in text else FREE_TEXT

    def take(self, room, holder_id, holder_name, ttl_seconds, slots=1):
        now = time.time()
        result = self.client.eval(
            _TAKE_SCRIPT, 1, self._key(room), now, max(1, int(slots)), str(holder_id), now + ttl_seconds, f"{holder_id}|{holder_name}", int(ttl_seconds) + 5
        )
        if int(result[0]) == 1:
            return True, None
        return False, join_names([self._holder_name(member) for member in result[1:]])

    def release(self, room, holder_id):
        self.client.eval(_RELEASE_SCRIPT, 1, self._key(room), str(holder_id))

    def current(self, room):
        members = self.client.zrangebyscore(self._key(room), time.time(), "+inf")
        return join_names([self._holder_name(member) for member in members]) if members else None

    # La fila de espera es un conjunto ordenado por la hora de llegada: `id|nombre` con la hora como puntaje.
    @staticmethod
    def _line_key(room):
        return f"ia-line:{room}"

    @staticmethod
    def _text(value):
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)

    def _line(self, room):
        return [self._text(member) for member in self.client.zrange(self._line_key(room), 0, -1)]

    def line_up(self, room, holder_id, holder_name, ttl_seconds):
        key = self._line_key(room)
        now = time.time()
        self.client.zremrangebyscore(key, "-inf", now - ttl_seconds)
        if not any(member.startswith(f"{holder_id}|") for member in self._line(room)):
            self.client.zadd(key, {f"{holder_id}|{holder_name}": now})
        self.client.expire(key, ttl_seconds)

    def leave_line(self, room, holder_id):
        key = self._line_key(room)
        for member in self._line(room):
            if member.startswith(f"{holder_id}|"):
                self.client.zrem(key, member)

    def place_in_line(self, room, holder_id):
        for place, member in enumerate(self._line(room)):
            if member.startswith(f"{holder_id}|"):
                return place
        return None

    def waiting(self, room):
        return [self._holder_name(member) for member in self._line(room)]
