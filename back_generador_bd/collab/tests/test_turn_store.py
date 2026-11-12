from unittest import mock

from django.test import SimpleTestCase

from collab.turn import _RELEASE_SCRIPT, _TAKE_SCRIPT, InMemoryTurnStore, RedisTurnStore, join_names


class TurnStoreContract:
    """Lo que debe cumplir cualquier adaptador del puerto TurnStore: tantos pedidos a la vez por sala como cupos tenga, y uno por persona."""

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

    def test_a_room_with_several_slots_attends_that_many_people_at_once(self):
        store = self.make_store()

        self.assertTrue(store.take("sala-a", 1, "Ana", 130, 3)[0])
        self.assertTrue(store.take("sala-a", 2, "Beto", 130, 3)[0])
        self.assertTrue(store.take("sala-a", 3, "Carla", 130, 3)[0])
        tomado, quienes = store.take("sala-a", 4, "Dora", 130, 3)

        self.assertFalse(tomado)
        self.assertEqual(quienes, "Ana, Beto y Carla")
        self.assertEqual(store.current("sala-a"), "Ana, Beto y Carla")

    def test_a_person_never_holds_two_turns_even_with_free_slots(self):
        store = self.make_store()
        store.take("sala-a", 1, "Ana", 130, 3)

        tomado, quienes = store.take("sala-a", 1, "Ana", 130, 3)

        self.assertFalse(tomado)
        self.assertEqual(quienes, "Ana")

    def test_releasing_one_turn_frees_one_slot_and_keeps_the_others(self):
        store = self.make_store()
        store.take("sala-a", 1, "Ana", 130, 2)
        store.take("sala-a", 2, "Beto", 130, 2)

        store.release("sala-a", 1)

        self.assertEqual(store.current("sala-a"), "Beto")
        self.assertTrue(store.take("sala-a", 3, "Carla", 130, 2)[0])
        self.assertFalse(store.take("sala-a", 4, "Dora", 130, 2)[0])

    def test_the_slots_are_per_room(self):
        store = self.make_store()
        store.take("sala-a", 1, "Ana", 130, 1)

        self.assertTrue(store.take("sala-b", 2, "Beto", 130, 1)[0])


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


class JoinNamesTests(SimpleTestCase):
    def test_names_are_joined_the_way_a_person_would_say_them(self):
        self.assertEqual(join_names(["Ana"]), "Ana")
        self.assertEqual(join_names(["Ana", "Beto"]), "Ana y Beto")
        self.assertEqual(join_names(["Ana", "Beto", "Carla"]), "Ana, Beto y Carla")
        self.assertEqual(join_names([]), "otra persona")


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
    """Lo mínimo de un cliente de Redis que usa RedisTurnStore: conjuntos ordenados y los dos guiones de turno con la misma semántica que en Redis."""

    def __init__(self):
        self.values = {}

    # Conjunto ordenado (los turnos y la fila de espera): miembro -> puntaje.
    def zadd(self, key, mapping):
        self.values.setdefault(key, {}).update(mapping)

    def zrange(self, key, start, stop):
        members = self.values.get(key, {})
        return [member.encode() for member, _ in sorted(members.items(), key=lambda item: item[1])]

    def zrangebyscore(self, key, low, high):
        members = self.values.get(key, {})
        return [member.encode() for member, score in sorted(members.items(), key=lambda item: item[1]) if score >= float(low)]

    def zrem(self, key, member):
        self.values.get(key, {}).pop(member, None)

    def zremrangebyscore(self, key, low, high):
        members = self.values.get(key, {})
        for member in [m for m, score in members.items() if score <= high]:
            del members[member]

    def expire(self, key, seconds):
        return True

    def eval(self, script, numkeys, key, *args):
        members = self.values.setdefault(key, {})
        if script == _TAKE_SCRIPT:
            now, slots, holder_id, expires, member, _ttl = args
            for expired in [m for m, score in members.items() if score <= now]:
                del members[expired]
            holders = [m.encode() for m, _ in sorted(members.items(), key=lambda item: item[1])]
            if any(m.startswith(f"{holder_id}|") for m in members) or len(holders) >= slots:
                return [0, *holders]
            members[member] = expires
            return [1]
        if script == _RELEASE_SCRIPT:
            for member in [m for m in members if m.startswith(f"{args[0]}|")]:
                del members[member]
                return 1
            return 0
        raise AssertionError("guion de Redis que el doble no conoce")


class RedisTurnStoreTests(TurnStoreContract, SimpleTestCase):
    def make_store(self):
        return RedisTurnStore(FakeRedis())
