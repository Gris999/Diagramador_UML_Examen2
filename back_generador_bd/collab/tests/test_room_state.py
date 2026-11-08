import time
from unittest import mock

from django.test import SimpleTestCase, override_settings

from collab.room_state import InMemoryRoomState, RedisRoomState
from collab.stores import get_room_state


class RoomStateContract:
    """Lo que debe cumplir cualquier adaptador del puerto RoomStateStore: datos JSON pasajeros por clave."""

    def make_store(self):
        raise NotImplementedError

    def test_a_value_comes_back_as_it_was_saved(self):
        store = self.make_store()

        store.set("clave", {"changes": {"classes": [{"name": "Ñandú"}]}, "n": 3}, 60)

        self.assertEqual(store.get("clave"), {"changes": {"classes": [{"name": "Ñandú"}]}, "n": 3})

    def test_a_key_that_was_never_saved_is_none(self):
        self.assertIsNone(self.make_store().get("nada"))

    def test_saving_again_replaces_the_value(self):
        store = self.make_store()
        store.set("clave", "gemini", 60)
        store.set("clave", "ollama", 60)

        self.assertEqual(store.get("clave"), "ollama")

    def test_delete_removes_the_value_and_is_harmless_when_there_is_none(self):
        store = self.make_store()
        store.set("clave", 1, 60)

        store.delete("clave")
        store.delete("clave")

        self.assertIsNone(store.get("clave"))

    def test_keys_do_not_mix(self):
        store = self.make_store()
        store.set("sala-a", "uno", 60)
        store.set("sala-b", "dos", 60)

        self.assertEqual((store.get("sala-a"), store.get("sala-b")), ("uno", "dos"))


class InMemoryRoomStateTests(RoomStateContract, SimpleTestCase):
    def setUp(self):
        InMemoryRoomState.reset()

    def make_store(self):
        return InMemoryRoomState()

    def test_a_value_expires_by_itself(self):
        store = self.make_store()
        store.set("clave", "x", 10)

        with mock.patch("collab.room_state.time.monotonic", return_value=time.monotonic() + 11):
            self.assertIsNone(store.get("clave"))


class FakeRedis:
    """Lo mínimo de Redis que usa el adaptador: guarda bytes y recuerda el vencimiento pedido."""

    def __init__(self):
        self.values = {}
        self.expirations = {}

    def set(self, key, value, ex=None):
        self.values[key] = value.encode("utf-8")
        self.expirations[key] = ex

    def get(self, key):
        return self.values.get(key)

    def delete(self, key):
        self.values.pop(key, None)


class RedisRoomStateTests(RoomStateContract, SimpleTestCase):
    def make_store(self):
        self.redis = FakeRedis()
        return RedisRoomState(self.redis)

    def test_each_value_is_saved_with_its_expiration(self):
        store = self.make_store()

        store.set("clave", "x", 600)

        self.assertEqual(list(self.redis.expirations.values()), [600])


class RoomStateChoiceTests(SimpleTestCase):
    @override_settings(TURN_STORE="memory")
    def test_it_follows_the_turn_adapter_setting(self):
        self.assertIsInstance(get_room_state(), InMemoryRoomState)

    @override_settings(TURN_STORE="redis")
    def test_redis_is_used_when_the_turn_lives_in_redis(self):
        with mock.patch("collab.stores._redis_client", return_value=FakeRedis()):
            self.assertIsInstance(get_room_state(), RedisRoomState)
