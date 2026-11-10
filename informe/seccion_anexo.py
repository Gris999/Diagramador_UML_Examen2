"""Anexos D a G del informe, generados de los mismos modelos que el cuerpo del capítulo 2.

Los informes de referencia solo llevan en el cuerpo los diagramas de cada flujo de trabajo y dejan los estándares de codificación en los anexos. Lo que este proyecto
tiene de más (el detalle del análisis, del diseño y de la implementación, el plan y los resultados de las pruebas, y la validación, verificación y auditoría) está aquí,
así que no puede diferir del cuerpo: sale de `modelo/analisis.py`, `modelo/diseno.py`, `modelo/realizaciones.py`, `modelo/implementacion.py`, `modelo/pruebas.py`
y `modelo/trazabilidad.py`.

Cada anexo empieza con un título de nivel 1 (que el generador del informe numera 6.4, 6.5, …) y sigue con títulos de nivel 2 y 3.
"""

import seccion_analisis
import seccion_diseno
import seccion_implementacion
import seccion_pruebas
import seccion_validacion

TITULO_ESTANDARES = "Anexo D. Estándares de codificación"
TITULO_DETALLE = "Anexo E. Detalle del análisis, del diseño y de la implementación"
TITULO_PRUEBAS = "Anexo F. Pruebas: plan, procedimientos y resultados"
TITULO_VALIDACION = "Anexo G. Validación, verificación y auditoría"


def estandares():
    return "\n".join([f"# {TITULO_ESTANDARES}\n",
                      "Estos son los estándares de codificación que se siguieron en cada pila del sistema, con la razón de cada uno.\n",
                      seccion_implementacion.estandares()])


def detalle():
    return "\n".join([f"# {TITULO_DETALLE}\n",
                      "Este anexo amplía el análisis (sección 2.2), el diseño (sección 2.3) y la implementación (sección 2.4) con el detalle que el cuerpo del capítulo 2 no repite: "
                      "las fichas de las clases, los flujos de sucesos de cada realización, la arquitectura con sus subsistemas e interfaces, las clases de diseño con los nombres "
                      "reales del código y la tabla de componentes con su traza al diseño.\n",
                      seccion_analisis.generar_anexo(), seccion_diseno.generar_anexo(), seccion_implementacion.generar_anexo()])


def pruebas():
    return "\n".join([f"# {TITULO_PRUEBAS}\n",
                      "Este anexo completa el reporte de prueba de la sección 2.5: el plan, los procedimientos manuales, la ejecución de las pruebas automáticas, los defectos que se encontraron, "
                      "la evaluación y el índice que une cada caso de prueba con el código.\n",
                      seccion_pruebas.generar_anexo()])


def _bajar(md):
    """Quita el título de nivel 2 de la primera línea y baja un nivel los demás (## queda como título del anexo)."""
    lineas = md.split("\n")
    salida = []
    for n, linea in enumerate(lineas):
        if n == 0 and linea.startswith("## "):
            continue
        salida.append(linea[1:] if linea.startswith("###") else linea)
    return "\n".join(salida)


def validacion():
    return "\n".join([f"# {TITULO_VALIDACION}\n", _bajar(seccion_validacion.generar_anexo())])


# (título del anexo, función que lo genera), en el orden en que van después del anexo C
ANEXOS = [(TITULO_ESTANDARES, estandares), (TITULO_DETALLE, detalle), (TITULO_PRUEBAS, pruebas), (TITULO_VALIDACION, validacion)]
