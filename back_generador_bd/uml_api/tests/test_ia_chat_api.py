import json
import uuid
from datetime import timedelta
from unittest import mock

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APITestCase

from collab.models import ActivityEvent, ChatMessage, IaAttempt, Participant
from collab.stores import get_turn_store
from collab.turn import InMemoryTurnStore
from uml_api.services.ai_provider import AIProviderError
from uml_api.services.change_guard import count_destructive, validate_changes
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


class ChatTestBase(APITestCase):
    room = "sala-demo"

    def setUp(self):
        InMemoryTurnStore.reset()
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

    def review_reply(self, observations, summary="Hay detalles por mejorar."):
        return json.dumps({"resumen": summary, "observaciones": observations})


class IaChatApiTests(ChatTestBase):
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

    def test_the_conversation_belongs_to_the_whole_room(self):
        self.ask(self.ana, "pregunta-de-ana")
        self.ask(self.beto, "¿Qué dijo Ana?")

        for persona in (self.ana, self.beto):
            historial = self.own_history(persona)
            self.assertEqual(historial.status_code, 200)
            self.assertEqual(
                [(m["author_name"], m["content"]) for m in historial.data["messages"]],
                [
                    ("Ana", "pregunta-de-ana"),
                    ("IA", "Respuesta de prueba"),
                    ("Beto", "¿Qué dijo Ana?"),
                    ("IA", "Respuesta de prueba"),
                ],
            )

    def test_the_prompt_carries_the_conversation_of_the_room_with_who_said_what(self):
        self.ask(self.ana, "pregunta-previa-de-ana")

        self.ask(self.beto, "segunda pregunta, de Beto")

        prompt = self.provider.prompts[-1]
        self.assertIn("Ana: pregunta-previa-de-ana", prompt)
        self.assertIn("IA: Respuesta de prueba", prompt)
        self.assertIn("segunda pregunta, de Beto", prompt)

    def test_a_room_does_not_see_the_conversation_of_another_room(self):
        otro = Participant.objects.create(room="otra-sala", token=uuid.uuid4(), display_name="Eva")
        self.ask(self.ana, "solo-en-sala-demo")

        respuesta = self.client.get(
            self.history_url("otra-sala"), HTTP_X_PARTICIPANT_TOKEN=str(otro.token)
        )

        self.assertEqual(respuesta.data["messages"], [])

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
        IaAttempt.objects.bulk_create(
            [IaAttempt(room=self.room, participant=self.ana) for _ in range(12)]
        )

        response = self.ask(self.ana, "una más")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.provider.prompts, [])

    def test_old_messages_do_not_count_toward_the_throttle(self):
        old = IaAttempt.objects.bulk_create(
            [IaAttempt(room=self.room, participant=self.ana) for _ in range(12)]
        )
        IaAttempt.objects.filter(id__in=[a.id for a in old]).update(
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


class ChatReliabilityTests(ChatTestBase):
    """Atomicidad, topes de coste y confirmación de cambios destructivos."""

    def test_a_failure_while_publishing_a_review_leaves_nothing_half_saved(self):
        self.provider.reply = self.review_reply([{"texto": "Falta una clave", "pedido": "agrega id"}])

        with mock.patch.object(
            ActivityEvent.objects, "create", side_effect=RuntimeError("base caída")
        ):
            response = self.ask(self.ana, "revisa", mode="review")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(ChatMessage.objects.count(), 0)
        self.assertEqual(ActivityEvent.objects.count(), 0)

    def test_the_whole_room_shares_a_request_budget(self):
        IaAttempt.objects.bulk_create(
            [IaAttempt(room=self.room, participant=self.beto) for _ in range(30)]
        )

        response = self.ask(self.ana, "una más")

        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.provider.prompts, [])

    def test_the_whole_service_shares_a_request_budget_across_rooms(self):
        other = Participant.objects.create(room="otra", token=uuid.uuid4(), display_name="Eva")
        IaAttempt.objects.bulk_create(
            [IaAttempt(room="otra", participant=other) for _ in range(60)]
        )

        response = self.ask(self.ana, "una más")

        self.assertEqual(response.status_code, 429)

    def test_a_failing_provider_still_spends_the_budget(self):
        with mock.patch.object(
            self.provider, "chat", side_effect=AIProviderError("caído")
        ):
            for _ in range(12):
                self.assertEqual(self.ask(self.ana, "hola").status_code, 502)

            response = self.ask(self.ana, "hola")

        self.assertEqual(response.status_code, 429)

    def test_a_rejected_request_gives_its_slot_back(self):
        IaAttempt.objects.bulk_create(
            [IaAttempt(room=self.room, participant=self.ana) for _ in range(12)]
        )

        self.ask(self.ana, "una más")

        self.assertEqual(IaAttempt.objects.filter(participant=self.ana).count(), 12)

    def test_the_slot_is_reserved_before_the_provider_is_called(self):
        seen = []

        def chat(prompt):
            seen.append(IaAttempt.objects.filter(participant=self.ana).count())
            return "ok"

        with mock.patch.object(self.provider, "chat", side_effect=chat):
            self.ask(self.ana, "hola")

        self.assertEqual(seen, [1])

    def test_old_attempts_are_cleaned_up(self):
        old = IaAttempt.objects.create(room=self.room, participant=self.ana)
        IaAttempt.objects.filter(id=old.id).update(created_at=timezone.now() - timedelta(hours=3))

        self.ask(self.ana, "hola")

        self.assertFalse(IaAttempt.objects.filter(id=old.id).exists())

    def test_change_mode_reports_how_many_deletions_the_ai_proposes(self):
        self.provider.change_result = {
            "classes": [
                {"name": "Pedido", "eliminar": True},
                {"name": "Cliente", "attributes": [{"name": "edad", "eliminar": True}]},
            ],
            "relationships": [{"sourceId": "A", "targetId": "B", "eliminar": True}],
        }

        response = self.ask(self.ana, "quita cosas", mode="change")

        self.assertEqual(response.data["destructive"], 3)

    def test_change_mode_asks_for_confirmation_when_the_model_returns_less_than_there_was(self):
        uml = {"classes": [{"id": "c1", "name": "Cliente",
                            "attributes": [{"name": "id", "type": "int"}, {"name": "nombre", "type": "string"}],
                            "methods": []}], "relationships": []}
        self.provider.change_result = {"classes": [{"id": "c1", "name": "Cliente", "attributes": []}]}

        response = self.ask(self.ana, "limpia Cliente", mode="change", uml=uml)

        self.assertEqual(response.data["destructive"], 2)

    def test_a_harmless_change_reports_no_deletions(self):
        response = self.ask(self.ana, "agrega Factura", mode="change")

        self.assertEqual(response.data["destructive"], 0)

    def test_an_oversized_change_from_the_model_is_rejected_whole(self):
        self.provider.change_result = {"classes": [{"name": f"C{n}"} for n in range(200)]}

        response = self.ask(self.ana, "crea de todo", mode="change")

        self.assertEqual(response.status_code, 502)
        self.assertNotIn("changes", response.data)
        self.assertEqual(ChatMessage.objects.count(), 0)


class ChangeGuardAgainstTheCurrentDiagramTests(SimpleTestCase):
    """Una respuesta que deja menos de lo que había también borra, aunque no lo marque."""

    uml = {
        "classes": [
            {
                "id": "c1",
                "name": "Cliente",
                "attributes": [{"name": "id", "type": "int"}, {"name": "nombre", "type": "string"}],
                "methods": [{"name": "comprar"}],
            }
        ],
        "relationships": [],
    }

    def test_returning_fewer_members_than_the_class_has_counts_as_deleting_them(self):
        changes = {"classes": [{"id": "c1", "name": "Cliente", "attributes": [], "methods": []}]}

        self.assertEqual(count_destructive(changes, self.uml), 3)

    def test_returning_only_the_new_attribute_would_wipe_the_others(self):
        changes = {"classes": [{"name": "Cliente", "attributes": [{"name": "email", "type": "string"}]}]}

        self.assertEqual(count_destructive(changes, self.uml), 2)

    def test_the_editor_matches_names_exactly_so_another_spelling_is_a_new_class(self):
        changes = {"classes": [{"name": "cliente", "attributes": [{"name": "email"}]}]}

        self.assertEqual(count_destructive(changes, self.uml), 0)

    def test_a_response_with_deletion_marks_only_deletes_what_is_marked(self):
        changes = {"classes": [{"name": "Cliente", "attributes": [{"name": "nombre", "eliminar": True}]}]}

        self.assertEqual(count_destructive(changes, self.uml), 1)

    def test_an_edit_does_not_replace_the_members_it_leaves_out(self):
        changes = {
            "original": self.uml,
            "editado": {"classes": [{"id": "c1", "name": "Cliente", "attributes": [
                {"originalName": "id", "name": "codigo", "type": "int", "editado": True}
            ]}]},
        }

        self.assertEqual(count_destructive(changes, self.uml), 0)

    def test_keeping_everything_and_adding_more_is_harmless(self):
        changes = {"classes": [{
            "id": "c1",
            "name": "Cliente",
            "attributes": [{"name": "id"}, {"name": "nombre"}, {"name": "email"}],
            "methods": [{"name": "comprar"}],
        }]}

        self.assertEqual(count_destructive(changes, self.uml), 0)

    def test_members_already_flagged_are_not_counted_twice(self):
        changes = {"classes": [{
            "id": "c1",
            "name": "Cliente",
            "attributes": [{"name": "id"}, {"name": "nombre", "eliminar": True}],
            "methods": [{"name": "comprar"}],
        }]}

        self.assertEqual(count_destructive(changes, self.uml), 1)

    def test_classes_that_do_not_exist_yet_and_edit_sections_are_not_penalized(self):
        creating = {"classes": [{"name": "Factura", "attributes": []}]}
        editing = {"editado": {"classes": [{"id": "c1", "name": "Cliente", "attributes": [{"name": "email"}]}]}}

        self.assertEqual(count_destructive(creating, self.uml), 0)
        self.assertEqual(count_destructive(editing, self.uml), 0)

    def test_a_missing_or_malformed_diagram_changes_nothing(self):
        changes = {"classes": [{"id": "c1", "name": "Cliente", "attributes": []}]}

        for uml in (None, "x", [], {"classes": "no"}, {"classes": [None, 3]}):
            self.assertEqual(count_destructive(changes, uml), 0)


class ChangeGuardTests(SimpleTestCase):
    def test_counts_deletions_in_every_format_the_editor_understands(self):
        changes = {
            "editado": {
                "classes": [{"name": "A", "methods": [{"name": "m", "eliminar": True}]}],
                "relationships": [{"id": "r", "eliminar": True}],
            },
            "classes": [{"name": "B", "eliminar": True}],
        }

        self.assertEqual(count_destructive(changes), 3)

    def test_tolerates_malformed_input(self):
        for value in (None, "x", 3, [], {"classes": "no"}, {"classes": [None, 4, {"attributes": "no"}]}):
            self.assertEqual(count_destructive(value), 0)

    def test_validation_rejects_huge_or_non_dict_changes(self):
        with self.assertRaises(AIProviderError):
            validate_changes([1, 2])
        with self.assertRaises(AIProviderError):
            validate_changes({"classes": [{"name": "x"}] * 61})
        with self.assertRaises(AIProviderError):
            validate_changes({"relationships": [{}] * 151})
        validate_changes({"classes": [{"name": "x"}] * 60, "relationships": [{}] * 150})


class ClaimSuggestionApiTests(ChatTestBase):
    """Una idea de la IA solo la puede aplicar una persona, también tras recargar."""

    def setUp(self):
        super().setUp()
        self.event = ActivityEvent.objects.create(
            room=self.room,
            actor=self.ana,
            actor_name="IA",
            actor_kind="ia",
            type="ia_review",
            summary="revisó el diagrama a pedido de Ana: 2 observaciones",
            data={"findings": [
                {"text": "Falta una clave", "prompt": "agrega id"},
                {"text": "Está aislada", "prompt": "relaciona"},
            ]},
        )

    def claim_url(self, event_id=None, index=0, room=None):
        return f"/api/rooms/{room or self.room}/activity/{event_id or self.event.id}/apply/{index}/"

    def claim(self, participant, **kwargs):
        headers = {"HTTP_X_PARTICIPANT_TOKEN": str(participant.token)} if participant else {}
        return self.client.post(self.claim_url(**kwargs), **headers)

    def test_the_first_person_claims_it_and_the_room_is_told(self):
        response = self.claim(self.beto)

        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        [entry] = self.event.data["applied"]
        self.assertEqual(
            (entry["index"], entry["by"], entry["by_id"], entry["state"]),
            (0, "Beto", self.beto.id, "reserved"),
        )
        self.assertEqual(response.data["event"]["data"]["applied"][0]["index"], 0)
        self.assertEqual(
            [group for group, _ in self.layer.sent],
            [f"canvas_{self.room}", f"canvas_{self.room}_viewers"],
        )
        self.assertEqual(self.layer.sent[0][1]["event"]["id"], self.event.id)

    def test_a_second_claim_of_the_same_idea_is_refused(self):
        self.claim(self.beto)

        response = self.claim(self.ana)

        self.assertEqual(response.status_code, 409)
        self.event.refresh_from_db()
        self.assertEqual(len(self.event.data["applied"]), 1)

    def test_other_ideas_of_the_same_review_stay_available(self):
        self.claim(self.beto, index=0)

        response = self.claim(self.ana, index=1)

        self.assertEqual(response.status_code, 200)

    def test_only_who_claimed_it_can_release_it(self):
        self.claim(self.beto)

        stranger = self.client.delete(
            self.claim_url(), HTTP_X_PARTICIPANT_TOKEN=str(self.ana.token)
        )
        owner = self.client.delete(
            self.claim_url(), HTTP_X_PARTICIPANT_TOKEN=str(self.beto.token)
        )

        self.assertEqual(stranger.status_code, 403)
        self.assertEqual(owner.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.data.get("applied"), [])
        self.assertEqual(self.claim(self.ana).status_code, 200)

    def confirm(self, participant, **kwargs):
        return self.client.put(
            self.claim_url(**kwargs), HTTP_X_PARTICIPANT_TOKEN=str(participant.token)
        )

    def release(self, participant, **kwargs):
        return self.client.delete(
            self.claim_url(**kwargs), HTTP_X_PARTICIPANT_TOKEN=str(participant.token)
        )

    def age_reservation(self, seconds):
        self.event.refresh_from_db()
        data = dict(self.event.data)
        for entry in data["applied"]:
            if "reserved_at" in entry:
                entry["reserved_at"] = (timezone.now() - timedelta(seconds=seconds)).isoformat()
        self.event.data = data
        self.event.save()

    def test_confirming_marks_the_idea_as_applied_for_good(self):
        self.claim(self.beto)

        response = self.confirm(self.beto)

        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        [entry] = self.event.data["applied"]
        self.assertEqual(entry["state"], "applied")
        self.assertEqual(entry["by"], "Beto")
        self.assertNotIn("reserved_at", entry)
        # Una vez aplicada ni la reserva vencida ni una liberación la devuelven.
        self.assertEqual(self.claim(self.ana).status_code, 409)
        self.assertEqual(self.release(self.beto).status_code, 409)
        self.event.refresh_from_db()
        self.assertEqual(self.event.data["applied"][0]["state"], "applied")

    def test_an_expired_reservation_can_be_taken_by_someone_else(self):
        self.claim(self.beto)
        self.assertEqual(self.claim(self.ana).status_code, 409)

        self.age_reservation(seconds=151)

        self.assertEqual(self.claim(self.ana).status_code, 200)
        self.event.refresh_from_db()
        [entry] = self.event.data["applied"]
        self.assertEqual(entry["by"], "Ana")

    def test_a_reservation_that_has_not_expired_still_blocks_others(self):
        self.claim(self.beto)
        self.age_reservation(seconds=100)

        self.assertEqual(self.claim(self.ana).status_code, 409)

    def test_the_same_person_can_retry_their_own_reservation(self):
        self.claim(self.beto)

        self.assertEqual(self.claim(self.beto).status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(len(self.event.data["applied"]), 1)

    def test_only_the_holder_can_confirm_a_live_reservation(self):
        self.claim(self.beto)

        self.assertEqual(self.confirm(self.ana).status_code, 409)
        self.event.refresh_from_db()
        self.assertEqual(self.event.data["applied"][0]["state"], "reserved")

    def test_confirming_after_the_reservation_expired_still_records_the_change(self):
        self.claim(self.beto)
        self.age_reservation(seconds=400)

        self.assertEqual(self.confirm(self.beto).status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.data["applied"][0]["state"], "applied")

    def test_confirming_loses_to_someone_who_took_over_an_expired_reservation(self):
        self.claim(self.beto)
        self.age_reservation(seconds=400)
        self.claim(self.ana)

        self.assertEqual(self.confirm(self.beto).status_code, 409)

    def test_ideas_stored_before_reservations_existed_count_as_applied(self):
        self.event.data = {**self.event.data, "applied": [{"index": 0, "by": "Beto", "by_id": self.beto.id}]}
        self.event.save()

        self.assertEqual(self.claim(self.ana).status_code, 409)
        self.assertEqual(self.release(self.beto).status_code, 409)

    def test_confirm_and_release_are_announced_to_the_room(self):
        self.claim(self.beto)
        self.layer.sent.clear()

        self.confirm(self.beto)

        self.assertEqual(len(self.layer.sent), 2)
        self.assertEqual(self.layer.sent[0][1]["event"]["data"]["applied"][0]["state"], "applied")

    def test_invalid_requests_are_rejected(self):
        self.assertEqual(self.claim(None).status_code, 403)
        self.assertEqual(self.claim(self.ana, index=5).status_code, 404)
        self.assertEqual(self.claim(self.ana, event_id=99999).status_code, 404)
        other = ActivityEvent.objects.create(room="otra", actor_name="IA", type="ia_review", data={"findings": [{"text": "x", "prompt": "y"}]})
        self.assertEqual(self.claim(self.ana, event_id=other.id).status_code, 404)
        not_review = ActivityEvent.objects.create(room=self.room, actor_name="Ana", type="add_class", data={})
        self.assertEqual(self.claim(self.ana, event_id=not_review.id).status_code, 404)

    def test_a_finding_without_a_request_cannot_be_claimed(self):
        self.event.data = {"findings": [{"text": "solo informativa", "prompt": ""}]}
        self.event.save()

        self.assertEqual(self.claim(self.ana).status_code, 404)


class OllamaProviderTests(SimpleTestCase):
    def provider(self):
        from uml_api.services.ai_provider import OllamaProvider
        return OllamaProvider(base_url="http://ollama.local:11434", model="qwen3.5:9b")

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
        self.assertEqual(body["model"], "qwen3.5:9b")
        self.assertIs(body["think"], False)
        self.assertEqual(body["prompt"], "pregunta")
        self.assertFalse(body["stream"])
        self.assertIn("timeout", post.call_args.kwargs)

    def test_change_uses_the_same_instructions_gemini_uses_and_tolerates_markdown(self):
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
        self.assertTrue(body["prompt"].startswith(build_change_prompt("agrega la clase Factura", uml)))
        self.assertIn("ÚNICAMENTE con el JSON", body["prompt"])
        # Qwen 3.5 no soporta salida estructurada en Ollama: no se pide `format`.
        self.assertNotIn("format", body)

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

        with override_settings(AI_PROVIDER="ollama", OLLAMA_MODEL="qwen3.5:9b", GEMINI_API_KEY="secreto"):
            response = self.client.get("/api/ia/provider/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"provider": "ollama", "label": "IA local (qwen3.5:9b)"})
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


class ShareTurnTests(ChatTestBase):
    """C1: la IA atiende un pedido a la vez por sala y dice a quién está atendiendo."""

    def hold_turn(self, participant, room=None):
        return get_turn_store().take(room or self.room, participant.id, participant.display_name, 130)

    def test_a_request_while_the_ai_is_busy_is_refused_with_who_is_being_served(self):
        self.hold_turn(self.beto)

        response = self.ask(self.ana, "¿hay algo?")

        self.assertEqual(response.status_code, 409)
        self.assertIn("Beto", response.data["error"])
        self.assertEqual(self.provider.prompts, [])
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_a_refused_request_does_not_spend_the_budget(self):
        self.hold_turn(self.beto)

        self.ask(self.ana, "¿hay algo?")

        self.assertEqual(IaAttempt.objects.count(), 0)

    def test_the_turn_is_given_back_after_a_normal_answer(self):
        self.ask(self.ana, "hola")

        self.assertIsNone(get_turn_store().current(self.room))
        self.assertEqual(self.ask(self.beto, "y yo").status_code, 200)

    def test_the_turn_is_given_back_when_the_provider_fails(self):
        with mock.patch("uml_api.chat_views.get_ai_provider", return_value=FailingProvider()):
            self.assertEqual(self.ask(self.ana, "hola").status_code, 502)

        self.assertIsNone(get_turn_store().current(self.room))

    def test_the_turn_is_given_back_when_the_request_is_throttled(self):
        with mock.patch("uml_api.chat_views.MAX_REQUESTS_PER_MINUTE", 0):
            self.assertEqual(self.ask(self.ana, "hola").status_code, 429)

        self.assertIsNone(get_turn_store().current(self.room))

    def test_the_turn_is_given_back_for_review_and_change_modes_too(self):
        self.ask(self.ana, "revisa", mode="review")
        self.ask(self.ana, "agrega Factura", mode="change", uml={"classes": []})

        self.assertIsNone(get_turn_store().current(self.room))

    def test_rooms_do_not_wait_for_each_other(self):
        self.hold_turn(self.beto)
        eva = Participant.objects.create(room="otra-sala", token=uuid.uuid4(), display_name="Eva")

        response = self.client.post(
            self.chat_url("otra-sala"),
            {"mode": "ask", "message": "hola"},
            format="json",
            HTTP_X_PARTICIPANT_TOKEN=str(eva.token),
        )

        self.assertEqual(response.status_code, 200)

    def test_invalid_input_does_not_take_the_turn(self):
        self.ask(self.ana, "   ")

        self.assertIsNone(get_turn_store().current(self.room))

    def test_if_the_turn_store_fails_the_room_still_gets_its_answer(self):
        """Redis caído no deja a la sala sin IA: se registra el fallo y los topes de uso siguen protegiendo el costo."""
        class BrokenTurns:
            def take(self, *args):
                raise ConnectionError("redis caído")

            def release(self, *args):
                raise ConnectionError("redis caído")

        with mock.patch("uml_api.chat_views.get_turn_store", return_value=BrokenTurns()):
            response = self.ask(self.ana, "hola")

        self.assertEqual(response.status_code, 200)
