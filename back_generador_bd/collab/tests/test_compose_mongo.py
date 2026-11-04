"""El servicio `mongo` de `docker-compose.db.yml` solo arranca si se pide, exige autenticación y no recibe el `.env` completo.

MongoDB es opcional (C3): la actividad y la conversación quedan en PostgreSQL salvo que `ACTIVITY_STORE` / `CONVERSATION_STORE` valgan `mongo`. Si el servicio
arrancara con el resto de la base de datos, ocuparía memoria en la máquina de 2 GB sin que nadie lo use, y con `env_file` recibiría también la clave de Gemini y la
contraseña de PostgreSQL. Se lee el texto del archivo (no hay un lector de YAML en este entorno).
"""

from pathlib import Path
from unittest import SkipTest

from django.test import SimpleTestCase

COMPOSE = Path(__file__).resolve().parents[3] / "docker-compose.db.yml"
VARIABLES_DE_MONGO = {"MONGO_INITDB_ROOT_USERNAME", "MONGO_INITDB_ROOT_PASSWORD"}


def bloque_de_servicio(texto, nombre):
    """Las líneas del servicio `nombre`, sin la línea de su nombre, hasta el siguiente servicio o sección."""
    lineas = texto.splitlines()
    inicio = next(i for i, linea in enumerate(lineas) if linea == f"  {nombre}:")
    bloque = []
    for linea in lineas[inicio + 1:]:
        if linea.strip() and not linea.startswith("   ") and not linea.lstrip().startswith("#"):
            break
        bloque.append(linea)
    return bloque


class ComposeMongoTests(SimpleTestCase):
    def setUp(self):
        if not COMPOSE.exists():
            raise SkipTest("docker-compose.db.yml no está en esta copia del repositorio")
        self.texto = COMPOSE.read_text(encoding="utf-8")
        self.mongo = bloque_de_servicio(self.texto, "mongo")

    def test_mongo_solo_arranca_con_su_perfil(self):
        self.assertIn('    profiles: ["mongo"]', self.mongo)

    def test_mongo_no_recibe_el_env_completo(self):
        self.assertFalse([linea for linea in self.mongo if linea.strip().startswith("env_file")])

    def test_mongo_recibe_solo_su_usuario_y_su_clave_por_nombre(self):
        inicio = self.mongo.index("    environment:")
        variables = []
        for linea in self.mongo[inicio + 1:]:
            if not linea.startswith("      - "):
                break
            variables.append(linea.removeprefix("      - ").strip())
        self.assertEqual(set(variables), VARIABLES_DE_MONGO)
        self.assertTrue(all("=" not in v for v in variables), "los valores se leen del entorno, no se escriben en el archivo")

    def test_mongo_exige_autenticacion(self):
        comando = next(linea for linea in self.mongo if linea.strip().startswith("command:"))
        self.assertIn('"--auth"', comando)

    def test_postgres_sigue_arrancando_sin_perfil(self):
        postgres = bloque_de_servicio(self.texto, "postgres")
        self.assertFalse([linea for linea in postgres if linea.strip().startswith("profiles")])
