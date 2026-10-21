from django.db import models


class Participant(models.Model):
    room = models.CharField(max_length=64)
    token = models.UUIDField()
    display_name = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("room", "token"),
                name="unique_participant_room_token",
            ),
        ]

    def __str__(self):
        return f"{self.display_name} ({self.room})"


class ActivityEvent(models.Model):
    room = models.CharField(max_length=64)
    actor = models.ForeignKey(
        Participant,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_events",
    )
    actor_name = models.CharField(max_length=40)
    actor_kind = models.CharField(max_length=16, default="user")
    type = models.CharField(max_length=32)
    target_id = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=255)
    data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=("room", "created_at"),
                name="activity_room_created_idx",
            ),
        ]
