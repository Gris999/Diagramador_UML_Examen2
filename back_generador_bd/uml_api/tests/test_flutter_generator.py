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

            # La infraestructura del asistente (P0) se genera para las
            # entidades UML originales, con el mismo determinismo verificado
            # arriba (first_files == second_files ya lo cubre byte a byte).
            assistant_files = [
                "app_schema.dart",
                "business_command.dart",
                "command_parser.dart",
                "command_validator.dart",
                "entity_service_adapter.dart",
                "entity_service_registry.dart",
                "command_router.dart",
                "voice_input_controller.dart",
                "assistant_view.dart",
            ]
            for filename in assistant_files:
                self.assertTrue((first / f"lib/assistant/{filename}").is_file())
            self.assertTrue((first / "test/assistant/command_parser_test.dart").is_file())
            self.assertTrue((first / "test/assistant/command_validator_test.dart").is_file())
            # PersonRole es una entidad intermedia M:N; el vocabulario del
            # asistente en este P0 solo cubre las clases UML originales.
            registry = (first / "lib/assistant/entity_service_registry.dart").read_text()
            self.assertNotIn("PersonRole", registry)
            self.assertIn("Employee", registry)

            main = (first / "lib/main.dart").read_text()
            imports = re.findall(r"^import 'views/[^']+';$", main, re.MULTILINE)
            self.assertEqual(len(imports), len(set(imports)))
            self.assertEqual(
                main.count("import 'views/person_role_list_view.dart';"),
                1,
            )
            self.assertIn("import 'assistant/assistant_view.dart';", main)
            self.assertIn("AssistantView()", main)

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


class AssistantSchemaGeneratorTests(SimpleTestCase):
    """Cobertura semántica de la infraestructura del asistente (P0)."""

    def test_pubspec_includes_speech_to_text(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            pubspec = (output / "pubspec.yaml").read_text()
            self.assertIn("speech_to_text:", pubspec)

    def test_app_schema_reflects_inheritance_and_field_metadata(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            schema = (output / "lib/assistant/app_schema.dart").read_text()

            # Herencia: Employee incluye los atributos heredados de Person
            # (id, name, active) además de su propio salary.
            employee_block = schema[schema.index("name: 'Employee'"):]
            self.assertIn("name: 'id'", employee_block[:employee_block.index("relations:")])
            self.assertIn("name: 'name'", employee_block[:employee_block.index("relations:")])
            self.assertIn("name: 'active'", employee_block[:employee_block.index("relations:")])
            self.assertIn("name: 'salary'", employee_block[:employee_block.index("relations:")])

            # PK numérica: autoincremental, no requerida en CREATE.
            person_block = schema[schema.index("name: 'Person'"):schema.index("name: 'Pet'")]
            self.assertIn("isPrimaryKey: true", person_block)
            self.assertIn("isAutoIncrement: true", person_block)

            # Tipos Dart y claves JSON correctos para cada tipo soportado.
            self.assertIn("dartType: 'int'", schema)
            self.assertIn("dartType: 'String'", schema)
            self.assertIn("dartType: 'bool'", schema)
            self.assertIn("jsonKey: 'active'", schema)

            # PK double explícita en el modelo: Employee hereda la PK int de
            # Person, así que se prueba por separado en otro test.

            # Heurística de nameField: 'label' está en la lista de prioridad,
            # 'nickname' cae al primer campo String no-PK por no estarlo.
            self.assertIn("nameField: 'label'", schema)
            self.assertIn("nameField: 'nickname'", schema)

    def test_intermediate_entities_excluded_from_app_schema(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            schema = (output / "lib/assistant/app_schema.dart").read_text()
            # PersonRole (la entidad intermedia M:N) nunca es una entidad de
            # primera clase del asistente: no tiene su propia
            # AssistantEntitySchema ni puede resolverse por nombre. Sí puede
            # aparecer como targetEntity de una relación one-to-many
            # (Person/Role realmente tienen esa colección), lo cual es
            # metadata descriptiva y no vocabulario invocable.
            self.assertNotIn("name: 'PersonRole'", schema)
            self.assertIn("targetEntity: 'PersonRole'", schema)

    def test_registry_wires_existing_generated_services(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            registry = (output / "lib/assistant/entity_service_registry.dart").read_text()
            for entity, snake in [("Person", "person"), ("Pet", "pet"), ("Role", "role"), ("Employee", "employee")]:
                self.assertIn(f"import '../services/{snake}_service.dart';", registry)
                self.assertIn(f"{entity}Service _service = {entity}Service();", registry)
            self.assertNotIn("DatabaseHelper", registry)
            self.assertNotIn("package:http", registry)

    def test_date_field_marked_unwritable_and_required_relation_flagged(self):
        uml = {
            "classes": [
                {
                    "id": "cita",
                    "name": "Cita",
                    "attributes": [
                        {"name": "id", "type": "int"},
                        {"name": "fecha", "type": "Date"},
                    ],
                },
                {
                    "id": "paciente",
                    "name": "Paciente",
                    "attributes": [
                        {"name": "id", "type": "int"},
                        {"name": "nombre", "type": "String"},
                    ],
                },
            ],
            "relationships": [
                {
                    "id": "cita-paciente",
                    "type": "association",
                    "sourceId": "cita",
                    "targetId": "paciente",
                    "labels": ["*", "1"],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(uml).generate_project(output)
            schema = (output / "lib/assistant/app_schema.dart").read_text()
            cita_block = schema[schema.index("name: 'Cita'"):schema.index("name: 'Paciente'")]

            # Date se mapea a DateTime en Dart y se marca no escribible: no
            # se corrige la generación de fechas en esta feature, solo se
            # falla de forma cerrada en el asistente.
            self.assertIn("dartType: 'DateTime'", cita_block)
            fecha_field = cita_block[cita_block.index("name: 'fecha'"):]
            self.assertIn("writable: false", fecha_field[:fecha_field.index(")")])

            # Relación many-to-one obligatoria: el asistente exige el ID
            # crudo, nunca resuelve el nombre relacionado.
            self.assertIn("targetEntity: 'Paciente'", cita_block)
            self.assertIn("requiredOnCreate: true", cita_block[cita_block.index("AssistantRelationField"):])

            validator = (output / "lib/assistant/command_validator.dart").read_text()
            self.assertIn("dartType == 'double'", validator)
            self.assertIn("case 'DateTime':\n        return null;", validator)

    def test_main_exposes_assistant_entry_point(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            main = (output / "lib/main.dart").read_text()
            self.assertIn("FloatingActionButton", main)
            self.assertIn("AssistantView()", main)

    def test_setup_documentation_exists(self):
        repo_root = Path(__file__).resolve().parents[3]
        setup_doc = repo_root / "docs" / "FLUTTER_ASSISTANT_SETUP.md"
        self.assertTrue(setup_doc.is_file())
        content = setup_doc.read_text()
        self.assertIn("NSMicrophoneUsageDescription", content)
        self.assertIn("RECORD_AUDIO", content)
        self.assertNotIn("on-device recognizer", content)
        self.assertIn("Dart SDK >= 3.12.0", content)

    def test_voice_controller_does_not_reference_nonexistent_generated_doc(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            controller = (output / "lib/assistant/voice_input_controller.dart").read_text()
            self.assertNotIn("docs/FLUTTER_ASSISTANT_SETUP.md", controller)

    def test_validator_applies_coerced_values_not_raw_strings(self):
        """CommandValidator must not discard the coerced value it validated."""
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            validator = (output / "lib/assistant/command_validator.dart").read_text()
            # CREATE/UPDATE/DELETE's valid() branch must be built from a NEW
            # BusinessCommand whose data is the coerced map, not the
            # original `command` (only READ legitimately returns `command`
            # unchanged, since it never writes anything).
            create_fn = validator[
                validator.index("ValidationResult _validateCreate("):
                validator.index("ValidationResult _validateMutation(")
            ]
            mutation_fn = validator[
                validator.index("ValidationResult _validateMutation("):
                validator.index("static dynamic coerce")
            ]
            self.assertIn("data: coercedData", create_fn)
            self.assertIn("data: coercedData", mutation_fn)
            self.assertNotIn("return ValidationResult.valid(command);", create_fn)
            self.assertNotIn("return ValidationResult.valid(command);", mutation_fn)

    def test_validator_rejects_explicit_autoincrement_pk_on_create(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            validator = (output / "lib/assistant/command_validator.dart").read_text()
            self.assertIn(
                "entity.pkField.isAutoIncrement && command.data.containsKey(entity.pkField.name)",
                validator,
            )

    def test_double_pk_blocks_all_mutations_but_not_read(self):
        uml = {
            "classes": [
                {
                    "id": "medida",
                    "name": "Medida",
                    "attributes": [
                        {"name": "valor", "type": "double"},
                        {"name": "etiqueta", "type": "String"},
                    ],
                },
            ],
            "relationships": [],
        }
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(uml).generate_project(output)

            schema = (output / "lib/assistant/app_schema.dart").read_text()
            medida_block = schema[schema.index("name: 'Medida'"):]
            valor_field = medida_block[medida_block.index("name: 'valor'"):medida_block.index("name: 'etiqueta'")]
            # Mirrors _generate_form_view.is_numeric_pk: a double PK is ALSO
            # generator-populated (not user-entered), same as an int PK.
            self.assertIn("isPrimaryKey: true", valor_field)
            self.assertIn("isAutoIncrement: true", valor_field)

            validator = (output / "lib/assistant/command_validator.dart").read_text()
            # The double-PK block must appear in BOTH _validateCreate and
            # _validateMutation (used by update/delete), not only create.
            create_fn = validator[
                validator.index("ValidationResult _validateCreate("):
                validator.index("ValidationResult _validateMutation(")
            ]
            mutation_fn = validator[validator.index("ValidationResult _validateMutation("):]
            self.assertIn("dartType == 'double'", create_fn)
            self.assertIn("dartType == 'double'", mutation_fn)
            # READ is untouched: validate() returns the command as-is for
            # CommandAction.read regardless of PK type.
            self.assertIn("case CommandAction.read:\n        return ValidationResult.valid(command);", validator)

    def test_router_tests_cover_coercion_pk_and_two_phase_delete(self):
        uml = {
            "classes": [
                {
                    "id": "producto",
                    "name": "Producto",
                    "attributes": [
                        {"name": "id", "type": "int"},
                        {"name": "nombre", "type": "String"},
                        {"name": "precio", "type": "double"},
                        {"name": "activo", "type": "Boolean"},
                    ],
                },
            ],
            "relationships": [],
        }
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(uml).generate_project(output)
            router_test = (output / "test/assistant/command_router_test.dart").read_text()
            self.assertIn("adapter as an actual bool", router_test)
            self.assertIn("adapter as an actual double", router_test)
            self.assertIn("lastUpdatedId", router_test)
            self.assertIn("confirmDelete deletes that exact PK without re-matching", router_test)
            self.assertIn("rows.clear()", router_test)

    def test_normalize_treats_hyphen_dash_variants_as_space(self):
        """Regression for the iOS speech_to_text hyphenation bug: a row
        stored as 'Coca cola' must match a voice-produced filter like
        'Coca-Cola'. AppSchema.normalize() is the single, central place
        that both UPDATE and DELETE matching go through (via
        CommandRouter._valuesMatch), so fixing it there fixes both."""
        uml = {
            "classes": [
                {
                    "id": "producto",
                    "name": "Producto",
                    "attributes": [
                        {"name": "id", "type": "int"},
                        {"name": "nombre", "type": "String"},
                        {"name": "precio", "type": "double"},
                        {"name": "activo", "type": "Boolean"},
                    ],
                },
            ],
            "relationships": [],
        }
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(uml).generate_project(output)

            schema = (output / "lib/assistant/app_schema.dart").read_text()
            # The fix lives only inside AppSchema.normalize(): dash/dash-like
            # variants become a space, then repeated whitespace collapses.
            self.assertIn("dashVariants", schema)
            self.assertIn("result.replaceAll(dash, ' ')", schema)
            self.assertIn("RegExp(' +')", schema)
            # Narrow scope: no general punctuation stripping was added.
            self.assertNotIn("RegExp(r'[^\\w\\s]')", schema)

            router_test = (output / "test/assistant/command_router_test.dart").read_text()
            # Direct unit-level regressions on AppSchema.normalize() itself.
            self.assertIn("final base = AppSchema.normalize('Coca cola');", router_test)
            self.assertIn("expect(base, 'coca cola');", router_test)
            self.assertIn("expect(AppSchema.normalize('Coca-Cola'), base);", router_test)
            self.assertIn("expect(AppSchema.normalize('Coca–Cola'), base);", router_test)  # en dash
            self.assertIn("expect(AppSchema.normalize('Coca—Cola'), base);", router_test)  # em dash
            self.assertIn("expect(AppSchema.normalize('Coca---Cola'), 'coca cola');", router_test)
            self.assertIn("expect(AppSchema.normalize('Coca   cola'), 'coca cola');", router_test)

            # Functional regression: a row stored with a plain space is
            # found by CommandRouter when the UPDATE filter uses a dash.
            self.assertIn(
                "UPDATE finds a row stored with a plain space using a filter written with a dash",
                router_test,
            )
            self.assertIn("nameJsonKey: 'Coca cola'", router_test)
            self.assertIn("filters: {'nombre': 'Coca-Cola'}", router_test)

            # DELETE must reuse the exact same central normalization, not a
            # duplicated matching implementation in CommandRouter.
            self.assertIn(
                "DELETE reuses the same normalized matching as UPDATE (AppSchema.normalize)",
                router_test,
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


class LocalLlmGeneratorTests(SimpleTestCase):
    """Cobertura del trabajo Local-LLM Phase A: pubspec, script de setup de
    iOS, y que la extraccion local por LLM no hardcodee ningun esquema."""

    ALTERNATE_UML = {
        "classes": [
            {
                "id": "vehiculo",
                "name": "Vehiculo",
                "attributes": [
                    {"name": "id", "type": "int"},
                    {"name": "placa", "type": "String"},
                    {"name": "kilometraje", "type": "int"},
                ],
            },
            {
                "id": "taller",
                "name": "Taller",
                "attributes": [
                    {"name": "id", "type": "int"},
                    {"name": "direccion", "type": "String"},
                ],
            },
        ],
        "relationships": [
            {
                "id": "vehiculo-taller",
                "type": "association",
                "sourceId": "vehiculo",
                "targetId": "taller",
                "labels": ["*", "1"],
            }
        ],
    }

    def test_pubspec_includes_local_llm_runtime_and_flutter_floor(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            pubspec = (output / "pubspec.yaml").read_text()
            self.assertIn("llamadart:", pubspec)
            self.assertIn("llamadart_llama_cpp_flutter:", pubspec)
            self.assertIn("file_selector:", pubspec)
            self.assertIn("path_provider:", pubspec)
            self.assertIn("flutter: '>=3.38.0'", pubspec)

    def test_ios_setup_script_is_generated_and_executable(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            script = output / "tool" / "configure_ios_local_ai.sh"
            self.assertTrue(script.exists())
            content = script.read_text()
            self.assertIn("16.4", content)
            self.assertIn("IPHONEOS_DEPLOYMENT_TARGET", content)
            self.assertIn("--verify", content)
            # No invoca Ruby/CocoaPods: solo sed/grep.
            self.assertNotIn("pod install", content)

    def test_gguf_picker_declares_ios_uniform_type_identifier(self):
        # iOS's file_selector_ios throws ArgumentError at runtime if an
        # XTypeGroup has extensions but no uniformTypeIdentifiers (physically
        # reproduced on a real iPhone: "The provided type group ... should
        # either allow all files, or have a non-empty
        # 'uniformTypeIdentifiers'"). Extensions alone are not enough on iOS.
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            manager = (output / "lib/assistant/local_model_manager.dart").read_text()
            self.assertIn("uniformTypeIdentifiers", manager)
            self.assertIn("extensions: ['gguf']", manager)

    def test_local_model_manager_generates_bounded_cpu_fallback_and_cleanup(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            manager = (output / "lib/assistant/local_model_manager.dart").read_text()
            view = (output / "lib/assistant/assistant_view.dart").read_text()
            lifecycle_tests = (
                output / "test/assistant/local_model_manager_test.dart"
            ).read_text()

            self.assertIn("Future<void>? _activeLoad", manager)
            self.assertIn("preferredBackend: GpuBackend.cpu", manager)
            self.assertIn("await candidate.dispose()", manager)
            self.assertIn("if (_ownsModelManager) _modelManager.dispose()", view)
            self.assertIn("one CPU fallback ends ready", lifecycle_tests)
            self.assertIn("concurrent load calls share one primary attempt", lifecycle_tests)

    def test_local_llm_extractor_is_byte_identical_across_unrelated_schemas(self):
        """Prueba directa de que el generador NO hardcodea ningun nombre de
        entidad/campo de ningun proyecto especifico: el mismo archivo Dart
        generado para dos esquemas UML completamente distintos (ninguno
        Producto/Cliente/Venta) debe ser exactamente el mismo, porque toda
        la logica de la extraccion local consulta AppSchema.entities en
        tiempo de ejecucion, no en tiempo de generacion."""
        with tempfile.TemporaryDirectory() as dir_a, tempfile.TemporaryDirectory() as dir_b:
            output_a = Path(dir_a)
            output_b = Path(dir_b)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output_a)
            FlutterCRUDGenerator(self.ALTERNATE_UML).generate_project(output_b)

            extractor_a = (output_a / "lib/assistant/local_llm_command_extractor.dart").read_text()
            extractor_b = (output_b / "lib/assistant/local_llm_command_extractor.dart").read_text()
            self.assertEqual(extractor_a, extractor_b)

            manager_a = (output_a / "lib/assistant/local_model_manager.dart").read_text()
            manager_b = (output_b / "lib/assistant/local_model_manager.dart").read_text()
            self.assertEqual(manager_a, manager_b)

            # 'Role' is deliberately excluded: it's a substring of the
            # llamadart API type `LlamaChatRole`, unrelated to any UML
            # schema entity — a coincidental match, not hardcoding.
            for name in ("Producto", "Cliente", "Venta", "Person", "Pet", "Employee", "Vehiculo", "Taller"):
                self.assertNotIn(name, extractor_a)

    def test_local_llm_extractor_never_calls_router_or_adapter_directly(self):
        """La extraccion local SOLO propone un BusinessCommand: nunca debe
        importar CommandRouter/EntityServiceAdapter ni invocar confirmDelete,
        que es justamente lo que garantiza que el modelo local no pueda
        ejecutar nada por si mismo. Mencionarlos en un comentario de
        documentacion (para explicar la relacion con esas clases) es
        aceptable; importarlos o invocarlos no lo es."""
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            extractor = (output / "lib/assistant/local_llm_command_extractor.dart").read_text()
            self.assertNotIn("import 'command_router.dart'", extractor)
            self.assertNotIn("import 'entity_service_adapter.dart'", extractor)
            self.assertNotIn("CommandRouter(", extractor)
            self.assertNotIn("EntityServiceAdapter(", extractor)
            self.assertNotIn("confirmDelete(", extractor)

    def test_assistant_view_wires_local_ai_fallback_without_touching_delete_flow(self):
        with tempfile.TemporaryDirectory() as output_dir:
            output = Path(output_dir)
            FlutterCRUDGenerator(REPRESENTATIVE_UML).generate_project(output)
            view = (output / "lib/assistant/assistant_view.dart").read_text()
            self.assertIn("LocalLlmCommandExtractor", view)
            self.assertIn("LocalModelState.ready", view)
            # El flujo de confirmacion de DELETE en dos fases sigue intacto y
            # sin condicionarlo a si el comando vino del modelo local.
            self.assertIn("_confirmDelete(outcome.pendingDelete!)", view)
            self.assertIn("_router.confirmDelete(outcome.pendingDelete!)", view)
            # El fallback nunca se etiqueta como IA.
            self.assertIn("usedLocalAi", view)
