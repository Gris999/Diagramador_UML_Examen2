"""Diagramas de casos de uso (flujo de requisitos) para Enterprise Architect, a partir de `modelo/requisitos.py`.

Reglas (PUDS p. 29, 31 y 32; guías públicas de RUP):
  * los actores quedan fuera de la frontera del sistema y los casos de uso dentro;
  * la asociación une al actor con el caso que inicia; si están A1 y A2 solo se une A2 y una generalización A1 -> A2
    dice que el Diseñador también lo hace; el actor secundario (A3) va a la derecha;
  * `extend` se declara solo donde hay comportamiento opcional de otro caso (modelo.requisitos.RELACIONES);
  * las líneas son horizontales y verticales (estilo de árbol de EA) y no cruzan casos de uso.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import layout  # noqa: E402
from especificaciones import GRIS_PARCIAL1, REQ, tam_actor, tam_cu  # noqa: E402
from modelo import requisitos as R  # noqa: E402

# Casos de uso nuevos del segundo parcial: amarillo suave, como la cabecera de las tablas del informe.
NUEVO = dict(fondo="#FFF2CC", borde="#BF9000", texto="#000000")


def num(codigo):
    return codigo  # ya viene como CU1, CU14...


def nombre(codigo):
    return f"{codigo}: {R.CASOS[codigo]['nombre']}"


def _actor(m, a):
    return m.elem(a, "Actor", R.NOMBRE_ACTOR[a], REQ)


def _caso(m, c):
    return m.elem(c, "UseCase", nombre(c), REQ)


def diagrama(m, id_, titulo, propios, relacionados=(), nuevos=None):
    """`propios`: casos de uso del diagrama; `relacionados`: los de otros ciclos que se muestran por una relación (en gris).
    `nuevos`: casos que se pintan de amarillo (por defecto, los del ciclo 4)."""
    nuevos = set(R.casos_del_ciclo(4)) if nuevos is None else set(nuevos)
    mostrados = list(propios) + [c for c in relacionados if c not in propios]
    actores, secundarios = [], []
    for c in propios:
        for a in R.CASOS[c]["actores"]:
            lista = secundarios if a == "A3" else actores
            if a not in lista:
                lista.append(a)
    actores.sort()
    nodos = {a: tam_actor(R.NOMBRE_ACTOR[a]) for a in actores + secundarios}
    nodos.update({c: tam_cu(nombre(c)) for c in mostrados})
    aristas, conectores = [], []
    for c in propios:
        for a in R.CASOS[c]["actores"]:
            if a == "A3":
                aristas.append((c, a))
                conectores.append(dict(de=c, a=a, tipo="Association"))
        for a in R.actores_dibujados(c):
            if a != "A3":
                aristas.append((a, c))
                conectores.append(dict(de=a, a=c, tipo="Association"))
    for origen, destino, tipo, _ in R.RELACIONES:
        if origen in mostrados and destino in mostrados:
            aristas.append((origen, destino))
            conectores.append(dict(de=origen, a=destino, tipo="Dependency", est=tipo, arbol="V"))
    if "A1" in actores and "A2" in actores:
        conectores.append(dict(de="A1", a="A2", tipo="Generalization"))  # el Diseñador es un Colaborador con más permisos
    for a in actores + secundarios:
        _actor(m, a)
    for c in mostrados:
        _caso(m, c)
    m.elem("SYS", "Boundary", "Plataforma CASE colaborativa", REQ)
    ajenos = [c for c in mostrados if c not in propios]
    # Los casos relacionados van en la misma columna que los propios (uno junto al otro, unidos en vertical): así ninguna
    # línea hacia el actor secundario pasa por detrás de ellos.
    juntos = (("A1", "A2"),) + tuple((o, d) for o, d, _, _ in R.RELACIONES if o in mostrados and d in mostrados)
    pos = layout.columnas(nodos, [actores, list(propios) + ajenos, secundarios], aristas, hueco_x=170, pares_juntos=juntos)
    x0 = min(pos[c][0] for c in mostrados) - 25
    y0 = min(pos[c][1] for c in mostrados) - 40
    x1 = max(pos[c][0] + nodos[c][0] for c in mostrados) + 25
    y1 = max(pos[c][1] + nodos[c][1] for c in mostrados) + 25
    for a in actores:  # fuera de la frontera
        pos[a] = (min(pos[a][0], x0 - 40 - nodos[a][0]), pos[a][1])
    for a in secundarios:
        pos[a] = (max(pos[a][0], x1 + 40), pos[a][1])
    objetos = [("SYS", x0, y0, x1 - x0, y1 - y0)]
    for clave in nodos:
        if clave in ajenos:
            color = (GRIS_PARCIAL1,)
        elif clave in nuevos:
            color = (NUEVO,)
        else:
            color = ()
        objetos.append((clave, *pos[clave], *nodos[clave], *color))
    m.diagrama(id_, titulo, "Use Case", REQ, objetos, conectores, arbol="H")


def construir(m):
    """Agrega al modelo los diagramas de casos de uso: uno por caso, uno por ciclo, el modelo completo y la vista de la arquitectura."""
    relacionados = {}
    for origen, destino, _, _ in R.RELACIONES:
        relacionados.setdefault(origen, []).append(destino)
        relacionados.setdefault(destino, []).append(origen)
    for codigo in sorted(R.CASOS, key=R.numero):
        diagrama(m, f"uc-{codigo}", nombre(codigo), [codigo], relacionados.get(codigo, []))
    for numero_ciclo, _, codigos in R.CICLOS:
        extra = sorted({r for c in codigos for r in relacionados.get(c, []) if r not in codigos}, key=R.numero)
        diagrama(m, f"uc-ciclo-{numero_ciclo}", f"Casos de uso del ciclo de vida {numero_ciclo}", codigos, extra)
    todos = sorted(R.CASOS, key=R.numero)
    diagrama(m, "uc-modelo", "Modelo de casos de uso completo", todos)
    diagrama(m, "uc-arquitectura", "Vista de la arquitectura del modelo de casos de uso", R.SIGNIFICATIVOS)


if __name__ == "__main__":
    from especificaciones import Modelo

    modelo = Modelo()
    construir(modelo)
    print(len(modelo.diagramas), "diagramas de casos de uso;", len(modelo.elementos), "elementos")
