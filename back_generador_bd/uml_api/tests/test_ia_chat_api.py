import json
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
        self.change_calls = []
        self.change_result = {
            "classes": [{"name": "Factura", "attributes": [{"name": "total", "type": "float"}]}],
            "relationships": [],
        }

    def chat(self, prompt):
        self.prompts.append(prompt)
        return self.reply

    def change(self, instruction, uml):
        self.change_calls.append((instruction, uml))
        return self.change_result


class FailingProvider:
    def chat(self, prompt):
        raise AIProviderError("proveedor caído")

    def change(self, instruction, uml):
        raise AIProviderError("proveedor caído")


class FakeChannelLayer:
    def __init__(self):
        self.sent = []

    async def group_send(self, group, message):
        self.sent.append((group, message))


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
        self.layer = FakeChannelLayer()
        layer_patcher = mock.patch(
            "uml_api.chat_views.get_channel_layer",
            return_value=self.layer,
        )
        layer_patcher.start()
        self.addCleanup(layer_patcher.stop)

    def chat_url(self, room=None):
        return f"/api/rooms/{room or self.room}/ia/chat/"

    def history_url(self, room=None):
        return f"/api/rooms/{room or self.room}/chat/"

    def ask(self, participant, message, mode="ask", **extra):
        body = {"mode": mode, "message": message, **extra}
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


    def test_change_mode_returns_the_changes_for_the_client_to_apply(self):
        response = self.ask(self.ana, "agrega la clase Factura", mode="change", uml={"classes": []})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["changes"], self.provider.change_result)
        self.assertTrue(response.data["reply"])
        self.assertEqual(
            self.provider.change_calls,
            [("agrega la clase Factura", {"classes": []})],
        )
        stored = ChatMessage.objects.filter(participant=self.ana).order_by("id")
        self.assertEqual([m.mode for m in stored], ["change", "change"])
        self.assertEqual([m.role for m in stored], ["user", "ia"])

    def test_change_mode_failure_returns_502_and_stores_nothing(self):
        with mock.patch(
            "uml_api.chat_views.get_ai_provider",
            return_value=FailingProvider(),
        ):
            response = self.ask(self.ana, "agrega X", mode="change")

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("changes", response.data)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_ask_and_review_never_return_changes_to_apply(self):
        diagram = json.dumps({"classes": [{"name": "Intrusa"}], "relationships": []})
        self.provider.reply = diagram

        ask_response = self.ask(self.ana, "¿qué ves?")
        review_response = self.ask(self.ana, "revisa", mode="review")

        self.assertNotIn("changes", ask_response.data)
        self.assertNotIn("changes", review_response.data)
        self.assertEqual(self.provider.change_calls, [])

    def review_reply(self, observations, summary="Hay detalles por mejorar."):
        return json.dumps({"resumen": summary, "observaciones": observations})

    def test_review_returns_suggestions_and_publishes_an_event_for_the_room(self):
        self.provider.reply = self.review_reply([
            {"texto": "Cliente no tiene clave primaria", "pedido": "agrega el atributo id: int a Cliente"},
            {"texto": "Pedido no se relaciona con nadie", "pedido": ""},
        ])

        response = self.ask(self.ana, "revisa el diagrama", mode="review", uml={"classes": []})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [s["text"] for s in response.data["suggestions"]],
            ["Cliente no tiene clave primaria", "Pedido no se relaciona con nadie"],
        )
        self.assertEqual(response.data["suggestions"][0]["prompt"], "agrega el atributo id: int a Cliente")
        self.assertIn("Hay detalles por mejorar.", response.data["reply"])

        event = ActivityEvent.objects.get(room=self.room, type="ia_review")
        self.assertEqual(event.actor_kind, "ia")
        self.assertEqual(event.actor_name, "IA")
        self.assertIn("a pedido de Ana", event.summary)
        self.assertIn("2 observaciones", event.summary)
        self.assertEqual(len(event.data["findings"]), 2)
        self.assertEqual(
            event.data["findings"][0],
            {"text": "Cliente no tiene clave primaria", "prompt": "agrega el atributo id: int a Cliente"},
        )

        self.assertEqual(
            [group for group, _ in self.layer.sent],
            [f"canvas_{self.room}", f"canvas_{self.room}_viewers"],
        )
        for _, message in self.layer.sent:
            self.assertEqual(message["type"], "activity")
            self.assertEqual(message["event"]["id"], event.id)
            self.assertEqual(message["event"]["actor_kind"], "ia")

    def test_review_accepts_an_answer_wrapped_in_a_markdown_fence(self):
        self.provider.reply = "```json\n" + self.review_reply([{"texto": "Falta una clave", "pedido": "agrega id"}]) + "\n```"

        response = self.ask(self.ana, "revisa", mode="review")

        self.assertEqual(len(response.data["suggestions"]), 1)

    def test_review_with_a_plain_text_answer_has_no_suggestions(self):
        self.provider.reply = "Todo se ve bien."

        response = self.ask(self.ana, "revisa", mode="review")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["suggestions"], [])
        self.assertIn("Todo se ve bien.", response.data["reply"])
        self.assertIn(
            "sin observaciones",
            ActivityEvent.objects.get(type="ia_review").summary,
        )

    def test_review_keeps_at_most_five_suggestions_and_skips_empty_ones(self):
        self.provider.reply = self.review_reply(
            [{"texto": f"Observación {n}", "pedido": f"cambio {n}"} for n in range(8)]
            + [{"texto": "", "pedido": "x"}, "no-es-dict", None]
        )

        response = self.ask(self.ana, "revisa", mode="review")

        self.assertEqual(len(response.data["suggestions"]), 5)

    def test_review_prompt_carries_the_diagram_and_asks_for_json(self):
        uml = {"classes": [{"id": "c1", "name": "Cliente", "attributes": [], "methods": []}], "relationships": []}

        self.ask(self.ana, "revisa", mode="review", uml=uml)

        prompt = self.provider.prompts[0]
        self.assertIn("Cliente", prompt)
        self.assertIn("observaciones", prompt)
        self.assertIn("atributos", prompt)

    def test_review_works_without_a_message(self):
        response = self.client.post(
            self.chat_url(),
            {"mode": "review", "uml": {"classes": []}},
            format="json",
            HTTP_X_PARTICIPANT_TOKEN=str(self.ana.token),
        )

        self.assertEqual(response.status_code, 200)

    def test_history_exposes_the_mode_of_each_message(self):
        self.ask(self.ana, "agrega X", mode="change")

        history = self.own_history(self.ana)

        self.assertEqual([m["mode"] for m in history.data["messages"]], ["change", "change"])


class GeminiProviderTests(SimpleTestCase):
    def test_chat_uses_a_short_timeout_and_few_attempts(self):
        from django.test import override_settings
        from uml_api.services.ai_provider import GeminiProvider

        response = mock.Mock()
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": " hola "}]}}]
        }
        with override_settings(GEMINI_API_KEY="clave-real"), mock.patch(
            "uml_api.services.ai_provider._post_gemini", return_value=response
        ) as post:
            reply = GeminiProvider().chat("pregunta")

        self.assertEqual(reply, "hola")
        self.assertEqual(post.call_args.kwargs["timeout"], 30)
        self.assertEqual(post.call_args.kwargs["max_attempts"], 2)

    def test_errors_never_leak_the_api_key(self):
        from django.test import override_settings
        from uml_api.services.ai_provider import GeminiProvider

        with override_settings(GEMINI_API_KEY="clave-secreta-123"), mock.patch(
            "uml_api.services.ai_provider._post_gemini",
            side_effect=RuntimeError("https://x/?key=clave-secreta-123"),
        ):
            with self.assertRaises(AIProviderError) as caught:
                GeminiProvider().chat("pregunta")

        self.assertNotIn("clave-secreta-123", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)


class OllamaProviderTests(SimpleTestCase):
    def provider(self):
        from uml_api.services.ai_provider import OllamaProvider
        return OllamaProvider(base_url="http://ollama.local:11434", model="qwen2.5:7b")

    def fake_response(self, text):
        response = mock.Mock()
        response.json.return_value = {"response": text}
        return response

    def test_chat_sends_the_prompt_to_the_local_server_without_streaming(self):
        with mock.patch(
            "uml_api.services.ai_provider.requests.post",
            return_value=self.fake_response("  Hola desde el modelo local  "),
        ) as post:
            reply = self.provider().chat("pregunta")

        self.assertEqual(reply, "Hola desde el modelo local")
        self.assertEqual(post.call_args.args[0], "http://ollama.local:11434/api/generate")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "qwen2.5:7b")
        self.assertEqual(body["prompt"], "pregunta")
        self.assertFalse(body["stream"])
        self.assertIn("timeout", post.call_args.kwargs)

    def test_change_asks_for_json_with_the_same_prompt_gemini_uses(self):
        from uml_api.services.services_gemini import build_change_prompt

        uml = {"classes": [], "relationships": []}
        reply = '```json\n{"classes": [{"name": "Factura"}]}\n```'
        with mock.patch(
            "uml_api.services.ai_provider.requests.post",
            return_value=self.fake_response(reply),
        ) as post:
            changes = self.provider().change("agrega la clase Factura", uml)

        self.assertEqual(changes, {"classes": [{"name": "Factura"}]})
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["prompt"], build_change_prompt("agrega la clase Factura", uml))
        self.assertEqual(body["format"], "json")

    def test_a_server_that_is_down_or_answers_garbage_is_an_ai_error(self):
        import requests

        provider = self.provider()
        with mock.patch(
            "uml_api.services.ai_provider.requests.post",
            side_effect=requests.ConnectionError("no hay servidor"),
        ):
            with self.assertRaises(AIProviderError):
                provider.chat("hola")
        with mock.patch(
            "uml_api.services.ai_provider.requests.post",
            return_value=self.fake_response("esto no es json"),
        ):
            with self.assertRaises(AIProviderError):
                provider.change("agrega X", None)
        with mock.patch(
            "uml_api.services.ai_provider.requests.post",
            return_value=self.fake_response("   "),
        ):
            with self.assertRaises(AIProviderError):
                provider.chat("hola")

    def test_provider_selection_follows_the_settings(self):
        from django.test import override_settings
        from uml_api.services.ai_provider import GeminiProvider, OllamaProvider, get_ai_provider

        with override_settings(AI_PROVIDER="ollama", OLLAMA_BASE_URL="http://x:1", OLLAMA_MODEL="m"):
            provider = get_ai_provider()
        self.assertIsInstance(provider, OllamaProvider)
        self.assertEqual((provider.base_url, provider.model), ("http://x:1", "m"))
        with override_settings(AI_PROVIDER="gemini"):
            self.assertIsInstance(get_ai_provider(), GeminiProvider)
        with override_settings(AI_PROVIDER="otro"):
            with self.assertRaises(AIProviderError):
                get_ai_provider()


class ProviderInfoApiTests(APITestCase):
    def test_reports_which_provider_answers_without_exposing_secrets(self):
        from django.test import override_settings

        with override_settings(AI_PROVIDER="ollama", OLLAMA_MODEL="qwen2.5:7b", GEMINI_API_KEY="secreto"):
            response = self.client.get("/api/ia/provider/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"provider": "ollama", "label": "IA local (qwen2.5:7b)"})
        self.assertNotIn("secreto", str(response.data))

    def test_gemini_is_reported_as_cloud(self):
        from django.test import override_settings

        with override_settings(AI_PROVIDER="gemini"):
            response = self.client.get("/api/ia/provider/")

        self.assertEqual(response.data, {"provider": "gemini", "label": "IA en la nube (Gemini)"})


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
