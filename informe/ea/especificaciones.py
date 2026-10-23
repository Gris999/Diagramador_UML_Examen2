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
from parte2 import _mensajes, _roles, clases_analisis, datos_cu, grupos_por_control  # noqa: E402
from parte2_datos import (CICLOS, CICLOS_PARCIAL1, CUS, DEPENDENCIAS_PAQUETES, NOMBRE_ACTOR,  # noqa: E402
                          PAQUETE_LIENZO, PAQUETES)
from parte2_datos import nombre_cu as nombre_de_cu  # noqa: E402

REQ = "Modelo de requisitos y análisis"
MARGEN = 30


def num(cu):
    """CU-14 -> CU14 y CU-01 -> CU1, como se citan los casos de uso en el informe."""
    return re.sub(r"CU-0?(\d+)", r"CU\1", cu)


def nombre_cu(cu):
    return f"{num(cu)}: {nombre_de_cu(cu)}"


def actores_dibujados(actores):
    """El Diseñador es un Colaborador con más permisos: si están los dos, solo se une el Colaborador (A2) y la
    generalización A1 -> A2 dice que el Diseñador también puede hacerlo. Así no se montan dos líneas por caso de uso."""
    return [a for a in actores if not (a == "A1" and "A2" in actores)]


# Casos de uso y paquete del primer parcial: se dibujan en gris para distinguirlos de los nuevos.
GRIS_PARCIAL1 = dict(fondo="#E7E6E6", borde="#7F7F7F", texto="#404040")


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

    def diagrama(self, id_, nombre, tipo, ruta, objetos, conectores, enlaces=None, arbol=None):
        """`objetos`: [(clave, x, y, w, h)] en orden de dibujo (los primeros quedan al fondo)."""
        minimo_x = min(o[1] for o in objetos)
        minimo_y = min(o[2] for o in objetos)
        dx, dy = MARGEN - minimo_x, MARGEN + 10 - minimo_y
        # `enlaces`: "paralelos" separa las líneas que unen el mismo par; "ocultar" no dibuja los conectores que EA
        # muestra solos al coincidir dos elementos de otro diagrama.
        if enlaces is None:
            enlaces = "" if tipo == "Sequence" else "paralelos"
        # `arbol`: estilo de línea ortogonal de EA para los conectores que no digan otro ("H": sale y entra en horizontal con el
        # tramo vertical en el hueco entre columnas; "V": igual en vertical; "OS": cuadrada).
        if arbol:
            for cn in conectores:
                if "arbol" not in cn and cn.get("tipo") not in ("Generalization", "Sequence", "NoteLink"):
                    cn["arbol"] = arbol
        self.diagramas.append(dict(
            id=id_, nombre=nombre, tipo=tipo, ruta=ruta, enlaces=enlaces,
            objetos=[dict(k=o[0], x=o[1] + dx, y=o[2] + dy, w=o[3], h=o[4], **(o[5] if len(o) > 5 else {})) for o in objetos],
            conectores=conectores))


K_EXPORT = 1.37  # EA exporta estos diagramas con unas 1,37 veces el tamaño de las coordenadas


def etiqueta_tronco(dy, lineas):
    """Posición de la etiqueta de un conector horizontal con tronco, para que quede a la izquierda del tramo vertical y a la altura
    de la flecha de su destino (`dy`: diferencia de altura entre origen y destino, en coordenadas). Está calibrada para un hueco
    de 500 coordenadas entre origen y destino."""
    ancho = 6.2 * max(len(x) for x in lineas)
    ox = ((268 - K_EXPORT * abs(dy)) * 0.2 + (166 - ancho) / 2) / K_EXPORT - 8 - 64 * (len(lineas) - 1)
    oy = (K_EXPORT * dy - 7 * len(lineas) + 14) / K_EXPORT
    return f"{int(ancho)}:{14 * len(lineas)}:{int(ox)}:{int(oy)}"


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
    """Actores, casos de uso del diagrama y casos de uso que estos incluyen, en tres columnas. Toda línea une columnas vecinas y
    va en horizontal y vertical (estilo árbol de EA), así que ninguna pasa por encima de un caso de uso."""
    mostrados = list(codigos)
    for cu in codigos:
        for inc in datos_cu(cu)[2]:
            if inc not in mostrados:
                mostrados.append(inc)
    actores = []
    for cu in codigos:
        for actor in datos_cu(cu)[1]:
            if actor not in actores:
                actores.append(actor)
    actores.sort()
    nodos = {a: tam_actor(NOMBRE_ACTOR[a]) for a in actores}
    nodos.update({cu: tam_cu(nombre_cu(cu)) for cu in mostrados})
    aristas, conectores = [], []
    for cu in codigos:
        _, cu_actores, incluye = datos_cu(cu)
        for actor in actores_dibujados(cu_actores):
            aristas.append((actor, cu))
            conectores.append(dict(de=actor, a=cu, tipo="Association"))
        for inc in incluye:
            aristas.append((cu, inc))
            conectores.append(dict(de=cu, a=inc, tipo="Dependency", est="include"))
    if "A1" in actores and "A2" in actores:
        conectores.append(dict(de="A1", a="A2", tipo="Generalization"))  # el Diseñador es un Colaborador con más permisos
    for a in actores:
        _actor(m, a)
    for cu in mostrados:
        _caso(m, cu)
    m.elem("SYS", "Boundary", "Plataforma CASE colaborativa", REQ)
    col_cu = [cu for cu in mostrados if cu in codigos]
    col_inc = [cu for cu in mostrados if cu not in codigos]
    pos = layout.columnas(nodos, [actores, col_cu, col_inc], aristas, hueco_x=150, pares_juntos=(("A1", "A2"),))
    x0 = min(pos[c][0] for c in mostrados) - 25
    y0 = min(pos[c][1] for c in mostrados) - 40
    x1 = max(pos[c][0] + nodos[c][0] for c in mostrados) + 25
    y1 = max(pos[c][1] + nodos[c][1] for c in mostrados) + 25
    for a in actores:  # los actores quedan fuera del límite del sistema
        pos[a] = (min(pos[a][0], x0 - 40 - nodos[a][0]), pos[a][1])
    objetos = [("SYS", x0, y0, x1 - x0, y1 - y0)]
    for c in nodos:
        extra = (GRIS_PARCIAL1,) if c in mostrados and c not in CUS else ()
        objetos.append((c, *pos[c], *nodos[c], *extra))
    m.diagrama(id_, nombre, "Use Case", REQ, objetos, conectores, arbol="H")


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
        x, y = (i % 2) * 640, (i // 2) * 130
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
    """Casos de uso del paquete dentro de su caja, con los actores que los inician a la izquierda (líneas ortogonales)."""
    nombre, _, cus = PAQUETES[indice]
    actores = sorted({a for cu in cus for a in CUS[cu]["actores"]})
    nodos = {a: tam_actor(NOMBRE_ACTOR[a]) for a in actores}
    nodos.update({cu: tam_cu(nombre_cu(cu)) for cu in cus})
    aristas, conectores = [], []
    for cu in cus:
        for a in actores_dibujados(CUS[cu]["actores"]):
            aristas.append((a, cu))
            conectores.append(dict(de=a, a=cu, tipo="Association"))
    if "A1" in actores and "A2" in actores:
        conectores.append(dict(de="A1", a="A2", tipo="Generalization"))
    for a in actores:
        _actor(m, a)
    for cu in cus:
        _caso(m, cu)
    pos = layout.columnas(nodos, [actores, list(cus)], aristas, hueco_x=190, pares_juntos=(("A1", "A2"),))
    x0 = min(pos[c][0] for c in cus) - 30
    y0 = min(pos[c][1] for c in cus) - 50
    x1 = max(pos[c][0] + nodos[c][0] for c in cus) + 30
    y1 = max(pos[c][1] + nodos[c][1] for c in cus) + 30
    objetos = [(_paquete(m, indice), x0, y0, x1 - x0, y1 - y0)]
    objetos += [(c, *pos[c], *nodos[c]) for c in nodos]
    m.diagrama(f"pk-vista-{indice + 1}", f"Vista del paquete {nombre}", "Package", REQ, objetos, conectores, arbol="H")


def diagrama_dependencias_paquetes(m):
    claves = {nombre: _paquete(m, i) for i, (nombre, _, _) in enumerate(PAQUETES)}
    claves[PAQUETE_LIENZO] = m.elem("PKG0", "Package", PAQUETE_LIENZO.upper(), REQ)
    # En L: Asistencia sobre Colaboración (vertical), Colaboración junto a Gestión de lienzo (horizontal) y Asistencia hacia
    # Gestión por el lado y hacia abajo, sin pasar por otro paquete.
    sitio = {"Asistencia inteligente": (0, 0), "Colaboración": (0, 260), PAQUETE_LIENZO: (460, 260)}
    objetos = [(claves[n], *sitio[n], 240, 90, *((GRIS_PARCIAL1,) if n == PAQUETE_LIENZO else ())) for n in sitio]
    conectores = []
    for o, d in DEPENDENCIAS_PAQUETES:
        cn = dict(de=claves[o], a=claves[d], tipo="Dependency")
        if (o, d) == ("Asistencia inteligente", PAQUETE_LIENZO):
            cn["arbol"] = "OS"
        conectores.append(cn)
    m.diagrama("pk-dep", "Dependencias entre paquetes de análisis", "Package", REQ, objetos, conectores)


# ---- comunicación y secuencia por caso de uso --------------------------------------------------------
def _roles_ea(m, cu, prefijo, ruta):
    """Elementos del caso de uso para un diagrama: {rol: clave}. Cada diagrama tiene los suyos."""
    claves, roles = {}, _roles(cu)
    for rol, (tipo, etiqueta) in roles.items():
        clave = f"{prefijo}:{cu}:{rol}"
        if rol == "U":
            m.elem(clave, "Actor", etiqueta, ruta)
        else:
            est = {"IU": "boundary", "EX": "boundary", "CT": "control"}.get(rol, "entity")
            m.elem(clave, "Class", etiqueta, ruta, est=est)
        claves[rol] = clave
    return claves, roles


def diagrama_comunicacion(m, cu):
    """Quien inicia, interfaz y control en una fila (líneas horizontales); entidades y servicio de IA en una columna a la
    derecha del control, unidos por líneas ortogonales. Los mensajes entre el mismo par y en el mismo sentido comparten
    línea con una etiqueta de varias filas."""
    ruta = f"Análisis de casos de uso|Comunicación {num(cu)}"
    claves, roles = _roles_ea(m, cu, "com", ruta)
    mensajes = _mensajes(cu)
    tam = {rol: (tam_actor(roles[rol][1]) if rol == "U" else (80, 70)) for rol in claves}
    derecha = [rol for rol in claves if rol not in ("U", "IU", "CT")]
    x, columnas_x = 0, {}
    for rol in ("U", "IU", "CT"):
        columnas_x[rol] = x
        x += tam[rol][0] + (250 if rol == "U" else 330 if rol == "IU" else 420)
    objetos, centros = [], {}
    for rol in ("U", "IU", "CT"):
        w, h = tam[rol]
        objetos.append((claves[rol], columnas_x[rol], -h / 2, w, h))
    paso = 130
    for i, rol in enumerate(derecha):
        w, h = tam[rol]
        objetos.append((claves[rol], x, (i - (len(derecha) - 1) / 2) * paso - h / 2, w, h))
    objetos = [(k, int(px), int(py), w, h) for k, px, py, w, h in objetos]
    grupos = {}
    for numero, (origen, destino, texto, _) in enumerate(mensajes, 1):
        grupos.setdefault((origen, destino), []).append(f"{numero}: {texto}")
    conectores = []
    for (origen, destino), lineas in grupos.items():
        cn = dict(de=claves[origen], a=claves[destino], tipo="Association", nombre="\n".join(lineas), dir="Source -> Destination")
        if destino in derecha:
            cn["arbol"] = "H"
            # La etiqueta va justo a la izquierda del tramo vertical, a la altura de la flecha de su entidad, para que se lea
            # a cuál pertenece aunque varias líneas compartan el tronco.
            dy = (derecha.index(destino) - (len(derecha) - 1) / 2) * paso
            cn["etiq"] = etiqueta_tronco(dy, lineas)
        conectores.append(cn)
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
        es_actor = rol == "U"
        w, h = (tam_actor(roles[rol][1])[0], 90) if es_actor else (80, 70)
        objetos.append((clave, int(xs[indice[rol]] - w / 2), 0, w, h))
    conectores = [dict(de=claves[o], a=claves[d], tipo="Sequence", nombre=t, seq=n)
                  for n, (o, d, t, _) in enumerate(mensajes, 1)]
    m.diagrama(f"sec-{cu.replace('-', '')}", f"{num(cu)}: {CUS[cu]['nombre']}", "Sequence", ruta, objetos, conectores)


# ---- clases de análisis por ciclo --------------------------------------------------------------------
def diagrama_clases_analisis(m, numero, codigos):
    ruta = f"Clases de análisis|Ciclo {numero}"
    interfaces, controles, entidades, relaciones, externas = clases_analisis(codigos)
    nodos = {}
    # «control» con un espacio al final: sin él EA dibuja el icono de control en lugar de la caja con operaciones.
    for est, grupo in (("interfaz", interfaces), ("control ", controles), ("entidad", entidades), ("interfaz", externas)):
        for nombre, ops in grupo.items():
            clave = f"cla:{numero}:{nombre}"
            miembros = sorted(o.replace("()", "") + "()" for o in ops)
            m.elem(clave, "Class", nombre, ruta, est=est, meths=[(o.replace("()", ""), "", "Public", "") for o in sorted(ops)])
            nodos[clave] = tam_clase(nombre, miembros)
    aristas = [(f"cla:{numero}:{o}", f"cla:{numero}:{d}") for o, d in sorted(relaciones)]
    cols = [[f"cla:{numero}:{n}" for n in interfaces], [f"cla:{numero}:{n}" for n in controles],
            [f"cla:{numero}:{n}" for n in list(entidades) + list(externas)]]
    pos = layout.columnas(nodos, cols, aristas, hueco_x=130, hueco_y=26, pares_juntos=())
    objetos = [(k, *pos[k], *nodos[k]) for k in nodos]
    conectores = [dict(de=o, a=d, tipo="Association", dir="Source -> Destination") for o, d in aristas]
    m.diagrama(f"cla-{numero}", f"Clases de análisis del ciclo {numero.split('-')[0]}: {', '.join(c.replace('-0', '').replace('-', '') for c in codigos)}",
               "Class", ruta, objetos, conectores, arbol="H")


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
    # Fila de arriba: módulos y la interfaz; fila de abajo: quienes los usan, justo debajo de lo que usan (líneas verticales).
    objetos = [("co:MOD", 0, 0, 330, 120), ("co:AIP", 430, 0, 260, 90), ("co:GRD", 790, 0, 330, 90),
               ("co:OLL", 0, 260, 300, 130), ("co:GEM", 430, 260, 260, 90), ("co:VW", 790, 260, 350, 90)]
    conectores = [dict(de="co:GEM", a="co:AIP", tipo="Realization"), dict(de="co:OLL", a="co:AIP", tipo="Realization"),
                  dict(de="co:OLL", a="co:MOD", tipo="Dependency", nombre="usa"),
                  dict(de="co:VW", a="co:AIP", tipo="Dependency"), dict(de="co:VW", a="co:GRD", tipo="Dependency")]
    m.diagrama("codigo", "Diagrama de código: proveedores de IA", "Class", ruta, objetos, conectores, arbol="V")


def diagrama_despliegue(m):
    ruta = "Diseño físico"
    nodo = lambda k, nombre, est, **kw: m.elem(k, "Node", nombre, ruta, est=est, **kw)
    art = lambda k, nombre, padre, est="": m.elem(k, "Artifact", nombre, ruta, padre=padre, est=est)
    nodo("dp:N", "Navegador del usuario", "device")
    art("dp:A", "Aplicación Angular", "dp:N")
    nodo("dp:EC2", "AWS EC2 (Ubuntu 24.04, 2 vCPU, 2 GB)", "device")
    nodo("dp:NG", "nginx + Let's Encrypt\n/ hacia Angular\n/api y /ws hacia Django\n/generate hacia Spring", "execution environment", padre="dp:EC2")
    nodo("dp:DK", "Docker Compose", "execution environment", padre="dp:EC2")
    art("dp:FE", "angular_frontend :4000 (publicado 4200)", "dp:DK")
    art("dp:DJ", "django_backend_UML :8000 (Daphne)", "dp:DK")
    art("dp:SP", "spring_backend :7001", "dp:DK")
    art("dp:PG", "postgres_db :5432", "dp:DK", "database")
    art("dp:RD", "redis_server :6379", "dp:DK", "database")
    nodo("dp:G", "Google Gemini API (nube, HTTPS)", "")
    nodo("dp:MAC", "Equipo con Apple Silicon", "device")
    art("dp:OL", "Ollama + modelo reentrenado :11434", "dp:MAC")
    # nginx a la izquierda reparte hacia FE, DJ y SP apilados; la base de datos y Redis quedan abajo a la derecha para
    # que ninguna línea cruce una caja; Gemini arriba y Ollama a la altura de Django.
    objetos = [("dp:N", 0, 200, 150, 100), ("dp:A", 10, 235, 125, 50),
               ("dp:EC2", 230, 0, 690, 470), ("dp:NG", 245, 190, 215, 110), ("dp:DK", 480, 30, 420, 420),
               ("dp:DJ", 495, 75, 175, 60), ("dp:FE", 495, 190, 175, 60), ("dp:SP", 495, 305, 175, 60),
               ("dp:PG", 720, 280, 165, 60), ("dp:RD", 720, 370, 165, 60),
               ("dp:G", 495, -160, 175, 70), ("dp:MAC", 1010, 20, 190, 130), ("dp:OL", 1020, 60, 165, 70)]
    conectores = [dict(de="dp:N", a="dp:NG", nombre="HTTPS / WSS :443", arbol="H"), dict(de="dp:NG", a="dp:FE", arbol="H"),
                  dict(de="dp:NG", a="dp:DJ", arbol="H"), dict(de="dp:NG", a="dp:SP", arbol="H"),
                  dict(de="dp:DJ", a="dp:PG", arbol="H"), dict(de="dp:DJ", a="dp:RD", arbol="H"),
                  dict(de="dp:DJ", a="dp:G", arbol="V"),
                  dict(de="dp:DJ", a="dp:OL", tipo="Dependency", nombre="HTTP (opcional)", arbol="H")]
    m.diagrama("despliegue", "Diagrama de despliegue", "Deployment", ruta, objetos, conectores)


def diagrama_capas(m):
    ruta = "Diseño lógico"
    capas = [("Capa de presentación", [("cp:ui", "Componentes Angular (editor, paneles, chat, vista móvil)", 2)]),
             ("Capa de aplicación", [("cp:sv", "Servicios Angular (colaboración, IA, diagrama)", 0),
                                     ("cp:vw", "Vistas DRF y consumidores de WebSocket", 2)]),
             ("Capa de dominio", [("cp:dm", "Modelo del diagrama (JointJS: clases y relaciones)", 0),
                                  ("cp:md", "Modelos de datos Django (participante, actividad, chat)", 1)]),
             ("Capa de infraestructura", [("cp:pg", "PostgreSQL", 1), ("cp:rd", "Redis", 2),
                                          ("cp:pv", "Proveedores de IA (Gemini, Ollama)", 3), ("cp:gn", "Generador Spring Boot", 4)])]
    # Cinco columnas: cada componente queda debajo o junto a los que usa, y las dependencias que saltan una capa
    # (Vistas DRF hacia Redis, IA y generador) pasan por huecos vacíos de la capa intermedia.
    ancho_col, paso, ancho = 190, 210, 20 + 5 * 210
    objetos, y = [], 0
    for i, (titulo, comps) in enumerate(capas, 1):
        m.elem(f"cp:C{i}", "Package", titulo, ruta)
        objetos.append((f"cp:C{i}", 0, y, ancho, 120))
        for k, nombre, col in comps:
            m.elem(k, "Component", nombre, ruta)
            objetos.append((k, 20 + col * paso, y + 50, ancho_col, 55))
        y += 120 + 70
    conectores = [dict(de="cp:ui", a="cp:sv", tipo="Dependency"), dict(de="cp:sv", a="cp:vw", tipo="Dependency", arbol="H"),
                  dict(de="cp:vw", a="cp:md", tipo="Dependency"), dict(de="cp:sv", a="cp:dm", tipo="Dependency"),
                  dict(de="cp:md", a="cp:pg", tipo="Dependency"), dict(de="cp:vw", a="cp:rd", tipo="Dependency"),
                  dict(de="cp:vw", a="cp:pv", tipo="Dependency"), dict(de="cp:vw", a="cp:gn", tipo="Dependency")]
    m.diagrama("capas", "Diseño lógico en capas", "Package", ruta, objetos, conectores, arbol="V")


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
               ("uml_api_backupuml", 0, 330, *tam["uml_api_backupuml"], GRIS_PARCIAL1)]
    conectores = [dict(de=n, a="collab_participant", tipo="Association", cd="0..*", ca="1", dir="Source -> Destination")
                  for n in ("collab_activityevent", "collab_chatmessage", "collab_iaattempt")]
    m.diagrama("datos", "Modelo de datos", "Class", ruta, objetos, conectores, arbol="H")


# ---- implementación ----------------------------------------------------------------------------------
def diagrama_componentes(m):
    ruta = "Diagrama de componentes"
    # Cada par que se comunica queda en la misma fila (línea horizontal) o en la misma columna (línea vertical).
    m.elem("cm:PKC", "Package", "Cliente (navegador)", ruta)
    m.elem("cm:PKS", "Package", "Servidor Django", ruta)
    nombres = {"cm:ED": "Editor de diagrama", "cm:SC": "Servicios de colaboración", "cm:SI": "Servicios de IA y chat",
               "cm:SE": "Exportaciones e importaciones", "cm:AI": "collab: actividad e identidad", "cm:RW": "collab: relé de WebSocket",
               "cm:CH": "uml_api: chat con la IA", "cm:XF": "uml_api: XMI y generador Flutter", "cm:PR": "uml_api: proveedores de IA",
               "cm:GS": "Generador Spring Boot", "cm:RE": "Redis", "cm:PG": "PostgreSQL", "cm:GE": "Gemini", "cm:OL": "Ollama (modelo reentrenado)"}
    for k, n in nombres.items():
        m.elem(k, "Component", n, ruta, est="database" if k in ("cm:RE", "cm:PG") else "")
    fila = {0: 50, 1: 140, 2: 230, 3: 320}
    objetos = [("cm:PKC", 0, 0, 280, 400), ("cm:PKS", 380, 0, 300, 400),
               ("cm:ED", 25, fila[0], 230, 45), ("cm:SC", 25, fila[1], 230, 45), ("cm:SI", 25, fila[2], 230, 45), ("cm:SE", 25, fila[3], 230, 45),
               ("cm:AI", 410, fila[0], 240, 45), ("cm:RW", 410, fila[1], 240, 45), ("cm:CH", 410, fila[2], 240, 45), ("cm:XF", 410, fila[3], 240, 45),
               ("cm:GS", 25, 480, 230, 45),
               ("cm:PG", 800, fila[0], 190, 45), ("cm:RE", 800, fila[1], 190, 45), ("cm:PR", 800, fila[2], 190, 45),
               ("cm:GE", 1110, fila[2], 190, 45), ("cm:OL", 1110, fila[3], 230, 45)]
    conectores = [dict(de="cm:ED", a="cm:SC", tipo="Dependency", arbol="V"), dict(de="cm:SC", a="cm:RW", tipo="Dependency", nombre="WebSocket", arbol="H"),
                  dict(de="cm:SI", a="cm:CH", tipo="Dependency", nombre="REST", arbol="H"), dict(de="cm:SE", a="cm:XF", tipo="Dependency", nombre="REST", arbol="H"),
                  dict(de="cm:SE", a="cm:GS", tipo="Dependency", nombre="HTTPS", arbol="V"), dict(de="cm:RW", a="cm:AI", tipo="Dependency", arbol="V"),
                  dict(de="cm:RW", a="cm:RE", tipo="Dependency", arbol="H"), dict(de="cm:AI", a="cm:PG", tipo="Dependency", arbol="H"),
                  dict(de="cm:CH", a="cm:PR", tipo="Dependency", arbol="H"), dict(de="cm:CH", a="cm:PG", tipo="Dependency", arbol="H"),
                  dict(de="cm:PR", a="cm:GE", tipo="Dependency", arbol="H"), dict(de="cm:PR", a="cm:OL", tipo="Dependency", arbol="H")]
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
    # Asistencia por IA arriba; edición, colaboración y actividad en una fila; interoperabilidad bajo edición. Así las
    # dependencias no atraviesan otro subsistema.
    posiciones = {"ss:S4": (360, 0), "ss:S1": (0, 380), "ss:S2": (360, 380), "ss:S3": (720, 380), "ss:S5": (0, 640)}
    objetos = []
    for k, titulo, comps in subs:
        m.elem(k, "Package", titulo, ruta, est="subsistema")
        x, y = posiciones[k]
        objetos.append((k, x, y, *tamanos[k]))
        for j, (ck, cn) in enumerate(comps):
            m.elem(ck, "Component", cn, ruta)
            objetos.append((ck, x + 20, y + 50 + j * 55, 250, 42))
    # Las dependencias de la fila del medio van en horizontal; las demás, en vertical.
    horizontales = {("ss:S2", "ss:S1"), ("ss:S2", "ss:S3")}
    conectores = [dict(de=o, a=d, tipo="Dependency", arbol="H" if (o, d) in horizontales else "V") for o, d in dependencias]
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
    # nginx en la fila del medio; Angular arriba, Django en la fila de nginx y Spring abajo; el túnel arriba de nginx.
    objetos = [("fl:U", 0, -55, 90, 110), ("fl:N", 230, -45, 200, 90), ("fl:T", 220, -230, 230, 80),
               ("fl:F", 930, -190, 190, 60), ("fl:D", 930, -30, 170, 60), ("fl:S", 930, 130, 200, 60),
               ("fl:R", 1360, -100, 150, 60), ("fl:P", 1360, 40, 150, 60)]
    conectores = [dict(de="fl:U", a="fl:N", nombre="HTTPS 443", arbol="H"),
                  dict(de="fl:N", a="fl:F", nombre="/", arbol="H", etiq=etiqueta_tronco(-160, ["/"])),
                  dict(de="fl:N", a="fl:D", nombre="/api  /ws", arbol="H"),
                  dict(de="fl:N", a="fl:S", nombre="/generate", arbol="H", etiq=etiqueta_tronco(160, ["/generate"])),
                  dict(de="fl:D", a="fl:R", arbol="H"), dict(de="fl:D", a="fl:P", arbol="H"),
                  dict(de="fl:T", a="fl:N", tipo="Dependency", arbol="V")]
    m.diagrama("despliegue-flujo", "Flujo de tráfico del despliegue", "Deployment", ruta, objetos, conectores)


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
    p1 = _c4(m, "c4c:disenador", "persona", "Diseñador", "Persona", "Crea la sala y expulsa a quien haga falta", ruta)
    p2 = _c4(m, "c4c:colaborador", "persona", "Colaborador", "Persona", "Diseña el diagrama de clases UML en equipo", ruta)
    s = _c4(m, "c4c:sistema", "sistema", "Plataforma CASE colaborativa", "Sistema de software",
            "Modelado UML 2.5, IA como integrante de la sala, generación de código", ruta)
    g = _c4(m, "c4c:gemini", "externo", "Google Gemini", "Sistema externo", "IA en la nube", ruta)
    o = _c4(m, "c4c:ollama", "externo", "Ollama + modelo reentrenado", "Sistema externo", "IA local, sin internet", ruta)
    ea = _c4(m, "c4c:ea", "externo", "Enterprise Architect", "Sistema externo", "Herramienta CASE (intercambio XMI)", ruta)
    # Las dos personas a la izquierda y los tres sistemas externos a la derecha, a 500 coordenadas del sistema.
    objetos = [_caja(p1, "persona", 0, -140, 220, 150), _caja(p2, "persona", 0, 140, 220, 150),
               _caja(s, "sistema", 720, 0, 280, 150),
               _caja(g, "externo", 1500, -190, 250, 120), _caja(o, "externo", 1500, 15, 250, 120), _caja(ea, "externo", 1500, 220, 250, 120)]
    centro = 75
    def rel(de, a, texto, tecnologia, y_de, y_a):
        lineas = [texto, f"[{tecnologia}]"]
        return _rel(de, a, texto, tecnologia) | {"arbol": "H", "etiq": etiqueta_tronco(y_a - y_de, lineas)}
    conectores = [_rel(p1, s, "Crea y gestiona la sala", "HTTPS / WebSocket") | {"arbol": "H"},
                  _rel(p2, s, "Edita y conversa con la IA", "HTTPS / WebSocket") | {"arbol": "H"},
                  rel(s, g, "Pide respuestas", "HTTPS", centro, -130), rel(s, o, "Pide respuestas (opcional)", "HTTP", centro, 75),
                  rel(s, ea, "Importa y exporta modelos", "XMI", centro, 280)]
    m.diagrama("c4-contexto", "Diagrama de contexto del sistema", "Component", ruta, objetos, conectores)


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
    objetos = [_caja(p, "persona", 75, 0, 200, 150),
               ("c4k:limite", 0, 190, 1150, 600),
               _caja(web, "contenedor", 40, 280, 270, 150), _caja(api, "contenedor", 530, 280, 300, 160),
               _caja(gen, "contenedor", 40, 570, 270, 150),
               _caja(pg, "contenedor", 530, 600, 250, 150), _caja(rd, "contenedor", 860, 600, 250, 150),
               _caja(g, "externo", 1330, 215, 250, 120), _caja(o, "externo", 1330, 385, 250, 120)]
    # Línea vertical entre elementos de arriba y abajo, horizontal entre los de al lado.
    centro_api = 360
    conectores = [_rel(p, web, "Usa", "HTTPS") | {"arbol": "V"}, _rel(web, api, "Edición y chat", "REST + WebSocket") | {"arbol": "H"},
                  _rel(web, gen, "Genera backend", "HTTPS") | {"arbol": "V"}, _rel(api, pg, "Lee y escribe", "SQL") | {"arbol": "V"},
                  _rel(api, rd, "Presencia", "RESP") | {"arbol": "V"},
                  _rel(api, g, "Pide respuestas", "HTTPS") | {"arbol": "H", "etiq": etiqueta_tronco(275 - centro_api, ["Pide respuestas", "[HTTPS]"])},
                  _rel(api, o, "Pide respuestas (opcional)", "HTTP") | {"arbol": "H", "etiq": etiqueta_tronco(445 - centro_api, ["Pide respuestas (opcional)", "[HTTP]"])}]
    m.diagrama("c4-contenedores", "Diagrama de contenedor", "Component", ruta, objetos, conectores)


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
    # Cuatro columnas: la guardia y el XMI a la derecha del chat, PostgreSQL justo debajo del chat y Redis a la izquierda del
    # relé. Así cada línea va en horizontal o vertical sin cruzar un componente.
    objetos = [("c4m:limite", 0, 0, 1500, 470),
               _caja(web, "contenedor", 540, -250, 270, 150),
               _caja(canvas, "componente", 30, 50, 290, 150), _caja(chat, "componente", 410, 50, 290, 150),
               _caja(guard, "componente", 790, 50, 290, 150), _caja(xmi, "componente", 1170, 50, 290, 150),
               _caja(act, "componente", 30, 290, 290, 140), _caja(provider, "componente", 790, 290, 290, 140),
               _caja(rd, "contenedor", -330, 70, 230, 110), _caja(pg, "contenedor", 410, 570, 290, 110),
               _caja(prov, "externo", 1570, 305, 230, 110)]
    conectores = [_rel(web, canvas, "Operaciones", "WebSocket") | {"arbol": "V"}, _rel(web, chat, "Pedidos", "REST") | {"arbol": "V"},
                  _rel(web, xmi, "Importa y exporta", "REST") | {"arbol": "V"}, _rel(canvas, act, "Registra") | {"arbol": "V"},
                  _rel(canvas, rd, "Roles") | {"arbol": "H"}, _rel(act, pg, "Guarda") | {"arbol": "V"},
                  _rel(chat, guard, "Valida") | {"arbol": "H"}, _rel(chat, provider, "Pide") | {"arbol": "H"},
                  _rel(provider, prov, "Pide respuestas", "HTTP") | {"arbol": "H"}, _rel(chat, pg, "Guarda chats") | {"arbol": "V"}]
    m.diagrama("c4-componentes", "Diagrama de componentes (C4)", "Component", ruta, objetos, conectores)


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
    # Modelo de este parcial: los seis casos de uso nuevos y, en gris, los del primer parcial que reutilizan.
    diagrama_casos_uso(m, "uc-ciclo-todo", "Modelo de casos de uso de este parcial (ciclos 4 a 6)", acumulado)
    diagrama_paquetes_identificados(m)
    diagrama_paquetes_y_cu(m)
    for i in range(len(PAQUETES)):
        diagrama_vista_paquete(m, i)
    diagrama_dependencias_paquetes(m)
    for _, _, _, codigos in CICLOS:
        for cu in codigos:
            diagrama_comunicacion(m, cu)
    for numero, _, _, codigos in CICLOS:
        for indice, (_, cus) in enumerate(grupos_por_control(codigos), 1):
            diagrama_clases_analisis(m, f"{numero}-{indice}", cus)
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
