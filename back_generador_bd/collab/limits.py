import threading
import time

from .ports import RateLimiter


class InMemoryRateLimiter(RateLimiter):
    """Contadores en la memoria del proceso: sirven para las pruebas y para un solo proceso; con varios procesos hace falta Redis."""

    _counts = {}
    _lock = threading.Lock()

    @classmethod
    def reset(cls):
        with cls._lock:
            cls._counts.clear()

    def allow(self, key, limit, window_seconds):
        window = int(time.time() // window_seconds)
        with self._lock:
            # Las ventanas viejas ya no cuentan: se descartan para que el diccionario no crezca sin fin.
            for old in [k for k in self._counts if k[1] == window_seconds and k[2] < window]:
                del self._counts[old]
            counter = (key, window_seconds, window)
            self._counts[counter] = self._counts.get(counter, 0) + 1
            return self._counts[counter] <= limit


class RedisRateLimiter(RateLimiter):
    """Adaptador de Redis: una ventana fija por clave, compartida por todos los procesos del servidor."""

    def __init__(self, client):
        self.client = client

    def allow(self, key, limit, window_seconds):
        window = int(time.time() // window_seconds)
        name = f"rate:{key}:{window_seconds}:{window}"
        count = self.client.incr(name)
        if count == 1:
            # El contador vive un poco más que su ventana y desaparece solo.
            self.client.expire(name, window_seconds * 2)
        return count <= limit
