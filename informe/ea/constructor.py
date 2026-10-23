"""Construye un modelo en Enterprise Architect a partir de especificaciones y exporta los diagramas.

EA se controla por su interfaz de automatización (COM) con un script VBScript que se ejecuta dentro
de la botella de CrossOver. Este módulo solo escribe ese script y lo lanza; las especificaciones
(`especificaciones.py`) dicen qué elementos y diagramas hay.

Notas del entorno (descubiertas probando):
  * el VBScript de Wine pierde las cadenas creadas con ChrW al pasarlas a procedimientos (llegan vacías o
    dan error 445) y no imprime texto con acentos: el script se escribe en cp1252 con las tildes literales
    y los registros de depuración solo usan ASCII;
  * crear un modelo raíz nuevo cuelga a EA: se usa el que trae EABase.qea;
  * cada llamada a COM arranca su propia instancia de EA (tarda unos segundos).
"""

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

CX = "/Applications/CrossOver.app/Contents/SharedSupport/CrossOver/bin"
BOTELLA = "Enterprise Architect 17.2"
DRIVE_C = Path.home() / "Library/Application Support/CrossOver/Bottles" / BOTELLA / "drive_c"
EA_BASE = DRIVE_C / "Program Files/Sparx Systems/EA Trial/EABase.qea"
CARPETA = DRIVE_C / "ea"


SUSTITUTOS = {"\u2264": "<=", "\u2265": ">=", "\u2192": "->", "\u2190": "<-", "\u2013": "-", "\u2014": "-",
              "\u2018": "'", "\u2019": "'", "\u201c": "\u00ab", "\u201d": "\u00bb", "\u2022": "-", "\u2026": "..."}


def vs(texto):
    """Literal VBScript de `texto`. El script se guarda en cp1252, así que las tildes van tal cual."""
    texto = "".join(SUSTITUTOS.get(ch, ch) for ch in str(texto))
    partes = texto.split("\n")
    return " & vbCrLf & ".join('"' + p.replace('"', '""') + '"' for p in partes)


CABECERA = r'''On Error Resume Next
Dim r, raiz, pi, fso, dEl, dPk, dCn, SALIDA, LOGF
Set fso = CreateObject("Scripting.FileSystemObject")
Set dEl = CreateObject("Scripting.Dictionary")
Set dPk = CreateObject("Scripting.Dictionary")
Set dCn = CreateObject("Scripting.Dictionary")
SALIDA = "C:\ea\out\"
LOGF = "C:\ea\log.txt"

Function Ascii(s)
  On Error Resume Next
  Dim i, c, o
  o = ""
  For i = 1 To Len(s)
    c = AscW(Mid(s, i, 1))
    If c > 31 And c < 127 Then o = o & Chr(c) Else o = o & "?"
  Next
  Ascii = o
End Function
Sub Log(s)
  On Error Resume Next
  Dim f
  Set f = fso.OpenTextFile(LOGF, 8, True)
  f.WriteLine Time & " " & s
  f.Close
End Sub
Sub Chk(ctx)
  If Err.Number <> 0 Then
    Log "ERROR " & ctx & " n=" & Err.Number & " " & Ascii(Err.Description)
    Err.Clear
  End If
End Sub

Function Pkg(ruta)
  On Error Resume Next
  Dim partes, padre, p, i, acum
  If dPk.Exists(ruta) Then
    Set Pkg = dPk(ruta)
    Exit Function
  End If
  partes = Split(ruta, "|")
  Set padre = raiz
  acum = ""
  For i = 0 To UBound(partes)
    If acum = "" Then acum = partes(i) Else acum = acum & "|" & partes(i)
    If dPk.Exists(acum) Then
      Set padre = dPk(acum)
    Else
      Set p = padre.Packages.AddNew(CStr(partes(i)), "")
      p.Update
      padre.Packages.Refresh
      dPk.Add acum, p
      Set padre = p
    End If
  Next
  Chk "Pkg " & ruta
  Set Pkg = padre
End Function

Function Elem(clave, ruta, tipo, nombre, est, padre, notas)
  On Error Resume Next
  Dim p, e, q
  If dEl.Exists(clave) Then
    Set Elem = dEl(clave)
    Exit Function
  End If
  Set p = Pkg(ruta)
  If tipo = "Package" Then
    Set q = p.Packages.AddNew(CStr(nombre), "")
    q.Update
    p.Packages.Refresh
    Set e = q.Element
    If est <> "" Then
      e.Stereotype = est
      e.Update
    End If
  Else
    Set e = p.Elements.AddNew(CStr(nombre), CStr(tipo))
    If est <> "" Then e.Stereotype = est
    If padre <> "" Then e.ParentID = dEl(padre).ElementID
    If notas <> "" Then e.Notes = notas
    e.Update
    p.Elements.Refresh
  End If
  dEl.Add clave, e
  Chk "Elem " & clave
  Set Elem = e
End Function

Sub Attr(clave, nombre, tipo, est, vis, pos)
  On Error Resume Next
  Dim a
  Set a = dEl(clave).Attributes.AddNew(nombre, tipo)
  If est <> "" Then a.Stereotype = est
  a.Visibility = vis
  a.Pos = pos
  a.Update
  Chk "Attr " & clave
End Sub

Sub Meth(clave, nombre, ret, vis, params, pos)
  On Error Resume Next
  Dim m, ps, i, pr, q
  Set m = dEl(clave).Methods.AddNew(nombre, ret)
  m.Visibility = vis
  m.Pos = pos
  m.Update
  If params <> "" Then
    ps = Split(params, ";")
    For i = 0 To UBound(ps)
      pr = Split(ps(i), ":")
      Set q = m.Parameters.AddNew(pr(0), pr(1))
      q.Update
    Next
  End If
  Chk "Meth " & clave
End Sub

Function Dia(ruta, nombre, tipo)
  On Error Resume Next
  Dim p, d
  Set p = Pkg(ruta)
  Set d = p.Diagrams.AddNew(CStr(nombre), CStr(tipo))
  d.Update
  p.Diagrams.Refresh
  Chk "Dia " & ruta
  Set Dia = d
End Function

Sub Obj(d, clave, l, t, w, h)
  On Error Resume Next
  Dim o
  Set o = d.DiagramObjects.AddNew("l=" & l & ";r=" & (l + w) & ";t=" & (-t) & ";b=" & (-(t + h)) & ";", "")
  o.ElementID = dEl(clave).ElementID
  o.Update
  Chk "Obj " & clave
End Sub

Sub Con(idd, de, a, tipo, nombre, est, cd, ca, dir, seq)
  On Error Resume Next
  Dim k, c, origen
  k = de & ">" & a & ">" & tipo & ">" & nombre & ">" & est
  If seq > 0 Then k = idd & ">" & k
  If dCn.Exists(k) Then Exit Sub
  Set origen = dEl(de)
  Set c = origen.Connectors.AddNew(nombre, tipo)
  c.SupplierID = dEl(a).ElementID
  If est <> "" Then c.Stereotype = est
  If seq > 0 Then c.SequenceNo = seq
  If dir <> "" Then c.Direction = dir
  c.Update
  If cd <> "" Then
    c.ClientEnd.Cardinality = cd
    c.ClientEnd.Update
  End If
  If ca <> "" Then
    c.SupplierEnd.Cardinality = ca
    c.SupplierEnd.Update
  End If
  origen.Connectors.Refresh
  dCn.Add k, 1
  Chk "Con " & de & " " & a
End Sub

Sub Paralelos(d)
  On Error Resume Next
  Dim cx, cy, grupos, i, o, dl, c, a, b, k, ids, n, j, off, dxc, dyc, geo
  Set cx = CreateObject("Scripting.Dictionary")
  Set cy = CreateObject("Scripting.Dictionary")
  Set grupos = CreateObject("Scripting.Dictionary")
  For i = 0 To d.DiagramObjects.Count - 1
    Set o = d.DiagramObjects.GetAt(i)
    cx(CStr(o.ElementID)) = (o.Left + o.Right) / 2
    cy(CStr(o.ElementID)) = (o.Top + o.Bottom) / 2
  Next
  For i = 0 To d.DiagramLinks.Count - 1
    Set dl = d.DiagramLinks.GetAt(i)
    Set c = r.GetConnectorByID(dl.ConnectorID)
    a = c.ClientID
    b = c.SupplierID
    If a < b Then k = a & "-" & b Else k = b & "-" & a
    If grupos.Exists(k) Then grupos(k) = grupos(k) & "," & i Else grupos.Add k, CStr(i)
  Next
  For Each k In grupos.Keys
    ids = Split(grupos(k), ",")
    n = UBound(ids) + 1
    If n > 1 Then
      For j = 0 To n - 1
        Set dl = d.DiagramLinks.GetAt(CInt(ids(j)))
        Set c = r.GetConnectorByID(dl.ConnectorID)
        off = CInt((j - (n - 1) / 2) * 30)
        dxc = Abs(cx(CStr(c.ClientID)) - cx(CStr(c.SupplierID)))
        dyc = Abs(cy(CStr(c.ClientID)) - cy(CStr(c.SupplierID)))
        If dxc >= dyc Then
          geo = "SX=0;SY=" & off & ";EX=0;EY=" & off & ";"
        Else
          geo = "SX=" & off & ";SY=0;EX=" & off & ";EY=0;"
        End If
        dl.Geometry = geo
        dl.Update
      Next
    End If
  Next
  Chk "Paralelos"
End Sub

Sub OcultarEnlaces(d)
  On Error Resume Next
  Dim i, dl
  For i = 0 To d.DiagramLinks.Count - 1
    Set dl = d.DiagramLinks.GetAt(i)
    dl.IsHidden = True
    dl.Update
  Next
  Chk "Ocultar"
End Sub

Sub Fin(d, idd, modo)
  On Error Resume Next
  d.DiagramObjects.Refresh
  d.DiagramLinks.Refresh
  If modo = 1 Then Paralelos d
  If modo = 2 Then OcultarEnlaces d
  r.ReloadDiagram d.DiagramID
  pi.PutDiagramImageToFile d.DiagramGUID, SALIDA & idd & ".png", 1
  Chk "export " & idd
  Log "ok " & idd
End Sub

Set r = CreateObject("EA.Repository")
Chk "CreateObject"
r.OpenFile "C:\ea\modelo.qea"
Chk "OpenFile"
Set raiz = r.Models.GetAt(0)
raiz.Name = @NOMBRE_RAIZ@
raiz.Update
Set pi = r.GetProjectInterface()
Log "inicio"
'''


def _estructura(modelo):
    """Líneas VBScript que crean elementos, diagramas y conectores de `modelo`."""
    elementos = modelo["elementos"]
    creados = set()
    salida = []

    def crear(clave):
        if clave in creados:
            return
        creados.add(clave)
        e = elementos[clave]
        if e.get("padre"):
            crear(e["padre"])
        salida.append(f'Elem {vs(clave)}, {vs(e["ruta"])}, {vs(e["tipo"])}, {vs(e["nombre"])}, '
                      f'{vs(e.get("est", ""))}, {vs(e.get("padre", ""))}, {vs(e.get("notas", ""))}')
        for pos, (nombre, tipo, est, vis) in enumerate(e.get("attrs", [])):
            salida.append(f'Attr {vs(clave)}, {vs(nombre)}, {vs(tipo)}, {vs(est)}, {vs(vis)}, {pos}')
        for pos, (nombre, ret, vis, params) in enumerate(e.get("meths", [])):
            salida.append(f'Meth {vs(clave)}, {vs(nombre)}, {vs(ret)}, {vs(vis)}, {vs(params)}, {pos}')

    for d in modelo["diagramas"]:
        for o in d["objetos"]:
            crear(o["k"])
        salida.append(f'Log "diagrama {d["id"]}"')
        salida.append(f'Set dg = Dia({vs(d["ruta"])}, {vs(d["nombre"])}, {vs(d["tipo"])})')
        for o in d["objetos"]:
            salida.append(f'Obj dg, {vs(o["k"])}, {o["x"]}, {o["y"]}, {o["w"]}, {o["h"]}')
        for c in d["conectores"]:
            salida.append(
                f'Con {vs(d["id"])}, {vs(c["de"])}, {vs(c["a"])}, {vs(c.get("tipo", "Association"))}, '
                f'{vs(c.get("nombre", ""))}, {vs(c.get("est", ""))}, {vs(c.get("cd", ""))}, {vs(c.get("ca", ""))}, '
                f'{vs(c.get("dir", ""))}, {c.get("seq", 0)}')
        modo = {"": 0, "paralelos": 1, "ocultar": 2}[d.get("enlaces", "")]
        salida.append(f'Fin dg, {vs(d["id"])}, {modo}')
    return salida


def generar_vbs(modelo, nombre_raiz="Plataforma CASE colaborativa"):
    cabecera = CABECERA.replace("@NOMBRE_RAIZ@", vs(nombre_raiz))
    cuerpo = "\n".join(_estructura(modelo))
    cierre = "\nr.CloseFile\nr.Exit\nLog \"FIN\"\n"
    texto = cabecera + "\nDim dg\n" + cuerpo + cierre
    try:
        texto.encode("cp1252")
    except UnicodeEncodeError as error:
        raise ValueError(f"el script de EA debe poder escribirse en cp1252: {error}") from error
    for numero, linea in enumerate(texto.split("\n"), 1):
        if len(linea) > 950:
            raise ValueError(f"línea {numero} demasiado larga para VBScript ({len(linea)})")
    return texto


def ejecutar(modelo, destino, espera=1800, nombre_raiz="Plataforma CASE colaborativa"):
    """Escribe el script, lo ejecuta en la botella y copia las imágenes y el .qea a `destino`."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    CARPETA.mkdir(exist_ok=True)
    salida = CARPETA / "out"
    if salida.exists():
        shutil.rmtree(salida)
    salida.mkdir()
    log = CARPETA / "log.txt"
    log.unlink(missing_ok=True)
    shutil.copy(EA_BASE, CARPETA / "modelo.qea")
    script = CARPETA / "generar.vbs"
    script.write_bytes(generar_vbs(modelo, nombre_raiz).replace("\n", "\r\n").encode("cp1252"))
    # Cierra instancias de EA incrustadas que hayan quedado de pruebas anteriores.
    subprocess.run("for p in $(pgrep -f 'EA.exe -Embedding'); do kill $p; done", shell=True)
    time.sleep(2)
    proceso = subprocess.Popen(
        [f"{CX}/wine", "--bottle", BOTELLA, "cscript", "//nologo", r"C:\ea\generar.vbs"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env={**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1"})
    inicio = time.time()
    while time.time() - inicio < espera:
        time.sleep(3)
        if log.exists() and "FIN" in log.read_text(errors="ignore"):
            break
        if proceso.poll() is not None and not (log.exists() and "FIN" in log.read_text(errors="ignore")):
            break
    proceso.terminate()
    texto_log = log.read_text(errors="ignore") if log.exists() else ""
    for png in salida.glob("*.png"):
        shutil.copy(png, destino / png.name)
    shutil.copy(CARPETA / "modelo.qea", destino / "modelo.qea")
    (destino / "ea.log").write_text(texto_log)
    return texto_log
