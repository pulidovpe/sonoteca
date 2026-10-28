"""Proveedor de imágenes QML: image://cover/<album_id>. Extrae, recorta, escala y cachea."""
from __future__ import annotations

import hashlib
import threading
from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter
from PySide6.QtQuick import QQuickImageProvider

from sonoteca.core import paths
from sonoteca.core.covers import (
    album_cover_source,
    artist_cover_album,
    artist_photo,
    extract_embedded_cover,
)
from sonoteca.core.db import connect

BUCKETS = (160, 320, 640)  # tamaños en disco; evita una miniatura por cada tamaño pedido


def bucket_for(requested: int) -> int:
    if requested <= 0:
        return 320
    return next((b for b in BUCKETS if requested <= b), BUCKETS[-1])


def placeholder(album_id: int, size: int) -> QImage:
    """Degradado de color estable por álbum (sin texto, para no depender de fuentes)."""
    img = QImage(size, size, QImage.Format.Format_RGB32)
    hue = (album_id * 47) % 360
    grad = QLinearGradient(0, 0, size, size)
    grad.setColorAt(0.0, QColor.fromHsl(hue, 120, 90))
    grad.setColorAt(1.0, QColor.fromHsl((hue + 40) % 360, 130, 45))
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.fillRect(QRect(0, 0, size, size), grad)
    p.setPen(QColor(255, 255, 255, 70))
    p.setBrush(Qt.BrushStyle.NoBrush)
    for frac in (0.62, 0.38, 0.12):  # anillos concéntricos tipo disco
        r = int(size * frac)
        p.drawEllipse(size // 2 - r // 2 - 0, size // 2 - r // 2, r, r)
    p.end()
    return img


class CoverProvider(QQuickImageProvider):
    def __init__(self, db_path: Path | str | None = None, cache_dir: Path | None = None) -> None:
        super().__init__(QQuickImageProvider.ImageType.Image)
        self._db_path = db_path
        base = Path(cache_dir) if cache_dir else paths.cache_dir()
        self._cache_dir = base / "covers"
        self._local = threading.local()  # cada hilo de carga usa su propia conexión SQLite

    def _conn(self):
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._local.conn = connect(self._db_path)
        return conn

    def requestImage(self, id: str, size: QSize, requestedSize: QSize) -> QImage:
        """`id` es '<id_álbum>' o 'artist/<id_artista>' (usa la portada de uno de sus álbumes)."""
        raw = id.split("?")[0]
        is_artist = raw.startswith("artist/")
        try:
            number = int(raw.removeprefix("artist/"))
        except ValueError:
            number = 0
        target = bucket_for(max(requestedSize.width(), requestedSize.height()))
        image = None
        if is_artist:
            photo = artist_photo(number)  # la foto descargada tiene prioridad sobre las portadas
            if photo is not None:
                image = self._load_file("folder", photo, target)
        if image is None:
            album_id = artist_cover_album(self._conn(), number) if is_artist else number
            image = self._load(album_id, target) if album_id else None
        if image is not None and not image.isNull():
            return image
        return placeholder(number + (1000 if is_artist else 0), target)

    def _load(self, album_id: int, target: int) -> QImage | None:
        source = album_cover_source(self._conn(), album_id)
        if source is None:
            return None
        return self._load_file(*source, target)

    def _load_file(self, kind: str, path: Path, target: int) -> QImage | None:
        try:
            st = path.stat()
        except OSError:
            return None
        key = hashlib.sha1(f"{path}|{st.st_mtime_ns}|{st.st_size}|{target}".encode()).hexdigest()
        cached = self._cache_dir / f"{key}.jpg"
        if cached.exists():
            img = QImage(str(cached))
            if not img.isNull():
                return img
        data = extract_embedded_cover(path) if kind == "embedded" else _read(path)
        if not data:
            return None
        img = QImage.fromData(data)
        if img.isNull():
            return None
        side = min(img.width(), img.height())  # recorte cuadrado centrado
        img = img.copy((img.width() - side) // 2, (img.height() - side) // 2, side, side)
        if side > target:
            img = img.scaled(target, target, Qt.AspectRatioMode.IgnoreAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            img.save(str(cached), "JPG", 88)
        except OSError:
            pass  # sin caché en disco la app sigue funcionando
        return img


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None
