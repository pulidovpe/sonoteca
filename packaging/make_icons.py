"""Genera los iconos de Sonoteca a partir de assets/icons/original.png (logo con fondo blanco y márgenes).

Uso (solo desarrollo; necesita `pip install pillow numpy`):  python packaging/make_icons.py

Pasos: quita el fondo blanco exterior (transparente, con borde suavizado y sin halo blanco), recorta al icono, lo
centra en un lienzo cuadrado y escribe en assets/icons/:
  sonoteca-1024.png   original en cuadrado 1024 (maestro)
  sonoteca.png        512 px (también se copia a src/sonoteca/ui/icon.png para la ventana en ejecución)
  sonoteca.ico        Windows (16-256 px)
  sonoteca.icns       macOS (el icono ocupa ~80 % del lienzo, como pide la cuadrícula de iconos de Apple)
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
ICONS = ROOT / "assets" / "icons"
BG_TOLERANCE = 22          # cuánto puede alejarse un píxel del blanco para contar como fondo
MAC_BODY = 824 / 1024      # fracción del lienzo que ocupa el icono en macOS


def remove_white_background(src: Image.Image) -> Image.Image:
    rgb = src.convert("RGB")
    probe = rgb.copy()
    marker = (255, 0, 255)
    for corner in ((0, 0), (rgb.width - 1, 0), (0, rgb.height - 1), (rgb.width - 1, rgb.height - 1)):
        ImageDraw.floodfill(probe, corner, marker, thresh=BG_TOLERANCE)   # solo el blanco conectado al borde
    bg = np.all(np.asarray(probe) == marker, axis=2)
    bg_img = Image.fromarray((bg * 255).astype("uint8"))
    near = np.asarray(bg_img.filter(ImageFilter.MaxFilter(7))) > 0       # fondo dilatado 3 px
    near_inner = np.asarray(bg_img.filter(ImageFilter.MaxFilter(19))) > 0
    band = near & ~bg                                                    # borde antialiased
    ring = near_inner & ~near                                            # justo dentro del borde
    arr = np.asarray(rgb).astype(np.float32)
    edge_color = np.median(arr[ring], axis=0)                            # color oscuro del borde del icono
    lum = arr.mean(axis=2)
    bg_lum = float(np.median(arr[bg].mean(axis=1)))
    dark_lum = float(edge_color.mean())
    alpha = np.where(bg, 0.0, 255.0)
    soft = np.clip((bg_lum - lum) / max(bg_lum - dark_lum, 1.0), 0.0, 1.0) * 255.0
    alpha[band] = soft[band]
    out = arr.copy()
    out[band] = edge_color                                               # sin halo blanco en el borde
    rgba = np.dstack([out, alpha]).clip(0, 255).astype("uint8")
    return Image.fromarray(rgba, "RGBA")


def square_canvas(img: Image.Image, side: int, body: float = 1.0) -> Image.Image:
    """Recorta al contenido y lo centra, sin deformar, en un lienzo transparente side x side."""
    img = img.crop(img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox())
    target = int(side * body)
    scale = target / max(img.size)
    resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(resized, ((side - resized.width) // 2, (side - resized.height) // 2), resized)
    return canvas


def main() -> None:
    keyed = remove_white_background(Image.open(ICONS / "original.png"))
    master = square_canvas(keyed, 1024)
    master.save(ICONS / "sonoteca-1024.png")
    master.resize((512, 512), Image.LANCZOS).save(ICONS / "sonoteca.png")
    master.resize((512, 512), Image.LANCZOS).save(ROOT / "src" / "sonoteca" / "ui" / "icon.png")
    master.save(ICONS / "sonoteca.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    square_canvas(keyed, 1024, MAC_BODY).save(ICONS / "sonoteca.icns")
    print("Iconos generados en", ICONS)


if __name__ == "__main__":
    main()
