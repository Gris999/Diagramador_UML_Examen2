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


# ----------------------------------------------------------------------------------------------------------------------------------------
# Intercambio real con Enterprise Architect (2026-11-12). Los archivos de `fixtures/ea/` son exportaciones de EA 17.2 de un modelo que se armó así:
# la app exportó un diagrama con clase abstracta, interfaz, enumeración y visibilidad; EA lo importó; en EA se agregaron una clase abstracta, una
# interfaz y una enumeración más; y EA exportó el paquete como XMI 2.1 en sus tres variantes (UML 2.0, UML 2.1 y UML 2.4/2.5).
# ----------------------------------------------------------------------------------------------------------------------------------------
from pathlib import Path  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ea"
EA_EXPORTS = ("ea-xmi21-uml20.xmi", "ea-xmi21-uml21.xmi", "ea-xmi21-uml24.xmi")


def _by_name(uml):
    return {c["name"]: c for c in uml["classes"]}


class RealEnterpriseArchitectExportTests(SimpleTestCase):
    def imported(self, name):
        return import_xmi_to_uml((FIXTURES / name).read_bytes())

    def test_every_xmi_variant_of_ea_gives_the_same_classes_and_kinds(self):
        for name in EA_EXPORTS:
            with self.subTest(name):
                classes = _by_name(self.imported(name))

                self.assertEqual(set(classes), {"Ahorro", "Cliente", "Cuenta", "Estado", "Factura", "Imprimible", "Moneda", "Pagable"})
                self.assertEqual(classes["Cuenta"].get("kind"), "abstract")
                self.assertEqual(classes["Factura"].get("kind"), "abstract")  # creada directamente en EA
                self.assertEqual(classes["Pagable"].get("kind"), "interface")
                self.assertEqual(classes["Imprimible"].get("kind"), "interface")
                self.assertEqual(classes["Estado"].get("kind"), "enumeration")
                self.assertEqual(classes["Moneda"].get("kind"), "enumeration")
                self.assertNotIn("kind", classes["Cliente"])

    def test_every_xmi_variant_keeps_the_visibility_of_each_member_including_the_public_ones(self):
        """UML 2.4/2.5 de EA no escribe la visibilidad pública (es la de por omisión): hay que leerla como pública."""
        for name in EA_EXPORTS:
            with self.subTest(name):
                classes = _by_name(self.imported(name))

                self.assertEqual({a["name"]: a["visibility"] for a in classes["Cliente"]["attributes"]}, {"id": "-", "nombre": "+", "correo": "#"})
                self.assertEqual(classes["Cliente"]["methods"][0]["visibility"], "~")
                self.assertEqual({a["name"]: a["visibility"] for a in classes["Cuenta"]["attributes"]}, {"saldo": "#", "titular": "-"})
                self.assertEqual(classes["Cuenta"]["methods"][0]["visibility"], "+")
                self.assertEqual(classes["Pagable"]["methods"][0]["visibility"], "+")
                self.assertEqual({a["name"]: a["visibility"] for a in classes["Factura"]["attributes"]}, {"total": "#", "emitida": "-"})

    def test_enumeration_literals_come_without_type_or_visibility(self):
        for name in EA_EXPORTS:
            with self.subTest(name):
                estado = _by_name(self.imported(name))["Estado"]

                self.assertEqual([a["name"] for a in estado["attributes"]], ["ACTIVO", "INACTIVO"])
                self.assertTrue(all(not a.get("type") and "visibility" not in a for a in estado["attributes"]))

    def test_the_type_the_user_chose_in_ea_wins_over_the_generic_one_in_the_body(self):
        """EA escribe `UnlimitedNatural` en el cuerpo del XMI para un `double`; el nombre elegido está en su extensión."""
        for name in EA_EXPORTS:
            with self.subTest(name):
                factura = _by_name(self.imported(name))["Factura"]

                self.assertEqual({a["name"]: a["type"] for a in factura["attributes"]}, {"total": "double", "emitida": "bool"})

    def test_a_return_type_that_ea_links_by_id_comes_back_as_its_name(self):
        for name in EA_EXPORTS:
            with self.subTest(name):
                classes = _by_name(self.imported(name))

                self.assertEqual(classes["Factura"]["methods"][0]["returnType"], "void")  # no `EAnone_void`
                self.assertEqual(classes["Imprimible"]["methods"][0]["returnType"], "void")

    def test_generalization_and_association_with_multiplicities_come_through(self):
        for name in EA_EXPORTS:
            with self.subTest(name):
                uml = self.imported(name)
                names = {c["id"]: c["name"] for c in uml["classes"]}
                relations = {(r["type"], names[r["sourceId"]], names[r["targetId"]]): r["labels"] for r in uml["relationships"]}

                self.assertIn(("generalization", "Ahorro", "Cuenta"), relations)
                association = next(labels for (kind, source, target), labels in relations.items() if kind == "association")
                self.assertEqual(sorted(association), ["0..*", "1"])


class AppToEnterpriseArchitectExportTests(SimpleTestCase):
    """Lo que la app escribe para EA: EA lo importó con los tipos de retorno y de parámetros (antes los perdía)."""

    UML = {
        "classes": [
            {"id": "cuenta", "name": "Cuenta", "attributes": [], "methods": []},
            {
                "id": "cliente",
                "name": "Cliente",
                "attributes": [{"name": "cuenta", "type": "Cuenta", "visibility": "-"}],
                "methods": [
                    {"name": "pedir", "parameters": "producto: Cuenta, cantidad: int", "returnType": "Cuenta", "visibility": "+"},
                    {"name": "calcular", "parameters": "monto: double", "returnType": "double", "visibility": "#"},
                    {"name": "avisar", "parameters": "", "returnType": "void"},
                ],
            },
        ],
        "relationships": [],
    }

    def operations(self):
        root = ET.fromstring(export_uml_to_xmi(self.UML))
        local = lambda e: e.tag.split("}", 1)[-1]  # noqa: E731
        return {o.attrib["name"]: o for o in root.iter() if local(o) == "ownedOperation"}

    def child_type(self, parameter):
        return next((c for c in parameter if c.tag.split("}", 1)[-1] == "type"), None)

    def test_primitive_parameter_and_return_types_are_written_as_uml_primitive_types(self):
        calcular = self.operations()["calcular"]
        monto = next(p for p in calcular if p.attrib["name"] == "monto")
        retorno = next(p for p in calcular if p.attrib["direction"] == "return")

        for parameter, expected in ((monto, "#Real"), (retorno, "#Real")):
            declared = self.child_type(parameter)
            self.assertIsNotNone(declared)
            self.assertTrue(declared.attrib["href"].endswith(expected))
            self.assertNotIn("type", parameter.attrib)  # ya no `type="double"`, que EA descartaba

    def test_a_parameter_or_return_of_a_class_type_points_to_that_class_by_id(self):
        pedir = self.operations()["pedir"]
        producto = next(p for p in pedir if p.attrib["name"] == "producto")
        retorno = next(p for p in pedir if p.attrib["direction"] == "return")

        self.assertEqual(producto.attrib["type"], "cuenta")
        self.assertEqual(retorno.attrib["type"], "cuenta")

    def test_an_attribute_of_a_class_type_points_to_that_class_by_id(self):
        root = ET.fromstring(export_uml_to_xmi(self.UML))
        attribute = next(a for a in root.iter() if a.tag.split("}", 1)[-1] == "ownedAttribute")

        self.assertEqual(attribute.attrib["type"], "cuenta")

    def test_void_is_not_a_type(self):
        avisar = self.operations()["avisar"]

        self.assertEqual([p for p in avisar if p.attrib.get("direction") == "return"], [])

    def test_coming_back_into_the_app_the_types_are_the_ones_that_went_out(self):
        uml = import_xmi_to_uml(export_uml_to_xmi(self.UML))
        cliente = _by_name(uml)["Cliente"]
        methods = {m["name"]: m for m in cliente["methods"]}

        self.assertEqual(cliente["attributes"][0]["type"], "Cuenta")  # el id vuelve a ser el nombre de la clase
        self.assertEqual((methods["pedir"]["parameters"], methods["pedir"]["returnType"]), ("producto: Cuenta, cantidad: Integer", "Cuenta"))
        self.assertEqual(methods["calcular"]["returnType"], "Real")
        self.assertEqual(methods["avisar"]["returnType"], "")
        self.assertEqual([m["visibility"] for m in cliente["methods"] if "visibility" in m], ["+", "#"])

    def test_the_file_the_app_wrote_for_ea_still_imports_with_kinds_and_visibility(self):
        uml = import_xmi_to_uml((FIXTURES / "exportado-por-la-app.xmi").read_bytes())
        classes = _by_name(uml)

        self.assertEqual(classes["Cuenta"].get("kind"), "abstract")
        self.assertEqual(classes["Pagable"].get("kind"), "interface")
        self.assertEqual(classes["Estado"].get("kind"), "enumeration")
        self.assertEqual({a["name"]: a["visibility"] for a in classes["Cliente"]["attributes"]}, {"id": "-", "nombre": "+", "correo": "#"})


class XmiReadContextTests(SimpleTestCase):
    def doc(self, exporter, member_attrs=""):
        documentation = f'<xmi:Documentation exporter="{exporter}"/>' if exporter else ""
        return f"""<?xml version="1.0"?>
<xmi:XMI xmlns:xmi="{XMI_NS}" xmlns:uml="http://schema.omg.org/spec/UML/2.1" xmi:version="2.1">{documentation}
 <uml:Model xmi:type="uml:Model" name="M">
  <packagedElement xmi:type="uml:Class" xmi:id="c1" name="Cuenta">
   <ownedAttribute xmi:type="uml:Property" xmi:id="a1" name="saldo" {member_attrs}/>
   <ownedAttribute xmi:type="uml:Property" xmi:id="a2" name="oculto" visibility="private"/>
   <ownedOperation xmi:id="o1" name="depositar"/>
  </packagedElement>
 </uml:Model>
</xmi:XMI>""".encode()

    def test_in_an_ea_file_a_member_without_visibility_is_public(self):
        cuenta = _by_name(import_xmi_to_uml(self.doc("Enterprise Architect")))["Cuenta"]

        self.assertEqual([a["visibility"] for a in cuenta["attributes"]], ["+", "-"])
        self.assertEqual(cuenta["methods"][0]["visibility"], "+")

    def test_in_any_other_file_a_member_without_visibility_stays_without_it(self):
        for exporter in ("", "Otra herramienta"):
            with self.subTest(exporter):
                cuenta = _by_name(import_xmi_to_uml(self.doc(exporter)))["Cuenta"]

                self.assertNotIn("visibility", cuenta["attributes"][0])
                self.assertEqual(cuenta["attributes"][1]["visibility"], "-")
                self.assertNotIn("visibility", cuenta["methods"][0])

    def test_a_type_that_is_the_id_of_a_class_becomes_the_name_of_that_class(self):
        xmi = f"""<?xml version="1.0"?>
<xmi:XMI xmlns:xmi="{XMI_NS}" xmlns:uml="http://schema.omg.org/spec/UML/2.1" xmi:version="2.1"><uml:Model name="M">
 <packagedElement xmi:type="uml:Class" xmi:id="EAID_1" name="Cliente"/>
 <packagedElement xmi:type="uml:Class" xmi:id="EAID_2" name="Pedido">
  <ownedAttribute xmi:type="uml:Property" xmi:id="x" name="cliente" type="EAID_1"/>
 </packagedElement></uml:Model></xmi:XMI>""".encode()

        pedido = _by_name(import_xmi_to_uml(xmi))["Pedido"]

        self.assertEqual(pedido["attributes"][0]["type"], "Cliente")


class AppEnterpriseArchitectRoundTripTests(SimpleTestCase):
    def test_what_ea_exports_after_importing_the_apps_file_keeps_kinds_visibility_and_types(self):
        """La app exportó (`exportado-por-la-app.xmi`), EA lo importó y lo volvió a exportar (`ea-ida-y-vuelta-uml21.xmi`): nada se perdió."""
        classes = _by_name(import_xmi_to_uml((FIXTURES / "ea-ida-y-vuelta-uml21.xmi").read_bytes()))
        cliente = classes["Cliente"]
        pedir = next(m for m in cliente["methods"] if m["name"] == "pedir")

        self.assertEqual((pedir["visibility"], pedir["parameters"], pedir["returnType"]), ("+", "producto: Cuenta, cantidad: Integer", "Cuenta"))
        self.assertEqual(classes["Cuenta"].get("kind"), "abstract")
        self.assertEqual(classes["Pagable"].get("kind"), "interface")
        self.assertEqual(classes["Estado"].get("kind"), "enumeration")
        self.assertEqual(classes["Pagable"]["methods"][0]["returnType"], "Boolean")
