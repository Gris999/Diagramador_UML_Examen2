from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from uml_api.services.xmi_service import export_uml_to_xmi


class XmiApiTests(APITestCase):

    def setUp(self):
        self.uml = {
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

    def test_export_endpoint_returns_xmi_file(self):
        response = self.client.post(
            "/api/xmi/export/",
            self.uml,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(
            response["Content-Type"].startswith("application/xml")
        )

        self.assertIn(
            "attachment",
            response["Content-Disposition"],
        )

        self.assertIn(
            'filename="diagram.xmi"',
            response["Content-Disposition"],
        )

        self.assertIn(
            b"Persona",
            response.content,
        )

    def test_export_endpoint_rejects_invalid_model(self):
        response = self.client.post(
            "/api/xmi/export/",
            {
                "classes": [None],
                "relationships": [],
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("error", response.data)

    def test_import_endpoint_returns_internal_uml_json(self):
        xmi_bytes = export_uml_to_xmi(self.uml)

        uploaded = SimpleUploadedFile(
            "diagram.xmi",
            xmi_bytes,
            content_type="application/xml",
        )

        response = self.client.post(
            "/api/xmi/import/",
            {"file": uploaded},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            len(response.data["classes"]),
            2,
        )

        names = {
            item["name"]
            for item in response.data["classes"]
        }

        self.assertEqual(
            names,
            {"Persona", "Mascota"},
        )

        self.assertEqual(
            len(response.data["relationships"]),
            1,
        )

    def test_import_endpoint_rejects_malformed_xmi(self):
        uploaded = SimpleUploadedFile(
            "broken.xmi",
            b"<not-valid",
            content_type="application/xml",
        )

        response = self.client.post(
            "/api/xmi/import/",
            {"file": uploaded},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "error",
            response.data,
        )

    def test_import_endpoint_requires_file(self):
        response = self.client.post(
            "/api/xmi/import/",
            {},
            format="multipart",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "error",
            response.data,
        )
