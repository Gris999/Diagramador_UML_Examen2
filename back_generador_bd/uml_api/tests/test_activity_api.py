import uuid

from django.db import IntegrityError, transaction
from rest_framework.test import APITestCase

from collab.models import ActivityEvent, Participant


class ParticipantActivityModelTests(APITestCase):
    def test_participant_is_unique_by_room_and_token(self):
        token = uuid.uuid4()
        participant = Participant.objects.create(
            room="team-alpha",
            token=token,
            display_name="Ana",
        )

        self.assertIsNotNone(participant.created_at)
        self.assertIsNotNone(participant.last_seen)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Participant.objects.create(
                room="team-alpha",
                token=token,
                display_name="Another name",
            )

        other_room = Participant.objects.create(
            room="team-beta",
            token=token,
            display_name="Ana",
        )
        self.assertNotEqual(participant.id, other_room.id)

    def test_activity_actor_is_nullable_and_kind_defaults_to_user(self):
        event = ActivityEvent.objects.create(
            room="human-readable-room",
            actor=None,
            actor_name="Usuario anónimo",
            type="delete",
            target_id="joint-cell-1",
            summary="eliminó un elemento",
            data={"t": "delete", "id": "joint-cell-1"},
        )

        self.assertIsNone(event.actor)
        self.assertEqual(event.actor_kind, "user")
        self.assertIsNotNone(event.created_at)


class RoomActivityApiTests(APITestCase):
    room = "sprint-demo"

    def create_event(self, number, room=None):
        return ActivityEvent.objects.create(
            room=room or self.room,
            actor=None,
            actor_name="Ana",
            type="add_class",
            target_id=f"class-{number}",
            summary=f"añadió la clase Clase{number}",
            data={"t": "add_class", "id": f"class-{number}"},
        )

    def test_history_is_room_scoped_and_oldest_first(self):
        first = self.create_event(1)
        second = self.create_event(2)
        self.create_event(3, room="another-room")

        response = self.client.get(f"/api/rooms/{self.room}/activity/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [event["id"] for event in response.data["events"]],
            [first.id, second.id],
        )
        self.assertEqual(response.data["events"][0]["room"], self.room)
        self.assertEqual(response.data["events"][0]["actor"], None)
        self.assertIn("created_at", response.data["events"][0])

    def test_since_returns_only_newer_event_ids(self):
        first = self.create_event(1)
        second = self.create_event(2)
        third = self.create_event(3)

        response = self.client.get(
            f"/api/rooms/{self.room}/activity/?since={first.id}"
        )

        self.assertEqual(
            [event["id"] for event in response.data["events"]],
            [second.id, third.id],
        )

    def test_without_since_returns_the_latest_events_oldest_first(self):
        created = [self.create_event(number) for number in range(150)]

        response = self.client.get(f"/api/rooms/{self.room}/activity/?limit=100")

        self.assertEqual(
            [event["id"] for event in response.data["events"]],
            [event.id for event in created[-100:]],
        )

    def test_limit_defaults_to_100_and_is_capped_at_200(self):
        for number in range(205):
            self.create_event(number)

        default_response = self.client.get(f"/api/rooms/{self.room}/activity/")
        capped_response = self.client.get(
            f"/api/rooms/{self.room}/activity/?limit=999"
        )

        self.assertEqual(len(default_response.data["events"]), 100)
        self.assertEqual(len(capped_response.data["events"]), 200)

    def test_invalid_query_values_fall_back_safely(self):
        self.create_event(1)

        response = self.client.get(
            f"/api/rooms/{self.room}/activity/?since=nope&limit=nope"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["events"]), 1)
