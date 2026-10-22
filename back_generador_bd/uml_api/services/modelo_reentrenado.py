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


def restaurar(cambios: dict, alias: dict, uml_real: dict) -> dict:
    """Vuelve a los ids reales y recupera lo que el modelo no vio."""
    resultado = copy.deepcopy(cambios)
    reales = {c.get("id"): c for c in _lista(uml_real.get("classes") if isinstance(uml_real, dict) else None)}

    for clase in _lista(resultado.get("classes")):
        real = alias.get(clase.get("id"))
        if real is None:
            continue
        clase["id"] = real
        original = reales.get(real, {})
        for campo in ("attributes", "methods"):
            if isinstance(clase.get(campo), list):
                clase[campo] = _fusionar_miembros(clase[campo], _lista(original.get(campo)))
    for relacion in _lista(resultado.get("relationships")):
        for campo in ("id", "sourceId", "targetId"):
            if relacion.get(campo) in alias:
                relacion[campo] = alias[relacion[campo]]
    return resultado
