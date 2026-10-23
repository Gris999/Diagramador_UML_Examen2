"""Genera el informe del proyecto en Word (.docx) a partir de los documentos del repositorio.

    informe/.venv/bin/python informe/generar_informe.py

Une el contenido nuevo (`informe/contenido/`) con los documentos PUDS, de IA local,
de reentrenamiento y de despliegue de `docs/`, convierte los diagramas Mermaid a
imágenes y escribe `informe/build/Informe.docx`. El PDF se obtiene abriendo ese
archivo en Word (ver `exportar_pdf.sh`).
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
INFORME = RAIZ / "informe"
BUILD = INFORME / "build"
DOCS = RAIZ / "docs"

# --- Datos de la carátula (completar lo marcado) ----------------------------------------------
TITULO = ("Plataforma CASE Colaborativa de Modelado UML 2.5 con Inteligencia Artificial como Integrante "
          "de la Sala, Generación de Backend (Spring Boot) y Flutter, e IA Local Reentrenada")
PARCIAL = "SEGUNDO PARCIAL"
NUMERO = "29"
INTEGRANTES = [("Alaca Pedro", "222007281"), ("Quenta Callejas Yohan Sebastian", "222009462")]
MATERIA = "Ingeniería de software 1"
SIGLA = "INF 422"
DOCENTE = "Ing. Martínez Canedo Rolando Antonio"
GESTION = "Semestre 2 - 2026"
LUGAR = "Santa Cruz - Bolivia"

REFERENCIAS = {
    "01-requisitos.md": "la sección 2.2", "02-analisis.md": "la sección 2.3", "03-diseno.md": "la sección 2.4",
    "04-implementacion.md": "la sección 2.5", "05-pruebas.md": "la sección 2.6", "README.md": "la sección 2.1",
    "REQUIREMENTS.md": "la lista de requisitos", "PLAN_PUDS_IA_PARTICIPANTE.md": "el plan de trabajo PUDS",
    "DESPLIEGUE.md": "el Anexo C", "GAP_MATRIX.md": "la matriz de requisitos", "IA_LOCAL.md": "el Anexo A",
    "ENTREGA.md": "el Anexo D", "DEMO.md": "el guion de la demostración", "PLAN_REENTRENAMIENTO_IA.md": "el Anexo B",
    "AI_CONTEXT.md": "el contexto del proyecto",
}
FUENTE = "Arial"
EMOJIS = {"✅": "✔", "📋": "○", "🔄": "◐", "🤖": ""}

ANCHO_UTIL_CM = 16.0
ALTO_MAX_IMAGEN_CM = 19.0


# --- Utilidades de Word ---------------------------------------------------------------------
def sombrear(elemento_pr, color):
    sombra = OxmlElement("w:shd")
    sombra.set(qn("w:val"), "clear")
    sombra.set(qn("w:color"), "auto")
    sombra.set(qn("w:fill"), color)
    elemento_pr.append(sombra)


def campo(parrafo, codigo, texto_previo=""):
    """Inserta un campo de Word (PAGE, TOC...) en el párrafo."""
    def fld(tipo):
        run = parrafo.add_run()
        c = OxmlElement("w:fldChar")
        c.set(qn("w:fldCharType"), tipo)
        run._r.append(c)
        return run

    fld("begin")
    run = parrafo.add_run()
    instruccion = OxmlElement("w:instrText")
    instruccion.set(qn("xml:space"), "preserve")
    instruccion.text = codigo
    run._r.append(instruccion)
    fld("separate")
    parrafo.add_run(texto_previo)
    fld("end")


def configurar_estilos(doc):
    """Tipografía y tamaños tomados de los informes modelo (Google Docs, Arial)."""
    from docx.enum.style import WD_STYLE_TYPE

    estilos = doc.styles
    normal = estilos["Normal"]
    normal.font.name = FUENTE
    normal.font.size = Pt(11)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.5

    # Títulos en Arial normal (no negrita): 20 / 16 / 14 gris oscuro / 12 gris / 12 gris.
    formatos = {1: (20, 0x000000), 2: (16, 0x000000), 3: (14, 0x434343), 4: (12, 0x666666), 5: (12, 0x666666)}
    for nivel, (tam, color) in formatos.items():
        h = estilos[f"Heading {nivel}"]
        h.font.name = FUENTE
        h.font.size = Pt(tam)
        h.font.bold = False
        h.font.italic = False
        h.font.color.rgb = RGBColor((color >> 16) & 255, (color >> 8) & 255, color & 255)
        for atributo in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            h.element.rPr.rFonts.set(qn(atributo), FUENTE)
        for tema in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            h.element.rPr.rFonts.attrib.pop(qn(tema), None)  # sin esto Word usa la fuente del tema (Calibri)
        h.paragraph_format.space_before = Pt(18 if nivel == 1 else 14 if nivel == 2 else 12)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.line_spacing = 1.15
        h.paragraph_format.keep_with_next = True

    # Índice: Arial 11, compacto, con puntos hasta el número de página y sangría de 18 pt por nivel.
    # Se definen con los identificadores que usa Word (TOC1...TOC5) para que los adopte al actualizar el índice.
    from docx.oxml import parse_xml

    ancho_texto = int(16.0 / 2.54 * 1440)  # 16 cm en veinteavos de punto
    for nivel in range(1, 6):
        negrita = "<w:b/>" if nivel == 1 else ""
        tam = 22 if nivel <= 3 else 20
        estilos.element.append(parse_xml(
            f'<w:style xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            f'w:type="paragraph" w:styleId="TOC{nivel}"><w:name w:val="toc {nivel}"/>'
            f'<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:autoRedefine/><w:uiPriority w:val="39"/><w:unhideWhenUsed/>'
            f'<w:pPr><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{ancho_texto}"/></w:tabs>'
            f'<w:spacing w:before="0" w:after="20" w:line="276" w:lineRule="auto"/><w:ind w:left="{360 * (nivel - 1)}"/></w:pPr>'
            f'<w:rPr>{negrita}<w:sz w:val="{tam}"/></w:rPr></w:style>'))


def configurar_pagina(doc):
    seccion = doc.sections[0]
    seccion.orientation = WD_ORIENT.PORTRAIT
    seccion.page_width, seccion.page_height = Cm(21.0), Cm(29.7)  # A4, como los modelos
    seccion.left_margin = seccion.right_margin = Cm(2.5)
    seccion.top_margin = seccion.bottom_margin = Cm(2.5)
    seccion.different_first_page_header_footer = True  # la carátula no lleva número
    pie = seccion.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    campo(pie, "PAGE", "1")
    for run in pie.runs:
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)


# --- Texto con formato en línea ---------------------------------------------------------------
PATRON_INLINE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\*[^\s*][^*]*?\*|\[[^\]]+\]\([^)]+\))")


def limpiar(texto):
    texto = re.sub(r"<br\s*/?>", " ", texto)
    for emoji, reemplazo in EMOJIS.items():
        texto = texto.replace(emoji, reemplazo)
    return texto


def agregar_inline(parrafo, texto, tam=None, negrita=False, cursiva=False, color=None):
    texto = limpiar(texto)
    for trozo in PATRON_INLINE.split(texto):
        if not trozo:
            continue
        if trozo.startswith("**") and trozo.endswith("**") and len(trozo) > 4:
            agregar_inline(parrafo, trozo[2:-2], tam, True, cursiva, color)
        elif trozo.startswith("`") and trozo.endswith("`"):
            run = parrafo.add_run(trozo[1:-1])
            run.font.name = "Menlo"
            run._r.rPr.rFonts.set(qn("w:eastAsia"), "Menlo")
            run.font.size = Pt((tam or 10.5) - 1)
            run.bold, run.italic = negrita, cursiva
            sombrear(run._r.get_or_add_rPr(), "EEF0F4")
        elif trozo.startswith("*") and trozo.endswith("*") and len(trozo) > 2:
            agregar_inline(parrafo, trozo[1:-1], tam, negrita, True, color)
        elif trozo.startswith("[") and "](" in trozo:
            etiqueta, destino = re.match(r"\[([^\]]+)\]\(([^)]+)\)", trozo).groups()
            if destino.startswith("http"):
                agregar_inline(parrafo, f"{etiqueta} ({destino})" if etiqueta != destino else destino, tam, negrita, cursiva, color)
            else:
                agregar_inline(parrafo, etiqueta, tam, negrita, cursiva, color)
        else:
            run = parrafo.add_run(trozo)
            run.bold, run.italic = negrita, cursiva
            if tam:
                run.font.size = Pt(tam)
            if color:
                run.font.color.rgb = color


# --- Bloques -----------------------------------------------------------------------------------
class Constructor:
    def __init__(self):
        self.doc = Document()
        configurar_estilos(self.doc)
        configurar_pagina(self.doc)
        self.diagramas = 0
        self.diagramas_ea = 0
        self.contador = [0, 0, 0, 0]  # para numerar documentos incluidos

    # párrafos -------------------------------------------------------------------------------
    def titulo(self, texto, nivel, salto_pagina=False):
        if salto_pagina:
            self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        texto = re.sub(r"[`*]", "", limpiar(texto)).strip()
        # Como en los informes modelo: 1., 2. y las secciones 2.1, 2.2, 2.3 a 2.5 (nivel 2) van en mayúsculas.
        if (nivel == 1 and re.match(r"^(1\.|2\.)\s", texto)) or re.match(r"^2\.[12](\.\d+)*\s|^2\.[345]\s", texto):
            texto = texto.upper()
        encabezado = self.doc.add_heading(texto, level=min(nivel, 5))
        if nivel == 3 and re.match(r"^\d+[\)\.]\s", texto):
            # Subtemas de los capítulos 5 y 6 ("1) Diseño conceptual"): negrita 12, negro.
            for run in encabezado.runs:
                run.bold = True
                run.font.size = Pt(12)
                run.font.color.rgb = RGBColor(0, 0, 0)

    def parrafo(self, texto, **kw):
        p = self.doc.add_paragraph()
        agregar_inline(p, texto, **kw)
        return p

    def lista(self, items):
        for nivel, tipo, texto, numero in items:
            p = self.doc.add_paragraph()
            sangria = 36 + 18 * nivel
            p.paragraph_format.left_indent = Pt(sangria)
            p.paragraph_format.first_line_indent = Pt(-18)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.tab_stops.add_tab_stop(Pt(sangria))
            if tipo == "bullet":
                simbolo = "➢" if texto.startswith("➢") else "●"
                agregar_inline(p, f"{simbolo}\t{texto.lstrip('➢ ')}")
            else:
                agregar_inline(p, f"{numero}.\t{texto}")

    def cita(self, lineas):
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.right_indent = Cm(0.3)
        sombrear(p._p.get_or_add_pPr(), "F1F3F9")
        agregar_inline(p, " ".join(lineas), tam=9.5, cursiva=True)

    def codigo(self, lineas):
        for linea in lineas or [""]:
            p = self.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.left_indent = Cm(0.4)
            sombrear(p._p.get_or_add_pPr(), "F3F4F6")
            run = p.add_run(linea.replace("\t", "    ") or " ")
            run.font.name = "Menlo"
            run._r.rPr.rFonts.set(qn("w:eastAsia"), "Menlo")
            run.font.size = Pt(8)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def imagen(self, ruta, pie=None, ancho_cm=None):
        ruta = Path(ruta)
        if not ruta.exists():
            self.parrafo(f"[Falta la imagen: {ruta.name}]", cursiva=True)
            return
        with Image.open(ruta) as im:
            ancho, alto = im.size
        ancho_cm = ancho_cm or min(ANCHO_UTIL_CM, 15.0)
        alto_cm = ancho_cm * alto / ancho
        if alto_cm > ALTO_MAX_IMAGEN_CM:
            ancho_cm *= ALTO_MAX_IMAGEN_CM / alto_cm
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = bool(pie)
        p.add_run().add_picture(str(ruta), width=Cm(ancho_cm))
        if pie:
            c = self.doc.add_paragraph()
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            agregar_inline(c, pie, tam=9, cursiva=True, color=RGBColor(0x55, 0x55, 0x55))

    def tabla(self, filas):
        """Tablas como en los informes modelo: ficha de caso de uso (columna naranja), cabecera amarilla."""
        ficha = all(not c.strip() for c in filas[0])  # primera fila vacía = ficha clave-valor
        if ficha:
            filas = filas[1:]
        columnas = max(len(f) for f in filas)
        tabla = self.doc.add_table(rows=0, cols=columnas)
        tabla.style = "Table Grid"
        tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
        propiedades = tabla._tbl.tblPr
        ancho = OxmlElement("w:tblW")
        ancho.set(qn("w:type"), "pct")
        ancho.set(qn("w:w"), "5000")
        propiedades.append(ancho)

        anchos = None
        if ficha:
            anchos = [6.9, ANCHO_UTIL_CM - 6.9]
        elif [c.strip() for c in filas[0]] == ["NRO", "Casos de uso", "Estado", "Prioridad", "Riesgo", "Actor"]:
            anchos = [1.6, 5.6, 2.3, 2.3, 2.0, 2.2]
        elif columnas >= 4:
            # Anchos según el contenido, para que columnas cortas como "ID" o "CU" no se partan letra por letra.
            pesos = [min(max(max(len(f[c]) if c < len(f) else 0 for f in filas), 8), 50) for c in range(columnas)]
            minimos = [min(4.0, max(1.5, 0.27 * max((len(w) for f in filas if c < len(f) for w in f[c].split()), default=4)))
                       for c in range(columnas)]
            anchos = [max(m, ANCHO_UTIL_CM * p / sum(pesos)) for m, p in zip(minimos, pesos)]
            factor = ANCHO_UTIL_CM / sum(anchos)
            anchos = [a_ * factor for a_ in anchos]
        tam = 11 if (ficha or columnas <= 3 or anchos) else 10 if columnas == 4 else 9.5
        if anchos:
            tabla.autofit = False

        for numero, fila in enumerate(filas):
            celdas = tabla.add_row().cells
            for indice in range(columnas):
                texto = fila[indice] if indice < len(fila) else ""
                celda = celdas[indice]
                if anchos:
                    celda.width = Cm(anchos[indice])
                parrafo = celda.paragraphs[0]
                parrafo.paragraph_format.space_after = Pt(4)
                parrafo.paragraph_format.space_before = Pt(4)
                parrafo.paragraph_format.line_spacing = 1.15
                encabezado = numero == 0 and not ficha
                agregar_inline(parrafo, texto, tam=tam, negrita=(ficha and indice == 0))
                if encabezado:
                    sombrear(celda._tc.get_or_add_tcPr(), "FFF2CC")
                elif ficha and indice == 0:
                    sombrear(celda._tc.get_or_add_tcPr(), "FCE5CD")
                if ficha and numero < len(filas) - 1:
                    parrafo.paragraph_format.keep_with_next = True  # la ficha no se parte entre páginas
                if not ficha and numero == 0:
                    parrafo.paragraph_format.keep_with_next = True  # la cabecera no se queda sola al pie de la página
            if numero == 0 and not ficha:
                tabla.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
        for fila_xml in tabla.rows:
            fila_xml._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def diagrama_ea(self, fuente):
        """Imagen exportada de Enterprise Architect para el bloque, si la hay (`' ea:<id>` en la primera línea)."""
        marca = re.search(r"^' ea:(\S+)", fuente, re.M)
        png = BUILD / "ea" / f"{marca.group(1)}.png" if marca else None
        if not png or not png.exists():
            return False
        self.diagramas += 1
        self.diagramas_ea += 1
        with Image.open(png) as im:
            ancho_px = im.size[0]
        self.imagen(png, pie=None, ancho_cm=min(ANCHO_UTIL_CM, max(6.0, ancho_px / 96 * 2.54)))
        return True

    def plantuml(self, fuente):
        """Diagrama UML con PlantUML; el tamaño final respeta el tamaño natural (150 dpi).

        Los diagramas que existen en Enterprise Architect (`informe/ea/`) usan esa imagen; PlantUML dibuja el
        resto (los de C4) y sirve de respaldo si falta la imagen de EA.
        """
        if self.diagrama_ea(fuente):
            return
        carpeta = BUILD / "uml"
        carpeta.mkdir(parents=True, exist_ok=True)
        huella = hashlib.sha1(fuente.encode()).hexdigest()[:10]
        entrada, salida = carpeta / f"{huella}.puml", carpeta / f"{huella}.png"
        if not salida.exists():
            entrada.write_text(fuente.replace("skinparam shadowing false", "skinparam dpi 150\nskinparam shadowing false", 1),
                               encoding="utf-8")
            resultado = subprocess.run(["plantuml", "-tpng", "-charset", "UTF-8", "-DPLANTUML_LIMIT_SIZE=16384", str(entrada)],
                                       capture_output=True, text=True, timeout=180)
            if not salida.exists():
                raise RuntimeError(f"PlantUML falló ({huella}): {resultado.stderr[-600:]}\n{fuente[:300]}")
        self.diagramas += 1
        with Image.open(salida) as im:
            ancho_px = im.size[0]
        dpi = 150 if "skinparam dpi 150" in entrada.read_text(encoding="utf-8") else 96
        ancho_cm = min(ANCHO_UTIL_CM, max(11.0, ancho_px / dpi * 2.54 * 1.5))
        self.imagen(salida, pie=None, ancho_cm=ancho_cm)

    def mermaid(self, fuente):
        # `%% ea:<id>` en el bloque: se usa la imagen de Enterprise Architect si existe (ver `plantuml`).
        marca = re.search(r"^%% ea:(\S+)", fuente, re.M)
        if marca and (BUILD / "ea" / f"{marca.group(1)}.png").exists():
            self.diagramas += 1
            self.diagramas_ea += 1
            self.imagen(BUILD / "ea" / f"{marca.group(1)}.png", pie=None, ancho_cm=ANCHO_UTIL_CM)
            return
        BUILD.joinpath("diagramas").mkdir(parents=True, exist_ok=True)
        huella = hashlib.sha1(fuente.encode()).hexdigest()[:10]
        entrada = BUILD / "diagramas" / f"{huella}.mmd"
        salida = BUILD / "diagramas" / f"{huella}.png"
        if not salida.exists():
            entrada.write_text(fuente, encoding="utf-8")
            subprocess.run(
                [str(INFORME / "node_modules/.bin/mmdc"), "-i", str(entrada), "-o", str(salida),
                 "-p", str(INFORME / "puppeteer.json"), "-s", "2", "-b", "white", "-q"],
                check=True, cwd=INFORME, timeout=180,
            )
        self.diagramas += 1
        self.imagen(salida, pie=None, ancho_cm=15.5)

    # Markdown --------------------------------------------------------------------------------
    def markdown(self, texto, desplazar=0, prefijo=None, titulo_h1=None, renumerar=False):
        """Convierte Markdown. `renumerar`: reemplaza la numeración de los títulos por `prefijo`."""
        def referencia(m):
            nombre = Path(m.group(1)).name
            return REFERENCIAS.get(nombre, nombre)

        # Los enlaces a otros documentos del repositorio no sirven en el informe: se citan por sección.
        texto = re.sub(r"\[`?([^\]`]+\.md)`?\]\([^)]*\.md[^)]*\)", referencia, texto)
        texto = re.sub(r"`(?:\.\./|docs/(?:puds/)?)?([A-Za-z0-9_\-]+\.md)`",
                       lambda m: REFERENCIAS.get(m.group(1), m.group(0)), texto)
        # Los casos de uso se citan como en los informes modelo: CU1, CU14 (no CU-01, CU-14).
        texto = re.sub(r"\bCU-0?(\d+)", r"CU\1", texto)
        lineas = texto.split("\n")
        i, lista, contadores = 0, [], [0, 0, 0, 0, 0]
        base = Path(".")
        primero = True

        def vaciar_lista():
            nonlocal lista
            if lista:
                self.lista(lista)
                lista = []

        while i < len(lineas):
            linea = lineas[i]
            if linea.startswith("```"):
                vaciar_lista()
                lenguaje = linea[3:].strip()
                i += 1
                bloque = []
                while i < len(lineas) and not lineas[i].startswith("```"):
                    bloque.append(lineas[i])
                    i += 1
                i += 1
                if lenguaje == "mermaid":
                    self.mermaid("\n".join(bloque))
                elif lenguaje == "plantuml":
                    self.plantuml("\n".join(bloque))
                else:
                    self.codigo(bloque)
                continue
            if linea.startswith("|") and i + 1 < len(lineas) and re.match(r"^\|[\s:\-|]+\|\s*$", lineas[i + 1]):
                vaciar_lista()
                filas = []
                while i < len(lineas) and lineas[i].startswith("|"):
                    if not re.match(r"^\|[\s:\-|]+\|\s*$", lineas[i]):
                        protegido = re.sub(r"`[^`]*`", lambda m: m.group(0).replace("|", "\u2502"), lineas[i])
                        celdas = [c.strip().replace("\u2502", "|").replace("\\|", "|") for c in protegido.strip().strip("|").split("|")]
                        filas.append(celdas)
                    i += 1
                self.tabla(filas)
                continue
            titulo = re.match(r"^(#{1,5})\s+(.*)$", linea)
            if titulo:
                vaciar_lista()
                nivel = len(titulo.group(1))
                texto_titulo = titulo.group(2).strip()
                if renumerar:
                    if nivel == 1:
                        if primero:
                            texto_titulo = titulo_h1 or texto_titulo
                        contadores = [0, 0, 0, 0, 0]
                        etiqueta = prefijo
                        nuevo_nivel = 2 + desplazar
                    else:
                        contadores[nivel - 1] += 1
                        for k in range(nivel, 5):
                            contadores[k] = 0
                        partes = [str(contadores[k]) for k in range(1, nivel)]
                        etiqueta = prefijo + "." + ".".join(partes)
                        nuevo_nivel = nivel + 1 + desplazar
                    sin_numero = re.sub(r"^\d+(\.\d+)*\.?\s+", "", texto_titulo)
                    self.titulo(f"{etiqueta} {sin_numero}", nuevo_nivel)
                    primero = False
                else:
                    self.titulo(texto_titulo, nivel + desplazar, salto_pagina=(nivel + desplazar == 1))
                i += 1
                continue
            imagen = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", linea)
            if imagen:
                vaciar_lista()
                pie = None
                if i + 1 < len(lineas) and re.match(r"^\*[^*].*\*\s*$", lineas[i + 1].strip()):
                    pie = lineas[i + 1].strip()[1:-1]
                    i += 1
                ruta = Path(imagen.group(2))
                if not ruta.is_absolute():
                    ruta = next((c for c in (INFORME / ruta, DOCS / ruta, BUILD / ruta, RAIZ / ruta) if c.exists()), INFORME / ruta)
                self.imagen(ruta, pie=pie)
                i += 1
                continue
            if linea.startswith(">"):
                vaciar_lista()
                cita = []
                while i < len(lineas) and lineas[i].startswith(">"):
                    cita.append(lineas[i].lstrip("> ").strip())
                    i += 1
                self.cita([c for c in cita if c])
                continue
            item = re.match(r"^(\s*)([-*])\s+(.*)$", linea)
            numerado = re.match(r"^(\s*)(\d+)\.\s+(.*)$", linea)
            if item or numerado:
                m = item or numerado
                nivel = min(len(m.group(1)) // 2, 1)
                # Continuación de un ítem en la línea siguiente (sangría sin viñeta).
                texto_item = m.group(3)
                while (i + 1 < len(lineas) and lineas[i + 1].startswith("  ") and lineas[i + 1].strip()
                       and not re.match(r"^\s*([-*]|\d+\.)\s+", lineas[i + 1])):
                    texto_item += " " + lineas[i + 1].strip()
                    i += 1
                lista.append((nivel, "bullet" if item else "num", texto_item, m.group(2) if numerado else ""))
                i += 1
                continue
            if linea.strip() == "" or linea.strip() == "---":
                vaciar_lista()
                i += 1
                continue
            vaciar_lista()
            parrafo = [linea.strip()]
            while (i + 1 < len(lineas) and lineas[i + 1].strip()
                   and not re.match(r"^(#{1,5}\s|```|\||>|!\[|\s*([-*]|\d+\.)\s+|---)", lineas[i + 1])):
                parrafo.append(lineas[i + 1].strip())
                i += 1
            p = self.parrafo(" ".join(parrafo))
            texto_parrafo = " ".join(parrafo)
            if texto_parrafo.startswith("**") and texto_parrafo.endswith("**") or texto_parrafo.startswith("*Ciclo"):
                p.paragraph_format.keep_with_next = True  # el rótulo no se separa de su diagrama o tabla
                if texto_parrafo.startswith("**") and texto_parrafo.endswith("**") and texto_parrafo.count("**") == 2:
                    for run in p.runs:
                        run.font.size = Pt(13)  # como los títulos de caso de uso del modelo
            i += 1
        vaciar_lista()

    # Carátula e índice ----------------------------------------------------------------------
    def caratula(self):
        """Carátula con las medidas del informe modelo (A4): tamaños, colores, escudo de 5 x 6,5 cm."""
        doc = self.doc

        def linea(texto="", tam=12, negrita=False, alinear=WD_ALIGN_PARAGRAPH.CENTER, antes=0, despues=0,
                  color=None, sangria=0, interlineado=None):
            p = doc.add_paragraph()
            p.alignment = alinear
            formato = p.paragraph_format
            formato.space_before, formato.space_after = Pt(antes), Pt(despues)
            formato.left_indent = Pt(sangria)
            formato.line_spacing = interlineado or 1.15
            if texto:
                r = p.add_run(texto)
                r.bold = negrita
                r.font.size = Pt(tam)
                if color:
                    r.font.color.rgb = color
            return p

        izquierda = WD_ALIGN_PARAGRAPH.LEFT
        linea("UNIVERSIDAD AUTÓNOMA GABRIEL RENÉ MORENO", 16, True, antes=10, despues=12, interlineado=1.3)
        linea("FACULTAD DE INGENIERÍA EN CIENCIAS DE LA COMPUTACIÓN Y TELECOMUNICACIONES", 14, False,
              despues=14, color=RGBColor(0x0C, 0x34, 0x3D), interlineado=1.8)
        logo = INFORME / "recursos" / "logo-facultad.png"
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(14)
        if logo.exists():
            p.add_run().add_picture(str(logo), width=Cm(5.0), height=Cm(6.5))
        linea(f"“{TITULO}”", 17, True, despues=12)
        linea(PARCIAL, 14, True, despues=6)
        linea(f"Número: {NUMERO}", 12, True, izquierda, despues=10, sangria=36)
        linea("INTEGRANTES :", 12, True, izquierda, despues=4, sangria=36)
        for nombre, registro in INTEGRANTES:
            p = linea("", 12, False, izquierda, despues=0, sangria=54, interlineado=1.45)
            p.paragraph_format.tab_stops.add_tab_stop(Pt(288))
            simbolo = p.add_run("❖  ")
            simbolo.font.size = Pt(11)
            p.add_run(nombre).font.size = Pt(12)
            p.add_run("\t")
            p.add_run(registro).font.size = Pt(12)
        linea("", 12, False, izquierda, despues=4)
        for etiqueta, valor in (("Materia: ", MATERIA), ("Sigla: ", SIGLA), ("Docente: ", DOCENTE), ("Gestión: ", GESTION)):
            p = linea("", 12, False, izquierda, despues=0, interlineado=1.45)
            r = p.add_run(etiqueta)
            r.bold = True
            r.font.size = Pt(12)
            p.add_run(valor).font.size = Pt(12)
        linea("", 12, False, despues=4)
        linea(LUGAR, 14, True)

    def indice(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        p = self.doc.add_paragraph()
        campo(p, r'TOC \o "1-5" \h \z \u', "Haz clic derecho y elige «Actualizar campo» para generar el índice.")


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8")


def pruebas_segundo_parcial(texto):
    """Casos de prueba de lo nuevo: deja fuera los que solo prueban lo del primer parcial (editor, XMI, generadores)."""
    salida = []
    for linea in texto.split("\n"):
        if linea.startswith("## 2. Casos de prueba"):
            salida += [linea, "", "Se listan las pruebas de lo nuevo en este parcial y las de la colaboración y los roles, que "
                       "cambiaron; las pruebas del editor, de XMI y de los generadores son del primer parcial y no se repiten.", ""]
            continue
        m = re.match(r"^\| (CP-\d+) \| ([^|]*) \|(.*)$", linea)
        if not m:
            salida.append(linea)
            continue
        cp, cus_texto, resto = m.groups()
        codigos = set()
        for a, b in re.findall(r"CU-(\d+)(?:…(\d+))?", cus_texto):
            codigos.update(range(int(a), int(b or a) + 1))
        if not codigos:  # transversal (por ejemplo, el despliegue)
            salida.append(linea)
        elif any(n >= 14 or n in (3, 4) for n in codigos):
            salida.append(f"| {cp} | {', '.join(f'CU-{n:02d}' for n in sorted(codigos))} |{resto}")
    return "\n".join(salida)


def seccion_de(texto, desde, hasta=None):
    """Recorta un Markdown entre dos títulos (el primero incluido, el segundo excluido)."""
    inicio = texto.index(desde)
    fin = texto.index(hasta, inicio) if hasta else len(texto)
    return texto[inicio:fin]


def main():
    sys.path.insert(0, str(INFORME))
    b = Constructor()
    b.caratula()
    b.indice()

    contenido = INFORME / "contenido"
    # Parte 0 y 1
    b.markdown(leer(contenido / "00-introduccion.md"))
    b.markdown(leer(contenido / "01-introduccion.md"))

    # Parte 2: registro del proceso PUDS (estructura de los informes modelo)
    import parte2

    b.markdown(parte2.generar())
    b.markdown(pruebas_segundo_parcial(leer(DOCS / "puds" / "05-pruebas.md")), prefijo="2.5", renumerar=True,
               titulo_h1="Flujo de trabajo: pruebas")

    # Parte 3: manual
    b.markdown(leer(contenido / "03-manual.md"))

    # Bibliografía
    b.markdown(leer(contenido / "04-bibliografia.md"))

    # Anexos
    b.titulo("5. Anexos", 1, salto_pagina=True)
    anexos = [
        ("Anexo A. IA local con Ollama (instalación, activación y evaluación)", DOCS / "IA_LOCAL.md", "A"),
        ("Anexo B. Reentrenamiento del modelo de IA", DOCS / "REENTRENAMIENTO_IA.md", "B"),
        ("Anexo C. Despliegue en AWS", DOCS / "DESPLIEGUE.md", "C"),
    ]
    for titulo_anexo, ruta, letra in anexos:
        b.markdown(leer(ruta), prefijo=f"5.{'ABCD'.index(letra) + 1}", renumerar=True, titulo_h1=titulo_anexo)

    BUILD.mkdir(exist_ok=True)
    salida = BUILD / "Informe.docx"
    b.doc.save(salida)
    print("Escrito", salida, f"({salida.stat().st_size // 1024} KB, {b.diagramas} diagramas, {b.diagramas_ea} de Enterprise Architect)")


if __name__ == "__main__":
    main()
