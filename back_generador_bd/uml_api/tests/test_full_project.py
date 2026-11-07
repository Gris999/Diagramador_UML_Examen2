import io
import zipfile
from unittest import mock

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from uml_api.services import full_project

UML = {
    "appName": "Sistema Escolar",
    "sqlScript": "CREATE TABLE alumno (id SERIAL PRIMARY KEY);",
    "classes": [
        {"id": "a", "name": "Alumno", "attributes": [{"name": "id", "type": "int"}, {"name": "nombre", "type": "String"}]},
        {"id": "c", "name": "Curso", "attributes": [{"name": "id", "type": "int"}, {"name": "titulo", "type": "String"}]},
    ],
    "relationships": [],
}


def _fake_spring_zip(payload):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("demo/pom.xml", "<project/>")
        archive.writestr("demo/src/main/java/App.java", "class App {}")
    return buffer.getvalue()


class FullProjectTests(SimpleTestCase):
    def _names(self, data):
        return set(zipfile.ZipFile(io.BytesIO(data)).namelist())

    def test_zip_has_backend_mobile_app_sql_and_instructions(self):
        data, filename = full_project.build_full_project_zip(UML, _fake_spring_zip)

        names = self._names(data)
        self.assertEqual("sistema-escolar.zip", filename)
        self.assertIn("LEEME.md", names)
        self.assertIn("backend/demo/pom.xml", names)
        self.assertIn("app_movil/pubspec.yaml", names)
        self.assertIn("app_movil/lib/main.dart", names)
        self.assertIn("app_movil/assets/icon/app_icon.png", names)
        self.assertIn("base_de_datos/esquema.sql", names)
        archive = zipfile.ZipFile(io.BytesIO(data))
        self.assertIn("CREATE TABLE alumno", archive.read("base_de_datos/esquema.sql").decode())
        readme = archive.read("LEEME.md").decode()
        self.assertIn("Sistema Escolar", readme)
        self.assertIn("Alumno", readme)
        self.assertIn("flutter create", readme)
        self.assertIn("mvn spring-boot:run", readme)
        self.assertNotIn("mvnw", readme)
        self.assertIn("generated-app-postman-collection.json", readme)
        self.assertIn("configure_ios_local_ai.sh", readme)

    def test_the_mobile_app_gets_the_name_and_spring_only_the_diagram(self):
        seen = {}

        def spring(payload):
            seen.update(payload)
            return _fake_spring_zip(payload)

        data, _ = full_project.build_full_project_zip(UML, spring)

        self.assertEqual({"classes", "relationships"}, set(seen))  # sin appName ni sqlScript
        main = zipfile.ZipFile(io.BytesIO(data)).read("app_movil/lib/main.dart").decode()
        self.assertIn("const String _appName = 'Sistema Escolar';", main)

    def test_without_sql_or_name_it_still_builds_with_neutral_defaults(self):
        plain = {k: v for k, v in UML.items() if k not in ("appName", "sqlScript")}
        data, filename = full_project.build_full_project_zip(plain, _fake_spring_zip)
        self.assertEqual("mi-aplicacion.zip", filename)
        self.assertNotIn("base_de_datos/esquema.sql", self._names(data))

    def test_an_unreachable_backend_generator_is_reported_not_swallowed(self):
        def broken(_payload):
            raise full_project.SpringUnavailable("sin conexion")

        with self.assertRaises(full_project.SpringUnavailable):
            full_project.build_full_project_zip(UML, broken)


class FullProjectEndpointTests(SimpleTestCase):
    def test_endpoint_returns_a_zip_attachment(self):
        with mock.patch("uml_api.views.fetch_spring_zip", _fake_spring_zip):
            response = APIClient().post("/api/generar_todo/", UML, format="json")

        self.assertEqual(200, response.status_code)
        self.assertIn("sistema-escolar.zip", response["Content-Disposition"])
        names = zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))).namelist()
        self.assertIn("backend/demo/pom.xml", names)

    def test_endpoint_rejects_a_diagram_without_classes(self):
        response = APIClient().post("/api/generar_todo/", {"classes": []}, format="json")
        self.assertEqual(400, response.status_code)

    def test_endpoint_answers_502_when_the_backend_generator_is_down(self):
        def broken(_payload):
            raise full_project.SpringUnavailable("sin conexion")

        with mock.patch("uml_api.views.fetch_spring_zip", broken):
            response = APIClient().post("/api/generar_todo/", UML, format="json")

        self.assertEqual(502, response.status_code)
        self.assertIn("backend", response.json()["error"].lower())
