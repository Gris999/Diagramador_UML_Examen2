import re
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

from django.test import SimpleTestCase
from rest_framework.test import APIClient

from uml_api.services.flutter_generator import FlutterCRUDGenerator


REPRESENTATIVE_UML = {
    "classes": [
        {
            "id": "person",
            "name": "Person",
            "attributes": [
                {"name": "id", "type": "int"},
                {"name": "name", "type": "String"},
                {"name": "active", "type": "Boolean"},
            ],
        },
        {
            "id": "pet",
            "name": "Pet",
            "attributes": [
                {"name": "id", "type": "int"},
                {"name": "nickname", "type": "String"},
            ],
        },
        {
            "id": "role",
            "name": "Role",
            "attributes": [
                {"name": "id", "type": "int"},
                {"name": "label", "type": "String"},
            ],
        },
        {
            "id": "employee",
            "name": "Employee",
            "attributes": [
                {"name": "salary", "type": "double"},
            ],
        },
    ],
    "relationships": [
        {
            "id": "person-pets",
            "type": "association",
            "sourceId": "person",
            "targetId": "pet",
            "labels": ["1", "0..*"],
        },
        {
            "id": "person-roles",
            "type": "association",
            "sourceId": "person",
            "targetId": "role",
            "labels": ["0..*", "0..*"],
        },
        {
            "id": "employee-person",
            "type": "generalization",
            "sourceId": "employee",
            "targetId": "person",
            "labels": [],
        },
    ],
}


class FlutterGeneratorTests(SimpleTestCase):
    def test_representative_project_is_unique_complete_and_deterministic(self):
        generator = FlutterCRUDGenerator(REPRESENTATIVE_UML)

        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = Path(first_dir)
            second = Path(second_dir)
            generator.generate_project(first)
            generator.generate_project(second)

            first_files = {
                path.relative_to(first): path.read_bytes()
                for path in first.rglob("*")
                if path.is_file()
            }
            second_files = {
                path.relative_to(second): path.read_bytes()
                for path in second.rglob("*")
                if path.is_file()
            }
            self.assertEqual(first_files, second_files)

            expected_entities = ["person", "pet", "role", "employee", "person_role"]
            self.assertTrue((first / "pubspec.yaml").is_file())
            self.assertTrue((first / "lib/main.dart").is_file())
            self.assertTrue((first / "test/widget_test.dart").is_file())
            for entity in expected_entities:
                self.assertTrue((first / f"lib/models/{entity}.dart").is_file())
                self.assertTrue((first / f"lib/services/{entity}_service.dart").is_file())
                self.assertTrue((first / f"lib/views/{entity}_list_view.dart").is_file())
                self.assertTrue((first / f"lib/views/{entity}_form_view.dart").is_file())
                self.assertTrue((first / f"lib/views/{entity}_detail_view.dart").is_file())

            intermediate_files = [
                path for path in first_files
                if "person_role" in path.name
            ]
            self.assertEqual(len(intermediate_files), 5)
            self.assertIn(
                "class Employee extends Person",
                (first / "lib/models/employee.dart").read_text(),
            )

            main = (first / "lib/main.dart").read_text()
            imports = re.findall(r"^import 'views/[^']+';$", main, re.MULTILINE)
            self.assertEqual(len(imports), len(set(imports)))
            self.assertEqual(
                main.count("import 'views/person_role_list_view.dart';"),
                1,
            )

    def test_generated_source_regresses_known_analyzer_failures(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)

            person_detail = (output / "lib/views/person_detail_view.dart").read_text()
            pet_detail = (output / "lib/views/pet_detail_view.dart").read_text()
            self.assertNotRegex(person_detail, r"\)\)\n\s+const SizedBox")
            self.assertNotRegex(
                pet_detail,
                r"if \([^\n]+\) _buildDetailRow\([^\n]+\)\n",
            )
            self.assertIn("...item.pet.map((e) => Padding(", person_detail)
            self.assertIn(")),\n", person_detail)
            self.assertIn("item.person!.name.toString()),", pet_detail)

            form_sources = "\n".join(
                path.read_text()
                for path in (output / "lib/views").glob("*_form_view.dart")
            )
            self.assertIn("initialValue: validValue", form_sources)
            self.assertIn("initialValue: _selectedPersonId", form_sources)
            self.assertNotIn("value: validValue", form_sources)
            self.assertNotRegex(form_sources, r"\n\s+value: _selected\w+Id,")
            self.assertIn("value: item.id", form_sources)

            person_service = (output / "lib/services/person_service.dart").read_text()
            pet_service = (output / "lib/services/pet_service.dart").read_text()
            self.assertNotIn("../models/pet.dart", person_service)
            self.assertNotIn("../models/person_role.dart", person_service)
            self.assertNotIn("../models/person.dart", pet_service)

    def test_intermediate_detail_fallback_separates_sized_box_child(self):
        uml = {
            "classes": [
                {
                    "id": "empty",
                    "name": "Empty",
                    "attributes": [{"name": "id", "type": "int"}],
                },
                {
                    "id": "label",
                    "name": "Label",
                    "attributes": [
                        {"name": "id", "type": "int"},
                        {"name": "name", "type": "String"},
                    ],
                },
            ],
            "relationships": [
                {
                    "id": "empty-labels",
                    "type": "association",
                    "sourceId": "empty",
                    "targetId": "label",
                    "labels": ["*", "*"],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(uml).generate_project(output)

            detail = (
                output / "lib/views/empty_label_detail_view.dart"
            ).read_text()
            self.assertIn(
                "_buildDetailRow('Empty', item.empty?.toString() ?? "
                "'No disponible'),\n"
                "                const SizedBox(height: 12),\n"
                "                _buildDetailRow('ID de Label'",
                detail,
            )


class FlutterGeneratorApiTests(SimpleTestCase):
    def setUp(self):
        self.client = APIClient()

    def test_valid_uml_returns_generated_zip(self):
        response = self.client.post(
            "/api/generar_flutter/",
            REPRESENTATIVE_UML,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        archive_bytes = b"".join(response.streaming_content)
        with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
            names = set(archive.namelist())
        self.assertIn("pubspec.yaml", names)
        self.assertIn("lib/main.dart", names)
        self.assertIn("test/widget_test.dart", names)

    def test_empty_classes_returns_client_error(self):
        response = self.client.post(
            "/api/generar_flutter/",
            {"classes": [], "relationships": []},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"error": "El JSON UML debe contener 'classes'."},
        )




    def test_database_helper_generated(self):
        """1. lib/database/database_helper.dart is generated"""
        import tempfile
        from pathlib import Path
        from uml_api.services.flutter_generator import FlutterCRUDGenerator
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            FlutterCRUDGenerator({"classes": [{"id": "cls_1", "name": "persona", "attributes": [{"name": "id", "type": "int"}, {"name": "is_active", "type": "bool"}]}]}).generate_project(base_path)
            db_file = base_path / 'lib' / 'database' / 'database_helper.dart'
            self.assertTrue(db_file.exists())

    def test_pubspec_contains_sqflite(self):
        """2. generated pubspec contains sqflite and path"""
        import tempfile
        from pathlib import Path
        from uml_api.services.flutter_generator import FlutterCRUDGenerator
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            FlutterCRUDGenerator({"classes": [{"id": "cls_1", "name": "persona", "attributes": [{"name": "id", "type": "int"}, {"name": "is_active", "type": "bool"}]}]}).generate_project(base_path)
            pubspec_file = base_path / 'pubspec.yaml'
            pubspec_content = pubspec_file.read_text(encoding='utf-8')
            self.assertIn('sqflite:', pubspec_content)
            self.assertIn('path:', pubspec_content)

    def test_database_schema(self):
        """3-8. DatabaseHelper contains CREATE TABLE, correct mappings, etc."""
        import tempfile
        from pathlib import Path
        from uml_api.services.flutter_generator import FlutterCRUDGenerator
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            uml = {
                "classes": [
                    {"id": "cls_1", "name": "persona", "attributes": [{"name": "id", "type": "int"}, {"name": "is_active", "type": "bool"}]},
                    {"id": "cls_2", "name": "carro", "attributes": [{"name": "id", "type": "int"}]}
                ],
                "relationships": [
                    {"sourceId": "cls_1", "targetId": "cls_2", "type": "association", "labels": ["1..*", "1..*"]}
                ]
            }
            FlutterCRUDGenerator(uml).generate_project(base_path)
            db_file = base_path / 'lib' / 'database' / 'database_helper.dart'
            db_content = db_file.read_text(encoding='utf-8')
            self.assertIn('CREATE TABLE persona', db_content)
            self.assertIn("id INTEGER PRIMARY KEY", db_content)
            self.assertIn("isactive INTEGER", db_content)
            self.assertIn('CREATE TABLE carropersona', db_content)
            self.assertIn("id INTEGER PRIMARY KEY", db_content)
            self.assertIn("personaid INTEGER", db_content)
            self.assertIn("carroid INTEGER", db_content)

    def test_boolean_normalization_in_db_helper(self):
        """9. boolean fields are normalized in DatabaseHelper"""
        import tempfile
        from pathlib import Path
        from uml_api.services.flutter_generator import FlutterCRUDGenerator
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            FlutterCRUDGenerator({"classes": [{"id": "cls_1", "name": "persona", "attributes": [{"name": "id", "type": "int"}, {"name": "is_active", "type": "bool"}]}]}).generate_project(base_path)
            db_file = base_path / 'lib' / 'database' / 'database_helper.dart'
            db_content = db_file.read_text(encoding='utf-8')
            self.assertIn("_boolColumns =", db_content)
            self.assertIn("'persona': ['isactive']", db_content)
            self.assertIn("result[col] = result[col] == true || result[col] == 1 || result[col] == 'true' ? 1 : 0", db_content)

    def test_from_json_accepts_sqlite_booleans(self):
        """10. generated fromJson accepts SQLite 1/0 and API true/false"""
        import tempfile
        from pathlib import Path
        from uml_api.services.flutter_generator import FlutterCRUDGenerator
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            FlutterCRUDGenerator({"classes": [{"id": "cls_1", "name": "persona", "attributes": [{"name": "id", "type": "int"}, {"name": "is_active", "type": "bool"}]}]}).generate_project(base_path)
            model_file = base_path / 'lib' / 'models' / 'persona.dart'
            model_content = model_file.read_text(encoding='utf-8')
            self.assertIn("is_active: json['isactive'] == true || json['isactive'] == 1 || json['isactive'] == 'true'", model_content)

    def test_local_db_fallback_in_service(self):
        """11-15. Service uses local DB fallback, Web protected, etc."""
        import tempfile
        from pathlib import Path
        from uml_api.services.flutter_generator import FlutterCRUDGenerator
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            FlutterCRUDGenerator({"classes": [{"id": "cls_1", "name": "persona", "attributes": [{"name": "id", "type": "int"}, {"name": "is_active", "type": "bool"}]}]}).generate_project(base_path)
            service_file = base_path / 'lib' / 'services' / 'persona_service.dart'
            service_content = service_file.read_text(encoding='utf-8')
            self.assertIn("if (kIsWeb) return remoteData;", service_content)
            self.assertIn("DatabaseHelper.instance.upsert", service_content)
            self.assertIn("DatabaseHelper.instance.getAll", service_content)
            self.assertIn("DatabaseHelper.instance.insertLocal", service_content)
            self.assertIn("DatabaseHelper.instance.updateLocal", service_content)
            self.assertIn("DatabaseHelper.instance.deleteLocal", service_content)
            self.assertIn("body: json.encode(item.toJson())", service_content)
