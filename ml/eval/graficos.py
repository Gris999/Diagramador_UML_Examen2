"""Gráficos de una corrida: curva de pérdida y comparación de aciertos por operación.

Requiere matplotlib (no está en el entorno de entrenamiento: `pip install matplotlib`).

    python ml/eval/graficos.py ml/runs/dia2
"""

import csv
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

COLORES = {"base": "#9aa5b8", "reentrenado": "#3b6fd4", "ollama": "#2f9e6b"}


def curva_perdida(corrida: Path):
    filas = list(csv.DictReader(open(corrida / "loss.csv", encoding="utf-8")))
    entrenamiento = [(int(f["iteracion"]), float(f["perdida"])) for f in filas if f["tipo"] == "train"]
    validacion = [(int(f["iteracion"]), float(f["perdida"])) for f in filas if f["tipo"] == "val"]
    figura, eje = plt.subplots(figsize=(7.5, 4))
    eje.plot(*zip(*entrenamiento), color="#c9d3ea", linewidth=1, label="entrenamiento (cada 10 iteraciones)")
    if len(entrenamiento) >= 7:
        ventana = 5
        suave = [sum(v for _, v in entrenamiento[max(0, i - ventana + 1): i + 1]) / len(entrenamiento[max(0, i - ventana + 1): i + 1])
                 for i in range(len(entrenamiento))]
        eje.plot([x for x, _ in entrenamiento], suave, color="#3b6fd4", linewidth=2, label="entrenamiento (promedio móvil)")
    eje.plot(*zip(*validacion), color="#d9534f", marker="o", linewidth=2, label="validación (ejemplos no usados para entrenar)")
    eje.set_yscale("log")
    eje.set_xlabel("Iteración")
    eje.set_ylabel("Pérdida (escala logarítmica)")
    eje.set_title("Curva de pérdida del entrenamiento LoRA")
    eje.grid(alpha=0.3)
    eje.legend()
    figura.tight_layout()
    figura.savefig(corrida / "curva-perdida.png", dpi=170)
    plt.close(figura)


def comparacion(corrida: Path):
    resultados = {}
    for nombre, archivo in (("base", "eval-base.json"), ("reentrenado", "eval-reentrenado.json"), ("ollama", "eval-ollama.json")):
        ruta = corrida / archivo
        if ruta.exists():
            resultados[nombre] = json.loads(ruta.read_text(encoding="utf-8"))["resumen"]
    operaciones = sorted(resultados["base"]["por_operacion"])
    etiquetas = {"base": "Qwen3-4B base (sin entrenar)", "reentrenado": "Reentrenado (LoRA, MLX)", "ollama": "Desplegado en Ollama (int4)"}

    figura, ejes = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"width_ratios": [1, 2.6]})
    total = ejes[0]
    for indice, (nombre, resumen) in enumerate(resultados.items()):
        porcentaje = 100 * resumen["correctos"] / resumen["ejemplos"]
        total.bar(indice, porcentaje, color=COLORES[nombre], width=0.7)
        total.text(indice, porcentaje + 1.5, f"{porcentaje:.0f} %\n({resumen['correctos']}/{resumen['ejemplos']})", ha="center", fontsize=9)
    total.set_xticks(range(len(resultados)))
    total.set_xticklabels(["Base", "Reentrenado", "Ollama"], fontsize=9)
    total.set_ylim(0, 112)
    total.set_ylabel("Respuestas exactamente correctas (%)")
    total.set_title("Total")

    detalle = ejes[1]
    ancho = 0.8 / len(resultados)
    for desplazamiento, (nombre, resumen) in enumerate(resultados.items()):
        valores = [100 * resumen["por_operacion"][op]["correctos"] / resumen["por_operacion"][op]["total"] for op in operaciones]
        posiciones = [i + desplazamiento * ancho for i in range(len(operaciones))]
        detalle.bar(posiciones, valores, width=ancho, color=COLORES[nombre], label=etiquetas[nombre])
    detalle.set_xticks([i + ancho * (len(resultados) - 1) / 2 for i in range(len(operaciones))])
    detalle.set_xticklabels([op.replace("_", "\n") for op in operaciones], fontsize=6.5)
    detalle.set_ylim(0, 112)
    detalle.set_title("Por tipo de operación")
    detalle.legend(fontsize=8, loc="upper center", ncol=3)
    figura.suptitle("Conjunto de prueba: ejemplos que el modelo nunca vio", fontsize=11)
    figura.tight_layout()
    figura.savefig(corrida / "comparacion.png", dpi=170)
    plt.close(figura)


if __name__ == "__main__":
    carpeta = Path(sys.argv[1])
    curva_perdida(carpeta)
    comparacion(carpeta)
    print("gráficos en", carpeta)
