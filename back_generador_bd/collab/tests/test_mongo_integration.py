"""Los mismos contratos de los adaptadores de MongoDB contra un servidor MongoDB real.

Se saltan si no hay servidor. Para correrlas:

    docker run -d --rm --name mongo_prueba -p 127.0.0.1:27018:27017 mongo:7
    MONGO_TEST_URL=mongodb://127.0.0.1:27018 back_generador_bd/.venv/bin/python back_generador_bd/manage.py test collab.tests.test_mongo_integration
"""

import os
import uuid
from unittest import skipUnless

import pymongo
from django.test import TestCase, TransactionTestCase

from collab.models import Participant
from collab.mongo_stores import MongoActivityStore, MongoConversationStore, ensure_indexes
from collab.tests.test_activity_store import ActivityStoreContract, LiveActivityContract
from collab.tests.test_conversation_store import ConversationStoreContract

MONGO_TEST_URL = os.environ.get("MONGO_TEST_URL")


class RealMongo:
    def make_database(self):
        client = pymongo.MongoClient(MONGO_TEST_URL, tz_aware=True, serverSelectionTimeoutMS=3000)
        self.addCleanup(client.close)
        name = f"prueba_{uuid.uuid4().hex[:12]}"
        self.addCleanup(client.drop_database, name)
        database = client[name]
        ensure_indexes(database)
        return database


@skipUnless(MONGO_TEST_URL, "MONGO_TEST_URL no está definida")
class RealMongoActivityStoreTests(RealMongo, ActivityStoreContract, TestCase):
    def make_store(self):
        self.database = self.make_database()
        return MongoActivityStore(self.database)


@skipUnless(MONGO_TEST_URL, "MONGO_TEST_URL no está definida")
class RealMongoLiveActivityTests(RealMongo, LiveActivityContract, TransactionTestCase):
    def make_store(self):
        return MongoActivityStore(self.make_database())


@skipUnless(MONGO_TEST_URL, "MONGO_TEST_URL no está definida")
class RealMongoConversationStoreTests(RealMongo, ConversationStoreContract, TestCase):
    def make_store(self):
        return MongoConversationStore(self.make_database())

    def make_participant(self, name="Ana"):
        return Participant.objects.create(room=self.room, token=uuid.uuid4(), display_name=name)


@skipUnless(MONGO_TEST_URL, "MONGO_TEST_URL no está definida")
class RealMongoConcurrencyTests(RealMongo, TestCase):
    def test_two_people_reserving_ideas_at_once_both_end_up_saved(self):
        from concurrent.futures import ThreadPoolExecutor

        store = MongoActivityStore(self.make_database())
        evento = store.create(room="sala", actor_id=None, actor_name="IA", actor_kind="ia", event_type="ia_review", summary="r", data={"applied": []})

        def reservar(indice):
            return store.update_data("sala", evento["id"], lambda data: {**data, "applied": data["applied"] + [{"index": indice}]})

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(reservar, range(4)))

        reservadas = sorted(entry["index"] for entry in store.get("sala", evento["id"])["data"]["applied"])
        self.assertEqual(reservadas, [0, 1, 2, 3])
