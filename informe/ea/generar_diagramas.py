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
import etiquetas  # noqa: E402
import especificaciones  # noqa: E402

DESTINO = AQUI.parent / "build" / "ea"

if __name__ == "__main__":
    # `--solo requisitos`: diagramas de casos de uso (modelo/requisitos.py). `--solo analisis`: diagramas del análisis
    # (modelo/analisis.py); `--solo analisis:COL-01,COL-09` solo esas colaboraciones (para probar). `--solo diseno[:COL-01,ARQ]`: lo mismo para el diseño.
    solo = sys.argv[sys.argv.index("--solo") + 1] if "--solo" in sys.argv else ""
    if solo == "requisitos":
        import casos_de_uso

        base = especificaciones.Modelo()
        casos_de_uso.construir(base)
        modelo = dict(elementos=base.elementos, diagramas=base.diagramas)
    elif solo.startswith("diseno"):
        import diseno

        base = especificaciones.Modelo()
        diseno.construir(base, solo.split(":")[1].split(",") if ":" in solo else None)
        modelo = dict(elementos=base.elementos, diagramas=base.diagramas)
    elif solo.startswith("analisis"):
        import analisis

        base = especificaciones.Modelo()
        analisis.construir(base, solo.split(":")[1].split(",") if ":" in solo else None)
        modelo = dict(elementos=base.elementos, diagramas=base.diagramas)
    else:
        modelo = especificaciones.construir()
    print(f"{len(modelo['diagramas'])} diagramas, {len(modelo['elementos'])} elementos")
    if etiquetas.hay_automaticos(modelo):
        # EA pone las etiquetas de los mensajes donde no se leen: se mide la primera pasada y se corrigen (ver etiquetas.py).
        paso1 = DESTINO.parent / "ea_paso1"
        constructor.ejecutar(etiquetas.paso1(modelo), paso1, espera=1500)
        print(etiquetas.paso2(modelo, paso1), "etiquetas ubicadas junto a su flecha")
    log = constructor.ejecutar(modelo, DESTINO, espera=1500)
    errores = [linea for linea in log.splitlines() if "ERROR" in linea]
    listos = [linea for linea in log.splitlines() if " ok " in linea]
    print(f"{len(listos)} diagramas exportados; {len(errores)} errores")
    for linea in errores[:30]:
        print(linea)
    print("terminó" if "FIN" in log else "NO terminó (revisar ea.log)")
