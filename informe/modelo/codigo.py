"""Índice del código del software: clases, atributos y operaciones reales, para que el diseño y el código no se separen.

El diseño del informe (clases de diseño, mensajes de las secuencias) cita nombres de clases y operaciones. Este módulo lee el código
(Python con `ast`; TypeScript por patrones) y `modelo/diseno.py` comprueba contra él que cada clase y cada operación citada existe,
salvo las que el diseño marca como nuevas (cambios C1 a C4 que se programan después del diseño).

Una función de un módulo Python que no está en una clase (por ejemplo, una vista de Django) se indexa como operación de la «clase»
`<archivo>` del módulo, que el diseño dibuja con el estereotipo «module».
"""

import ast
import re
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARPETAS_PY = [RAIZ / "back_generador_bd" / "collab", RAIZ / "back_generador_bd" / "uml_api", RAIZ / "back_generador_bd" / "uml_api" / "services",
               RAIZ / "back_generador_bd" / "uml_api" / "utils"]
CARPETA_JAVA = RAIZ / "back_generator_uml" / "src" / "main" / "java"
CARPETAS_TS = [RAIZ / "front_generador_bd" / "src" / "services", RAIZ / "front_generador_bd" / "src" / "app"]


def _visibilidad(nombre):
    if nombre.startswith("__") and not nombre.endswith("__"):
        return "private"
    return "protected" if nombre.startswith("_") and not nombre.startswith("__") else "public"


def _argumentos(nodo):
    a = nodo.args
    nombres = [x.arg for x in a.posonlyargs + a.args if x.arg not in ("self", "cls")]
    if a.vararg:
        nombres.append("*" + a.vararg.arg)
    nombres += [x.arg for x in a.kwonlyargs]
    if a.kwarg:
        nombres.append("**" + a.kwarg.arg)
    return nombres


def _tipo_valor(valor):
    """Tipo aproximado de lo que se asigna: el nombre de la clase si es una llamada o una referencia a una clase, o el de su literal."""
    if isinstance(valor, ast.Call):
        return ast.unparse(valor.func).split(".")[-1]
    if isinstance(valor, ast.Name):
        return valor.id if valor.id[:1].isupper() else ""
    if isinstance(valor, ast.Constant):
        return type(valor.value).__name__
    if isinstance(valor, (ast.Set, ast.SetComp)):
        return "set"
    if isinstance(valor, (ast.Dict, ast.DictComp)):
        return "dict"
    if isinstance(valor, (ast.List, ast.ListComp)):
        return "list"
    return ""


def _clase_py(nodo):
    atributos, metodos = {}, {}
    for hijo in nodo.body:
        if isinstance(hijo, ast.Assign):
            for t in hijo.targets:
                if isinstance(t, ast.Name):
                    atributos[t.id] = dict(vis=_visibilidad(t.id), tipo=_tipo_valor(hijo.value))
        elif isinstance(hijo, ast.AnnAssign) and isinstance(hijo.target, ast.Name):
            atributos[hijo.target.id] = dict(vis=_visibilidad(hijo.target.id), tipo=ast.unparse(hijo.annotation))
        elif isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            metodos[hijo.name] = dict(args=_argumentos(hijo), vis=_visibilidad(hijo.name), asincrono=isinstance(hijo, ast.AsyncFunctionDef))
            for sub in ast.walk(hijo):
                if isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name) and t.value.id == "self":
                            atributos.setdefault(t.attr, dict(vis=_visibilidad(t.attr), tipo=_tipo_valor(sub.value)))
    bases = [ast.unparse(b) for b in nodo.bases]
    return dict(lenguaje="python", tipo="clase", bases=bases, atributos=atributos, metodos=metodos)


def _indexar_python(ruta):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    relativa = ruta.relative_to(RAIZ).as_posix()
    clases, funciones = {}, {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.ClassDef):
            clases[nodo.name] = _clase_py(nodo)
        elif isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funciones[nodo.name] = dict(args=_argumentos(nodo), vis=_visibilidad(nodo.name), asincrono=isinstance(nodo, ast.AsyncFunctionDef))
    if funciones:
        clases[f"<{ruta.name}>"] = dict(lenguaje="python", tipo="módulo", bases=[], atributos={}, metodos=funciones)
    return relativa, clases


RE_CLASE_TS = re.compile(r"^export\s+(?:abstract\s+)?(class|interface)\s+([A-Za-z_$][\w$]*)(?:\s+extends\s+([\w$.<>, ]+?))?(?:\s+implements\s+([\w$., ]+?))?\s*\{", re.M)
PLANTILLA_METODO_TS = (r"^ {%d,%d}((?:(?:public|private|protected|static|async|override)\s+)*)([A-Za-z_$][\w$]*)\s*(?:<[^>(]*>)?\(((?:[^()]|\([^()]*\))*)\)"
                       r"\s*(?::\s*[^{;=]+?)?\s*[%s]")
PLANTILLA_CAMPO_TS = r"^ {%d}((?:(?:public|private|protected|static|readonly)\s+)*)([A-Za-z_$][\w$]*)\s*[?!]?\s*(:\s*([^=;\n]+?)\s*(?:=|;|$)|=\s*(?:new\s+)?([A-Za-z_$][\w$.]*)(<[^(]*>)?)"
PALABRAS = {"if", "for", "while", "switch", "return", "catch", "constructor", "get", "set", "else", "function", "try"}


def _cuerpo(texto, inicio):
    """Texto de una clase TypeScript desde la llave que la abre hasta su llave de cierre (a nivel 0 de sangría)."""
    fin = texto.find("\n}", inicio)
    return texto[inicio:fin if fin != -1 else len(texto)]


def _indexar_ts(ruta):
    texto = ruta.read_text(encoding="utf-8").replace("\t", "  ")
    relativa = ruta.relative_to(RAIZ).as_posix()
    clases = {}
    for m in RE_CLASE_TS.finditer(texto):
        tipo, nombre, base, impl = m.group(1), m.group(2), m.group(3), m.group(4)
        cuerpo = _cuerpo(texto, m.end())
        metodos, atributos = {}, {}
        primera = next((linea for linea in cuerpo.split("\n") if linea.strip() and not linea.strip().startswith(("//", "/*", "*"))), "  x")
        sangria = len(primera) - len(primera.lstrip(" "))
        re_metodo = re.compile(PLANTILLA_METODO_TS % (sangria, sangria + 2, "{;" if tipo == "interface" else "{"), re.M)
        re_campo = re.compile(PLANTILLA_CAMPO_TS % sangria, re.M)
        for mm in re_metodo.finditer(cuerpo):
            mods, n, args = mm.group(1), mm.group(2), mm.group(3)
            if n in PALABRAS and n != "constructor":
                continue
            vis = "private" if "private" in mods else "protected" if "protected" in mods else "public"
            nombres = [a.split(":")[0].split("=")[0].strip().rstrip("?").lstrip(".") for a in args.split(",") if a.strip()]
            metodos[n] = dict(args=nombres, vis=vis, asincrono="async" in mods)
        for mm in re_campo.finditer(cuerpo):
            mods, n = mm.group(1), mm.group(2)
            if n in PALABRAS or n in metodos:
                continue
            tipo_ts = (mm.group(4) or (mm.group(5) or "") + (mm.group(6) or "")).strip()
            tipo_ts = {"true": "boolean", "false": "boolean", "null": "", "undefined": ""}.get(tipo_ts, tipo_ts)
            atributos[n] = dict(vis="private" if "private" in mods else "protected" if "protected" in mods else "public", tipo=tipo_ts)
        bases = ([base.strip()] if base else []) + ([x.strip() for x in impl.split(",")] if impl else [])
        clases[nombre] = dict(lenguaje="typescript", tipo="interfaz" if tipo == "interface" else "clase", bases=bases, atributos=atributos,
                              metodos=metodos)
    return relativa, clases


RE_CLASE_JAVA = re.compile(r"^(?:public\s+)?(?:final\s+)?(?:abstract\s+)?(class|interface|record|enum)\s+([A-Za-z_]\w*)", re.M)
RE_METODO_JAVA = re.compile(r"^ {4}((?:(?:public|private|protected|static|final|synchronized)\s+)*)(?:<[^>]+>\s+)?[\w<>\[\],.? ]+?\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)", re.M)
RE_CAMPO_JAVA = re.compile(r"^ {4}((?:(?:public|private|protected|static|final)\s+)+)[\w<>\[\],.? ]+?\s+([a-zA-Z_]\w*)\s*(?:=|;)", re.M)


def _indexar_java(ruta):
    texto = ruta.read_text(encoding="utf-8")
    relativa = ruta.relative_to(RAIZ).as_posix()
    clases = {}
    for m in RE_CLASE_JAVA.finditer(texto):
        nombre = m.group(2)
        metodos, atributos = {}, {}
        for mm in RE_METODO_JAVA.finditer(texto):
            mods, n, args = mm.group(1), mm.group(2), mm.group(3)
            if n in PALABRAS or n == nombre:
                continue
            vis = "private" if "private" in mods else "protected" if "protected" in mods else "public"
            nombres = [a.strip().split()[-1] for a in args.split(",") if a.strip()]
            metodos[n] = dict(args=nombres, vis=vis, asincrono=False)
        for mm in RE_CAMPO_JAVA.finditer(texto):
            atributos[mm.group(2)] = dict(vis="private" if "private" in mm.group(1) else "public", tipo="")
        clases[nombre] = dict(lenguaje="java", tipo="interfaz" if m.group(1) == "interface" else "clase", bases=[], atributos=atributos,
                              metodos=metodos)
    return relativa, clases


@lru_cache(maxsize=1)
def indice():
    """{archivo relativo: {clase: {...}}} de todo el código que el diseño cita."""
    resultado = {}
    for carpeta in CARPETAS_PY:
        for ruta in sorted(carpeta.glob("*.py")):
            if ruta.name in ("__init__.py", "apps.py", "admin.py", "tests.py") or "migrations" in ruta.parts:
                continue
            archivo, clases = _indexar_python(ruta)
            if clases:
                resultado[archivo] = clases
    for carpeta in CARPETAS_TS:
        for ruta in sorted(carpeta.rglob("*.ts")):
            if ruta.name.endswith(".spec.ts") or "node_modules" in ruta.parts:
                continue
            archivo, clases = _indexar_ts(ruta)
            if clases:
                resultado[archivo] = clases
    for ruta in sorted(CARPETA_JAVA.rglob("*.java")):
        archivo, clases = _indexar_java(ruta)
        if clases:
            resultado[archivo] = clases
    return resultado


def buscar(archivo, clase):
    return indice().get(archivo, {}).get(clase)


def existe(archivo, clase, operacion=None):
    """¿Existe la clase en el archivo y, si se da, esa operación (método, o atributo para una propiedad invocable) en ella?"""
    c = buscar(archivo, clase)
    if c is None:
        return False
    if operacion is None:
        return True
    return operacion in c["metodos"] or operacion in c["atributos"]


if __name__ == "__main__":
    ind = indice()
    print(len(ind), "archivos,", sum(len(v) for v in ind.values()), "clases")
    for a in ("back_generador_bd/collab/consumers.py", "front_generador_bd/src/services/colaboration/collaboration.service.ts"):
        for n, c in ind[a].items():
            print(a.split("/")[-1], n, "métodos:", len(c["metodos"]), "atributos:", len(c["atributos"]))
