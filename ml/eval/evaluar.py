"""Evalúa un modelo (con o sin adaptador LoRA) sobre el conjunto de prueba.

Genera con decodificación determinista (temperatura 0), interpreta el JSON y lo
compara con la respuesta correcta en forma canónica (sin ids de clases nuevas,
sin importar el orden). Escribe un JSON con los resultados y cada respuesta.

    ml/.venv/bin/python ml/eval/evaluar.py --modelo <ruta> [--adaptador <ruta>] \
        --datos ml/data/out --salida ml/runs/spike/eval-base.json --nombre base
"""

import argparse
import json
import platform
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
from formato import conversacion  # noqa: E402


def quitar_razonamiento(texto):
    """Quita el bloque <think>...</think> (vacío) que la plantilla de Qwen3 antepone a la respuesta.

    Al entrenar, la plantilla de chat renderiza el turno del asistente con ese bloque; el
    modelo aprende a emitirlo y en la inferencia aparece antes del JSON. El proveedor de la
    app lo quita igual.
    """
    return re.sub(r"^\s*<think>.*?</think>\s*", "", texto, flags=re.DOTALL)


def interpretar(texto):
    """JSON de la respuesta (tolera ```json ... ``` y el bloque <think>); None si no es JSON de un objeto."""
    limpio = re.sub(r"^```(?:json)?\s*|\s*```$", "", quitar_razonamiento(texto).strip(), flags=re.MULTILINE)
    try:
        valor = json.loads(limpio)
    except ValueError:
        return None
    return valor if isinstance(valor, dict) else None


def canonico(cambios, ids_conocidos):
    """Forma comparable: nombres en lugar de ids, conjuntos en lugar de listas."""
    por_id = dict(ids_conocidos)
    for clase in cambios.get("classes", []) or []:
        if isinstance(clase, dict) and clase.get("id") is not None:
            por_id.setdefault(clase["id"], clase.get("name"))

    def miembros(lista):
        return frozenset(
            (str(m.get("name")), str(m.get("type", "")), bool(m.get("eliminar")))
            for m in (lista or []) if isinstance(m, dict)
        )

    clases = frozenset(
        (str(c.get("name")), miembros(c.get("attributes")), miembros(c.get("methods")), bool(c.get("eliminar")))
        for c in cambios.get("classes", []) or [] if isinstance(c, dict)
    )
    relaciones = frozenset(
        (str(r.get("type")), por_id.get(r.get("sourceId"), r.get("sourceId")),
         por_id.get(r.get("targetId"), r.get("targetId")), bool(r.get("eliminar")))
        for r in cambios.get("relationships", []) or [] if isinstance(r, dict)
    )
    return clases, relaciones


def puntuar(ejemplo, texto):
    """(json_valido, correcto) de una respuesta frente a la correcta del ejemplo."""
    ids = {c["id"]: c["name"] for c in ejemplo["uml"]["classes"]}
    obtenido = interpretar(texto)
    valido = obtenido is not None
    return valido, bool(valido and canonico(obtenido, ids) == canonico(ejemplo["esperado"], ids))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", required=True)
    parser.add_argument("--adaptador")
    parser.add_argument("--datos", default="ml/data/out")
    parser.add_argument("--salida", required=True)
    parser.add_argument("--nombre", default="modelo")
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--limite", type=int)
    args = parser.parse_args()

    from mlx_lm import generate, load
    from mlx_lm.sample_utils import make_sampler

    modelo, tokenizador = load(args.modelo, adapter_path=args.adaptador)
    sampler = make_sampler(temp=0.0)
    ejemplos = [json.loads(linea) for linea in open(Path(args.datos) / "test_meta.jsonl", encoding="utf-8")]
    if args.limite:
        ejemplos = ejemplos[: args.limite]

    resultados, por_operacion = [], defaultdict(lambda: [0, 0, 0])
    inicio = time.monotonic()
    for numero, ejemplo in enumerate(ejemplos, 1):
        mensajes = conversacion(ejemplo["uml"], ejemplo["pedido"])
        prompt = tokenizador.apply_chat_template(mensajes, add_generation_prompt=True, tokenize=False)
        t0 = time.monotonic()
        texto = generate(modelo, tokenizador, prompt=prompt, max_tokens=args.max_tokens, sampler=sampler)
        segundos = time.monotonic() - t0

        valido, correcto = puntuar(ejemplo, texto)

        contadores = por_operacion[ejemplo["op"]]
        contadores[0] += 1
        contadores[1] += valido
        contadores[2] += correcto
        resultados.append({
            "n": numero, "op": ejemplo["op"], "pedido": ejemplo["pedido"], "json_valido": valido,
            "correcto": correcto, "segundos": round(segundos, 2), "respuesta": texto,
        })
        print(f"[{numero}/{len(ejemplos)}] {ejemplo['op']:<24} válido={valido!s:<5} correcto={correcto!s:<5} {segundos:.1f}s", flush=True)

    total = len(resultados)
    resumen = {
        "nombre": args.nombre,
        "modelo": args.modelo,
        "adaptador": args.adaptador,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "equipo": f"{platform.machine()} / {platform.platform()}",
        "ejemplos": total,
        "json_valido": sum(r["json_valido"] for r in resultados),
        "correctos": sum(r["correcto"] for r in resultados),
        "segundos_promedio": round(sum(r["segundos"] for r in resultados) / max(total, 1), 2),
        "segundos_total": round(time.monotonic() - inicio, 1),
        "por_operacion": {op: {"total": c[0], "json_valido": c[1], "correctos": c[2]} for op, c in sorted(por_operacion.items())},
    }
    destino = Path(args.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"resumen": resumen, "resultados": resultados}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{args.nombre}: JSON válido {resumen['json_valido']}/{total} · correctos {resumen['correctos']}/{total} · {resumen['segundos_promedio']} s promedio")


if __name__ == "__main__":
    main()
