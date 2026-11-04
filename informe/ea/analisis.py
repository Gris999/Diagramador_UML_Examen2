"""Diagramas del flujo de análisis (PUDS, capítulo 8) para Enterprise Architect, a partir de `modelo/analisis.py`.

  an-paquetes        paquetes del análisis y los casos de uso que realiza cada uno
  an-dependencias    dependencias entre paquetes, por capas
  an-pkg-<id>        contenido de cada paquete: clases con estereotipo, atributos y asociaciones
  acp-<COL>          clases participantes de una realización de caso de uso (con el actor)
  com-<COL>          diagrama de colaboración de esa realización, con los mensajes numerados

Reglas (PUDS 8.4.3, 8.6.2): el caso de uso empieza con un mensaje de un actor a un objeto de interfaz; los mensajes dicen el propósito de
quien invoca (no son operaciones); los enlaces son instancias de las asociaciones que muestra el diagrama de clases participantes.
Las líneas son horizontales y verticales (estilo de árbol de EA) y no cruzan otros elementos.
"""

import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout  # noqa: E402
from especificaciones import tam_actor, tam_cu  # noqa: E402
from modelo import analisis as A  # noqa: E402
from modelo import requisitos as R  # noqa: E402

MODELO = "Modelo de análisis"
ICONO = (110, 100)  # el ícono de EA sobresale de una caja de 80 de alto: con 100 las líneas entre elementos apilados se ven
ANCHO_ETIQUETA = 30  # caracteres por renglón en las etiquetas de los mensajes
NUEVO = dict(fondo="#FFF2CC", borde="#BF9000", texto="#000000")


def _paquete(id_):
    return next(p for p in A.PAQUETES if p["id"] == id_)


def ruta_paquete(id_):
    p = _paquete(id_)
    return f"{MODELO}|{_paquete(p['padre'])['nombre']}|{p['nombre']}" if p["padre"] else f"{MODELO}|{p['nombre']}"


def _tam_clase(clave):
    c = A.CLASES[clave]
    lineas = [f"{n}: {t}" for n, t in c["atrib"]]
    ancho = max(150, int(6.6 * max([len(c["nombre"]) + 8] + [len(x) + 3 for x in lineas])))
    return ancho, 54 + 16 * max(1, len(lineas))


def _estereotipo(clave, rectangulo=False):
    return A.ESTEREOTIPO[A.CLASES[clave]["est"]] + (" " if rectangulo else "")


def _nuevo(clave):
    return A.CLASES[clave]["estado"].startswith("nuevo")


# ---- paquetes -------------------------------------------------------------------------------------------
def diagrama_paquetes(m):
    """Cada paquete con los casos de uso que realiza; el de servicio dentro de su paquete."""
    ruta = f"{MODELO}|Paquetes del análisis"

    def caja(p):
        casos = p["casos"]
        tam = {cu: tam_cu(f"{cu}: {R.CASOS[cu]['nombre']}") for cu in casos}
        pos, (ancho, alto) = layout.rejilla(tam, 1, 20, 14) if casos else ({}, (0, 0))
        return pos, tam, ancho + 50, alto + 70

    cajas = {}
    for p in [q for q in A.PAQUETES if not q["padre"]]:
        servicios = [q for q in A.PAQUETES if q["padre"] == p["id"]]
        pos, tam, ancho, alto = caja(p)
        hijos = [(q, caja(q)) for q in servicios]
        ancho_total = max([ancho, 260] + [c[2] + 30 for _, c in hijos])
        alto_total = max(alto, 150) + sum(c[3] + 30 for _, c in hijos) + 20
        cajas[p["id"]] = (p, servicios, pos, tam, hijos, ancho_total, alto_total)
    sitios, _ = layout.rejilla({i: (c[5] + 30, c[6]) for i, c in cajas.items()}, 3, 50, 50)
    objetos = []
    for i, (p, servicios, pos, tam, hijos, ancho_total, alto_total) in cajas.items():
        x, y0 = sitios[i]
        clave = m.elem(f"paq:{p['id']}", "Package", p["nombre"], ruta)
        objetos.append((clave, x, y0, ancho_total + 30, alto_total))
        for cu in p["casos"]:
            m.elem(f"paq:{cu}", "UseCase", f"{cu}: {R.CASOS[cu]['nombre']}", ruta)
            objetos.append((f"paq:{cu}", x + 15 + pos[cu][0], y0 + 50 + pos[cu][1], *tam[cu]))
        if not p["casos"]:
            nota = m.elem(f"paq:nota:{p['id']}", "Note", "", ruta,
                          notas="Sala\nParticipante\nEvento de Actividad\n(clases compartidas: no realizan casos de uso)")
            objetos.append((nota, x + 20, y0 + 50, ancho_total - 10, 90))
        y = y0 + 50 + (sum(tam[cu][1] + 14 for cu in p["casos"]) if p["casos"] else 110) + 10
        for q, (qpos, qtam, qancho, qalto) in hijos:
            sc = m.elem(f"paq:{q['id']}", "Package", q["nombre"], ruta, est="service package")
            objetos.append((sc, x + 20, y, ancho_total - 10, qalto))
            for cu in q["casos"]:
                m.elem(f"paq:{cu}", "UseCase", f"{cu}: {R.CASOS[cu]['nombre']}", ruta)
                objetos.append((f"paq:{cu}", x + 35 + qpos[cu][0], y + 50 + qpos[cu][1], *qtam[cu]))
            y += qalto + 30
    m.diagrama("an-paquetes", "Paquetes del análisis y casos de uso que realizan", "Package", ruta, objetos, [], enlaces="ocultar")


def diagrama_dependencias(m):
    """Dependencias entre paquetes sin las que ya están implícitas por otra ruta (reducción transitiva)."""
    ruta = f"{MODELO}|Paquetes del análisis"
    raices = [p["id"] for p in A.PAQUETES if not p["padre"]]
    claves = {i: m.elem(f"dep:{i}", "Package", _paquete(i)["nombre"], ruta) for i in raices}
    tam = {i: (240, 80) for i in raices}
    reducidas = A.dependencias_reducidas()
    # De izquierda a derecha, de lo general a lo específico: quien depende queda a la derecha de aquello de lo que depende.
    profundidad = {}

    def prof(i):
        if i not in profundidad:
            profundidad[i] = 1 + max([prof(b) for a, b in reducidas if a == i] + [-1])
        return profundidad[i]

    for i in raices:
        prof(i)
    cols = [[i for i in raices if profundidad[i] == n] for n in range(max(profundidad.values()) + 1)]
    cols = [c for c in cols if c]
    pos = layout.columnas(tam, cols, reducidas, hueco_x=130, hueco_y=50, pares_juntos=(), arbol=True)
    objetos = [(claves[i], *pos[i], *tam[i]) for i in raices]
    conectores = [dict(de=claves[a], a=claves[b], tipo="Dependency", arbol="H") for a, b in reducidas]
    m.diagrama("an-dependencias", "Dependencias entre los paquetes del análisis", "Package", ruta, objetos, conectores)


# ---- contenido de un paquete ------------------------------------------------------------------------------
def _disponer(claves, hueco_x=60, hueco_y=26, por_columna=4):
    """Clases en columnas por estereotipo (interfaz, control, entidad), apiladas: {clave: (x, y)} y tamaños."""
    tam = {k: _tam_clase(k) for k in claves}
    pos, x = {}, 0
    for est in ("interfaz", "control", "entidad"):
        grupo = [k for k in claves if A.CLASES[k]["est"] == est]
        for i in range(0, len(grupo), por_columna):
            trozo = grupo[i:i + por_columna]
            y = 0
            for k in trozo:
                pos[k] = (x, y)
                y += tam[k][1] + hueco_y
            x += max(tam[k][0] for k in trozo) + hueco_x
    return pos, tam


def _conectores_asociaciones(m, prefijo, claves, columna):
    """Asociaciones entre `claves` con su multiplicidad (sin nombre: los nombres están en las tablas de la sección) y las flechas de
    composición y agregación; una línea vertical entre elementos de la misma columna."""
    conectores = []
    for a, b, nombre, ma, mb, tipo in A.RELACIONES:
        if a in claves and b in claves:
            conectores.append(dict(de=f"{prefijo}:{a}", a=f"{prefijo}:{b}", tipo="Association", cd=ma, ca=mb,
                                   arbol="V" if columna[a] == columna[b] else "H", agr={"comp": 2, "agr": 1}.get(tipo, 0)))
    return conectores


def diagrama_paquete(m, id_):
    p = _paquete(id_)
    ruta = ruta_paquete(id_)
    servicios = [q for q in A.PAQUETES if q["padre"] == id_]
    principal = [c["clave"] for c in A.clases_de_paquete(id_)]
    pos, tam = _disponer(principal)
    bx0 = min(pos[k][0] for k in principal) - 30
    by0 = min(pos[k][1] for k in principal) - 55
    bx1 = max(pos[k][0] + tam[k][0] for k in principal) + 30
    by1 = max(pos[k][1] + tam[k][1] for k in principal) + 25
    todas = list(principal)
    cajas = [(m.elem(f"pkg:{id_}", "Package", p["nombre"], ruta), bx0, by0, bx1 - bx0, by1 - by0)]
    objetos, extras = [], []
    for q in servicios:
        claves_q = [c["clave"] for c in A.clases_de_paquete(q["id"])]
        qpos, qtam = _disponer(claves_q)
        ox = bx0 + 20 - min(qpos[k][0] for k in claves_q)
        oy = by1 + 55 - min(qpos[k][1] for k in claves_q) + 35
        for k in claves_q:
            pos[k] = (qpos[k][0] + ox, qpos[k][1] + oy)
            tam[k] = qtam[k]
        qx0 = min(pos[k][0] for k in claves_q) - 20
        qy0 = min(pos[k][1] for k in claves_q) - 50
        qx1 = max(pos[k][0] + tam[k][0] for k in claves_q) + 20
        qy1 = max(pos[k][1] + tam[k][1] for k in claves_q) + 20
        extras.append((m.elem(f"pkg:{q['id']}", "Package", q["nombre"], ruta, est="service package"), qx0, qy0, qx1 - qx0, qy1 - qy0))
        todas += claves_q
        cajas[0] = (cajas[0][0], bx0, by0, max(bx1, qx1 + 10) - bx0, qy1 + 25 - by0)
    for k in todas:
        c = A.CLASES[k]
        m.elem(f"pkg:{k}", "Class", c["nombre"], ruta, est=_estereotipo(k, True),
               attrs=[(n, t, "", "Public") for n, t in c["atrib"]])
        objetos.append((f"pkg:{k}", *pos[k], *tam[k], *((NUEVO,) if _nuevo(k) else ())))
    # Solo las clases con sus atributos (PUDS 8.6.3.2: las clases con muchos atributos se muestran en un diagrama aparte); las asociaciones
    # se muestran en los diagramas de clases participantes de cada realización y se listan en las tablas de la sección.
    m.diagrama(f"an-pkg-{id_}", f"Clases del análisis del paquete {p['nombre']}", "Class", ruta, cajas + extras + objetos, [])


# ---- realización de un caso de uso --------------------------------------------------------------------------
def _instancias(col):
    inst = dict(col["actores"])
    if any(o == "S" or d == "S" for o, d, _ in col["mensajes"]):
        inst["S"] = A.ACTOR_EXTERNO["S"]
    return inst


def _ruta_colaboracion(col):
    return f"{MODELO}|Realizaciones de casos de uso|{col['id']}"


def _elementos_colaboracion(m, col):
    ruta = _ruta_colaboracion(col)
    inst = _instancias(col)
    for k, (_, rotulo) in inst.items():
        m.elem(f"re:{col['id']}:{k}", "Actor", rotulo, ruta)
    for k in col["objetos"]:
        c = A.CLASES[k]
        m.elem(f"re:{col['id']}:{k}", "Class", c["nombre"], ruta, est=_estereotipo(k))
    return inst


def _tam_nodo(col, k, inst):
    return tam_actor(inst[k][1]) if k in inst else ICONO


def _columnas_entidades(entidades, aristas):
    """Reparte las entidades en una o dos columnas: dos entidades relacionadas entre sí van, si se puede, en columnas distintas (así la
    línea que las une no atraviesa a una tercera apilada en medio)."""
    vecinos = {e: {b if a == e else a for a, b in aristas if e in (a, b) and a in entidades and b in entidades} for e in entidades}
    if not any(vecinos.values()):
        return [list(entidades)]
    color = {}
    for e in sorted(entidades, key=lambda e: (-len(vecinos[e]), entidades.index(e))):
        en_a = sum(1 for v in vecinos[e] if color.get(v) == 0)
        en_b = sum(1 for v in vecinos[e] if color.get(v) == 1)
        color[e] = 1 if en_a > en_b else 0
    return [c for c in ([e for e in entidades if color[e] == 0], [e for e in entidades if color[e] == 1]) if c]


def diagrama_participantes(m, col):
    """Clases del análisis que participan en la realización y las asociaciones entre ellas (PUDS, figura 8.11)."""
    ruta = _ruta_colaboracion(col)
    inst = _elementos_colaboracion(m, col)
    clave = lambda k: f"re:{col['id']}:{k}"  # noqa: E731
    objetos_cl = col["objetos"]
    tam = {k: _tam_nodo(col, k, inst) for k in list(inst) + objetos_cl}
    izq = [k for k in inst if k != "S"]
    cols = [izq,
            [k for k in objetos_cl if A.CLASES[k]["est"] == "interfaz" and k != "InterfazServicioIA"],
            [k for k in objetos_cl if A.CLASES[k]["est"] == "control"],
            *_columnas_entidades([k for k in objetos_cl if A.CLASES[k]["est"] == "entidad"],
                                 [(a, b) for a, b, *_ in A.RELACIONES if a in objetos_cl and b in objetos_cl]),
            [k for k in objetos_cl if k == "InterfazServicioIA"],
            [k for k in inst if k == "S"]]
    cols = [c for c in cols if c]
    asociaciones = [(a, b) for a, b, *_ in A.RELACIONES if a in objetos_cl and b in objetos_cl]
    aristas = list(asociaciones)
    # el actor se une a la clase de interfaz con la que se comunica (la del primer mensaje que envía o recibe)
    enlaces_actor = []
    for k in inst:
        for o, d, _ in col["mensajes"]:
            if o == k and d in objetos_cl:
                enlaces_actor.append((k, d))
                break
            if d == k and o in objetos_cl:
                enlaces_actor.append((k, o))
                break
    aristas += enlaces_actor
    pos = layout.columnas(tam, cols, aristas, hueco_x=170, hueco_y=50, pares_juntos=(), arbol=True)
    objetos = [(clave(k), *pos[k], *tam[k]) for k in tam]
    columna = {k: i for i, c in enumerate(cols) for k in c}
    conectores = _conectores_asociaciones(m, f"re:{col['id']}", objetos_cl, columna)
    conectores += [dict(de=clave(a), a=clave(b), tipo="Association", arbol="H") for a, b in enlaces_actor]
    m.diagrama(f"acp-{col['id']}", f"{col['id']}: clases participantes de «{col['nombre']}»", "Class", ruta, objetos, conectores)


def _etiqueta(numero, texto, flecha=""):
    """Etiqueta de un mensaje, partida en renglones; `flecha` ('->' o '<-') dice el sentido cuando la línea lleva mensajes en los dos."""
    renglones = textwrap.wrap(f"{numero}: {texto}", ANCHO_ETIQUETA, break_long_words=False)
    if flecha == "->":
        renglones[-1] += " ->"
    elif flecha == "<-":
        renglones[0] = "<- " + renglones[0]
    return "\n".join(renglones)


def diagrama_colaboracion(m, col):
    ruta = _ruta_colaboracion(col)
    inst = _elementos_colaboracion(m, col)
    clave = lambda k: f"re:{col['id']}:{k}"  # noqa: E731
    objetos_cl = col["objetos"]
    tam = {k: _tam_nodo(col, k, inst) for k in list(inst) + objetos_cl}
    cols = [[k for k in inst if k != "S"],
            [k for k in objetos_cl if A.CLASES[k]["est"] == "interfaz" and k != "InterfazServicioIA"],
            [k for k in objetos_cl if A.CLASES[k]["est"] == "control"],
            *_columnas_entidades([k for k in objetos_cl if A.CLASES[k]["est"] == "entidad"],
                                 [(o, d) for o, d, _ in col["mensajes"] if o in objetos_cl and d in objetos_cl]),
            [k for k in objetos_cl if k == "InterfazServicioIA"],
            [k for k in inst if k == "S"]]
    cols = [c for c in cols if c]
    columna = {k: i for i, c in enumerate(cols) for k in c}
    # Una sola línea (el enlace) por pareja de objetos, con los mensajes de los dos sentidos; si los lleva en los dos, cada uno dice el sentido.
    enlaces = {}
    for numero, (origen, destino, texto) in enumerate(col["mensajes"], 1):
        enlaces.setdefault(frozenset((origen, destino)), []).append((numero, origen, destino, texto))
    aristas, conectores = [], []
    for pareja, mensajes in enlaces.items():
        primero = mensajes[0]
        izquierda, derecha = sorted((primero[1], primero[2]), key=lambda k: (columna[k], list(tam).index(k)))
        dos_sentidos = len({(o, d) for _, o, d, _ in mensajes}) > 1
        etiquetas = []
        for numero, origen, destino, texto in mensajes:
            flecha = ("->" if origen == izquierda else "<-") if dos_sentidos else ""
            etiquetas.append(_etiqueta(numero, texto, flecha))
        aristas.append((izquierda, derecha))
        lineas = "\n".join(etiquetas).split("\n")
        cn = dict(de=clave(izquierda), a=clave(derecha), tipo="Association", nombre="\n".join(etiquetas),
                  arbol="V" if columna[izquierda] == columna[derecha] else "H",
                  etiq_auto=(int(6 * max(len(x) for x in lineas)), 14 * len(lineas)))
        if not dos_sentidos:
            cn["dir"] = "Source -> Destination"
            if mensajes[0][1] != izquierda:  # el único sentido es de derecha a izquierda: el origen es el elemento de la derecha
                cn["de"], cn["a"] = clave(derecha), clave(izquierda)
        conectores.append(cn)
    pos = layout.columnas(tam, cols, aristas, hueco_x=230, hueco_y=60, pares_juntos=(), arbol=True)
    objetos = [(clave(k), *pos[k], *tam[k]) for k in tam]
    m.diagrama(f"com-{col['id']}", f"{col['id']}: {col['nombre']}", "Collaboration", ruta, objetos, conectores)


def construir(m, solo=None):
    """Agrega al modelo los diagramas del análisis. `solo`: lista de identificadores de colaboración (para probar)."""
    A.validar(R)
    if solo is None:
        diagrama_paquetes(m)
        diagrama_dependencias(m)
        for p in A.PAQUETES:
            if not p["padre"]:
                diagrama_paquete(m, p["id"])
    for col in A.COLABORACIONES:
        if solo is None or col["id"] in solo:
            diagrama_participantes(m, col)
            diagrama_colaboracion(m, col)


if __name__ == "__main__":
    from especificaciones import Modelo

    modelo = Modelo()
    construir(modelo)
    print(len(modelo.diagramas), "diagramas de análisis;", len(modelo.elementos), "elementos")
