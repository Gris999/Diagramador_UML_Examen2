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
             ("EN EL SOFTWARE", f"{c['estado'].capitalize()}: {c['donde']}")]
    return "\n".join(["| | |", "|---|---|"] + [f"| **{k}** | {v} |" for k, v in filas]) + "\n"


def _tabla_trazabilidad():
    filas = ["| Clase del análisis | Estereotipo | Paquete | Estado | Dónde vive en el software |", "|---|---|---|---|---|"]
    for p in A.PAQUETES:
        for c in A.clases_de_paquete(p["id"]):
            filas.append(f"| {c['nombre']} | {c['est']} | {p['nombre']} | {c['estado']} | {c['donde']} |")
    return "\n".join(filas) + "\n"


def generar():
    A.validar(R)
    md = ["## 2.2 Análisis\n",
          "El análisis refina cada caso de uso en términos de clases y objetos que colaboran, sin pensar todavía en el lenguaje ni en las "
          "tecnologías: se ocupa de los requisitos funcionales y deja los demás, que aquí se llaman requisitos especiales, para el diseño. "
          f"El modelo de análisis tiene {len(A.PAQUETES)} paquetes (dos de ellos de servicio), {len(A.CLASES)} clases y "
          f"{len(A.COLABORACIONES)} colaboraciones que realizan los {len(R.CASOS)} casos de uso. Cada clase es de interfaz (lo que depende de "
          "un actor), de control (la coordinación de un caso de uso) o de entidad (la información que perdura), y sus responsabilidades no se escribieron a "
          "mano: son los mensajes que recibe en las colaboraciones. Como el modelo manda y el software debe seguirlo, la sección 2.2.4 dice dónde "
          "vive hoy cada clase en el código y qué clases son nuevas o cambian en este parcial.\n"]

    # ---- 2.2.1 arquitectura
    md += ["### 2.2.1 Análisis de la arquitectura\n",
           "#### Paquetes del análisis\n",
           "Los paquetes agrupan los casos de uso por el actor que los usa, por el proceso del que forman parte o por la relación entre ellos "
           "(generalización o extensión). Las clases de entidad que casi todos necesitan se extraen a un paquete propio (el núcleo de la sala) y "
           "lo opcional va en paquetes de servicio, que se entregan o se quitan enteros.\n",
           _tabla_paquetes(),
           _uml_respaldo("an-paquetes", "Paquetes del análisis y casos de uso que realizan"),
           "#### Dependencias entre paquetes y capas\n",
           "Las dependencias salen de los mensajes y asociaciones de las colaboraciones: un paquete depende de otro si alguna de sus clases usa una "
           "clase del otro. Se buscó cohesión alta y acoplamiento bajo, y no hay ciclos: el modelo se ordena en una capa general (el núcleo de la "
           "sala y la edición del diagrama) y una capa específica de la aplicación que descansa sobre ella. Los paquetes de servicio dependen "
           "como parte del paquete que los contiene.\n",
           _dependencias(),
           _uml_respaldo("an-dependencias", "Dependencias entre los paquetes del análisis"),
           "#### Requisitos especiales comunes\n",
           "El arquitecto identifica los requisitos que atraviesan varias clases para que las realizaciones y las clases los citen y el diseño "
           "los resuelva una sola vez.\n",
           "| ID | Requisito especial | Qué exige |", "|---|---|---|"]
    md += [f"| {i} | {n} | {d} |" for i, n, d in A.ESPECIALES_COMUNES]
    md += ["",
           "Características de la persistencia (rango de tamaño, volumen, período, frecuencia de actualización y fiabilidad), tomadas de lo que "
           "el software ya hace:\n",
           "| Clase | Rango de tamaño | Volumen | Período | Frecuencia de actualización | Fiabilidad |", "|---|---|---|---|---|---|"]
    md += [f"| {' | '.join(fila)} |" for fila in A.PERSISTENCIA]
    md.append("")

    # ---- 2.2.2 clases por paquete
    md += ["### 2.2.2 Clases del análisis por paquete\n",
           "Cada paquete se muestra con sus clases y atributos (que llevan tipos conceptuales, no de un lenguaje); las asociaciones con "
           "multiplicidad están en el diagrama de clases participantes de cada realización (sección 2.2.3) y en la ficha de cada clase. Las "
           "responsabilidades de cada ficha son las de las colaboraciones, que se citan entre corchetes.\n"]
    for p in A.PAQUETES:
        if p["padre"]:
            continue
        servicios = [q for q in A.PAQUETES if q["padre"] == p["id"]]
        md += [f"#### Paquete {p['nombre']}\n", f"{p['por_que']}\n",
               _uml_respaldo(f"an-pkg-{p['id']}", f"Clases del análisis del paquete {p['nombre']}")]
        md += [_ficha_clase(c) for c in A.clases_de_paquete(p["id"])]
        for q in servicios:
            md += [f"**Paquete de servicio {q['nombre']}.** {q['por_que']}\n"]
            md += [_ficha_clase(c) for c in A.clases_de_paquete(q["id"])]

    # ---- 2.2.3 realizaciones
    md += ["### 2.2.3 Realización de los casos de uso: análisis\n",
           "Cada caso de uso se realiza con una o más colaboraciones, una por cada flujo diferenciado. Todas empiezan con un mensaje de un actor "
           "a una clase de interfaz; los mensajes dicen para qué un objeto invoca a otro (no son operaciones) y los enlaces son instancias de las "
           "asociaciones del diagrama de clases participantes. El servicio de IA, que es un actor sistema externo, se comunica a través de su "
           "propia clase de interfaz. En los diagramas, cuando dos objetos intercambian mensajes en los dos sentidos comparten una sola línea y "
           "la flecha de texto «->» o «<-» dice el sentido.\n"]
    for numero_ciclo, titulo, codigos in R.CICLOS:
        md.append(f"#### Ciclo de vida #{numero_ciclo}\n")
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
                md += ["Clases participantes:\n", _uml_respaldo(f"acp-{col['id']}", f"{col['id']}: clases participantes"),
                       "Diagrama de colaboración:\n", _uml_respaldo(f"com-{col['id']}", f"{col['id']}: {col['nombre']}")]
                if col["especiales"]:
                    md += ["Requisitos especiales de la realización:\n"] + [f"- {e}" for e in col["especiales"]] + [""]

    # ---- 2.2.4 trazabilidad
    md += ["### 2.2.4 Las clases del análisis en el software\n",
           "El modelo manda: esta tabla dice, para cada clase del análisis, si ya existe en el código (y dónde), si cambia por alguno de los cambios "
           "de este parcial (C1: conversación compartida con la IA; C2: avisos en la vista del celular; C3: MongoDB para la conversación y la "
           "actividad) o si es nueva (C4: asistente de ayuda). La entidad Diagrama vive en el navegador (JointJS) y se respalda en el servidor.\n",
           _tabla_trazabilidad()]
    return "\n".join(md)
