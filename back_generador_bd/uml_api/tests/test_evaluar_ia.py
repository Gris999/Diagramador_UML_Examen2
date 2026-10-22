import os
import subprocess
import sys
from pathlib import Path
from unittest import skipUnless

from django.test import SimpleTestCase

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "evaluar_ia.py"


@skipUnless(SCRIPT.exists(), "el script de evaluación no está en este entorno (p. ej. dentro del contenedor)")
class EvaluationVerifiersTests(SimpleTestCase):
    """Las verificaciones de la evaluación de la IA deben rechazar respuestas casi buenas.

    Sin esto, "10/10" podría significar solo "devolvió un JSON que menciona la palabra".
    """

    def test_verifiers_accept_good_answers_and_reject_nearly_good_ones(self):
        env = {
            **os.environ,
            "DJANGO_SETTINGS_MODULE": "diagramador_uml.settings_test",
            "DJANGO_SECRET_KEY": os.environ.get("DJANGO_SECRET_KEY", "test"),
            "POSTGRES_PASSWORD": os.environ.get("POSTGRES_PASSWORD", "test"),
        }
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--verificadores"],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr[-2000:])
        self.assertIn("Verificadores correctos.", result.stdout)
