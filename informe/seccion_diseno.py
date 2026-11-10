"""Sección 2.3 del informe: diseño (flujo de diseño del PUDS), generada de `modelo/diseno.py` y `modelo/realizaciones.py`.

Sigue el capítulo 9 del libro: diseño de la arquitectura (nodos, capas, subsistemas con interfaces, clases activas y mecanismos genéricos), clases de diseño
(con los nombres y operaciones del código, comprobados contra él), realización de cada caso de uso en el diseño (clases participantes y diagramas de
secuencia por escenario).
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
        filas.append(f"| **{i['nombre']}** | {D.NOMBRE_SUBSISTEMA[i['sub']]} | {_clases(i['realiza'])} | {usan} | {', '.join(i['operaciones'])} | {i['motivo']} |")
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
    for nombre, _estado, cols in D.TABLAS:
        filas += [f"**{nombre}**.\n", "| Columna | Tipo | Nota |", "|---|---|---|"] + [f"| {c} | {t} | {k or '—'} |" for c, t, k in cols] + [""]
    return "\n".join(filas)


def _tabla_colecciones():
    filas = []
    for nombre, cols in D.COLECCIONES:
        filas += [f"**{nombre}**.\n", "| Campo | Tipo | Nota |", "|---|---|---|"] + [f"| {c} | {t} | {k or '—'} |" for c, t, k in cols] + [""]
    return "\n".join(filas)


def _tabla_clases(sub):
    filas = ["| Clase de diseño | Tipo | Archivo | Realiza (clase del análisis) |", "|---|---|---|---|"]
    for o in D.objetos_de(sub):
        c = None if o["nuevo"] else D.C.buscar(o["archivo"], o["clase"])
        tipo = {"interface": "interfaz", "module": "módulo", "active": "clase activa", "entity": "modelo"}.get(o["est"], "clase")
        if c:
            tipo = f"{tipo} ({c['lenguaje']})"
        traza = ", ".join(A.CLASES[k]["nombre"] for k in D.analisis_de(o["clave"])) or "—"
        filas.append(f"| **{o['rotulo']}** | {tipo} | `{o['archivo']}` | {traza} |")
    return "\n".join(filas) + "\n"


def _tabla_trazas():
    filas = ["| Clase del análisis | Clases de diseño que la realizan |", "|---|---|"]
    for p in A.PAQUETES:
        for c in A.clases_de_paquete(p["id"]):
            filas.append(f"| {c['nombre']} | {_clases([k for k, _ in D.TRAZA[c['clave']]])} |")
    return "\n".join(filas) + "\n"


def generar():
    """Sección 2.3. Misma estructura que los documentos de referencia: patrón C4 (contexto, contenedor, componentes y código), diseño de la arquitectura
    (físico y lógico) y diagramas de secuencia por ciclo de vida. El resto del diseño (nodos, subsistemas, mecanismos, clases de diseño y detalle de las
    realizaciones) está en el Anexo E (`generar_anexo`)."""
    D.validar(analisis=A)
    D.validar_realizaciones(A)
    md = ["## 2.3 Flujo de trabajo: diseño\n"]

    # ---- 2.3.1 patrón de desarrollo C4 (el nivel de código es el diseño de datos: las clases persistentes y su mapeo)
    md += ["### 2.3.1 Patrón de desarrollo C4\n",
           "#### 2.3.1.1 Diagrama de contexto del sistema\n", _uml_respaldo("c4-contexto", "Diagrama de contexto del sistema"),
           "#### 2.3.1.2 Diagrama de contenedor\n", _uml_respaldo("di-c4-contenedores", "Diagrama de contenedor"),
           "#### 2.3.1.3 Diagrama de componentes\n", _uml_respaldo("di-c4-componentes", "Diagrama de componentes (C4)"),
           "#### 2.3.1.4 Diagrama de código\n",
           _uml_respaldo("dd-postgres", "Modelo de datos relacional (PostgreSQL)"), _uml_respaldo("dd-mongo", "Colecciones de MongoDB"),
           "Mapeo de las clases persistentes a tablas de PostgreSQL:\n", _tabla_datos(),
           "Mapeo a colecciones de MongoDB:\n", _tabla_colecciones()]

    # ---- 2.3.2 diseño de la arquitectura
    md += ["### 2.3.2 Diseño de la arquitectura\n",
           "#### 2.3.2.1 Diseño físico (diagrama de despliegue)\n", _uml_respaldo("di-despliegue", "Diagrama de despliegue"),
           "#### 2.3.2.2 Diseño lógico: diagrama de paquete organizado en capas\n", _uml_respaldo("di-capas", "Diseño en capas")]

    # ---- 2.3.3 diagramas de secuencia por ciclo de vida
    md += ["### 2.3.3 Diagrama de secuencia\n"]
    for numero_ciclo, titulo, codigos in Q.CICLOS:
        md.append(f"#### Ciclo de vida #{numero_ciclo}\n")
        for cu in codigos:
            for col in A.colaboraciones_de(cu):
                r = next(x for x in R.REALIZACIONES if x["col"] == col["id"])
                md += [_uml_respaldo(f"sq-{col['id']}-{e['id']}", f"{cu} - {e['nombre']}") for e in r["escenarios"]]
    return "\n".join(md)


def generar_anexo():
    """Detalle del diseño para el Anexo E (títulos de nivel 2 y 3; el generador del informe los numera 6.5.n): nodos y conexiones, subsistemas e
    interfaces, clases activas y mecanismos, clases de diseño por subsistema y detalle de las realizaciones."""
    D.validar(analisis=A)
    D.validar_realizaciones(A)
    md = ["## Diseño: nodos y conexiones\n",
          "La configuración física sigue el patrón de tres capas: los clientes (navegadores), la lógica de la aplicación (Django y Spring Boot) y los datos (PostgreSQL, Redis y MongoDB), "
          "detrás de nginx con HTTPS. El tráfico de tiempo real usa WebSocket sobre el mismo puerto 443. El diagrama dibuja `mongo_db` como un contenedor del servidor, que es la opción "
          "de diseño (se levanta con el perfil `mongo` de Docker Compose); en el servidor de AWS ese contenedor no corre, porque la actividad y la conversación se guardan en MongoDB Atlas, "
          "un servicio gestionado en la nube al que solo puede entrar la IP del servidor.\n",
          _tabla_nodos(), _tabla_conexiones(),
          "## Diseño: subsistemas e interfaces\n",
          "Los subsistemas de las dos capas superiores salen de los paquetes del análisis, con una traza a cada uno: un paquete de análisis, un subsistema de diseño. Se agrega la carcasa "
          "del editor, que el análisis no tiene porque es de la tecnología: reúne los botones y paneles de los demás subsistemas en la interfaz de Angular; depende de todos y nadie "
          "depende de ella. El software del sistema y la capa intermedia se tratan como subsistemas con interfaces explícitas, para poder cambiar de producto (por ejemplo, el proveedor "
          "de IA o la base de datos de la conversación).\n",
          _tabla_subsistemas(),
          "Las dependencias entre subsistemas son las del análisis (sin ciclos), sin las que ya están implícitas por otra ruta:\n",
          _uml_respaldo("di-subsistemas", "Subsistemas del diseño y sus dependencias"),
          "Software del sistema y capa intermedia:\n", _tabla_software(),
          "Un subsistema que tiene una dependencia que apunta hacia él proporciona una interfaz. Las interfaces son los puertos de la arquitectura hexagonal: las clases que los usan "
          "no saben si detrás hay PostgreSQL, MongoDB, Redis, Gemini u Ollama.\n",
          _tabla_interfaces(),
          "## Diseño: clases activas y mecanismos genéricos\n", _tabla_activas(),
          "Cada requisito especial común del análisis (Anexo E, requisitos especiales comunes) se resuelve una sola vez con un mecanismo, y las clases lo usan:\n", _tabla_mecanismos()]

    md += ["## Diseño: clases de diseño por subsistema\n",
           "Cada clase usa el lenguaje de programación y su visibilidad (`+` pública, `#` protegida, `-` privada); los atributos y las operaciones son los del código. "
           "Las asociaciones del diagrama son referencias reales: inyección en el constructor, atributo o importación. Cada clase y cada operación que aparece en este capítulo se "
           "comprueba contra el código fuente (la herramienta que genera este informe lee las clases de Python, TypeScript y Java del repositorio) y, si no existe, el informe no se genera.\n"]
    for s in D.SUBSISTEMAS:
        md += [f"### Subsistema {s['nombre']}\n", _uml_respaldo(f"dc-{s['id']}", f"Clases de diseño del subsistema {s['nombre']}"), _tabla_clases(s["id"])]
    md += ["### Traza del análisis al diseño\n", "Cada clase del análisis se realiza con una o más clases de diseño:\n", _tabla_trazas()]

    md += ["## Diseño: detalle de la realización de los casos de uso\n",
           "Cada realización del diseño traza a una realización del análisis, con su flujo de eventos, las clases participantes y los requisitos de implementación. Los mensajes de "
           "los diagramas de secuencia son llamadas a operaciones reales: el diagrama sirve para leer el código y el código para comprobar el diagrama.\n"]
    for numero_ciclo, titulo, codigos in Q.CICLOS:
        md.append(f"### Ciclo de vida #{numero_ciclo}\n")
        for cu in codigos:
            md.append(f"**{cu}: {Q.CASOS[cu]['nombre']}.**\n")
            for col in A.colaboraciones_de(cu):
                r = next(x for x in R.REALIZACIONES if x["col"] == col["id"])
                md += [f"**{col['id']}: {col['nombre']}.** Traza: realización del análisis {col['id']}.\n", "Flujo de eventos del diseño:\n"]
                md += [f"{i}. {t}" for i, t in enumerate(r["flujo"], 1)] + [""]
                md += ["Clases de diseño participantes:\n", _uml_respaldo(f"dp-{col['id']}", f"{col['id']}: clases de diseño participantes")]
                if r["implementacion"]:
                    md += ["Requisitos de implementación:\n"] + [f"- {x}" for x in r["implementacion"]] + [""]
    return "\n".join(md)
