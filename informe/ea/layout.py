"""Posiciones de los elementos de un diagrama, calculadas con Graphviz (`dot`).

Enterprise Architect dibuja cada elemento en el rectángulo que se le indica; aquí se decide dónde va
cada uno para que los diagramas queden ordenados y con pocos cruces. Todas las medidas son píxeles
del lienzo de EA (a 100 %). El origen es la esquina superior izquierda y `y` crece hacia abajo.
"""

from pathlib import Path

import subprocess

PUNTOS_POR_PX = 72 / 96  # Graphviz trabaja en puntos; EA en píxeles lógicos


def _px_a_pulgadas(px):
    return px / 96


def dot(nodos, aristas, direccion="LR", separacion_nodos=40, separacion_niveles=70, agrupar=None):
    """Devuelve ({clave: (x, y)}, (ancho, alto)) con la esquina superior izquierda de cada nodo.

    nodos:    {clave: (ancho_px, alto_px)}
    aristas:  [(origen, destino)]
    agrupar:  {clave: nivel} fuerza que los nodos con el mismo nivel queden en la misma fila/columna.
    """
    ids = {clave: f"n{i}" for i, clave in enumerate(nodos)}
    inverso = {v: k for k, v in ids.items()}
    lineas = [
        "digraph g {",
        f"  rankdir={direccion}; splines=false; nodesep={_px_a_pulgadas(separacion_nodos):.3f}; "
        f"ranksep={_px_a_pulgadas(separacion_niveles):.3f}; newrank=true;",
        "  node [shape=box, fixedsize=true, label=\"\"];",
    ]
    for clave, (ancho, alto) in nodos.items():
        lineas.append(f'  {ids[clave]} [width={_px_a_pulgadas(ancho):.3f}, height={_px_a_pulgadas(alto):.3f}];')
    for origen, destino in aristas:
        if origen in nodos and destino in nodos and origen != destino:
            lineas.append(f'  {ids[origen]} -> {ids[destino]};')
    if agrupar:
        niveles = {}
        for clave, nivel in agrupar.items():
            niveles.setdefault(nivel, []).append(clave)
        for claves in niveles.values():
            lineas.append("  { rank=same; " + "; ".join(ids[c] for c in claves) + "; }")
    lineas.append("}")
    resultado = subprocess.run(["dot", "-Tplain"], input="\n".join(lineas), capture_output=True, text=True, timeout=60)
    if resultado.returncode != 0:
        raise RuntimeError(f"Graphviz falló: {resultado.stderr[-400:]}")
    posiciones, ancho_total, alto_total = {}, 0, 0
    filas = []
    for linea in resultado.stdout.splitlines():
        partes = linea.split()
        if not partes:
            continue
        if partes[0] == "graph":
            ancho_total, alto_total = float(partes[2]) * 96, float(partes[3]) * 96
        elif partes[0] == "node":
            filas.append((inverso[partes[1]], float(partes[2]) * 96, float(partes[3]) * 96,
                          float(partes[4]) * 96, float(partes[5]) * 96))
    for clave, cx, cy, ancho, alto in filas:
        posiciones[clave] = (round(cx - ancho / 2), round(alto_total - cy - alto / 2))
    return posiciones, (round(ancho_total), round(alto_total))


def rejilla(tamanos, columnas, hueco_x=40, hueco_y=40):
    """Coloca los elementos en filas de `columnas` (para listas de paquetes o casos de uso sin relaciones)."""
    posiciones, x, y, alto_fila, ancho_max, contador = {}, 0, 0, 0, 0, 0
    for clave, (ancho, alto) in tamanos.items():
        if contador and contador % columnas == 0:
            x, y, alto_fila = 0, y + alto_fila + hueco_y, 0
        posiciones[clave] = (x, y)
        x += ancho + hueco_x
        ancho_max = max(ancho_max, x - hueco_x)
        alto_fila = max(alto_fila, alto)
        contador += 1
    return posiciones, (ancho_max, y + alto_fila)


# ---- acomodo por columnas con el mínimo de cruces ---------------------------------------------------------
def _segmento_cruza_caja(p, q, caja, margen=8):
    """¿El segmento p-q atraviesa la caja (x, y, w, h) achicada `margen` píxeles?"""
    x, y, w, h = caja
    x0, y0, x1, y1 = x + margen, y + margen, x + w - margen, y + h - margen
    if x1 <= x0 or y1 <= y0:
        return False
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for d, a in ((-dx, p[0] - x0), (dx, x1 - p[0]), (-dy, p[1] - y0), (dy, y1 - p[1])):
        if d == 0:
            if a < 0:
                return False
        else:
            r = a / d
            if d < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return False
    return True


def _orienta(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segmentos_se_cruzan(a, b, c, d):
    return _orienta(a, b, c) * _orienta(a, b, d) < 0 and _orienta(c, d, a) * _orienta(c, d, b) < 0


def _ruta_arbol(a, b, caja_a, caja_b, tronco=50):
    """Puntos del trazo de una línea de estilo árbol de EA (sale en horizontal, sube o baja por un tramo vertical a `tronco` unidades del
    destino y entra en horizontal); entre elementos de la misma columna, un tramo vertical."""
    (xa, ya, wa, ha), (xb, yb, wb, hb) = caja_a, caja_b
    ca, cb = (xa + wa / 2, ya + ha / 2), (xb + wb / 2, yb + hb / 2)
    if abs(ca[0] - cb[0]) < 1:
        return [ca, cb]
    if cb[0] > ca[0]:
        t = xb - tronco
    else:
        t = xb + wb + tronco
    return [ca, (t, ca[1]), (t, cb[1]), cb]


def columnas(nodos, cols, aristas, hueco_x=170, hueco_y=30, pares_juntos=(("A1", "A2"),), semilla=7, arbol=False):
    """Ver `_columnas`. Guarda el resultado en `build/layout_cache.json`: la búsqueda tarda segundos por diagrama y el resultado solo
    depende de los argumentos (la semilla es fija)."""
    import hashlib
    import json

    llave = hashlib.sha1(json.dumps([nodos, cols, sorted(map(list, aristas)), hueco_x, hueco_y, [list(p) for p in pares_juntos], semilla,
                                     arbol], sort_keys=True, default=list).encode()).hexdigest()
    archivo = Path(__file__).resolve().parent.parent / "build" / "layout_cache.json"
    try:
        cache = json.loads(archivo.read_text())
    except (OSError, ValueError):
        cache = {}
    if llave not in cache:
        cache[llave] = {k: list(v) for k, v in _columnas(nodos, cols, aristas, hueco_x, hueco_y, pares_juntos, semilla, arbol).items()}
        archivo.parent.mkdir(exist_ok=True)
        archivo.write_text(json.dumps(cache))
    return {k: tuple(v) for k, v in cache[llave].items()}


def _columnas(nodos, cols, aristas, hueco_x=170, hueco_y=30, pares_juntos=(("A1", "A2"),), semilla=7, arbol=False):
    """Coloca los nodos en columnas (de izquierda a derecha) buscando el acomodo con menos líneas que atraviesan otros
    nodos y menos cruces entre líneas. Cada columna tiene casillas en vertical; la búsqueda mueve y cambia nodos de
    casilla (varios reinicios, con semilla fija para que el resultado sea siempre el mismo).

    `pares_juntos`: nodos que conviene dejar en casillas vecinas (por ejemplo, un actor y su generalización).
    `arbol`: las líneas se miden con el trazo ortogonal de estilo árbol de EA en lugar de la recta entre centros.
    Devuelve {clave: (x, y)} con la esquina superior izquierda de cada nodo."""
    import itertools
    import random

    n_casillas = max(len(c) for c in cols) + 2
    paso = max(h for _, h in nodos.values()) + hueco_y
    anchos = [max((nodos[k][0] for k in col), default=0) for col in cols]
    xs, x = [], 0
    for ancho in anchos:
        xs.append(x)
        x += ancho + hueco_x
    columna_de = {k: ci for ci, col in enumerate(cols) for k in col}

    def posiciones(casilla):
        pos = {}
        for k, s in casilla.items():
            ci = columna_de[k]
            pos[k] = (xs[ci] + (anchos[ci] - nodos[k][0]) / 2, s * paso + (paso - hueco_y - nodos[k][1]) / 2)
        return pos

    def costo(casilla):
        pos = posiciones(casilla)
        centro = {k: (pos[k][0] + nodos[k][0] / 2, pos[k][1] + nodos[k][1] / 2) for k in pos}
        total = 0.0
        lineas = []  # (puntos, a, b)
        for a, b in aristas:
            if a in pos and b in pos:
                if arbol:
                    puntos = _ruta_arbol(a, b, (*pos[a], *nodos[a]), (*pos[b], *nodos[b]))
                else:
                    puntos = [centro[a], centro[b]]
                lineas.append((puntos, a, b))
        for puntos, a, b in lineas:
            for p, q in zip(puntos, puntos[1:]):
                for k in pos:
                    if k not in (a, b) and _segmento_cruza_caja(p, q, (*pos[k], *nodos[k]), margen=-6):
                        total += 100
            total += 0.02 * abs(puntos[-1][1] - puntos[0][1])
        for (pts1, a1, b1), (pts2, a2, b2) in itertools.combinations(lineas, 2):
            if len({a1, b1, a2, b2}) == 4:
                for p1, q1 in zip(pts1, pts1[1:]):
                    for p2, q2 in zip(pts2, pts2[1:]):
                        if _segmentos_se_cruzan(p1, q1, p2, q2):
                            total += 10
        for a, b in pares_juntos:
            if a in casilla and b in casilla:
                total += 30 * (abs(casilla[a] - casilla[b]) - 1)
        return total

    azar = random.Random(semilla)
    mejor, mejor_costo = None, None
    for _ in range(120):
        casilla = {}
        for col in cols:
            libres = azar.sample(range(n_casillas), len(col))
            casilla.update(dict(zip(col, libres)))
        actual = costo(casilla)
        for _ in range(400):
            col = [c for c in cols if c]
            col = azar.choice(col)
            k = azar.choice(col)
            nuevo = dict(casilla)
            ocupadas = {casilla[o]: o for o in col}
            destino = azar.randrange(n_casillas)
            if destino in ocupadas and ocupadas[destino] != k:
                nuevo[ocupadas[destino]] = casilla[k]  # intercambio
            nuevo[k] = destino
            c = costo(nuevo)
            if c <= actual:
                casilla, actual = nuevo, c
        if mejor_costo is None or actual < mejor_costo:
            mejor, mejor_costo = casilla, actual
            if actual < 1:
                break
    pos = posiciones(mejor)
    columnas.ultimo_costo = mejor_costo
    return {k: (round(v[0]), round(v[1])) for k, v in pos.items()}
