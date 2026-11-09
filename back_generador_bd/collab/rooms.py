"""Cómo se comparte cada sala cuando se entra con el correo: roles, acceso general (como en Google Docs) y la lista «Mis diagramas».

- **Roles por persona** (`RoomMember`): `owner` (todo: nombre, permisos, borrar), `editor` (edita e invita) y `viewer` (solo mira).
- **Acceso general** (`RoomSettings`): `restricted` (solo entran los correos agregados) o `anyone` (cualquiera con el enlace que haya iniciado
  sesión), y con qué rol entra quien llega por el enlace (`link_role`).
- El rol que una persona tiene de verdad es el más alto entre el suyo y el del enlace (si está abierto).
- Borrar una sala es lógico: queda marcada y nadie vuelve a entrar; sus datos no se tocan.
"""

from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import RoomMember, RoomSettings

OWNER = RoomMember.ROLE_OWNER
EDITOR = RoomMember.ROLE_EDITOR
VIEWER = RoomMember.ROLE_VIEWER
RANK = {VIEWER: 1, EDITOR: 2, OWNER: 3}
ASSIGNABLE_ROLES = (VIEWER, EDITOR)
LINK_MODES = (RoomSettings.LINK_RESTRICTED, RoomSettings.LINK_ANYONE)
MAX_TITLE_CHARS = 80
# Métodos que solo leen: con rol de lector se pueden usar; el resto (escribir) pide ser editor.
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


class SharingError(ValueError):
    """Un cambio de permisos que no procede; el mensaje se le muestra a la persona."""


def at_least(role, needed):
    return RANK.get(role, 0) >= RANK[needed]


def higher(first, second):
    return first if RANK.get(first, 0) >= RANK.get(second, 0) else second


def settings_of(room):
    return RoomSettings.objects.filter(room=room).first()


def _role_from(member, cfg):
    """Lo que una persona puede hacer: su rol (si la agregaron) o el del enlace (si está abierto), el más alto de los dos."""
    if cfg is not None and cfg.deleted:
        return None
    role = member.role if member is not None and member.source != RoomMember.SOURCE_LINK else None
    if cfg is not None and cfg.link_access == RoomSettings.LINK_ANYONE:
        role = higher(role, cfg.link_role) if role else cfg.link_role
    return role


def effective_role(room, email):
    """El rol de ese correo en la sala (`owner`, `editor`, `viewer`) o `None` si no tiene acceso. No cambia nada."""
    member = RoomMember.objects.filter(room=room, email=email).first()
    return _role_from(member, settings_of(room))


def _touch(room, email, cfg):
    """Anota que la persona abrió la sala ahora (para ordenar «Mis diagramas»); si entró por el enlace público, la sala queda en su lista."""
    now = timezone.now()
    if RoomMember.objects.filter(room=room, email=email).update(last_opened_at=now) == 0:
        try:
            RoomMember.objects.create(
                room=room, email=email, role=cfg.link_role if cfg else VIEWER, source=RoomMember.SOURCE_LINK, last_opened_at=now
            )
        except IntegrityError:
            RoomMember.objects.filter(room=room, email=email).update(last_opened_at=now)


def enter(room, email, *, claim=False):
    """Entra a la sala. Devuelve `(estado, rol)`.

    Estado `ok`: tiene acceso. `denied`: la sala ya tiene gente (o está borrada) y él no puede entrar. `unclaimed`: nadie la abrió todavía y no
    se pidió reclamarla. Con `claim=True` el primero que llega a una sala sin dueño queda como propietario (si dos llegan a la vez, solo una
    gana: lo asegura la base de datos).
    """
    cfg = settings_of(room)
    if cfg is not None and cfg.deleted:
        return "denied", None
    if not RoomMember.objects.filter(room=room).exists():
        if not claim:
            return "unclaimed", None
        try:
            with transaction.atomic():
                RoomMember.objects.create(
                    room=room, email=email, role=OWNER, source=RoomMember.SOURCE_OWNER, last_opened_at=timezone.now()
                )
                RoomSettings.objects.get_or_create(room=room)
        except IntegrityError:
            return enter(room, email)
        return "ok", OWNER
    role = effective_role(room, email)
    if role is None:
        return "denied", None
    cfg = cfg or RoomSettings.objects.get_or_create(room=room)[0]  # una sala de antes de los permisos recibe los de siempre
    _touch(room, email, cfg)
    return "ok", role


def list_members(room):
    """Las personas agregadas a la sala (no las que solo abrieron el enlace): el propietario primero, después por orden de llegada."""
    rows = RoomMember.objects.filter(room=room).exclude(source=RoomMember.SOURCE_LINK).order_by("created_at", "id")
    items = [{"email": r.email, "role": r.role, "source": r.source} for r in rows]
    return [i for i in items if i["role"] == OWNER] + [i for i in items if i["role"] != OWNER]


def owner_of(room):
    member = RoomMember.objects.filter(room=room, role=OWNER).first()
    return member.email if member else None


def describe(room, email, role):
    """Todo lo que la pantalla necesita saber de la sala para esta persona."""
    cfg = settings_of(room)
    return {
        "required": True,
        "email": email,
        "role": role,
        "is_owner": role == OWNER,
        "can_edit": at_least(role, EDITOR),
        "title": cfg.title if cfg else "",
        "link_access": cfg.link_access if cfg else RoomSettings.LINK_RESTRICTED,
        "link_role": cfg.link_role if cfg else VIEWER,
        "owner": owner_of(room),
        "members": list_members(room),
    }


def clean_title(value):
    if not isinstance(value, str):
        raise SharingError("El nombre debe ser texto.")
    text = " ".join("".join(c for c in value if c.isprintable() or c.isspace()).split())
    if len(text) > MAX_TITLE_CHARS:
        raise SharingError(f"El nombre no puede pasar de {MAX_TITLE_CHARS} caracteres.")
    return text


def update_settings(room, *, title=None, link_access=None, link_role=None):
    """Cambia el nombre y el acceso general de la sala (lo hace el propietario). Solo se tocan los datos que llegan."""
    cfg, _ = RoomSettings.objects.get_or_create(room=room)
    if title is not None:
        cfg.title = clean_title(title)
    if link_access is not None:
        if link_access not in LINK_MODES:
            raise SharingError("El acceso general debe ser «restringido» o «cualquiera con el enlace».")
        cfg.link_access = link_access
    if link_role is not None:
        if link_role not in ASSIGNABLE_ROLES:
            raise SharingError("Con el enlace se puede entrar como lector o como editor.")
        cfg.link_role = link_role
    cfg.save()
    return cfg


def add_members(room, emails, invited_by, role):
    """Agrega correos con ese rol y devuelve los que son nuevos en la lista. Quien ya estaba agregado conserva su rol (se cambia aparte)."""
    if role not in ASSIGNABLE_ROLES:
        raise SharingError("La persona puede entrar como lector o como editor.")
    added = []
    for email in emails:
        member, created = RoomMember.objects.get_or_create(
            room=room, email=email,
            defaults={"role": role, "source": RoomMember.SOURCE_INVITE, "invited_by": invited_by or ""},
        )
        if not created and member.source == RoomMember.SOURCE_LINK:
            # Estaba solo porque abrió el enlace: ahora la invitaron de verdad.
            RoomMember.objects.filter(pk=member.pk).update(role=role, source=RoomMember.SOURCE_INVITE, invited_by=invited_by or "")
            created = True
        if created:
            added.append(email)
    return added


def remove_added(room, emails):
    """Quita a invitados que se acaban de agregar (nunca al propietario): se usa si el correo de la invitación no salió."""
    RoomMember.objects.filter(room=room, email__in=emails, source=RoomMember.SOURCE_INVITE).exclude(role=OWNER).delete()


def set_member_role(room, email, role):
    """Cambia el rol de alguien de la lista (no del propietario). `False` si esa persona no está en la lista."""
    if role not in ASSIGNABLE_ROLES:
        raise SharingError("La persona puede entrar como lector o como editor.")
    updated = (
        RoomMember.objects.filter(room=room, email=email).exclude(role=OWNER).exclude(source=RoomMember.SOURCE_LINK).update(role=role)
    )
    return updated > 0


def remove_member(room, email):
    """Quita a alguien de la sala (no al propietario). `False` si no estaba."""
    deleted, _ = RoomMember.objects.filter(room=room, email=email).exclude(role=OWNER).delete()
    return deleted > 0


def delete_room(room):
    """Borra la sala: queda marcada y nadie vuelve a entrar (sus datos no se tocan)."""
    cfg, _ = RoomSettings.objects.get_or_create(room=room)
    cfg.deleted = True
    cfg.save(update_fields=["deleted", "updated_at"])


def my_rooms(email):
    """Las salas de esa persona para «Mis diagramas»: las suyas, a las que la invitaron y las que abrió por un enlace público (si sigue abierto)."""
    rows = list(RoomMember.objects.filter(email=email))
    names = [r.room for r in rows]
    configs = {c.room: c for c in RoomSettings.objects.filter(room__in=names)}
    owners = dict(RoomMember.objects.filter(room__in=names, role=OWNER).values_list("room", "email"))
    documents = []
    for member in rows:
        cfg = configs.get(member.room)
        role = _role_from(member, cfg)
        if role is None:
            continue
        documents.append({
            "room": member.room,
            "title": cfg.title if cfg else "",
            "role": role,
            "owner": owners.get(member.room),
            "link_access": cfg.link_access if cfg else RoomSettings.LINK_RESTRICTED,
            "created_at": member.created_at.isoformat(),
            "last_opened_at": member.last_opened_at.isoformat() if member.last_opened_at else None,
            "_sort": (member.last_opened_at or member.created_at),
        })
    documents.sort(key=lambda d: d["_sort"], reverse=True)
    for document in documents:
        del document["_sort"]
    return documents
