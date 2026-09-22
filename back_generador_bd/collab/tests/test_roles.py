from django.test import SimpleTestCase, override_settings
from channels.layers import InMemoryChannelLayer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

from collab.consumers import CanvasConsumer
from collab.routing import websocket_urlpatterns


class InMemoryRoleStore:
    rooms = {}

    def __init__(self, channel_layer, group_name):
        self.channel_layer = channel_layer
        self.group_name = group_name

    async def join(self, channel_name):
        await self.channel_layer.group_add(self.group_name, channel_name)
        members = self.rooms.setdefault(self.group_name, [])
        if channel_name not in members:
            members.append(channel_name)
        return list(members)

    async def leave(self, channel_name):
        await self.channel_layer.group_discard(self.group_name, channel_name)
        members = self.rooms.get(self.group_name, [])
        if channel_name not in members:
            return False, list(members)
        members.remove(channel_name)
        if not members:
            self.rooms.pop(self.group_name, None)
        return True, list(members)

    async def remove_by_host(self, requester, target):
        members = self.rooms.get(self.group_name, [])
        if not members or members[0] != requester or target == requester:
            return False, list(members)
        if target not in members:
            return False, list(members)
        members.remove(target)
        await self.channel_layer.group_discard(self.group_name, target)
        return True, list(members)


@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
})
class CanvasRoleTests(SimpleTestCase):
    application = URLRouter(websocket_urlpatterns)

    def setUp(self):
        InMemoryRoleStore.rooms.clear()
        self.original_role_store = CanvasConsumer.role_store_class
        CanvasConsumer.role_store_class = InMemoryRoleStore

    def tearDown(self):
        CanvasConsumer.role_store_class = self.original_role_store

    async def connect_client(self, room="roles"):
        communicator = WebsocketCommunicator(
            self.application,
            f"/ws/canvas/{room}/",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        join = await self.receive_until(
            communicator,
            lambda message: message.get("type") == "presence"
            and message.get("action") == "join",
        )
        state = await self.receive_state(communicator)
        return communicator, join["peer"], state

    async def receive_until(self, communicator, predicate):
        for _ in range(12):
            message = await communicator.receive_json_from(timeout=1)
            if predicate(message):
                return message
        self.fail("Expected WebSocket message was not received")

    async def receive_state(self, communicator, member_count=None):
        return await self.receive_until(
            communicator,
            lambda message: message.get("type") == "presence"
            and message.get("action") == "state"
            and (
                member_count is None
                or len(message.get("members", [])) == member_count
            ),
        )

    def assert_roles(self, state, expected):
        self.assertEqual(
            [(member["peer"], member["role"]) for member in state["members"]],
            expected,
        )

    async def test_join_order_assigns_roles_and_empty_room_resets_host(self):
        first, first_id, first_state = await self.connect_client()
        self.assert_roles(first_state, [(first_id, "host")])

        second, second_id, second_state = await self.connect_client()
        self.assert_roles(
            second_state,
            [(first_id, "host"), (second_id, "participant")],
        )
        await self.receive_state(first, 2)

        third, third_id, third_state = await self.connect_client()
        self.assert_roles(
            third_state,
            [
                (first_id, "host"),
                (second_id, "participant"),
                (third_id, "participant"),
            ],
        )

        await third.disconnect()
        await second.disconnect()
        await first.disconnect()

        replacement, replacement_id, replacement_state = await self.connect_client()
        self.assert_roles(replacement_state, [(replacement_id, "host")])
        await replacement.disconnect()

    async def test_participant_cannot_remove_another_participant(self):
        host, _, _ = await self.connect_client()
        participant, _, _ = await self.connect_client()
        await self.receive_state(host, 2)
        target, target_id, _ = await self.connect_client()
        await self.receive_state(host, 3)
        await self.receive_state(participant, 3)

        await participant.send_json_to({
            "type": "remove_participant",
            "peer": target_id,
        })

        rejection = await self.receive_until(
            participant,
            lambda message: message.get("type") == "remove_rejected",
        )
        self.assertEqual(rejection, {"type": "remove_rejected"})
        self.assertTrue(await target.receive_nothing(timeout=0.05))

        await target.disconnect()
        await participant.disconnect()
        await host.disconnect()

    async def test_host_can_remove_participant(self):
        host, _, _ = await self.connect_client()
        participant, participant_id, _ = await self.connect_client()
        await self.receive_state(host, 2)

        await host.send_json_to({
            "type": "remove_participant",
            "peer": participant_id,
        })

        removal = await self.receive_until(
            host,
            lambda message: message.get("type") == "presence"
            and message.get("action") == "remove",
        )
        self.assertEqual(removal["peer"], participant_id)
        state = await self.receive_state(host, 1)
        self.assertEqual(state["members"][0]["role"], "host")

        removed = await participant.receive_json_from(timeout=1)
        self.assertEqual(removed["type"], "removed")
        close_event = await participant.receive_output(timeout=1)
        self.assertEqual(close_event["type"], "websocket.close")
        self.assertEqual(close_event["code"], 4003)

        await participant.disconnect()
        await host.disconnect()

    async def test_host_disconnect_promotes_longest_connected_participant(self):
        host, _, _ = await self.connect_client()
        second, second_id, _ = await self.connect_client()
        await self.receive_state(host, 2)
        third, third_id, _ = await self.connect_client()
        await self.receive_state(host, 3)
        await self.receive_state(second, 3)

        await host.disconnect()

        promoted_state = await self.receive_state(second, 2)
        self.assert_roles(
            promoted_state,
            [(second_id, "host"), (third_id, "participant")],
        )
        third_state = await self.receive_state(third, 2)
        self.assert_roles(
            third_state,
            [(second_id, "host"), (third_id, "participant")],
        )

        await third.disconnect()
        await second.disconnect()

    async def test_direct_signaling_payload_remains_unchanged(self):
        sender, sender_id, _ = await self.connect_client()
        receiver, receiver_id, _ = await self.connect_client()
        await self.receive_state(sender, 2)
        payload = {"type": "ice", "candidate": {"candidate": "candidate-1"}}

        await sender.send_json_to({
            "type": "signal",
            "to": receiver_id,
            "payload": payload,
        })

        signal = await self.receive_until(
            receiver,
            lambda message: message.get("type") == "signal",
        )
        self.assertEqual(signal, {
            "type": "signal",
            "from": sender_id,
            "payload": payload,
        })

        await receiver.disconnect()
        await sender.disconnect()

    async def test_room_broadcast_payload_reaches_other_client_unchanged(self):
        sender, sender_id, _ = await self.connect_client()
        receiver, _, _ = await self.connect_client()
        await self.receive_state(sender, 2)
        payload = {
            "t": "move",
            "id": "class-1",
            "x": 40,
            "y": 60,
        }

        await sender.send_json_to({
            "type": "broadcast",
            "payload": payload,
        })

        broadcast = await self.receive_until(
            receiver,
            lambda message: message.get("type") == "broadcast"
            and message.get("payload") == payload,
        )
        self.assertEqual(broadcast, {
            "type": "broadcast",
            "from": sender_id,
            "payload": payload,
        })

        await receiver.disconnect()
        await sender.disconnect()
