"""Crear el adaptador de actividad al conectar no debe bloquear el bucle de eventos del servidor.

Con MongoDB en otra máquina (por ejemplo Atlas), `get_activity_store()` abre la conexión y crea los índices la primera vez, y si la base no responde espera
hasta el tiempo límite de selección de servidor. Hecho dentro de `connect` (que corre en el bucle de eventos), una base caída congelaría a todas las salas;
hecho en un hilo, solo espera esa conexión.
"""

import asyncio

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, override_settings

from collab.consumers import CanvasConsumer
from collab.routing import websocket_urlpatterns
from collab.tests.fakes import InMemoryActivityStore, InMemoryIdentityStore, InMemoryRoleStore, reset_stores


class StoreThatNotesWhereItWasBuilt(InMemoryActivityStore):
    built_on_event_loop = []

    def __init__(self):
        try:
            asyncio.get_running_loop()
            self.built_on_event_loop.append(True)
        except RuntimeError:
            self.built_on_event_loop.append(False)


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ConnectStoreOffEventLoopTests(SimpleTestCase):
    application = URLRouter(websocket_urlpatterns)

    def setUp(self):
        reset_stores()
        StoreThatNotesWhereItWasBuilt.built_on_event_loop = []
        self.original = (CanvasConsumer.role_store_class, CanvasConsumer.identity_store_class, CanvasConsumer.activity_store_class)
        CanvasConsumer.role_store_class = InMemoryRoleStore
        CanvasConsumer.identity_store_class = InMemoryIdentityStore
        CanvasConsumer.activity_store_class = StoreThatNotesWhereItWasBuilt

    def tearDown(self):
        CanvasConsumer.role_store_class, CanvasConsumer.identity_store_class, CanvasConsumer.activity_store_class = self.original

    async def test_the_activity_store_is_built_outside_the_event_loop(self):
        communicator = WebsocketCommunicator(self.application, "/ws/canvas/store-thread-room/")
        connected, _ = await communicator.connect()

        self.assertTrue(connected)
        self.assertEqual(StoreThatNotesWhereItWasBuilt.built_on_event_loop, [False])
        await communicator.disconnect()
