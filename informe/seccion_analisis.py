"""Sección 2.2 del informe: análisis (flujo de análisis del PUDS), generada de `modelo/analisis.py`.

Sigue el capítulo 8 del libro: análisis de la arquitectura (paquetes, dependencias y requisitos especiales comunes), clases del
análisis por paquete (responsabilidades, atributos, relaciones y requisitos especiales) y realización de cada caso de uso (flujo de sucesos,
clases participantes y diagrama de colaboración). Las responsabilidades de cada clase salen de los mensajes que recibe en las colaboraciones.
"""

from modelo import analisis as A
from modelo import requisitos as R
from seccion_requisitos import _uml_respaldo

ETIQUETA_EST = {"interfaz": "«boundary» (interfaz)", "control": "«control»", "entidad": "«entity» (entidad)"}
NOMBRE_TIPO = {"paquete": "Paquete", "servicio": "Paquete de servicio"}


def _lista(items):
    return "<br>".join(f"• {x}" for x in items) if items else "—"


def _numerada(pasos):
    return [f"{i}. {p}" for i, p in enumerate(pasos, 1)]


def _casos(ids):
    return ", ".join(ids) if ids else "—"


def _responsabilidades(clave):
    items = [f"{texto} [{', '.join(cols)}]" for texto, cols in A.responsabilidades(clave)]
    return _lista(items)


def _atributos(c):
    return _lista([f"{n}: {t}" for n, t in c["atrib"]])


def _relaciones(clave):
    """Asociaciones de una clase, cada una como la frase que la nombra y su multiplicidad (de origen a destino)."""
    textos = []
    for origen, destino, nombre, ma, mb, tipo in A.relaciones_de(clave):
        verbo = {"comp": "se compone de", "agr": "agrupa a"}.get(tipo, nombre)
        textos.append(f"{A.CLASES[origen]['nombre']} {verbo} {A.CLASES[destino]['nombre']} [{ma} a {mb}]")
    return _lista(textos)


def _tabla_paquetes():
    filas = ["| Paquete | Capa | Casos de uso | Por qué se agrupan |", "|---|---|---|---|"]
    for p in A.PAQUETES:
        capa = "general" if p["capa"] == "general" else "aplicación"
        tipo = f"paquete de servicio de {A.NOMBRE_PAQUETE[p['padre']]}" if p["padre"] else "paquete"
        filas.append(f"| **{p['nombre']}**<br>{tipo} | {capa} | {_casos(p['casos'])} | {p['por_que']} |")
    return "\n".join(filas) + "\n"


def _dependencias():
    filas = ["| Paquete | Depende de | Por qué |", "|---|---|---|"]
    motivos = {}
    for col in A.COLABORACIONES:
        for origen, destino, _ in col["mensajes"]:
            if origen in A.CLASES and destino in A.CLASES:
                a, b = A._raiz(A.CLASES[origen]["paquete"]), A._raiz(A.CLASES[destino]["paquete"])
                if a != b:
                    motivos.setdefault((a, b), set()).add(f"{A.CLASES[origen]['nombre']} usa {A.CLASES[destino]['nombre']}")
    for a, b in A.DEPENDENCIAS:
        ejemplos = sorted(motivos[(a, b)])
        filas.append(f"| {A.NOMBRE_PAQUETE[a]} | {A.NOMBRE_PAQUETE[b]} | {'; '.join(ejemplos[:2])}{'…' if len(ejemplos) > 2 else ''} |")
    return "\n".join(filas) + "\n"


def _ficha_clase(c):
    """Ficha de una clase del análisis (PUDS 8.4.2): responsabilidades, atributos, relaciones y requisitos especiales."""
    filas = [("CLASE", f"{c['nombre']} {ETIQUETA_EST[c['est']]}"),
             ("DESCRIPCIÓN", c["desc"]),
             ("RESPONSABILIDADES", _responsabilidades(c["clave"])),
             ("ATRIBUTOS", _atributos(c)),
             ("RELACIONES", _relaciones(c["clave"])),
             ("REQUISITOS ESPECIALES", _lista(c["espec"])),
             ("EN EL SOFTWARE", c["donde"])]
    return "\n".join(["| | |", "|---|---|"] + [f"| **{k}** | {v} |" for k, v in filas]) + "\n"


def generar():
    """Sección 2.2. Misma estructura que el documento de referencia: análisis de la arquitectura (identificar paquetes, relacionar paquetes y casos de uso,
    vista del paquete), análisis de casos de uso (diagramas de comunicación), análisis de clases y análisis de paquetes."""
    A.validar(R)
    raices = [p for p in A.PAQUETES if not p["padre"]]
    con_casos = [p for p in raices if any(q["casos"] for q in [p] + [s for s in A.PAQUETES if s["padre"] == p["id"]])]
    md = ["## 2.2 Flujo de trabajo: análisis\n"]

    # ---- 2.2.1 análisis de la arquitectura
    md += ["### 2.2.1 Análisis de la arquitectura\n",
           "#### 2.2.1.1 Identificar paquetes\n", _uml_respaldo("an-identificar", "Identificar paquetes del análisis"),
           "#### 2.2.1.2 Relacionar paquetes y casos de uso\n"]
    md += [_uml_respaldo(f"an-relacion-{p['id']}", f"Paquete {p['nombre']} y sus casos de uso") for p in con_casos]
    md += ["#### 2.2.1.3 Vista del paquete\n"]
    md += [_uml_respaldo(f"an-vista-{p['id']}", f"Vista del paquete {p['nombre']}") for p in con_casos]
    md += ["#### 2.2.1.4 Requisitos especiales comunes\n",
           "Los requisitos que atraviesan varias clases se identifican aquí para que las realizaciones y las clases los citen y el diseño los resuelva una sola vez.\n",
           "| ID | Requisito especial | Qué exige |", "|---|---|---|"]
    md += [f"| {i} | {n} | {d} |" for i, n, d in A.ESPECIALES_COMUNES]
    md += ["",
           "Características de la persistencia (rango de tamaño, volumen, período, frecuencia de actualización y fiabilidad):\n",
           "| Clase | Rango de tamaño | Volumen | Período | Frecuencia de actualización | Fiabilidad |", "|---|---|---|---|---|---|"]
    md += [f"| {' | '.join(fila)} |" for fila in A.PERSISTENCIA]
    md.append("")

    # ---- 2.2.2 análisis de casos de uso
    md += ["### 2.2.2 Análisis de casos de uso\n", "#### 2.2.2.1 Diagramas de comunicación\n"]
    for numero_ciclo, titulo, codigos in R.CICLOS:
        md.append(f"##### Ciclo de vida #{numero_ciclo}\n")
        for cu in codigos:
            for col in A.colaboraciones_de(cu):
                md += [f"**{col['id']}: {col['nombre']}.**\n", _uml_respaldo(f"com-{col['id']}", f"{col['id']}: {col['nombre']}")]
    md += ["#### 2.2.2.2 Flujos de sucesos y clases participantes\n",
           "Cada caso de uso se realiza con una o más colaboraciones, una por cada flujo diferenciado. Todas empiezan con un mensaje de un actor a una clase de interfaz; "
           "los mensajes dicen para qué un objeto invoca a otro (no son operaciones) y los enlaces son instancias de las asociaciones del diagrama de clases participantes.\n"]
    for numero_ciclo, titulo, codigos in R.CICLOS:
        md.append(f"##### Ciclo de vida #{numero_ciclo}\n")
        for cu in codigos:
            md.append(f"**{cu}: {R.CASOS[cu]['nombre']}.**\n")
            for col in A.colaboraciones_de(cu):
                md.append(f"**{col['id']}: {col['nombre']}.**\n")
                if col["reutiliza"] and col["id"] == "COL-08":
                    md.append(f"Colaboración reutilizable: la usan las realizaciones de {' y '.join(col['reutiliza'])}.\n")
                elif col["reutiliza"]:
                    md.append(f"Reutiliza {', '.join(col['reutiliza'])}.\n")
                if col["extiende"]:
                    md.append(f"Es el punto de extensión de {cu}: ejecuta la realización de {col['extiende']} (COL-08 y COL-09).\n")
                md += ["Flujo de sucesos del análisis:\n"] + _numerada(col["flujo"]) + [""]
                md += ["Clases participantes:\n", _uml_respaldo(f"acp-{col['id']}", f"{col['id']}: clases participantes")]
                if col["especiales"]:
                    md += ["Requisitos especiales de la realización:\n"] + [f"- {e}" for e in col["especiales"]] + [""]

    # ---- 2.2.3 análisis de clases
    md += ["### 2.2.3 Análisis de clases\n",
           "Cada paquete se muestra con sus clases y atributos (que llevan tipos conceptuales, no de un lenguaje). Las responsabilidades de cada ficha son las de las colaboraciones, "
           "que se citan entre corchetes.\n"]
    for p in A.PAQUETES:
        if p["padre"]:
            continue
        servicios = [q for q in A.PAQUETES if q["padre"] == p["id"]]
        md += [f"#### Paquete {p['nombre']}\n", _uml_respaldo(f"an-pkg-{p['id']}", f"Clases del análisis del paquete {p['nombre']}")]
        md += [_ficha_clase(c) for c in A.clases_de_paquete(p["id"])]
        for q in servicios:
            md += [f"**Paquete de servicio {q['nombre']}.**\n"]
            md += [_ficha_clase(c) for c in A.clases_de_paquete(q["id"])]

    # ---- 2.2.4 análisis de paquetes
    md += ["### 2.2.4 Análisis de paquetes\n", _uml_respaldo("an-dependencias", "Dependencias entre los paquetes del análisis")]
    return "\n".join(md)
