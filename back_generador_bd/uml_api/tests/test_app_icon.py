import struct
import zlib

from django.test import SimpleTestCase

from uml_api.services import app_icon


def _decode(png):
    """Lee un PNG de 8 bits sin entrelazado y devuelve (ancho, alto, tipo de color, filas sin filtro)."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, header = 8, b"", None
    while pos < len(png):
        length, tag = struct.unpack(">I4s", png[pos:pos + 8])
        data = png[pos + 8:pos + 8 + length]
        assert zlib.crc32(tag + data) & 0xFFFFFFFF == struct.unpack(">I", png[pos + 8 + length:pos + 12 + length])[0]
        if tag == b"IHDR":
            header = struct.unpack(">IIBBBBB", data)
        elif tag == b"IDAT":
            idat += data
        pos += 12 + length
    width, height, depth, color_type, _c, _f, _i = header
    channels = {2: 3, 6: 4}[color_type]
    raw = zlib.decompress(idat)
    stride = 1 + width * channels
    rows = [raw[i * stride + 1:(i + 1) * stride] for i in range(height)]
    assert all(raw[i * stride] == 0 for i in range(height))
    return width, height, color_type, rows


class AppIconTests(SimpleTestCase):
    def test_icon_is_a_valid_1024_rgb_png_without_transparency(self):
        width, height, color_type, rows = _decode(app_icon.render_png("AE295C"))
        self.assertEqual((1024, 1024, 2), (width, height, color_type))  # iOS no admite transparencia
        self.assertEqual(1024 * 3, len(rows[0]))

    def test_icon_has_a_white_card_in_the_middle_and_the_brand_color_in_the_corner(self):
        _w, _h, _t, rows = _decode(app_icon.render_png("AE295C"))
        corner = tuple(rows[8][8 * 3:8 * 3 + 3])
        self.assertGreater(corner[0], corner[1] + 40, "la esquina debe ser del color de la app (rojizo), no blanca")
        centre_left_of_bar = tuple(rows[300][512 * 3:512 * 3 + 3])  # sobre la tarjeta, por encima de la barra
        self.assertTrue(all(channel > 225 for channel in centre_left_of_bar), centre_left_of_bar)

    def test_foreground_is_transparent_around_the_symbol_and_opaque_on_it(self):
        width, height, color_type, rows = _decode(app_icon.render_png("AE295C", foreground=True))
        self.assertEqual((1024, 1024, 6), (width, height, color_type))
        self.assertEqual(0, rows[4][4 * 4 + 3])           # esquina: transparente
        self.assertGreater(rows[512][512 * 4 + 3], 200)   # centro: opaco

    def test_icon_depends_only_on_the_color_and_is_cached(self):
        self.assertIs(app_icon.render_png("112233"), app_icon.render_png("112233"))
        self.assertNotEqual(app_icon.render_png("112233"), app_icon.render_png("AA3322"))
