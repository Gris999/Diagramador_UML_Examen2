"""Sección 2.6 del informe: validación, verificación y auditoría, generada de `modelo/trazabilidad.py`.

Los cuatro pasos que pidió el docente: 1) la documentación (capítulos 1 y 2); 2) la validación; 3) la verificación (control de calidad); 4) la auditoría.
Todo se calcula del modelo y del repositorio al generar el informe y `trazabilidad.validar()` falla si algo no coincide.
"""

import subprocess

from modelo import diseno as D
from modelo import pruebas as P
from modelo import realizaciones as RZ
from modelo import requisitos as R
from modelo import trazabilidad as T

ORDEN_PILA = {"back": 0, "front": 1, "java": 2}


def miles(n):
    return f"{n:,}".replace(",", ".")


def _ids_de_pruebas():
    citadas = {ref for c in P.CASOS_DE_PRUEBA for ref in c["auto"]} | {ref for d in P.DEFECTOS for ref in d["pruebas"]}
    ordenadas = sorted(citadas, key=lambda r: (ORDEN_PILA[r[0]], r[1], r[2]))
    return {ref: f"T-{n:03d}" for n, ref in enumerate(ordenadas, 1)}


def _rango(ids):
    """['CP-1.B', 'CP-1.A1', …] → texto corto: «CP-1.B a CP-1.N1 (5)»."""
    return f"{ids[0]} a {ids[-1]} ({len(ids)})" if len(ids) > 1 else ids[0]


def _git(*args):
    return subprocess.run(["git", "-C", str(T.RAIZ), *args], capture_output=True, text=True, check=True).stdout.strip()


def generar():
    resumen = T.validar()
    ver = resumen["verificacion"]
    filas = T.matriz()
    tests = _ids_de_pruebas()
    cobertura = T.cobertura_del_codigo()
    aud = T.auditoria()
    revisados, _, descartados = T.escanear_secretos()
    dep = T.dependencias()

    md = ["## 2.6 Validación, verificación y auditoría\n",
          "Cerrada la documentación (capítulos 1 y 2), faltan tres pasos que comprueban que lo documentado y lo construido son lo mismo. La **validación** responde si se construyó "
          "el producto correcto: todo lo que está en el documento está en el software, en dos niveles, el del **producto** (los casos de uso y los requisitos) y el de la **calidad** "
          "(seguridad, fiabilidad, costo, recuperación, mantenibilidad, interoperabilidad y usabilidad). La **verificación** es el control de calidad que responde si se construyó bien: "
          "todo lo registrado en el documento está en el software **y al revés**, y cada diagrama de secuencia corresponde a operaciones reales del código. La **auditoría** comprueba "
          "que el proceso fue correcto y que cada versión está guardada y se puede rastrear.\n",
          "Estas comprobaciones no se hacen a mano: la sección se genera de un modelo que lee el repositorio y falla si encuentra una celda vacía, una operación que no existe en el código, "
          "una clase del código sin explicar o un secreto escrito en un archivo. Si falla, el informe no se genera.\n"]

    md += ["### 2.6.1 Matriz de trazabilidad\n",
           "Cada fila sigue un caso de uso a lo largo de todos los flujos de trabajo: los requisitos que cubre, las colaboraciones del análisis (sección 2.2), las realizaciones del diseño "
           "con sus diagramas de secuencia (sección 2.3), el código que las implementa (sección 2.4) y los casos de prueba (sección 2.5). No tiene celdas vacías.\n",
           "| Caso de uso | Requisitos | Análisis | Diseño: realización · escenarios · mensajes | Implementación: clases · archivos | Pruebas: casos · automáticas · manuales |", "|---|---|---|---|---|---|"]
    for f in filas:
        md.append(f"| {f['cu']}: {f['nombre']} | {', '.join(f['rf'])} | {', '.join(f['analisis'])} | {', '.join(f['diseno'])} · {f['escenarios']} · {f['mensajes']} | "
                  f"{len(f['clases'])} · {len(f['archivos'])} | {_rango(f['casos'])} · {f['automaticas']} · {f['manuales']} |")
    unicas = [r for r in RZ.REALIZACIONES if r['col'] in {d for f in filas for d in f['diseno']}]
    md.append(f"| **Total** | {len({r for f in filas for r in f['rf']})} requisitos | {len({a for f in filas for a in f['analisis']})} colaboraciones | "
              f"{len(unicas)} realizaciones · {sum(len(r['escenarios']) for r in unicas)} · {sum(len(e['mensajes']) for r in unicas for e in r['escenarios'])} | "
              f"{len({c for f in filas for c in f['clases']})} clases · {len({a for f in filas for a in f['archivos']})} archivos | "
              f"{sum(len(f['casos']) for f in filas)} casos · {len({r for c in P.CASOS_DE_PRUEBA for r in c['auto']})} · {sum(f['manuales'] for f in filas)} |")
    md += ["", "Las columnas de escenarios y mensajes cuentan los diagramas de secuencia de la realización del diseño; una clase, un archivo o una realización que usan varios casos de uso se cuenta una vez "
           "en el total. Un caso de uso puede tener más de una colaboración y una colaboración puede realizar más de un caso de uso (por ejemplo, COL-08 realiza CU7 y CU9).\n"]

    md += ["#### Requisitos del proyecto\n",
           "Cada requisito de `docs/REQUIREMENTS.md` lo cubre un caso de uso o un requisito adicional (RA, sección 2.1.8) o es la documentación misma.\n",
           "| Requisito | Qué pide | Lo cubre |", "|---|---|---|"]
    md += [f"| {i} | {g} | {c} |" for i, g, c in T.requisitos_del_proyecto()]
    md.append("")

    md += ["### 2.6.2 Validación del producto\n",
           "El producto es el correcto si cada camino de cada caso de uso, tal como lo promete su ficha, ocurre en el software. Eso es justamente lo que mide la sección 2.5: "
           f"los {len(R.CASOS)} casos de uso tienen {len(P.caminos_del_modelo())} caminos, cada uno con su caso de prueba, y todos tienen pruebas automáticas que pasan; "
           f"{sum(f['manuales'] for f in filas)} caminos se ejecutaron además a mano en el navegador con la IA real y todos pasaron. Al preparar esas pruebas aparecieron {len(P.DEFECTOS)} "
           "defectos en los que el software no hacía lo que decía el documento (o al revés), y se corrigieron (sección 2.5.5). La validación del producto se cumple con este resultado: "
           f"los {len(T.requisitos_del_proyecto())} requisitos de la tabla anterior están cubiertos y cada camino prometido ocurre en el software.\n"]

    md += ["### 2.6.3 Validación de la calidad\n",
           "El segundo nivel pregunta si el producto, además de hacer lo que promete, tiene las cualidades que se necesitan. Cada atributo de calidad se demuestra con pruebas que existen "
           "(identificadas con el índice T-nnn de la sección 2.5.7 cuando una prueba ya figuraba allí):\n",
           "| Atributo | Qué se exige | Cómo se verificó | Pruebas |", "|---|---|---|---|"]
    for atributo, exige, como, refs in T.calidad():
        nombres = "<br>".join(f"{P.NOMBRE_PILA[p]}: `{a.split('/')[-1]}` · {n.split('.')[-1] if p != 'front' else n}" for p, a, n in refs)
        md.append(f"| {atributo} | {exige} | {como} | {nombres} |")
    md += ["", "Los requisitos adicionales del modelo de requisitos (sección 2.1.8) se demuestran así:\n", "| Requisito adicional | Evidencia |", "|---|---|"]
    for ra in R.REQUISITOS_ADICIONALES:
        texto, refs, archivos = T.EVIDENCIA_RA[ra[0]]
        pruebas = "; ".join(f"`{n.split('.')[-1] if p != 'front' else n}`" for p, a, n in refs)
        files = ("; archivos: " + ", ".join(f"`{x}`" for x in archivos)) if archivos else ""
        md.append(f"| {ra[0]}: {ra[1]} | {texto} Pruebas: {pruebas}{files}. |")
    md.append("")

    md += ["### 2.6.4 Verificación: del documento al software\n",
           "Todo lo que el diseño dice del software se compara con el código. La comparación la hace el modelo de diseño con un índice del código (lee las clases y los métodos de los archivos Python, "
           "TypeScript y Java) cada vez que se arma el informe:\n",
           "| Lo que dice el documento | Cuántos | Qué se comprueba en el código |", "|---|---|---|",
           f"| Subsistemas de diseño | {ver['subsistemas']} | Cada uno tiene su subsistema de implementación y sus componentes (sección 2.4) |",
           f"| Clases de diseño | {ver['clases']} | Existe esa clase (o módulo) en ese archivo |",
           f"| Interfaces (puertos) | {ver['interfaces']} | Existe la interfaz y la realizan las clases que el diseño dice |",
           f"| Asociaciones entre clases | {ver['asociaciones']} | El código de la clase de origen nombra a la de destino (la inyecta, la importa o la crea) |",
           f"| Realizaciones del diseño | {ver['realizaciones']} | Una por cada colaboración del análisis (18 colaboraciones realizan los 14 casos de uso) |",
           f"| Diagramas de secuencia | {ver['escenarios']} | Cada uno es un escenario de una realización |",
           f"| Mensajes de secuencia | {ver['mensajes']} | Cada mensaje es una operación que existe en la clase que lo recibe ({ver['operaciones']} operaciones distintas; {ver['externos']} mensajes marcados como del navegador o de un producto externo no se comprueban) |",
           f"| Dependencias entre subsistemas | — | Las mismas que entre los paquetes del análisis, sin ciclos |", "",
           "El docente pidió que «el diagrama de secuencia debe estar relacionado con el software»: aquí lo está en cada mensaje. Esta comprobación encontró discrepancias que se corrigieron "
           "(sección 2.6.6), por ejemplo una colección de MongoDB que el diseño llamaba de otra manera y un camino de CU9 (analizar la consistencia del modelo) que no tenía diagrama de secuencia.\n"]

    md += ["### 2.6.5 Verificación: del software al documento\n",
           f"La otra dirección pregunta qué hay en el código que el documento no nombra. El índice del código encuentra **{cobertura['total']} clases y módulos** en las carpetas del sistema "
           f"(sin las pruebas); **{cobertura['modeladas']}** están en el diseño ({cobertura['modeladas'] * 100 // cobertura['total']} %). Las otras {len(cobertura['sin_modelar'])} no se modelan a propósito, "
           "cada una por una razón que está escrita y que se comprueba: si aparece código nuevo sin modelar y sin razón, o si una razón deja de corresponder a código, el informe no se genera.\n",
           "| Razón por la que no se modela | Cantidad | Ejemplos |", "|---|---|---|"]
    por_categoria = {}
    for (sufijo, clase), (categoria, coincidencias) in cobertura["razones"].items():
        por_categoria.setdefault(categoria, []).append(clase)
    for categoria, clases in por_categoria.items():
        ejemplos = ", ".join(f"`{c}`" for c in clases[:4]) + (" …" if len(clases) > 4 else "")
        md.append(f"| {categoria} | {len(clases)} | {ejemplos} |")
    md.append("")

    md += ["### 2.6.6 Hallazgos de la verificación\n",
           "Verificar en las dos direcciones encontró diferencias entre el documento y el software. Todas se corrigieron y las que cambiaron el comportamiento tienen una prueba "
           "que fallaba antes (sección 2.5.5):\n",
           "| Hallazgo | Dirección | Qué se hizo |", "|---|---|---|",
           "| `POST /api/chatbot/` seguía publicado: pedía cambios a la IA sin turno ni topes de uso y la aplicación ya no lo usaba | Software sin documento | Se eliminó el endpoint y se agregó una prueba de que no existe |",
           "| El diseño llamaba `conversation_messages` a la colección de mensajes y le daba campos (`id`, `actor_id`) que el código no tiene | Documento distinto del software | Se corrigió el diseño y la implementación (sección 2.4.5) comprueba los nombres de las colecciones y de sus campos |",
           "| El análisis de consistencia del modelo (CU9, camino A3) no tenía clase de diseño ni diagrama de secuencia | Software sin documento | Se agregó `UmlValidationService` y el escenario «analizar la consistencia del modelo» a COL-11 |",
           "| La ficha de CU1 decía que un código mal escrito «avisa y vuelve a la portada» y el software abría cualquier texto como sala (D-01) | Documento sin software | Se implementó la validación del código y se corrigió la ficha (A1 y A2) |",
           "| La ficha de CU2 prohíbe relaciones sin clase en un extremo y el software las dejaba colgadas y las exportaba (D-02, D-03) | Documento sin software | Se impidió en el lienzo y en la exportación |",
           "| Las fichas de CU11 y CU12 prometen avisar si el generador falla y el software solo escribía en la consola (D-04) | Documento sin software | Se muestra un aviso claro |",
           "| La ficha de CU4 permite volver a entrar tras una expulsión y el software volvía a expulsar a quien volvía sin recargar (D-05) | Documento sin software | Se corrigió el estado de la expulsión |",
           "| La ficha de CU14 decía que ante un fallo de la IA se «remite al manual» y el software solo muestra un mensaje (D-07) | Documento distinto del software | Se corrigió la ficha |",
           "| Varios requisitos del proyecto no los citaba ningún caso de uso (por ejemplo RF-13, RF-15 a RF-17, RF-22, RF-34, RF-35, RNF-06) | Documento incompleto | Se agregaron a las fichas de CU3, CU6, CU12, CU13 y CU14 y se comprobó que todos quedan cubiertos |", ""]

    md += ["### 2.6.7 Auditoría\n",
           "La auditoría revisa el proceso y sus versiones. Todo el trabajo está en un repositorio de Git, con una copia en GitHub (el código QR de la carátula lleva a ella), de modo que cada "
           "cambio se puede rastrear a quién lo hizo, cuándo y por qué.\n",
           "**Versiones.**\n",
           "| Dato | Valor |", "|---|---|",
           f"| Repositorio en GitHub (`origin`) | {aud['remotos'].get('origin', '—').removesuffix('.git')} |",
           f"| Repositorio del que se partió (`upstream`) | {aud['remotos'].get('upstream', '—').removesuffix('.git')} |",
           f"| Línea base del primer parcial | etiqueta `{aud['base']['etiqueta']}`, commit `{aud['base']['commit']}` ({aud['base']['fecha']}) |",
           f"| Etiquetas | {', '.join(f'`{e}`' for e in aud['etiquetas'])} |",
           f"| Ramas locales | {', '.join(f'`{r}`' for r in aud['ramas'])} |",
           f"| Commits en total y desde la línea base | {aud['commits_total']} y {aud['desde_base']} |",
           f"| Commits desde la línea base por tipo | {', '.join(f'{n} {t}' for t, n in sorted(aud['tipos'].items(), key=lambda kv: -kv[1]))} |",
           f"| Personas que aportaron al repositorio | {', '.join(f'{n} ({c})' for n, c in sorted(aud['autores'].items(), key=lambda kv: -kv[1]))} |",
           f"| Estado al generar este informe | rama `{aud['rama']}`, commit `{aud['cabeza']}`, {aud['fecha']}; {aud['archivos']} archivos rastreados |", "",
           "**Calidad del proceso.** Cada commit tiene un solo propósito y su mensaje dice qué cambia y en qué construcción o fase ocurre (`(C1)` a `(C4)`, `(F5)`). Antes de entrar, cada commit pasa "
           "una revisión automática que compara el cambio con las reglas de `AGENTS.md` y lo rechaza si las incumple; las pruebas se ejecutan antes de dar un trabajo por terminado.\n"]
    sin_revision = _git("log", "--fixed-strings", "--grep=without the automatic review", "--date=short", "--pretty=format:%h (%ad)").splitlines()
    if sin_revision:
        md += ["**Excepciones registradas.** La cuota del servicio de la revisión automática se agotó durante la preparación de este documento. Por eso "
               f"{'un commit entró' if len(sin_revision) == 1 else f'{len(sin_revision)} commits entraron'} sin esa revisión, con autorización expresa de quien dirige el proyecto, y "
               f"{'su mensaje lo dice' if len(sin_revision) == 1 else 'sus mensajes lo dicen'}: " + ", ".join(f"`{x}`" for x in sin_revision) + ". Tenían sus pruebas en verde.\n"]

    md += ["**Secretos.** "
           f"Se buscaron claves de Google y de AWS, tokens de GitHub, llaves privadas, contraseñas escritas en asignaciones y direcciones con usuario y contraseña en los {revisados} archivos de "
           f"texto que Git rastrea: **0 hallazgos**. {len(descartados)} coincidencias eran identificadores anónimos (UUID) escritos a mano en las pruebas. "
           f"El archivo `.env` {'está' if aud['env_ignorado'] else 'NO está'} en `.gitignore` y {'no' if not aud['env_rastreado'] else 'SÍ'} lo rastrea Git; en el repositorio solo está `.env.example`, con los nombres de las variables. "
           "La contraseña que estuvo escrita en un commit antiguo se rotó el 2026-10-22 en el servidor y en la base local (ver `docs/GAP_MATRIX.md`).\n",
           "**Dependencias.** Versiones de las piezas principales, leídas de los archivos de cada proyecto:\n",
           "| Proyecto | Versiones |", "|---|---|",
           f"| Backend Django (`requirements.txt`, {dep['python_total']} paquetes) | {', '.join(f'{n} {v}' for n, v in dep['python'])} |",
           f"| Frontend Angular (`package.json`, {dep['front_total']} paquetes) | {', '.join(f'{n} {v}' for n, v in dep['front'])} |",
           f"| Generador Spring (`pom.xml`) | {', '.join(f'{n} {v}' for n, v in dep['java'])} |", "",
           "**Cómo repetir las comprobaciones.** Cualquiera puede repetirlas desde el repositorio:\n",
           "- Django: `back_generador_bd/.venv/bin/python back_generador_bd/manage.py test` (las que usan base de datos, dentro del contenedor: `docker exec django_backend_UML python manage.py test`).",
           "- Angular: `npx ng test --watch=false --browsers=ChromeHeadless` en `front_generador_bd`.",
           "- Spring: `./mvnw test` en `back_generator_uml` (compila el proyecto que genera).",
           "- MongoDB real: `MONGO_TEST_URL=mongodb://127.0.0.1:27018 manage.py test collab.tests.test_mongo_integration` con un contenedor `mongo:7`.",
           "- Este documento: `python generar_informe.py` en `informe/`, que corre todas las validaciones de las secciones 2.4 a 2.6 antes de escribir el archivo.",
           "- Despliegue: `scripts/smoke-test.sh`.", "",
           "**Limitaciones conocidas que la auditoría deja a la vista.**\n",
           "- Los endpoints de imagen y de audio (`/api/uml_from_image/` y `/api/uml_from_audio/`) no tienen topes de uso propios como el chat y la ayuda: las tres peticiones comparten solo la cuota del proveedor de IA.",
           "- La rama de trabajo del segundo parcial está en el repositorio local; subirla a GitHub y desplegarla en AWS se hace con la aprobación de quien dirige el proyecto.",
           "- Lo que todavía no se probó, y por eso no se afirma, está en la sección 2.5.6.\n"]
    return "\n".join(md)


if __name__ == "__main__":
    import sys

    sys.stdout.write(generar())
