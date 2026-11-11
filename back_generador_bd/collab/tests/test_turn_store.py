from unittest import mock

from django.test import SimpleTestCase

from collab.turn import InMemoryTurnStore, RedisTurnStore


class TurnStoreContract:
    """Lo que debe cumplir cualquier adaptador del puerto TurnStore: un solo pedido a la IA a la vez por sala."""

    def make_store(self):
        raise NotImplementedError

    def test_the_first_request_in_a_room_gets_the_turn(self):
        store = self.make_store()

        tomado, quien = store.take("sala-a", 1, "Ana", 130)

        self.assertTrue(tomado)
        self.assertIsNone(quien)

    def test_a_second_request_in_the_same_room_waits_and_learns_who_has_the_turn(self):
        store = self.make_store()
        store.take("sala-a", 1, "Ana", 130)

        tomado, quien = store.take("sala-a", 2, "Beto", 130)

        self.assertFalse(tomado)
        self.assertEqual(quien, "Ana")
        self.assertEqual(store.current("sala-a"), "Ana")

    def test_rooms_have_their_own_turn(self):
        store = self.make_store()
        store.take("sala-a", 1, "Ana", 130)

        self.assertTrue(store.take("sala-b", 2, "Beto", 130)[0])

    def test_releasing_the_turn_lets_the_next_request_in(self):
        store = self.make_store()
        store.take("sala-a", 1, "Ana", 130)

        store.release("sala-a", 1)

        self.assertIsNone(store.current("sala-a"))
        self.assertTrue(store.take("sala-a", 2, "Beto", 130)[0])

    def test_only_the_holder_can_release_the_turn(self):
        store = self.make_store()
        store.take("sala-a", 1, "Ana", 130)

        store.release("sala-a", 2)

        self.assertEqual(store.current("sala-a"), "Ana")

    def test_the_line_keeps_the_order_of_arrival(self):
        store = self.make_store()

        store.line_up("sala-a", 1, "Ana", 100)
        store.line_up("sala-a", 2, "Beto", 100)
        store.line_up("sala-a", 3, "Carla", 100)

        self.assertEqual([store.place_in_line("sala-a", n) for n in (1, 2, 3)], [0, 1, 2])
        self.assertEqual(store.waiting("sala-a"), ["Ana", "Beto", "Carla"])

    def test_lining_up_twice_keeps_the_place(self):
        store = self.make_store()
        store.line_up("sala-a", 1, "Ana", 100)
        store.line_up("sala-a", 2, "Beto", 100)

        store.line_up("sala-a", 1, "Ana", 100)

        self.assertEqual(store.place_in_line("sala-a", 1), 0)
        self.assertEqual(store.waiting("sala-a"), ["Ana", "Beto"])

    def test_leaving_the_line_moves_the_others_up(self):
        store = self.make_store()
        store.line_up("sala-a", 1, "Ana", 100)
        store.line_up("sala-a", 2, "Beto", 100)

        store.leave_line("sala-a", 1)

        self.assertIsNone(store.place_in_line("sala-a", 1))
        self.assertEqual(store.place_in_line("sala-a", 2), 0)

    def test_each_room_has_its_own_line(self):
        store = self.make_store()
        store.line_up("sala-a", 1, "Ana", 100)

        self.assertEqual(store.waiting("sala-b"), [])
        self.assertIsNone(store.place_in_line("sala-b", 1))


class InMemoryTurnStoreTests(TurnStoreContract, SimpleTestCase):
    def setUp(self):
        InMemoryTurnStore.reset()

    def make_store(self):
        return InMemoryTurnStore()

    def test_a_place_in_the_line_expires_by_itself(self):
        store = self.make_store()
        with mock.patch("collab.turn.time.monotonic", return_value=1000.0):
            store.line_up("sala-a", 1, "Ana", 90)
        with mock.patch("collab.turn.time.monotonic", return_value=1091.0):
            self.assertEqual(store.waiting("sala-a"), [])
            self.assertIsNone(store.place_in_line("sala-a", 1))

    def test_the_turn_expires_by_itself(self):
        store = self.make_store()
        with mock.patch("collab.turn.time.monotonic", return_value=1000.0):
            store.take("sala-a", 1, "Ana", 130)
        with mock.patch("collab.turn.time.monotonic", return_value=1131.0):
            self.assertIsNone(store.current("sala-a"))
            self.assertTrue(store.take("sala-a", 2, "Beto", 130)[0])


class FakeRedis:
    """Lo mínimo de un cliente de Redis que usa RedisTurnStore, con la semántica de SET NX EX y del guion de devolver el turno."""

    def __init__(self):
        self.values = {}

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return None
        self.values[key] = value.encode() if isinstance(value, str) else value
        return True

    def get(self, key):
        return self.values.get(key)

    # Conjunto ordenado (la fila de espera): miembro -> puntaje.
    def zadd(self, key, mapping):
        self.values.setdefault(key, {}).update(mapping)

    def zrange(self, key, start, stop):
        members = self.values.get(key, {})
        return [member.encode() for member, _ in sorted(members.items(), key=lambda item: item[1])]

    def zrem(self, key, member):
        self.values.get(key, {}).pop(member, None)

    def zremrangebyscore(self, key, low, high):
        members = self.values.get(key, {})
        for member in [m for m, score in members.items() if score <= high]:
            del members[member]

    def expire(self, key, seconds):
        return True

    def eval(self, script, numkeys, key, holder):
        value = self.values.get(key)
        if value is not None and value.decode().startswith(f"{holder}|"):
            del self.values[key]
            return 1
        return 0


class RedisTurnStoreTests(TurnStoreContract, SimpleTestCase):
    def make_store(self):
        return RedisTurnStore(FakeRedis())
