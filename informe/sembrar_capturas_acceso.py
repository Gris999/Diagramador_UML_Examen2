"""Prepara datos de ejemplo para las capturas del manual de acceso (personas ficticias @example.com, solo en una base LOCAL de demostración).

Uso, desde `back_generador_bd/` y con Django corriendo en local con AUTH_REQUIRED=True (misma base y misma DJANGO_SECRET_KEY que el servidor local):

    .venv/bin/python ../informe/sembrar_capturas_acceso.py <sesiones.json>

Crea cuatro diagramas con sus roles y escribe en <sesiones.json> las sesiones firmadas y los códigos de sala que usa `capturas_acceso.mjs`.
Nunca se corre contra el servidor de producción.
"""
import json, os, sys, uuid
sys.path.insert(0, os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diagramador_uml.settings")
import django
django.setup()
from django.conf import settings
from collab import auth, rooms
from collab.models import RoomMember, RoomSettings

ANA, BRUNO, CARLA, DARIO = "ana.quispe@example.com", "bruno.rojas@example.com", "carla.vaca@example.com", "dario.pinto@example.com"
_db = settings.DATABASES["default"]
if "postgresql" in _db["ENGINE"] and _db.get("HOST") not in ("localhost", "127.0.0.1"):
    sys.exit("Este script borra datos de las personas de ejemplo: solo se corre contra una base local de demostración.")
RoomMember.objects.filter(email__in=[ANA, BRUNO, CARLA, DARIO]).delete()

def sala(duenio, titulo, enlace=None, rol_enlace="viewer"):
    codigo = str(uuid.uuid4())
    rooms.enter(codigo, duenio, claim=True)
    rooms.update_settings(codigo, title=titulo)
    if enlace:
        rooms.update_settings(codigo, link_access=enlace, link_role=rol_enlace)
    return codigo

biblioteca = sala(ANA, "Biblioteca")
tienda = sala(ANA, "Tienda en línea", enlace="anyone", rol_enlace="viewer")
rooms.add_members(tienda, [BRUNO], ANA, "editor")
rooms.add_members(tienda, [CARLA], ANA, "viewer")
ventas = sala(BRUNO, "Sistema de ventas")
rooms.add_members(ventas, [ANA], BRUNO, "editor")
estudios = sala(CARLA, "Plan de estudios")
rooms.add_members(estudios, [ANA], CARLA, "viewer")
for codigo, quien in ((ventas, ANA), (estudios, ANA)):
    rooms.enter(codigo, quien)

out = dict(
    sesiones={n: auth.make_session(e) for n, e in (("ana", ANA), ("bruno", BRUNO), ("dario", DARIO))},
    salas=dict(biblioteca=biblioteca, tienda=tienda, ventas=ventas, estudios=estudios),
)
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "sesiones.json", "w"), indent=1)
print(json.dumps(out["salas"]))
print([(r["title"], r["role"]) for r in rooms.my_rooms(ANA)])
