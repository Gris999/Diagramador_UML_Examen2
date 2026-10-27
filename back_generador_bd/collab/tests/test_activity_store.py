import uuid

from asgiref.sync import async_to_sync
from django.test import TestCase, TransactionTestCase

from collab.activity import ORMActivityStore
from collab.models import ActivityEvent, Participant


class ActivityStoreContract:
    """Lo que debe cumplir cualquier adaptador del puerto ActivityStore (PostgreSQL, MongoDB)."""

    room = "sala-actividad"

    def make_store(self):
        raise NotImplementedError

    def make_participant(self, name="Ana"):
        return Participant.objects.create(room=self.room, token=uuid.uuid4(), display_name=name)

    def create(self, store, summary="añadió una clase", room=None, actor=None, actor_name="Ana", event_type="add_class", data=None, kind="user"):
        return store.create(
            room=room or self.room,
            actor_id=actor.id if actor else None,
            actor_name=actor_name,
            event_type=event_type,
            target_id="c1",
            summary=summary,
            data={"t": event_type} if data is None else data,
            actor_kind=kind,
        )

    def test_create_returns_the_event_as_the_api_shows_it(self):
        store = self.make_store()
        ana = self.make_participant("Ana")

        event = self.create(store, actor=ana, data={"t": "add_class", "id": "c1"})

        self.assertEqual(
            {key: event[key] for key in ("room", "actor", "actor_name", "actor_kind", "type", "target_id", "summary", "data")},
            {"room": self.room, "actor": ana.id, "actor_name": "Ana", "actor_kind": "user", "type": "add_class", "target_id": "c1",
             "summary": "añadió una clase", "data": {"t": "add_class", "id": "c1"}},
        )
        self.assertIsInstance(event["id"], int)
        self.assertTrue(event["created_at"])

    def test_the_ai_can_be_the_author_of_an_event(self):
        event = self.create(self.make_store(), actor_name="IA", kind="ia", event_type="ia_review")

        self.assertEqual((event["actor_name"], event["actor_kind"], event["type"]), ("IA", "ia", "ia_review"))

    def test_recent_returns_the_latest_events_of_the_room_oldest_first(self):
        store = self.make_store()
        for numero in range(12):
            self.create(store, summary=f"evento {numero}")
        self.create(store, summary="de otra sala", room="otra-sala")

        resumenes = [e["summary"] for e in store.recent(self.room, 5)]

        self.assertEqual(resumenes, [f"evento {n}" for n in range(7, 12)])

    def test_since_returns_only_what_is_newer_than_the_last_known_event_in_order(self):
        store = self.make_store()
        primero = self.create(store, summary="uno")
        self.create(store, summary="dos")
        self.create(store, summary="tres")

        resumenes = [e["summary"] for e in store.since(self.room, primero["id"], 10)]

        self.assertEqual(resumenes, ["dos", "tres"])
        self.assertEqual([e["summary"] for e in store.since(self.room, primero["id"], 1)], ["dos"])

    def test_get_finds_an_event_of_that_room_only(self):
        store = self.make_store()
        evento = self.create(store, summary="mío")

        self.assertEqual(store.get(self.room, evento["id"])["summary"], "mío")
        self.assertIsNone(store.get("otra-sala", evento["id"]))
        self.assertIsNone(store.get(self.room, evento["id"] + 1000))

    def test_ids_grow_so_the_order_of_the_activity_is_kept(self):
        store = self.make_store()
        a = self.create(store, summary="a")
        b = self.create(store, summary="b")

        self.assertLess(a["id"], b["id"])

    def test_update_data_applies_the_change_and_returns_the_event(self):
        store = self.make_store()
        evento = self.create(store, event_type="ia_review", data={"findings": [{"text": "x"}], "applied": []})

        actualizado = store.update_data(self.room, evento["id"], lambda data: {**data, "applied": [{"index": 0}]})

        self.assertEqual(actualizado["data"]["applied"], [{"index": 0}])
        self.assertEqual(store.get(self.room, evento["id"])["data"]["applied"], [{"index": 0}])
        self.assertEqual(store.get(self.room, evento["id"])["data"]["findings"], [{"text": "x"}])

    def test_update_data_of_a_missing_event_is_reported(self):
        with self.assertRaises(LookupError):
            self.make_store().update_data(self.room, 999999, lambda data: data)

    def test_update_data_that_refuses_leaves_the_event_as_it_was(self):
        store = self.make_store()
        evento = self.create(store, data={"estado": "libre"})

        def rechaza(data):
            raise ValueError("ya tomada")

        with self.assertRaises(ValueError):
            store.update_data(self.room, evento["id"], rechaza)

        self.assertEqual(store.get(self.room, evento["id"])["data"], {"estado": "libre"})


class LiveActivityContract:
    """Lo que usa el canal en vivo (WebSocket): las versiones asíncronas, que cierran las conexiones viejas y por eso no pueden correr dentro de la
    transacción de un `TestCase`."""

    room = "sala-actividad"

    def make_store(self):
        raise NotImplementedError

    def test_identify_registers_a_person_once_per_room_and_keeps_the_latest_name(self):
        store = self.make_store()
        token = str(uuid.uuid4())

        primero = async_to_sync(store.identify)(self.room, token, "Ana")
        segundo = async_to_sync(store.identify)(self.room, token, "Ana María")

        self.assertEqual(primero, segundo)
        self.assertEqual(Participant.objects.get(id=primero).display_name, "Ana María")

    def test_the_async_record_used_by_the_websocket_matches_create(self):
        store = self.make_store()

        evento = async_to_sync(store.record)(
            room=self.room, actor_id=None, actor_name="Ana", event_type="delete", target_id="c9", summary="eliminó un elemento", data={"t": "delete"},
        )

        self.assertEqual(store.get(self.room, evento["id"])["summary"], "eliminó un elemento")


class ORMActivityStoreTests(ActivityStoreContract, TestCase):
    def make_store(self):
        return ORMActivityStore()

    def test_events_are_kept_in_the_relational_table(self):
        self.create(self.make_store(), summary="en postgres")

        self.assertEqual(ActivityEvent.objects.filter(room=self.room).count(), 1)


class ORMLiveActivityTests(LiveActivityContract, TransactionTestCase):
    def make_store(self):
        return ORMActivityStore()
