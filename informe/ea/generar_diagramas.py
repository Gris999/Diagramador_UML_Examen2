"""Genera en Enterprise Architect todos los diagramas del informe y deja las imágenes en `build/ea/`.

Uso:  python3 informe/ea/generar_diagramas.py

Necesita CrossOver con una botella «Enterprise Architect 17.2» donde esté instalado EA (ver `constructor.py`).
Además de las imágenes deja `build/ea/modelo.qea`, el modelo de EA con todos los elementos y diagramas.
"""

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

import constructor  # noqa: E402
import especificaciones  # noqa: E402

DESTINO = AQUI.parent / "build" / "ea"

if __name__ == "__main__":
    modelo = especificaciones.construir()
    print(f"{len(modelo['diagramas'])} diagramas, {len(modelo['elementos'])} elementos")
    log = constructor.ejecutar(modelo, DESTINO, espera=1500)
    errores = [linea for linea in log.splitlines() if "ERROR" in linea]
    listos = [linea for linea in log.splitlines() if " ok " in linea]
    print(f"{len(listos)} diagramas exportados; {len(errores)} errores")
    for linea in errores[:30]:
        print(linea)
    print("terminó" if "FIN" in log else "NO terminó (revisar ea.log)")
