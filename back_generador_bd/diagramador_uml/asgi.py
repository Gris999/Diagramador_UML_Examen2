import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'diagramador_uml.settings')

from django.core.asgi import get_asgi_application

# Django debe cargar sus apps antes de importar las rutas: los consumers de
# collab usan modelos del ORM y fallan al importarse con las apps sin listas.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402
import collab.routing  # noqa: E402  # 👈 importa las rutas de tu app

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            collab.routing.websocket_urlpatterns  # 👈 añade aquí
        )
    ),
})
