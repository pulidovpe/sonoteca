"""Almacén de portadas en la carpeta de datos del usuario (no en la caché ni en el repositorio).

  covers/chosen/<sha1>.jpg|png     portadas que el usuario eligió (y, en la Fase 5, las descargadas)
  covers/previous/<sha1>.jpg|png   portadas que había en los archivos antes de reemplazarlas
  covers/previous/manifest.tsv     fecha, archivo de origen y nombre de la imagen archivada

Los nombres son el hash del contenido: guardar dos veces la misma imagen no duplica nada.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path

from . import paths
from .covers import extract_embedded_cover
from .tag_writer import image_mime

_EXT = {"image/jpeg": ".jpg", "image/png": ".png"}


def _save(folder: Path, data: bytes) -> Path:
    """Guarda `data` como <sha1>.<ext> de forma atómica; si ya existe, no hace nada."""
    ext = _EXT[image_mime(data)]  # ValueError si no es JPG/PNG
    target = folder / f"{hashlib.sha1(data).hexdigest()}{ext}"
    if target.exists():
        return target
    folder.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return target


def store_chosen(data: bytes) -> Path:
    """Copia la imagen elegida por el usuario a la carpeta de la app."""
    return _save(paths.covers_dir() / "chosen", data)


def archive_previous(file_path: Path | str, data: bytes) -> Path:
    """Guarda la portada que tenía `file_path` antes de ser reemplazada."""
    folder = paths.covers_dir() / "previous"
    saved = _save(folder, data)
    with open(folder / "manifest.tsv", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\t{file_path}\t{saved.name}\n")
    return saved


def archive_embedded(file_path: Path | str) -> Path | None:
    """Archiva la portada embebida actual de un archivo, si tiene. Lanza OSError si no puede."""
    data = extract_embedded_cover(Path(file_path))
    return archive_previous(file_path, data) if data else None
