import json
import uuid

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, override_settings

from collab.consumers import CanvasConsumer
from collab.routing import websocket_urlpatterns
from collab.tests.fakes import (
    FailingActivityStore,
    InMemoryActivityStore,
    InMemoryIdentityStore,
    InMemoryRoleStore,
    reset_stores,
)


@override_settings(CHANNEL_LAYERS={
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
})
class CanvasIdentityActivityTests(SimpleTestCase):
    application = URLRouter(websocket_urlpatterns)

    def setUp(self):
        reset_stores()
        self.original_role_store = CanvasConsumer.role_store_class
        self.original_identity_store = CanvasConsumer.identity_store_class
        self.original_activity_store = CanvasConsumer.activity_store_class
        CanvasConsumer.role_store_class = InMemoryRoleStore
        CanvasConsumer.identity_store_class = InMemoryIdentityStore
        CanvasConsumer.activity_store_class = InMemoryActivityStore

    def tearDown(self):
        CanvasConsumer.role_store_class = self.original_role_store
        CanvasConsumer.identity_store_class = self.original_identity_store
        CanvasConsumer.activity_store_class = self.original_activity_store

    async def connect_client(self, room="activity-room"):
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
        for _ in range(30):
            message = await communicator.receive_json_from(timeout=1)
            if predicate(message):
                return message
        self.fail("Expected WebSocket message was not received")

    async def receive_state(self, communicator, predicate=lambda _members: True):
        return await self.receive_until(
            communicator,
            lambda message: message.get("type") == "presence"
            and message.get("action") == "state"
            and predicate(message.get("members", [])),
        )

    async def send_hello(self, communicator, token, name):
        await communicator.send_json_to({
            "type": "hello",
            "token": token,
            "name": name,
        })

    async def test_hello_adds_sanitized_names_and_late_joiner_sees_them(self):
        first, first_id, _ = await self.connect_client()
        first_token = str(uuid.uuid4())
        await self.send_hello(first, first_token, "  Ana\nMaría  ")
        first_named = await self.receive_state(
            first,
            lambda members: members[0].get("name") == "AnaMaría",
        )
        self.assertEqual(first_named["members"][0]["peer"], first_id)

        second, second_id, second_state = await self.connect_client()
        self.assertEqual(
            second_state["members"],
            [
                {"peer": first_id, "role": "host", "name": "AnaMaría"},
                {"peer": second_id, "role": "participant", "name": None},
            ],
        )

        await self.send_hello(second, str(uuid.uuid4()), "Bruno")
        both_named = await self.receive_state(
            first,
            lambda members: len(members) == 2
            and members[1].get("name") == "Bruno",
        )
        self.assertEqual(
            [member["name"] for member in both_named["members"]],
            ["AnaMaría", "Bruno"],
        )

        await second.disconnect()
        await first.disconnect()

    async def test_invalid_hello_is_ignored_and_legacy_activity_is_anonymous(self):
        client, _, _ = await self.connect_client()

        await self.send_hello(client, "not-a-uuid", "Ignored")
        await self.send_hello(client, str(uuid.uuid4()), "")
        await self.send_hello(client, str(uuid.uuid4()), "x" * 41)
        await client.send_json_to({
            "type": "broadcast",
            "payload": {"t": "add_class", "id": "class-1", "payload": {}},
        })

        activity = await self.receive_until(
            client,
            lambda message: message.get("type") == "activity",
        )
        self.assertIsNone(activity["event"]["actor"])
        self.assertEqual(activity["event"]["actor_name"], "Usuario anónimo")
        self.assertEqual(InMemoryIdentityStore.rooms, {})

        await client.disconnect()

    async def test_named_activity_reaches_all_three_clients(self):
        clients = []
        for name in ("Ana", "Bruno", "Carla"):
            client, _, _ = await self.connect_client()
            clients.append(client)
            await self.send_hello(client, str(uuid.uuid4()), name)

        for client in clients:
            state = await self.receive_state(
                client,
                lambda members: len(members) == 3
                and [member.get("name") for member in members]
                == ["Ana", "Bruno", "Carla"],
            )
            self.assertEqual(len(state["members"]), 3)

        payload = {
            "t": "add_class",
            "id": "class-client",
            "payload": {"name": "Cliente"},
        }
        await clients[1].send_json_to({"type": "broadcast", "payload": payload})

        for client in clients:
            activity = await self.receive_until(
                client,
                lambda message: message.get("type") == "activity"
                and message.get("event", {}).get("target_id") == "class-client",
            )
            self.assertEqual(activity["event"]["actor_name"], "Bruno")
            self.assertIsNotNone(activity["event"]["actor"])

        for client in reversed(clients):
            await client.disconnect()

    async def test_only_meaningful_operations_create_activity(self):
        client, _, _ = await self.connect_client()
        await self.send_hello(client, str(uuid.uuid4()), "Carla")
        await self.receive_state(
            client,
            lambda members: members[0].get("name") == "Carla",
        )

        excluded = [
            "move", "resize", "update_vertices", "move_label", "move_link",
            "edit_label", "add_label", "del_label", "request_full_state",
            "full_state",
        ]
        for event_type in excluded:
            await client.send_json_to({
                "type": "broadcast",
                "payload": {"t": event_type, "id": "ignored"},
            })

        included = [
            {"t": "add_class", "id": "c1", "payload": {"name": "Cliente"}},
            {"t": "delete", "id": "c2"},
            {"t": "add_link", "id": "l1", "sourceId": "c1", "targetId": "c2"},
            {"t": "edit_text", "id": "c1", "field": "attributes", "value": "id: int"},
        ]
        for payload in included:
            await client.send_json_to({"type": "broadcast", "payload": payload})

        received = []
        for _ in included:
            activity = await self.receive_until(
                client,
                lambda message: message.get("type") == "activity",
            )
            received.append(activity["event"]["type"])

        self.assertEqual(received, [payload["t"] for payload in included])
        self.assertEqual(len(InMemoryActivityStore.events), 4)
        self.assertEqual(
            InMemoryActivityStore.events[0]["summary"],
            "añadió la clase Cliente",
        )
        self.assertEqual(
            InMemoryActivityStore.events[-1]["summary"],
            "editó los atributos",
        )

        await client.disconnect()

    async def test_repeated_edit_for_same_target_and_field_is_coalesced(self):
        client, _, _ = await self.connect_client()
        payload = {
            "t": "edit_text",
            "id": "class-1",
            "field": "methods",
            "value": "save(): void",
        }

        await client.send_json_to({"type": "broadcast", "payload": payload})
        await self.receive_until(client, lambda message: message.get("type") == "activity")
        await client.send_json_to({"type": "broadcast", "payload": payload})
        await client.send_json_to({"type": "broadcast", "payload": payload})
        await client.send_json_to({
            "type": "broadcast",
            "payload": {"t": "move", "id": "class-1", "x": 1, "y": 2},
        })
        await self.receive_until(
            client,
            lambda message: message.get("type") == "broadcast"
            and message.get("payload", {}).get("t") == "move",
        )

        self.assertEqual(len(InMemoryActivityStore.events), 1)
        await client.disconnect()

    async def test_a_new_connection_is_told_its_own_peer_id_before_anything_else(self):
        first, first_id, _ = await self.connect_client()
        second = WebsocketCommunicator(self.application, "/ws/canvas/activity-room/")
        connected, _ = await second.connect()
        self.assertTrue(connected)

        welcome = await second.receive_json_from(timeout=1)

        # Aunque otro participante haya entrado justo antes, el primer mensaje
        # identifica a esta conexión y no a la del otro.
        self.assertEqual(welcome["type"], "presence")
        self.assertEqual(welcome["action"], "self")
        self.assertNotEqual(welcome["peer"], first_id)
        own_join = await self.receive_until(
            second,
            lambda message: message.get("action") == "join"
            and message.get("peer") == welcome["peer"],
        )
        self.assertEqual(own_join["peer"], welcome["peer"])
        await second.disconnect()
        await first.disconnect()

    async def test_operations_applied_by_the_ia_are_logged_on_behalf_of_the_requester(self):
        client, _, _ = await self.connect_client()
        await self.send_hello(client, str(uuid.uuid4()), "Ana")
        await self.receive_state(
            client,
            lambda members: members[0].get("name") == "Ana",
        )

        await client.send_json_to({
            "type": "broadcast",
            "payload": {
                "t": "add_class",
                "id": "c9",
                "payload": {"name": "Factura"},
                "via_ia": True,
            },
        })
        ia_activity = await self.receive_until(
            client,
            lambda message: message.get("type") == "activity",
        )
        await client.send_json_to({
            "type": "broadcast",
            "payload": {"t": "add_class", "id": "c10", "payload": {"name": "Pago"}},
        })
        user_activity = await self.receive_until(
            client,
            lambda message: message.get("type") == "activity",
        )

        self.assertEqual(ia_activity["event"]["actor_kind"], "ia")
        self.assertEqual(ia_activity["event"]["actor_name"], "IA")
        self.assertEqual(
            ia_activity["event"]["summary"],
            "añadió la clase Factura (a pedido de Ana)",
        )
        self.assertEqual(
            InMemoryActivityStore.events[0]["actor"],
            InMemoryActivityStore.participants[
                next(iter(InMemoryActivityStore.participants))
            ]["id"],
        )
        self.assertEqual(user_activity["event"]["actor_kind"], "user")
        self.assertEqual(user_activity["event"]["actor_name"], "Ana")
        await client.disconnect()

    async def test_only_a_literal_true_marks_an_operation_as_ia(self):
        client, _, _ = await self.connect_client()
        await self.send_hello(client, str(uuid.uuid4()), "Ana")

        for flag in ("true", 1, "yes"):
            await client.send_json_to({
                "type": "broadcast",
                "payload": {"t": "delete", "id": f"c-{flag}", "via_ia": flag},
            })
            await self.receive_until(
                client,
                lambda message: message.get("type") == "activity",
            )

        self.assertEqual(
            {event["actor_kind"] for event in InMemoryActivityStore.events},
            {"user"},
        )
        await client.disconnect()

    async def test_oversized_operation_data_is_not_stored_whole(self):
        client, _, _ = await self.connect_client()
        payload = {
            "t": "add_class",
            "id": "big-class",
            "payload": {"name": "Cliente", "junk": "x" * 50_000},
        }

        await client.send_json_to({"type": "broadcast", "payload": payload})
        activity = await self.receive_until(
            client,
            lambda message: message.get("type") == "activity",
        )

        stored = InMemoryActivityStore.events[0]
        self.assertLessEqual(len(json.dumps(stored["data"])), 8192)
        self.assertEqual(stored["data"]["id"], "big-class")
        self.assertEqual(activity["event"]["summary"], "añadió la clase Cliente")
        await client.disconnect()

    async def test_activity_flood_is_capped_but_relay_keeps_working(self):
        original_limit = CanvasConsumer.activity_rate_limit
        CanvasConsumer.activity_rate_limit = 3
        try:
            sender, _, _ = await self.connect_client()
            receiver, _, _ = await self.connect_client()
            await self.receive_state(sender, lambda members: len(members) == 2)

            for number in range(6):
                await sender.send_json_to({
                    "type": "broadcast",
                    "payload": {"t": "delete", "id": f"class-{number}"},
                })
            relayed = []
            while len(relayed) < 6:
                message = await self.receive_until(
                    receiver,
                    lambda item: item.get("type") == "broadcast",
                )
                relayed.append(message["payload"]["id"])

            self.assertEqual(relayed, [f"class-{number}" for number in range(6)])
            self.assertEqual(len(InMemoryActivityStore.events), 3)
            await receiver.disconnect()
            await sender.disconnect()
        finally:
            CanvasConsumer.activity_rate_limit = original_limit

    async def test_repeated_identical_hello_is_not_persisted_again(self):
        client, _, _ = await self.connect_client()
        token = str(uuid.uuid4())

        for _ in range(3):
            await self.send_hello(client, token, "Dora")
        await self.send_hello(client, token, "Dora Ruiz")
        await self.receive_state(
            client,
            lambda members: members[0].get("name") == "Dora Ruiz",
        )

        self.assertEqual(InMemoryActivityStore.identify_calls, 2)
        await client.disconnect()

    async def test_activity_persistence_failure_does_not_break_relay(self):
        CanvasConsumer.activity_store_class = FailingActivityStore
        sender, sender_id, _ = await self.connect_client()
        receiver, _, _ = await self.connect_client()
        await self.receive_state(sender, lambda members: len(members) == 2)
        payload = {"t": "delete", "id": "class-1"}

        with self.assertLogs("collab.consumers", level="ERROR"):
            await sender.send_json_to({"type": "broadcast", "payload": payload})
            broadcast = await self.receive_until(
                receiver,
                lambda message: message.get("type") == "broadcast",
            )
        self.assertEqual(broadcast, {
            "type": "broadcast",
            "from": sender_id,
            "payload": payload,
        })

        await receiver.disconnect()
        await sender.disconnect()

    async def test_disconnect_and_host_removal_clean_live_identity(self):
        host, _, _ = await self.connect_client()
        participant, participant_id, _ = await self.connect_client()
        await self.receive_state(host, lambda members: len(members) == 2)
        await self.send_hello(participant, str(uuid.uuid4()), "Diego")
        await self.receive_state(
            host,
            lambda members: len(members) == 2
            and members[1].get("name") == "Diego",
        )

        await host.send_json_to({
            "type": "remove_participant",
            "peer": participant_id,
        })
        await self.receive_until(
            host,
            lambda message: message.get("type") == "presence"
            and message.get("action") == "remove",
        )

        identities = InMemoryIdentityStore.rooms.get("canvas_activity-room", {})
        self.assertNotIn(participant_id, identities)
        await participant.disconnect()
        await host.disconnect()
