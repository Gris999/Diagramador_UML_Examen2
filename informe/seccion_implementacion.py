"""Sección 2.4 del informe: flujo de trabajo de implementación (PUDS cap. 10), generada de `modelo/implementacion.py`.

Todo lo que se afirma se comprueba contra el repositorio al generar el informe: los archivos existen, los contenedores están en Docker Compose, las tablas
tienen su modelo y su migración, las colecciones coinciden con el adaptador y cada construcción tiene sus commits.
"""

from modelo import diseno as D
from modelo import implementacion as I
from seccion_requisitos import _uml_respaldo

ESTEREOTIPO = {"Python": "<<file>> Python", "TypeScript": "<<file>> TypeScript", "Java": "<<file>> Java"}


def miles(n):
    return f"{n:,}".replace(",", ".")


def _corta(ruta):
    for prefijo in ("front_generador_bd/src/", "back_generador_bd/", "back_generator_uml/src/main/java/generator_uml/back_generator_uml/"):
        if ruta.startswith(prefijo):
            return ruta[len(prefijo):]
    return ruta


def _raiz_de(ruta):
    if ruta.startswith("front_generador_bd"):
        return "front_generador_bd/src/"
    if ruta.startswith("back_generator_uml"):
        return "back_generator_uml/…/back_generator_uml/"
    return "back_generador_bd/"


def generar():
    resumen = I.validar()
    subs = I.subsistemas()
    md = ["## 2.4 Implementación\n",
          "El flujo de implementación convierte el diseño en código. Lo que se implementó está descrito aquí como el **modelo de implementación**: los subsistemas de implementación "
          "(la misma división que el diseño, en carpetas), los componentes (los archivos de código fuente que contienen las clases de diseño), los ejecutables asignados a los nodos, "
          "las tablas y colecciones donde se guardan los datos y el plan con que se integró el ciclo 4. Todo se genera del modelo de diseño y se comprueba contra el repositorio cada vez "
          "que se arma el informe: si un archivo, un contenedor, una tabla o un campo que aquí se nombra no existiera, el informe no se generaría.\n"]

    md += ["### 2.4.1 Alcance y estándares de código\n",
           f"El sistema implementado tiene **{resumen['subsistemas']} subsistemas de implementación**, **{resumen['componentes']} componentes** de código fuente y unas "
           f"**{miles(resumen['lineas'])} líneas** (sin contar las pruebas, que se describen en la sección 2.5), escritas en TypeScript (Angular 20 con JointJS), Python 3.12 (Django 5, "
           "Django REST Framework y Channels) y Java 21 (Spring Boot 3.5). Los estándares que se siguieron están en `AGENTS.md`, el documento que le dice a las personas y a los "
           "asistentes de IA cómo trabajar en el repositorio:\n"]
    md += [f"- {e}" for e in I.ESTANDARES]
    md.append("")

    md += ["### 2.4.2 Subsistemas de implementación\n",
           "Cada subsistema de diseño (sección 2.3) tiene un subsistema de implementación con el mismo nombre y las mismas fronteras, en una o varias carpetas del repositorio. "
           "La tabla muestra dónde vive cada uno.\n",
           "| Subsistema | Capa | Carpetas | Componentes | Líneas |", "|---|---|---|---|---|"]
    for s in subs:
        carpetas = "<br>".join(f"`{_corta(c)}`" for c in s["carpetas"])
        md.append(f"| {s['nombre']} | {s['capa'].capitalize()} | {carpetas} | {len(s['componentes'])} | {miles(s['lineas'])} |")
    md += ["", "Las rutas se dan relativas a `front_generador_bd/src/` (Angular), `back_generador_bd/` (Django) o `back_generator_uml/src/main/java/generator_uml/back_generator_uml/` (Spring Boot), "
           "según el tipo de archivo.\n"]

    md += ["### 2.4.3 Componentes y su traza al diseño\n",
           "Un componente es un archivo de código fuente (`<<file>>`). La traza dice qué clases de diseño de la sección 2.3 implementa: así, desde una clase del diseño se llega al "
           "archivo que la contiene y al revés. Los nombres entre `< >` son módulos de funciones (no clases).\n"]
    for s in subs:
        md += [f"#### {s['nombre']}\n", _uml_respaldo(f"im-{s['id']}", f"Componentes del subsistema de implementación {s['nombre']}"),
               "| Componente `<<file>>` | Lenguaje | Implementa (clases de diseño) | Líneas |", "|---|---|---|---|"]
        for c in s["componentes"]:
            clases = ", ".join(f"`{x}`" for x in c["clases"])
            md.append(f"| `{_corta(c['ruta'])}` | {c['lenguaje']} | {clases} | {miles(c['lineas'])} |")
        md.append("")

    filas, compose = I.ejecutables()
    md += ["### 2.4.4 Ejecutables y nodos\n",
           "Los ejecutables (`<<executable>>`) son los contenedores de Docker Compose; cada uno se asigna a un nodo del modelo de despliegue (sección 2.3.1). "
           "Los archivos `docker-compose.app.yml` (aplicación) y `docker-compose.db.yml` (bases de datos) los definen, y el modelo coincide con ellos: cada contenedor "
           "del modelo está en los archivos y cada contenedor de los archivos está en el modelo (`pgadmin` es solo una herramienta de desarrollo).\n",
           "| Ejecutable `<<executable>>` | Se construye de | Puertos publicados | Archivo | Función |", "|---|---|---|---|---|"]
    for f in filas:
        c = f["compose"]
        puertos = ", ".join(c["puertos"]) if c["puertos"] else "ninguno (red interna)"
        md.append(f"| `{f['nombre']}` | {c['origen']} | {puertos} | `{c['archivo']}` | {f['funcion']} |")
    md.append("")

    md += ["### 2.4.5 Tablas y colecciones\n",
           "Las clases persistentes del diseño se implementan como tablas de PostgreSQL (modelos de Django y sus migraciones) y como colecciones de MongoDB (el adaptador de "
           "`collab/mongo_stores.py`). La actividad y la conversación con la IA están en una de las dos según la configuración (`ACTIVITY_STORE` y `CONVERSATION_STORE`).\n",
           "| Tabla `<<table>>` | Modelo de Django | Migración que la crea | Estado |", "|---|---|---|---|"]
    for t in I.tablas():
        md.append(f"| `{t['tabla']}` | `{t['modelo']}` en `{_corta(t['archivo'])}` | `{t['migracion']}` | {t['estado'].capitalize()} |")
    md += ["", "| Colección `<<table>>` | Campos | Se usa en |", "|---|---|---|"]
    for c in I.colecciones():
        md.append(f"| `{c['coleccion']}` | {', '.join(f'`{x}`' for x in c['campos'])} | `collab/mongo_stores.py` |")
    md.append("")

    base = I.linea_base()
    md += ["### 2.4.6 Plan de integración\n",
           f"El sistema se integra por **construcciones**: cada una agrega una parte, se acepta con sus pruebas y queda en la rama de integración antes de empezar la siguiente. "
           f"La línea base es el primer parcial, la etiqueta `{base['etiqueta']}` del repositorio (commit `{base['commit']}`, {base['fecha']}). Sobre ella el ciclo 4 se integró en cuatro "
           "construcciones, en este orden y por esta razón:\n",
           "| Orden | Construcción | Casos de uso | Subsistemas que toca | Por qué en ese orden |", "|---|---|---|---|---|"]
    cons = I.construcciones()
    for c in cons:
        subsistemas = ", ".join(D.NOMBRE_SUBSISTEMA[x] for x in c["subsistemas"])
        md.append(f"| {c['orden']} | {c['id']}: {c['nombre']} | {', '.join(c['casos'])} | {subsistemas} | {c['por_que']} |")
    md.append("")
    for c in cons:
        md += [f"**{c['id']}: {c['nombre']}.** Clases nuevas: {', '.join(f'`{x}`' for x in c['nuevas'])}. Clases que cambian: {', '.join(f'`{x}`' for x in c['cambian'])}.\n",
               "Se acepta cuando:\n"]
        md += [f"- {p}" for p in c["pruebas"]]
        md += ["", f"Commits ({len(c['commits'])}, del más viejo al más nuevo):\n", "| Commit | Fecha | Mensaje |", "|---|---|---|"]
        md += [f"| `{h}` | {f} | {m.replace('|', '/')} |" for h, f, m in c["commits"]]
        md.append("")
    md += ["Cada construcción se escribió con las pruebas primero: la prueba falla con el comportamiento nuevo, se escribe el código y la prueba pasa. Antes de cada commit una revisión "
           "automática del código lo compara con las reglas de `AGENTS.md`. La sección 2.6 comprueba, además, que el código coincide con el diseño.\n"]
    return "\n".join(md)


if __name__ == "__main__":
    import sys

    sys.stdout.write(generar())
