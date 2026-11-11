import io
import tempfile
import zipfile
from pathlib import Path
from unittest import TestCase
from xml.etree import ElementTree as ET

from django.test import SimpleTestCase

from uml_api.services import full_project
from uml_api.services.flutter_generator import FlutterCRUDGenerator
from uml_api.services.uml_kinds import code_entities, kind_of
from uml_api.services.xmi_service import export_uml_to_xmi, import_xmi_to_uml

XMI_NS = "http://schema.omg.org/spec/XMI/2.1"


def packaged(root, name):
    for element in root.iter():
        if element.tag.split("}")[-1] == "packagedElement" and element.attrib.get("name") == name:
            return element
    return None


def xmi_type(element):
    return element.attrib.get(f"{{{XMI_NS}}}type")


DIAGRAM = {
    "classes": [
        {"id": "c1", "name": "Cuenta", "kind": "abstract",
         "attributes": [{"name": "saldo", "type": "double", "visibility": "-"}, {"name": "titular", "type": "String", "visibility": "#"}, {"name": "id", "type": "int"}],
         "methods": [{"name": "depositar", "parameters": "monto: double", "returnType": "bool", "visibility": "+"}, {"name": "auditar", "visibility": "~"}]},
        {"id": "c2", "name": "Pagable", "kind": "interface", "attributes": [], "methods": [{"name": "pagar", "visibility": "+"}]},
        {"id": "c3", "name": "Estado", "kind": "enumeration", "attributes": [{"name": "ACTIVO", "type": ""}, {"name": "CERRADO", "type": ""}], "methods": []},
        {"id": "c4", "name": "Cliente", "attributes": [{"name": "nombre", "type": "String"}], "methods": []},
    ],
    "relationships": [
        {"id": "r1", "type": "generalization", "sourceId": "c4", "targetId": "c1"},
        {"id": "r2", "type": "association", "sourceId": "c4", "targetId": "c2", "labels": ["1", "0..*"]},
    ],
}


class KindsTests(TestCase):
    def test_unknown_kind_is_a_plain_class(self):
        self.assertEqual("class", kind_of({}))
        self.assertEqual("class", kind_of({"kind": "otra"}))
        self.assertEqual("interface", kind_of({"kind": "interface"}))

    def test_code_entities_drops_interfaces_enumerations_and_their_relationships(self):
        result = code_entities(DIAGRAM)

        self.assertEqual(["c1", "c4"], [c["id"] for c in result["classes"]])
        self.assertEqual(["r1"], [r["id"] for r in result["relationships"]])

    def test_code_entities_returns_the_same_object_when_nothing_is_dropped(self):
        plain = {"classes": [{"id": "a", "name": "A"}], "relationships": []}

        self.assertIs(plain, code_entities(plain))


class XmiKindsTests(TestCase):
    def setUp(self):
        self.root = ET.fromstring(export_uml_to_xmi(DIAGRAM))

    def test_exports_each_kind_with_its_uml_type(self):
        abstract = packaged(self.root, "Cuenta")
        self.assertEqual("uml:Class", xmi_type(abstract))
        self.assertEqual("true", abstract.attrib.get("isAbstract"))
        self.assertEqual("uml:Interface", xmi_type(packaged(self.root, "Pagable")))
        self.assertEqual("uml:Enumeration", xmi_type(packaged(self.root, "Estado")))
        self.assertIsNone(packaged(self.root, "Cliente").attrib.get("isAbstract"))

    def test_exports_the_visibility_of_attributes_and_operations(self):
        cuenta = packaged(self.root, "Cuenta")
        visibility = {e.attrib["name"]: e.attrib.get("visibility") for e in cuenta if e.tag.split("}")[-1] in ("ownedAttribute", "ownedOperation")}

        self.assertEqual({"saldo": "private", "titular": "protected", "id": None, "depositar": "public", "auditar": "package"}, visibility)

    def test_exports_the_enumeration_values_as_literals(self):
        estado = packaged(self.root, "Estado")

        self.assertEqual(["ACTIVO", "CERRADO"], [e.attrib["name"] for e in estado if e.tag.split("}")[-1] == "ownedLiteral"])
        self.assertEqual([], [e for e in estado if e.tag.split("}")[-1] == "ownedAttribute"])

    def test_round_trip_keeps_the_kind_and_the_visibility(self):
        imported = import_xmi_to_uml(export_uml_to_xmi(DIAGRAM))
        by_name = {c["name"]: c for c in imported["classes"]}

        self.assertEqual("abstract", by_name["Cuenta"]["kind"])
        self.assertEqual("interface", by_name["Pagable"]["kind"])
        self.assertEqual("enumeration", by_name["Estado"]["kind"])
        self.assertNotIn("kind", by_name["Cliente"])
        self.assertEqual([("saldo", "-"), ("titular", "#"), ("id", None)], [(a["name"], a.get("visibility")) for a in by_name["Cuenta"]["attributes"]])
        self.assertEqual([("depositar", "+"), ("auditar", "~")], [(m["name"], m.get("visibility")) for m in by_name["Cuenta"]["methods"]])
        self.assertEqual(["ACTIVO", "CERRADO"], [a["name"] for a in by_name["Estado"]["attributes"]])

    def test_the_generalization_to_an_abstract_class_survives_the_round_trip(self):
        imported = import_xmi_to_uml(export_uml_to_xmi(DIAGRAM))

        self.assertIn(("c4", "c1", "generalization"), [(r["sourceId"], r["targetId"], r["type"]) for r in imported["relationships"]])


class GeneratorsSkipNonEntitiesTests(SimpleTestCase):
    def test_flutter_project_has_no_screens_for_an_interface_or_an_enumeration(self):
        with tempfile.TemporaryDirectory() as out:
            FlutterCRUDGenerator(DIAGRAM).generate_project(output_dir=out)
            names = {p.name for p in Path(out).rglob("*.dart")}

        self.assertIn("cuenta.dart", names)
        self.assertIn("cliente.dart", names)
        self.assertNotIn("pagable.dart", names)
        self.assertNotIn("estado.dart", names)

    def test_full_project_sends_spring_only_the_classes_that_become_entities(self):
        sent = {}

        def fake_spring(payload):
            sent.update(payload)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as archive:
                archive.writestr("demo/pom.xml", "<project/>")
            return buffer.getvalue()

        full_project.build_full_project_zip(dict(DIAGRAM, appName="Banco"), fake_spring)

        self.assertEqual(["Cuenta", "Cliente"], [c["name"] for c in sent["classes"]])
        self.assertEqual(["r1"], [r["id"] for r in sent["relationships"]])
