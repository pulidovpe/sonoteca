"""Iconos de la aplicación: existen, son válidos y están conectados al empaquetado."""
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets" / "icons"


def _png_header(path):
    data = path.read_bytes()[:33]
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height, depth, color_type = struct.unpack(">IIBB", data[16:26])
    return width, height, color_type


def test_png_icons_are_square_with_transparency():
    for name, side in (("sonoteca-1024.png", 1024), ("sonoteca.png", 512)):
        width, height, color_type = _png_header(ICONS / name)
        assert (width, height) == (side, side) and color_type == 6          # RGBA: esquinas transparentes
    assert _png_header(ROOT / "src" / "sonoteca" / "ui" / "icon.png")[:2] == (512, 512)


def test_ico_and_icns_have_valid_headers():
    ico = (ICONS / "sonoteca.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", ico[:6])
    assert (reserved, kind) == (0, 1) and count >= 6                         # varios tamaños para Windows
    icns = (ICONS / "sonoteca.icns").read_bytes()
    assert icns[:4] == b"icns" and struct.unpack(">I", icns[4:8])[0] == len(icns)


def test_spec_and_app_use_the_icons():
    spec = (ROOT / "packaging" / "sonoteca.spec").read_text(encoding="utf-8")
    assert "sonoteca.ico" in spec and "sonoteca.icns" in spec and '"sonoteca/ui"' in spec
    app = (ROOT / "src" / "sonoteca" / "ui" / "app.py").read_text(encoding="utf-8")
    assert "setWindowIcon" in app and 'ICON_PATH = Path(__file__).parent / "icon.png"' in app
