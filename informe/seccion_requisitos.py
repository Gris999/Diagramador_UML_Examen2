"""Sección 2.1 del informe: captura de requisitos (flujo de requisitos del PUDS), generada de `modelo/requisitos.py`.

Estructura de los informes de referencia (REF1/REF2) y de las cinco actividades del flujo: encontrar actores y casos de uso,
priorizar, detallar, estructurar el modelo y prototipar la interfaz; más el glosario y los requisitos adicionales.
"""

from modelo import requisitos as R

ESTILO_PLANTUML = None  # se importa perezosamente de parte2 (evita un ciclo de importación)


def _uml_respaldo(id_ea, titulo):
    """Bloque PlantUML mínimo: se usa solo si falta la imagen de Enterprise Architect de ese diagrama."""
    return f"```plantuml\n@startuml\n' ea:{id_ea}\ntitle {titulo}\n@enduml\n```\n"


def _lista(pasos):
    return "<br>".join(f"{i}. {p}" for i, p in enumerate(pasos, 1))


def _alternos(alternos):
    if not alternos:
        return "No tiene."
    filas = []
    for letra, (condicion, pasos) in zip("ABCDEFG", alternos):
        filas.append(f"**{letra}. {condicion}:**")
        filas += [f"{i}. {p}" for i, p in enumerate(pasos, 1)]
    return "<br>".join(filas)


def _bullets(items):
    return "<br>".join(f"• {x}" for x in items) if items else "Ninguno."


def _actores_texto(codigo):
    return ", ".join(f"{a} {R.NOMBRE_ACTOR[a]}" for a in R.CASOS[codigo]["actores"])


def _iniciador_texto(codigo):
    a = R.inicia(codigo)
    herencia = " (A1 Diseñador lo hereda)" if a == "A2" and "A1" in R.CASOS[codigo]["actores"] else ""
    return f"{a} {R.NOMBRE_ACTOR[a]}{herencia}"


def ficha(codigo):
    c = R.CASOS[codigo]
    filas = [
        ("CASO DE USO", f"{codigo}: {c['nombre']}"),
        ("PROPÓSITO", c["proposito"]),
        ("ACTORES", _actores_texto(codigo)),
        ("INICIADOR", _iniciador_texto(codigo)),
        ("PRECONDICIÓN", c["precondicion"]),
        ("FLUJO DE SUCESO PRINCIPAL", _lista(c["flujo"])),
        ("FLUJOS ALTERNOS", _alternos(c["alternos"])),
        ("POSTCONDICIÓN", c["postcondicion"]),
        ("EXCEPCIÓN", _bullets(c["excepciones"])),
        ("REQUISITOS ESPECIALES", _bullets(c["especiales"])),
    ]
    if c["no_permitido"]:
        filas.append(("CAMINOS NO PERMITIDOS", _bullets(c["no_permitido"])))
    return "\n".join(["| | |", "|---|---|"] + [f"| **{k}** | {v} |" for k, v in filas]) + "\n"


def _mayuscula(texto):
    return texto[:1].upper() + texto[1:]


def tabla_priorizacion(codigos):
    filas = ["| NRO | Casos de uso | Estado | Prioridad | Riesgo | Actor |", "|---|---|---|---|---|---|"]
    for cod in codigos:
        c = R.CASOS[cod]
        filas.append(f"| {cod} | {c['nombre']} | {_mayuscula(c['estado'])} | {_mayuscula(c['prioridad'])} | {_mayuscula(c['riesgo'])} | "
                     f"{', '.join(c['actores'])} |")
    return "\n".join(filas) + "\n"


def generar():
    R.validar()
    md = ["# 2. Registro del proceso de desarrollo de software (PUDS)\n",
          "Este capítulo registra cómo se aplicó el Proceso Unificado de Desarrollo de Software a la herramienta CASE colaborativa. El proceso "
          "no pide inventar nada: establece un flujo de trabajo (requisitos, análisis, diseño, implementación y pruebas) que se repite en cada "
          "ciclo de vida. Como el segundo parcial reúne todo lo construido, el documento recorre **cuatro ciclos de vida**: los ciclos 1 a 3 son la "
          "herramienta del primer parcial (con lo que cambió) y el **ciclo 4 es lo nuevo del segundo parcial**: la inteligencia artificial como un "
          "integrante más de la sala, la actividad del equipo, el seguimiento desde el celular y el asistente de ayuda. Todos los diagramas siguen "
          "la notación UML 2.5.1 y están hechos en Enterprise Architect.\n",
          "## 2.1 Captura de requisitos\n",
          "**Visión del proyecto.** Modelar un sistema con UML suele hacerse de forma individual y en herramientas de escritorio, y pasar del modelo "
          "al código es un trabajo manual. Cuando varias personas diseñan a la vez se pierde la visión de quién cambió qué, y la inteligencia "
          "artificial suele vivir fuera del equipo, sin conocer el diagrama ni lo que hizo cada integrante.\n",
          "**Objetivo general.** Desarrollar una plataforma CASE web para modelar diagramas de clases UML 2.5 de forma colaborativa, con la "
          "inteligencia artificial como un integrante más de la sala, que genere a partir del modelo un backend Spring Boot con PostgreSQL, una "
          "colección de Postman y un proyecto Flutter, para reducir el tiempo de desarrollo y mejorar la productividad.\n",
          "**Objetivos específicos.**\n",
          "- Crear y editar diagramas de clases en equipo, con roles, reconexión y recuperación del estado.",
          "- Crear o modificar el diagrama a partir de texto, voz e imágenes, y generar el código del sistema desde el modelo.",
          "- Incorporar la IA como integrante de la sala: actúa solo a pedido, conoce lo que hizo cada persona, comparte una sola conversación y "
          "deja sus ideas a la vista.",
          "- Permitir retomar el trabajo en otra sesión, seguirlo desde el celular y aprender a usar la herramienta con un asistente.",
          "- Intercambiar modelos con Enterprise Architect y ofrecer una IA local reentrenada, sin internet.\n",
          "**Alcance.** Incluye todo lo anterior y el despliegue en AWS con HTTPS. No incluye cuentas de usuario con inicio de sesión (el código de la "
          "sala es la llave de acceso) ni la edición desde la vista del celular.\n"]

    # 2.1.1 actores
    md += ["### 2.1.1 Actores\n",
           "Un actor es un rol de quien interactúa con el sistema desde fuera, e incluye a los sistemas externos. A1 y A2 son personas; A3 es un "
           "sistema externo y, por eso, secundario: ningún caso de uso lo inicia.\n"]
    for codigo, nombre, descripcion in R.ACTORES:
        md += [f"**{codigo}: {nombre}**\n", f"{descripcion}\n"]
    md += ["**Quién no es un actor.**\n", "| Elemento | Por qué no es un actor |", "|---|---|"]
    md += [f"| {nombre} | {motivo} |" for nombre, motivo in R.NO_SON_ACTORES]
    md.append("")

    # 2.1.2 casos de uso
    md += ["### 2.1.2 Casos de uso\n",
           "Cada caso de uso es un objetivo completo de un actor que le entrega un resultado de valor y se nombra con una frase verbal que dice ese "
           "objetivo. No se dividen en operaciones: por ejemplo, crear, editar y eliminar clases es un solo caso (CU2), y entrar a una sala "
           "incluye identificarse (CU1). Los casos de uso son catorce:\n"]
    for codigo in sorted(R.CASOS, key=R.numero):
        md.append(f"- ➢ {codigo}: {R.CASOS[codigo]['nombre']}")
    md.append("")

    # 2.1.3 priorizar
    md += ["### 2.1.3 Priorizar casos de uso\n",
           "Los casos de uso se agrupan en ciclos de vida según su prioridad y el riesgo que reducen: primero los que fijan la arquitectura, y la IA "
           "como integrante en el último ciclo. Se usan las escalas del proceso: prioridad crítica, importante o secundaria; riesgo crítico, "
           "significativo u ordinario; y estado propuesto, aprobado, incluido o validado.\n"]
    for numero_ciclo, titulo, codigos in R.CICLOS:
        md += [f"#### Ciclo de vida #{numero_ciclo}\n", f"*{titulo}.*\n", tabla_priorizacion(codigos)]
    md += ["**Vista de la arquitectura del modelo de casos de uso.** Los casos de uso significativos para la arquitectura, que se abordan primero:\n",
           "| Caso de uso | Por qué es significativo |", "|---|---|"]
    md += [f"| {c}: {R.CASOS[c]['nombre']} | {R.PORQUE_SIGNIFICATIVOS[c][:1].upper() + R.PORQUE_SIGNIFICATIVOS[c][1:]} |" for c in R.SIGNIFICATIVOS]
    md += ["", _uml_respaldo("uc-arquitectura", "Vista de la arquitectura del modelo de casos de uso")]

    # 2.1.4 detallar
    md += ["### 2.1.4 Detallar casos de uso\n",
           "Cada caso de uso se describe con su precondición, su camino básico, sus caminos alternos, su postcondición, las excepciones y los "
           "requisitos especiales que solo le afectan. Cada camino se convierte después en un caso de prueba (sección 2.5).\n"]
    for numero_ciclo, titulo, codigos in R.CICLOS:
        md.append(f"#### Ciclo de vida #{numero_ciclo}\n")
        for codigo in codigos:
            c = R.CASOS[codigo]
            md += [f"**{codigo}: {c['nombre']}.**\n", _uml_respaldo(f"uc-{codigo}", f"{codigo}: {c['nombre']}"), ficha(codigo)]

    # 2.1.5 estructurar
    md += ["### 2.1.5 Estructurar el modelo de caso de uso\n",
           "Los casos de uso se estructuran con relaciones de uso (`include`: secuencias comunes), de extensión (`extend`: comportamiento opcional) y "
           "generalizaciones. Se agregan solo cuando hay algo que factorizar. Aquí hay una generalización de actores (el Diseñador es un Colaborador "
           "con un permiso más, el de expulsar) y una extensión: aplicar una idea que publicó la IA en una revisión (CU9) ejecuta el cambio de CU7. "
           "«Estar en una sala» es una precondición de casi todos los casos, no una inclusión. En los diagramas, los casos en amarillo son los nuevos "
           "del segundo parcial y los grises son de otro ciclo y solo se muestran por una relación.\n"]
    md += ["Una extensión indica a qué caso de uso se le agrega el comportamiento, bajo qué condición y en qué punto de extensión:\n",
           "| Extensión | Caso de uso extendido | Condición | Punto de extensión |", "|---|---|---|---|"]
    md += [f"| {o}: {R.CASOS[o]['nombre']} | {d}: {R.CASOS[d]['nombre']} | {_mayuscula(R.CONDICION_EXTENSION[(o, d)])} | {punto} |"
           for o, d, _, punto in R.RELACIONES]
    md.append("")
    for numero_ciclo, titulo, _ in R.CICLOS:
        md += [f"#### Ciclo de vida #{numero_ciclo}\n", _uml_respaldo(f"uc-ciclo-{numero_ciclo}", f"Casos de uso del ciclo de vida {numero_ciclo}")]
    md += ["#### Modelo completo (ciclos 1 a 4)\n", _uml_respaldo("uc-modelo", "Modelo de casos de uso completo")]

    # 2.1.6 prototipo
    md += ["### 2.1.6 Prototipo de interfaz de usuario\n",
           "Pantallas reales de la aplicación para cada caso de uso que las tiene, como prototipo de lo que ve cada actor.\n"]
    mostradas = set()
    numero_figura = 0
    for codigo in sorted(R.CASOS, key=R.numero):
        pantalla = R.CASOS[codigo]["pantalla"]
        if not pantalla or pantalla in mostradas:
            continue
        mostradas.add(pantalla)
        numero_figura += 1
        usados = [c for c in sorted(R.CASOS, key=R.numero) if R.CASOS[c]["pantalla"] == pantalla]
        md += [f"![Pantalla de {', '.join(usados)}](capturas/{pantalla})",
               f"*Figura 2.{numero_figura}. Pantalla de {', '.join(usados)}.*\n"]

    # 2.1.7 glosario
    md += ["### 2.1.7 Glosario\n", "| Término | Significado |", "|---|---|"]
    md += [f"| **{t}** | {d} |" for t, d in R.GLOSARIO]
    md.append("")

    # 2.1.8 requisitos adicionales
    md += ["### 2.1.8 Requisitos adicionales\n",
           "Son los requisitos no funcionales que no se pueden asociar a un caso de uso en particular; los que sí, están en la ficha de su caso de uso.\n",
           "| ID | Requisito | Descripción | Verificación |", "|---|---|---|---|"]
    md += [f"| {i} | {n} | {d} | {v} |" for i, n, d, v in R.REQUISITOS_ADICIONALES]
    md.append("")
    return "\n".join(md)
