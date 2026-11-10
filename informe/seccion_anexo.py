"""Anexos del informe que se generan de los mismos modelos que el cuerpo del capítulo 2.

Los informes de referencia solo llevan en el cuerpo los diagramas de cada flujo de trabajo y dejan los estándares de codificación en los anexos. Lo que este proyecto
tiene de más sale de los mismos modelos que el cuerpo, así que no puede diferir de él: sale de `modelo/analisis.py`, `modelo/diseno.py`, `modelo/realizaciones.py`, `modelo/implementacion.py`, `modelo/pruebas.py`
y `modelo/trazabilidad.py`.

Cada anexo empieza con un título de nivel 1 (que el generador del informe numera 6.1, 6.2, …) y sigue con títulos de nivel 2 y 3.
"""

import seccion_analisis
import seccion_diseno
import seccion_implementacion
import seccion_pruebas
import seccion_validacion

TITULO_ESTANDARES = "Anexo A. Estándares de codificación"
TITULO_DETALLE = "Detalle del análisis, del diseño y de la implementación"
TITULO_PRUEBAS = "Pruebas: plan, procedimientos y resultados"
TITULO_VALIDACION = "Anexo C. Validación, verificación y auditoría"
TITULO_HOJA = "Anexo D. Hoja del segundo examen parcial"


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


def hoja():
    """La hoja escrita a mano del segundo examen parcial (foto en `recursos/hoja-examen.jpg`), como la última página de los anexos de los informes de referencia."""
    return "\n".join([f"# {TITULO_HOJA}\n",
                      "Hoja del segundo examen parcial del equipo, con la propuesta de agregar un generador automático de Flutter a la herramienta CASE colaborativa.\n",
                      "![Hoja del segundo examen parcial](recursos/hoja-examen.jpg)\n"])


# Los anexos del informe son A (estándares), B (reentrenamiento de la IA, de `docs/REENTRENAMIENTO_IA.md`), C (validación, verificación y auditoría) y D (la hoja del examen), como en los informes de
# referencia, que solo llevan los estándares de codificación. `detalle` y `pruebas` generan el detalle del análisis, del diseño y de la implementación y el plan y los
# resultados de las pruebas; no se incluyen en el informe por decisión del equipo (demasiado para un anexo), pero siguen disponibles aquí.
ANEXOS = [(TITULO_ESTANDARES, estandares), (TITULO_VALIDACION, validacion), (TITULO_HOJA, hoja)]
ANEXOS_OPCIONALES = [(TITULO_DETALLE, detalle), (TITULO_PRUEBAS, pruebas)]
