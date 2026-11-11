"""Tipos de clase UML 2.5 que el editor dibuja: clase, clase abstracta, interfaz y enumeración, y la visibilidad de sus miembros."""

CLASS_KINDS = ("class", "abstract", "interface", "enumeration")

# Las interfaces y las enumeraciones no son tablas ni entidades: los generadores de código no las convierten en nada.
NON_ENTITY_KINDS = ("interface", "enumeration")

# Signo de visibilidad del editor <-> valor de `visibility` de UML/XMI.
VISIBILITY_TO_XMI = {"+": "public", "-": "private", "#": "protected", "~": "package"}
VISIBILITY_FROM_XMI = {value: sign for sign, value in VISIBILITY_TO_XMI.items()}


def kind_of(uml_class) -> str:
    """El tipo de una clase del diagrama; lo que no se reconoce es una clase común."""
    kind = (uml_class or {}).get("kind")
    return kind if kind in CLASS_KINDS else "class"


def code_entities(uml_json):
    """El diagrama sin las interfaces y las enumeraciones (ni las relaciones que las tocan), para los generadores de código.

    Devuelve el mismo objeto si no hay nada que quitar."""
    classes = uml_json.get("classes", [])
    dropped = {c.get("id") for c in classes if kind_of(c) in NON_ENTITY_KINDS}
    if not dropped:
        return uml_json
    relationships = [r for r in uml_json.get("relationships", []) if r.get("sourceId") not in dropped and r.get("targetId") not in dropped]
    return dict(uml_json, classes=[c for c in classes if c.get("id") not in dropped], relationships=relationships)
