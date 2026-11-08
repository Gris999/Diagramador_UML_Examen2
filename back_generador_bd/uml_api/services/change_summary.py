"""Cuenta en español, en pocas líneas, qué haría un cambio que propone la IA.

La IA no aplica nada sin permiso: antes de pedirlo se le muestra a la persona lo que va a pasar. El cambio viene en el mismo formato que lee el
editor (crear, editar o eliminar), así que el resumen se arma leyendo ese JSON y no le pide nada más al modelo.
"""

from .ia_context import _text

MAX_LINES = 8


def _class_names(changes, uml):
    """Id → nombre de las clases del diagrama y del propio cambio, para nombrar los extremos de una relación."""
    names = {}
    sources = []
    if isinstance(uml, dict):
        sources.append(uml)
    if isinstance(changes, dict):
        sources.append(changes)
        for key in ("original", "editado"):
            if isinstance(changes.get(key), dict):
                sources.append(changes[key])
    for source in sources:
        classes = source.get("classes")
        for item in classes if isinstance(classes, list) else []:
            if isinstance(item, dict) and isinstance(item.get("id"), str) and _text(item.get("name"), 60):
                names.setdefault(item["id"], _text(item["name"], 60))
    return names


def _members(items, key_name="name"):
    return [
        f"{_text(item.get(key_name), 40)}: {_text(item.get('type'), 30)}".rstrip(": ") if "type" in item else _text(item.get(key_name), 40)
        for item in (items if isinstance(items, list) else [])
        if isinstance(item, dict) and _text(item.get(key_name), 40)
    ]


def _existing_names(uml):
    classes = uml.get("classes") if isinstance(uml, dict) else None
    found = set()
    for item in classes if isinstance(classes, list) else []:
        if isinstance(item, dict):
            for key in ("id", "name"):
                if isinstance(item.get(key), str):
                    found.add(item[key])
    return found


def _end(value, names):
    return names.get(value) or _text(value, 60) or "?"


def _class_lines(section, existing, edited=False):
    lines = []
    classes = section.get("classes")
    for item in classes if isinstance(classes, list) else []:
        if not isinstance(item, dict):
            continue
        name = _text(item.get("name"), 60) or "(sin nombre)"
        attributes = item.get("attributes") if isinstance(item.get("attributes"), list) else []
        methods = item.get("methods") if isinstance(item.get("methods"), list) else []

        if item.get("eliminar") is True:
            lines.append(f"Eliminar la clase {name}")
            continue

        removed = [m for m in attributes + methods if isinstance(m, dict) and m.get("eliminar") is True]
        kept_attributes = [a for a in attributes if isinstance(a, dict) and a.get("eliminar") is not True]
        kept_methods = [m for m in methods if isinstance(m, dict) and m.get("eliminar") is not True]
        for member in removed:
            lines.append(f"Quitar «{_text(member.get('name'), 40)}» de la clase {name}")

        renamed = [m for m in kept_attributes + kept_methods if m.get("originalName")]
        for member in renamed:
            lines.append(f"En la clase {name}, cambiar «{_text(member.get('originalName'), 40)}» por «{_text(member.get('name'), 40)}»")
        plain_attributes = [a for a in kept_attributes if not a.get("originalName")]
        plain_methods = [m for m in kept_methods if not m.get("originalName")]

        is_new = not edited and item.get("id") not in existing and name not in existing
        details = []
        if _members(plain_attributes):
            details.append("atributos: " + ", ".join(_members(plain_attributes)))
        if _members(plain_methods):
            details.append("métodos: " + ", ".join(_members(plain_methods)))
        if is_new:
            lines.append(f"Crear la clase {name}" + (f" ({'; '.join(details)})" if details else ""))
        elif details and not removed and not renamed:
            lines.append(f"Dejar la clase {name} con " + "; ".join(details))
        elif edited and item.get("editado") and not removed and not renamed and not details:
            lines.append(f"Cambiar la clase {name}")
    return lines


def _relationship_lines(section, names):
    lines = []
    relationships = section.get("relationships")
    for rel in relationships if isinstance(relationships, list) else []:
        if not isinstance(rel, dict):
            continue
        source, target = _end(rel.get("sourceId"), names), _end(rel.get("targetId"), names)
        kind = _text(rel.get("type"), 30) or "association"
        if rel.get("eliminar") is True:
            lines.append(f"Quitar la relación entre {source} y {target}")
        else:
            lines.append(f"Relacionar {source} con {target} ({kind})")
    return lines


def summarize_changes(changes, uml=None) -> list:
    """Líneas legibles de lo que haría el cambio; a lo más `MAX_LINES`, con «y N cambios más» si hay más."""
    if not isinstance(changes, dict):
        return []
    names = _class_names(changes, uml)
    existing = _existing_names(uml)

    lines = []
    edited = changes.get("editado")
    if isinstance(edited, dict) and changes.get("original"):
        lines += _class_lines(edited, existing, edited=True)
        lines += _relationship_lines(edited, names)
    else:
        lines += _class_lines(changes, existing)
        lines += _relationship_lines(changes, names)

    if len(lines) > MAX_LINES:
        extra = len(lines) - MAX_LINES
        lines = lines[:MAX_LINES] + [f"… y {extra} cambio{'s' if extra != 1 else ''} más"]
    return lines
