"""Flujo de trabajo de implementación (PUDS cap. 10): el modelo de implementación sale del modelo de diseño y se comprueba contra el repositorio.

Reglas que se siguen (Jacobson, Booch y Rumbaugh, cap. 10; material de la cátedra):

  * cada subsistema de diseño tiene un subsistema de implementación (la misma división, en carpetas) y cada clase de diseño se implementa en un componente,
    que es un archivo de código fuente (`<<file>>`) con traza a las clases de diseño que contiene;
  * los ejecutables (`<<executable>>`) se asignan a los nodos del modelo de despliegue: aquí, los contenedores de Docker Compose;
  * las clases persistentes de diseño se implementan como tablas de PostgreSQL y colecciones de MongoDB (`<<table>>`);
  * el plan de integración ordena el sistema en construcciones: cada construcción agrega una parte y se acepta con pruebas.

`validar()` comprueba que todo lo que este modelo afirma existe: los archivos, los contenedores en los archivos de Docker Compose, los modelos y las migraciones de
las tablas, los campos de las colecciones y que cada construcción tiene commits en el repositorio.
"""

import re
import subprocess
from collections import OrderedDict
from pathlib import Path

from modelo import diseno as D

RAIZ = Path(__file__).resolve().parents[2]
COMPOSE = [RAIZ / "docker-compose.app.yml", RAIZ / "docker-compose.db.yml"]
LENGUAJE = {".py": "Python", ".ts": "TypeScript", ".java": "Java", ".html": "HTML"}

# Estándares de código del proyecto (AGENTS.md y la revisión previa a cada commit).
ESTANDARES = [
    "Inspeccionar el código existente antes de cambiarlo y no duplicar lo que ya existe; cambios pequeños y reversibles.",
    "Las pruebas de lo crítico se escriben antes que el código (XMI, colaboración, permisos, reconexión, generadores, transformaciones UML, persistencia sin conexión).",
    "Sin secretos en el repositorio: claves, contraseñas y `.env` quedan fuera (solo los nombres de las variables en `.env.example`).",
    "Los puertos del sistema no cambian sin una razón concreta (Angular 4200, Django 8000, Redis 6379, PostgreSQL 5433 en el equipo, Spring 7001).",
    "Cada commit tiene un solo propósito y pasa una revisión automática antes de entrar; las ramas de trabajo se integran en `develop`.",
    "Se usa el Maven Wrapper del proyecto (no se exige Maven instalado) y no se ejecutan actualizaciones masivas de dependencias.",
]


def lineas(ruta):
    return len(Path(ruta).read_text(encoding="utf-8").splitlines())


def _archivos_por_subsistema():
    por_sub = OrderedDict((s["id"], OrderedDict()) for s in D.SUBSISTEMAS)
    for clave, o in D.OBJETOS.items():
        por_sub[o["sub"]].setdefault(o["archivo"], []).append(o["rotulo"] if o["est"] == "module" else o["clase"])
    return por_sub


def subsistemas():
    """Los subsistemas de implementación: uno por cada subsistema de diseño, con sus componentes (archivos) y las clases de diseño de cada uno."""
    salida = []
    for s in D.SUBSISTEMAS:
        archivos = _archivos_por_subsistema()[s["id"]]
        componentes = [dict(ruta=ruta, lenguaje=LENGUAJE.get(Path(ruta).suffix, "otro"), clases=clases, lineas=lineas(RAIZ / ruta)) for ruta, clases in archivos.items()]
        carpetas = sorted({str(Path(c["ruta"]).parent) + "/" for c in componentes})
        salida.append(dict(id=s["id"], nombre=s["nombre"], capa=s["capa"], carpetas=carpetas, componentes=componentes,
                           lineas=sum(c["lineas"] for c in componentes)))
    return salida


def _servicios_compose():
    """{contenedor: {'origen': ..., 'puertos': [...], 'archivo': ...}} leído de los archivos de Docker Compose."""
    servicios = {}
    for archivo in COMPOSE:
        actual = None
        en_puertos = False
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^  ([\w-]+):\s*$", linea)
            if m and not linea.startswith("   "):
                actual = dict(servicio=m.group(1), archivo=archivo.name, origen="", puertos=[], contenedor=None)
                en_puertos = False
                continue
            if actual is None:
                continue
            m = re.match(r"^    container_name:\s*(\S+)", linea)
            if m:
                actual["contenedor"] = m.group(1)
                servicios[m.group(1)] = actual
            m = re.match(r"^    (build|image):\s*(\S+)", linea)
            if m:
                actual["origen"] = ("Dockerfile de " if m.group(1) == "build" else "imagen ") + m.group(2)
            if re.match(r"^    ports:\s*$", linea):
                en_puertos = True
                continue
            if en_puertos:
                m = re.match(r'^      - "?([^"\s]+)"?', linea)
                if m:
                    actual["puertos"].append(m.group(1))
                else:
                    en_puertos = False
    return servicios


def ejecutables():
    """Los ejecutables (contenedores) del modelo de despliegue, con lo que dicen los archivos de Docker Compose."""
    compose = _servicios_compose()
    filas = []
    for nombre, tipo, descripcion, funcion, acceso in D.NODOS:
        if tipo != "contenedor":
            continue
        c = compose.get(nombre)
        filas.append(dict(nombre=nombre, descripcion=descripcion, funcion=funcion, acceso=acceso, compose=c))
    return filas, compose


def _modelos_django():
    """{tabla: (archivo de modelos, modelo)} de las aplicaciones Django del backend."""
    tablas = {}
    for app in ("collab", "uml_api"):
        archivo = RAIZ / "back_generador_bd" / app / "models.py"
        for m in re.finditer(r"^class (\w+)\(models\.Model\)", archivo.read_text(encoding="utf-8"), re.M):
            tablas[f"{app}_{m.group(1).lower()}"] = (f"back_generador_bd/{app}/models.py", m.group(1), app)
    return tablas


def tablas():
    """Las tablas de PostgreSQL del diseño con su modelo de Django y la migración que las crea."""
    modelos = _modelos_django()
    filas = []
    for nombre, estado, _ in D.TABLAS:
        archivo, modelo, app = modelos.get(nombre, (None, None, None))
        migracion = None
        if modelo:
            for ruta in sorted((RAIZ / "back_generador_bd" / app / "migrations").glob("0*.py")):
                if re.search(rf"name=['\"]{modelo}['\"]", ruta.read_text(encoding="utf-8")):
                    migracion = ruta.name
                    break
        filas.append(dict(tabla=nombre, estado=estado, archivo=archivo, modelo=modelo, migracion=migracion))
    return filas


def colecciones():
    """Las colecciones de MongoDB del diseño y si el adaptador usa cada campo con ese nombre."""
    codigo = (RAIZ / "back_generador_bd" / "collab" / "mongo_stores.py").read_text(encoding="utf-8")
    filas = []
    for nombre, campos in D.COLECCIONES:
        usadas = f'"{nombre}"' in codigo
        faltan = [c for c, _, _ in campos if nombre != "counters" and f'"{c}"' not in codigo]
        filas.append(dict(coleccion=nombre, usada=usadas, campos=[c for c, _, _ in campos], faltan=faltan))
    return filas


def _git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], capture_output=True, text=True, check=True).stdout.strip()


def commits_de(etiqueta):
    """Commits del repositorio cuyo mensaje lleva «(etiqueta)», del más viejo al más nuevo: [(hash corto, fecha, mensaje)]."""
    salida = _git("log", "--reverse", "--fixed-strings", f"--grep=({etiqueta}", "--date=short", "--pretty=format:%h\t%ad\t%s")
    return [tuple(linea.split("\t", 2)) for linea in salida.splitlines() if linea]


def _subsistemas_de(clases):
    return sorted({D.OBJETOS[c]["sub"] for c in clases if c in D.OBJETOS}, key=lambda s: [x["id"] for x in D.SUBSISTEMAS].index(s))


# Orden en que se integraron las construcciones del ciclo 4 y por qué (lo decidió la dependencia entre ellas).
ORDEN_DE_INTEGRACION = ["C1", "C3", "C2", "C4"]
POR_QUE_ESE_ORDEN = {
    "C1": "Primero: define los puertos `ConversationStore` y `TurnStore` y el control compartido de la IA; todo lo demás del ciclo se apoya en ellos.",
    "C3": "Después de C1: agrega el puerto `ActivityStore` y los adaptadores de MongoDB para la actividad y para la conversación que C1 dejó detrás de un puerto.",
    "C2": "No depende de las anteriores (es solo del navegador); se integró con ellas ya estables para probar el seguimiento con la actividad real.",
    "C4": "Al final: reutiliza el proveedor de IA y los puertos de C1 y C3 (`RateLimiter` se agrega junto a los demás puertos).",
}


def construcciones():
    """Las construcciones del ciclo 4 en el orden en que se integraron, con sus commits."""
    por_id = {c["id"]: c for c in D.CAMBIOS}
    salida = []
    for orden, cid in enumerate(ORDEN_DE_INTEGRACION, 1):
        c = por_id[cid]
        commits = commits_de(cid)
        salida.append(dict(orden=orden, id=cid, nombre=c["nombre"], casos=c["casos"], subsistemas=_subsistemas_de(c["nuevas"] + c["cambian"]),
                           nuevas=c["nuevas"], cambian=c["cambian"], pruebas=c["pruebas"], commits=commits, por_que=POR_QUE_ESE_ORDEN[cid]))
    return salida


def linea_base():
    """La línea base del primer parcial: la etiqueta v1.0 del repositorio."""
    etiqueta = "v1.0"
    return dict(etiqueta=etiqueta, commit=_git("rev-list", "-n", "1", "--abbrev-commit", etiqueta), fecha=_git("log", "-1", "--date=short", "--format=%ad", etiqueta))


def validar():
    errores = []
    comp = subsistemas()
    if [s["id"] for s in comp] != [s["id"] for s in D.SUBSISTEMAS]:
        errores.append("los subsistemas de implementación no son los de diseño")
    for s in comp:
        if not s["componentes"]:
            errores.append(f"{s['id']}: el subsistema no tiene componentes")
        for c in s["componentes"]:
            if not (RAIZ / c["ruta"]).is_file():
                errores.append(f"{s['id']}: el componente {c['ruta']} no existe")
    clases_de_diseno = sum(len(c["clases"]) for s in comp for c in s["componentes"])
    if clases_de_diseno != len(D.OBJETOS):
        errores.append(f"las clases de diseño asignadas a componentes ({clases_de_diseno}) no son todas las del diseño ({len(D.OBJETOS)})")
    filas, compose = ejecutables()
    for f in filas:
        if f["compose"] is None:
            errores.append(f"el contenedor {f['nombre']} del modelo de despliegue no está en los archivos de Docker Compose")
    nombres_modelo = {f["nombre"] for f in filas}
    for contenedor, c in compose.items():
        if contenedor not in nombres_modelo and contenedor != "pgadmin":
            errores.append(f"el contenedor {contenedor} de {c['archivo']} no está en el modelo de despliegue")
    for t in tablas():
        if not t["modelo"]:
            errores.append(f"la tabla {t['tabla']} no tiene un modelo de Django")
        elif not t["migracion"]:
            errores.append(f"la tabla {t['tabla']} ({t['modelo']}) no tiene una migración que la cree")
    for c in colecciones():
        if not c["usada"]:
            errores.append(f"la colección {c['coleccion']} no la usa el adaptador de MongoDB")
        if c["faltan"]:
            errores.append(f"la colección {c['coleccion']}: el adaptador no usa los campos {', '.join(c['faltan'])}")
    for c in construcciones():
        if not c["commits"]:
            errores.append(f"{c['id']}: no hay commits en el repositorio con «({c['id']})»")
    if errores:
        raise ValueError("Modelo de implementación inconsistente:\n  " + "\n  ".join(errores))
    return dict(subsistemas=len(comp), componentes=sum(len(s["componentes"]) for s in comp), lineas=sum(s["lineas"] for s in comp))


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    print(validar())
