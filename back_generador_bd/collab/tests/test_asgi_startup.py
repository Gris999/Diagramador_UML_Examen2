import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase


BACKEND_DIR = Path(__file__).resolve().parents[2]


class AsgiStartupTests(SimpleTestCase):
    def test_asgi_module_imports_in_a_fresh_process(self):
        # Los consumers importan modelos del ORM. Si asgi.py importa las rutas
        # antes de que Django cargue las apps, el servidor (daphne) no arranca,
        # pero las pruebas normales no lo notan porque ya tienen Django listo.
        # Por eso se importa el módulo en un proceso nuevo, igual que daphne.
        env = {
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "diagramador_uml.settings_test",
            "DJANGO_SECRET_KEY": os.environ.get("DJANGO_SECRET_KEY", "test"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", "test"),
        }
        result = subprocess.run(
            [sys.executable, "-c", "import diagramador_uml.asgi"],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
