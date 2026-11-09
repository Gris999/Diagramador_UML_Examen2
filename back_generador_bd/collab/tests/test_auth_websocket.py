from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TransactionTestCase, override_settings

from collab import auth
from collab.consumers import CanvasConsumer
from collab.models import RoomMember
from collab.routing import websocket_urlpatterns
from collab.tests.fakes import (
    InMemoryActivityStore,
    InMemoryIdentityStore,
    InMemoryRoleStore,
    reset_stores,
)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class WebSocketSessionTests(TransactionTestCase):
    """Con `AUTH_REQUIRED` el WebSocket solo se abre con una sesión; sin el interruptor funciona como siempre."""

    application = URLRouter(websocket_urlpatterns)

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

    def tearDown(self):
        (
            CanvasConsumer.role_store_class,
            CanvasConsumer.identity_store_class,
            CanvasConsumer.activity_store_class,
        ) = self.original

    async def allow(self, email="ana@x.com", room="auth-room"):
        """Pone al correo en la lista de la sala (como si la hubiera abierto o lo hubieran invitado)."""
        await database_sync_to_async(RoomMember.objects.create)(room=room, email=email, role="owner")

    async def open(self, query=""):
        communicator = WebsocketCommunicator(self.application, f"/ws/canvas/auth-room/{query}")
        connected, code = await communicator.connect()
        return communicator, connected, code

    async def first_message(self, communicator):
        return await communicator.receive_json_from(timeout=1)

    @override_settings(AUTH_REQUIRED=False)
    async def test_without_the_switch_anyone_connects(self):
        communicator, connected, _ = await self.open()

        self.assertTrue(connected)
        self.assertEqual((await self.first_message(communicator))["action"], "self")
        await communicator.disconnect()

    @override_settings(AUTH_REQUIRED=True)
    async def test_with_the_switch_a_connection_without_session_is_closed_with_4401(self):
        communicator, connected, _ = await self.open()

        self.assertTrue(connected)  # se acepta para poder decirle al navegador por qué se cierra
        output = await communicator.receive_output(timeout=1)
        self.assertEqual((output["type"], output["code"]), ("websocket.close", 4401))
        # y no llegó a entrar a la sala
        self.assertEqual(InMemoryRoleStore.rooms, {})

    @override_settings(AUTH_REQUIRED=True)
    async def test_a_made_up_or_expired_session_is_closed_too(self):
        for query in ("?s=inventada", "?s=", f"?s={auth.make_session('ana@x.com')}x"):
            communicator, _, _ = await self.open(query)
            output = await communicator.receive_output(timeout=1)
            self.assertEqual(output.get("code"), 4401, query)

    @override_settings(AUTH_REQUIRED=True)
    async def test_with_a_valid_session_the_connection_enters_the_room(self):
        await self.allow()
        communicator, connected, _ = await self.open(f"?s={auth.make_session('ana@x.com')}")

        self.assertTrue(connected)
        self.assertEqual((await self.first_message(communicator))["action"], "self")
        await communicator.disconnect()

    @override_settings(AUTH_REQUIRED=True)
    async def test_the_mobile_viewer_needs_a_session_too(self):
        await self.allow()
        communicator, _, _ = await self.open("?mode=viewer")
        output = await communicator.receive_output(timeout=1)
        self.assertEqual(output.get("code"), 4401)

        viewer, connected, _ = await self.open(f"?mode=viewer&s={auth.make_session('ana@x.com')}")
        self.assertTrue(connected)
        await viewer.disconnect()

    @override_settings(AUTH_REQUIRED=True)
    async def test_the_session_travels_in_the_address_only_and_not_in_a_message(self):
        await self.allow()
        communicator, _, _ = await self.open(f"?s={auth.make_session('ana@x.com')}")
        while not await communicator.receive_nothing(timeout=0.2):  # lo que llega al entrar (presencia)
            await communicator.receive_json_from(timeout=1)

        # un `hello` con una sesión inventada no cambia nada: la puerta es la conexión
        await communicator.send_json_to({"type": "hello", "token": "no-uuid", "name": "X", "session": "x"})
        self.assertTrue(await communicator.receive_nothing(timeout=0.3))
        await communicator.disconnect()

    @override_settings(AUTH_REQUIRED=True)
    async def test_a_valid_session_of_somebody_who_was_not_invited_is_closed_with_4403(self):
        await self.allow("ana@x.com")

        communicator, connected, _ = await self.open(f"?s={auth.make_session('beto@x.com')}")

        self.assertTrue(connected)
        output = await communicator.receive_output(timeout=1)
        self.assertEqual((output["type"], output["code"]), ("websocket.close", 4403))
        self.assertEqual(InMemoryRoleStore.rooms, {})

    @override_settings(AUTH_REQUIRED=True)
    async def test_the_mobile_viewer_of_somebody_who_was_not_invited_is_closed_too(self):
        await self.allow("ana@x.com")

        viewer, _, _ = await self.open(f"?mode=viewer&s={auth.make_session('beto@x.com')}")

        self.assertEqual((await viewer.receive_output(timeout=1)).get("code"), 4403)

    @override_settings(AUTH_REQUIRED=True)
    async def test_an_invited_address_enters_the_room(self):
        await self.allow("ana@x.com")
        await database_sync_to_async(RoomMember.objects.create)(room="auth-room", email="beto@x.com", role="editor")

        communicator, connected, _ = await self.open(f"?s={auth.make_session('beto@x.com')}")

        self.assertTrue(connected)
        self.assertEqual((await self.first_message(communicator))["action"], "self")
        await communicator.disconnect()

    @override_settings(AUTH_REQUIRED=True)
    async def test_a_room_nobody_opened_is_closed_so_it_has_to_be_entered_through_the_access_route_first(self):
        communicator, _, _ = await self.open(f"?s={auth.make_session('ana@x.com')}")

        self.assertEqual((await communicator.receive_output(timeout=1)).get("code"), 4403)

    @override_settings(AUTH_REQUIRED=True)
    async def test_a_viewer_cannot_open_the_editor_connection_but_can_follow_in_read_only(self):
        await database_sync_to_async(RoomMember.objects.create)(room="auth-room", email="ana@x.com", role="owner")
        await database_sync_to_async(RoomMember.objects.create)(room="auth-room", email="eva@x.com", role="viewer")
        session = auth.make_session("eva@x.com")

        editor, _, _ = await self.open(f"?s={session}")
        self.assertEqual((await editor.receive_output(timeout=1)).get("code"), 4403)

        viewer, connected, _ = await self.open(f"?mode=viewer&s={session}")
        self.assertTrue(connected)
        await viewer.disconnect()

    @override_settings(AUTH_REQUIRED=True)
    async def test_with_the_link_open_as_viewer_a_stranger_follows_but_does_not_edit_and_as_editor_edits(self):
        from collab import rooms

        await database_sync_to_async(RoomMember.objects.create)(room="auth-room", email="ana@x.com", role="owner")
        await database_sync_to_async(rooms.update_settings)("auth-room", link_access="anyone", link_role="viewer")
        session = auth.make_session("luis@x.com")

        editor, _, _ = await self.open(f"?s={session}")
        self.assertEqual((await editor.receive_output(timeout=1)).get("code"), 4403)
        viewer, connected, _ = await self.open(f"?mode=viewer&s={session}")
        self.assertTrue(connected)
        await viewer.disconnect()

        await database_sync_to_async(rooms.update_settings)("auth-room", link_role="editor")
        allowed, connected, _ = await self.open(f"?s={session}")
        self.assertTrue(connected)
        self.assertEqual((await self.first_message(allowed))["action"], "self")
        await allowed.disconnect()

    @override_settings(AUTH_REQUIRED=True)
    async def test_a_deleted_room_closes_the_connection_even_for_the_owner(self):
        from collab import rooms

        await database_sync_to_async(RoomMember.objects.create)(room="auth-room", email="ana@x.com", role="owner")
        await database_sync_to_async(rooms.delete_room)("auth-room")

        communicator, _, _ = await self.open(f"?s={auth.make_session('ana@x.com')}")

        self.assertEqual((await communicator.receive_output(timeout=1)).get("code"), 4403)

