from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import SimpleTestCase, override_settings

REDIS_LAYER = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("redis.test", 6379)]},
    }
}


class FakeRedis:
    """Cliente mínimo en memoria: lo justo para `scan_iter` y `delete`."""

    instances = []

    def __init__(self, keys=None, fail=False, **kwargs):
        self.kwargs = kwargs
        self.keys = set(keys or [])
        self.fail = fail
        FakeRedis.instances.append(self)

    @classmethod
    def seeded(cls, keys, fail=False):
        return lambda **kwargs: cls(keys=keys, fail=fail, **kwargs)

    def scan_iter(self, match=None, count=None):
        if self.fail:
            raise ConnectionError("redis caído")
        import fnmatch

        return iter([k for k in sorted(self.keys) if fnmatch.fnmatch(k, match)])

    def delete(self, *keys):
        self.keys.difference_update(keys)


class ClearRoomStateTests(SimpleTestCase):
    """Tras reiniciar el servidor no puede quedar nadie "conectado" en las salas."""

    def setUp(self):
        FakeRedis.instances.clear()

    def run_command(self, factory):
        out = StringIO()
        with mock.patch(
            "collab.management.commands.clear_room_state.redis.Redis", side_effect=factory
        ):
            call_command("clear_room_state", stdout=out)
        return out.getvalue()

    @override_settings(CHANNEL_LAYERS=REDIS_LAYER)
    def test_removes_the_room_groups_viewers_and_identities_but_nothing_else(self):
        keys = [
            "asgi:group:canvas_sala-1",
            "asgi:group:canvas_sala-1:identities",
            "asgi:group:canvas_sala-1_viewers",
            "asgi:group:canvas_otra",
            "asgi:group:otro_servicio",
            "asgi:specific.AbC!xyz",
            "cache:algo",
        ]
        output = self.run_command(FakeRedis.seeded(keys))

        remaining = FakeRedis.instances[0].keys
        self.assertEqual(
            remaining,
            {"asgi:group:otro_servicio", "asgi:specific.AbC!xyz", "cache:algo"},
        )
        self.assertIn("4", output)

    @override_settings(CHANNEL_LAYERS=REDIS_LAYER)
    def test_connects_to_the_configured_host_and_port(self):
        self.run_command(FakeRedis.seeded([]))

        self.assertEqual(FakeRedis.instances[0].kwargs, {"host": "redis.test", "port": 6379})

    @override_settings(CHANNEL_LAYERS={
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [("redis.test", 6379)], "prefix": "miapp"},
        }
    })
    def test_respects_a_custom_key_prefix(self):
        keys = ["miapp:group:canvas_x", "asgi:group:canvas_y"]
        self.run_command(FakeRedis.seeded(keys))

        self.assertEqual(FakeRedis.instances[0].keys, {"asgi:group:canvas_y"})

    @override_settings(CHANNEL_LAYERS=REDIS_LAYER)
    def test_an_unreachable_redis_never_stops_the_server_from_starting(self):
        output = self.run_command(FakeRedis.seeded(["asgi:group:canvas_x"], fail=True))

        self.assertIn("No se pudo limpiar", output)

    @override_settings(CHANNEL_LAYERS={
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    })
    def test_does_nothing_with_the_in_memory_layer(self):
        with mock.patch("collab.management.commands.clear_room_state.redis.Redis") as client:
            call_command("clear_room_state", stdout=StringIO())

        client.assert_not_called()
