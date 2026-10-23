"""Especificaciones de los diagramas del informe para Enterprise Architect.

Los diagramas por caso de uso (casos de uso, comunicación, clases de análisis, paquetes y secuencia) salen
de los mismos datos que las tablas del informe (`parte2_datos.py`); los de diseño (código, despliegue, capas,
datos, componentes y subsistemas) se describen aquí. Los identificadores coinciden con los de `parte2.py`
(`' ea:<id>`), que es como el generador del informe sabe qué imagen de EA pone en cada lugar.

Regla de orden en EA: cada diagrama vive en el mismo paquete que sus elementos. Así EA no antepone el nombre
del paquete ("Paquete::Clase", "(from ...)") y los mensajes de un diagrama no aparecen en otro.
"""

import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout  # noqa: E402
from parte2 import _mensajes, _roles, clases_analisis  # noqa: E402
from parte2_datos import CICLOS, CUS, DEPENDENCIAS_PAQUETES, NOMBRE_ACTOR, PAQUETES  # noqa: E402

REQ = "Modelo de requisitos y análisis"
MARGEN = 30


def num(cu):
    """CU-14 -> CU14 y CU-01 -> CU1, como se citan los casos de uso en el informe."""
    return re.sub(r"CU-0?(\d+)", r"CU\1", cu)


def nombre_cu(cu):
    return f"{num(cu)}: {CUS[cu]['nombre']}"


class Modelo:
    def __init__(self):
        self.elementos = {}
        self.diagramas = []

    def elem(self, clave, tipo, nombre, ruta, **extra):
        nuevo = dict(tipo=tipo, nombre=nombre, ruta=ruta, **extra)
        if clave in self.elementos:
            actual = self.elementos[clave]
            if (actual["tipo"], actual["nombre"], actual["ruta"]) != (tipo, nombre, ruta):
                raise ValueError(f"la clave {clave!r} se usa para dos elementos distintos: {actual['nombre']!r} y {nombre!r}")
        else:
            self.elementos[clave] = nuevo
        return clave

    def diagrama(self, id_, nombre, tipo, ruta, objetos, conectores, enlaces=None):
        """`objetos`: [(clave, x, y, w, h)] en orden de dibujo (los primeros quedan al fondo)."""
        minimo_x = min(o[1] for o in objetos)
        minimo_y = min(o[2] for o in objetos)
        dx, dy = MARGEN - minimo_x, MARGEN + 10 - minimo_y
        # `enlaces`: "paralelos" separa las líneas que unen el mismo par; "ocultar" no dibuja los conectores que EA
        # muestra solos al coincidir dos elementos de otro diagrama.
        if enlaces is None:
            enlaces = "" if tipo == "Sequence" else "paralelos"
        self.diagramas.append(dict(
            id=id_, nombre=nombre, tipo=tipo, ruta=ruta, enlaces=enlaces,
            objetos=[dict(k=o[0], x=o[1] + dx, y=o[2] + dy, w=o[3], h=o[4], **(o[5] if len(o) > 5 else {})) for o in objetos],
            conectores=conectores))


# ---- tamaños ---------------------------------------------------------------------------------------
def tam_actor(nombre):
    return max(80, 7 * len(nombre)), 100


def tam_cu(nombre):
    lineas = max(2, math.ceil(len(nombre) / 27))
    return 175, 38 + 15 * lineas


def tam_icono(etiqueta):
    return 80, 70


def tam_clase(nombre, miembros):
    ancho = max(150, int(7 * max([len(nombre) + 8] + [len(m) + 4 for m in miembros])))
    return ancho, 40 + 17 * max(1, len(miembros))


# ---- casos de uso ----------------------------------------------------------------------------------
def _actor(m, a):
    return m.elem(a, "Actor", NOMBRE_ACTOR[a], REQ)


def _caso(m, cu):
    return m.elem(cu, "UseCase", nombre_cu(cu), REQ)


def diagrama_casos_uso(m, id_, nombre, codigos):
    mostrados = list(codigos)
    for cu in codigos:
        for inc in CUS[cu]["incluye"]:
            if inc not in mostrados:
                mostrados.append(inc)
    primarios, secundarios = [], []
    for cu in codigos:
        for indice, actor in enumerate(CUS[cu]["actores"]):
            destino = primarios if (indice == 0 or actor == "A2") else secundarios
            if actor not in primarios and actor not in secundarios:
                destino.append(actor)
    nodos = {a: tam_actor(NOMBRE_ACTOR[a]) for a in primarios + secundarios}
    nodos.update({cu: tam_cu(nombre_cu(cu)) for cu in mostrados})
    aristas, conectores = [], []
    for cu in codigos:
        for actor in CUS[cu]["actores"]:
            if actor in primarios:
                aristas.append((actor, cu))
                conectores.append(dict(de=actor, a=cu, tipo="Association"))
            else:
                aristas.append((cu, actor))
                conectores.append(dict(de=cu, a=actor, tipo="Association"))
        for inc in CUS[cu]["incluye"]:
            aristas.append((cu, inc))
            conectores.append(dict(de=cu, a=inc, tipo="Dependency", est="include"))
    if "A2" in primarios and "A1" in primarios:
        aristas.append(("A2", "A1"))
        conectores.append(dict(de="A2", a="A1", tipo="Generalization"))
    for a in primarios + secundarios:
        _actor(m, a)
    for cu in mostrados:
        _caso(m, cu)
    m.elem("SYS", "Boundary", "Plataforma CASE colaborativa", REQ)
    # Participante y Host (generalización) van uno sobre otro, en la misma columna.
    mismo_nivel = {"A1": 0, "A2": 0} if "A2" in primarios and "A1" in primarios else None
    pos, _ = layout.dot(nodos, aristas, "LR", 16, 80, agrupar=mismo_nivel)
    x0 = min(pos[c][0] for c in mostrados) - 25
    y0 = min(pos[c][1] for c in mostrados) - 40
    x1 = max(pos[c][0] + nodos[c][0] for c in mostrados) + 25
    y1 = max(pos[c][1] + nodos[c][1] for c in mostrados) + 25
    # Los actores quedan siempre fuera del límite del sistema.
    for a in primarios:
        pos[a] = (min(pos[a][0], x0 - 40 - nodos[a][0]), pos[a][1])
    for a in secundarios:
        pos[a] = (max(pos[a][0], x1 + 40), pos[a][1])
    objetos = [("SYS", x0, y0, x1 - x0, y1 - y0)] + [(c, *pos[c], *nodos[c]) for c in nodos]
    m.diagrama(id_, nombre, "Use Case", REQ, objetos, conectores)


# ---- paquetes de análisis --------------------------------------------------------------------------
def _paquete(m, indice):
    nombre = PAQUETES[indice][0].upper()
    return m.elem(f"PKG{indice + 1}", "Package", nombre, REQ)


def _caja_paquete(cus, columnas=2, hueco=24):
    """(ancho, alto, {cu: (dx, dy)}) de un paquete que contiene los casos de uso `cus` en rejilla."""
    tamanos = {cu: tam_cu(nombre_cu(cu)) for cu in cus}
    posiciones, (ancho, alto) = layout.rejilla(tamanos, columnas, hueco, hueco)
    return ancho + 40, alto + 70, {cu: (posiciones[cu][0] + 20, posiciones[cu][1] + 50) for cu in cus}


def diagrama_paquetes_identificados(m):
    objetos, conectores = [], []
    for i, (nombre, contenido, _) in enumerate(PAQUETES):
        clave = _paquete(m, i)
        nota = m.elem(f"NT{i + 1}", "Note", "", REQ, notas=contenido)
        x, y = (i % 2) * 560, (i // 2) * 130
        objetos += [(clave, x, y, 220, 90), (nota, x + 250, y, 280, 90)]
        conectores.append(dict(de=nota, a=clave, tipo="NoteLink"))
    m.diagrama("pk-identificados", "Paquetes de análisis identificados", "Package", REQ, objetos, conectores)


def diagrama_paquetes_y_cu(m):
    cajas = [_caja_paquete(cus, 2) for _, _, cus in PAQUETES]
    tamanos = {i: (c[0], c[1]) for i, c in enumerate(cajas)}
    pos, _ = layout.rejilla(tamanos, 2, 50, 50)
    objetos = []
    for i, (nombre, _, cus) in enumerate(PAQUETES):
        ancho, alto, internos = cajas[i]
        px, py = pos[i]
        objetos.append((_paquete(m, i), px, py, ancho, alto))
        for cu in cus:
            _caso(m, cu)
            objetos.append((cu, px + internos[cu][0], py + internos[cu][1], *tam_cu(nombre_cu(cu))))
    m.diagrama("pk-cu", "Paquetes de análisis y casos de uso", "Package", REQ, objetos, [], enlaces="ocultar")


def diagrama_vista_paquete(m, indice):
    nombre, _, cus = PAQUETES[indice]
    actores = []
    for cu in cus:
        a = CUS[cu]["actores"][0]
        if a not in actores:
            actores.append(a)
    ancho, alto, internos = _caja_paquete(cus, 2 if len(cus) < 7 else 3)
    px = 160
    objetos = [(_paquete(m, indice), px, 0, ancho, alto)]
    for cu in cus:
        _caso(m, cu)
        objetos.append((cu, px + internos[cu][0], internos[cu][1], *tam_cu(nombre_cu(cu))))
    conectores = []
    paso = alto / (len(actores) + 1)
    for i, a in enumerate(actores, 1):
        _actor(m, a)
        w, h = tam_actor(NOMBRE_ACTOR[a])
        objetos.append((a, 20, int(paso * i - h / 2), w, h))
    for cu in cus:
        conectores.append(dict(de=CUS[cu]["actores"][0], a=cu, tipo="Association"))
        for inc in CUS[cu]["incluye"]:
            if inc in cus:
                conectores.append(dict(de=cu, a=inc, tipo="Dependency", est="include"))
    m.diagrama(f"pk-vista-{indice + 1}", f"Vista del paquete {nombre}", "Package", REQ, objetos, conectores)


def diagrama_dependencias_paquetes(m):
    claves = {nombre: _paquete(m, i) for i, (nombre, _, _) in enumerate(PAQUETES)}
    sitio = {"Asistencia por IA": (330, 0), "Colaboración": (60, 170), "Actividad": (600, 170),
             "Modelado": (330, 340), "Interoperabilidad": (30, 340), "Generación": (630, 340)}
    objetos = [(claves[n], *sitio[n], 220, 80) for n in sitio]
    conectores = [dict(de=claves[o], a=claves[d], tipo="Dependency") for o, d in DEPENDENCIAS_PAQUETES]
    m.diagrama("pk-dep", "Dependencias entre paquetes de análisis", "Package", REQ, objetos, conectores)


# ---- comunicación y secuencia por caso de uso --------------------------------------------------------
def _roles_ea(m, cu, prefijo, ruta):
    """Elementos del caso de uso para un diagrama: {rol: clave}. Cada diagrama tiene los suyos."""
    claves, roles = {}, _roles(cu)
    for rol, (tipo, etiqueta) in roles.items():
        clave = f"{prefijo}:{cu}:{rol}"
        if rol in ("U", "EX"):
            m.elem(clave, "Actor", etiqueta, ruta)
        else:
            est = {"IU": "boundary", "CT": "control"}.get(rol, "entity")
            m.elem(clave, "Class", etiqueta, ruta, est=est)
        claves[rol] = clave
    return claves, roles


def diagrama_comunicacion(m, cu):
    ruta = f"Análisis de casos de uso|Comunicación {num(cu)}"
    claves, roles = _roles_ea(m, cu, "com", ruta)
    mensajes = _mensajes(cu)
    nodos = {}
    for rol, clave in claves.items():
        etiqueta = roles[rol][1]
        w, h = tam_actor(etiqueta) if rol in ("U", "EX") else tam_icono(etiqueta)
        nodos[clave] = (max(w, 6 * len(etiqueta)), h + 25)
    aristas = [(claves[o], claves[d]) for o, d, _, r in mensajes if not r and o != d]
    pos, _ = layout.dot(nodos, aristas, "LR", 30, 105)
    objetos = []
    for rol, clave in claves.items():
        w, h = tam_actor(roles[rol][1]) if rol in ("U", "EX") else tam_icono(roles[rol][1])
        px, py = pos[clave]
        objetos.append((clave, px + (nodos[clave][0] - w) // 2, py, w, h))
    conectores = []
    for numero, (origen, destino, texto, retorno) in enumerate(mensajes, 1):
        if origen == destino:
            continue
        conectores.append(dict(de=claves[origen], a=claves[destino], tipo="Dependency" if retorno else "Association",
                               nombre=f"{numero}: {texto}", dir="Source -> Destination"))
    m.diagrama(f"com-{cu.replace('-', '')}", f"{num(cu)}: {CUS[cu]['nombre']}", "Collaboration", ruta, objetos, conectores)


def diagrama_secuencia(m, cu):
    """Secuencia con la separación mínima que deja leer cada mensaje (los textos largos ensanchan su tramo)."""
    ruta = f"Diseño de secuencia|Secuencia {num(cu)}"
    claves, roles = _roles_ea(m, cu, "sec", ruta)
    mensajes = _mensajes(cu)
    orden = list(claves)
    indice = {rol: i for i, rol in enumerate(orden)}
    tramos = [140] * (len(orden) - 1)  # separación entre líneas de vida vecinas
    pedidos = []
    for origen, destino, texto, _ in mensajes:
        a, b = sorted((indice[origen], indice[destino]))
        if a != b:
            pedidos.append((b - a, a, b, int(6.4 * len(texto)) + 40))
    for _, a, b, necesario in sorted(pedidos):
        actual = sum(tramos[a:b])
        if actual < necesario:
            for k in range(a, b):
                tramos[k] += (necesario - actual) / (b - a)
    xs, x = [0], 0
    for tramo in tramos:
        x += tramo
        xs.append(x)
    objetos = []
    for rol, clave in claves.items():
        es_actor = rol in ("U", "EX")
        w, h = (tam_actor(roles[rol][1])[0], 90) if es_actor else (80, 70)
        objetos.append((clave, int(xs[indice[rol]] - w / 2), 0, w, h))
    conectores = [dict(de=claves[o], a=claves[d], tipo="Sequence", nombre=t, seq=n)
                  for n, (o, d, t, _) in enumerate(mensajes, 1)]
    m.diagrama(f"sec-{cu.replace('-', '')}", f"{num(cu)}: {CUS[cu]['nombre']}", "Sequence", ruta, objetos, conectores)


# ---- clases de análisis por ciclo --------------------------------------------------------------------
def diagrama_clases_analisis(m, numero, codigos):
    ruta = f"Clases de análisis|Ciclo {numero}"
    interfaces, controles, entidades, relaciones = clases_analisis(codigos)
    nodos, objetos = {}, []
    # «control» con un espacio al final: sin él EA dibuja el icono de control en lugar de la caja con operaciones.
    for est, grupo in (("interfaz", interfaces), ("control ", controles), ("entidad", entidades)):
        for nombre, ops in grupo.items():
            clave = f"cla:{numero}:{nombre}"
            miembros = sorted(o.replace("()", "") + "()" for o in ops)
            m.elem(clave, "Class", nombre, ruta, est=est, meths=[(o.replace("()", ""), "", "Public", "") for o in sorted(ops)])
            nodos[clave] = tam_clase(nombre, miembros)
    aristas = [(f"cla:{numero}:{o}", f"cla:{numero}:{d}") for o, d in sorted(relaciones)]
    pos, _ = layout.dot(nodos, aristas, "LR", 40, 110)
    objetos = [(k, *pos[k], *nodos[k]) for k in nodos]
    conectores = [dict(de=o, a=d, tipo="Association", dir="Source -> Destination") for o, d in aristas]
    m.diagrama(f"cla-ciclo-{numero}", f"Clases de análisis del ciclo {numero}", "Class", ruta, objetos, conectores)


# ---- diseño ------------------------------------------------------------------------------------------
def diagrama_codigo(m):
    ruta = "Diseño de código"
    m.elem("co:AIP", "Class", "AIProvider", ruta, est="interface", meths=[
        ("chat", "str", "Public", "prompt:str"), ("change", "dict", "Public", "instruction:str;uml:dict")])
    m.elem("co:GEM", "Class", "GeminiProvider", ruta, meths=[
        ("chat", "str", "Public", "prompt:str"), ("change", "dict", "Public", "instruction:str;uml:dict")])
    m.elem("co:OLL", "Class", "OllamaProvider", ruta,
           attrs=[("model", "str", "", "Private"), ("change_model", "str", "", "Private")],
           meths=[("chat", "str", "Public", "prompt:str"), ("change", "dict", "Public", "instruction:str;uml:dict")])
    m.elem("co:MOD", "Class", "modelo_reentrenado", ruta, est="módulo", meths=[
        ("compactar", "", "Public", "uml:dict"), ("mensajes", "", "Public", "uml:dict;pedido:str"),
        ("restaurar", "", "Public", "cambios:dict;alias:dict;uml:dict"), ("quitar_razonamiento", "", "Public", "texto:str")])
    m.elem("co:GRD", "Class", "change_guard", ruta, est="módulo", meths=[
        ("validate_changes", "", "Public", "cambios:dict"), ("count_destructive", "", "Public", "cambios:dict;uml:dict")])
    m.elem("co:VW", "Class", "ChatView", ruta, est="vista", meths=[
        ("ia_chat", "", "Public", "request:Request;room:str"),
        ("claim_suggestion", "", "Public", "request:Request;room:str;id:str;idx:int")])
    nodos = {"co:AIP": (260, 90), "co:GEM": (260, 90), "co:OLL": (300, 130), "co:MOD": (330, 120), "co:GRD": (330, 90), "co:VW": (350, 90)}
    aristas = [("co:GEM", "co:AIP"), ("co:OLL", "co:AIP"), ("co:OLL", "co:MOD"), ("co:VW", "co:AIP"), ("co:VW", "co:GRD")]
    pos, _ = layout.dot(nodos, aristas, "BT", 50, 90)
    conectores = [dict(de="co:GEM", a="co:AIP", tipo="Realization"), dict(de="co:OLL", a="co:AIP", tipo="Realization"),
                  dict(de="co:OLL", a="co:MOD", tipo="Dependency", nombre="usa"),
                  dict(de="co:VW", a="co:AIP", tipo="Dependency"), dict(de="co:VW", a="co:GRD", tipo="Dependency")]
    m.diagrama("codigo", "Diagrama de código: proveedores de IA", "Class", ruta, [(k, *pos[k], *nodos[k]) for k in nodos], conectores)


def diagrama_despliegue(m):
    ruta = "Diseño físico"
    nodo = lambda k, nombre, est, **kw: m.elem(k, "Node", nombre, ruta, est=est, **kw)
    art = lambda k, nombre, padre, est="": m.elem(k, "Artifact", nombre, ruta, padre=padre, est=est)
    nodo("dp:N", "Navegador del usuario", "device")
    art("dp:A", "Aplicación Angular", "dp:N")
    nodo("dp:EC2", "AWS EC2 (Ubuntu 24.04, 2 vCPU, 2 GB)", "device")
    nodo("dp:NG", "nginx + Let's Encrypt", "execution environment", padre="dp:EC2")
    nodo("dp:DK", "Docker Compose", "execution environment", padre="dp:EC2")
    art("dp:FE", "angular_frontend :4000 (publicado 4200)", "dp:DK")
    art("dp:DJ", "django_backend_UML :8000 (Daphne)", "dp:DK")
    art("dp:SP", "spring_backend :7001", "dp:DK")
    art("dp:PG", "postgres_db :5432", "dp:DK", "database")
    art("dp:RD", "redis_server :6379", "dp:DK", "database")
    nodo("dp:G", "Google Gemini API (nube)", "")
    nodo("dp:MAC", "Equipo con Apple Silicon", "device")
    art("dp:OL", "Ollama + modelo reentrenado :11434", "dp:MAC")
    objetos = [("dp:N", 0, 140, 150, 100), ("dp:A", 10, 175, 125, 50),
               ("dp:EC2", 230, 0, 590, 410), ("dp:NG", 245, 165, 130, 70), ("dp:DK", 400, 30, 400, 360),
               ("dp:FE", 415, 75, 175, 60), ("dp:DJ", 610, 75, 175, 60), ("dp:SP", 415, 160, 175, 60),
               ("dp:PG", 415, 290, 175, 60), ("dp:RD", 610, 290, 175, 60),
               ("dp:G", 900, 30, 170, 70), ("dp:MAC", 900, 230, 190, 130), ("dp:OL", 910, 270, 165, 70)]
    conectores = [dict(de="dp:N", a="dp:NG", nombre="HTTPS / WSS :443"), dict(de="dp:NG", a="dp:FE", nombre="/"),
                  dict(de="dp:NG", a="dp:DJ", nombre="/api, /ws"), dict(de="dp:NG", a="dp:SP", nombre="/generate"),
                  dict(de="dp:DJ", a="dp:PG"), dict(de="dp:DJ", a="dp:RD"), dict(de="dp:DJ", a="dp:G", nombre="HTTPS"),
                  dict(de="dp:DJ", a="dp:OL", tipo="Dependency", nombre="HTTP (opcional)")]
    m.diagrama("despliegue", "Diagrama de despliegue", "Deployment", ruta, objetos, conectores)


def diagrama_capas(m):
    ruta = "Diseño lógico"
    capas = [("Capa de presentación", [("cp:ui", "Componentes Angular (editor, paneles, chat, vista móvil)")]),
             ("Capa de aplicación", [("cp:sv", "Servicios Angular (colaboración, IA, diagrama)"),
                                     ("cp:vw", "Vistas DRF y consumidores de WebSocket")]),
             ("Capa de dominio", [("cp:dm", "Modelo del diagrama (JointJS: clases y relaciones)"),
                                  ("cp:md", "Modelos de datos Django (participante, actividad, chat)")]),
             ("Capa de infraestructura", [("cp:pg", "PostgreSQL"), ("cp:rd", "Redis"),
                                          ("cp:pv", "Proveedores de IA (Gemini, Ollama)"), ("cp:gn", "Generador Spring Boot")])]
    ancho, objetos, y = 560, [], 0
    for i, (titulo, comps) in enumerate(capas, 1):
        m.elem(f"C{i}", "Package", titulo, ruta)
        filas = math.ceil(len(comps) / 2)
        alto = 50 + filas * 55
        objetos.append((f"C{i}", 0, y, ancho, alto))
        for j, (k, nombre) in enumerate(comps):
            m.elem(k, "Component", nombre, ruta)
            if len(comps) == 1:
                objetos.append((k, 90, y + 50, ancho - 180, 45))
            else:
                objetos.append((k, 20 + (j % 2) * 270, y + 50 + (j // 2) * 55, 250, 45))
        y += alto + 40
    conectores = [dict(de="cp:ui", a="cp:sv", tipo="Dependency"), dict(de="cp:sv", a="cp:vw", tipo="Dependency"),
                  dict(de="cp:vw", a="cp:md", tipo="Dependency"), dict(de="cp:sv", a="cp:dm", tipo="Dependency"),
                  dict(de="cp:md", a="cp:pg", tipo="Dependency"), dict(de="cp:vw", a="cp:rd", tipo="Dependency"),
                  dict(de="cp:vw", a="cp:pv", tipo="Dependency"), dict(de="cp:vw", a="cp:gn", tipo="Dependency")]
    m.diagrama("capas", "Diseño lógico en capas", "Package", ruta, objetos, conectores)


TABLAS_DATOS = [
    ("collab_participant", [("id", "bigint", "PK"), ("room", "varchar(64)", ""), ("token", "uuid", ""),
                            ("display_name", "varchar(40)", ""), ("created_at", "timestamptz", ""), ("last_seen", "timestamptz", "")]),
    ("collab_activityevent", [("id", "bigint", "PK"), ("room", "varchar(64)", ""), ("actor_id", "bigint", "FK"),
                              ("actor_name", "varchar(40)", ""), ("actor_kind", "varchar(16)", ""), ("type", "varchar(32)", ""),
                              ("summary", "varchar(255)", ""), ("data", "jsonb", ""), ("created_at", "timestamptz", "")]),
    ("collab_chatmessage", [("id", "bigint", "PK"), ("room", "varchar(64)", ""), ("participant_id", "bigint", "FK"),
                            ("role", "varchar(8)", ""), ("mode", "varchar(8)", ""), ("content", "text", ""),
                            ("created_at", "timestamptz", "")]),
    ("collab_iaattempt", [("id", "bigint", "PK"), ("room", "varchar(64)", ""), ("participant_id", "bigint", "FK"),
                          ("created_at", "timestamptz", "")]),
    ("uml_api_backupuml", [("id", "bigint", "PK"), ("room_id", "uuid", ""), ("data", "jsonb", ""), ("created_at", "timestamptz", "")]),
]


def diagrama_datos(m):
    ruta = "Diseño de datos"
    tam = {}
    for nombre, cols in TABLAS_DATOS:
        m.elem(nombre, "Class", nombre, ruta, est="table", attrs=[(c, t, est, "Public") for c, t, est in cols])
        tam[nombre] = (260, 40 + 17 * len(cols))
    objetos = [("collab_participant", 320, 120, *tam["collab_participant"]),
               ("collab_activityevent", 0, 0, *tam["collab_activityevent"]),
               ("collab_chatmessage", 680, 0, *tam["collab_chatmessage"]),
               ("collab_iaattempt", 680, 260, *tam["collab_iaattempt"]),
               ("uml_api_backupuml", 0, 330, *tam["uml_api_backupuml"])]
    conectores = [dict(de=n, a="collab_participant", tipo="Association", cd="0..*", ca="1", dir="Source -> Destination")
                  for n in ("collab_activityevent", "collab_chatmessage", "collab_iaattempt")]
    m.diagrama("datos", "Modelo de datos", "Class", ruta, objetos, conectores)


# ---- implementación ----------------------------------------------------------------------------------
def diagrama_componentes(m):
    ruta = "Diagrama de componentes"
    cliente = [("cm:ED", "Editor de diagrama"), ("cm:SC", "Servicios de colaboración"), ("cm:SI", "Servicios de IA y chat"),
               ("cm:SE", "Exportaciones e importaciones")]
    servidor = [("cm:RW", "collab: relé de WebSocket"), ("cm:AI", "collab: actividad e identidad"), ("cm:CH", "uml_api: chat con la IA"),
                ("cm:PR", "uml_api: proveedores de IA"), ("cm:XF", "uml_api: XMI y generador Flutter")]
    m.elem("cm:PKC", "Package", "Cliente (navegador)", ruta)
    m.elem("cm:PKS", "Package", "Servidor Django", ruta)
    objetos = [("cm:PKC", 0, 0, 260, 330), ("cm:PKS", 420, 0, 280, 400)]
    for i, (k, n) in enumerate(cliente):
        m.elem(k, "Component", n, ruta)
        objetos.append((k, 25, 50 + i * 70, 210, 45))
    for i, (k, n) in enumerate(servidor):
        m.elem(k, "Component", n, ruta)
        objetos.append((k, 450, 50 + i * 70, 220, 45))
    for k, n, est in (("cm:GS", "Generador Spring Boot", ""), ("cm:PG", "PostgreSQL", "database"), ("cm:RE", "Redis", "database"),
                      ("cm:GE", "Gemini", ""), ("cm:OL", "Ollama (modelo reentrenado)", "")):
        m.elem(k, "Component", n, ruta, est=est)
    objetos += [("cm:GS", 20, 400, 200, 45), ("cm:PG", 880, 130, 160, 45), ("cm:RE", 880, 30, 160, 45),
                ("cm:GE", 880, 250, 160, 45), ("cm:OL", 880, 340, 200, 45)]
    conectores = [dict(de="cm:ED", a="cm:SC", tipo="Dependency"),
                  dict(de="cm:SC", a="cm:RW", tipo="Dependency", nombre="WebSocket"),
                  dict(de="cm:SI", a="cm:CH", tipo="Dependency", nombre="REST"),
                  dict(de="cm:SE", a="cm:XF", tipo="Dependency", nombre="REST"),
                  dict(de="cm:SE", a="cm:GS", tipo="Dependency", nombre="HTTPS"),
                  dict(de="cm:RW", a="cm:AI", tipo="Dependency"), dict(de="cm:RW", a="cm:RE", tipo="Dependency"),
                  dict(de="cm:AI", a="cm:PG", tipo="Dependency"), dict(de="cm:CH", a="cm:PR", tipo="Dependency"),
                  dict(de="cm:CH", a="cm:PG", tipo="Dependency"), dict(de="cm:PR", a="cm:GE", tipo="Dependency"),
                  dict(de="cm:PR", a="cm:OL", tipo="Dependency")]
    m.diagrama("componentes", "Diagrama de componentes", "Component", ruta, objetos, conectores)


def diagrama_subsistemas(m):
    ruta = "Diagrama de subsistemas"
    subs = [("ss:S1", "Subsistema de edición", [("ss:ed1", "Editor de diagrama"), ("ss:ed2", "Reglas del editor (entidad intermedia)")]),
            ("ss:S2", "Subsistema de colaboración", [("ss:co1", "Relé de operaciones"), ("ss:co2", "Roles y presencia"), ("ss:co3", "Respaldo del diagrama")]),
            ("ss:S3", "Subsistema de actividad", [("ss:ac1", "Registro de actividad"), ("ss:ac2", "Identidad de participantes"), ("ss:ac3", "Vista móvil de seguimiento")]),
            ("ss:S4", "Subsistema de asistencia por IA", [("ss:ia1", "Chat privado"), ("ss:ia2", "Guardia de cambios"), ("ss:ia3", "Proveedores de IA"), ("ss:ia4", "Modelo reentrenado")]),
            ("ss:S5", "Subsistema de interoperabilidad y generación", [("ss:in1", "XMI (Enterprise Architect)"), ("ss:in2", "Generador Spring Boot"), ("ss:in3", "Generador Flutter")])]
    dependencias = [("ss:S2", "ss:S1"), ("ss:S2", "ss:S3"), ("ss:S4", "ss:S1"), ("ss:S4", "ss:S2"), ("ss:S4", "ss:S3"), ("ss:S5", "ss:S1")]
    tamanos = {k: (290, 60 + 55 * len(comps)) for k, _, comps in subs}
    posiciones, _ = layout.dot(tamanos, dependencias, "TB", 70, 90)
    objetos = []
    for k, titulo, comps in subs:
        m.elem(k, "Package", titulo, ruta, est="subsistema")
        x, y = posiciones[k]
        objetos.append((k, x, y, *tamanos[k]))
        for j, (ck, cn) in enumerate(comps):
            m.elem(ck, "Component", cn, ruta)
            objetos.append((ck, x + 20, y + 50 + j * 55, 250, 42))
    conectores = [dict(de=o, a=d, tipo="Dependency") for o, d in dependencias]
    m.diagrama("subsistemas", "Diagrama de subsistemas", "Package", ruta, objetos, conectores)


def diagrama_flujo_despliegue(m):
    """Flujo de tráfico del Anexo C (docs/DESPLIEGUE.md)."""
    ruta = "Anexo C|Flujo de despliegue"
    m.elem("fl:U", "Actor", "Usuarios", ruta)
    m.elem("fl:N", "Node", "nginx + Let's Encrypt", ruta, est="execution environment")
    m.elem("fl:F", "Component", "angular-app :4200", ruta)
    m.elem("fl:D", "Component", "django :8000", ruta)
    m.elem("fl:S", "Component", "spring-backend :7001", ruta)
    m.elem("fl:R", "Component", "redis", ruta, est="database")
    m.elem("fl:P", "Component", "postgres", ruta, est="database")
    m.elem("fl:T", "Component", "Quick Tunnel de Cloudflare\n(respaldo, nginx :8080)", ruta)
    nodos = {"fl:U": (90, 110), "fl:N": (200, 90), "fl:F": (190, 60), "fl:D": (170, 60), "fl:S": (200, 60),
             "fl:R": (150, 60), "fl:P": (150, 60), "fl:T": (230, 80)}
    aristas = [("fl:U", "fl:N"), ("fl:N", "fl:F"), ("fl:N", "fl:D"), ("fl:N", "fl:S"), ("fl:D", "fl:R"), ("fl:D", "fl:P"), ("fl:T", "fl:N")]
    pos, _ = layout.dot(nodos, aristas, "LR", 40, 110)
    conectores = [dict(de="fl:U", a="fl:N", nombre="HTTPS 443"), dict(de="fl:N", a="fl:F", nombre="/"),
                  dict(de="fl:N", a="fl:D", nombre="/api  /ws"), dict(de="fl:N", a="fl:S", nombre="/generate"),
                  dict(de="fl:D", a="fl:R"), dict(de="fl:D", a="fl:P"),
                  dict(de="fl:T", a="fl:N", tipo="Dependency")]
    m.diagrama("despliegue-flujo", "Flujo de tráfico del despliegue", "Deployment", ruta,
               [(k, *pos[k], *nodos[k]) for k in nodos], conectores)


# ---- C4 ----------------------------------------------------------------------------------------------
# EA no trae una tecnología C4: se usan elementos UML (actor, componente, límite) con los colores del modelo C4.
C4_COLORES = {
    "persona": dict(fondo="#08427B", texto="#000000", borde="#073B6F"),
    "sistema": dict(fondo="#1168BD", texto="#FFFFFF", borde="#0B4884"),
    "externo": dict(fondo="#999999", texto="#FFFFFF", borde="#6B6B6B"),
    "contenedor": dict(fondo="#438DD5", texto="#FFFFFF", borde="#3C7FC0"),
    "componente": dict(fondo="#85BBF0", texto="#000000", borde="#78A8D8"),
}


def _c4(m, clave, rol, nombre, tipo, descripcion, ruta, tecnologia=""):
    """Elemento C4 con el texto en tres líneas: nombre, [tipo: tecnología] y descripción."""
    corchete = f"[{tipo}: {tecnologia}]" if tecnologia else f"[{tipo}]"
    texto = f"{nombre}\n{corchete}\n\n{descripcion}" if descripcion else f"{nombre}\n{corchete}"
    if rol == "persona":
        m.elem(clave, "Actor", texto, ruta)
    else:
        m.elem(clave, "Component", texto, ruta, est="database" if tipo.startswith("Base de datos") else "")
    return clave


def _caja(clave, rol, x, y, w=240, h=130):
    return (clave, x, y, w, h, C4_COLORES[rol])


def _rel(de, a, texto, tecnologia=""):
    nombre = f"{texto}\n[{tecnologia}]" if tecnologia else texto
    return dict(de=de, a=a, tipo="Association", nombre=nombre, dir="Source -> Destination")


def diagrama_c4_contexto(m):
    ruta = "Diseño C4|Contexto"
    p1 = _c4(m, "c4c:participante", "persona", "Participante", "Persona", "Diseña diagramas de clases UML en equipo", ruta)
    p2 = _c4(m, "c4c:observador", "persona", "Observador", "Persona", "Sigue la sala desde el celular, en solo lectura", ruta)
    s = _c4(m, "c4c:sistema", "sistema", "Plataforma CASE colaborativa", "Sistema de software",
            "Modelado UML 2.5, IA como integrante de la sala, generación de código", ruta)
    g = _c4(m, "c4c:gemini", "externo", "Google Gemini", "Sistema externo", "IA en la nube", ruta)
    o = _c4(m, "c4c:ollama", "externo", "Ollama + modelo reentrenado", "Sistema externo", "IA local, sin internet", ruta)
    ea = _c4(m, "c4c:ea", "externo", "Enterprise Architect", "Sistema externo", "Herramienta CASE (intercambio XMI)", ruta)
    objetos = [_caja(p1, "persona", 0, 0, 200, 150), _caja(p2, "persona", 0, 260, 200, 150),
               _caja(s, "sistema", 420, 130, 280, 150),
               _caja(g, "externo", 920, 0, 250, 120), _caja(o, "externo", 920, 190, 250, 120), _caja(ea, "externo", 920, 380, 250, 120)]
    conectores = [_rel(p1, s, "Edita y conversa con la IA", "HTTPS / WebSocket"), _rel(p2, s, "Sigue en vivo", "HTTPS"),
                  _rel(s, g, "Pide respuestas", "HTTPS"), _rel(s, o, "Pide respuestas (opcional)", "HTTP"),
                  _rel(s, ea, "Importa y exporta modelos", "XMI")]
    m.diagrama("c4-contexto", "Diagrama de contexto del sistema", "Component", ruta, objetos, conectores, enlaces="paralelos")


def diagrama_c4_contenedores(m):
    ruta = "Diseño C4|Contenedores"
    p = _c4(m, "c4k:p", "persona", "Participante", "Persona", "Edita el diagrama", ruta)
    m.elem("c4k:limite", "Boundary", "Plataforma CASE colaborativa", ruta)
    web = _c4(m, "c4k:web", "contenedor", "Aplicación web", "Contenedor", "Editor, chat con la IA, actividad, vista móvil", ruta, "Angular 20 (SSR) + JointJS")
    api = _c4(m, "c4k:api", "contenedor", "API y tiempo real", "Contenedor", "REST, WebSocket, actividad, proveedores de IA, XMI, generador Flutter", ruta, "Django 5 + Channels + Daphne")
    gen = _c4(m, "c4k:gen", "contenedor", "Generador de backend", "Contenedor", "Proyecto Spring + PostgreSQL y colección Postman", ruta, "Spring Boot 3.5 (Java 21)")
    pg = _c4(m, "c4k:pg", "contenedor", "Base de datos", "Base de datos", "Respaldo, participantes, actividad y chats", ruta, "PostgreSQL 17")
    rd = _c4(m, "c4k:redis", "contenedor", "Estado de salas", "Base de datos", "Capa de canales y orden de conexión (host)", ruta, "Redis 7")
    g = _c4(m, "c4k:gemini", "externo", "Google Gemini", "Sistema externo", "IA en la nube", ruta)
    o = _c4(m, "c4k:ollama", "externo", "Ollama", "Sistema externo", "IA local con modelo reentrenado", ruta)
    objetos = [_caja(p, "persona", 100, 0, 200, 150),
               ("c4k:limite", 0, 190, 1080, 600),
               _caja(web, "contenedor", 40, 280, 270, 150), _caja(api, "contenedor", 440, 280, 300, 160),
               _caja(gen, "contenedor", 40, 570, 270, 150),
               _caja(pg, "contenedor", 440, 600, 250, 150), _caja(rd, "contenedor", 770, 600, 250, 150),
               _caja(g, "externo", 1200, 250, 250, 120), _caja(o, "externo", 1200, 440, 250, 120)]
    conectores = [_rel(p, web, "Usa", "HTTPS"), _rel(web, api, "Edición y chat", "REST + WebSocket"),
                  _rel(web, gen, "Genera backend", "HTTPS"), _rel(api, pg, "Lee y escribe", "SQL"),
                  _rel(api, rd, "Presencia y roles", "RESP"), _rel(api, g, "Pide respuestas", "HTTPS"),
                  _rel(api, o, "Pide respuestas (opcional)", "HTTP")]
    m.diagrama("c4-contenedores", "Diagrama de contenedor", "Component", ruta, objetos, conectores, enlaces="paralelos")


def diagrama_c4_componentes(m):
    ruta = "Diseño C4|Componentes"
    web = _c4(m, "c4m:web", "contenedor", "Aplicación web", "Contenedor", "Editor y paneles", ruta, "Angular")
    pg = _c4(m, "c4m:pg", "contenedor", "PostgreSQL", "Base de datos", "", ruta)
    rd = _c4(m, "c4m:redis", "contenedor", "Redis", "Base de datos", "", ruta)
    prov = _c4(m, "c4m:prov", "externo", "Gemini / Ollama", "Sistema externo", "Proveedores de IA", ruta)
    m.elem("c4m:limite", "Boundary", "API y tiempo real (Django)", ruta)
    canvas = _c4(m, "c4m:canvas", "componente", "CanvasConsumer", "Componente", "Relé de operaciones, presencia, roles y observadores", ruta, "Channels")
    act = _c4(m, "c4m:act", "componente", "Actividad e identidad", "Componente", "Registra quién hizo qué y valida el nombre", ruta, "collab")
    chat = _c4(m, "c4m:chat", "componente", "Chat con la IA", "Componente", "Preguntar, pedir cambio y revisar; topes de uso; reserva de ideas", ruta, "DRF")
    guard = _c4(m, "c4m:guard", "componente", "Guardia de cambios", "Componente", "Valida tamaño y cuenta lo que se eliminaría", ruta, "uml_api")
    provider = _c4(m, "c4m:provider", "componente", "Proveedores de IA", "Componente", "Interfaz con Gemini y Ollama (modelo reentrenado)", ruta, "uml_api")
    xmi = _c4(m, "c4m:xmi", "componente", "XMI y generador Flutter", "Componente", "Intercambio con Enterprise Architect y proyecto móvil", ruta, "uml_api")
    objetos = [("c4m:limite", 0, 0, 1000, 470),
               _caja(web, "contenedor", 330, -250, 270, 150),
               _caja(canvas, "componente", 30, 50, 290, 150), _caja(chat, "componente", 350, 50, 290, 150), _caja(xmi, "componente", 670, 50, 290, 150),
               _caja(act, "componente", 30, 290, 290, 140), _caja(guard, "componente", 350, 290, 290, 140), _caja(provider, "componente", 670, 290, 290, 140),
               _caja(rd, "contenedor", -330, 70, 230, 110), _caja(pg, "contenedor", -330, 310, 230, 110),
               _caja(prov, "externo", 1120, 310, 230, 110)]
    conectores = [_rel(web, canvas, "Operaciones", "WebSocket"), _rel(web, chat, "Pedidos", "REST"),
                  _rel(web, xmi, "Importa y exporta", "REST"), _rel(canvas, act, "Registra"),
                  _rel(canvas, rd, "Roles"), _rel(act, pg, "Guarda"), _rel(chat, guard, "Valida"),
                  _rel(chat, provider, "Pide"), _rel(provider, prov, "Pide respuestas", "HTTP"),
                  _rel(chat, pg, "Guarda chats")]
    m.diagrama("c4-componentes", "Diagrama de componentes (C4)", "Component", ruta, objetos, conectores, enlaces="paralelos")


# ---- conjunto ----------------------------------------------------------------------------------------
def construir():
    m = Modelo()
    for _, _, _, codigos in CICLOS:
        for cu in codigos:
            diagrama_casos_uso(m, f"uc-{cu.replace('-', '')}", nombre_cu(cu), [cu])
    acumulado = []
    for numero, _, _, codigos in CICLOS:
        acumulado += codigos
        diagrama_casos_uso(m, f"uc-ciclo-{numero}", f"Casos de uso del ciclo {numero}", codigos)
    diagrama_casos_uso(m, "uc-ciclo-todo", "Modelo de casos de uso completo", acumulado)
    diagrama_paquetes_identificados(m)
    diagrama_paquetes_y_cu(m)
    for i in range(len(PAQUETES)):
        diagrama_vista_paquete(m, i)
    diagrama_dependencias_paquetes(m)
    for _, _, _, codigos in CICLOS:
        for cu in codigos:
            diagrama_comunicacion(m, cu)
    for numero, _, _, codigos in CICLOS:
        diagrama_clases_analisis(m, numero, codigos)
    diagrama_codigo(m)
    diagrama_despliegue(m)
    diagrama_capas(m)
    diagrama_datos(m)
    for _, _, _, codigos in CICLOS:
        for cu in codigos:
            diagrama_secuencia(m, cu)
    diagrama_componentes(m)
    diagrama_subsistemas(m)
    diagrama_c4_contexto(m)
    diagrama_c4_contenedores(m)
    diagrama_c4_componentes(m)
    diagrama_flujo_despliegue(m)
    return dict(elementos=m.elementos, diagramas=m.diagramas)


if __name__ == "__main__":
    modelo = construir()
    print(len(modelo["diagramas"]), "diagramas;", len(modelo["elementos"]), "elementos")
