import json
import threading
import time

from .ports import RoomStateStore


class InMemoryRoomState(RoomStateStore):
    """Estado de la sala en la memoria del proceso: sirve para las pruebas y para un solo proceso; con varios procesos hace falta Redis."""

    _values = {}
    _lock = threading.Lock()

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._values.clear()

    def get(self, key):
        with self._lock:
            entry = self._values.get(key)
            if entry is None:
                return None
            if entry[1] <= time.monotonic():
                del self._values[key]
                return None
            return json.loads(entry[0])

    def set(self, key, value, ttl_seconds):
        with self._lock:
            self._values[key] = (json.dumps(value), time.monotonic() + ttl_seconds)

    def delete(self, key):
        with self._lock:
            self._values.pop(key, None)


class RedisRoomState(RoomStateStore):
    """Adaptador de Redis: una clave con vencimiento por dato, compartida por todos los procesos del servidor."""

    def __init__(self, client):
        self.client = client

    def get(self, key):
        value = self.client.get(f"room-state:{key}")
        if value is None:
            return None
        return json.loads(value.decode("utf-8") if isinstance(value, bytes) else value)

    def set(self, key, value, ttl_seconds):
        self.client.set(f"room-state:{key}", json.dumps(value), ex=ttl_seconds)

    def delete(self, key):
        self.client.delete(f"room-state:{key}")
