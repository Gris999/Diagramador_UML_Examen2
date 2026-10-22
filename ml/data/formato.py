"""Formato de la conversación con el modelo reentrenado (prompt corto).

El modelo reentrenado aprende las reglas del editor, por eso el prompt no las
repite una por una como el de Gemini (`build_change_prompt`). Este módulo es la
fuente única del texto: lo usan el generador de datos, la evaluación y, más
adelante, el proveedor de la app (una prueba compara ambas copias).
"""

import json

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


def compacto(valor) -> str:
    return json.dumps(valor, ensure_ascii=False, separators=(",", ":"))


def mensaje_usuario(uml: dict, pedido: str) -> str:
    return f"DIAGRAMA:\n{compacto(uml)}\n\nPEDIDO: {pedido}"


def conversacion(uml: dict, pedido: str, esperado: dict | None = None) -> list[dict]:
    """Mensajes en el formato de chat; con `esperado` incluye la respuesta correcta."""
    mensajes = [
        {"role": "system", "content": SISTEMA},
        {"role": "user", "content": mensaje_usuario(uml, pedido)},
    ]
    if esperado is not None:
        mensajes.append({"role": "assistant", "content": compacto(esperado)})
    return mensajes
