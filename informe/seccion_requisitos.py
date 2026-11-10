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
    """Capítulo 2 del informe, flujo de requisitos. Misma estructura que el documento de referencia: actores, casos de uso, priorizar, detallar y estructurar."""
    R.validar()
    md = ["# 2. Proceso de desarrollo\n",
          "## 2.1 Captura de requisitos\n"]

    # 2.1.1 actores
    md += ["### 2.1.1 Actores\n"]
    for codigo, nombre, descripcion in R.ACTORES:
        md += [f"**{codigo}: {nombre}**\n", f"{descripcion}\n"]

    # 2.1.2 casos de uso
    md += ["### 2.1.2 Casos de uso\n"]
    for codigo in sorted(R.CASOS, key=R.numero):
        c = R.CASOS[codigo]
        md.append(f"**{codigo}: {c['nombre']}.** {c['proposito']}\n")

    # 2.1.3 priorizar
    md += ["### 2.1.3 Priorizar casos de uso\n"]
    for numero_ciclo, titulo, codigos in R.CICLOS:
        md += [f"#### Ciclo de vida #{numero_ciclo}\n", tabla_priorizacion(codigos)]

    # 2.1.4 detallar
    md += ["### 2.1.4 Detallar casos de uso\n"]
    for numero_ciclo, titulo, codigos in R.CICLOS:
        md.append(f"#### Ciclo de vida #{numero_ciclo}\n")
        for codigo in codigos:
            c = R.CASOS[codigo]
            md += [f"**{codigo}: {c['nombre']}.**\n", ficha(codigo)]

    # 2.1.5 estructurar
    md += ["### 2.1.5 Estructurar el modelo de caso de uso\n"]
    for numero_ciclo, _, _ in R.CICLOS:
        md += [f"#### Ciclo de vida #{numero_ciclo}\n", _uml_respaldo(f"uc-ciclo-{numero_ciclo}", f"Casos de uso del ciclo de vida {numero_ciclo}")]
    return "\n".join(md)
