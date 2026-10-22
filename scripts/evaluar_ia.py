"""Evaluación de proveedores de IA con 10 pedidos fijos (RF-33).

Uso (desde la raíz del repositorio, con el entorno virtual del backend):

    DJANGO_SECRET_KEY=x POSTGRES_PASSWORD=x back_generador_bd/.venv/bin/python \
        scripts/evaluar_ia.py gemini
    ... scripts/evaluar_ia.py ollama [modelo] [url]

Cada pedido llama al proveedor tal como lo hace el chat de la sala y verifica de
forma automática que la respuesta sea un JSON utilizable y que contenga lo
pedido. Imprime una tabla en Markdown (válido, correcto, segundos) y un resumen.
No modifica ningún diagrama ni base de datos: solo llama al proveedor.
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


def nombres(items, clave="name"):
    return {str(i.get(clave, "")).lower() for i in items}


def texto(changes):
    return json.dumps(changes, ensure_ascii=False).lower()


# (id, pedido, diagrama de entrada, verificación)
PEDIDOS = [
    ("crear clase con atributos", "Agrega una clase Factura con los atributos total: float y fecha: Date", None,
     lambda c: any(k["name"].lower() == "factura" and {"total", "fecha"} <= nombres(k.get("attributes", []))
                   for k in todo(c)[0] if isinstance(k.get("name"), str))),
    ("crear dos clases y una relación", "Crea las clases Cliente y Pedido y una asociación de Cliente a Pedido", None,
     lambda c: {"cliente", "pedido"} <= nombres(todo(c)[0]) and len(todo(c)[1]) >= 1),
    ("agregar atributo", "Agrega el atributo email: string a la clase Cliente", CLIENTE_PEDIDO,
     lambda c: "email" in texto(c) and "cliente" in texto(c)),
    ("agregar método", "Agrega el método comprar() a la clase Cliente", CLIENTE_PEDIDO,
     lambda c: "comprar" in texto(c) and "cliente" in texto(c)),
    ("editar tipo de atributo", "Cambia el tipo del atributo total de la clase Pedido a decimal", CLIENTE_PEDIDO,
     lambda c: "decimal" in texto(c) and "total" in texto(c)),
    ("eliminar atributo", "Elimina el atributo edad de la clase Persona", PERSONA,
     lambda c: any(a.get("eliminar") is True and str(a.get("name", "")).lower() == "edad"
                   for k in todo(c)[0] for a in k.get("attributes", []) if isinstance(a, dict))),
    ("eliminar clase", "Elimina la clase Pedido", CLIENTE_PEDIDO,
     lambda c: any(k.get("eliminar") is True and str(k.get("name", "")).lower() == "pedido" for k in todo(c)[0])),
    ("herencia", "Haz que Empleado herede de Persona", PERSONA,
     lambda c: any("generaliz" in str(r.get("type", "")).lower() for r in todo(c)[1])),
    ("dominio desde texto", "Crea un sistema de biblioteca con las clases Libro, Autor y Prestamo", None,
     lambda c: sum(any(n in nombre for n in ("libro", "autor", "prestamo", "préstamo")) for nombre in nombres(todo(c)[0])) >= 3),
]


def correr_cambio(proveedor, pedido, uml):
    return proveedor.change(pedido, uml)


def correr_revision(proveedor):
    resultado = parse_review(proveedor.chat(build_review_prompt(uml=DEFECTUOSO)))
    return resultado


def main():
    nombre = sys.argv[1] if len(sys.argv) > 1 else "gemini"
    if nombre == "ollama":
        modelo = sys.argv[2] if len(sys.argv) > 2 else None
        url = sys.argv[3] if len(sys.argv) > 3 else None
        proveedor = OllamaProvider(base_url=url, model=modelo)
        etiqueta = f"ollama ({proveedor.model})"
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
            correcto = bool(verifica(cambios))
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
        # El diagrama tiene una clase aislada y sin atributos: debe señalar algo.
        correcto = len(revision["findings"]) >= 1
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
