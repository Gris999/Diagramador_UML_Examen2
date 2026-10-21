import uuid
from datetime import timedelta
from unittest import mock

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from collab.models import ActivityEvent, ChatMessage, Participant
from uml_api.services.ai_provider import AIProviderError
from uml_api.services.ia_context import summarize_uml


class FakeProvider:
    def __init__(self, reply="Respuesta de prueba"):
        self.reply = reply
        self.prompts = []

    def chat(self, prompt):
        self.prompts.append(prompt)
        return self.reply


class FailingProvider:
    def chat(self, prompt):
        raise AIProviderError("proveedor caído")


class IaChatApiTests(APITestCase):
    room = "sala-demo"

    def setUp(self):
        self.ana = Participant.objects.create(
            room=self.room, token=uuid.uuid4(), display_name="Ana"
        )
        self.beto = Participant.objects.create(
            room=self.room, token=uuid.uuid4(), display_name="Beto"
        )
        self.provider = FakeProvider()
        patcher = mock.patch(
            "uml_api.chat_views.get_ai_provider",
            return_value=self.provider,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def chat_url(self, room=None):
        return f"/api/rooms/{room or self.room}/ia/chat/"

    def history_url(self, room=None):
        return f"/api/rooms/{room or self.room}/chat/"

    def ask(self, participant, message, **extra):
        body = {"mode": "ask", "message": message, **extra}
        return self.client.post(
            self.chat_url(),
            body,
            format="json",
            HTTP_X_PARTICIPANT_TOKEN=str(participant.token),
        )

    def own_history(self, participant, room=None, query=""):
        return self.client.get(
            self.history_url(room) + query,
            HTTP_X_PARTICIPANT_TOKEN=str(participant.token),
        )

    def add_event(self, actor_name, summary):
        return ActivityEvent.objects.create(
            room=self.room,
            actor_name=actor_name,
            type="add_class",
            summary=summary,
        )

    def test_requires_a_known_participant_token(self):
        for headers in (
            {},
            {"HTTP_X_PARTICIPANT_TOKEN": "no-es-uuid"},
            {"HTTP_X_PARTICIPANT_TOKEN": str(uuid.uuid4())},
        ):
            response = self.client.post(
                self.chat_url(),
                {"mode": "ask", "message": "hola"},
                format="json",
                **headers,
            )
            self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get(self.history_url()).status_code, 403)
        self.assertEqual(ChatMessage.objects.count(), 0)
        self.assertEqual(self.provider.prompts, [])

    def test_ask_answers_and_stores_both_messages(self):
        response = self.ask(self.ana, "¿Cuántas clases hay?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Respuesta de prueba")
        stored = list(
            ChatMessage.objects.filter(participant=self.ana).order_by("id")
        )
        self.assertEqual(
            [(message.role, message.content) for message in stored],
            [("user", "¿Cuántas clases hay?"), ("ia", "Respuesta de prueba")],
        )

    def test_prompt_includes_the_activity_of_every_participant(self):
        self.add_event("Beto", "añadió la clase Pedido")
        self.add_event("Ana", "eliminó un elemento")

        self.ask(self.ana, "¿Qué hizo Beto?")

        prompt = self.provider.prompts[0]
        self.assertIn("Beto: añadió la clase Pedido", prompt)
        self.assertIn("Ana: eliminó un elemento", prompt)
        self.assertIn("¿Qué hizo Beto?", prompt)

    def test_prompt_includes_a_summary_of_the_current_diagram(self):
        uml = {
            "classes": [{
                "id": "c1",
                "name": "Cliente",
                "attributes": [{"name": "id", "type": "int"}],
                "methods": [{"name": "comprar"}],
            }],
            "relationships": [],
        }

        self.ask(self.ana, "Describe el diagrama", uml=uml)

        prompt = self.provider.prompts[0]
        self.assertIn("Cliente", prompt)
        self.assertIn("id: int", prompt)
        self.assertIn("comprar", prompt)

    def test_chat_is_private_to_its_owner(self):
        self.ask(self.ana, "secreto-de-ana")

        beto_history = self.own_history(self.beto)
        self.assertEqual(beto_history.status_code, 200)
        self.assertEqual(beto_history.data["messages"], [])

        self.ask(self.beto, "¿Qué dijo Ana?")
        beto_prompt = self.provider.prompts[-1]
        self.assertNotIn("secreto-de-ana", beto_prompt)
        self.assertNotIn("Respuesta de prueba", beto_prompt)

        ana_history = self.own_history(self.ana)
        self.assertEqual(
            [message["content"] for message in ana_history.data["messages"]],
            ["secreto-de-ana", "Respuesta de prueba"],
        )

    def test_the_prompt_carries_only_the_requesters_own_history(self):
        self.ask(self.ana, "pregunta-previa-de-ana")

        self.ask(self.ana, "segunda pregunta")

        prompt = self.provider.prompts[-1]
        self.assertIn("pregunta-previa-de-ana", prompt)

    def test_token_of_another_room_is_rejected(self):
        outsider = Participant.objects.create(
            room="otra-sala", token=uuid.uuid4(), display_name="Eva"
        )

        response = self.client.post(
            self.chat_url(),
            {"mode": "ask", "message": "hola"},
            format="json",
            HTTP_X_PARTICIPANT_TOKEN=str(outsider.token),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.own_history(outsider).status_code, 403)

    def test_history_returns_the_latest_messages_oldest_first(self):
        for number in range(30):
            ChatMessage.objects.create(
                room=self.room,
                participant=self.ana,
                role="user",
                content=f"mensaje {number}",
            )

        response = self.own_history(self.ana, query="?limit=10")

        self.assertEqual(
            [message["content"] for message in response.data["messages"]],
            [f"mensaje {number}" for number in range(20, 30)],
        )

    def test_provider_failure_returns_502_and_stores_nothing(self):
        with mock.patch(
            "uml_api.chat_views.get_ai_provider",
            return_value=FailingProvider(),
        ):
            response = self.ask(self.ana, "hola")

        self.assertEqual(response.status_code, 502)
        self.assertIn("error", response.data)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_invalid_input_is_rejected(self):
        bad_bodies = [
            {"mode": "ask", "message": ""},
            {"mode": "ask", "message": "   "},
            {"mode": "ask", "message": "x" * 2001},
            {"mode": "ask", "message": 123},
            {"mode": "ask"},
            {"mode": "inventado", "message": "hola"},
        ]
        for body in bad_bodies:
            response = self.client.post(
                self.chat_url(),
                body,
                format="json",
                HTTP_X_PARTICIPANT_TOKEN=str(self.ana.token),
            )
            self.assertEqual(response.status_code, 400, body)
        self.assertEqual(self.provider.prompts, [])

    def test_too_many_requests_in_a_minute_are_throttled(self):
        for number in range(12):
            ChatMessage.objects.create(
                room=self.room,
                participant=self.ana,
                role="user",
                content=f"antes {number}",
            )

        response = self.ask(self.ana, "una más")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.provider.prompts, [])

    def test_old_messages_do_not_count_toward_the_throttle(self):
        old = ChatMessage.objects.bulk_create([
            ChatMessage(
                room=self.room,
                participant=self.ana,
                role="user",
                content=f"viejo {number}",
            )
            for number in range(12)
        ])
        ChatMessage.objects.filter(id__in=[m.id for m in old]).update(
            created_at=timezone.now() - timedelta(minutes=5)
        )

        response = self.ask(self.ana, "ahora sí")

        self.assertEqual(response.status_code, 200)

    def test_only_the_most_recent_activity_is_sent_to_the_model(self):
        for number in range(45):
            self.add_event("Beto", f"añadió la clase C{number}")

        self.ask(self.ana, "resumen")

        prompt = self.provider.prompts[0]
        self.assertIn("añadió la clase C44", prompt)
        self.assertNotIn("añadió la clase C0\n", prompt)


class SummarizeUmlTests(SimpleTestCase):
    def test_summarizes_classes_and_relationships_by_name(self):
        summary = summarize_uml({
            "classes": [
                {"id": "a", "name": "Cliente", "attributes": [{"name": "id", "type": "int"}], "methods": []},
                {"id": "b", "name": "Pedido", "attributes": [], "methods": [{"name": "total"}]},
            ],
            "relationships": [
                {"type": "association", "sourceId": "a", "targetId": "b", "labels": ["1", "0..*"]},
            ],
        })

        self.assertIn("Cliente", summary)
        self.assertIn("id: int", summary)
        self.assertIn("total", summary)
        self.assertIn("Cliente", summary.split("Relaciones")[-1])
        self.assertIn("Pedido", summary.split("Relaciones")[-1])
        self.assertIn("0..*", summary)

    def test_tolerates_missing_or_malformed_input(self):
        for value in (None, "texto", 5, [], {}, {"classes": "no"}, {"classes": [None, 3, {"name": None}]}):
            self.assertIsInstance(summarize_uml(value), str)

    def test_is_truncated_to_a_safe_size(self):
        huge = {"classes": [{"id": str(n), "name": f"Clase{n}", "attributes": [], "methods": []} for n in range(5000)]}

        self.assertLessEqual(len(summarize_uml(huge)), 12_000 + 200)
