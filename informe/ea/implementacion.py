"""Diagramas del flujo de implementación (PUDS, capítulo 10) para Enterprise Architect, a partir de `modelo/implementacion.py`.

  im-<subsistema>     diagrama de componentes de un subsistema de implementación: sus archivos de código fuente (`<<file>>`), con las dependencias que
                      hay entre ellos por las asociaciones del diseño (la clase de un archivo nombra a la de otro)
"""

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
sys.path.insert(0, str(AQUI.parent))

import layout  # noqa: E402
from modelo import diseno as D  # noqa: E402
from modelo import implementacion as I  # noqa: E402

MODELO = "Modelo de implementación"
ANCHO, ALTO = 250, 56


def _profundidad(nodos, aristas):
    """Columna de cada archivo: los que no dependen de nadie del subsistema a la izquierda (sin recursión infinita si hay ciclos)."""
    prof = {}

    def calcular(n, visitados):
        if n in prof:
            return prof[n]
        if n in visitados:
            return 0
        visitados = visitados | {n}
        prof[n] = 1 + max([calcular(b, visitados) for a, b in aristas if a == n] + [-1])
        return prof[n]

    for n in nodos:
        calcular(n, frozenset())
    return prof


def diagrama_componentes_subsistema(m, sub):
    ruta = f"{MODELO}|{sub['nombre']}"
    prefijo = f"im:{sub['id']}"
    por_clave = {k: o["archivo"] for k, o in D.OBJETOS.items() if o["sub"] == sub["id"]}
    archivos = [c["ruta"] for c in sub["componentes"]]
    elementos = {}
    for ruta_archivo in archivos:
        nombre = Path(ruta_archivo).name
        elementos[ruta_archivo] = m.elem(f"{prefijo}:{ruta_archivo}", "Component", nombre, ruta, est="file")
    aristas = []
    for origen, destino, *_ in D.ASOCIACIONES:
        a, b = por_clave.get(origen), por_clave.get(destino)
        if a and b and a != b and (a, b) not in aristas:
            aristas.append((a, b))
    prof = _profundidad(archivos, aristas)
    columnas = {}
    for ruta_archivo in archivos:
        columnas.setdefault(prof[ruta_archivo], []).append(ruta_archivo)
    cols = [columnas[n] for n in sorted(columnas)]
    # una columna muy larga se parte en varias para que el diagrama no quede altísimo
    partidas = []
    for c in cols:
        partidas += [c[i:i + 6] for i in range(0, len(c), 6)]
    tam = {a: (ANCHO, ALTO) for a in archivos}
    pos = layout.columnas(tam, partidas, aristas, hueco_x=110, hueco_y=24, pares_juntos=(), arbol=True)
    x0 = min(pos[a][0] for a in archivos) - 30
    y0 = min(pos[a][1] for a in archivos) - 55
    x1 = max(pos[a][0] + ANCHO for a in archivos) + 30
    y1 = max(pos[a][1] + ALTO for a in archivos) + 25
    caja = m.elem(f"{prefijo}:caja", "Package", f"Subsistema de implementación: {sub['nombre']}", ruta, est="implementation subsystem")
    objetos = [(caja, x0, y0, x1 - x0, y1 - y0)]
    objetos += [(elementos[a], *pos[a], *tam[a]) for a in archivos]
    conectores = [dict(de=elementos[a], a=elementos[b], tipo="Dependency", arbol="H") for a, b in aristas]
    m.diagrama(f"im-{sub['id']}", f"Componentes del subsistema de implementación {sub['nombre']}", "Component", ruta, objetos, conectores)


def construir(m):
    I.validar()
    for sub in I.subsistemas():
        diagrama_componentes_subsistema(m, sub)


if __name__ == "__main__":
    from especificaciones import Modelo

    modelo = Modelo()
    construir(modelo)
    print(len(modelo.diagramas), "diagramas de implementación;", len(modelo.elementos), "elementos")
