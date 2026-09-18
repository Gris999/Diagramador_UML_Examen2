import xml.etree.ElementTree as ET

from django.test import SimpleTestCase

from uml_api.services.xmi_service import (
    export_uml_to_xmi,
    import_xmi_to_uml,
)


XMI_NS = "http://schema.omg.org/spec/XMI/2.1"


class EnterpriseArchitectXMITests(SimpleTestCase):
    def test_imports_ea_association_type_references_and_multiplicity(self):
        ea_xmi = b'''<?xml version="1.0" encoding="windows-1252"?>
<xmi:XMI
    xmlns:xmi="http://schema.omg.org/spec/XMI/2.1"
    xmlns:uml="http://schema.omg.org/spec/UML/2.1"
    xmi:version="2.1">

  <uml:Model xmi:type="uml:Model" name="EA_Model">

    <packagedElement
        xmi:type="uml:Class"
        xmi:id="mascota"
        name="Mascota">

      <ownedAttribute
          xmi:type="uml:Property"
          xmi:id="mascota-id"
          name="id">
        <type
            xmi:type="uml:PrimitiveType"
            href="http://schema.omg.org/spec/UML/2.1/uml.xml#Integer"/>
      </ownedAttribute>

      <ownedAttribute
          xmi:type="uml:Property"
          xmi:id="mascota-nombre"
          name="nombre">
        <type
            xmi:type="uml:PrimitiveType"
            href="http://schema.omg.org/spec/UML/2.1/uml.xml#String"/>
      </ownedAttribute>
    </packagedElement>

    <packagedElement
        xmi:type="uml:Association"
        xmi:id="persona-mascota">

      <memberEnd xmi:idref="end-persona"/>

      <ownedEnd
          xmi:type="uml:Property"
          xmi:id="end-persona"
          aggregation="none">
        <type xmi:idref="persona"/>
        <lowerValue
            xmi:type="uml:LiteralInteger"
            value="0"/>
        <upperValue
            xmi:type="uml:LiteralInteger"
            value="1"/>
      </ownedEnd>

      <memberEnd xmi:idref="end-mascota"/>

      <ownedEnd
          xmi:type="uml:Property"
          xmi:id="end-mascota"
          aggregation="none">
        <type xmi:idref="mascota"/>
        <lowerValue
            xmi:type="uml:LiteralInteger"
            value="1"/>
        <upperValue
            xmi:type="uml:LiteralUnlimitedNatural"
            value="-1"/>
      </ownedEnd>
    </packagedElement>

    <packagedElement
        xmi:type="uml:Class"
        xmi:id="persona"
        name="Persona">

      <ownedAttribute
          xmi:type="uml:Property"
          xmi:id="persona-id"
          name="id">
        <type
            xmi:type="uml:PrimitiveType"
            href="http://schema.omg.org/spec/UML/2.1/uml.xml#Integer"/>
      </ownedAttribute>

      <ownedAttribute
          xmi:type="uml:Property"
          xmi:id="persona-nombre"
          name="nombre">
        <type
            xmi:type="uml:PrimitiveType"
            href="http://schema.omg.org/spec/UML/2.1/uml.xml#String"/>
      </ownedAttribute>
    </packagedElement>

  </uml:Model>
</xmi:XMI>
'''

        imported = import_xmi_to_uml(ea_xmi)

        classes = {
            uml_class["name"]: uml_class
            for uml_class in imported["classes"]
        }

        self.assertEqual(
            classes["Persona"]["attributes"][0]["type"],
            "Integer",
        )
        self.assertEqual(
            classes["Persona"]["attributes"][1]["type"],
            "String",
        )

        self.assertEqual(len(imported["relationships"]), 1)

        relation = imported["relationships"][0]

        self.assertEqual(relation["type"], "association")
        self.assertEqual(
            {relation["sourceId"], relation["targetId"]},
            {"persona", "mascota"},
        )
        self.assertEqual(
            relation["labels"],
            ["0..1", "1..*"],
        )

    def test_export_uses_uml_primitive_type_hrefs(self):
        source = {
            "classes": [
                {
                    "id": "persona",
                    "name": "Persona",
                    "attributes": [
                        {
                            "name": "id",
                            "type": "int",
                        },
                        {
                            "name": "nombre",
                            "type": "string",
                        },
                    ],
                    "methods": [],
                }
            ],
            "relationships": [],
        }

        xmi = export_uml_to_xmi(source)
        root = ET.fromstring(xmi)

        attributes = {
            element.attrib.get("name"): element
            for element in root.iter()
            if element.tag.split("}", 1)[-1] == "ownedAttribute"
        }

        id_type = next(
            child
            for child in attributes["id"]
            if child.tag.split("}", 1)[-1] == "type"
        )

        name_type = next(
            child
            for child in attributes["nombre"]
            if child.tag.split("}", 1)[-1] == "type"
        )

        self.assertTrue(
            id_type.attrib["href"].endswith("#Integer")
        )
        self.assertTrue(
            name_type.attrib["href"].endswith("#String")
        )
        self.assertEqual(
            id_type.attrib[f"{{{XMI_NS}}}type"],
            "uml:PrimitiveType",
        )
