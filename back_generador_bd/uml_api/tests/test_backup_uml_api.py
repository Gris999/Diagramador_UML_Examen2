import uuid

from rest_framework import status
from rest_framework.test import APITestCase

from uml_api.models import BackupUML


class BackupUmlApiTests(APITestCase):
    """Regression coverage for the diagram persistence round-trip.

    A room's diagram must survive leaving and re-entering the room: the
    frontend POSTs the JointJS export to set_backup_uml and GETs it back
    from get_backup_uml when no live peer answers the full-state request.
    """

    def setUp(self):
        self.room_id = uuid.uuid4()
        self.uml = {
            "classes": [
                {
                    "id": "class-1",
                    "name": "Cliente",
                    "attributes": [{"name": "id", "type": "int"}],
                    "methods": [],
                    "position": {"x": 10, "y": 20},
                    "size": {"width": 180, "height": 110},
                }
            ],
            "relationships": [],
        }

    def _set_url(self, room_id):
        return f"/api/set_backup_uml/{room_id}/"

    def _get_url(self, room_id):
        return f"/api/get_backup_uml/{room_id}/"

    def test_get_backup_for_unknown_room_returns_404(self):
        response = self.client.get(self._get_url(self.room_id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(BackupUML.objects.count(), 0)

    def test_set_backup_persists_and_get_backup_restores_it(self):
        set_response = self.client.post(
            self._set_url(self.room_id), self.uml, format="json"
        )
        self.assertEqual(set_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BackupUML.objects.count(), 1)

        get_response = self.client.get(self._get_url(self.room_id))
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.json()["classes"][0]["name"], "Cliente")

    def test_set_backup_twice_updates_the_same_room_instead_of_duplicating(self):
        self.client.post(self._set_url(self.room_id), self.uml, format="json")

        updated_uml = {**self.uml, "classes": []}
        second_response = self.client.post(
            self._set_url(self.room_id), updated_uml, format="json"
        )

        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(BackupUML.objects.count(), 1)

        get_response = self.client.get(self._get_url(self.room_id))
        self.assertEqual(get_response.json()["classes"], [])
