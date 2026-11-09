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


class RoomMember(models.Model):
    """Quién aparece en una sala cuando se entra con el correo (`collab.rooms`): su rol y de dónde viene su acceso.

    `role` es lo que puede hacer: `owner` (todo), `editor` (editar e invitar) o `viewer` (solo mirar). `source` dice por qué está en la lista: lo
    creó (`owner`), lo invitaron (`invite`) o abrió la sala por su enlace público (`link`); en este último caso la fila solo sirve para que la sala
    aparezca en su lista «Mis diagramas»: lo que puede hacer lo decide la sala (`RoomSettings`) mientras el enlace siga abierto.
    Una sala tiene un solo propietario (lo asegura la restricción de abajo, también si dos personas la abren al mismo tiempo).
    """

    ROLE_OWNER = "owner"
    ROLE_EDITOR = "editor"
    ROLE_VIEWER = "viewer"
    SOURCE_OWNER = "owner"
    SOURCE_INVITE = "invite"
    SOURCE_LINK = "link"

    room = models.CharField(max_length=64)
    email = models.EmailField(max_length=254)
    role = models.CharField(max_length=16, default=ROLE_EDITOR)
    source = models.CharField(max_length=16, default=SOURCE_INVITE)
    invited_by = models.EmailField(max_length=254, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("room", "email"), name="unique_room_member_email"),
            models.UniqueConstraint(
                fields=("room",),
                condition=models.Q(role="owner"),
                name="one_owner_per_room",
            ),
        ]
        indexes = [
            models.Index(fields=("room",), name="room_member_room_idx"),
            models.Index(fields=("email",), name="room_member_email_idx"),
        ]

    def __str__(self):
        return f"{self.email} ({self.role}) en {self.room}"


class RoomSettings(models.Model):
    """Cómo se comparte una sala y cómo se llama: el nombre, el acceso general (restringido o cualquiera con el enlace) y si está borrada."""

    LINK_RESTRICTED = "restricted"
    LINK_ANYONE = "anyone"

    room = models.CharField(max_length=64, unique=True)
    title = models.CharField(max_length=80, blank=True, default="")
    link_access = models.CharField(max_length=16, default=LINK_RESTRICTED)
    link_role = models.CharField(max_length=16, default=RoomMember.ROLE_VIEWER)
    deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title or 'Sin título'} ({self.room})"
