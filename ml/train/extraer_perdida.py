"""Extrae la pérdida del log crudo de mlx-lm a un CSV (iteración, tipo, pérdida).

Entiende las dos formas del log: la tabla con colores de las versiones nuevas de
mlx-lm ("  25  val 0.391 ..." y "  30  0.356 ▼ ...") y la de una línea por registro
("Iter 25: Val loss 0.391").

    ml/.venv/bin/python ml/train/extraer_perdida.py train.log loss.csv
"""

import csv
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
CLASICO = re.compile(r"Iter (\d+): (Train|Val) loss ([0-9.]+)")
TABLA_VAL = re.compile(r"^\s*(\d+)\s+val\s+([0-9.]+)", re.MULTILINE)
TABLA_TRAIN = re.compile(r"^\s*(\d+)\s+([0-9.]+)\s+[▲▼=]", re.MULTILINE)


def main(origen, destino):
    texto = ANSI.sub("", open(origen, encoding="utf-8").read())
    filas = [(int(i), tipo.lower(), float(valor)) for i, tipo, valor in CLASICO.findall(texto)]
    filas += [(int(i), "val", float(valor)) for i, valor in TABLA_VAL.findall(texto)]
    filas += [(int(i), "train", float(valor)) for i, valor in TABLA_TRAIN.findall(texto)]
    filas.sort(key=lambda f: (f[0], f[1]))
    with open(destino, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["iteracion", "tipo", "perdida"])
        escritor.writerows(filas)
    entrenamiento = [f[2] for f in filas if f[1] == "train"]
    validacion = [f[2] for f in filas if f[1] == "val"]
    if entrenamiento:
        print(f"pérdida de entrenamiento: {entrenamiento[0]:.3f} -> {entrenamiento[-1]:.3f} ({len(entrenamiento)} registros)")
    if validacion:
        print(f"pérdida de validación:    {validacion[0]:.3f} -> {validacion[-1]:.3f} ({len(validacion)} registros)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
