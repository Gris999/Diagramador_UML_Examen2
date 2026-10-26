"""Diagramas del flujo de diseño (PUDS, capítulo 9) para Enterprise Architect, a partir de `modelo/diseno.py` y `modelo/realizaciones.py`.

  di-despliegue, di-capas, di-subsistemas, di-interfaces      arquitectura: nodos, capas, subsistemas e interfaces entre ellos
  di-c4-contenedores, di-c4-componentes                       los niveles 2 y 3 del modelo C4 (el de contexto no cambia)
  dc-<subsistema>                                             clases de diseño de cada subsistema, con los atributos y las operaciones del código
  dp-<COL>                                                    clases de diseño participantes de una realización
  sq-<COL>-<escenario>                                        diagrama de secuencia de un escenario (operaciones reales del código)
  dd-postgres, dd-mongo                                       diseño de datos

Las clases y operaciones se leen del código (`modelo/codigo.py`): lo que se dibuja es lo que existe, salvo lo que los cambios C1 a C4 agregan (amarillo).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout  # noqa: E402
from especificaciones import _c4, _caja, _rel, diagrama_c4_contexto, tam_actor  # noqa: E402
from modelo import analisis as A  # noqa: E402
from modelo import codigo as C  # noqa: E402
from modelo import diseno as D  # noqa: E402
from modelo import realizaciones as R  # noqa: E402

MODELO = "Modelo de diseño"
NUEVO = dict(fondo="#FFF2CC", borde="#BF9000", texto="#000000")
CAPAS_ORDEN = ["carcasa", "gestion", "actividad", "seguimiento", "ia", "ayuda", "intercambio", "edicion", "nucleo"]
EST_EA = {"entity": "model", "active": "active", "module": "module", "interface": "interface", None: ""}


def _estereotipo(o):
    return EST_EA.get(o["est"], o["est"] or "")


def _operaciones_usadas(clave):
    """Operaciones de la clase que aparecen en alguna realización, en orden de aparición, con los argumentos del primer mensaje."""
    vistas = {}
    for r in R.REALIZACIONES:
        for e in r["escenarios"]:
            for _, destino, op, args in e["mensajes"]:
                if destino.split("#")[0] == clave and not op.startswith("·") and op not in vistas:
                    vistas[op] = args
    return vistas


def _etiqueta_op(op, args):
    return f"{op}({args})"


def _tam_clase(lineas, titulo):
    ancho = max(170, int(6.6 * max([len(titulo) + 6] + [len(x) + 4 for x in lineas])))
    return ancho, 56 + 16 * max(1, len(lineas))


def _actores(col_id):
    col = next(c for c in A.COLABORACIONES if c["id"] == col_id)
    return col["actores"]


# ---- secuencias ---------------------------------------------------------------------------------------------
def _rotulo_vida(vida, col_id):
    base = vida.split("#")[0]
    if base in D.ACTORES_SECUENCIA:
        actor = _actores(col_id).get(base)
        if actor:
            return actor[1]
        return "Diseñador" if base == "D" else "Colaborador"
    return D.OBJETOS[base]["rotulo"] + (" (otra pantalla)" if "#" in vida else "")


def diagrama_secuencia(m, r, e):
    ruta = f"{MODELO}|Realizaciones del diseño|{r['col']}"
    prefijo = f"sq:{r['col']}-{e['id']}"
    vidas = []
    for origen, destino, _, _ in e["mensajes"]:
        for v in (origen, destino):
            if v not in vidas:
                vidas.append(v)
    claves, tam = {}, {}
    for v in vidas:
        clave = f"{prefijo}:{v}"
        rotulo = _rotulo_vida(v, r["col"])
        if v.split("#")[0] in D.ACTORES_SECUENCIA:
            m.elem(clave, "Actor", rotulo, ruta)
            tam[v] = (tam_actor(rotulo)[0], 90)
        else:
            obj = D.OBJETOS[v.split("#")[0]]
            m.elem(clave, "Class", rotulo, ruta, est=_estereotipo(obj))
            tam[v] = (max(120, int(7.4 * len(rotulo)) + 24), 44)
        claves[v] = clave
    indice = {v: i for i, v in enumerate(vidas)}
    tramos = [max(tam[vidas[i]][0] / 2 + tam[vidas[i + 1]][0] / 2 + 30, 150) for i in range(len(vidas) - 1)]
    mensajes = []
    for numero, (origen, destino, op, args) in enumerate(e["mensajes"], 1):
        texto = f"{numero}: {op.lstrip('·')}({args})" if args or not op.startswith("·") else f"{numero}: {op.lstrip('·')}"
        mensajes.append((origen, destino, texto))
        a, b = sorted((indice[origen], indice[destino]))
        if a != b:
            necesario = int(6.4 * len(texto)) + 40
            actual = sum(tramos[a:b])
            if actual < necesario:
                for k in range(a, b):
                    tramos[k] += (necesario - actual) / (b - a)
    xs, x = [0], 0
    for tramo in tramos:
        x += tramo
        xs.append(x)
    objetos = []
    for v in vidas:
        w, h = tam[v]
        objetos.append((claves[v], int(xs[indice[v]] - w / 2), 0, w, h))
    conectores = [dict(de=claves[o], a=claves[d], tipo="Sequence", nombre=t, seq=n) for n, (o, d, t) in enumerate(mensajes, 1)]
    m.diagrama(f"sq-{r['col']}-{e['id']}", f"{r['col']} ({e['id']}): {e['nombre']}", "Sequence", ruta, objetos, conectores)


# ---- clases de diseño ------------------------------------------------------------------------------------------
def _elemento_clase(m, clave_el, clave_obj, ruta, con_atributos, ops=None):
    """Clase de diseño en EA con los atributos (tipos del código) y las operaciones (con los parámetros reales)."""
    o = D.OBJETOS[clave_obj]
    c = C.buscar(o["archivo"], o["clase"]) if not o["nuevo"] else None
    atributos = []
    if con_atributos and c:
        orden = sorted(c["atributos"].items(), key=lambda kv: {"public": 0, "protected": 1, "private": 2}.get(kv[1]["vis"], 3))
        atributos = [(n, a["tipo"] or "", "", a["vis"].capitalize()) for n, a in orden[:7]]
    usadas = list(ops) if ops is not None else list(_operaciones_usadas(clave_obj))
    if ops is None:  # una clase que realiza una interfaz muestra las operaciones de la interfaz
        usadas += [op for i in D.INTERFACES if clave_obj in i["realiza"] for op in i["operaciones"] if op not in usadas]
    usadas += [x for x in R.OPERACIONES_NUEVAS.get(clave_obj, []) if x not in usadas]
    metodos, lineas = [], [f"{n}: {t}" for n, t, _, _ in atributos]
    for op in usadas:
        real = c["metodos"].get(op) if c else None
        args = real["args"] if real else []
        vis = (real["vis"] if real else "public").capitalize()
        metodos.append((op, "", vis, ";".join(f"{x}:{x}" for x in args)))
        lineas.append(f"{op}({', '.join(args)})")
    m.elem(clave_el, "Class", o["rotulo"], ruta, est=_estereotipo(o), attrs=atributos, meths=metodos)
    return _tam_clase(lineas, o["rotulo"]), o["nuevo"]


def _conector_asoc(origen, destino, etiqueta, prefijo, columna):
    tipo = {"hereda de": "Generalization", "realiza": "Realization"}.get(etiqueta, "Dependency")
    return dict(de=f"{prefijo}:{origen}", a=f"{prefijo}:{destino}", tipo=tipo, arbol="V" if columna.get(origen) == columna.get(destino) else "H")


def diagrama_clases_subsistema(m, sub):
    s = next(x for x in D.SUBSISTEMAS if x["id"] == sub)
    ruta = f"{MODELO}|Subsistemas|{s['nombre']}"
    claves = [o["clave"] for o in D.objetos_de(sub)]
    prefijo = f"dc:{sub}"
    tam, nuevos = {}, {}
    for k in claves:
        tam[k], nuevos[k] = _elemento_clase(m, f"{prefijo}:{k}", k, ruta, con_atributos=True)
    # interfaces que proporciona el subsistema y que no son una clase de diseño
    interfaces = [i for i in D.INTERFACES if i["sub"] == sub and i["nombre"] not in D.OBJETOS]
    for i in interfaces:
        el = f"{prefijo}:I:{i['nombre']}"
        m.elem(el, "Interface", i["nombre"], ruta, meths=[(op, "", "Public", "") for op in i["operaciones"]])
        tam[f"I:{i['nombre']}"] = _tam_clase([f"{op}()" for op in i["operaciones"]], i["nombre"])
        nuevos[f"I:{i['nombre']}"] = bool(i.get("nuevo"))
    todas = list(tam)
    asoc = [(a, b, e) for a, b, e, *_ in D.ASOCIACIONES if a in claves and b in claves]
    asoc += [(k, f"I:{i['nombre']}", "realiza") for i in interfaces for k in i["realiza"] if k in claves]
    # columnas: las clases de interfaz de la interfaz a la derecha; el resto en columnas de cuatro
    interior = [k for k in todas if k in claves]
    cols = [interior[i:i + 4] for i in range(0, len(interior), 4)] + ([[k for k in todas if k.startswith("I:")]] if interfaces else [])
    cols = [c for c in cols if c]
    columna = {k: i for i, c in enumerate(cols) for k in c}
    pos = layout.columnas(tam, cols, [(a, b) for a, b, _ in asoc], hueco_x=110, hueco_y=30, pares_juntos=(), arbol=True)
    x0 = min(pos[k][0] for k in todas) - 30
    y0 = min(pos[k][1] for k in todas) - 55
    x1 = max(pos[k][0] + tam[k][0] for k in todas) + 30
    y1 = max(pos[k][1] + tam[k][1] for k in todas) + 25
    caja = m.elem(f"{prefijo}:caja", "Package", s["nombre"], ruta, est="design subsystem")
    objetos = [(caja, x0, y0, x1 - x0, y1 - y0)]
    objetos += [(f"{prefijo}:{k}", *pos[k], *tam[k], *((NUEVO,) if nuevos[k] else ())) for k in todas]
    conectores = [_conector_asoc(a, b, e, prefijo, columna) for a, b, e in asoc]
    m.diagrama(f"dc-{sub}", f"Clases de diseño del subsistema {s['nombre']}", "Class", ruta, objetos, conectores)


def diagrama_clases_participantes(m, r):
    ruta = f"{MODELO}|Realizaciones del diseño|{r['col']}"
    prefijo = f"dp:{r['col']}"
    claves = []
    for e in r["escenarios"]:
        for origen, destino, _, _ in e["mensajes"]:
            for v in (origen, destino):
                b = v.split("#")[0]
                if b in D.OBJETOS and b not in claves:
                    claves.append(b)
    ops = {k: {} for k in claves}
    for e in r["escenarios"]:
        for _, destino, op, args in e["mensajes"]:
            b = destino.split("#")[0]
            if b in ops and not op.startswith("·"):
                ops[b].setdefault(op, args)
    tam, nuevos = {}, {}
    for k in claves:
        tam[k], nuevos[k] = _elemento_clase(m, f"{prefijo}:{k}", k, ruta, con_atributos=False, ops=ops[k])
    asoc = [(a, b, e) for a, b, e, *_ in D.ASOCIACIONES if a in claves and b in claves]
    orden = [s for s in CAPAS_ORDEN if any(D.OBJETOS[k]["sub"] == s for k in claves)]
    cols = [[k for k in claves if D.OBJETOS[k]["sub"] == s] for s in orden]
    # una columna con más de cuatro clases se parte
    partidas = []
    for c in cols:
        partidas += [c[i:i + 4] for i in range(0, len(c), 4)]
    columna = {k: i for i, c in enumerate(partidas) for k in c}
    pos = layout.columnas(tam, partidas, [(a, b) for a, b, _ in asoc], hueco_x=120, hueco_y=30, pares_juntos=(), arbol=True)
    objetos = [(f"{prefijo}:{k}", *pos[k], *tam[k], *((NUEVO,) if nuevos[k] else ())) for k in claves]
    conectores = [_conector_asoc(a, b, e, prefijo, columna) for a, b, e in asoc]
    m.diagrama(f"dp-{r['col']}", f"{r['col']}: clases de diseño participantes", "Class", ruta, objetos, conectores)


# ---- arquitectura -----------------------------------------------------------------------------------------------
def diagrama_capas(m):
    ruta = f"{MODELO}|Arquitectura"
    filas = [
        ("Capa específica de la aplicación", [(s["id"], s["nombre"] + (" (servicio)" if s["servicio"] else "")) for s in D.SUBSISTEMAS if s["capa"] == "específica"],
         "design subsystem"),
        ("Capa general de la aplicación", [(s["id"], s["nombre"]) for s in D.SUBSISTEMAS if s["capa"] == "general"], "design subsystem"),
        ("Capa intermedia", [(f"mw{i}", n) for i, (n, c, *_) in enumerate(D.SOFTWARE_DEL_SISTEMA) if c == "intermedia"], "middleware"),
        ("Capa de software del sistema", [(f"sw{i}", n) for i, (n, c, *_) in enumerate(D.SOFTWARE_DEL_SISTEMA) if c == "sistema"], "system software"),
    ]
    objetos, y = [], 0
    ancho_col, paso = 220, 240
    ancho_total = 40 + 6 * paso
    for t, (titulo, items, est) in enumerate(filas):
        m.elem(f"cp:C{t}", "Package", titulo, ruta)
        columnas_fila = 6
        filas_alto = (len(items) + columnas_fila - 1) // columnas_fila
        alto = 70 + filas_alto * 80
        objetos.append((f"cp:C{t}", 0, y, ancho_total, alto))
        for j, (k, nombre) in enumerate(items):
            m.elem(f"cp:{k}", "Component", nombre, ruta, est=est)
            objetos.append((f"cp:{k}", 20 + (j % columnas_fila) * paso, y + 50 + (j // columnas_fila) * 80, ancho_col, 60))
        y += alto + 40
    m.diagrama("di-capas", "Diseño en capas", "Package", ruta, objetos, [])


def diagrama_subsistemas(m):
    """Subsistemas de la capa específica y de la general con sus dependencias (las del análisis sin las implícitas por otra ruta); los de servicio van dentro del
    que los contiene y la carcasa del editor, que los compone a todos, va arriba como una banda."""
    ruta = f"{MODELO}|Arquitectura"
    raices = [s["id"] for s in D.SUBSISTEMAS if s["id"] != "carcasa" and not s["servicio"]]
    servicios = {s["id"]: next(p["padre"] for p in A.PAQUETES if p["id"] == s["traza"]) for s in D.SUBSISTEMAS if s["servicio"]}
    reducidas = A.dependencias_reducidas()
    hijos = {r: [k for k, v in servicios.items() if v == r] for r in raices}
    claves = {r: m.elem(f"ds:{r}", "Package", D.NOMBRE_SUBSISTEMA[r], ruta, est="design subsystem") for r in raices}
    tam = {r: (270, 90 + 80 * len(hijos[r])) for r in raices}
    profundidad = {}

    def prof(i):
        if i not in profundidad:
            profundidad[i] = 1 + max([prof(b) for a, b in reducidas if a == i] + [-1])
        return profundidad[i]

    for r in raices:
        prof(r)
    cols = [c for c in ([r for r in raices if profundidad[r] == n] for n in range(max(profundidad.values()) + 1)) if c]
    pos = layout.columnas(tam, cols, reducidas, hueco_x=150, hueco_y=50, pares_juntos=(), arbol=True)
    objetos = []
    for r in raices:
        objetos.append((claves[r], *pos[r], *tam[r]))
        for j, k in enumerate(hijos[r]):
            hijo = m.elem(f"ds:{k}", "Package", D.NOMBRE_SUBSISTEMA[k], ruta, est="design service subsystem")
            objetos.append((hijo, pos[r][0] + 15, pos[r][1] + 80 + 80 * j, tam[r][0] - 30, 65))
    x0 = min(pos[r][0] for r in raices)
    x1 = max(pos[r][0] + tam[r][0] for r in raices)
    y0 = min(pos[r][1] for r in raices)
    m.elem("ds:carcasa", "Package", D.NOMBRE_SUBSISTEMA["carcasa"] + " (compone a todos los demás; nadie depende de ella)", ruta, est="design subsystem")
    objetos.insert(0, ("ds:carcasa", x0, y0 - 140, x1 - x0, 90))
    conectores = [dict(de=claves[a], a=claves[b], tipo="Dependency", arbol="H") for a, b in reducidas]
    m.diagrama("di-subsistemas", "Subsistemas del diseño y sus dependencias", "Package", ruta, objetos, conectores)


def diagrama_interfaces(m):
    """Cada interfaz con el subsistema que la proporciona (realización) y los que la usan, según los mensajes de las secuencias."""
    ruta = f"{MODELO}|Arquitectura"
    usuarios = {i["nombre"]: set() for i in D.INTERFACES}
    quien = {}
    for i in D.INTERFACES:
        for k in i["realiza"] + [i["nombre"]]:
            quien[k] = i["nombre"]
    for r in R.REALIZACIONES:
        for e in r["escenarios"]:
            for origen, destino, _, _ in e["mensajes"]:
                bo, bd = origen.split("#")[0], destino.split("#")[0]
                if bd in quien and bo in D.OBJETOS and D.OBJETOS[bo]["sub"] != next(i["sub"] for i in D.INTERFACES if i["nombre"] == quien[bd]):
                    usuarios[quien[bd]].add(D.OBJETOS[bo]["sub"])
    subs = {}
    ids = [s["id"] for s in D.SUBSISTEMAS]
    for s in D.SUBSISTEMAS:
        subs[s["id"]] = m.elem(f"di:{s['id']}", "Package", s["nombre"], ruta, est="design subsystem")
    interfaces = {}
    for i in D.INTERFACES:
        interfaces[i["nombre"]] = m.elem(f"di:I:{i['nombre']}", "Interface", i["nombre"], ruta,
                                         meths=[(op, "", "Public", "") for op in i["operaciones"]])
    aristas, conectores = [], []
    for i in D.INTERFACES:
        aristas.append((i["sub"], i["nombre"]))
        conectores.append(dict(de=subs[i["sub"]], a=interfaces[i["nombre"]], tipo="Realization", arbol="H"))
        for u in sorted(usuarios[i["nombre"]]):
            aristas.append((u, i["nombre"]))
            conectores.append(dict(de=subs[u], a=interfaces[i["nombre"]], tipo="Dependency", arbol="H"))
    usados = [s for s in ids if any(s in (a, b) for a, b in aristas)]
    tam = {s: (230, 60) for s in usados}
    tam.update({i["nombre"]: _tam_clase([f"{op}()" for op in i["operaciones"]], i["nombre"]) for i in D.INTERFACES})
    pos = layout.columnas(tam, [usados, [i["nombre"] for i in D.INTERFACES]], aristas, hueco_x=300, hueco_y=30, pares_juntos=(), arbol=True)
    objetos = [(subs[s], *pos[s], *tam[s]) for s in usados]
    objetos += [(interfaces[i["nombre"]], *pos[i["nombre"]], *tam[i["nombre"]], *((NUEVO,) if i.get("nuevo") else ())) for i in D.INTERFACES]
    m.diagrama("di-interfaces", "Interfaces entre subsistemas", "Class", ruta, objetos, conectores)


def diagrama_despliegue(m):
    ruta = f"{MODELO}|Diseño físico"
    nodo = lambda k, nombre, est, **kw: m.elem(k, "Node", nombre, ruta, est=est, **kw)  # noqa: E731
    art = lambda k, nombre, padre, est="": m.elem(k, "Artifact", nombre, ruta, padre=padre, est=est)  # noqa: E731
    nodo("dp:N", "Navegador del usuario", "device")
    art("dp:A", "Aplicación Angular", "dp:N")
    nodo("dp:M", "Navegador del celular", "device")
    art("dp:V", "Vista de seguimiento", "dp:M")
    nodo("dp:EC2", "AWS EC2 (Ubuntu 24.04, 2 vCPU, 2 GB)", "device")
    nodo("dp:NG", "nginx + Let's Encrypt\n/ hacia Angular\n/api y /ws hacia Django\n/generate hacia Spring", "execution environment", padre="dp:EC2")
    nodo("dp:DK", "Docker Compose", "execution environment", padre="dp:EC2")
    art("dp:FE", "angular_frontend :4000 (publicado 4200)", "dp:DK")
    art("dp:DJ", "django_backend_UML :8000 (Daphne)", "dp:DK")
    art("dp:SP", "spring_backend :7001", "dp:DK")
    art("dp:PG", "postgres_db :5432", "dp:DK", "database")
    art("dp:RD", "redis_server :6379", "dp:DK", "database")
    art("dp:MG", "mongo_db :27017 (C3)", "dp:DK", "database")
    nodo("dp:G", "Google Gemini API (nube, HTTPS)", "")
    nodo("dp:MAC", "Equipo con Apple Silicon", "device")
    art("dp:OL", "Ollama + modelo reentrenado :11434", "dp:MAC")
    objetos = [("dp:N", 0, 160, 150, 100), ("dp:A", 10, 195, 125, 50), ("dp:M", 0, 330, 150, 100), ("dp:V", 10, 365, 125, 50),
               ("dp:EC2", 230, 0, 690, 560), ("dp:NG", 245, 190, 215, 110), ("dp:DK", 480, 30, 420, 510),
               ("dp:DJ", 495, 75, 175, 60), ("dp:FE", 495, 190, 175, 60), ("dp:SP", 495, 305, 175, 60),
               ("dp:PG", 720, 230, 165, 60), ("dp:RD", 720, 330, 165, 60), ("dp:MG", 720, 430, 165, 60),
               ("dp:G", 495, -160, 175, 70), ("dp:MAC", 1010, 20, 190, 130), ("dp:OL", 1020, 60, 165, 70)]
    conectores = [dict(de="dp:N", a="dp:NG", nombre="HTTPS / WSS :443", arbol="H"), dict(de="dp:M", a="dp:NG", nombre="HTTPS / WSS :443", arbol="H"),
                  dict(de="dp:NG", a="dp:FE", arbol="H"), dict(de="dp:NG", a="dp:DJ", arbol="H"), dict(de="dp:NG", a="dp:SP", arbol="H"),
                  dict(de="dp:DJ", a="dp:PG", arbol="H"), dict(de="dp:DJ", a="dp:RD", arbol="H"), dict(de="dp:DJ", a="dp:MG", arbol="H"),
                  dict(de="dp:DJ", a="dp:G", arbol="V"), dict(de="dp:DJ", a="dp:OL", tipo="Dependency", nombre="HTTP (opcional)", arbol="H")]
    m.diagrama("di-despliegue", "Diagrama de despliegue", "Deployment", ruta, objetos, conectores)


def diagrama_c4_contenedores(m):
    ruta = f"{MODELO}|Diseño C4|Contenedores"
    p = _c4(m, "c4k:p", "persona", "Participante", "Persona", "Edita el diagrama y conversa con la IA", ruta)
    m.elem("c4k:limite", "Boundary", "Plataforma CASE colaborativa", ruta)
    web = _c4(m, "c4k:web", "contenedor", "Aplicación web", "Contenedor", "Editor, chat con la IA, actividad, vista móvil, ayuda", ruta, "Angular 20 (SSR) + JointJS")
    api = _c4(m, "c4k:api", "contenedor", "API y tiempo real", "Contenedor", "REST, WebSocket, actividad, conversación, proveedores de IA, XMI, Flutter", ruta,
              "Django 5 + Channels + Daphne")
    gen = _c4(m, "c4k:gen", "contenedor", "Generador de backend", "Contenedor", "Proyecto Spring + PostgreSQL y colección Postman", ruta, "Spring Boot 3.5 (Java 21)")
    pg = _c4(m, "c4k:pg", "contenedor", "Datos relacionales", "Base de datos", "Participantes, topes de uso, respaldo del diagrama", ruta, "PostgreSQL")
    rd = _c4(m, "c4k:redis", "contenedor", "Estado de salas", "Base de datos", "Canales, orden de conexión (host) y turno de la IA", ruta, "Redis 7")
    mg = _c4(m, "c4k:mongo", "contenedor", "Documentos", "Base de datos", "Conversación con la IA y actividad (solo se agregan)", ruta, "MongoDB 7")
    g = _c4(m, "c4k:gemini", "externo", "Google Gemini", "Sistema externo", "IA en la nube", ruta)
    o = _c4(m, "c4k:ollama", "externo", "Ollama", "Sistema externo", "IA local con modelo reentrenado", ruta)
    objetos = [_caja(p, "persona", 75, 0, 200, 150), ("c4k:limite", 0, 190, 1450, 600),
               _caja(web, "contenedor", 40, 280, 270, 150), _caja(api, "contenedor", 530, 280, 300, 160), _caja(gen, "contenedor", 40, 570, 270, 150),
               _caja(pg, "contenedor", 480, 600, 250, 150), _caja(rd, "contenedor", 790, 600, 250, 150), _caja(mg, "contenedor", 1100, 600, 250, 150),
               _caja(g, "externo", 1630, 215, 250, 120), _caja(o, "externo", 1630, 385, 250, 120)]
    from especificaciones import etiqueta_tronco
    centro_api = 360
    conectores = [_rel(p, web, "Usa", "HTTPS") | {"arbol": "V"}, _rel(web, api, "Edición y chat", "REST + WebSocket") | {"arbol": "H"},
                  _rel(web, gen, "Genera backend", "HTTPS") | {"arbol": "V"}, _rel(api, pg, "Lee y escribe", "SQL") | {"arbol": "V"},
                  _rel(api, rd, "Presencia y turno", "RESP") | {"arbol": "V"}, _rel(api, mg, "Conversación y actividad", "MongoDB") | {"arbol": "V"},
                  _rel(api, g, "Pide respuestas", "HTTPS") | {"arbol": "H", "etiq": etiqueta_tronco(275 - centro_api, ["Pide respuestas", "[HTTPS]"])},
                  _rel(api, o, "Pide respuestas (opcional)", "HTTP") | {"arbol": "H", "etiq": etiqueta_tronco(445 - centro_api, ["Pide respuestas (opcional)", "[HTTP]"])}]
    m.diagrama("di-c4-contenedores", "Diagrama de contenedor", "Component", ruta, objetos, conectores)


def diagrama_c4_componentes(m):
    ruta = f"{MODELO}|Diseño C4|Componentes"
    web = _c4(m, "c4m:web", "contenedor", "Aplicación web", "Contenedor", "Editor y paneles", ruta, "Angular")
    pg = _c4(m, "c4m:pg", "contenedor", "PostgreSQL", "Base de datos", "", ruta)
    rd = _c4(m, "c4m:redis", "contenedor", "Redis", "Base de datos", "", ruta)
    mg = _c4(m, "c4m:mongo", "contenedor", "MongoDB", "Base de datos", "", ruta)
    prov = _c4(m, "c4m:prov", "externo", "Gemini / Ollama", "Sistema externo", "Proveedores de IA", ruta)
    m.elem("c4m:limite", "Boundary", "API y tiempo real (Django)", ruta)
    canvas = _c4(m, "c4m:canvas", "componente", "CanvasConsumer", "Componente", "Relé de operaciones, presencia, roles y observadores", ruta, "Channels")
    stores = _c4(m, "c4m:stores", "componente", "Puertos de actividad y conversación", "Componente", "ActivityStore, ConversationStore y TurnStore; adaptadores PostgreSQL, "
                 "MongoDB y Redis", ruta, "collab")
    chat = _c4(m, "c4m:chat", "componente", "Chat con la IA", "Componente", "Preguntar, pedir cambio y revisar; topes de uso; reserva de ideas", ruta, "DRF")
    guard = _c4(m, "c4m:guard", "componente", "Guardia de cambios", "Componente", "Valida tamaño y cuenta lo que se eliminaría", ruta, "uml_api")
    provider = _c4(m, "c4m:provider", "componente", "Proveedores de IA", "Componente", "Puerto AIProvider con Gemini y Ollama", ruta, "uml_api")
    ayuda = _c4(m, "c4m:ayuda", "componente", "Asistente de ayuda", "Componente", "Responde dudas de uso con el manual; tope por persona", ruta, "DRF (C4)")
    xmi = _c4(m, "c4m:xmi", "componente", "XMI y generador Flutter", "Componente", "Intercambio con Enterprise Architect y proyecto móvil", ruta, "uml_api")
    objetos = [("c4m:limite", 0, 0, 1500, 480), _caja(web, "contenedor", 540, -250, 270, 150),
               _caja(canvas, "componente", 30, 50, 290, 150), _caja(chat, "componente", 410, 50, 290, 150), _caja(guard, "componente", 790, 50, 290, 150),
               _caja(xmi, "componente", 1170, 50, 290, 150), _caja(stores, "componente", 30, 290, 290, 140), _caja(provider, "componente", 790, 290, 290, 140),
               _caja(ayuda, "componente", 1170, 290, 290, 140), _caja(rd, "contenedor", -330, 70, 230, 110), _caja(pg, "contenedor", 410, 590, 290, 110),
               _caja(mg, "contenedor", 30, 590, 290, 110), _caja(prov, "externo", 1570, 305, 230, 110)]
    conectores = [_rel(web, canvas, "Operaciones", "WebSocket") | {"arbol": "V"}, _rel(web, chat, "Pedidos", "REST") | {"arbol": "V"},
                  _rel(web, xmi, "Importa y exporta", "REST") | {"arbol": "V"}, _rel(canvas, stores, "Registra") | {"arbol": "V"},
                  _rel(canvas, rd, "Roles") | {"arbol": "H"}, _rel(stores, mg, "Guarda") | {"arbol": "V"}, _rel(chat, guard, "Valida") | {"arbol": "H"},
                  _rel(chat, provider, "Pide") | {"arbol": "H"}, _rel(provider, prov, "Pide respuestas", "HTTP") | {"arbol": "H"},
                  _rel(chat, pg, "Cupos") | {"arbol": "V"}, _rel(ayuda, provider, "Pide") | {"arbol": "V"}]
    m.diagrama("di-c4-componentes", "Diagrama de componentes (C4)", "Component", ruta, objetos, conectores)


# ---- datos ----------------------------------------------------------------------------------------------------------
def diagrama_datos_postgres(m):
    ruta = f"{MODELO}|Diseño de datos"
    tam, nuevos = {}, {}
    for nombre, estado, cols in D.TABLAS:
        m.elem(f"dd:{nombre}", "Class", nombre, ruta, est="table", attrs=[(c, t, "PK" if "PK" in k else "FK" if "FK" in k else "", "Public") for c, t, k in cols])
        tam[nombre] = (270, 40 + 17 * len(cols))
        nuevos[nombre] = estado.startswith("cambia")
    objetos = [("dd:collab_participant", 330, 150, *tam["collab_participant"]), ("dd:collab_activityevent", 0, 0, *tam["collab_activityevent"]),
               ("dd:collab_chatmessage", 690, 0, *tam["collab_chatmessage"], *((NUEVO,) if nuevos["collab_chatmessage"] else ())),
               ("dd:collab_iaattempt", 690, 300, *tam["collab_iaattempt"]), ("dd:uml_api_backupuml", 0, 340, *tam["uml_api_backupuml"])]
    conectores = [dict(de=f"dd:{n}", a="dd:collab_participant", tipo="Association", cd="0..*", ca="1", dir="Source -> Destination", arbol="H")
                  for n in ("collab_activityevent", "collab_chatmessage", "collab_iaattempt")]
    m.diagrama("dd-postgres", "Modelo de datos relacional (PostgreSQL)", "Class", ruta, objetos, conectores)


def diagrama_datos_mongo(m):
    ruta = f"{MODELO}|Diseño de datos"
    tam = {}
    for nombre, cols in D.COLECCIONES:
        m.elem(f"dm:{nombre}", "Class", nombre, ruta, est="collection", attrs=[(c, t, "", "Public") for c, t, _ in cols])
        tam[nombre] = (300, 40 + 17 * len(cols))
    objetos = [("dm:activity_events", 0, 0, *tam["activity_events"], NUEVO), ("dm:conversation_messages", 450, 0, *tam["conversation_messages"], NUEVO),
               ("dm:counters", 450, 300, *tam["counters"], NUEVO)]
    conectores = [dict(de="dm:activity_events", a="dm:counters", tipo="Dependency", nombre="id con $inc", arbol="V"),
                  dict(de="dm:conversation_messages", a="dm:counters", tipo="Dependency", nombre="id con $inc", arbol="V")]
    m.diagrama("dd-mongo", "Colecciones de MongoDB (C3)", "Class", ruta, objetos, conectores)


def construir(m, solo=None):
    """Agrega al modelo los diagramas del diseño. `solo`: identificadores de colaboración para probar; «ARQ» agrega la arquitectura y las clases por subsistema."""
    D.validar(analisis=A)
    D.validar_realizaciones(A)
    if solo is None or "ARQ" in solo:
        diagrama_despliegue(m)
        diagrama_capas(m)
        diagrama_subsistemas(m)
        diagrama_c4_contexto(m)
        diagrama_c4_contenedores(m)
        diagrama_c4_componentes(m)
        diagrama_datos_postgres(m)
        diagrama_datos_mongo(m)
        for s in CAPAS_ORDEN:
            diagrama_clases_subsistema(m, s)
    for r in R.REALIZACIONES:
        if solo is None or r["col"] in solo:
            diagrama_clases_participantes(m, r)
            for e in r["escenarios"]:
                diagrama_secuencia(m, r, e)


if __name__ == "__main__":
    from especificaciones import Modelo

    modelo = Modelo()
    construir(modelo)
    print(len(modelo.diagramas), "diagramas de diseño;", len(modelo.elementos), "elementos")
