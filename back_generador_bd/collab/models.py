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


class ChatMessage(models.Model):
    """Mensaje de la conversación de la sala con la IA.

    La conversación es una sola por sala: la leen y la alimentan todas las personas de la sala. `participant` es quien preguntó (también en la
    respuesta de la IA) y `author_name` quién lo dijo.
    """

    ROLE_USER = "user"
    ROLE_IA = "ia"

    room = models.CharField(max_length=64)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    author_name = models.CharField(max_length=40, blank=True, default="")
    role = models.CharField(max_length=8)
    mode = models.CharField(max_length=8, default="ask")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=("participant", "id"),
                name="chat_participant_id_idx",
            ),
            models.Index(
                fields=("room", "id"),
                name="chat_room_id_idx",
            ),
        ]


class IaAttempt(models.Model):
    """Pedido a la IA que ya reservó cupo, haya salido bien o no.

    El tope por minuto cuenta estas filas y no los mensajes guardados: así un
    proveedor que falla, o pedidos simultáneos, igual gastan cupo.
    """

    room = models.CharField(max_length=64)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name="ia_attempts",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
