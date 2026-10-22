"""Tablas en Markdown de una corrida (totales y por operación), para pegar en el informe.

    python ml/eval/reporte.py ml/runs/dia2
"""

import hashlib
import json
import sys
from pathlib import Path


def cargar(corrida, nombre):
    return json.loads((corrida / f"eval-{nombre}.json").read_text(encoding="utf-8"))["resumen"]


def tablas(corrida: Path) -> str:
    r = {n: cargar(corrida, n) for n in ("base", "reentrenado", "ollama")}
    total = ["| Modelo | JSON válido | Respuestas exactamente correctas | Tiempo promedio |", "|---|---|---|---|"]
    etiquetas = {"base": "Qwen3-4B base, sin entrenar", "reentrenado": "Reentrenado con LoRA (MLX)",
                 "ollama": "Reentrenado y desplegado en Ollama (int4)"}
    for n, resumen in r.items():
        n_ej = resumen["ejemplos"]
        total.append(f"| {etiquetas[n]} | {resumen['json_valido']}/{n_ej} | **{resumen['correctos']}/{n_ej}** "
                     f"({100 * resumen['correctos'] / n_ej:.0f} %) | {resumen['segundos_promedio']} s |")
    por_op = ["| Operación | Base | Reentrenado | Ollama |", "|---|---|---|---|"]
    for op in sorted(r["base"]["por_operacion"]):
        celdas = [f"{r[n]['por_operacion'][op]['correctos']}/{r[n]['por_operacion'][op]['total']}" for n in r]
        por_op.append(f"| {op.replace('_', ' ')} | " + " | ".join(celdas) + " |")
    return "\n".join(total) + "\n\n" + "\n".join(por_op)


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


if __name__ == "__main__":
    carpeta = Path(sys.argv[1])
    print(tablas(carpeta))
    adaptador = carpeta / "adapters" / "adapters.safetensors"
    if adaptador.exists():
        print(f"\nadaptador: {adaptador.stat().st_size} bytes, sha256 {sha256(adaptador)}")
