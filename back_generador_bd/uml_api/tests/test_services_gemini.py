from unittest import TestCase

from uml_api.services.services_gemini import (
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
