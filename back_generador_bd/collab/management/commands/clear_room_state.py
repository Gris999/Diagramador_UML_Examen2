import redis
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Borra de Redis el estado de las salas de colaboración (grupos de "
        "editores y observadores y nombres vivos). Se ejecuta al arrancar el "
        "servidor: al iniciar no hay ninguna conexión viva, así que todo lo que "
        "quedó de la ejecución anterior son participantes 'fantasma' (incluido "
        "un host que ya no existe) que de otro modo permanecerían hasta que "
        "venza la expiración de los grupos."
    )

    def handle(self, *args, **options):
        config = settings.CHANNEL_LAYERS.get("default", {})
        if "RedisChannelLayer" not in config.get("BACKEND", ""):
            self.stdout.write("Sin Redis (capa en memoria): nada que limpiar.")
            return

        layer_config = config.get("CONFIG", {})
        prefix = layer_config.get("prefix", "asgi")
        pattern = f"{prefix}:group:canvas_*"
        deleted = 0

        try:
            for host in layer_config.get("hosts", []):
                client = self._client(host)
                keys = list(client.scan_iter(match=pattern, count=500))
                if keys:
                    client.delete(*keys)
                deleted += len(keys)
        except Exception as exc:
            # Un Redis caído no debe impedir que el servidor arranque.
            self.stdout.write(f"No se pudo limpiar el estado de las salas ({type(exc).__name__}).")
            return

        self.stdout.write(f"Estado de salas limpiado: {deleted} claves eliminadas.")

    @staticmethod
    def _client(host):
        if isinstance(host, str):
            return redis.Redis.from_url(host)
        if isinstance(host, dict):
            return redis.Redis(**host)
        return redis.Redis(host=host[0], port=host[1])
