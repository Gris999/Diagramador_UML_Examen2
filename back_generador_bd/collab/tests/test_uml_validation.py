import asyncio
import json
import time
from unittest import mock

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, override_settings

from collab.consumers import UMLConsumer, ValidationBudget
from collab.routing import websocket_urlpatterns

@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
})
class UmlValidationDoesNotBlockTheServerTests(SimpleTestCase):
    """La validación llama a Gemini, que tarda: no puede congelar al resto de la sala."""

    application = URLRouter(websocket_urlpatterns)

    async def test_a_slow_ai_call_does_not_block_the_event_loop(self):
        ticks = 0

        async def heartbeat():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        def slow_gemini(prompt):
            time.sleep(0.5)  # simula la espera de red de Gemini
            return json.dumps({"validas": [], "errores": []})

        communicator = WebsocketCommunicator(self.application, "/ws/uml/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        with mock.patch("collab.consumers.call_gemini_analysis", side_effect=slow_gemini):
            beat = asyncio.create_task(heartbeat())
            await communicator.send_json_to({
                "action": "validate_model",
                "uml": {"classes": [], "relationships": []},
            })
            result = await communicator.receive_json_from(timeout=5)
            beat.cancel()

        self.assertEqual(result["action"], "validation_result")
        # Con el bucle bloqueado el latido no avanzaría durante los 0,5 s de espera.
        self.assertGreaterEqual(ticks, 20)
        await communicator.disconnect()

    async def test_a_failing_ai_call_is_reported_without_closing_the_socket(self):
        communicator = WebsocketCommunicator(self.application, "/ws/uml/")
        await communicator.connect()

        with mock.patch(
            "collab.consumers.call_gemini_analysis",
            side_effect=RuntimeError("sin clave"),
        ):
            await communicator.send_json_to({"action": "validate_model", "uml": {}})
            result = await communicator.receive_json_from(timeout=5)

        self.assertEqual(result["action"], "validation_result")
        self.assertIn("error", result["analysis"])
        await communicator.disconnect()

    async def test_a_burst_of_requests_costs_a_single_ai_call(self):
        calls = []

        def slow_gemini(prompt):
            calls.append(prompt)
            time.sleep(0.3)
            return json.dumps({"validas": [], "errores": []})

        communicator = WebsocketCommunicator(self.application, "/ws/uml/")
        await communicator.connect()

        with mock.patch("collab.consumers.call_gemini_analysis", side_effect=slow_gemini):
            for _ in range(5):
                await communicator.send_json_to({"action": "validate_model", "uml": {}})
            await communicator.receive_json_from(timeout=5)
            self.assertTrue(await communicator.receive_nothing(timeout=0.6))

        self.assertEqual(len(calls), 1)
        await communicator.disconnect()

    async def test_malformed_messages_are_ignored(self):
        communicator = WebsocketCommunicator(self.application, "/ws/uml/")
        await communicator.connect()

        await communicator.send_to(text_data="no es json")
        await communicator.send_json_to([1, 2, 3])
        await communicator.send_json_to({"action": "otra_cosa"})

        self.assertTrue(await communicator.receive_nothing(timeout=0.3))
        await communicator.disconnect()


@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
})
class UmlValidationLimitsTests(SimpleTestCase):
    """El tope es del servicio entero y la última validación nunca se pierde."""

    application = URLRouter(websocket_urlpatterns)

    def setUp(self):
        self.calls = []
        gemini = mock.patch(
            "collab.consumers.call_gemini_analysis", side_effect=self.fake_gemini
        )
        gemini.start()
        self.addCleanup(gemini.stop)

    def fake_gemini(self, prompt):
        self.calls.append(prompt)
        time.sleep(0.2)
        return json.dumps({"validas": [], "errores": []})

    async def connect(self):
        communicator = WebsocketCommunicator(self.application, "/ws/uml/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        return communicator

    async def test_the_last_diagram_of_a_burst_is_validated_after_the_interval(self):
        communicator = await self.connect()

        with mock.patch.object(UMLConsumer, "min_validation_interval", 0.4):
            await communicator.send_json_to({"action": "validate_model", "uml": {"v": 1}})
            await communicator.receive_json_from(timeout=5)
            await communicator.send_json_to({"action": "validate_model", "uml": {"v": 2}})
            await communicator.send_json_to({"action": "validate_model", "uml": {"v": 3}})
            result = await communicator.receive_json_from(timeout=5)

        self.assertEqual(result["action"], "validation_result")
        self.assertEqual(len(self.calls), 2)
        self.assertIn('"v": 1', self.calls[0])
        self.assertIn('"v": 3', self.calls[1])
        self.assertNotIn('"v": 2', "".join(self.calls))
        await communicator.disconnect()

    async def test_a_diagram_that_was_already_validated_is_not_validated_again(self):
        communicator = await self.connect()

        with mock.patch.object(UMLConsumer, "min_validation_interval", 0.1):
            await communicator.send_json_to({"action": "validate_model", "uml": {"v": 1}})
            await communicator.receive_json_from(timeout=5)
            await communicator.send_json_to({"action": "validate_model", "uml": {"v": 1}})
            self.assertTrue(await communicator.receive_nothing(timeout=0.5))

        self.assertEqual(len(self.calls), 1)
        await communicator.disconnect()

    async def test_validations_in_progress_are_limited_across_connections(self):
        first = await self.connect()
        second = await self.connect()

        with mock.patch.object(UMLConsumer, "budget", ValidationBudget(max_concurrent=1)):
            await first.send_json_to({"action": "validate_model", "uml": {"who": "a"}})
            await second.send_json_to({"action": "validate_model", "uml": {"who": "b"}})
            results = [
                await first.receive_json_from(timeout=5),
                await second.receive_json_from(timeout=5),
            ]

        # Cuál de las dos conexiones llega primero no importa: una sola valida.
        self.assertEqual(sum("error" in r["analysis"] for r in results), 1)
        self.assertEqual(len(self.calls), 1)
        await first.disconnect()
        await second.disconnect()

    async def test_validations_per_minute_are_limited_across_connections(self):
        communicators = [await self.connect() for _ in range(3)]

        with mock.patch.object(
            UMLConsumer, "budget", ValidationBudget(max_concurrent=5, max_per_minute=2)
        ):
            results = []
            for number, communicator in enumerate(communicators):
                await communicator.send_json_to({"action": "validate_model", "uml": {"n": number}})
                results.append(await communicator.receive_json_from(timeout=5))

        failed = [r for r in results if "error" in r["analysis"]]
        self.assertEqual(len(failed), 1)
        self.assertEqual(len(self.calls), 2)
        for communicator in communicators:
            await communicator.disconnect()

    async def test_the_slot_is_given_back_when_the_ai_call_fails(self):
        communicator = await self.connect()
        budget = ValidationBudget(max_concurrent=1)

        with mock.patch.object(UMLConsumer, "budget", budget), mock.patch(
            "collab.consumers.call_gemini_analysis", side_effect=RuntimeError("sin clave")
        ):
            await communicator.send_json_to({"action": "validate_model", "uml": {}})
            await communicator.receive_json_from(timeout=5)

        self.assertEqual(budget.active, 0)
        await communicator.disconnect()

    async def test_nothing_is_validated_after_the_connection_closes(self):
        communicator = await self.connect()

        with mock.patch.object(UMLConsumer, "min_validation_interval", 0.5):
            await communicator.send_json_to({"action": "validate_model", "uml": {"v": 1}})
            await communicator.receive_json_from(timeout=5)
            await communicator.send_json_to({"action": "validate_model", "uml": {"v": 2}})
            await communicator.disconnect()
            await asyncio.sleep(0.8)

        self.assertEqual(len(self.calls), 1)

    async def test_huge_messages_are_ignored(self):
        communicator = await self.connect()

        await communicator.send_json_to({
            "action": "validate_model",
            "uml": {"basura": "x" * (UMLConsumer.max_message_chars + 1)},
        })

        self.assertTrue(await communicator.receive_nothing(timeout=0.3))
        self.assertEqual(self.calls, [])
        await communicator.disconnect()
