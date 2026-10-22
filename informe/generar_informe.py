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
NUMERO = "[N.° DE GRUPO]"
INTEGRANTES = [("Alaca Pedro", "[REGISTRO]"), ("Quenta Callejas Yohan Sebastian", "[REGISTRO]")]
MATERIA = "Ingeniería de Software 1"
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

ANCHO_UTIL_CM = 16.4
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
    estilos = doc.styles
    normal = estilos["Normal"]
    normal.font.name = FUENTE
    normal.font.size = Pt(10.5)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15

    tamanos = {1: 16, 2: 13.5, 3: 12, 4: 11}
    for nivel, tam in tamanos.items():
        h = estilos[f"Heading {nivel}"]
        h.font.name = FUENTE
        h.font.size = Pt(tam)
        h.font.bold = True
        h.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44) if nivel <= 2 else RGBColor(0x33, 0x33, 0x33)
        h.element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
        h.element.rPr.rFonts.set(qn("w:ascii"), FUENTE)
        h.element.rPr.rFonts.set(qn("w:hAnsi"), FUENTE)
        h.paragraph_format.space_before = Pt(16 if nivel == 1 else 12)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.keep_with_next = True
    from docx.enum.style import WD_STYLE_TYPE
    for nivel, sangria in ((1, 0.0), (2, 0.5), (3, 1.0)):
        toc = estilos.add_style(f"toc {nivel}", WD_STYLE_TYPE.PARAGRAPH)
        toc.base_style = estilos["Normal"]
        toc.font.size = Pt(9.5 if nivel == 1 else 9)
        toc.font.bold = nivel == 1
        toc.paragraph_format.left_indent = Cm(sangria)
        toc.paragraph_format.space_after = Pt(1)
        toc.paragraph_format.space_before = Pt(4 if nivel == 1 else 0)
        toc.paragraph_format.line_spacing = 1.0
    for nombre in ("List Bullet", "List Bullet 2"):
        estilos[nombre].font.name = FUENTE
        estilos[nombre].font.size = Pt(10.5)
        estilos[nombre].paragraph_format.space_after = Pt(2)


def configurar_pagina(doc):
    seccion = doc.sections[0]
    seccion.orientation = WD_ORIENT.PORTRAIT
    seccion.page_width, seccion.page_height = Cm(21.59), Cm(27.94)  # carta
    seccion.left_margin = seccion.right_margin = Cm(2.6)
    seccion.top_margin, seccion.bottom_margin = Cm(2.4), Cm(2.2)
    seccion.different_first_page_header_footer = True

    encabezado = seccion.header.paragraphs[0]
    encabezado.text = "Ingeniería de Software 1 — Informe del proyecto"
    encabezado.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for run in encabezado.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
    pie = seccion.footer.paragraphs[0]
    pie.alignment = WD_ALIGN_PARAGRAPH.CENTER
    campo(pie, "PAGE", "1")
    for run in pie.runs:
        run.font.size = Pt(9)


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
        self.contador = [0, 0, 0, 0]  # para numerar documentos incluidos

    # párrafos -------------------------------------------------------------------------------
    def titulo(self, texto, nivel, salto_pagina=False):
        if salto_pagina:
            self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        self.doc.add_heading(limpiar(texto), level=min(nivel, 4))

    def parrafo(self, texto, **kw):
        p = self.doc.add_paragraph()
        agregar_inline(p, texto, **kw)
        return p

    def lista(self, items):
        for nivel, tipo, texto, numero in items:
            if tipo == "bullet":
                p = self.doc.add_paragraph(style="List Bullet" if nivel == 0 else "List Bullet 2")
                agregar_inline(p, texto)
            else:
                p = self.doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.9 + 0.8 * nivel)
                p.paragraph_format.first_line_indent = Cm(-0.6)
                p.paragraph_format.space_after = Pt(2)
                agregar_inline(p, f"{numero}. {texto}")

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
        # Tabla de "ficha" (caso de uso): primera fila vacía = sin encabezado y primera columna sombreada.
        ficha = all(not c.strip() for c in filas[0])
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
        tam = 8.5 if columnas >= 4 else 9.5
        for numero, fila in enumerate(filas):
            celdas = tabla.add_row().cells
            for indice in range(columnas):
                texto = fila[indice] if indice < len(fila) else ""
                celda = celdas[indice]
                parrafo = celda.paragraphs[0]
                parrafo.paragraph_format.space_after = Pt(1)
                parrafo.paragraph_format.line_spacing = 1.0
                agregar_inline(parrafo, texto, tam=tam, negrita=(numero == 0 and not ficha))
                if numero == 0 and not ficha:
                    sombrear(celda._tc.get_or_add_tcPr(), "DDE3F0")
                elif ficha and indice == 0:
                    sombrear(celda._tc.get_or_add_tcPr(), "FCE4D6")
                if ficha and numero < len(filas) - 1:
                    parrafo.paragraph_format.keep_with_next = True  # la ficha no se parte entre páginas
            if numero == 0 and not ficha:
                fila_pr = tabla.rows[0]._tr.get_or_add_trPr()
                cabecera = OxmlElement("w:tblHeader")
                fila_pr.append(cabecera)
        for fila_xml in tabla.rows:
            no_partir = OxmlElement("w:cantSplit")
            fila_xml._tr.get_or_add_trPr().append(no_partir)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def plantuml(self, fuente):
        """Diagrama UML con PlantUML; el tamaño final respeta el tamaño natural (150 dpi)."""
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
        ancho_cm = min(ANCHO_UTIL_CM - 0.8, max(5.0, ancho_px / dpi * 2.54))
        self.imagen(salida, pie=f"Diagrama {self.diagramas}", ancho_cm=ancho_cm)

    def mermaid(self, fuente):
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
        self.imagen(salida, pie=f"Diagrama {self.diagramas}", ancho_cm=15.5)

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
            i += 1
        vaciar_lista()

    # Carátula e índice ----------------------------------------------------------------------
    def caratula(self):
        doc = self.doc

        def linea(texto, tam, negrita=False, despues=6, alinear=WD_ALIGN_PARAGRAPH.CENTER, color=None):
            p = doc.add_paragraph()
            p.alignment = alinear
            p.paragraph_format.space_after = Pt(despues)
            r = p.add_run(texto)
            r.bold = negrita
            r.font.size = Pt(tam)
            if color:
                r.font.color.rgb = color
            return p

        linea("UNIVERSIDAD AUTÓNOMA GABRIEL RENÉ MORENO", 15, True, 10)
        linea("FACULTAD DE INGENIERÍA EN CIENCIAS DE LA COMPUTACIÓN Y TELECOMUNICACIONES", 12, False, 24,
              color=RGBColor(0x1F, 0x4E, 0x5F))
        logo = INFORME / "recursos" / "logo-facultad.png"
        if logo.exists():
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(26)
            p.add_run().add_picture(str(logo), width=Cm(4.6))
        linea(f"“{TITULO}”", 17, True, 28)
        linea(f"Número: {NUMERO}", 11, True, 12, WD_ALIGN_PARAGRAPH.LEFT)
        linea("INTEGRANTES :", 11, True, 6, WD_ALIGN_PARAGRAPH.LEFT)
        tabla = doc.add_table(rows=0, cols=2)
        for nombre, registro in INTEGRANTES:
            celdas = tabla.add_row().cells
            celdas[0].width, celdas[1].width = Cm(11.5), Cm(4.5)
            for celda, texto in ((celdas[0], f"❖  {nombre}"), (celdas[1], registro)):
                parrafo = celda.paragraphs[0]
                parrafo.paragraph_format.space_after = Pt(3)
                run = parrafo.add_run(texto)
                run.font.size = Pt(10.5)
                if texto.startswith("["):
                    run.font.highlight_color = 7  # amarillo: dato por completar
        doc.add_paragraph().paragraph_format.space_after = Pt(12)
        for etiqueta, valor in (("Materia: ", MATERIA), ("Sigla: ", SIGLA), ("Docente: ", DOCENTE), ("Gestión: ", GESTION)):
            p = doc.add_paragraph()
            p.paragraph_format.space_after = Pt(3)
            r = p.add_run(etiqueta)
            r.bold = True
            r.font.size = Pt(10.5)
            r2 = p.add_run(valor)
            r2.font.size = Pt(10.5)
        doc.add_paragraph().paragraph_format.space_after = Pt(30)
        linea(LUGAR, 12, True)

    def indice(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        p = self.doc.add_paragraph()
        r = p.add_run("Contenido")
        r.bold = True
        r.font.size = Pt(16)
        r.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
        p = self.doc.add_paragraph()
        campo(p, r'TOC \o "1-3" \h \z \u', "Haz clic derecho y elige «Actualizar campo» para generar el índice.")


def leer(ruta):
    return Path(ruta).read_text(encoding="utf-8")


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
    b.markdown(leer(contenido / "01-fundamentacion.md"), desplazar=1)

    # Parte 2: registro del proceso PUDS (estructura de los informes modelo)
    import parte2

    b.markdown(parte2.generar())
    b.markdown(leer(DOCS / "puds" / "05-pruebas.md"), prefijo="2.5", renumerar=True,
               titulo_h1="Flujo de trabajo: pruebas")

    # Parte 3: manual
    b.markdown(leer(contenido / "03-manual.md"))

    # Bibliografía
    b.markdown(leer(contenido / "04-bibliografia.md"))

    # Anexos
    b.titulo("5. Anexos", 1, salto_pagina=True)
    anexos = [
        ("Anexo A. IA local con Ollama (instalación, activación y evaluación)", DOCS / "IA_LOCAL.md", "A"),
        ("Anexo B. Reentrenamiento del modelo de IA", DOCS / "PLAN_REENTRENAMIENTO_IA.md", "B"),
        ("Anexo C. Despliegue en AWS", DOCS / "DESPLIEGUE.md", "C"),
        ("Anexo D. Entrega y limitaciones conocidas", DOCS / "ENTREGA.md", "D"),
    ]
    for titulo_anexo, ruta, letra in anexos:
        b.markdown(leer(ruta), prefijo=f"5.{'ABCD'.index(letra) + 1}", renumerar=True, titulo_h1=titulo_anexo)

    BUILD.mkdir(exist_ok=True)
    salida = BUILD / "Informe.docx"
    b.doc.save(salida)
    print("Escrito", salida, f"({salida.stat().st_size // 1024} KB, {b.diagramas} diagramas)")


if __name__ == "__main__":
    main()
