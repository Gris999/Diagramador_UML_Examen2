import uuid
from unittest import mock

from collab.limits import InMemoryRateLimiter
from collab.models import ActivityEvent, ChatMessage, Participant
from collab.room_state import InMemoryRoomState

from .test_ia_chat_api import ChatTestBase, FailingProvider

DIAGRAMA = {
    "classes": [{"id": "c1", "name": "Cliente", "attributes": [{"name": "nombre", "type": "String"}], "methods": []}],
    "relationships": [],
}


class UnifiedChatBase(ChatTestBase):
    def setUp(self):
        super().setUp()
        InMemoryRoomState.reset()
        InMemoryRateLimiter.reset()
        self.addCleanup(InMemoryRoomState.reset)
        self.addCleanup(InMemoryRateLimiter.reset)

    def say(self, participant, message, uml=DIAGRAMA):
        return self.ask(participant, message, mode="auto", uml=uml)

    def stored(self):
        return list(ChatMessage.objects.order_by("id").values_list("role", "author_name", "mode", "content"))


class UnifiedChatAskTests(UnifiedChatBase):
    def test_a_question_is_answered_without_touching_the_diagram(self):
        response = self.say(self.ana, "¿Cuántas clases hay?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["reply"], "Respuesta de prueba")
        self.assertEqual(response.data["intent"], "ask")
        self.assertNotIn("changes", response.data)
        self.assertNotIn("proposal", response.data)
        self.assertEqual(self.provider.change_calls, [])
        self.assertEqual([row[2] for row in self.stored()], ["ask", "ask"])

    def test_a_question_that_mentions_an_edit_verb_is_still_a_question(self):
        response = self.say(self.ana, "¿Cómo agrego una clase?")

        self.assertEqual(response.data["intent"], "ask")
        self.assertEqual(self.provider.change_calls, [])


class UnifiedChatProposalTests(UnifiedChatBase):
    def test_an_order_is_proposed_and_not_applied(self):
        response = self.say(self.ana, "Agrega una clase Factura con total")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "change")
        self.assertNotIn("changes", response.data)
        self.assertEqual(response.data["proposal"]["lines"], ["Crear la clase Factura (atributos: total: float)"])
        self.assertEqual(response.data["proposal"]["destructive"], 0)
        # La vista previa es exactamente el cambio que se aplicaría con el «sí», para dibujarlo sobre el diagrama sin tocarlo.
        self.assertEqual(response.data["proposal"]["preview"], self.provider.change_result)
        self.assertIn("¿Lo aplico?", response.data["reply"])
        self.assertIn("Crear la clase Factura", response.data["reply"])
        self.assertEqual(len(self.provider.change_calls), 1)
        self.assertEqual(self.provider.change_calls[0][0], "Agrega una clase Factura con total")
        # la propuesta queda en la conversación de la sala, con quien la pidió
        self.assertEqual([(row[0], row[1], row[2]) for row in self.stored()], [("user", "Ana", "change"), ("ia", "IA", "change")])

    def test_saying_yes_hands_over_the_change_to_apply(self):
        self.say(self.ana, "Agrega una clase Factura con total")

        response = self.say(self.ana, "sí, aplícalo")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "confirm")
        self.assertEqual(response.data["changes"], self.provider.change_result)
        self.assertEqual(response.data["destructive"], 0)
        self.assertEqual(response.data["reply"], "Listo, apliqué el cambio en el diagrama.")
        self.assertEqual(len(self.provider.change_calls), 1)  # no se le vuelve a pedir nada a la IA
        self.assertEqual(self.provider.prompts, [])

    def test_the_change_can_only_be_applied_once(self):
        self.say(self.ana, "Agrega una clase Factura con total")
        self.say(self.ana, "sí")

        again = self.say(self.ana, "sí")

        self.assertEqual(again.data["intent"], "ask")
        self.assertNotIn("changes", again.data)

    def test_saying_no_drops_the_proposal_and_changes_nothing(self):
        self.say(self.ana, "Agrega una clase Factura con total")

        response = self.say(self.ana, "no, descártalo")

        self.assertEqual(response.data["intent"], "discard")
        self.assertNotIn("changes", response.data)
        self.assertIn("No cambié el diagrama", response.data["reply"])
        self.assertEqual(self.say(self.ana, "sí").data["intent"], "ask")

    def test_yes_without_a_proposal_is_just_a_message(self):
        response = self.say(self.ana, "sí")

        self.assertEqual(response.data["intent"], "ask")
        self.assertNotIn("changes", response.data)

    def test_someone_else_cannot_confirm_my_proposal(self):
        self.say(self.ana, "Agrega una clase Factura con total")

        response = self.say(self.beto, "sí")

        self.assertEqual(response.data["intent"], "ask")
        self.assertNotIn("changes", response.data)
        # lo de Ana sigue esperando a Ana
        self.assertEqual(self.say(self.ana, "sí").data["intent"], "confirm")

    def test_a_new_order_replaces_the_one_that_was_waiting(self):
        self.say(self.ana, "Agrega una clase Factura con total")
        self.provider.change_result = {"classes": [{"name": "Venta"}], "relationships": []}
        self.say(self.ana, "Agrega una clase Venta")

        response = self.say(self.ana, "sí")

        self.assertEqual(response.data["changes"], {"classes": [{"name": "Venta"}], "relationships": []})

    def test_a_proposal_that_deletes_warns_and_counts_what_goes(self):
        self.provider.change_result = {"classes": [{"name": "Cliente", "eliminar": True}], "relationships": []}

        proposal = self.say(self.ana, "elimina la clase Cliente")

        self.assertEqual(proposal.data["proposal"]["destructive"], 1)
        self.assertIn("Eliminar la clase Cliente", proposal.data["reply"])
        self.assertIn("elimina 1 elemento", proposal.data["reply"])

        confirmed = self.say(self.ana, "sí")
        self.assertEqual(confirmed.data["destructive"], 1)

    def test_the_deletions_to_confirm_are_counted_on_the_diagram_of_now(self):
        self.provider.change_result = {"classes": [{"name": "Cliente", "attributes": [{"name": "otro", "type": "int"}]}]}
        self.say(self.ana, "cambia la clase Cliente", uml=DIAGRAMA)

        # entre la propuesta y el «sí» el diagrama ganó un atributo que el cambio dejaría fuera
        grown = {"classes": [{"id": "c1", "name": "Cliente", "attributes": [
            {"name": "nombre", "type": "String"}, {"name": "edad", "type": "int"}, {"name": "otro", "type": "int"}], "methods": []}],
            "relationships": []}
        confirmed = self.say(self.ana, "sí", uml=grown)

        self.assertEqual(confirmed.data["destructive"], 2)

    def test_saying_it_directly_skips_the_permission(self):
        response = self.say(self.ana, "Agrega una clase Factura con total directamente")

        self.assertEqual(response.data["intent"], "change")
        self.assertEqual(response.data["changes"], self.provider.change_result)
        self.assertNotIn("proposal", response.data)
        self.assertEqual(response.data["reply"], "Listo, apliqué el cambio en el diagrama.")
        # y no deja nada esperando
        self.assertEqual(self.say(self.ana, "sí").data["intent"], "ask")

    def test_a_proposal_that_is_too_big_is_refused_and_nothing_is_kept(self):
        self.provider.change_result = {"classes": [{"name": f"C{n}"} for n in range(200)], "relationships": []}

        response = self.say(self.ana, "agrega 200 clases")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(ChatMessage.objects.count(), 0)
        self.assertEqual(self.say(self.ana, "sí").data["intent"], "ask")

    def test_when_the_provider_fails_nothing_is_stored_or_left_waiting(self):
        with mock.patch("uml_api.chat_views.get_ai_provider", return_value=FailingProvider()):
            response = self.say(self.ana, "agrega una clase Factura")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(ChatMessage.objects.count(), 0)
        self.assertEqual(self.say(self.ana, "sí").data["intent"], "ask")

    def test_if_the_proposal_cannot_be_kept_the_conversation_is_not_left_half_saved(self):
        broken = mock.Mock()
        broken.get.return_value = None
        broken.set.side_effect = ConnectionError("redis caído")
        with mock.patch("uml_api.chat_views.get_room_state", return_value=broken):
            response = self.say(self.ana, "agrega una clase Factura")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_a_saved_proposal_with_an_unexpected_shape_is_ignored_instead_of_failing(self):
        InMemoryRoomState().set(f"ia-proposal:{self.room}:{self.ana.id}", {"algo": "raro"}, 60)
        InMemoryRoomState().set(f"ia-proposal:{self.room}:{self.beto.id}", "texto", 60)

        for person in (self.ana, self.beto):
            response = self.say(person, "sí")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["intent"], "ask")
            self.assertNotIn("changes", response.data)

    def test_if_the_state_store_is_down_the_chat_still_answers_questions(self):
        broken = mock.Mock()
        broken.get.side_effect = ConnectionError("redis caído")
        with mock.patch("uml_api.chat_views.get_room_state", return_value=broken):
            response = self.say(self.ana, "¿Cuántas clases hay?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "ask")


class UnifiedChatHistoryTests(UnifiedChatBase):
    def setUp(self):
        super().setUp()
        self.add_event("Beto", "añadió la clase Factura")
        self.add_event("Ana", "renombró la clase Cliente")
        self.add_event("Beto", "añadió la relación Factura → Cliente")

    def test_what_a_person_did_comes_from_the_activity_log_without_the_ai(self):
        response = self.say(self.ana, "¿Qué hizo Beto?")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "history")
        reply = response.data["reply"]
        self.assertIn("Lo último que hizo Beto", reply)
        self.assertIn("añadió la clase Factura", reply)
        self.assertIn("añadió la relación Factura → Cliente", reply)
        self.assertNotIn("renombró", reply)
        self.assertEqual(self.provider.prompts, [])
        self.assertEqual(self.provider.change_calls, [])

    def test_the_answer_is_part_of_the_shared_conversation(self):
        self.say(self.ana, "¿Qué hizo Beto?")

        history = self.own_history(self.beto).data["messages"]

        self.assertEqual([m["author_name"] for m in history], ["Ana", "IA"])
        self.assertIn("Beto", history[1]["content"])

    def test_a_person_with_no_activity_is_said_so(self):
        response = self.say(self.beto, "¿Qué hizo Ana?")
        self.assertIn("Ana", response.data["reply"])
        ActivityEvent.objects.filter(actor_name="Ana").delete()

        response = self.say(self.beto, "¿Qué hizo Ana?")

        self.assertEqual(response.data["reply"], "No veo actividad de Ana en esta sala todavía.")

    def test_the_history_of_everyone_names_who_did_each_thing(self):
        response = self.say(self.ana, "Muéstrame el historial")

        self.assertEqual(response.data["intent"], "history")
        self.assertIn("Lo último que pasó en la sala", response.data["reply"])
        self.assertIn("Ana renombró la clase Cliente", response.data["reply"])
        self.assertIn("Beto añadió la clase Factura", response.data["reply"])

    def test_only_the_latest_actions_are_listed(self):
        for number in range(20):
            self.add_event("Beto", f"añadió la clase C{number}")

        reply = self.say(self.ana, "¿Qué hizo Beto?").data["reply"]

        self.assertIn("añadió la clase C19", reply)
        self.assertNotIn("añadió la clase C0\n", reply + "\n")
        self.assertIn("acciones anteriores", reply)

    def test_what_the_ai_did_at_the_request_of_a_person_counts_as_theirs(self):
        ActivityEvent.objects.create(
            room=self.room, actor_name="IA", actor_kind="ia", type="add_class",
            summary="añadió la clase Pedido (a pedido de Beto)",
        )
        ActivityEvent.objects.create(
            room=self.room, actor_name="IA", actor_kind="ia", type="ia_review",
            summary="revisó el diagrama a pedido de Ana: 1 observación", data={"requested_by": "Ana"},
        )

        beto = self.say(self.ana, "¿Qué hizo Beto?").data["reply"]
        ana = self.say(self.beto, "¿Qué hizo Ana?").data["reply"]

        self.assertIn("IA añadió la clase Pedido (a pedido de Beto)", beto)
        self.assertNotIn("revisó el diagrama", beto)
        self.assertIn("IA revisó el diagrama a pedido de Ana", ana)
        self.assertNotIn("Pedido", ana)

    def test_what_the_ai_did_can_be_asked_too(self):
        ActivityEvent.objects.create(
            room=self.room, actor_name="IA", actor_kind="ia", type="ia_review", summary="revisó el diagrama a pedido de Ana: 1 observación"
        )

        response = self.say(self.beto, "¿Qué hizo la IA?")

        self.assertEqual(response.data["intent"], "history")
        self.assertIn("revisó el diagrama a pedido de Ana", response.data["reply"])

    def test_a_name_nobody_in_the_room_has_goes_to_the_ai(self):
        response = self.say(self.ana, "¿Qué hizo Carlos?")

        self.assertEqual(response.data["intent"], "ask")
        self.assertEqual(len(self.provider.prompts), 1)

    def test_the_ai_prompt_still_carries_the_activity_for_other_questions(self):
        self.say(self.ana, "Resume lo que pasó con la clase Factura")

        self.assertIn("Beto: añadió la clase Factura", self.provider.prompts[0])


class UnifiedChatReviewTests(UnifiedChatBase):
    def test_asking_for_a_review_leaves_the_ideas_in_the_activity_history(self):
        self.provider.reply = self.review_reply([{"texto": "Falta una clave", "pedido": "agrega id a Cliente"}])

        response = self.say(self.ana, "Revisa el diagrama")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["intent"], "review")
        self.assertEqual(response.data["suggestions"], [{"id": 0, "text": "Falta una clave", "prompt": "agrega id a Cliente"}])
        self.assertIn("Las ideas quedaron en Actividad", response.data["reply"])
        event = ActivityEvent.objects.get(type="ia_review")
        self.assertEqual(event.actor_name, "IA")
        self.assertEqual(event.data["findings"][0]["text"], "Falta una clave")

    def test_a_review_without_findings_does_not_point_to_the_activity(self):
        self.provider.reply = self.review_reply([], summary="Todo se ve bien.")

        response = self.say(self.ana, "revisa mi modelo")

        self.assertNotIn("Actividad", response.data["reply"])


class UnifiedChatModeTests(UnifiedChatBase):
    def test_the_old_modes_keep_working(self):
        self.assertEqual(self.ask(self.ana, "hola", mode="ask").data["reply"], "Respuesta de prueba")
        changed = self.ask(self.ana, "agrega Factura", mode="change", uml=DIAGRAMA)
        self.assertEqual(changed.data["changes"], self.provider.change_result)
        self.assertNotIn("proposal", changed.data)

    def test_an_unknown_mode_is_refused(self):
        self.assertEqual(self.ask(self.ana, "hola", mode="otro").status_code, 400)


class RoomProviderApiTests(UnifiedChatBase):
    def url(self, room=None):
        return f"/api/rooms/{room or self.room}/ia/provider/"

    def get(self, participant=None, room=None):
        headers = {"HTTP_X_PARTICIPANT_TOKEN": str(participant.token)} if participant else {}
        return self.client.get(self.url(room), **headers)

    def put(self, participant, provider, room=None):
        return self.client.put(
            self.url(room), {"provider": provider}, format="json", HTTP_X_PARTICIPANT_TOKEN=str(participant.token)
        )

    def with_options(self, gemini=True, ollama=True):
        options = [
            {"id": "gemini", "label": "Nube (Gemini)", "available": gemini},
            {"id": "ollama", "label": "Local (qwen3.5:9b)", "available": ollama},
        ]
        patcher = mock.patch("uml_api.chat_views.provider_options", return_value=options)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_it_needs_a_known_participant(self):
        self.with_options()

        self.assertEqual(self.get().status_code, 403)
        stranger = Participant(room=self.room, token=uuid.uuid4(), display_name="X")
        self.assertEqual(self.get(stranger).status_code, 403)
        self.assertEqual(self.put(stranger, "ollama").status_code, 403)

    def test_it_says_which_model_answers_and_which_are_available(self):
        self.with_options(ollama=False)

        with self.settings(AI_PROVIDER="gemini"):
            response = self.get(self.ana)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "gemini")
        self.assertEqual([(o["id"], o["available"]) for o in response.data["options"]], [("gemini", True), ("ollama", False)])

    def test_the_room_can_switch_to_the_local_model_and_everyone_sees_it(self):
        self.with_options()

        response = self.put(self.ana, "ollama")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider"], "ollama")
        self.assertEqual(self.get(self.beto).data["provider"], "ollama")
        event = ActivityEvent.objects.get(type="ia_provider")
        self.assertEqual(event.actor_name, "Ana")
        self.assertIn("cambió la IA de la sala a Local", event.summary)
        self.assertEqual(self.layer.sent[0][1]["event"]["type"], "ia_provider")

    def test_the_chat_then_uses_the_model_the_room_chose(self):
        self.with_options()
        self.put(self.ana, "ollama")

        with mock.patch("uml_api.chat_views.get_ai_provider", return_value=self.provider) as chosen:
            self.say(self.beto, "¿Cuántas clases hay?")

        chosen.assert_called_once_with("ollama")

    def test_without_a_choice_the_chat_uses_the_server_default(self):
        with mock.patch("uml_api.chat_views.get_ai_provider", return_value=self.provider) as chosen:
            self.say(self.beto, "¿Cuántas clases hay?")

        chosen.assert_called_once_with(None)

    def test_a_model_this_server_does_not_have_is_refused(self):
        self.with_options(ollama=False)

        response = self.put(self.ana, "ollama")

        self.assertEqual(response.status_code, 409)
        self.assertIn("no está disponible", response.data["error"])
        self.assertFalse(ActivityEvent.objects.filter(type="ia_provider").exists())

    def test_an_unknown_model_is_refused(self):
        self.with_options()

        self.assertEqual(self.put(self.ana, "gpt").status_code, 400)
        self.assertEqual(self.put(self.ana, None).status_code, 400)

    def test_choosing_the_same_model_again_does_not_spam_the_activity(self):
        self.with_options()
        self.put(self.ana, "ollama")
        self.put(self.beto, "ollama")

        self.assertEqual(ActivityEvent.objects.filter(type="ia_provider").count(), 1)

    def test_flipping_the_model_over_and_over_is_throttled(self):
        self.with_options()

        results = [self.put(self.ana, "ollama" if n % 2 == 0 else "gemini").status_code for n in range(7)]

        self.assertEqual(results, [200] * 6 + [429])
        self.assertEqual(ActivityEvent.objects.filter(type="ia_provider").count(), 6)
        # el modelo se quedó como estaba: el último cambio no se hizo
        self.assertEqual(self.get(self.ana).data["provider"], "gemini")

    def test_a_failing_limiter_does_not_block_the_change(self):
        self.with_options()
        broken = mock.Mock()
        broken.allow.side_effect = ConnectionError("redis caído")

        with mock.patch("uml_api.chat_views.get_rate_limiter", return_value=broken):
            response = self.put(self.ana, "ollama")

        self.assertEqual(response.status_code, 200)

    def test_each_room_has_its_own_model(self):
        self.with_options()
        self.put(self.ana, "ollama")
        outsider = Participant.objects.create(room="otra-sala", token=uuid.uuid4(), display_name="Eva")

        with self.settings(AI_PROVIDER="gemini"):
            response = self.get(outsider, room="otra-sala")

        self.assertEqual(response.data["provider"], "gemini")
