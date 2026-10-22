"""Evaluación de proveedores de IA con 10 pedidos fijos (RF-33).

Uso (desde la raíz del repositorio, con el entorno virtual del backend):

    DJANGO_SECRET_KEY=x POSTGRES_PASSWORD=x back_generador_bd/.venv/bin/python \
        scripts/evaluar_ia.py gemini
    ... scripts/evaluar_ia.py ollama [modelo] [url] [modelo-reentrenado-para-cambios]

Cada pedido llama al proveedor tal como lo hace el chat de la sala y verifica de
forma automática que la respuesta sea un JSON utilizable y que haga exactamente
lo pedido: la clase, el atributo, el tipo o los extremos de la relación
correctos, que no se pierda lo que ya existía y que la cantidad de eliminaciones
sea la esperada (la misma regla que usa el chat para pedir confirmación).
Imprime una tabla en Markdown (válido, correcto, segundos) y un resumen.
No modifica ningún diagrama ni base de datos: solo llama al proveedor.

    scripts/evaluar_ia.py --verificadores

comprueba, sin llamar a ningún proveedor, que las verificaciones aceptan una
respuesta buena y rechazan respuestas casi buenas (clase equivocada, tipo
equivocado, atributos perdidos, dirección invertida...).
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "back_generador_bd"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diagramador_uml.settings")

import django  # noqa: E402

django.setup()

from uml_api.services.ai_provider import (  # noqa: E402
    AIProviderError,
    GeminiProvider,
    OllamaProvider,
)
from uml_api.services.change_guard import count_destructive, validate_changes  # noqa: E402
from uml_api.services.ia_context import build_review_prompt, parse_review  # noqa: E402

PERSONA = {
    "classes": [
        {"id": "p", "name": "Persona", "attributes": [{"name": "nombre", "type": "string"}, {"name": "edad", "type": "int"}], "methods": []},
        {"id": "e", "name": "Empleado", "attributes": [{"name": "sueldo", "type": "float"}], "methods": []},
    ],
    "relationships": [],
}
CLIENTE_PEDIDO = {
    "classes": [
        {"id": "c", "name": "Cliente", "attributes": [{"name": "id", "type": "int"}, {"name": "nombre", "type": "string"}], "methods": []},
        {"id": "o", "name": "Pedido", "attributes": [{"name": "total", "type": "float"}], "methods": []},
    ],
    "relationships": [],
}
DEFECTUOSO = {
    "classes": [
        {"id": "a", "name": "Cliente", "attributes": [{"name": "nombre", "type": "string"}], "methods": []},
        {"id": "b", "name": "Pedido", "attributes": [{"name": "total", "type": "float"}], "methods": []},
        {"id": "x", "name": "Producto", "attributes": [], "methods": []},
    ],
    "relationships": [],
}


def todo(changes):
    """Clases y relaciones del cambio, venga directo o dentro de `editado`."""
    partes = [changes] + ([changes["editado"]] if isinstance(changes.get("editado"), dict) else [])
    clases, rels = [], []
    for parte in partes:
        clases += [c for c in parte.get("classes", []) if isinstance(c, dict)]
        rels += [r for r in parte.get("relationships", []) if isinstance(r, dict)]
    return clases, rels


def minusculas(valor):
    return str(valor if valor is not None else "").strip().lower()


def nombres(items, clave="name"):
    return {minusculas(i.get(clave)) for i in items}


def clase(cambios, nombre):
    """La clase del cambio con ese nombre (sin distinguir mayúsculas), o None."""
    return next((k for k in todo(cambios)[0] if minusculas(k.get("name")) == nombre), None)


def miembros(k, clave):
    """Atributos o métodos de una clase, solo los que son objetos."""
    lista = k.get(clave) if k else None
    return [m for m in lista if isinstance(m, dict)] if isinstance(lista, list) else []


def miembro(k, clave, nombre):
    """El atributo/método con ese nombre (o `originalName`, en una edición)."""
    return next((m for m in miembros(k, clave)
                 if nombre in (minusculas(m.get("name")), minusculas(m.get("originalName")))), None)


def es_tipo(atributo, *candidatos):
    return atributo is not None and any(t in minusculas(atributo.get("type")) for t in candidatos)


def extremos(rel, cambios, uml):
    """(origen, destino) de una relación como nombres de clase en minúsculas.

    Los extremos pueden venir como nombre o como id; el id se busca entre las
    clases del diagrama de entrada y entre las del propio cambio.
    """
    por_id = {}
    for k in (uml or {}).get("classes", []) + todo(cambios)[0]:
        if isinstance(k, dict) and k.get("id") is not None:
            por_id[str(k["id"])] = minusculas(k.get("name"))
    def resolver(valor):
        return por_id.get(str(valor), minusculas(valor))
    return resolver(rel.get("sourceId")), resolver(rel.get("targetId"))


def relacion(cambios, uml, origen, destino, tipo=None):
    """Hay una relación (no marcada para eliminar) de `origen` a `destino`."""
    return any(
        r.get("eliminar") is not True
        and (tipo is None or tipo in minusculas(r.get("type")))
        and extremos(r, cambios, uml) == (origen, destino)
        for r in todo(cambios)[1]
    )


def eliminaciones(cambios, uml):
    """Lo mismo que cuenta el chat para pedir confirmación antes de aplicar."""
    return count_destructive(cambios, uml)


def conserva(cambios, uml, nombre_clase, atributos):
    """La clase conserva todos esos atributos (el editor reemplaza lo que no viene)."""
    return atributos <= nombres(miembros(clase(cambios, nombre_clase), "attributes"))


NUMERICOS = ("float", "double", "decimal", "number", "real", "numeric")
TEXTOS = ("string", "str", "text", "varchar", "char")
FECHAS = ("date", "fecha", "time")


def v_crear_factura(c, uml):
    k = clase(c, "factura")
    return (k is not None
            and es_tipo(miembro(k, "attributes", "total"), *NUMERICOS)
            and es_tipo(miembro(k, "attributes", "fecha"), *FECHAS)
            and eliminaciones(c, uml) == 0)


def v_cliente_pedido(c, uml):
    clases = nombres(todo(c)[0])
    return ({"cliente", "pedido"} <= clases
            and relacion(c, uml, "cliente", "pedido")
            and eliminaciones(c, uml) == 0)


def v_atributo_email(c, uml):
    k = clase(c, "cliente")
    return (k is not None
            and es_tipo(miembro(k, "attributes", "email"), *TEXTOS)
            and conserva(c, uml, "cliente", {"id", "nombre"})
            and eliminaciones(c, uml) == 0)


def v_metodo_comprar(c, uml):
    k = clase(c, "cliente")
    # Si trae atributos, tienen que ser todos los que ya tenía.
    atributos_ok = "attributes" not in (k or {}) or conserva(c, uml, "cliente", {"id", "nombre"})
    return (k is not None
            and any(minusculas(m.get("name")).startswith("comprar") for m in miembros(k, "methods"))
            and atributos_ok
            and eliminaciones(c, uml) == 0)


def v_tipo_decimal(c, uml):
    k = clase(c, "pedido")
    return (k is not None
            and es_tipo(miembro(k, "attributes", "total"), "decimal")
            and not any(otra.get("eliminar") is True for otra in todo(c)[0])
            and eliminaciones(c, uml) == 0)


def v_eliminar_atributo(c, uml):
    persona = clase(c, "persona")
    edad = miembro(persona, "attributes", "edad")
    return (persona is not None
            and persona.get("eliminar") is not True
            and edad is not None and edad.get("eliminar") is True
            and all(a.get("eliminar") is not True for a in miembros(persona, "attributes") if a is not edad)
            and eliminaciones(c, uml) == 1)


def v_eliminar_clase(c, uml):
    pedido = clase(c, "pedido")
    return (pedido is not None
            and pedido.get("eliminar") is True
            and not any(k.get("eliminar") is True for k in todo(c)[0] if k is not pedido)
            and eliminaciones(c, uml) == 1)


def v_herencia(c, uml):
    return (relacion(c, uml, "empleado", "persona", "generaliz")
            and eliminaciones(c, uml) == 0)


def v_biblioteca(c, uml):
    return {"libro", "autor"} <= nombres(todo(c)[0]) and (
        {"prestamo"} <= nombres(todo(c)[0]) or {"préstamo"} <= nombres(todo(c)[0]))


# (id, pedido, diagrama de entrada, verificación)
PEDIDOS = [
    ("crear clase con atributos", "Agrega una clase Factura con los atributos total: float y fecha: Date", None,
     v_crear_factura),
    ("crear dos clases y una relación", "Crea las clases Cliente y Pedido y una asociación de Cliente a Pedido", None,
     v_cliente_pedido),
    ("agregar atributo", "Agrega el atributo email: string a la clase Cliente", CLIENTE_PEDIDO,
     v_atributo_email),
    ("agregar método", "Agrega el método comprar() a la clase Cliente", CLIENTE_PEDIDO,
     v_metodo_comprar),
    ("editar tipo de atributo", "Cambia el tipo del atributo total de la clase Pedido a decimal", CLIENTE_PEDIDO,
     v_tipo_decimal),
    ("eliminar atributo", "Elimina el atributo edad de la clase Persona", PERSONA,
     v_eliminar_atributo),
    ("eliminar clase", "Elimina la clase Pedido", CLIENTE_PEDIDO,
     v_eliminar_clase),
    ("herencia", "Haz que Empleado herede de Persona", PERSONA,
     v_herencia),
    ("dominio desde texto", "Crea un sistema de biblioteca con las clases Libro, Autor y Prestamo", None,
     v_biblioteca),
]


def v_revision(revision):
    """Señala el problema real (Producto aislado y sin atributos) y propone cómo arreglarlo."""
    hallazgos = revision["findings"]
    return (any("producto" in minusculas(h["text"]) for h in hallazgos)
            and any(h["prompt"] for h in hallazgos))


def correr_cambio(proveedor, pedido, uml):
    cambios = proveedor.change(pedido, uml)
    validate_changes(cambios)  # la misma validación que aplica el chat antes de responder
    return cambios


def correr_revision(proveedor):
    return parse_review(proveedor.chat(build_review_prompt(uml=DEFECTUOSO)))


def atr(nombre, tipo="string", **extra):
    return {"name": nombre, "type": tipo, **extra}


def cls(nombre, atributos=None, metodos=None, **extra):
    """Clase del cambio; sin `attributes`/`methods` el editor no toca los que ya tiene."""
    campos = {}
    if atributos is not None:
        campos["attributes"] = list(atributos)
    if metodos is not None:
        campos["methods"] = list(metodos)
    return {"name": nombre, **campos, **extra}


def rel(origen, destino, tipo="association", **extra):
    return {"type": tipo, "sourceId": origen, "targetId": destino, **extra}


def verificadores():
    """Cada verificación acepta una respuesta buena y rechaza varias casi buenas."""
    cliente = cls("Cliente", [atr("id", "int"), atr("nombre"), atr("email")])
    casos = {
        "crear clase con atributos": (v_crear_factura, None,
            {"classes": [cls("Factura", [atr("total", "float"), atr("fecha", "Date")])]},
            [{"classes": [cls("Factura", [atr("total", "string"), atr("fecha", "Date")])]},
             {"classes": [cls("Facturas", [atr("total", "float"), atr("fecha", "Date")])]},
             {"classes": [cls("Factura", [atr("total", "float")])]},
             {"classes": [cls("Pedido", [atr("total", "float"), atr("fecha", "Date")])]}]),
        "crear dos clases y una relación": (v_cliente_pedido, None,
            {"classes": [cls("Cliente"), cls("Pedido")], "relationships": [rel("Cliente", "Pedido")]},
            [{"classes": [cls("Cliente"), cls("Pedido")], "relationships": []},
             {"classes": [cls("Cliente"), cls("Pedido")], "relationships": [rel("Pedido", "Cliente")]},
             {"classes": [cls("Cliente"), cls("Pedido")], "relationships": [rel("Cliente", "Factura")]},
             {"classes": [cls("Cliente")], "relationships": [rel("Cliente", "Pedido")]}]),
        "agregar atributo": (v_atributo_email, CLIENTE_PEDIDO,
            {"classes": [{"id": "c", **cliente}]},
            [{"classes": [cls("Cliente", [atr("email")])]},  # borraría id y nombre
             {"classes": [cls("Cliente", [atr("id", "int"), atr("nombre"), atr("email", "int")])]},
             {"classes": [cls("Pedido", [atr("email")])]},
             {"classes": [cls("Cliente", [atr("id", "int"), atr("nombre"), atr("correo")])]}]),
        "agregar método": (v_metodo_comprar, CLIENTE_PEDIDO,
            {"classes": [cls("Cliente", metodos=[{"name": "comprar"}])]},
            [{"classes": [cls("Pedido", metodos=[{"name": "comprar"}])]},
             {"classes": [cls("Cliente", [atr("id", "int")], [{"name": "comprar"}])]},  # pierde nombre
             {"classes": [cls("Cliente", metodos=[{"name": "vender"}])]}]),
        "editar tipo de atributo": (v_tipo_decimal, CLIENTE_PEDIDO,
            {"original": CLIENTE_PEDIDO,
             "editado": {"classes": [{"id": "o", "name": "Pedido", "editado": True,
                                      "attributes": [{"originalName": "total", "name": "total",
                                                      "type": "decimal", "editado": True}]}]}},
            [{"classes": [cls("Pedido", [atr("total", "decimal")])]},  # formato directo: también vale
             {"original": CLIENTE_PEDIDO,
              "editado": {"classes": [{"id": "o", "name": "Pedido", "editado": True,
                                       "attributes": [{"originalName": "total", "name": "total",
                                                       "type": "string", "editado": True}]}]}},
             {"original": CLIENTE_PEDIDO,
              "editado": {"classes": [{"id": "c", "name": "Cliente", "editado": True,
                                       "attributes": [{"originalName": "total", "name": "total",
                                                       "type": "decimal", "editado": True}]}]}}]),
        "eliminar atributo": (v_eliminar_atributo, PERSONA,
            {"classes": [cls("Persona", [atr("edad", "int", eliminar=True)])]},
            [{"classes": [cls("Empleado", [atr("edad", "int", eliminar=True)])]},
             {"classes": [cls("Persona", [atr("nombre", eliminar=True)])]},
             {"classes": [cls("Persona", eliminar=True)]},
             {"classes": [cls("Persona", [atr("edad", "int", eliminar=True), atr("nombre", eliminar=True)])]},
             {"classes": [cls("Persona", [atr("nombre")])]}]),  # deja solo nombre: borra edad sin marcarlo
        "eliminar clase": (v_eliminar_clase, CLIENTE_PEDIDO,
            {"classes": [{"name": "Pedido", "eliminar": True}]},
            [{"classes": [{"name": "Cliente", "eliminar": True}]},
             {"classes": [{"name": "Pedido", "eliminar": True}, {"name": "Cliente", "eliminar": True}]},
             {"classes": [cls("Pedido")]}]),
        "herencia": (v_herencia, PERSONA,
            {"relationships": [rel("e", "p", "generalization")]},
            [{"relationships": [rel("p", "e", "generalization")]},  # invertida
             {"relationships": [rel("e", "p", "association")]},
             {"relationships": [rel("Empleado", "Cliente", "generalization")]}]),
        "dominio desde texto": (v_biblioteca, None,
            {"classes": [cls("Libro"), cls("Autor"), cls("Prestamo")]},
            [{"classes": [cls("Libro"), cls("Autor")]},
             {"classes": [cls("Libros"), cls("LibroAutor"), cls("Prestamos")]}]),
    }
    fallos = 0
    for nombre, (verifica, uml, buena, malas) in casos.items():
        resultados = [("buena", bool(verifica(buena, uml)), True)]
        resultados += [(f"mala {i}", bool(verifica(m, uml)), False) for i, m in enumerate(malas, 1)]
        # La segunda de "editar tipo" usa el formato directo, que también es correcto.
        if nombre == "editar tipo de atributo":
            resultados[1] = ("directa", resultados[1][1], True)
        for etiqueta, obtenido, esperado in resultados:
            if obtenido != esperado:
                fallos += 1
                print(f"FALLA  {nombre} / {etiqueta}: esperaba {esperado}, obtuvo {obtenido}")
    revision_buena = {"summary": "", "findings": [{"text": "Producto está aislado y sin atributos", "prompt": "agrega atributos a Producto"}]}
    revision_mala = [
        {"summary": "", "findings": []},
        {"summary": "", "findings": [{"text": "Falta documentación", "prompt": "documenta"}]},
        {"summary": "", "findings": [{"text": "Producto está aislado", "prompt": ""}]},
    ]
    for etiqueta, revision, esperado in [("revisión buena", revision_buena, True)] + [
        (f"revisión mala {i}", r, False) for i, r in enumerate(revision_mala, 1)
    ]:
        if bool(v_revision(revision)) != esperado:
            fallos += 1
            print(f"FALLA  {etiqueta}: esperaba {esperado}")
    print("Verificadores correctos." if not fallos else f"{fallos} verificación(es) incorrecta(s).")
    return fallos


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--verificadores":
        sys.exit(1 if verificadores() else 0)
    nombre = sys.argv[1] if len(sys.argv) > 1 else "gemini"
    if nombre == "ollama":
        modelo = sys.argv[2] if len(sys.argv) > 2 else None
        url = sys.argv[3] if len(sys.argv) > 3 else None
        cambios = sys.argv[4] if len(sys.argv) > 4 else None
        proveedor = OllamaProvider(base_url=url, model=modelo, change_model=cambios)
        etiqueta = f"ollama ({proveedor.model}" + (f"; cambios: {cambios} reentrenado)" if cambios else ")")
    else:
        proveedor = GeminiProvider()
        etiqueta = "gemini"

    filas = []
    for numero, (titulo, pedido, uml, verifica) in enumerate(PEDIDOS, 1):
        inicio = time.monotonic()
        valido = correcto = False
        detalle = ""
        try:
            cambios = correr_cambio(proveedor, pedido, uml)
            valido = True
            correcto = bool(verifica(cambios, uml))
        except AIProviderError as exc:
            detalle = str(exc)[:60]
        except Exception as exc:  # una verificación no debe tumbar la evaluación
            detalle = f"{type(exc).__name__}"
        filas.append((numero, titulo, valido, correcto, time.monotonic() - inicio, detalle))

    inicio = time.monotonic()
    valido = correcto = False
    detalle = ""
    try:
        revision = correr_revision(proveedor)
        valido = bool(revision["findings"]) or bool(revision["summary"])
        # El diagrama tiene una clase aislada y sin atributos (Producto): debe señalarla.
        correcto = bool(v_revision(revision))
    except AIProviderError as exc:
        detalle = str(exc)[:60]
    filas.append((10, "revisión de un diagrama con defectos", valido, correcto, time.monotonic() - inicio, detalle))

    print(f"\n### {etiqueta}\n")
    print("| # | Pedido | JSON válido | Resultado correcto | Segundos |")
    print("|---|---|---|---|---|")
    for numero, titulo, valido, correcto, segundos, detalle in filas:
        marca = lambda ok: "sí" if ok else "no"  # noqa: E731
        extra = f" ({detalle})" if detalle else ""
        print(f"| {numero} | {titulo}{extra} | {marca(valido)} | {marca(correcto)} | {segundos:.1f} |")
    validos = sum(f[2] for f in filas)
    correctos = sum(f[3] for f in filas)
    total = sum(f[4] for f in filas)
    print(f"\nJSON válido: {validos}/10 · Correcto: {correctos}/10 · Tiempo total: {total:.0f} s · Promedio: {total / 10:.1f} s")


if __name__ == "__main__":
    main()
