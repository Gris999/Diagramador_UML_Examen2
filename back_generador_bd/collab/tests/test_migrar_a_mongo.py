import uuid
from io import StringIO
from unittest import mock

import mongomock
from django.core.management import call_command
from django.test import TestCase

from collab import mongo
from collab.models import ActivityEvent, ChatMessage, Participant
from collab.mongo_stores import MongoActivityStore, MongoConversationStore


class MigrarAMongoTests(TestCase):
    room = "sala-historial"

    def setUp(self):
        self.database = mongomock.MongoClient()["pruebas"]
        patcher = mock.patch.object(mongo, "get_database", return_value=self.database)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.ana = Participant.objects.create(room=self.room, token=uuid.uuid4(), display_name="Ana")

    def run_command(self):
        salida = StringIO()
        call_command("migrar_a_mongo", stdout=salida)
        return salida.getvalue()

    def seed(self):
        ActivityEvent.objects.create(room=self.room, actor=self.ana, actor_name="Ana", type="add_class", target_id="c1", summary="añadió una clase", data={"t": "add_class"})
        revision = ActivityEvent.objects.create(
            room=self.room, actor_name="IA", actor_kind="ia", type="ia_review", summary="revisó", data={"findings": [{"text": "x", "prompt": "y"}]}
        )
        ChatMessage.objects.create(room=self.room, participant=self.ana, author_name="Ana", role="user", mode="ask", content="¿qué hay?")
        ChatMessage.objects.create(room=self.room, participant=self.ana, author_name="IA", role="ia", mode="ask", content="dos clases")
        # Guardado antes de que existiera `author_name`.
        ChatMessage.objects.create(room=self.room, participant=self.ana, role="user", mode="ask", content="viejo")
        return revision

    def test_the_existing_history_is_copied_with_the_same_ids_and_content(self):
        self.seed()

        self.run_command()

        eventos = MongoActivityStore(self.database).recent(self.room, 10)
        self.assertEqual([e["type"] for e in eventos], ["add_class", "ia_review"])
        self.assertEqual(eventos[0]["actor"], self.ana.id)
        self.assertEqual(eventos[1]["data"]["findings"], [{"text": "x", "prompt": "y"}])
        self.assertEqual([e["id"] for e in eventos], [e.id for e in ActivityEvent.objects.order_by("id")])
        mensajes = MongoConversationStore(self.database).history(self.room, 10)
        self.assertEqual([(m["author_name"], m["content"]) for m in mensajes], [("Ana", "¿qué hay?"), ("IA", "dos clases"), ("Ana", "viejo")])

    def test_running_it_twice_does_not_duplicate_anything(self):
        self.seed()

        self.run_command()
        self.run_command()

        self.assertEqual(len(MongoActivityStore(self.database).recent(self.room, 10)), 2)
        self.assertEqual(len(MongoConversationStore(self.database).history(self.room, 10)), 3)

    def test_what_is_saved_afterwards_continues_after_the_copied_ids(self):
        revision = self.seed()
        self.run_command()

        nuevo = MongoActivityStore(self.database).create(
            room=self.room, actor_id=None, actor_name="Beto", event_type="delete", summary="eliminó", data={}
        )

        self.assertGreater(nuevo["id"], revision.id)

    def test_an_event_already_changed_in_mongo_is_not_overwritten_by_the_old_copy(self):
        revision = self.seed()
        self.run_command()
        MongoActivityStore(self.database).update_data(self.room, revision.id, lambda data: {**data, "applied": [{"index": 0}]})

        self.run_command()

        self.assertEqual(MongoActivityStore(self.database).get(self.room, revision.id)["data"]["applied"], [{"index": 0}])

    def test_it_reports_how_much_was_copied(self):
        self.seed()

        salida = self.run_command()

        self.assertIn("2 eventos de actividad", salida)
        self.assertIn("3 mensajes", salida)

    def test_with_nothing_saved_it_says_so_and_changes_nothing(self):
        salida = self.run_command()

        self.assertIn("0 eventos de actividad", salida)
        self.assertEqual(self.database["activity_events"].count_documents({}), 0)
