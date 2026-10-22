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


def count_destructive(changes) -> int:
    """Cantidad de elementos que el cambio elimina (clases, atributos, métodos, relaciones)."""
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
    return total


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
