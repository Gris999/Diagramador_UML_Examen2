"""Anexo D del informe: detalle del análisis y del diseño.

Reúne lo que el análisis y el diseño del proyecto tienen de más que el documento de referencia (que solo pide los diagramas del cuerpo del capítulo 2):
requisitos especiales comunes, flujos de sucesos con sus clases participantes, fichas de las clases del análisis, nodos, subsistemas con interfaces,
mecanismos, modelo C4, clases de diseño y detalle de las realizaciones. Se genera de los mismos modelos que el cuerpo (`modelo/analisis.py`,
`modelo/diseno.py` y `modelo/realizaciones.py`), así que no puede diferir de él.
"""

import seccion_analisis
import seccion_diseno

TITULO = "Anexo D. Detalle del análisis y del diseño"


def generar():
    return "\n".join([f"# {TITULO}\n",
                      "Este anexo amplía el análisis (sección 2.2) y el diseño (sección 2.3) con el detalle que el cuerpo del capítulo 2 no repite: las fichas de las clases, "
                      "los flujos de sucesos de cada realización, la arquitectura con sus subsistemas e interfaces, y las clases de diseño con los nombres reales del código.\n",
                      seccion_analisis.generar_anexo(), seccion_diseno.generar_anexo()])
