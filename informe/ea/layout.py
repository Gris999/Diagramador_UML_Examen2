"""Posiciones de los elementos de un diagrama, calculadas con Graphviz (`dot`).

Enterprise Architect dibuja cada elemento en el rectángulo que se le indica; aquí se decide dónde va
cada uno para que los diagramas queden ordenados y con pocos cruces. Todas las medidas son píxeles
del lienzo de EA (a 100 %). El origen es la esquina superior izquierda y `y` crece hacia abajo.
"""

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
