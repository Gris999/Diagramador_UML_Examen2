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
    """Sección 2.4. Misma estructura que los documentos de referencia: diagrama de componentes y diagrama de subsistemas. El detalle de la implementación
    (alcance, tablas de subsistemas, componentes, ejecutables, tablas y colecciones, plan de integración) está en el Anexo E (`generar_anexo`) y los
    estándares de codificación en el Anexo D (`estandares`)."""
    I.validar()
    subs = I.subsistemas()
    md = ["## 2.4 Flujo de trabajo: implementación\n",
          "### 2.4.1 Diagrama de componentes\n"]
    for s in subs:
        md += [f"**{s['nombre']}.**\n", _uml_respaldo(f"im-{s['id']}", f"Componentes del subsistema de implementación {s['nombre']}")]
    md += ["### 2.4.2 Diagrama de subsistemas\n", _uml_respaldo("di-subsistemas", "Subsistemas del diseño y sus dependencias")]
    return "\n".join(md)


def estandares():
    """Anexo D: justificación del estándar de codificación de cada pila, como en los informes de referencia, y las reglas comunes del proyecto."""
    I.validar()
    md = ["## Estándar de codificación en Django REST Framework\n",
          "El backend de Django está dividido en dos aplicaciones independientes: `collab` (la sala, los roles, el tiempo real, la conversación y la actividad) y `uml_api` "
          "(el diagrama, la IA, la ayuda y las exportaciones). Cada una tiene sus modelos, vistas, servicios y pruebas, y sus cambios no obligan a tocar la otra.\n",
          "Las principales características de este estándar son:\n",
          "- **Modularidad:** una aplicación por responsabilidad; las vistas son delgadas y la lógica vive en servicios (`uml_api/services`) y en módulos con un solo propósito "
          "(`collab/roles.py`, `collab/limits.py`, `collab/turn.py`).",
          "- **Reutilización por puertos y adaptadores:** `collab/ports.py` declara los puertos (`ActivityStore`, `ConversationStore`, `TurnStore`, `RateLimiter`) y cada uno tiene "
          "adaptadores intercambiables (PostgreSQL, MongoDB, Redis y memoria) que se eligen con una variable de entorno.",
          "- **Separación de responsabilidades:** modelos y migraciones, vistas de la API REST, consumidores de WebSocket (`collab/consumers.py`) y servicios están en archivos distintos.",
          "- **Escalabilidad:** el estado compartido está en Redis y en la base de datos, no en la memoria de un proceso, de modo que se pueden agregar procesos sin cambiar el código.",
          "- **Mantenibilidad:** cada comportamiento tiene su prueba junto a la aplicación (`tests/`) y los nombres siguen las convenciones de Python (`snake_case` para funciones y módulos, `PascalCase` para clases).",
          "",
          "## Estándar de codificación en Angular\n",
          "El frontend se organiza con los componentes independientes de Angular 20 (sin `NgModule`) y servicios inyectables agrupados por dominio, lo que mantiene la interfaz separada de la lógica.\n",
          "Las principales características de este estándar son:\n",
          "- **Modularidad:** cada panel de la interfaz es un componente propio en `src/app` (el lienzo, el chat, la actividad, los participantes, la ayuda, «Mis diagramas») y los servicios "
          "están agrupados en `src/services` por dominio (diagrama, colaboración, IA, importación, exportación, autenticación).",
          "- **Reutilización de componentes:** la lógica que no depende de la pantalla está en utilidades puras (`*.util.ts`) que varios servicios comparten, por ejemplo las que dibujan las rutas de las "
          "relaciones o las del holograma de la IA.",
          "- **Inyección de dependencias:** los servicios son `@Injectable` y los componentes los reciben por inyección, así que la autenticación, la comunicación con la API y la colaboración "
          "se escriben una sola vez.",
          "- **Escalabilidad:** el estado de cada pantalla se maneja con señales (`signal`), que actualizan solo lo que cambió.",
          "- **Mantenibilidad:** cada servicio y cada utilidad tienen su archivo `*.spec.ts` al lado, que se ejecuta con Karma y Jasmine.",
          "",
          "## Estándar de codificación en Spring Boot\n",
          "El generador de código es un proyecto de Spring Boot 3.5 con Java 21 que sigue la arquitectura en capas que ofrece el framework y que produce proyectos con la misma estructura.\n",
          "Las principales características de este estándar son:\n",
          "- **Modularidad en capas:** paquetes separados para `controller`, `service`, `entity` y `configuration`; las plantillas de los proyectos que genera están aparte, en `resources/templates` (Mustache).",
          "- **Reutilización de componentes:** las clases del paquete `service` (`ProjectGenerator`, `PostmanCollectionGenerator`, `JsonNormalizer`, `NamingUtil`) se invocan desde un solo controlador y comparten los mismos nombres de clases y relaciones.",
          "- **Inyección de dependencias:** las anotaciones de Spring (`@Service`, `@RestController`, `@Configuration`) mantienen el código desacoplado.",
          "- **Escalabilidad:** agregar un tipo de relación o de archivo generado es agregar una plantilla y un método de servicio, sin tocar el resto.",
          "- **Mantenibilidad:** se usa el Maven Wrapper del proyecto (no se exige Maven instalado) y la compilación del proyecto generado se prueba con `./mvnw test`.",
          "",
          "## Reglas comunes del proyecto\n",
          "Además del estándar de cada pila, el repositorio tiene reglas de trabajo para todo el equipo en el archivo `AGENTS.md`:\n"]
    md += [f"- {e}" for e in I.ESTANDARES]
    md.append("")
    return "\n".join(md)


def generar_anexo():
    """Detalle de la implementación para el Anexo E (títulos de nivel 2 y 3; el generador del informe los numera 6.5.n): alcance, subsistemas, componentes con su
    traza al diseño, ejecutables, tablas y colecciones y plan de integración."""
    resumen = I.validar()
    subs = I.subsistemas()
    md = []

    md += ["## Implementación: alcance\n",
           f"El sistema implementado tiene **{resumen['subsistemas']} subsistemas de implementación**, **{resumen['componentes']} componentes** de código fuente y unas "
           f"**{miles(resumen['lineas'])} líneas** (sin contar las pruebas, que se describen en la sección 2.5 y en el Anexo F), escritas en TypeScript (Angular 20 con JointJS), Python 3.12 (Django 5, "
           "Django REST Framework y Channels) y Java 21 (Spring Boot 3.5). Los estándares de codificación están en el Anexo D.\n"]

    md += ["## Implementación: subsistemas\n",
           "Cada subsistema de diseño (sección 2.3) tiene un subsistema de implementación con el mismo nombre y las mismas fronteras, en una o varias carpetas del repositorio. "
           "La tabla muestra dónde vive cada uno.\n",
           "| Subsistema | Capa | Carpetas | Componentes | Líneas |", "|---|---|---|---|---|"]
    for s in subs:
        carpetas = "<br>".join(f"`{_corta(c)}`" for c in s["carpetas"])
        md.append(f"| {s['nombre']} | {s['capa'].capitalize()} | {carpetas} | {len(s['componentes'])} | {miles(s['lineas'])} |")
    md += ["", "Las rutas se dan relativas a `front_generador_bd/src/` (Angular), `back_generador_bd/` (Django) o `back_generator_uml/src/main/java/generator_uml/back_generator_uml/` (Spring Boot), "
           "según el tipo de archivo.\n"]

    md += ["## Implementación: componentes y su traza al diseño\n",
           "Un componente es un archivo de código fuente (`<<file>>`). La traza dice qué clases de diseño de la sección 2.3 implementa: así, desde una clase del diseño se llega al "
           "archivo que la contiene y al revés. Los nombres entre `< >` son módulos de funciones (no clases).\n"]
    for s in subs:
        md += [f"### {s['nombre']}\n",
               "| Componente `<<file>>` | Lenguaje | Implementa (clases de diseño) | Líneas |", "|---|---|---|---|"]
        for c in s["componentes"]:
            clases = ", ".join(f"`{x}`" for x in c["clases"])
            md.append(f"| `{_corta(c['ruta'])}` | {c['lenguaje']} | {clases} | {miles(c['lineas'])} |")
        md.append("")

    filas, compose = I.ejecutables()
    md += ["## Implementación: ejecutables y nodos\n",
           "Los ejecutables (`<<executable>>`) son los contenedores de Docker Compose; cada uno se asigna a un nodo del modelo de despliegue (sección 2.3.2.1). "
           "Los archivos `docker-compose.app.yml` (aplicación) y `docker-compose.db.yml` (bases de datos) los definen, y el modelo coincide con ellos: cada contenedor "
           "del modelo está en los archivos y cada contenedor de los archivos está en el modelo (`pgadmin` es solo una herramienta de desarrollo). "
           "`mongo_db` es opcional (se levanta con el perfil `mongo`) y en el servidor de AWS no corre: desde el 2026-11-04 la actividad y la conversación están en MongoDB Atlas.\n",
           "| Ejecutable `<<executable>>` | Se construye de | Puertos publicados | Archivo | Función |", "|---|---|---|---|---|"]
    for f in filas:
        c = f["compose"]
        puertos = ", ".join(c["puertos"]) if c["puertos"] else "ninguno (red interna)"
        md.append(f"| `{f['nombre']}` | {c['origen']} | {puertos} | `{c['archivo']}` | {f['funcion']} |")
    md.append("")

    md += ["## Implementación: tablas y colecciones\n",
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
    md += ["## Implementación: plan de integración\n",
           f"El sistema se integra por **construcciones**: cada una agrega una parte, se acepta con sus pruebas y queda en la rama de integración antes de empezar la siguiente. "
           f"La línea base es la etiqueta `{base['etiqueta']}` del repositorio (commit `{base['commit']}`, {base['fecha']}). Sobre ella el ciclo 4 se integró en cuatro "
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
           "automática del código lo compara con las reglas del proyecto (`AGENTS.md`). El Anexo G comprueba, además, que el código coincide con el diseño.\n"]
    return "\n".join(md)


if __name__ == "__main__":
    import sys

    sys.stdout.write(generar())
