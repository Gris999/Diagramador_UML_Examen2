"""Ubica las etiquetas de los mensajes de los diagramas de colaboración de Enterprise Architect (dos pasadas).

EA pone la etiqueta de un conector de estilo árbol en un punto que depende de la forma del trazo y no del destino, de modo que las etiquetas
de varios conectores que salen de un mismo elemento caen una sobre otra. Esto lo resuelve midiendo en lugar de adivinar:

  1. primera pasada: cada etiqueta se pinta de un color distinto y sin desplazamiento; se exportan las imágenes y se mide dónde cayó cada una;
  2. se calcula el desplazamiento que lleva cada etiqueta junto a la flecha de su destino (a la altura de la flecha, al lado del tramo
     vertical del árbol, hacia el lado del origen) y se vuelve a generar con las etiquetas en negro.

Calibración (experimentos con EA 17.2, ver `docs/PLAN_SEGUNDO_PARCIAL.md`): el desplazamiento OX/OY se suma a la posición por defecto en
unidades del diagrama; la imagen exportada mide 1,37 píxeles por unidad y el tramo vertical del árbol queda a 50 unidades del destino.
"""

import colorsys
import copy
from pathlib import Path

import numpy as np
from PIL import Image

K = 1.37          # píxeles de la imagen por unidad del diagrama
ATAQUE_CLASE = 56  # unidades bajo el borde superior de la caja donde la línea entra a un ícono de clase (boundary, control, entity)
SESGO_ACTOR = 14  # lo mismo para el muñeco de un actor
TRONCO = 50       # unidades entre el tramo vertical del árbol y el borde del destino
TOLERANCIA_TONO = 9    # grados
SEPARACION = 50        # unidades que se baja cada etiqueta en la primera pasada respecto de la anterior
# Colores de la primera pasada: tonos muy saturados y claros que no usa ningún otro elemento del diagrama (los íconos son color tostado,
# las líneas gris azulado y la cabeza de los actores amarillo pálido, de tono 45).
TONOS = [0, 22, 90, 112, 135, 157, 180, 202, 225, 247, 270, 292, 315, 337]  # sin los tonos 40 a 70 (cabeza de los actores)
PALETA = [tuple(round(255 * c) for c in colorsys.hsv_to_rgb(t / 360, 1, 0.9)) for t in TONOS]


def _bgr(rgb):
    r, g, b = rgb
    return r + 256 * g + 65536 * b


def automaticos(diagrama):
    return [c for c in diagrama["conectores"] if c.get("etiq_auto")]


def hay_automaticos(modelo):
    return any(automaticos(d) for d in modelo["diagramas"])


def _marcador(copia, d):
    """Cuadrito amarillo en la esquina superior izquierda del contenido: dice dónde cae en la imagen la coordenada (xmin, ymin), porque
    el margen de la imagen cambia de un diagrama a otro. Va dentro de los límites del contenido y no mueve el recorte de la imagen."""
    x, y = min(o["x"] for o in d["objetos"]), min(o["y"] for o in d["objetos"])
    clave = f"marcador:{d['id']}"
    copia["elementos"][clave] = dict(tipo="Class", nombre=" ", ruta=d["ruta"])
    d["objetos"].append(dict(k=clave, x=x, y=y, w=10, h=10, fondo="#FFFF00", borde="#FFFF00", texto="#FFFF00"))
    return x, y


def paso1(modelo):
    """Copia del modelo con cada etiqueta automática de un color distinto y sin desplazamiento (y un marcador de referencia)."""
    copia = copy.deepcopy(modelo)
    for d in copia["diagramas"]:
        autos = automaticos(d)
        if autos:
            d["marcador"] = _marcador(copia, d)
        if len(autos) > len(PALETA):
            raise ValueError(f"{d['id']}: demasiadas etiquetas para medir ({len(autos)})")
        for n, c in enumerate(autos):
            cx, cy = c["etiq_auto"]
            # Los rótulos de EA son opacos: si dos caen en el mismo punto (todos los que salen de un mismo elemento) uno tapa al otro y no se
            # puede medir. Cada uno se baja un tramo distinto y distante; luego se resta ese desplazamiento conocido.
            c["etiq"] = f"{cx}:{cy}:0:{SEPARACION * n}:{_bgr(PALETA[n])}"
    return copia


def medir(png, cuantos):
    """[(x0, y0, x1, y1) en píxeles | None] de las `cuantos` etiquetas, por su tono (los bordes suavizados del texto conservan el tono)."""
    imagen = np.asarray(Image.open(png).convert("RGB")).astype(float)
    r, g, b = imagen[..., 0], imagen[..., 1], imagen[..., 2]
    maximo, minimo = imagen.max(axis=2), imagen.min(axis=2)
    delta = np.where(maximo == minimo, 1, maximo - minimo)
    tono = np.where(maximo == r, ((g - b) / delta) % 6, np.where(maximo == g, (b - r) / delta + 2, (r - g) / delta + 4)) * 60
    saturacion = np.where(maximo == 0, 0, (maximo - minimo) / np.where(maximo == 0, 1, maximo))
    colorido = (saturacion > 0.25) & (maximo / 255 > 0.75)
    medidas = []
    for n in range(cuantos):
        cerca = np.abs(((tono - TONOS[n]) + 180) % 360 - 180) < TOLERANCIA_TONO
        ys, xs = np.nonzero(colorido & cerca)
        medidas.append((xs.min(), ys.min(), xs.max(), ys.max()) if len(xs) else None)
    return medidas


def medir_marcador(png):
    """(x, y) en píxeles de la esquina superior izquierda del marcador amarillo, o None."""
    imagen = np.asarray(Image.open(png).convert("RGB")).astype(float)
    r, g, b = imagen[..., 0], imagen[..., 1], imagen[..., 2]
    amarillo = (r > 200) & (g > 200) & (b < 90)
    ys, xs = np.nonzero(amarillo)
    return (xs.min() - 1, ys.min() - 1) if len(xs) else None


def modelo_marcador(d):
    """Coordenadas (x, y) donde `paso1` puso el marcador de este diagrama (el mínimo de x y de y de sus objetos)."""
    return min(o["x"] for o in d["objetos"]), min(o["y"] for o in d["objetos"])


def _libre(colocadas, x, y, ancho, alto):
    """Sube (y) la etiqueta lo necesario para que no se encime con las ya colocadas."""
    subir = True
    while subir:
        subir = False
        for (a0, b0, a1, b1) in colocadas:
            if x - ancho / 2 < a1 + 2 and x + ancho / 2 > a0 - 2 and y - alto / 2 < b1 + 2 and y + alto / 2 > b0 - 2:
                y = b0 - 3 - alto / 2
                subir = True
    return y


def paso2(modelo, carpeta_paso1):
    """Fija en `modelo` el desplazamiento de cada etiqueta automática, a partir de las imágenes de la primera pasada."""
    ajustadas = 0
    for d in modelo["diagramas"]:
        autos = automaticos(d)
        if not autos:
            continue
        png = Path(carpeta_paso1) / f"{d['id']}.png"
        marca = medir_marcador(png) if png.exists() else None
        if marca is None:
            continue
        mx, my = modelo_marcador(d)
        bx, by = marca[0] - K * mx, marca[1] - K * my  # píxel de la coordenada (0, 0) en la imagen de este diagrama

        def px(x, y, bx=bx, by=by):
            return K * x + bx, K * y + by

        medidas = medir(png, len(autos))
        objetos = {o["k"]: dict(o, sesgo={"Class": round(K * (ATAQUE_CLASE - o["h"] / 2)), "Actor": SESGO_ACTOR}.get(
            modelo["elementos"][o["k"]]["tipo"], 0)) for o in d["objetos"]}
        colocadas = []  # rectángulos (px) ya ocupados por otras etiquetas
        for n, (c, caja) in enumerate(zip(autos, medidas)):
            cx, cy = c["etiq_auto"]
            c["etiq"] = f"{cx}:{cy}:0:0:-1"
            if caja is None:
                continue
            o, t = objetos[c["de"]], objetos[c["a"]]
            centro_o = (o["x"] + o["w"] / 2, o["y"] + o["h"] / 2)
            centro_d = (t["x"] + t["w"] / 2, t["y"] + t["h"] / 2)
            ancho_px, alto_px = caja[2] - caja[0] + 1, caja[3] - caja[1] + 1
            ctr_x, ctr_y = (caja[0] + caja[2]) / 2, (caja[1] + caja[3]) / 2 - K * SEPARACION * n  # posición por defecto
            deseado = None
            derecha = centro_d[0] > centro_o[0]
            if c.get("arbol") == "H" and abs(centro_d[1] - centro_o[1]) > 12:
                # con tronco: junto al tramo vertical, a la altura de la flecha de su destino, del lado del origen
                borde = t["x"] if derecha else t["x"] + t["w"]
                tronco = px(borde + (-TRONCO if derecha else TRONCO), 0)[0]
                x = tronco - 14 - ancho_px / 2 if derecha else tronco + 14 + ancho_px / 2
                y = px(0, centro_d[1])[1] + t["sesgo"] - 9 - alto_px / 2
                deseado = (x, y)
            elif c.get("arbol") == "H":
                # recta: centrada entre el origen y el comienzo del tramo vertical del destino, sobre la línea
                borde_o = px(o["x"] + o["w"] if derecha else o["x"], 0)[0]
                borde_d = px(t["x"] if derecha else t["x"] + t["w"], 0)[0]
                limite = borde_d - 69 if derecha else borde_d + 69
                if abs(limite - borde_o) < ancho_px + 10:
                    limite = borde_d
                x = (borde_o + limite) / 2
                y = px(0, centro_o[1])[1] + o["sesgo"] - 9 - alto_px / 2
                deseado = (x, y)
            elif c.get("arbol") == "V":
                # vertical: al lado izquierdo de la línea, a mitad de camino entre los dos elementos
                x = px(centro_o[0], 0)[0] - 8 - ancho_px / 2
                y = (px(0, centro_o[1])[1] + px(0, centro_d[1])[1]) / 2 + (o["sesgo"] + t["sesgo"]) / 2
                deseado = (x, y)
            if deseado:
                x, y = deseado
                y = _libre(colocadas, x, y, ancho_px, alto_px)
                c["etiq"] = f"{cx}:{cy}:{round((x - ctr_x) / K)}:{round((y - ctr_y) / K)}:-1"
                ctr_x, ctr_y = x, y
                ajustadas += 1
            colocadas.append((ctr_x - ancho_px / 2, ctr_y - alto_px / 2, ctr_x + ancho_px / 2, ctr_y + alto_px / 2))
    return ajustadas
