"""Salvaguardas sobre los cambios que propone la IA antes de aplicarlos.

La salida del modelo se aplica en el navegador de quien lo pidió, y el modelo
también lee el contenido del diagrama (que puede venir de una importación). Por
eso el servidor acota el tamaño de lo que acepta y cuenta cuántas eliminaciones
trae: la interfaz pide confirmación antes de aplicar un cambio destructivo.
"""

from .ai_provider import AIProviderError

MAX_CLASSES_PER_CHANGE = 60
MAX_RELATIONSHIPS_PER_CHANGE = 150


def _sections(changes):
    """Las partes con clases/relaciones: el cambio directo y, en ediciones, `editado`."""
    if not isinstance(changes, dict):
        return []
    sections = [changes]
    edited = changes.get("editado")
    if isinstance(edited, dict):
        sections.append(edited)
    return sections


def _name_set(members):
    return {
        member["name"].strip().lower()
        for member in (members if isinstance(members, list) else [])
        if isinstance(member, dict) and isinstance(member.get("name"), str) and member["name"].strip()
    }


def _existing_classes(uml):
    """Clases del diagrama actual, indexables por id y por nombre exacto."""
    classes = uml.get("classes") if isinstance(uml, dict) else None
    index = {}
    for item in classes if isinstance(classes, list) else []:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("id"), str):
            index[item["id"]] = item
        if isinstance(item.get("name"), str):
            index.setdefault(item["name"], item)
    return index


def _has_delete_markers(changes):
    """Lo mismo que detecta el editor: con marcas, solo se borra lo marcado."""
    classes = changes.get("classes")
    for item in classes if isinstance(classes, list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("eliminar") is True:
            return True
        for key in ("attributes", "methods"):
            members = item.get(key)
            if any(isinstance(m, dict) and m.get("eliminar") is True
                   for m in (members if isinstance(members, list) else [])):
                return True
    relationships = changes.get("relationships")
    return any(isinstance(r, dict) and r.get("eliminar") is True
               for r in (relationships if isinstance(relationships, list) else []))


def _members_that_would_disappear(changes, uml):
    """Atributos y métodos que la respuesta deja fuera de clases que ya existían.

    El editor reemplaza los atributos y métodos de una clase existente (la que
    coincide por id o por nombre exacto) por los que trae el cambio: si el modelo
    devuelve menos, lo que falta se borra aunque no venga marcado con `eliminar`.
    Si el cambio trae marcas de eliminación, el editor solo borra lo marcado, y
    las ediciones (`original`/`editado`) tampoco reemplazan nada.
    """
    existing = _existing_classes(uml)
    if not existing or not isinstance(changes, dict):
        return 0
    if _has_delete_markers(changes) or (changes.get("original") and changes.get("editado")):
        return 0
    lost = 0
    classes = changes.get("classes")
    for item in classes if isinstance(classes, list) else []:
        if not isinstance(item, dict):
            continue
        match = existing.get(item.get("id")) or existing.get(item.get("name"))
        if match is None:
            continue
        for key in ("attributes", "methods"):
            if not isinstance(item.get(key), list):
                continue  # no se tocan: el editor solo reemplaza lo que viene
            lost += len(_name_set(match.get(key)) - _name_set(item[key]))
    return lost


def count_destructive(changes, uml=None) -> int:
    """Cantidad de elementos que el cambio elimina.

    Cuenta lo marcado con `eliminar` (clases, atributos, métodos, relaciones) y,
    si se pasa el diagrama actual, lo que la respuesta dejaría fuera de clases ya
    existentes.
    """
    total = 0
    for section in _sections(changes):
        classes = section.get("classes")
        for item in classes if isinstance(classes, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("eliminar") is True:
                total += 1
            for key in ("attributes", "methods"):
                members = item.get(key)
                total += sum(
                    1
                    for member in (members if isinstance(members, list) else [])
                    if isinstance(member, dict) and member.get("eliminar") is True
                )
        relationships = section.get("relationships")
        total += sum(
            1
            for rel in (relationships if isinstance(relationships, list) else [])
            if isinstance(rel, dict) and rel.get("eliminar") is True
        )
    return total + _members_that_would_disappear(changes, uml)


def validate_changes(changes) -> None:
    if not isinstance(changes, dict):
        raise AIProviderError("La IA no devolvió un cambio válido.")
    for section in _sections(changes):
        classes = section.get("classes")
        relationships = section.get("relationships")
        if isinstance(classes, list) and len(classes) > MAX_CLASSES_PER_CHANGE:
            raise AIProviderError("El cambio propuesto es demasiado grande.")
        if isinstance(relationships, list) and len(relationships) > MAX_RELATIONSHIPS_PER_CHANGE:
            raise AIProviderError("El cambio propuesto es demasiado grande.")
