"""Exportar e importar la biblioteca (un solo archivo `.sonoteca`).

El archivo es un zip con:
  manifest.json   versión de la app y del esquema, conteos, carpeta de datos de origen y carpeta de música común
  library.db      copia consistente de la base (API de respaldo de SQLite): canciones, listas, letras, contadores…
  covers/chosen/  portadas elegidas o descargadas
  artists/        fotos de artistas
NO incluye los ajustes en línea (contienen tu correo de contacto), la clave de DeepL ni la música misma.

Importar reemplaza la biblioteca actual, así que NO se aplica sobre la marcha: `stage_import` valida y deja el
contenido en `pending_import/`, y `apply_pending_import` lo aplica al arrancar, antes de abrir la base. Antes de
reemplazar nada, la biblioteca actual se guarda en `backups/antes-de-importar-<fecha>/`.
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path, PurePosixPath

from . import paths
from .db import SCHEMA_VERSION, connect
from .legacy import rewrite_cover_paths

FORMAT = 1
EXTENSION = ".sonoteca"
PENDING = "pending_import"
RESET_MARKER = "pending_reset"
_ALLOWED_DIRS = ("covers/chosen/", "artists/")

ProgressCb = Callable[[int, int], None]


class PortableError(Exception):
    """Mensaje pensado para mostrarse tal cual al usuario."""


def _count(conn: sqlite3.Connection, table: str) -> int:
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    except sqlite3.Error:
        return 0


def _common_root(file_paths: list[str]) -> str:
    """Carpeta común a todas las canciones ('' si no hay o solo comparten la raíz)."""
    if not file_paths:
        return ""
    try:
        root = os.path.commonpath([os.path.dirname(p) for p in file_paths])
    except ValueError:   # rutas de unidades distintas (Windows)
        return ""
    return root if root not in ("", "/", "\\") and len(Path(root).parts) > 1 else ""


def export_library(db_path: Path | str, dest: Path | str, include_images: bool = True,
                   data: Path | None = None, progress: ProgressCb | None = None) -> dict:
    """Escribe `dest` (.sonoteca). Devuelve el manifiesto. La base puede estar en uso: se copia con la API de respaldo."""
    dest = Path(dest)
    data = data or paths.data_dir()
    with tempfile.TemporaryDirectory(prefix="sonoteca-export-") as tmp:
        snapshot = Path(tmp) / "library.db"
        src = sqlite3.connect(db_path)
        dst = sqlite3.connect(snapshot)
        try:
            src.backup(dst)
            dst.row_factory = sqlite3.Row
            manifest = {
                "app": "sonoteca", "format": FORMAT, "created": datetime.now().isoformat(timespec="seconds"),
                "schema": dst.execute("PRAGMA user_version").fetchone()[0],
                "tracks": _count(dst, "tracks"), "albums": _count(dst, "albums"),
                "artists": _count(dst, "artists"), "playlists": _count(dst, "playlists"),
                "data_dir": str(data),
                "music_root": _common_root([r[0] for r in dst.execute("SELECT path FROM files")]),
                "images": include_images,
            }
            try:
                import sonoteca
                manifest["version"] = sonoteca.__version__
            except ImportError:
                manifest["version"] = ""
        finally:
            src.close()
            dst.close()

        images: list[tuple[Path, str]] = []
        if include_images:
            for folder, arc in ((data / "covers" / "chosen", "covers/chosen"), (data / "artists", "artists")):
                if folder.is_dir():
                    images += [(p, f"{arc}/{p.name}") for p in sorted(folder.iterdir()) if p.is_file()]
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        try:
            with zipfile.ZipFile(part, "w") as z:
                z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2),
                           compress_type=zipfile.ZIP_DEFLATED)
                z.write(snapshot, "library.db", compress_type=zipfile.ZIP_DEFLATED)
                for n, (path, arcname) in enumerate(images, 1):
                    if progress:
                        progress(n, len(images))
                    z.write(path, arcname, compress_type=zipfile.ZIP_STORED)   # JPG/PNG ya van comprimidos
            os.replace(part, dest)
        finally:
            part.unlink(missing_ok=True)
    return manifest


def _check_names(z: zipfile.ZipFile) -> None:
    for name in z.namelist():
        pure = PurePosixPath(name)
        if pure.is_absolute() or ".." in pure.parts:
            raise PortableError("El archivo no es una biblioteca de Sonoteca v\u00e1lida (rutas inseguras).")
        if name not in ("manifest.json", "library.db") and not name.startswith(_ALLOWED_DIRS):
            raise PortableError("El archivo no es una biblioteca de Sonoteca v\u00e1lida (contenido inesperado).")


def inspect_bundle(path: Path | str) -> dict:
    """Valida el archivo y devuelve su manifiesto, sin tocar nada."""
    path = Path(path)
    if not path.is_file() or not zipfile.is_zipfile(path):
        raise PortableError("El archivo no es una biblioteca de Sonoteca (.sonoteca).")
    with zipfile.ZipFile(path) as z:
        _check_names(z)
        try:
            manifest = json.loads(z.read("manifest.json"))
        except (KeyError, ValueError) as exc:
            raise PortableError("Falta el manifiesto: no es una exportaci\u00f3n de Sonoteca.") from exc
        if "library.db" not in z.namelist():
            raise PortableError("El archivo no contiene la base de datos.")
    if manifest.get("app") != "sonoteca" or int(manifest.get("format", 0)) > FORMAT:
        raise PortableError("Formato no reconocido: puede venir de una versi\u00f3n m\u00e1s nueva de Sonoteca.")
    if int(manifest.get("schema", 0)) > SCHEMA_VERSION:
        raise PortableError("La biblioteca se cre\u00f3 con una versi\u00f3n m\u00e1s nueva de Sonoteca. Actualiza la app.")
    return manifest


def stage_import(bundle: Path | str, new_music_root: str | None = None, data: Path | None = None) -> dict:
    """Valida y extrae a `pending_import/`; se aplica en el próximo arranque. `new_music_root` sustituye la
    carpeta de música de origen (si la música está en otra ruta en este equipo)."""
    data = data or paths.data_dir()
    manifest = inspect_bundle(bundle)
    pending = data / PENDING
    shutil.rmtree(pending, ignore_errors=True)
    (data / RESET_MARKER).unlink(missing_ok=True)   # si había un «empezar de cero» pendiente, manda esta importación
    pending.mkdir(parents=True)
    try:
        with zipfile.ZipFile(bundle) as z:
            z.extractall(pending)
        probe = sqlite3.connect(pending / "library.db")
        try:
            verdict = probe.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            probe.close()
        if verdict != "ok":
            raise PortableError("La base de datos del archivo est\u00e1 da\u00f1ada; no se import\u00f3 nada.")
        old_root = manifest.get("music_root", "")
        if new_music_root and old_root and new_music_root.rstrip("/\\") != old_root.rstrip("/\\"):
            (pending / "remap.json").write_text(json.dumps({"from": old_root, "to": new_music_root}), encoding="utf-8")
    except (PortableError, OSError, sqlite3.Error, zipfile.BadZipFile) as exc:
        shutil.rmtree(pending, ignore_errors=True)
        if isinstance(exc, PortableError):
            raise
        raise PortableError(f"No se pudo leer el archivo: {exc}") from exc
    return manifest


def has_pending_import(data: Path | None = None) -> bool:
    return ((data or paths.data_dir()) / PENDING / "library.db").exists()


def remap_music_root(db_path: Path | str, old: str, new: str) -> int:
    """Cambia el prefijo de las rutas de los archivos de música. Devuelve cuántas rutas cambió."""
    old, new = old.rstrip("/\\"), new.rstrip("/\\")
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT id, path FROM files").fetchall()
        changes = [(new + p[len(old):], i) for i, p in rows if p == old or p.startswith((old + "/", old + "\\"))]
        with conn:
            conn.executemany("UPDATE files SET path = ? WHERE id = ?", changes)
        return len(changes)
    finally:
        conn.close()


def apply_pending_import(data: Path | None = None) -> dict | None:
    """Aplica una importación preparada. Llamar al arrancar, ANTES de abrir la base. None si no había nada."""
    data = data or paths.data_dir()
    pending = data / PENDING
    if not (pending / "library.db").exists():
        return None
    backup = data / "backups" / f"antes-de-importar-{datetime.now():%Y%m%d-%H%M%S}"
    backup.mkdir(parents=True, exist_ok=True)
    for name in ("library.db", "library.db-wal", "library.db-shm", "covers", "artists"):
        current = data / name
        if current.exists():
            shutil.move(str(current), str(backup / name))
    shutil.move(str(pending / "library.db"), str(data / "library.db"))
    for name in ("covers", "artists"):
        if (pending / name).exists():
            shutil.move(str(pending / name), str(data / name))
    report = {"backup": str(backup), "remapped": 0, "cover_paths": 0, "missing": 0}
    try:
        manifest = json.loads((pending / "manifest.json").read_text(encoding="utf-8"))
        old_data = manifest.get("data_dir", "")
        if old_data and Path(old_data) != data:
            report["cover_paths"] = rewrite_cover_paths(data / "library.db", Path(old_data), data)
        remap = pending / "remap.json"
        if remap.exists():
            r = json.loads(remap.read_text(encoding="utf-8"))
            report["remapped"] = remap_music_root(data / "library.db", r["from"], r["to"])
    finally:
        shutil.rmtree(pending, ignore_errors=True)
    conn = connect(data / "library.db")   # migra el esquema si venía de una versión anterior
    try:
        report["missing"] = sum(1 for (p,) in conn.execute("SELECT path FROM files") if not Path(p).exists())
    finally:
        conn.close()
    return report


# ---- empezar desde cero ----
def stage_reset(keep_backup: bool = True, data: Path | None = None) -> None:
    """Prepara «empezar desde cero»: se aplica al volver a abrir la app, antes de abrir la base."""
    data = data or paths.data_dir()
    data.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(data / PENDING, ignore_errors=True)   # una importación pendiente queda anulada
    (data / RESET_MARKER).write_text(json.dumps({"keep_backup": bool(keep_backup)}), encoding="utf-8")


def has_pending_reset(data: Path | None = None) -> bool:
    return ((data or paths.data_dir()) / RESET_MARKER).exists()


def apply_pending_reset(data: Path | None = None, cache: Path | None = None) -> dict | None:
    """Vacía la biblioteca: base de datos, portadas y fotos descargadas, y la caché de miniaturas (sus nombres
    dependen de los ids de álbum, que empiezan de nuevo). Se CONSERVAN los ajustes (internet, servidores, contacto)
    y la clave de DeepL. Con `keep_backup` todo se guarda antes en `backups/antes-de-reiniciar-<fecha>/`."""
    data = data or paths.data_dir()
    marker = data / RESET_MARKER
    if not marker.exists():
        return None
    try:
        keep = bool(json.loads(marker.read_text(encoding="utf-8")).get("keep_backup", True))
    except (OSError, ValueError):
        keep = True
    backup = data / "backups" / f"antes-de-reiniciar-{datetime.now():%Y%m%d-%H%M%S}"
    if keep:
        backup.mkdir(parents=True, exist_ok=True)
    removed = []
    for name in ("library.db", "library.db-wal", "library.db-shm", "covers", "artists", PENDING):
        item = data / name
        if not item.exists():
            continue
        if keep and name != PENDING:
            shutil.move(str(item), str(backup / name))
        elif item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        else:
            item.unlink(missing_ok=True)
        removed.append(name)
    cache = cache or paths.cache_dir()
    here, there = data.resolve(), cache.resolve()
    if cache.is_dir() and there != here and there not in here.parents and here not in there.parents:
        shutil.rmtree(cache, ignore_errors=True)   # (si la cach\u00e9 y los datos comparten carpeta, no se toca)
    marker.unlink(missing_ok=True)
    return {"backup": str(backup) if keep else "", "removed": removed}
