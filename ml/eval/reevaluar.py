"""Vuelve a puntuar las respuestas guardadas de una evaluación (sin volver a generar).

Sirve cuando cambia la forma de interpretar la respuesta, no el modelo. Conserva
el texto crudo de cada respuesta y anota el motivo en el archivo.

    ml/.venv/bin/python ml/eval/reevaluar.py ml/runs/spike/eval-reentrenado.json ml/data/out "motivo"
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluar import puntuar  # noqa: E402


def main(archivo, datos, motivo):
    contenido = json.loads(Path(archivo).read_text(encoding="utf-8"))
    ejemplos = [json.loads(l) for l in open(Path(datos) / "test_meta.jsonl", encoding="utf-8")]
    resumen = contenido["resumen"]
    antes = {"json_valido": resumen["json_valido"], "correctos": resumen["correctos"]}

    por_operacion = defaultdict(lambda: [0, 0, 0])
    for ejemplo, resultado in zip(ejemplos, contenido["resultados"]):
        resultado["json_valido"], resultado["correcto"] = puntuar(ejemplo, resultado["respuesta"])
        c = por_operacion[ejemplo["op"]]
        c[0] += 1
        c[1] += resultado["json_valido"]
        c[2] += resultado["correcto"]

    resumen["json_valido"] = sum(r["json_valido"] for r in contenido["resultados"])
    resumen["correctos"] = sum(r["correcto"] for r in contenido["resultados"])
    resumen["por_operacion"] = {op: {"total": c[0], "json_valido": c[1], "correctos": c[2]} for op, c in sorted(por_operacion.items())}
    resumen["reescorado"] = {"motivo": motivo, "antes": antes}
    Path(archivo).write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{resumen['nombre']}: antes {antes} -> JSON válido {resumen['json_valido']}/{resumen['ejemplos']} · correctos {resumen['correctos']}/{resumen['ejemplos']}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
