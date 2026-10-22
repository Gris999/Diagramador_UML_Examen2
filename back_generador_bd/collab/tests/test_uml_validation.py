import asyncio
import json
import time
from unittest import mock

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, override_settings

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

