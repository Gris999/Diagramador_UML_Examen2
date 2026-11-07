"""Icono de la aplicacion movil generada, dibujado en Python puro (sin Pillow: no agrega dependencias al servidor).

El icono es el mismo dibujo para cualquier diagrama (una "tabla": tarjeta blanca con una barra de titulo y filas), pero su
color sale del nombre de la app, asi cada sistema tiene su propia identidad. `render_png` devuelve:
  - el icono completo (RGB, 1024x1024, sin transparencia: iOS no la admite);
  - o, con `foreground=True`, solo el simbolo sobre fondo transparente (RGBA) para el icono adaptable de Android.
El resultado se guarda en cache por color: se dibuja una sola vez por proceso.
"""
import math
import struct
import zlib
from functools import lru_cache

SIZE = 1024


def _chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _png(width, height, rows, color_type):
    raw = b"".join(b"\x00" + row for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(raw, 6)) + _chunk(b"IEND", b"")


def _coverage(px, py, cx, cy, half_w, half_h, radius):
    """Cobertura (0..1, con borde suavizado) de un rectangulo redondeado en el punto (px, py)."""
    dx = abs(px - cx) - (half_w - radius)
    dy = abs(py - cy) - (half_h - radius)
    distance = math.hypot(max(dx, 0.0), max(dy, 0.0)) + min(max(dx, dy), 0.0) - radius
    return min(1.0, max(0.0, 0.5 - distance))


def _shapes(brand, scale):
    """(centro x, centro y, mitad ancho, mitad alto, radio, color, opacidad) de cada pieza, de atras hacia adelante."""
    c = SIZE / 2

    def shape(dx, dy, half_w, half_h, radius, color, alpha):
        return (c + dx * scale, c + dy * scale, half_w * scale, half_h * scale, radius * scale, color, alpha)

    white = (255, 255, 255)
    return [
        shape(0, 0, 300, 250, 64, white, 0.97),        # tarjeta
        shape(0, -152, 240, 40, 20, brand, 1.0),       # barra de titulo
        shape(0, -34, 240, 22, 11, brand, 0.45),       # filas
        shape(0, 52, 240, 22, 11, brand, 0.45),
        shape(0, 138, 240, 22, 11, brand, 0.45),
    ]


@lru_cache(maxsize=64)
def render_png(seed_hex, foreground=False):
    """PNG del icono para el color base `seed_hex` (6 digitos hexadecimales, sin #)."""
    brand = tuple(int(seed_hex[i:i + 2], 16) for i in (0, 2, 4))
    if foreground:
        return _render_foreground(brand)
    return _render_full(brand)


def _render_full(brand):
    dark = tuple(int(channel * 0.55) for channel in brand)
    span = 2 * SIZE - 1
    gradient = [
        bytes(int(brand[k] + (dark[k] - brand[k]) * step / span) for k in range(3)) for step in range(2 * SIZE)
    ]
    shapes = _shapes(brand, 1.0)
    rows = []
    for y in range(SIZE):
        row = bytearray(b"".join(gradient[x + y] for x in range(SIZE)))
        for cx, cy, half_w, half_h, radius, color, alpha in shapes:
            if not (cy - half_h - 2 <= y <= cy + half_h + 2):
                continue
            for x in range(max(0, int(cx - half_w) - 2), min(SIZE, int(cx + half_w) + 3)):
                cover = _coverage(x + 0.5, y + 0.5, cx, cy, half_w, half_h, radius) * alpha
                if cover <= 0.0:
                    continue
                index = x * 3
                for k in range(3):
                    row[index + k] = int(row[index + k] * (1.0 - cover) + color[k] * cover)
        rows.append(bytes(row))
    return _png(SIZE, SIZE, rows, 2)


def _render_foreground(brand):
    # el simbolo ocupa el 62 % central: Android recorta el icono adaptable y deja visible ~66 %
    shapes = _shapes(brand, 0.62)
    empty = bytes(SIZE * 4)
    rows = []
    for y in range(SIZE):
        row = None
        for cx, cy, half_w, half_h, radius, color, alpha in shapes:
            if not (cy - half_h - 2 <= y <= cy + half_h + 2):
                continue
            if row is None:
                row = bytearray(empty)
            for x in range(max(0, int(cx - half_w) - 2), min(SIZE, int(cx + half_w) + 3)):
                source = _coverage(x + 0.5, y + 0.5, cx, cy, half_w, half_h, radius) * alpha
                if source <= 0.0:
                    continue
                index = x * 4
                backdrop = row[index + 3] / 255.0
                out_alpha = source + backdrop * (1.0 - source)
                for k in range(3):
                    row[index + k] = int(
                        (color[k] * source + row[index + k] * backdrop * (1.0 - source)) / out_alpha
                    )
                row[index + 3] = int(out_alpha * 255)
        rows.append(bytes(row) if row is not None else empty)
    return _png(SIZE, SIZE, rows, 6)
