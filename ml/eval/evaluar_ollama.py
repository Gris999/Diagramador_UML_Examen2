"""Evalúa un modelo ya desplegado en Ollama sobre el mismo conjunto de prueba.

Es la comprobación de que lo que se despliega se comporta como lo que se entrenó.

    ml/.venv/bin/python ml/eval/evaluar_ollama.py --modelo uml-qwen-spike \
        --salida ml/runs/spike/eval-ollama.json [--limite 20]
"""

import argparse
import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluar import puntuar  # noqa: E402
from formato import conversacion  # noqa: E402


def preguntar(url, modelo, mensajes):
    cuerpo = json.dumps({"model": modelo, "messages": mensajes, "stream": False, "think": False,
                         "options": {"temperature": 0, "num_predict": 700, "num_ctx": 4096}}).encode()
    pedido = urllib.request.Request(f"{url}/api/chat", data=cuerpo, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=300) as respuesta:
        return json.loads(respuesta.read())["message"]["content"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--modelo", required=True)
    parser.add_argument("--url", default="http://localhost:11434")
    parser.add_argument("--datos", default="ml/data/out")
    parser.add_argument("--salida", required=True)
    parser.add_argument("--limite", type=int)
    args = parser.parse_args()

    ejemplos = [json.loads(l) for l in open(Path(args.datos) / "test_meta.jsonl", encoding="utf-8")]
    if args.limite:
        ejemplos = ejemplos[: args.limite]
    resultados, por_operacion = [], defaultdict(lambda: [0, 0, 0])
    inicio = time.monotonic()
    for numero, ejemplo in enumerate(ejemplos, 1):
        t0 = time.monotonic()
        texto = preguntar(args.url, args.modelo, conversacion(ejemplo["uml"], ejemplo["pedido"]))
        segundos = time.monotonic() - t0
        valido, correcto = puntuar(ejemplo, texto)
        c = por_operacion[ejemplo["op"]]
        c[0] += 1
        c[1] += valido
        c[2] += correcto
        resultados.append({"n": numero, "op": ejemplo["op"], "pedido": ejemplo["pedido"], "json_valido": valido,
                           "correcto": correcto, "segundos": round(segundos, 2), "respuesta": texto})
        print(f"[{numero}/{len(ejemplos)}] {ejemplo['op']:<24} válido={valido!s:<5} correcto={correcto!s:<5} {segundos:.1f}s", flush=True)

    total = len(resultados)
    resumen = {
        "nombre": f"ollama:{args.modelo}", "modelo": args.modelo, "fecha": datetime.now().isoformat(timespec="seconds"),
        "ejemplos": total, "json_valido": sum(r["json_valido"] for r in resultados),
        "correctos": sum(r["correcto"] for r in resultados),
        "segundos_promedio": round(sum(r["segundos"] for r in resultados) / max(total, 1), 2),
        "segundos_total": round(time.monotonic() - inicio, 1),
        "por_operacion": {op: {"total": c[0], "json_valido": c[1], "correctos": c[2]} for op, c in sorted(por_operacion.items())},
    }
    destino = Path(args.salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"resumen": resumen, "resultados": resultados}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nollama:{args.modelo}: JSON válido {resumen['json_valido']}/{total} · correctos {resumen['correctos']}/{total} · {resumen['segundos_promedio']} s promedio")


if __name__ == "__main__":
    main()
