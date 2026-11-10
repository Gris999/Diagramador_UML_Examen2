"""Sección 2.5 del informe y Anexo F: flujo de trabajo de pruebas (PUDS cap. 12), generada de `modelo/pruebas.py`.

Plan de prueba, un caso de prueba por cada camino de cada caso de uso, procedimientos manuales con su ejecución, resultados de la ejecución completa,
defectos y evaluación. Cada prueba automática que se cita existe en el repositorio (`pruebas.validar()` lo comprueba al generar el informe).
"""

from modelo import pruebas as P
from modelo import requisitos as R

ORDEN_PILA = {"back": 0, "front": 1, "java": 2}
NOMBRE_CAMINO = {"B": "Básico", "A": "Alterno", "E": "Excepción", "N": "No permitido"}


def _etiqueta(camino):
    numero = camino[1:]
    return NOMBRE_CAMINO[camino[0]] + (f" {numero}" if numero else "")


def _celda(texto):
    return texto.replace("|", "\\|").replace("\n", " ")


def _ids_de_pruebas():
    """Identificador T-nnn de cada prueba automática citada, en el orden del índice (pila, archivo y nombre)."""
    citadas = {ref for c in P.CASOS_DE_PRUEBA for ref in c["auto"]} | {ref for d in P.DEFECTOS for ref in d["pruebas"]}
    ordenadas = sorted(citadas, key=lambda r: (ORDEN_PILA[r[0]], r[1], r[2]))
    return {ref: f"T-{n:03d}" for n, ref in enumerate(ordenadas, 1)}


def _lista_ids(refs, ids):
    return ", ".join(sorted((ids[r] for r in refs), key=lambda t: int(t[2:])))


def _rango_ids(refs, ids):
    """Lista de identificadores; los consecutivos se muestran como un rango (T-004 a T-009)."""
    numeros = sorted(int(ids[r][2:]) for r in refs)
    partes, i = [], 0
    while i < len(numeros):
        j = i
        while j + 1 < len(numeros) and numeros[j + 1] == numeros[j] + 1:
            j += 1
        partes.append(f"T-{numeros[i]:03d}" if i == j else (f"T-{numeros[i]:03d}, T-{numeros[j]:03d}" if j == i + 1 else f"T-{numeros[i]:03d} a T-{numeros[j]:03d}"))
        i = j + 1
    return ", ".join(partes)


def generar():
    """Sección 2.5. Misma estructura que los documentos de referencia: solo el reporte de prueba, con el número del caso de uso en la primera columna.
    El plan, los procedimientos, la ejecución, los defectos, la evaluación y el índice de pruebas están en el Anexo F (`generar_anexo`)."""
    P.validar()
    ids = _ids_de_pruebas()
    md = ["## 2.5 Flujo de trabajo: pruebas\n",
          "### 2.5.1 Reporte de prueba\n"]
    for numero_ciclo, titulo, codigos in R.CICLOS:
        md.append(f"#### Ciclo de vida #{numero_ciclo}\n")
        md += ["| CU | Criterios de aceptación | Datos de prueba | Procedimientos de prueba | Resultado esperado |", "|---|---|---|---|---|"]
        for cu in codigos:
            for c in P.casos_de_prueba(cu):
                procedimientos = f"Pruebas automáticas ({c['nivel']}): {_rango_ids(c['auto'], ids)}." if c["auto"] else "Sin pruebas automáticas."
                if c["manual"]:
                    procedimientos += " Procedimiento manual (Anexo F)."
                md.append(f"| {cu} | {_etiqueta(c['camino'])} ({P.id_caso(c)}) | {_celda(c['entrada'])} | {procedimientos} | {_celda(c['esperado'])} |")
        md.append("")
    md += ["Los identificadores T-nnn son los del índice de pruebas automáticas (Anexo F), con la pila, el archivo y el nombre de cada prueba.\n"]
    return "\n".join(md)


def generar_anexo():
    """Plan, procedimientos, ejecución, defectos, evaluación e índice de las pruebas para el Anexo F (títulos de nivel 2; el generador del informe los numera 6.6.n)."""
    resumen = P.validar()
    ids = _ids_de_pruebas()
    casos = P.casos_de_prueba()
    md = []

    md += ["## Plan de prueba\n",
           f"**Cobertura.** Los {len(R.CASOS)} casos de uso tienen **{resumen['caminos']} caminos** (el básico, cada alterno, cada excepción y cada camino no permitido) y "
           f"**{resumen['casos']} casos de prueba**: uno por camino. Todos tienen pruebas automáticas ({resumen['pruebas_citadas']} pruebas distintas, de las {resumen['pruebas_del_repositorio']} "
           f"que hay en el repositorio) y {resumen['con_manual']} tienen además un procedimiento manual, porque el resultado depende de varias personas, del navegador real, de archivos que "
           "se descargan o de la IA real. El informe comprueba, cada vez que se arma, que no falta ningún camino, que ningún caso sobra y que cada prueba automática citada existe de verdad.\n",
           "**Estrategia.** Las pruebas se escriben antes que el código y se ejecutan en cada cambio. Las críticas (XMI, colaboración y "
           "sincronización, permisos y roles, reconexión y recuperación de estado, generadores, transformaciones UML y persistencia sin conexión) tienen pruebas automáticas.\n",
           "| Nivel | Qué se verifica | Herramienta |", "|---|---|---|",
           "| Unidad | Servicios y componentes del navegador, utilidades puras, servicios y vistas de Django | Jasmine y Karma (Angular), `manage.py test` (Django), JUnit (Spring) |",
           "| Integración | El WebSocket de la sala con clientes simulados, las vistas de la API con la base de datos, los adaptadores de PostgreSQL, Redis y MongoDB con las mismas pruebas de contrato, "
           "los generadores de punta a punta y la compilación del proyecto Spring generado | Django (`WebsocketCommunicator`, `APITestCase`), JUnit, MongoDB 7 en Docker |",
           "| Sistema | Varias personas en la misma sala con la IA real, el celular, los archivos que se descargan, el intercambio con otras herramientas | Procedimientos manuales en el navegador (sección «Procedimientos de prueba» de este anexo) |",
           "| Despliegue | El sitio responde, el WebSocket negocia y los puertos internos están cerrados | `scripts/smoke-test.sh` (se ejecuta después de cada despliegue) |", "",
           "**Criterios.** Un cambio entra a la rama de integración cuando compila, pasan las pruebas relevantes, no lleva secretos y no hay regresiones en roles, expulsión, XMI ni "
           "exportaciones. Las pruebas que usan base de datos se ejecutan contra PostgreSQL; los adaptadores de MongoDB, además, contra un servidor real.\n",
           "**Entorno de las pruebas manuales.** La aplicación completa en un computador (Angular, Django con Daphne, PostgreSQL, Redis y el generador Spring) y el navegador integrado de la "
           "herramienta de desarrollo. Como las pestañas de un mismo navegador comparten el almacenamiento local, cada persona se creó fijando su nombre y su identificador antes de abrir su "
           "pestaña. La IA fue Google Gemini real.\n"]

    md += ["## Procedimientos de prueba\n",
           f"Los procedimientos manuales se ejecutaron el {P.FECHA_EJECUCION}. El resultado es «pasó», o «pasó con observación» cuando algo del procedimiento no se pudo repetir o se notó algo "
           "que conviene saber; ninguno falló después de las correcciones de los defectos que se listan más abajo.\n",
           "| Caso | Pasos | Resultado |", "|---|---|---|"]
    for c in casos:
        if not c["manual"]:
            continue
        resultado, nota = P.EJECUCIONES[(c["cu"], c["camino"])]
        pasos = "<br>".join(f"{i}. {_celda(p)}" for i, p in enumerate(c["manual"], 1))
        md.append(f"| {P.id_caso(c)} ({_etiqueta(c['camino'])}) | {pasos} | **{resultado}.** {_celda(nota)} |")
    md += ["", "Otras comprobaciones manuales del mismo día, hechas con otros pasos y el mismo resultado esperado:\n", "| Caso | Qué se comprobó |", "|---|---|"]
    for (cu, camino), texto in P.EJECUCIONES_ADICIONALES.items():
        md.append(f"| {P.id_caso(dict(cu=cu, camino=camino))} ({_etiqueta(camino)}) | {_celda(texto)} |")
    md.append("")

    md += ["## Ejecución de las pruebas automáticas\n",
           f"Ejecución completa del {P.FECHA_EJECUCION}, con el código que se entrega:\n",
           "| Qué | Comando | Resultado | Estado |", "|---|---|---|---|"]
    md += [f"| {q} | `{cmd}` | {r} | {e.capitalize()} |" for q, cmd, r, e in P.RESULTADOS]
    md.append("")

    md += ["## Defectos\n",
           "Preparar las pruebas encontró defectos que las pruebas anteriores no habían visto: unos al trazar cada camino de los casos de uso contra el software, y otros al ejecutar "
           "los procedimientos en el navegador. Cada defecto se reprodujo con una prueba automática que fallaba antes de la corrección y que ahora pasa.\n",
           "| ID | Caso de uso y camino | Cómo se encontró | Efecto | Corrección | Pruebas | Estado |", "|---|---|---|---|---|---|---|"]
    md += [f"| {d['id']} | {d['cu']} ({d['camino']}) | {_celda(d['como'])} | {_celda(d['efecto'])} | {_celda(d['correccion'])} | {_lista_ids(d['pruebas'], ids)} | Corregido |"
           for d in P.DEFECTOS]
    md.append("")

    md += ["## Evaluación de la prueba\n",
           "**Compleción.** Se mide contra el modelo de casos de uso, que es lo que el sistema prometió.\n",
           "| Caso de uso | Caminos | Casos de prueba | Pruebas automáticas distintas | Procedimientos manuales ejecutados |", "|---|---|---|---|---|"]
    total_caminos = total_manuales = 0
    for cu in sorted(R.CASOS, key=R.numero):
        de_este = P.casos_de_prueba(cu)
        automaticas = {ref for c in de_este for ref in c["auto"]}
        manuales = sum(1 for c in de_este if c["manual"])
        total_caminos += len(de_este)
        total_manuales += manuales
        md.append(f"| {cu}: {R.CASOS[cu]['nombre']} | {len(de_este)} | {len(de_este)} | {len(automaticas)} | {manuales} |")
    md += [f"| **Total** | **{total_caminos}** | **{resumen['casos']}** | **{resumen['pruebas_citadas']}** | **{total_manuales}** |", "",
           f"- Caminos con caso de prueba: {resumen['casos']} de {resumen['caminos']} (100 %).",
           f"- Casos con al menos una prueba automática: {resumen['con_automatica']} de {resumen['casos']} (100 %).",
           f"- Casos con procedimiento manual: {resumen['con_manual']}, todos ejecutados.", "",
           "**Fiabilidad.** Con el código que se entrega, todas las pruebas automáticas pasan (ejecución completa, más arriba) y todos los procedimientos manuales pasan, dos de ellos con una observación. "
           f"Se encontraron {len(P.DEFECTOS)} defectos y los {len(P.DEFECTOS)} están corregidos; no hay defectos abiertos.\n",
           "**Lo que falta probar.** No se probó todavía, y por eso no se afirma:\n"]
    md += [f"- {p}" for p in P.PENDIENTES]
    md.append("")

    md += ["## Índice de pruebas automáticas\n",
           "Cada prueba automática que cita un caso o un defecto, con su pila, el archivo (relativo a la carpeta de esa pila) y su nombre. Es la matriz que une el caso de prueba con el código.\n",
           "| ID | Pila | Archivo | Prueba |", "|---|---|---|---|"]
    for ref, ident in sorted(ids.items(), key=lambda kv: int(kv[1][2:])):
        pila, archivo, nombre = ref
        md.append(f"| {ident} | {P.NOMBRE_PILA[pila]} | `{archivo}` | {_celda(nombre)} |")
    md.append("")
    return "\n".join(md)


if __name__ == "__main__":
    import sys

    sys.stdout.write(generar())
