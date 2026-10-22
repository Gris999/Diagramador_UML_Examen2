import uuid
from unittest import mock

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, override_settings

from collab.consumers import CanvasConsumer
from collab.routing import websocket_urlpatterns
from collab.tests.fakes import (
    InMemoryActivityStore,
    InMemoryIdentityStore,
    InMemoryRoleStore,
    reset_stores,
)


@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
})
class ViewerModeTests(SimpleTestCase):
    """Los observadores (vista móvil) reciben la sala en vivo pero no la integran."""

    application = URLRouter(websocket_urlpatterns)
    room = "viewer-room"

    def setUp(self):
        reset_stores()
        self.original = (
            CanvasConsumer.role_store_class,
            CanvasConsumer.identity_store_class,
            CanvasConsumer.activity_store_class,
        )
        CanvasConsumer.role_store_class = InMemoryRoleStore
        CanvasConsumer.identity_store_class = InMemoryIdentityStore
        CanvasConsumer.activity_store_class = InMemoryActivityStore
        CanvasConsumer.viewer_counts.clear()
        CanvasConsumer.last_room_state_request.clear()

    def tearDown(self):
        (
            CanvasConsumer.role_store_class,
            CanvasConsumer.identity_store_class,
            CanvasConsumer.activity_store_class,
        ) = self.original

    async def connect(self, viewer=False):
        suffix = "?mode=viewer" if viewer else ""
        communicator = WebsocketCommunicator(
            self.application,
            f"/ws/canvas/{self.room}/{suffix}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        welcome = await communicator.receive_json_from(timeout=1)
        self.assertEqual(welcome["action"], "self")
        return communicator, welcome["peer"]

    async def receive_until(self, communicator, predicate, attempts=30):
        for _ in range(attempts):
            message = await communicator.receive_json_from(timeout=1)
            if predicate(message):
                return message
        self.fail("Expected WebSocket message was not received")

    async def assert_silent(self, communicator):
        self.assertTrue(await communicator.receive_nothing(timeout=0.3))

    async def test_a_viewer_never_becomes_host_even_if_it_connects_first(self):
        viewer, viewer_id = await self.connect(viewer=True)
        host, host_id = await self.connect()

        state = await self.receive_until(
            host,
            lambda m: m.get("action") == "state",
        )

        self.assertEqual(
            state["members"],
            [{"peer": host_id, "role": "host", "name": None}],
        )
        self.assertNotIn(viewer_id, [m["peer"] for m in state["members"]])
        await viewer.disconnect()
        await host.disconnect()

    async def test_viewers_receive_operations_and_activity_but_no_presence(self):
        viewer, _ = await self.connect(viewer=True)
        editor, _ = await self.connect()
        token = str(uuid.uuid4())
        await editor.send_json_to({"type": "hello", "token": token, "name": "Ana"})
        operation = {"t": "add_class", "id": "c1", "payload": {"name": "Cliente"}}

        await editor.send_json_to({"type": "broadcast", "payload": operation})

        relayed = await viewer.receive_json_from(timeout=1)
        activity = await viewer.receive_json_from(timeout=1)
        self.assertEqual(relayed["type"], "broadcast")
        self.assertEqual(relayed["payload"], operation)
        self.assertEqual(activity["type"], "activity")
        self.assertEqual(activity["event"]["actor_name"], "Ana")
        await self.assert_silent(viewer)
        await viewer.disconnect()
        await editor.disconnect()

    async def test_viewers_cannot_send_operations_or_other_messages(self):
        viewer, _ = await self.connect(viewer=True)
        editor, editor_id = await self.connect()
        await self.receive_until(editor, lambda m: m.get("action") == "state")

        await viewer.send_json_to({
            "type": "broadcast",
            "payload": {"t": "delete", "id": "c1"},
        })
        await viewer.send_json_to({"type": "remove_participant", "peer": editor_id})
        await viewer.send_json_to({
            "type": "signal", "to": editor_id, "payload": {"type": "offer"},
        })
        await viewer.send_json_to({
            "type": "hello", "token": str(uuid.uuid4()), "name": "Intruso",
        })

        await self.assert_silent(editor)
        self.assertEqual(InMemoryActivityStore.events, [])
        self.assertEqual(InMemoryActivityStore.identify_calls, 0)
        await viewer.disconnect()
        await editor.disconnect()

    async def test_a_viewer_can_only_ask_the_room_for_the_full_state(self):
        viewer, viewer_id = await self.connect(viewer=True)
        editor, _ = await self.connect()
        await self.receive_until(editor, lambda m: m.get("action") == "state")

        await viewer.send_json_to({
            "type": "broadcast",
            "payload": {"t": "request_full_state"},
        })
        asked = await self.receive_until(
            editor,
            lambda m: m.get("type") == "broadcast",
        )
        self.assertEqual(asked["from"], viewer_id)
        self.assertEqual(asked["payload"], {"t": "request_full_state"})

        snapshot = {"classes": [], "relationships": []}
        await editor.send_json_to({
            "type": "broadcast",
            "payload": {"t": "full_state", "payload": snapshot},
        })
        answer = await viewer.receive_json_from(timeout=1)
        self.assertEqual(answer["payload"]["t"], "full_state")
        await viewer.disconnect()
        await editor.disconnect()

    async def test_viewers_do_not_affect_host_succession_when_they_leave(self):
        host, host_id = await self.connect()
        viewer, _ = await self.connect(viewer=True)
        second, second_id = await self.connect()
        await self.receive_until(
            host,
            lambda m: m.get("action") == "state" and len(m["members"]) == 2,
        )

        await viewer.disconnect()
        await host.disconnect()

        state = await self.receive_until(
            second,
            lambda m: m.get("action") == "state"
            and [x["peer"] for x in m["members"]] == [second_id],
        )
        self.assertEqual(state["members"][0]["role"], "host")
        await second.disconnect()

    async def test_a_viewer_cannot_flood_the_room_with_full_state_requests(self):
        viewer, _ = await self.connect(viewer=True)
        editor, _ = await self.connect()
        await self.receive_until(editor, lambda m: m.get("action") == "state")

        for _ in range(6):
            await viewer.send_json_to({
                "type": "broadcast",
                "payload": {"t": "request_full_state"},
            })

        received = 0
        while not await editor.receive_nothing(timeout=0.3):
            message = await editor.receive_json_from(timeout=1)
            if message.get("type") == "broadcast":
                received += 1
        self.assertEqual(received, 1)
        await viewer.disconnect()
        await editor.disconnect()

    async def test_only_the_host_is_asked_for_the_full_state(self):
        host, _ = await self.connect()
        second, _ = await self.connect()
        viewer, viewer_id = await self.connect(viewer=True)
        await self.receive_until(
            second,
            lambda m: m.get("action") == "state" and len(m["members"]) == 2,
        )
        await self.receive_until(
            host,
            lambda m: m.get("action") == "state" and len(m["members"]) == 2,
        )
        # Se descarta lo que ya estaba pendiente (presencia de las conexiones).
        for peer in (host, second):
            while not await peer.receive_nothing(timeout=0.2):
                await peer.receive_json_from(timeout=1)

        await viewer.send_json_to({
            "type": "broadcast",
            "payload": {"t": "request_full_state"},
        })

        asked = await self.receive_until(host, lambda m: m.get("type") == "broadcast")
        self.assertEqual(asked["from"], viewer_id)
        await self.assert_silent(second)
        await viewer.disconnect()
        await host.disconnect()
        await second.disconnect()

    async def test_many_viewers_together_cost_one_state_request_per_interval(self):
        editor, _ = await self.connect()
        await self.receive_until(editor, lambda m: m.get("action") == "state")
        viewers = [(await self.connect(viewer=True))[0] for _ in range(4)]

        for viewer in viewers:
            await viewer.send_json_to({
                "type": "broadcast",
                "payload": {"t": "request_full_state"},
            })

        received = 0
        while not await editor.receive_nothing(timeout=0.3):
            message = await editor.receive_json_from(timeout=1)
            if message.get("type") == "broadcast":
                received += 1
        self.assertEqual(received, 1)
        for viewer in viewers:
            await viewer.disconnect()
        await editor.disconnect()

    async def test_a_room_accepts_a_limited_number_of_viewers(self):
        with mock.patch.object(CanvasConsumer, "max_viewers_per_room", 2):
            first, _ = await self.connect(viewer=True)
            second, _ = await self.connect(viewer=True)

            refused = WebsocketCommunicator(
                self.application, f"/ws/canvas/{self.room}/?mode=viewer"
            )
            connected, _ = await refused.connect()
            self.assertFalse(connected)

            await first.disconnect()
            replacement, _ = await self.connect(viewer=True)

            await second.disconnect()
            await replacement.disconnect()
        self.assertEqual(CanvasConsumer.viewer_counts, {})

    async def test_the_viewer_limit_does_not_apply_to_editors(self):
        with mock.patch.object(CanvasConsumer, "max_viewers_per_room", 1):
            viewer, _ = await self.connect(viewer=True)
            editors = [(await self.connect())[0] for _ in range(3)]

            for editor in editors:
                await editor.disconnect()
            await viewer.disconnect()
