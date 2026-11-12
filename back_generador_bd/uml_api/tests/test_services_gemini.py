from unittest import TestCase
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from uml_api.services.services_gemini import (
    call_gemini_from_image,
    _edge_to_relationship_type,
    _map_edges_to_relationships,
)


class EdgeRelationshipTypeTests(TestCase):

    def test_black_diamond_in_tail_is_composition(self):
        edge = {
            "head": {"shape": "none"},
            "tail": {
                "shape": "diamond",
                "diamond": "black",
                "fill": "black",
            },
            "line": {"style": "solid"},
        }

        self.assertEqual(
            _edge_to_relationship_type(edge),
            ("composition", "tail"),
        )

    def test_white_diamond_in_head_is_aggregation(self):
        edge = {
            "head": {
                "shape": "diamond",
                "fill": "white",
            },
            "tail": {"shape": "none"},
            "line": {"style": "solid"},
        }

        self.assertEqual(
            _edge_to_relationship_type(edge),
            ("aggregation", "head"),
        )

    def test_dashed_line_is_dependency(self):
        edge = {
            "head": {"shape": "none"},
            "tail": {"shape": "none"},
            "line": {"style": "dashed"},
        }

        self.assertEqual(
            _edge_to_relationship_type(edge),
            ("dependency", "none"),
        )

    def test_white_triangle_in_head_is_generalization(self):
        edge = {
            "head": {
                "shape": "triangle",
                "fill": "white",
                "size": "large",
            },
            "tail": {"shape": "none"},
            "line": {"style": "solid"},
        }

        self.assertEqual(
            _edge_to_relationship_type(edge),
            ("generalization", "head"),
        )


class MapEdgesToRelationshipsTests(TestCase):

    def test_aggregation_with_diamond_in_head_reverses_direction(self):
        parsed = {
            "nodes": [
                {
                    "id": "class-a",
                    "name": "Parte",
                    "attributes": [],
                    "methods": [],
                },
                {
                    "id": "class-b",
                    "name": "Todo",
                    "attributes": [],
                    "methods": [],
                },
            ],
            "edges_raw": [
                {
                    "id": "edge-1",
                    "sourceName": "Parte",
                    "targetName": "Todo",
                    "head": {
                        "shape": "diamond",
                        "fill": "white",
                    },
                    "tail": {"shape": "none"},
                    "line": {"style": "solid"},
                    "labels": [],
                }
            ],
        }

        result = _map_edges_to_relationships(parsed)

        self.assertEqual(len(result["relationships"]), 1)

        relationship = result["relationships"][0]

        self.assertEqual(relationship["type"], "aggregation")
        self.assertEqual(relationship["sourceId"], "class-b")
        self.assertEqual(relationship["targetId"], "class-a")

    def test_generalization_with_triangle_in_tail_reverses_direction(self):
        parsed = {
            "nodes": [
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
            "edges_raw": [
                {
                    "id": "edge-1",
                    "sourceName": "Padre",
                    "targetName": "Hija",
                    "head": {"shape": "none"},
                    "tail": {
                        "shape": "triangle",
                        "fill": "white",
                    },
                    "line": {"style": "solid"},
                    "labels": [],
                }
            ],
        }

        result = _map_edges_to_relationships(parsed)
        relationship = result["relationships"][0]

        self.assertEqual(relationship["type"], "generalization")
        self.assertEqual(relationship["sourceId"], "child-id")
        self.assertEqual(relationship["targetId"], "parent-id")

    def test_duplicate_bidirectional_relationships_are_merged(self):
        parsed = {
            "nodes": [
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
            "edges_raw": [
                {
                    "id": "edge-1",
                    "sourceName": "Persona",
                    "targetName": "Mascota",
                    "head": {"shape": "none"},
                    "tail": {"shape": "none"},
                    "line": {"style": "solid"},
                    "labels": ["1"],
                },
                {
                    "id": "edge-2",
                    "sourceName": "Mascota",
                    "targetName": "Persona",
                    "head": {"shape": "none"},
                    "tail": {"shape": "none"},
                    "line": {"style": "solid"},
                    "labels": ["0..*"],
                },
            ],
        }

        result = _map_edges_to_relationships(parsed)

        self.assertEqual(len(result["relationships"]), 1)

        relationship = result["relationships"][0]

        self.assertEqual(relationship["type"], "association")
        self.assertEqual(relationship["sourceId"], "person-id")
        self.assertEqual(relationship["targetId"], "pet-id")
        self.assertEqual(relationship["labels"], ["1", "0..*"])


class ImageNotationTests(SimpleTestCase):
    """La foto de un diagrama conserva la notación UML 2.5: visibilidad de los miembros y tipo de la clase."""

    def node(self, **extra):
        return {"id": "n1", "name": "Cuenta", "attributes": [], "methods": [], **extra}

    def classes(self, *nodes):
        return _map_edges_to_relationships({"nodes": list(nodes), "edges_raw": []})["classes"]

    def test_the_visibility_of_each_member_travels_to_the_editor(self):
        node = self.node(
            attributes=[{"name": "saldo", "type": "double", "visibility": "-"}, {"name": "titular", "type": "string", "visibility": "+"}],
            methods=[{"name": "depositar", "parameters": "monto: double", "returnType": "void", "visibility": "+"}],
        )

        (cuenta,) = self.classes(node)

        self.assertEqual([a["visibility"] for a in cuenta["attributes"]], ["-", "+"])
        self.assertEqual(cuenta["methods"][0]["visibility"], "+")

    def test_a_sign_left_inside_the_name_is_moved_to_the_visibility(self):
        node = self.node(attributes=[{"name": "- saldo", "type": "double"}], methods=[{"name": "#validar", "parameters": "", "returnType": ""}])

        (cuenta,) = self.classes(node)

        self.assertEqual(cuenta["attributes"][0], {"name": "saldo", "type": "double", "visibility": "-"})
        self.assertEqual(cuenta["methods"][0]["name"], "validar")
        self.assertEqual(cuenta["methods"][0]["visibility"], "#")

    def test_visibility_written_as_a_word_is_turned_into_its_sign(self):
        node = self.node(attributes=[{"name": "a", "type": "int", "visibility": "private"}, {"name": "b", "type": "int", "visibility": "Public"}, {"name": "c", "type": "int", "visibility": "protected"}, {"name": "d", "type": "int", "visibility": "package"}])

        (cuenta,) = self.classes(node)

        self.assertEqual([a["visibility"] for a in cuenta["attributes"]], ["-", "+", "#", "~"])

    def test_a_visibility_that_means_nothing_is_dropped_not_invented(self):
        node = self.node(attributes=[{"name": "a", "type": "int", "visibility": "secreto"}, {"name": "b", "type": "int", "visibility": ""}, {"name": "c", "type": "int", "visibility": None}, {"name": "d", "type": "int"}])

        (cuenta,) = self.classes(node)

        self.assertTrue(all("visibility" not in a for a in cuenta["attributes"]))

    def test_a_name_that_only_contains_a_sign_or_nothing_does_not_break(self):
        node = self.node(attributes=[{"name": "", "type": "int"}, {"name": "-", "type": "int"}, {"type": "int"}])

        (cuenta,) = self.classes(node)

        self.assertEqual(len(cuenta["attributes"]), 3)

    def test_members_that_are_not_objects_are_left_alone(self):
        node = self.node(attributes=["id: int"])

        (cuenta,) = self.classes(node)

        self.assertEqual(cuenta["attributes"], ["id: int"])

    def test_the_kind_of_the_class_is_kept_when_it_is_not_a_plain_class(self):
        kinds = [self.node(id=f"n{i}", name=f"C{i}", kind=kind) for i, kind in enumerate(["abstract", "interface", "enumeration", "Interface"])]

        result = self.classes(*kinds)

        self.assertEqual([c.get("kind") for c in result], ["abstract", "interface", "enumeration", "interface"])

    def test_a_plain_or_unknown_kind_is_not_written(self):
        result = self.classes(self.node(id="a", name="A", kind="class"), self.node(id="b", name="B", kind="otra cosa"), self.node(id="c", name="C"))

        self.assertTrue(all("kind" not in c for c in result))

    @override_settings(GEMINI_API_KEY="clave-de-prueba")
    def test_the_prompt_asks_for_visibility_and_the_kind_of_each_class(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"candidates": [{"content": {"parts": [{"text": '{"nodes": [], "edges_raw": []}'}]}}]}
        with patch("uml_api.services.services_gemini._post_gemini", return_value=response) as post:
            call_gemini_from_image("aW1hZ2Vu")

        prompt = post.call_args.args[0]["contents"][0]["parts"][0]["text"]
        for expected in ('"visibility"', "público", "privado", "protegido", "paquete", '"kind"', "interface", "enumeration", "abstract"):
            self.assertIn(expected, prompt)
