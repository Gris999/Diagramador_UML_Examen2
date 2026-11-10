"""Compila los diagramas C4 del informe (TikZ, LaTeX) y deja las imágenes en `build/latex/`.

Uso:  python3 informe/latex/compilar_c4.py

Necesita Tectonic (`brew install tectonic`; baja los paquetes de LaTeX que le faltan la primera vez) y `pdftoppm` (Poppler). Cada archivo `.tex` de esta carpeta
usa los estilos de `c4-estilos.tex` (colores y formas de C4) y produce la imagen con el identificador que el informe busca (el mismo que tenía en Enterprise Architect):
el generador del informe prefiere la imagen de `build/latex/` a la de `build/ea/`.
"""

import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI.parent / "build" / "latex"
DPI = 200

# archivo .tex -> identificador del diagrama en el informe
DIAGRAMAS = {"c4-contexto": "c4-contexto", "c4-contenedores": "di-c4-contenedores", "c4-componentes": "di-c4-componentes"}


def compilar():
    SALIDA.mkdir(parents=True, exist_ok=True)
    for fuente, identificador in DIAGRAMAS.items():
        resultado = subprocess.run(["tectonic", "-X", "compile", "--outdir", str(SALIDA), f"{fuente}.tex"], cwd=AQUI, capture_output=True, text=True)
        if resultado.returncode != 0:
            sys.exit(f"{fuente}.tex no compiló:\n{resultado.stdout[-1500:]}\n{resultado.stderr[-1500:]}")
        subprocess.run(["pdftoppm", "-r", str(DPI), "-png", "-singlefile", str(SALIDA / f"{fuente}.pdf"), str(SALIDA / identificador)], check=True)
        print(f"{fuente}.tex -> build/latex/{identificador}.png")


if __name__ == "__main__":
    compilar()
