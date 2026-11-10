import uuid
from unittest import mock

from collab.limits import InMemoryRateLimiter
from collab.models import ChatMessage, Participant

from .test_ia_chat_api import ChatTestBase, FailingProvider


class ChatSalaTests(ChatTestBase):
    """El chat de la sala es de las personas: se hablan entre sí en vivo y solo le hablan a la IA cuando quieren."""

    def setUp(self):
        super().setUp()
        InMemoryRateLimiter.reset()
        self.addCleanup(InMemoryRateLimiter.reset)

    def say_url(self, room=None):
        return f"/api/rooms/{room or self.room}/chat/say/"

    def say(self, participant, message):
        return self.client.post(
            self.say_url(), {"message": message}, format="json", HTTP_X_PARTICIPANT_TOKEN=str(participant.token)
        )

    def chat_events(self):
        return [(group, message) for group, message in self.layer.sent if message.get("type") == "chat"]

    def test_a_message_between_people_is_stored_with_its_author_and_does_not_call_the_ai(self):
        response = self.say(self.ana, "Beto, ¿tú haces Libro?")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["message"]["author_name"], "Ana")
        self.assertEqual(response.data["message"]["role"], "user")
        self.assertEqual(response.data["message"]["mode"], "chat")
        self.assertEqual(self.provider.prompts, [])
        self.assertEqual(self.provider.change_calls, [])
        self.assertEqual(list(ChatMessage.objects.values_list("author_name", "mode", "content")), [("Ana", "chat", "Beto, ¿tú haces Libro?")])

    def test_everyone_in_the_room_reads_it_in_the_shared_conversation(self):
        self.say(self.ana, "Yo hago Autor")
        self.say(self.beto, "Yo hago Libro")

        history = self.own_history(self.ana).data["messages"]

        self.assertEqual([(m["author_name"], m["content"]) for m in history], [("Ana", "Yo hago Autor"), ("Beto", "Yo hago Libro")])

    def test_the_room_and_the_phone_views_are_told_live_with_the_message(self):
        response = self.say(self.ana, "hola equipo")

        events = self.chat_events()
        self.assertEqual([group for group, _ in events], [f"canvas_{self.room}", f"canvas_{self.room}_viewers"])
        self.assertTrue(all(message["message"]["id"] == response.data["message"]["id"] for _, message in events))

    def test_an_exchange_with_the_ai_is_also_announced_so_nobody_has_to_refresh(self):
        self.ask(self.ana, "¿Cuántas clases hay?", mode="auto")

        self.assertEqual(len(self.chat_events()), 2)

    def test_a_failed_ai_request_announces_nothing(self):
        with mock.patch("uml_api.chat_views.get_ai_provider", return_value=FailingProvider()):
            response = self.ask(self.ana, "¿Cuántas clases hay?", mode="auto")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.chat_events(), [])

    def test_it_requires_a_known_participant(self):
        for headers in ({}, {"HTTP_X_PARTICIPANT_TOKEN": "no-es-uuid"}, {"HTTP_X_PARTICIPANT_TOKEN": str(uuid.uuid4())}):
            response = self.client.post(self.say_url(), {"message": "hola"}, format="json", **headers)
            self.assertEqual(response.status_code, 403)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_an_empty_or_too_long_message_is_rejected(self):
        self.assertEqual(self.say(self.ana, "   ").status_code, 400)
        self.assertEqual(self.say(self.ana, "x" * 2001).status_code, 400)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_someone_who_floods_the_chat_is_asked_to_wait(self):
        with mock.patch("uml_api.chat_views.MAX_SAYS_PER_MINUTE", 2):
            codes = [self.say(self.ana, f"mensaje {n}").status_code for n in range(3)]
            otra_persona = self.say(self.beto, "yo sí puedo").status_code

        self.assertEqual(codes, [201, 201, 429])
        self.assertEqual(otra_persona, 201)

    def test_the_ai_reads_what_the_people_said_as_part_of_the_conversation(self):
        self.say(self.ana, "Yo hago Autor")

        self.ask(self.beto, "¿Quién hace Autor?", mode="auto")

        self.assertIn("Yo hago Autor", self.provider.prompts[0])
