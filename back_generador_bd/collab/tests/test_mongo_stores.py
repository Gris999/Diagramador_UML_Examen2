import uuid
from unittest import mock

import mongomock
from mongomock.collection import Collection
from django.test import TestCase, TransactionTestCase, override_settings

from collab import mongo, stores
from collab.activity import ORMActivityStore
from collab.conversation import ORMConversationStore
from collab.models import Participant
from collab.mongo_stores import MAX_UPDATE_ATTEMPTS, MongoActivityStore, MongoConversationStore, ensure_indexes
from collab.tests.test_activity_store import ActivityStoreContract, LiveActivityContract
from collab.tests.test_conversation_store import ConversationStoreContract


def fresh_database():
    return mongomock.MongoClient()["pruebas"]


class MongoActivityStoreTests(ActivityStoreContract, TestCase):
    def make_store(self):
        self.database = fresh_database()
        return MongoActivityStore(self.database)

    def test_events_are_documents_in_their_own_collection_and_not_rows(self):
        from collab.models import ActivityEvent

        evento = self.create(self.make_store(), summary="en mongo")

        self.assertEqual(self.database["activity_events"].find_one({"_id": evento["id"]})["summary"], "en mongo")
        self.assertEqual(ActivityEvent.objects.count(), 0)

    def test_a_change_made_by_someone_else_in_the_middle_is_not_lost(self):
        store = self.make_store()
        evento = self.create(store, event_type="ia_review", data={"applied": []})
        llamadas = []

        def mutate(data):
            llamadas.append(dict(data))
            if len(llamadas) == 1:
                # Otra persona guarda su cambio justo después de que este leyó el evento.
                self.database["activity_events"].update_one(
                    {"_id": evento["id"]}, {"$set": {"data.applied": [{"index": 0, "by": "Beto"}]}, "$inc": {"v": 1}}
                )
            return {**data, "applied": data["applied"] + [{"index": 1, "by": "Ana"}]}

        store.update_data(self.room, evento["id"], mutate)

        self.assertEqual(len(llamadas), 2)
        self.assertEqual(
            store.get(self.room, evento["id"])["data"]["applied"],
            [{"index": 0, "by": "Beto"}, {"index": 1, "by": "Ana"}],
        )

    def test_it_gives_up_when_the_event_never_stops_changing(self):
        store = self.make_store()
        evento = self.create(store, data={"n": 0})

        def mutate(data):
            self.database["activity_events"].update_one({"_id": evento["id"]}, {"$inc": {"v": 1}})
            return data

        with self.assertRaises(RuntimeError):
            store.update_data(self.room, evento["id"], mutate)

        self.assertGreaterEqual(MAX_UPDATE_ATTEMPTS, 2)

    def test_the_room_and_order_index_exists_for_the_queries_by_room(self):
        self.make_store()

        ensure_indexes(self.database)

        for coleccion in ("activity_events", "chat_messages"):
            indices = self.database[coleccion].index_information()
            self.assertTrue(any(info["key"] == [("room", 1), ("_id", 1)] for info in indices.values()), coleccion)


class MongoLiveActivityTests(LiveActivityContract, TransactionTestCase):
    def make_store(self):
        return MongoActivityStore(fresh_database())


class MongoConversationStoreTests(ConversationStoreContract, TestCase):
    def make_store(self):
        self.database = fresh_database()
        return MongoConversationStore(self.database)

    def make_participant(self, name="Ana"):
        return Participant.objects.create(room=self.room, token=uuid.uuid4(), display_name=name)

    def test_messages_are_documents_in_their_own_collection(self):
        store = self.make_store()
        store.append_exchange(self.room, self.make_participant("Ana"), "ask", "hola", "buenas")

        self.assertEqual(self.database["chat_messages"].count_documents({"room": self.room}), 2)

    def test_a_failure_in_the_middle_leaves_neither_message(self):
        store = self.make_store()
        guardar = Collection.insert_one
        llamadas = []

        def segunda_falla(coleccion, documento, *args, **kwargs):
            llamadas.append(documento)
            if len(llamadas) == 2:
                raise RuntimeError("se cayó Mongo")
            return guardar(coleccion, documento, *args, **kwargs)

        with mock.patch.object(Collection, "insert_one", autospec=True, side_effect=segunda_falla):
            with self.assertRaises(RuntimeError):
                store.append_exchange(self.room, self.make_participant("Ana"), "ask", "hola", "buenas")

        self.assertEqual(store.history(self.room, 10), [])


class StoreSelectionTests(TestCase):
    def test_postgres_is_the_default_for_both_ports(self):
        self.assertIsInstance(stores.get_activity_store(), ORMActivityStore)
        self.assertIsInstance(stores.get_conversation_store(), ORMConversationStore)

    @override_settings(ACTIVITY_STORE="mongo", CONVERSATION_STORE="mongo")
    def test_a_setting_chooses_mongo_for_each_port(self):
        with mock.patch.object(mongo, "get_database", return_value=fresh_database()):
            self.assertIsInstance(stores.get_activity_store(), MongoActivityStore)
            self.assertIsInstance(stores.get_conversation_store(), MongoConversationStore)

    @override_settings(ACTIVITY_STORE="mongo", CONVERSATION_STORE="postgres")
    def test_each_port_is_chosen_on_its_own(self):
        with mock.patch.object(mongo, "get_database", return_value=fresh_database()):
            self.assertIsInstance(stores.get_activity_store(), MongoActivityStore)
            self.assertIsInstance(stores.get_conversation_store(), ORMConversationStore)

    @override_settings(ACTIVITY_STORE="cassandra")
    def test_an_unknown_adapter_is_reported_instead_of_silently_using_another(self):
        with self.assertRaises(ValueError):
            stores.get_activity_store()


class MongoConnectionTests(TestCase):
    def setUp(self):
        mongo.get_client.cache_clear()
        mongo._indexed.clear()
        self.addCleanup(mongo.get_client.cache_clear)
        self.addCleanup(mongo._indexed.clear)

    @override_settings(MONGO_URL="mongodb://usuario:clave@mongo_db:27017", MONGO_DB="uml")
    def test_the_database_comes_from_the_server_settings(self):
        with mock.patch.object(mongo.pymongo, "MongoClient", return_value=mongomock.MongoClient()) as client:
            database = mongo.get_database()

        self.assertEqual(database.name, "uml")
        self.assertEqual(client.call_args.args[0], "mongodb://usuario:clave@mongo_db:27017")

    @override_settings(MONGO_URL="mongodb://caido:27017", MONGO_DB="uml")
    def test_a_server_that_is_down_does_not_stop_the_connection_but_the_indexes_are_retried_next_time(self):
        from pymongo.errors import ServerSelectionTimeoutError

        with mock.patch.object(mongo.pymongo, "MongoClient", return_value=mongomock.MongoClient()):
            with mock.patch("collab.mongo_stores.ensure_indexes", side_effect=ServerSelectionTimeoutError("sin servidor")) as ensure:
                mongo.get_database()
                mongo.get_database()

        self.assertEqual(ensure.call_count, 2)
