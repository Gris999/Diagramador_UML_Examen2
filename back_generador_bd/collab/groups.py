def room_group_name(room_name):
    """Grupo de los editores de una sala (el orden de entrada define al host)."""
    return f"canvas_{room_name}"


def viewers_group_name(room_name):
    """Grupo de los observadores (vista móvil): solo reciben, no cuentan como miembros."""
    return f"canvas_{room_name}_viewers"
