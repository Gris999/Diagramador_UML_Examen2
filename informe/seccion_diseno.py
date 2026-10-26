"""Sección 2.3 del informe: diseño (flujo de diseño del PUDS), generada de `modelo/diseno.py` y `modelo/realizaciones.py`.

Sigue el capítulo 9 del libro: diseño de la arquitectura (nodos, capas, subsistemas con interfaces, clases activas y mecanismos genéricos), clases de diseño
(con los nombres y operaciones del código, comprobados contra él), realización de cada caso de uso en el diseño (clases participantes y diagramas de
secuencia por escenario) y el diseño de los cambios que se programan después (C1 a C4).
"""

from modelo import analisis as A
from modelo import diseno as D
from modelo import realizaciones as R
from modelo import requisitos as Q
from seccion_requisitos import _uml_respaldo

CAPA = {"específica": "específica de la aplicación", "general": "general de la aplicación"}


def _lista(items):
    return "<br>".join(f"• {x}" for x in items) if items else "—"


def _clases(claves):
    return ", ".join(D.OBJETOS[k]["rotulo"] for k in claves)


def _tabla_nodos():
    filas = ["| Nodo | Tipo | Características | Qué corre | Conexión |", "|---|---|---|---|---|"]
    filas += [f"| {n} | {t} | {c} | {q} | {x} |" for n, t, c, q, x in D.NODOS]
    return "\n".join(filas) + "\n"


def _tabla_conexiones():
    filas = ["| Desde | Hacia | Protocolo |", "|---|---|---|"]
    filas += [f"| {a} | {b} | {p} |" for a, b, p in D.CONEXIONES]
    return "\n".join(filas) + "\n"


def _tabla_subsistemas():
    filas = ["| Subsistema | Capa | Traza al análisis | Lenguajes | Clases de diseño |", "|---|---|---|---|---|"]
    for s in D.SUBSISTEMAS:
        traza = f"Paquete «{A.NOMBRE_PAQUETE[s['traza']]}»" if s["traza"] else "Ninguno (carcasa de la interfaz web)"
        nombre = s["nombre"] + (" (de servicio)" if s["servicio"] else "")
        filas.append(f"| **{nombre}** | {CAPA.get(s['capa'], s['capa'])} | {traza} | {s['lenguajes']} | {_clases([o['clave'] for o in D.objetos_de(s['id'])])} |")
    return "\n".join(filas) + "\n"


def _tabla_software():
    filas = ["| Producto | Capa | Dónde | Para qué | Lenguaje |", "|---|---|---|---|---|"]
    filas += [f"| {n} | {c} | {d} | {p} | {l} |" for n, c, d, p, l in D.SOFTWARE_DEL_SISTEMA]
    return "\n".join(filas) + "\n"


def _tabla_interfaces():
    usuarios = D.usuarios_de_interfaces()
    filas = ["| Interfaz | La proporciona | La realizan | La usan | Operaciones | Para qué |", "|---|---|---|---|---|---|"]
    for i in D.INTERFACES:
        usan = ", ".join(D.NOMBRE_SUBSISTEMA[u] for u in sorted(usuarios[i["nombre"]])) or "—"
        nueva = " (nueva)" if i.get("nuevo") else ""
        filas.append(f"| **{i['nombre']}**{nueva} | {D.NOMBRE_SUBSISTEMA[i['sub']]} | {_clases(i['realiza'])} | {usan} | {', '.join(i['operaciones'])} | {i['motivo']} |")
    return "\n".join(filas) + "\n"


def _tabla_activas():
    filas = ["| Clase activa | Por qué y cómo |", "|---|---|"]
    filas += [f"| **{n}** | {d} |" for n, d in D.ACTIVAS]
    return "\n".join(filas) + "\n"


def _tabla_mecanismos():
    filas = ["| Requisito | Mecanismo | Solución | Clases |", "|---|---|---|---|"]
    for rec, nombre, titulo, texto, claves in D.MECANISMOS:
        filas.append(f"| {rec} | **{nombre}**: {titulo} | {texto} | {_clases(claves)} |")
    return "\n".join(filas) + "\n"


def _tabla_datos():
    filas = []
    for nombre, estado, cols in D.TABLAS:
        filas += [f"**{nombre}** ({estado}).\n", "| Columna | Tipo | Nota |", "|---|---|---|"] + [f"| {c} | {t} | {k or '—'} |" for c, t, k in cols] + [""]
    return "\n".join(filas)


def _tabla_colecciones():
    filas = []
    for nombre, cols in D.COLECCIONES:
        filas += [f"**{nombre}**.\n", "| Campo | Tipo | Nota |", "|---|---|---|"] + [f"| {c} | {t} | {k or '—'} |" for c, t, k in cols] + [""]
    return "\n".join(filas)


def _tabla_clases(sub):
    filas = ["| Clase de diseño | Tipo | Archivo | Realiza (clase del análisis) | Estado |", "|---|---|---|---|---|"]
    for o in D.objetos_de(sub):
        c = None if o["nuevo"] else D.C.buscar(o["archivo"], o["clase"])
        tipo = {"interface": "interfaz", "module": "módulo", "active": "clase activa", "entity": "modelo"}.get(o["est"], "clase")
        if c:
            tipo = f"{tipo} ({c['lenguaje']})"
        traza = ", ".join(A.CLASES[k]["nombre"] for k in D.analisis_de(o["clave"])) or "—"
        filas.append(f"| **{o['rotulo']}** | {tipo} | `{o['archivo']}` | {traza} | {'nueva (' + _cambio(o['clave']) + ')' if o['nuevo'] else 'existe'} |")
    return "\n".join(filas) + "\n"


def _cambio(clave):
    return next((c["id"] for c in D.CAMBIOS if clave in c["nuevas"]), "C1 a C4")


def _tabla_trazas():
    filas = ["| Clase del análisis | Clases de diseño que la realizan |", "|---|---|"]
    for p in A.PAQUETES:
        for c in A.clases_de_paquete(p["id"]):
            filas.append(f"| {c['nombre']} | {_clases([k for k, _ in D.TRAZA[c['clave']]])} |")
    return "\n".join(filas) + "\n"


def _cambios():
    md = []
    for c in D.CAMBIOS:
        md += [f"#### {c['id']}: {c['nombre']}\n",
               f"**Casos de uso:** {', '.join(c['casos'])}. **Requisitos:** {c['rf']}.\n",
               f"**Por qué.** {c['motivo']}\n",
               "**Decisiones de diseño.**\n"] + [f"- {x}" for x in c["decisiones"]] + [""]
        filas = ["| Clase de diseño | Archivo | Estado |", "|---|---|---|"]
        filas += [f"| **{D.OBJETOS[k]['rotulo']}** | `{D.OBJETOS[k]['archivo']}` | nueva |" for k in c["nuevas"]]
        filas += [f"| {D.OBJETOS[k]['rotulo']} | `{D.OBJETOS[k]['archivo']}` | cambia |" for k in c["cambian"]]
        md += ["\n".join(filas) + "\n", "**Pruebas previstas** (se escriben antes del código).\n"] + [f"- {x}" for x in c["pruebas"]] + [""]
    return md


HALLAZGOS = [
    ("«Generar modelo» y la voz llegaban a la IA por una ruta antigua", "`Diagram.generateFromPrompt` → `ChatbotService.generateDiagram` → `GenerateUMLView`: sin topes, sin contexto "
     "de la sala, sin registro de actividad y sin conversación; CU7 dice que todo pedido pasa por el control de la IA", "C1: pasa por `IaActionsService.request` (modo «Pedir cambio»); la voz solo transcribe"),
    ("El chat con la IA era privado", "`chat_history` y `_answer` filtran por participante; el docente pidió una sola instancia y una conversación de la sala", "C1"),
    ("Dos pedidos a la IA podían correr a la vez en una sala", "`CollaborationService.activeIaRequests` solo muestra el estado; el servidor no serializa", "C1: `TurnStore`"),
    ("La conversación y la actividad viven en tablas relacionales", "`ChatMessage` y `ActivityEvent` son documentos que solo se agregan, con `data` variable", "C3: puertos y adaptadores con MongoDB"),
    ("La vista del celular no avisa", "`FollowView` solo muestra el diagrama", "C2"),
    ("No hay un asistente que enseñe a usar la herramienta", "no existe ninguna clase para el caso de uso CU14", "C4"),
    ("La interfaz web junta botones de varios subsistemas", "`Diagram` y `SidePanel` llaman a la IA, al intercambio y a la generación a la vez", "Se reconoce como carcasa del editor: depende de todos y nadie depende de ella"),
    ("`views.py` reúne vistas de cuatro subsistemas", "respaldo, actividad, IA e intercambio en un solo módulo", "No se reorganiza antes de la entrega; el diseño las separa por función (deuda técnica documentada)"),
]


def generar():
    D.validar(analisis=A)
    D.validar_realizaciones(A)
    md = ["## 2.3 Diseño\n",
          "El diseño lleva el análisis a la realidad física: el lenguaje de programación, la red, los productos que se reutilizan y los requisitos no funcionales. "
          "Sus clases no son un dibujo aparte del código: cada clase y cada operación que aparece en este capítulo se comprueba contra el código fuente "
          "(la herramienta que genera este informe lee las clases de Python, TypeScript y Java del repositorio) y, si no existe, el informe no se genera. "
          "Lo único que no existe todavía son las clases de los cambios C1 a C4 (en amarillo en los diagramas), que se diseñaron aquí antes de programarse.\n",
          f"El modelo de diseño tiene {len(D.SUBSISTEMAS)} subsistemas, {len(D.OBJETOS)} clases de diseño, {len(D.INTERFACES)} interfaces y "
          f"{sum(len(r['escenarios']) for r in R.REALIZACIONES)} diagramas de secuencia que realizan las {len(R.REALIZACIONES)} colaboraciones del análisis.\n"]

    # ---- 2.3.1 arquitectura
    md += ["### 2.3.1 Diseño de la arquitectura\n",
           "#### Nodos y configuración de red\n",
           "La configuración física sigue el patrón de tres capas del libro: los clientes (navegadores), la lógica de la aplicación (Django y Spring Boot) y los "
           "datos (PostgreSQL, Redis y MongoDB), detrás de nginx con HTTPS. El tráfico de tiempo real usa WebSocket sobre el mismo puerto 443.\n",
           _uml_respaldo("di-despliegue", "Diagrama de despliegue"), _tabla_nodos(), _tabla_conexiones(),
           "#### Capas y subsistemas\n",
           "Los subsistemas de las dos capas superiores salen de los paquetes del análisis, con una traza a cada uno (9.5.1.2.1): un paquete de análisis, un "
           "subsistema de diseño. Se agrega la carcasa del editor, que el análisis no tiene porque es de la tecnología: reúne los botones y paneles de los demás "
           "subsistemas en la interfaz de Angular; depende de todos y nadie depende de ella. El software del sistema y la capa intermedia se tratan como "
           "subsistemas con interfaces explícitas, para poder cambiar de producto (por ejemplo, el proveedor de IA o la base de datos de la conversación).\n",
           _uml_respaldo("di-capas", "Diseño en capas"), _tabla_subsistemas(),
           "Las dependencias entre subsistemas son las del análisis (sin ciclos), sin las que ya están implícitas por otra ruta:\n",
           _uml_respaldo("di-subsistemas", "Subsistemas del diseño y sus dependencias"),
           "Software del sistema y capa intermedia:\n", _tabla_software(),
           "#### Interfaces entre subsistemas\n",
           "Un subsistema que tiene una dependencia que apunta hacia él proporciona una interfaz (9.5.1.2.4). Las interfaces nuevas son los puertos de la arquitectura "
           "hexagonal que el ingeniero nombró: las clases que los usan no saben si detrás hay PostgreSQL, MongoDB, Redis, Gemini u Ollama.\n",
           _tabla_interfaces(),
           "#### Clases activas\n", _tabla_activas(),
           "#### Mecanismos genéricos de diseño\n",
           "Cada requisito especial común del análisis (sección 2.2.1) se resuelve una sola vez con un mecanismo, y las clases lo usan:\n", _tabla_mecanismos(),
           "#### Vista C4\n",
           "Los tres niveles del modelo C4 que cubre este sistema: contexto, contenedores y componentes del servidor.\n",
           _uml_respaldo("c4-contexto", "Diagrama de contexto del sistema"), _uml_respaldo("di-c4-contenedores", "Diagrama de contenedor"),
           _uml_respaldo("di-c4-componentes", "Diagrama de componentes (C4)"),
           "#### Diseño de los datos\n",
           "Los datos relacionales (participantes, topes de uso, respaldo del diagrama) siguen en PostgreSQL. La conversación y la actividad se agregan y se consultan por "
           "sala y por tiempo, con un campo `data` que cambia según el tipo: con C3 pasan a MongoDB detrás de los puertos, y PostgreSQL queda como adaptador de respaldo.\n",
           _uml_respaldo("dd-postgres", "Modelo de datos relacional (PostgreSQL)"), _tabla_datos(),
           _uml_respaldo("dd-mongo", "Colecciones de MongoDB (C3)"), _tabla_colecciones()]

    # ---- 2.3.2 clases de diseño
    md += ["### 2.3.2 Clases de diseño por subsistema\n",
           "Cada clase usa el lenguaje de programación y su visibilidad (`+` pública, `#` protegida, `-` privada); los atributos y las operaciones son los del código. "
           "Las asociaciones del diagrama son referencias reales: inyección en el constructor, atributo o importación.\n"]
    for s in D.SUBSISTEMAS:
        md += [f"#### Subsistema {s['nombre']}\n", _uml_respaldo(f"dc-{s['id']}", f"Clases de diseño del subsistema {s['nombre']}"), _tabla_clases(s["id"])]
    md += ["#### Traza del análisis al diseño\n", "Cada clase del análisis se realiza con una o más clases de diseño:\n", _tabla_trazas()]

    # ---- 2.3.3 realizaciones
    md += ["### 2.3.3 Realización de los casos de uso: diseño\n",
           "Cada realización del diseño traza a una realización del análisis (9.3.3), con su flujo de eventos, las clases participantes y un diagrama de secuencia por "
           "escenario. Los mensajes son llamadas a operaciones reales: el diagrama sirve para leer el código y el código para comprobar el diagrama.\n"]
    for numero_ciclo, titulo, codigos in Q.CICLOS:
        md.append(f"#### Ciclo de vida #{numero_ciclo}\n")
        for cu in codigos:
            md.append(f"**{cu}: {Q.CASOS[cu]['nombre']}.**\n")
            for col in A.colaboraciones_de(cu):
                r = next(x for x in R.REALIZACIONES if x["col"] == col["id"])
                md += [f"**{col['id']}: {col['nombre']}.** Traza: realización del análisis {col['id']}.\n", "Flujo de eventos del diseño:\n"]
                md += [f"{i}. {t}" for i, t in enumerate(r["flujo"], 1)] + [""]
                md += ["Clases de diseño participantes:\n", _uml_respaldo(f"dp-{col['id']}", f"{col['id']}: clases de diseño participantes")]
                for e in r["escenarios"]:
                    md += [f"Escenario {e['id']} — {e['nombre']}:\n", _uml_respaldo(f"sq-{col['id']}-{e['id']}", f"{col['id']} ({e['id']}): {e['nombre']}")]
                if r["implementacion"]:
                    md += ["Requisitos de implementación:\n"] + [f"- {x}" for x in r["implementacion"]] + [""]

    # ---- 2.3.4 cambios
    md += ["### 2.3.4 Diseño de los cambios de este parcial\n",
           "Los cambios C1 a C4 se diseñan antes de programarse: aquí queda lo que se va a construir y cómo se va a probar, y el código se escribe para cumplirlo "
           "(la prueba falla primero y después se programa).\n"] + _cambios()

    # ---- 2.3.5 hallazgos
    md += ["### 2.3.5 Lo que el cotejo entre el documento y el código encontró\n",
           "Al verificar cada clase y cada mensaje contra el código, aparecieron diferencias entre lo que decían los casos de uso y lo que hacía el software. "
           "Cada una se resolvió con un cambio de diseño o se documenta como deuda:\n",
           "| Hallazgo | Evidencia | Qué se decidió |", "|---|---|---|"]
    md += [f"| {h} | {e} | {d} |" for h, e, d in HALLAZGOS]
    md.append("")
    return "\n".join(md)
