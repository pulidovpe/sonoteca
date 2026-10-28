"""Escritura segura de tags (mp3 y m4a/mp4).

Garantías por archivo:
  1. Se trabaja sobre una copia temporal en la misma carpeta; el original no se toca hasta el final.
  2. Se relee la copia y se comprueba que los cambios quedaron y que la duración no cambió.
  3. Recién entonces se reemplaza el original de forma atómica (os.replace).
  4. Opcionalmente se guarda antes una copia del original en una carpeta de respaldo.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from mutagen.id3 import APIC, ID3, TALB, TCON, TDRC, TIT2, TPE1, TPE2, TPOS, TRCK, ID3NoHeaderError
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4, MP4Cover

from .tags import read_tags

FIELDS = ("title", "artist", "album_artist", "album", "year", "track_no", "disc_no", "genre")
LABELS = {
    "title": "Título", "artist": "Artista", "album_artist": "Artista del álbum",
    "album": "Álbum", "year": "Año", "track_no": "Nº de pista", "disc_no": "Nº de disco",
    "genre": "Género",
}
SINGLE_TRACK_ONLY = {"title", "track_no"}  # no tiene sentido aplicarlos a varias pistas a la vez
MAX_COVER_BYTES = 15 * 1024 * 1024

_ID3_TEXT = {"title": TIT2, "artist": TPE1, "album_artist": TPE2, "album": TALB, "genre": TCON}
_MP4_TEXT = {"title": "\xa9nam", "artist": "\xa9ART", "album_artist": "aART",
             "album": "\xa9alb", "genre": "\xa9gen"}


class TagWriteError(Exception):
    """No se pudo escribir un archivo; el original quedó intacto."""


def normalize_changes(raw: dict) -> dict:
    """Valida y normaliza. Valor None = quitar el campo. Lanza ValueError con mensaje en español."""
    out: dict = {}
    for key, value in raw.items():
        if key not in FIELDS:
            raise ValueError(f"Campo desconocido: {key}")
        text = "" if value is None else str(value).strip()
        if key in {"year", "track_no", "disc_no"}:
            if text == "":
                out[key] = None
                continue
            if not text.isdigit():
                raise ValueError(f"«{LABELS[key]}» debe ser un número")
            number = int(text)
            if key == "year" and not 1000 <= number <= 2999:
                raise ValueError("El año debe estar entre 1000 y 2999")
            if key != "year" and number < 1:
                raise ValueError(f"«{LABELS[key]}» debe ser mayor que 0")
            out[key] = number
        else:
            if key == "title" and not text:
                raise ValueError("El título no puede quedar vacío")
            out[key] = text or None
    return out


def image_mime(data: bytes) -> str:
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    raise ValueError("La portada debe ser una imagen JPG o PNG")


def read_cover_file(path: Path | str) -> bytes:
    path = Path(path)
    try:
        if path.stat().st_size > MAX_COVER_BYTES:
            raise ValueError("La imagen de portada pesa más de 15 MB")
        data = path.read_bytes()
    except OSError as exc:
        reason = "no existe o se movió" if isinstance(exc, FileNotFoundError) else (exc.strerror or str(exc))
        raise ValueError(f"No se pudo leer la imagen «{path.name}»: {reason}") from exc
    image_mime(data)  # valida el formato
    return data


def _with_total(number: int, existing: str | None) -> str:
    """Conserva el total de '3/12' al cambiar solo el número."""
    if existing and "/" in existing:
        total = existing.split("/", 1)[1].strip()
        if total.isdigit() and int(total) > 0:
            return f"{number}/{total}"
    return str(number)


def _apply_mp3(path: Path, changes: dict, cover: bytes | None, id3_version: int) -> None:
    try:
        tags = ID3(path)
    except ID3NoHeaderError:
        tags = ID3()
    enc = 1 if id3_version == 3 else 3  # UTF-16 en v2.3 (lo que esa versión admite); UTF-8 en v2.4
    for field, frame in _ID3_TEXT.items():
        if field in changes:
            tags.delall(frame.__name__)
            if changes[field] is not None:
                tags.add(frame(encoding=enc, text=[changes[field]]))
    if "year" in changes:
        tags.delall("TDRC")
        if changes["year"] is not None:
            tags.add(TDRC(encoding=enc, text=[str(changes["year"])]))
    for field, name, frame in (("track_no", "TRCK", TRCK), ("disc_no", "TPOS", TPOS)):
        if field in changes:
            existing = tags.get(name)
            old_text = str(existing.text[0]) if existing and existing.text else None
            tags.delall(name)
            if changes[field] is not None:
                tags.add(frame(encoding=enc, text=[_with_total(changes[field], old_text)]))
    if cover is not None:
        tags.delall("APIC")
        tags.add(APIC(encoding=enc, mime=image_mime(cover), type=3, desc="Cover", data=cover))
    tags.save(str(path), v2_version=id3_version)


def _apply_mp4(path: Path, changes: dict, cover: bytes | None) -> None:
    mp4 = MP4(path)
    if mp4.tags is None:
        mp4.add_tags()
    tags = mp4.tags
    for field, key in _MP4_TEXT.items():
        if field in changes:
            if changes[field] is None:
                tags.pop(key, None)
            else:
                tags[key] = [changes[field]]
    if "year" in changes:
        if changes["year"] is None:
            tags.pop("\xa9day", None)
        else:
            tags["\xa9day"] = [str(changes["year"])]
    for field, key in (("track_no", "trkn"), ("disc_no", "disk")):
        if field in changes:
            if changes[field] is None:
                tags.pop(key, None)
            else:
                old = tags.get(key)
                total = old[0][1] if old and isinstance(old[0], tuple) else 0
                tags[key] = [(changes[field], total)]
    if cover is not None:
        fmt = MP4Cover.FORMAT_PNG if image_mime(cover) == "image/png" else MP4Cover.FORMAT_JPEG
        tags["covr"] = [MP4Cover(cover, imageformat=fmt)]
    mp4.save()


def _length(path: Path) -> float:
    return float((MP3(path) if path.suffix.lower() == ".mp3" else MP4(path)).info.length)


def _verify(tmp: Path, changes: dict, expect_cover: bool, original_length: float) -> None:
    meta = read_tags(tmp)
    for field in ("title", "artist", "album_artist", "album", "genre", "year", "track_no",
                  "disc_no"):
        wanted = changes.get(field)
        if wanted is not None and getattr(meta, field) != wanted:
            raise TagWriteError(f"la verificación falló en «{LABELS[field]}»")
    if expect_cover and not meta.has_cover:
        raise TagWriteError("la verificación falló: la portada no quedó guardada")
    if abs(_length(tmp) - original_length) > 0.05:
        raise TagWriteError("la verificación falló: la duración del audio cambió")


def _backup(path: Path, backup_dir: Path) -> None:
    backup_dir.mkdir(parents=True, exist_ok=True)
    name = f"{hashlib.sha1(str(path).encode()).hexdigest()[:10]}-{path.name}"
    shutil.copy2(path, backup_dir / name)
    with open(backup_dir / "manifest.tsv", "a", encoding="utf-8") as f:
        f.write(f"{name}\t{path}\n")


def write_tags(path: Path | str, changes: dict, cover: bytes | None = None, *,
               id3_version: int = 3, backup_dir: Path | None = None) -> None:
    """Aplica `changes` (ya normalizados o crudos) a un archivo. Ver garantías en el docstring
    del módulo. Lanza TagWriteError si algo falla (el original no se modifica)."""
    path = Path(path)
    if path.suffix.lower() not in {".mp3", ".m4a", ".mp4"}:
        raise TagWriteError(f"{path.name}: formato no soportado")
    try:
        changes = normalize_changes(changes)
    except ValueError as exc:
        raise TagWriteError(str(exc)) from exc
    tmp = path.with_name(f".{path.stem}.sonoteca-tmp{path.suffix}")
    try:
        shutil.copy2(path, tmp)
        original_length = _length(tmp)
        if path.suffix.lower() == ".mp3":
            _apply_mp3(tmp, changes, cover, id3_version)
        else:
            _apply_mp4(tmp, changes, cover)
        _verify(tmp, changes, cover is not None, original_length)
        if backup_dir is not None:
            _backup(path, backup_dir)
        os.replace(tmp, path)
    except TagWriteError:
        raise
    except Exception as exc:
        raise TagWriteError(f"{path.name}: {type(exc).__name__}: {exc}") from exc
    finally:
        tmp.unlink(missing_ok=True)


def restore_backups(backup_dir: Path | str) -> tuple[int, list[str]]:
    """Restaura los originales guardados en `backup_dir` (usa manifest.tsv)."""
    backup_dir = Path(backup_dir)
    restored, failed = 0, []
    manifest = backup_dir / "manifest.tsv"
    if not manifest.exists():
        raise FileNotFoundError(f"No hay manifest.tsv en {backup_dir}")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if "\t" not in line:
            continue
        name, original = line.split("\t", 1)
        target = Path(original)
        tmp = target.with_name(f".{target.stem}.sonoteca-restore{target.suffix}")
        try:
            shutil.copy2(backup_dir / name, tmp)
            os.replace(tmp, target)
            restored += 1
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            failed.append(f"{original}: {exc}")
    return restored, failed
