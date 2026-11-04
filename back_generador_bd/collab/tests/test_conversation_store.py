import uuid
from types import SimpleNamespace

from django.test import TestCase

from collab.conversation import ORMConversationStore
from collab.models import ChatMessage, Participant


class ConversationStoreContract:
    """Lo que debe cumplir cualquier adaptador del puerto ConversationStore (PostgreSQL, MongoDB, en memoria)."""

    room = "sala-contrato"

    def make_store(self):
        raise NotImplementedError

    def make_participant(self, name="Ana"):
        raise NotImplementedError

    def test_a_room_without_messages_has_an_empty_history(self):
        self.assertEqual(self.make_store().history(self.room, 10), [])

    def test_an_exchange_stores_the_question_and_the_answer_with_their_authors(self):
        store = self.make_store()
        ana = self.make_participant("Ana")

        ids = store.append_exchange(self.room, ana, "ask", "¿Cuántas clases hay?", "Hay dos.")

        self.assertEqual(len(ids), 2)
        mensajes = store.history(self.room, 10)
        self.assertEqual(
            [(m["role"], m["author_name"], m["mode"], m["content"]) for m in mensajes],
            [("user", "Ana", "ask", "¿Cuántas clases hay?"), ("ia", "IA", "ask", "Hay dos.")],
        )
        self.assertTrue(all(isinstance(m["id"], int) for m in mensajes))
        self.assertTrue(all(m["created_at"] for m in mensajes))

    def test_the_conversation_is_shared_by_everyone_in_the_room(self):
        store = self.make_store()
        store.append_exchange(self.room, self.make_participant("Ana"), "ask", "pregunta de Ana", "respuesta 1")
        store.append_exchange(self.room, self.make_participant("Beto"), "ask", "pregunta de Beto", "respuesta 2")

        contenidos = [m["content"] for m in store.history(self.room, 10)]

        self.assertEqual(contenidos, ["pregunta de Ana", "respuesta 1", "pregunta de Beto", "respuesta 2"])

    def test_history_keeps_the_latest_messages_oldest_first(self):
        store = self.make_store()
        ana = self.make_participant("Ana")
        for numero in range(15):
            store.append_exchange(self.room, ana, "ask", f"pregunta {numero}", f"respuesta {numero}")

        contenidos = [m["content"] for m in store.history(self.room, 4)]

        self.assertEqual(contenidos, ["pregunta 13", "respuesta 13", "pregunta 14", "respuesta 14"])

    def test_rooms_do_not_see_each_others_messages(self):
        store = self.make_store()
        store.append_exchange("sala-a", self.make_participant("Ana"), "ask", "solo en A", "ok")

        self.assertEqual(store.history("sala-b", 10), [])

    def test_discarding_an_exchange_removes_only_that_exchange(self):
        store = self.make_store()
        ana = self.make_participant("Ana")
        store.append_exchange(self.room, ana, "ask", "se queda", "ok")
        ids = store.append_exchange(self.room, ana, "review", "se va", "ok")

        store.discard_exchange(self.room, ids)

        self.assertEqual([m["content"] for m in store.history(self.room, 10)], ["se queda", "ok"])

    def test_ids_grow_so_the_order_of_the_conversation_is_kept(self):
        store = self.make_store()
        ana = self.make_participant("Ana")
        primeros = store.append_exchange(self.room, ana, "ask", "uno", "ok")
        segundos = store.append_exchange(self.room, ana, "ask", "dos", "ok")

        self.assertLess(max(primeros), min(segundos))


class ORMConversationStoreTests(ConversationStoreContract, TestCase):
    def make_store(self):
        return ORMConversationStore()

    def make_participant(self, name="Ana"):
        return Participant.objects.create(room=self.room, token=uuid.uuid4(), display_name=name)

    def test_messages_saved_before_authors_were_stored_show_the_participant_name(self):
        ana = self.make_participant("Ana")
        ChatMessage.objects.create(room=self.room, participant=ana, role="user", content="viejo")
        ChatMessage.objects.create(room=self.room, participant=ana, role="ia", content="respuesta vieja")

        mensajes = ORMConversationStore().history(self.room, 10)

        self.assertEqual([m["author_name"] for m in mensajes], ["Ana", "IA"])

    def test_a_failure_in_the_middle_leaves_neither_message(self):
        ana = self.make_participant("Ana")
        with self.assertRaises(Exception):
            ORMConversationStore().append_exchange(self.room, ana, "ask", "x" * 10, None)

        self.assertEqual(ChatMessage.objects.count(), 0)
