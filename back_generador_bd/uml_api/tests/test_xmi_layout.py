from django.test import SimpleTestCase

from uml_api.services.xmi_service import (
    export_uml_to_xmi,
    import_xmi_to_uml,
)


class XMILayoutTests(SimpleTestCase):
    def test_round_trip_preserves_class_position_and_size(self):
        source = {
            "classes": [
                {
                    "id": "persona",
                    "name": "Persona",
                    "attributes": [
                        {
                            "name": "nombre",
                            "type": "String",
                        }
                    ],
                    "methods": [],
                    "position": {
                        "x": 123,
                        "y": 87,
                    },
                    "size": {
                        "width": 245,
                        "height": 160,
                    },
                },
                {
                    "id": "mascota",
                    "name": "Mascota",
                    "attributes": [],
                    "methods": [],
                    "position": {
                        "x": 531,
                        "y": 342,
                    },
                    "size": {
                        "width": 190,
                        "height": 120,
                    },
                },
            ],
            "relationships": [
                {
                    "id": "persona-mascota",
                    "type": "association",
                    "sourceId": "persona",
                    "targetId": "mascota",
                    "labels": ["1", "0..*"],
                }
            ],
        }

        xmi = export_uml_to_xmi(source)
        imported = import_xmi_to_uml(xmi)

        classes = {
            uml_class["id"]: uml_class
            for uml_class in imported["classes"]
        }

        self.assertEqual(
            classes["persona"]["position"],
            {
                "x": 123,
                "y": 87,
            },
        )

        self.assertEqual(
            classes["persona"]["size"],
            {
                "width": 245,
                "height": 160,
            },
        )

        self.assertEqual(
            classes["mascota"]["position"],
            {
                "x": 531,
                "y": 342,
            },
        )

        self.assertEqual(
            classes["mascota"]["size"],
            {
                "width": 190,
                "height": 120,
            },
        )
