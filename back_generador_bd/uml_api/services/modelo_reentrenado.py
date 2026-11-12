"""Conversación con el modelo reentrenado (prompt corto) y adaptación del diagrama.

El modelo se entrenó (carpeta `ml/` del repositorio) con un formato fijo: el
texto de `SISTEMA`, un diagrama compacto con ids cortos (`c1`, `c2`...) y el
pedido. `ml/data/formato.py` es la fuente de ese texto; una prueba comprueba que
esta copia sea idéntica.

El diagrama real del editor trae ids largos, posiciones y tamaños: `compactar`
lo reduce a lo que vio el modelo al entrenar y recuerda cómo volver a los ids
reales; `restaurar` deshace eso en la respuesta y conserva los datos que el
modelo no ve (parámetros y tipo de retorno de los métodos).
"""

import copy
import itertools
import json
import re

SISTEMA = (
    "Eres el asistente de un editor de diagramas de clases UML. Recibes el DIAGRAMA actual "
    "(JSON) y un PEDIDO. Respondes SOLO con un JSON de cambios, sin texto extra.\n"
    'Formato: {"classes":[{"id","name","attributes":[{"name","type"}],"methods":[{"name"}]}],'
    '"relationships":[{"type","sourceId","targetId"}]}\n'
    "Reglas:\n"
    "- Al modificar una clase que ya existe, devuelve la clase completa: mismo id, todos sus "
    "atributos y métodos, con el cambio aplicado.\n"
    '- Para eliminar, marca "eliminar": true en la clase, el atributo, el método o la relación '
    "y devuelve solo eso.\n"
    "- Las clases nuevas llevan un id corto nuevo; las relaciones usan los id de las clases.\n"
    "- Tipos de relación: association, aggregation, composition, generalization "
    "(origen = hijo, destino = padre)."
)

MAX_CLASES = 40


def _compacto(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, separators=(",", ":"))


def quitar_razonamiento(texto: str) -> str:
    """Quita el bloque <think></think> (vacío) que la plantilla de Qwen3 antepone a la respuesta."""
    return re.sub(r"^\s*<think>.*?</think>\s*", "", texto, flags=re.DOTALL)


def _lista(valor):
    return [item for item in valor if isinstance(item, dict)] if isinstance(valor, list) else []


def compactar(uml):
    """(diagrama compacto, {id corto: id real}); None si no hay diagrama utilizable."""
    clases = _lista(uml.get("classes") if isinstance(uml, dict) else None)[:MAX_CLASES]
    alias, compactas = {}, []
    for numero, clase in enumerate(clases, 1):
        if clase.get("id") is None:
            continue
        corto = f"c{numero}"
        alias[corto] = clase["id"]
        compactas.append({
            "id": corto,
            "name": str(clase.get("name", "")),
            "attributes": [{"name": str(a.get("name", "")), "type": str(a.get("type", ""))}
                           for a in _lista(clase.get("attributes"))],
            "methods": [{"name": str(m.get("name", ""))} for m in _lista(clase.get("methods"))],
        })
    por_real = {real: corto for corto, real in alias.items()}
    relaciones = []
    for numero, rel in enumerate(_lista(uml.get("relationships") if isinstance(uml, dict) else None), 1):
        origen, destino = por_real.get(rel.get("sourceId")), por_real.get(rel.get("targetId"))
        if origen is None or destino is None:
            continue
        corto = f"r{numero}"
        alias[corto] = rel.get("id")
        relaciones.append({"id": corto, "type": str(rel.get("type", "association")),
                           "sourceId": origen, "targetId": destino})
    return {"classes": compactas, "relationships": relaciones}, alias


def mensajes(uml_compacto: dict, pedido: str) -> list[dict]:
    return [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": f"DIAGRAMA:\n{_compacto(uml_compacto)}\n\nPEDIDO: {pedido}"},
    ]


def _fusionar_miembros(devueltos, originales):
    """Cada miembro devuelto conserva los datos del original con su mismo nombre."""
    por_nombre = {m.get("name"): m for m in originales}
    resultado = []
    for miembro in devueltos:
        if not isinstance(miembro, dict):
            continue
        original = por_nombre.get(miembro.get("name"))
        resultado.append({**original, **miembro} if original else miembro)
    return resultado


# Un pedido de renombrar: solo entonces es legítimo que una clase conserve su id y cambie de nombre.
_RENOMBRAR = re.compile(r"renombr|cambi\w*\s+(?:de\s+|el\s+)?nombre|cambi\w*\s+(?:la\s+clase\s+)?\w+\s+(?:a|por)\s|ll[aá]mal[aeo]s?\b|pas\w*\s+a\s+llamarse", re.IGNORECASE)
_ATRIBUTO = re.compile(r"\batributos?\b", re.IGNORECASE)
_METODO = re.compile(r"\b(?:m[eé]todos?|operaci[oó]n(?:es)?|funci[oó]n(?:es)?)\b", re.IGNORECASE)


def _corregir_ids(clases: list, alias: dict, reales: dict, instruccion: str | None) -> None:
    """El modelo pequeño a veces le da a una clase nueva un id que ya existe (la nueva «Pedido» llega con el id de «Cliente»), o a dos clases nuevas el mismo.

    Aplicado tal cual, la nueva clase renombraría (y vaciaría) a la que ya estaba. Con la instrucción a la vista se distingue: salvo que se pida renombrar,
    una clase de nombre nuevo que llega con el id de otra es una clase nueva y recibe un id libre. Sin instrucción (`None`) no se toca nada.
    """
    if instruccion is None:
        return
    renombra = bool(_RENOMBRAR.search(instruccion))
    nombre_de = {corto: reales[real].get("name") for corto, real in alias.items() if real in reales}
    ocupados = set(alias) | set(reales) | {c.get("id") for c in clases if c.get("id")}
    libres = (f"c{n}" for n in itertools.count(1) if f"c{n}" not in ocupados)
    vistos = set()
    for clase in clases:
        id_ = clase.get("id")
        ajeno = not renombra and id_ in nombre_de and isinstance(clase.get("name"), str) and clase["name"] != nombre_de[id_]
        if id_ is not None and (ajeno or id_ in vistos):
            clase["id"] = next(libres)
            ocupados.add(clase["id"])
        vistos.add(clase.get("id"))


# «Empleado herede de Persona», «Perro extienda Animal», «Gato es subclase de Animal»: el primero es el hijo y el segundo el padre.
_HERENCIA = re.compile(
    r"\b(\w+)\s+(?:hered\w+\s+de|extiend\w+(?:\s+de)?|(?:es|sea)\s+(?:una\s+)?(?:subclase|hij[oa])\s+de)\s+(?:la\s+clase\s+)?(\w+)", re.IGNORECASE
)


def _orientar_herencia(resultado: dict, reales: dict, instruccion: str | None) -> None:
    """El modelo pequeño a veces invierte la herencia (hace que Persona herede de Empleado). Si el pedido dice quién hereda de quién, la flecha va del hijo al padre."""
    if not instruccion:
        return
    dicho = _HERENCIA.search(instruccion)
    if not dicho:
        return
    hijo, padre = dicho.group(1).lower(), dicho.group(2).lower()
    nombres = {c.get("id"): c.get("name") for c in reales.values()}
    nombres.update({c.get("id"): c.get("name") for c in _lista(resultado.get("classes"))})
    for relacion in _lista(resultado.get("relationships")):
        if relacion.get("type") != "generalization":
            continue
        origen = str(nombres.get(relacion.get("sourceId")) or "").lower()
        destino = str(nombres.get(relacion.get("targetId")) or "").lower()
        if (origen, destino) == (padre, hijo):
            relacion["sourceId"], relacion["targetId"] = relacion["targetId"], relacion["sourceId"]


def _atributo_que_llego_como_metodo(clase: dict, original: dict, instruccion: str | None) -> None:
    """«Agrega el atributo telefono a Cliente»: si el modelo lo puso como método, se pasa a atributo (solo si el pedido habla de atributos y no de métodos)."""
    if not instruccion or not _ATRIBUTO.search(instruccion) or _METODO.search(instruccion):
        return
    if not isinstance(clase.get("methods"), list) or not isinstance(clase.get("attributes"), list):
        return
    conocidos = {m.get("name") for m in _lista(original.get("methods"))}
    atributos = {a.get("name") for a in clase["attributes"] if isinstance(a, dict)}
    for metodo in list(clase["methods"]):
        nombre = metodo.get("name") if isinstance(metodo, dict) else None
        if nombre and nombre not in conocidos and nombre not in atributos and re.search(rf"\b{re.escape(nombre)}\b", instruccion, re.IGNORECASE):
            clase["methods"].remove(metodo)
            clase["attributes"].append({"name": nombre, "type": "string"})


def restaurar(cambios: dict, alias: dict, uml_real: dict, instruccion: str | None = None) -> dict:
    """Vuelve a los ids reales y recupera lo que el modelo no vio. Con la `instruccion` también corrige los ids repetidos o ajenos de las clases nuevas."""
    resultado = copy.deepcopy(cambios)
    reales = {c.get("id"): c for c in _lista(uml_real.get("classes") if isinstance(uml_real, dict) else None)}
    # Nombre de cada clase existente -> su id corto. Un modelo pequeño a veces devuelve el id de otra
    # clase con el nombre correcto; aplicado tal cual, renombraría y vaciaría la clase equivocada.
    corto_por_nombre = {}
    for corto, real in alias.items():
        if corto.startswith("c") and real in reales and isinstance(reales[real].get("name"), str):
            corto_por_nombre.setdefault(reales[real]["name"], corto)

    clases = _lista(resultado.get("classes"))
    for clase in clases:
        nombre = clase.get("name")
        if isinstance(nombre, str) and nombre in corto_por_nombre and clase.get("id") != corto_por_nombre[nombre]:
            clase["id"] = corto_por_nombre[nombre]  # si el nombre es el de una clase que existe, manda el nombre
    _corregir_ids(clases, alias, reales, instruccion)
    for clase in clases:
        real = alias.get(clase.get("id"))
        if real is None:
            continue
        clase["id"] = real
        original = reales.get(real, {})
        _atributo_que_llego_como_metodo(clase, original, instruccion)
        for campo in ("attributes", "methods"):
            if isinstance(clase.get(campo), list):
                clase[campo] = _fusionar_miembros(clase[campo], _lista(original.get(campo)))
    for relacion in _lista(resultado.get("relationships")):
        for campo in ("id", "sourceId", "targetId"):
            if relacion.get(campo) in alias:
                relacion[campo] = alias[relacion[campo]]
    _orientar_herencia(resultado, reales, instruccion)
    return resultado
