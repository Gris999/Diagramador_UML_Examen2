from unittest import TestCase
from xml.etree import ElementTree as ET

from uml_api.services.xmi_service import (
    XMIError,
    export_uml_to_xmi,
    import_xmi_to_uml,
)


XMI_NS = "http://schema.omg.org/spec/XMI/2.1"


def xmi_attr(name):
    return f"{{{XMI_NS}}}{name}"


def find_packaged_element(root, uml_type):
    for element in root.iter():
        if element.tag.split("}")[-1] != "packagedElement":
            continue

        element_type = element.attrib.get(xmi_attr("type"), "")

        if element_type == uml_type:
            return element

    return None


class XmiExportTests(TestCase):

    def test_exports_xmi_root_and_class(self):
        uml = {
            "classes": [
                {
                    "id": "person-id",
                    "name": "Persona",
                    "attributes": [],
                    "methods": [],
                }
            ],
            "relationships": [],
        }

        xml_bytes = export_uml_to_xmi(uml)
        root = ET.fromstring(xml_bytes)

        self.assertEqual(root.tag, f"{{{XMI_NS}}}XMI")

        uml_class = find_packaged_element(root, "uml:Class")

        self.assertIsNotNone(uml_class)
        self.assertEqual(uml_class.attrib["name"], "Persona")
        self.assertEqual(uml_class.attrib[xmi_attr("id")], "person-id")

    def test_rejects_invalid_class_entry(self):
        with self.assertRaises(XMIError):
            export_uml_to_xmi(
                {
                    "classes": [None],
                    "relationships": [],
                }
            )

    def test_rejects_duplicate_xmi_ids(self):
        with self.assertRaises(XMIError):
            export_uml_to_xmi(
                {
                    "classes": [
                        {
                            "id": "duplicate-id",
                            "name": "A",
                            "attributes": [],
                            "methods": [],
                        },
                        {
                            "id": "duplicate-id",
                            "name": "B",
                            "attributes": [],
                            "methods": [],
                        },
                    ],
                    "relationships": [],
                }
            )

    def test_export_is_deterministic_and_generated_ids_are_unique(self):
        uml = {
            "classes": [
                {
                    "id": "person-id",
                    "name": "Persona",
                    "attributes": [
                        {"name": "nombre", "type": "String"}
                    ],
                    "methods": [
                        {
                            "name": "saludar",
                            "parameters": "mensaje: String",
                            "returnType": "Boolean",
                        }
                    ],
                },
                {
                    "id": "pet-id",
                    "name": "Mascota",
                    "attributes": [],
                    "methods": [],
                },
            ],
            "relationships": [
                {
                    "id": "association-id",
                    "type": "association",
                    "sourceId": "person-id",
                    "targetId": "pet-id",
                    "labels": ["1", "0..*"],
                }
            ],
        }

        first = export_uml_to_xmi(uml)
        second = export_uml_to_xmi(uml)

        self.assertEqual(first, second)

        root = ET.fromstring(first)

        ids = [
            value
            for element in root.iter()
            for key, value in element.attrib.items()
            if key == xmi_attr("id")
        ]

        self.assertEqual(
            len(ids),
            len(set(ids)),
        )

    def test_exports_attribute_and_operation(self):
        uml = {
            "classes": [
                {
                    "id": "person-id",
                    "name": "Persona",
                    "attributes": [
                        {
                            "name": "nombre",
                            "type": "String",
                        }
                    ],
                    "methods": [
                        {
                            "name": "saludar",
                            "parameters": "mensaje: String",
                            "returnType": "Boolean",
                        }
                    ],
                }
            ],
            "relationships": [],
        }

        root = ET.fromstring(export_uml_to_xmi(uml))
        uml_class = find_packaged_element(root, "uml:Class")

        attributes = [
            child
            for child in uml_class
            if child.tag.split("}")[-1] == "ownedAttribute"
            and not child.attrib.get("association")
        ]

        operations = [
            child
            for child in uml_class
            if child.tag.split("}")[-1] == "ownedOperation"
        ]

        self.assertEqual(len(attributes), 1)
        self.assertEqual(attributes[0].attrib["name"], "nombre")

        self.assertEqual(len(operations), 1)
        self.assertEqual(operations[0].attrib["name"], "saludar")

    def test_exports_association_and_multiplicities(self):
        uml = {
            "classes": [
                {
                    "id": "person-id",
                    "name": "Persona",
                    "attributes": [],
                    "methods": [],
                },
                {
                    "id": "pet-id",
                    "name": "Mascota",
                    "attributes": [],
                    "methods": [],
                },
            ],
            "relationships": [
                {
                    "id": "association-id",
                    "type": "association",
                    "sourceId": "person-id",
                    "targetId": "pet-id",
                    "labels": ["1", "0..*"],
                }
            ],
        }

        root = ET.fromstring(export_uml_to_xmi(uml))
        association = find_packaged_element(root, "uml:Association")

        self.assertIsNotNone(association)

        ends = [
            child
            for child in association
            if child.tag.split("}")[-1] == "ownedEnd"
        ]

        self.assertEqual(len(ends), 2)
        self.assertEqual(ends[0].attrib["type"], "person-id")
        self.assertEqual(ends[1].attrib["type"], "pet-id")

    def test_exports_aggregation_and_composition(self):
        for relation_type, aggregation_value in (
            ("aggregation", "shared"),
            ("composition", "composite"),
        ):
            with self.subTest(relation_type=relation_type):
                uml = {
                    "classes": [
                        {
                            "id": "whole-id",
                            "name": "Todo",
                            "attributes": [],
                            "methods": [],
                        },
                        {
                            "id": "part-id",
                            "name": "Parte",
                            "attributes": [],
                            "methods": [],
                        },
                    ],
                    "relationships": [
                        {
                            "id": "rel-id",
                            "type": relation_type,
                            "sourceId": "whole-id",
                            "targetId": "part-id",
                            "labels": ["1", "0..*"],
                        }
                    ],
                }

                root = ET.fromstring(export_uml_to_xmi(uml))
                association = find_packaged_element(root, "uml:Association")

                ends = [
                    child
                    for child in association
                    if child.tag.split("}")[-1] == "ownedEnd"
                ]

                self.assertEqual(
                    ends[0].attrib.get("aggregation"),
                    aggregation_value,
                )

    def test_exports_generalization(self):
        uml = {
            "classes": [
                {
                    "id": "child-id",
                    "name": "Hija",
                    "attributes": [],
                    "methods": [],
                },
                {
                    "id": "parent-id",
                    "name": "Padre",
                    "attributes": [],
                    "methods": [],
                },
            ],
            "relationships": [
                {
                    "id": "gen-id",
                    "type": "generalization",
                    "sourceId": "child-id",
                    "targetId": "parent-id",
                    "labels": [],
                }
            ],
        }

        root = ET.fromstring(export_uml_to_xmi(uml))

        child_class = None

        for element in root.iter():
            if (
                element.attrib.get(xmi_attr("id")) == "child-id"
                and element.attrib.get(xmi_attr("type")) == "uml:Class"
            ):
                child_class = element
                break

        self.assertIsNotNone(child_class)

        generalizations = [
            child
            for child in child_class
            if child.tag.split("}")[-1] == "generalization"
        ]

        self.assertEqual(len(generalizations), 1)
        self.assertEqual(
            generalizations[0].attrib["general"],
            "parent-id",
        )

    def test_exports_dependency(self):
        uml = {
            "classes": [
                {
                    "id": "client-id",
                    "name": "Cliente",
                    "attributes": [],
                    "methods": [],
                },
                {
                    "id": "supplier-id",
                    "name": "Servicio",
                    "attributes": [],
                    "methods": [],
                },
            ],
            "relationships": [
                {
                    "id": "dep-id",
                    "type": "dependency",
                    "sourceId": "client-id",
                    "targetId": "supplier-id",
                    "labels": [],
                }
            ],
        }

        root = ET.fromstring(export_uml_to_xmi(uml))
        dependency = find_packaged_element(root, "uml:Dependency")

        self.assertIsNotNone(dependency)
        self.assertEqual(dependency.attrib["client"], "client-id")
        self.assertEqual(dependency.attrib["supplier"], "supplier-id")


class XmiImportTests(TestCase):

    def test_json_xmi_json_round_trip(self):
        original = {
            "classes": [
                {
                    "id": "person-id",
                    "name": "Persona",
                    "attributes": [
                        {
                            "name": "nombre",
                            "type": "String",
                        }
                    ],
                    "methods": [
                        {
                            "name": "saludar",
                            "parameters": "mensaje: String",
                            "returnType": "Boolean",
                        }
                    ],
                },
                {
                    "id": "pet-id",
                    "name": "Mascota",
                    "attributes": [],
                    "methods": [],
                },
            ],
            "relationships": [
                {
                    "id": "association-id",
                    "type": "association",
                    "sourceId": "person-id",
                    "targetId": "pet-id",
                    "labels": ["1", "0..*"],
                }
            ],
        }

        imported = import_xmi_to_uml(export_uml_to_xmi(original))

        classes = {
            item["id"]: item
            for item in imported["classes"]
        }

        self.assertEqual(classes["person-id"]["name"], "Persona")
        self.assertEqual(
            classes["person-id"]["attributes"],
            [{"name": "nombre", "type": "String"}],
        )
        self.assertEqual(
            classes["person-id"]["methods"][0]["name"],
            "saludar",
        )
        self.assertEqual(
            classes["person-id"]["methods"][0]["returnType"],
            "Boolean",
        )

        self.assertEqual(len(imported["relationships"]), 1)

        relationship = imported["relationships"][0]

        self.assertEqual(relationship["type"], "association")
        self.assertEqual(relationship["sourceId"], "person-id")
        self.assertEqual(relationship["targetId"], "pet-id")
        self.assertEqual(relationship["labels"], ["1", "0..*"])

    def test_rejects_malformed_xml(self):
        with self.assertRaises(XMIError):
            import_xmi_to_uml("<not-valid")

    def test_rejects_doctype_and_entities(self):
        xml = """<?xml version="1.0"?>
<!DOCTYPE x [
  <!ENTITY attack SYSTEM "file:///etc/passwd">
]>
<x>&attack;</x>
"""

        with self.assertRaises(XMIError):
            import_xmi_to_uml(xml)


class EnterpriseArchitectStyleImportTests(TestCase):

    def test_imports_external_xmi_supported_subset(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<foo:XMI
    xmlns:foo="http://schema.omg.org/spec/XMI/2.1"
    xmlns:u="http://www.eclipse.org/uml2/5.0.0/UML">
  <u:Model foo:id="model-id" name="External Model">

    <packagedElement foo:type="u:Class" foo:id="base-id" name="Base"/>

    <packagedElement foo:type="u:Class" foo:id="child-id" name="Child">
      <ownedAttribute
          foo:type="u:Property"
          foo:id="attr-id"
          name="code"
          type="String"/>

      <ownedOperation
          foo:type="u:Operation"
          foo:id="operation-id"
          name="save">
        <ownedParameter
            foo:type="u:Parameter"
            foo:id="parameter-id"
            name="input"
            direction="in"
            type="String"/>
        <ownedParameter
            foo:type="u:Parameter"
            foo:id="return-id"
            name="return"
            direction="return"
            type="Boolean"/>
      </ownedOperation>

      <generalization
          foo:type="u:Generalization"
          foo:id="generalization-id"
          general="base-id"/>
    </packagedElement>

    <packagedElement foo:type="u:Class" foo:id="whole-id" name="Whole"/>
    <packagedElement foo:type="u:Class" foo:id="part-id" name="Part"/>
    <packagedElement foo:type="u:Class" foo:id="service-id" name="Service"/>

    <packagedElement
        foo:type="u:Association"
        foo:id="association-id">
      <ownedEnd
          foo:type="u:Property"
          foo:id="association-source"
          type="child-id">
        <lowerValue foo:type="u:LiteralInteger" value="1"/>
        <upperValue foo:type="u:LiteralInteger" value="1"/>
      </ownedEnd>
      <ownedEnd
          foo:type="u:Property"
          foo:id="association-target"
          type="part-id">
        <lowerValue foo:type="u:LiteralInteger" value="0"/>
        <upperValue foo:type="u:LiteralUnlimitedNatural" value="*"/>
      </ownedEnd>
    </packagedElement>

    <packagedElement
        foo:type="u:Association"
        foo:id="aggregation-id">
      <ownedEnd
          foo:type="u:Property"
          foo:id="aggregation-source"
          type="whole-id"
          aggregation="shared"/>
      <ownedEnd
          foo:type="u:Property"
          foo:id="aggregation-target"
          type="part-id"/>
    </packagedElement>

    <packagedElement
        foo:type="u:Association"
        foo:id="composition-id">
      <ownedEnd
          foo:type="u:Property"
          foo:id="composition-source"
          type="whole-id"
          aggregation="composite"/>
      <ownedEnd
          foo:type="u:Property"
          foo:id="composition-target"
          type="child-id"/>
    </packagedElement>

    <packagedElement
        foo:type="u:Dependency"
        foo:id="dependency-id"
        client="child-id"
        supplier="service-id"/>

  </u:Model>
</foo:XMI>
"""

        imported = import_xmi_to_uml(xml)

        classes = {
            item["id"]: item
            for item in imported["classes"]
        }

        self.assertEqual(
            classes["child-id"]["attributes"],
            [{"name": "code", "type": "String"}],
        )

        self.assertEqual(
            classes["child-id"]["methods"],
            [
                {
                    "name": "save",
                    "parameters": "input: String",
                    "returnType": "Boolean",
                }
            ],
        )

        relationships = {
            item["id"]: item
            for item in imported["relationships"]
        }

        self.assertEqual(
            relationships["generalization-id"]["type"],
            "generalization",
        )
        self.assertEqual(
            relationships["generalization-id"]["targetId"],
            "base-id",
        )

        self.assertEqual(
            relationships["association-id"]["type"],
            "association",
        )
        self.assertEqual(
            relationships["association-id"]["labels"],
            ["1", "0..*"],
        )

        self.assertEqual(
            relationships["aggregation-id"]["type"],
            "aggregation",
        )

        self.assertEqual(
            relationships["composition-id"]["type"],
            "composition",
        )

        self.assertEqual(
            relationships["dependency-id"]["type"],
            "dependency",
        )
        self.assertEqual(
            relationships["dependency-id"]["sourceId"],
            "child-id",
        )
        self.assertEqual(
            relationships["dependency-id"]["targetId"],
            "service-id",
        )

    def test_importer_does_not_depend_on_namespace_prefix(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<foo:XMI
    xmlns:foo="http://schema.omg.org/spec/XMI/2.1"
    xmlns:u="http://www.eclipse.org/uml2/5.0.0/UML">
  <u:Model foo:id="model-id" name="EA Model">
    <packagedElement foo:type="uml:Class" foo:id="class-1" name="Cliente"/>
  </u:Model>
</foo:XMI>
"""

        imported = import_xmi_to_uml(xml)

        self.assertEqual(len(imported["classes"]), 1)
        self.assertEqual(imported["classes"][0]["id"], "class-1")
        self.assertEqual(imported["classes"][0]["name"], "Cliente")
