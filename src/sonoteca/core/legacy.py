"""Migración desde el nombre anterior (`musicapp`) a `sonoteca`.

Antes de 0.9.0 los datos vivían en carpetas llamadas «musicapp». La primera vez que arranca la versión
nueva se MUEVEN (no se copian) a las carpetas de «sonoteca»: base de datos, portadas, fotos de artistas,
copias de respaldo y ajustes. Las rutas absolutas que la base guardó de las portadas se reescriben para que
apunten a la carpeta nueva, y la clave de DeepL se pasa al llavero con el nombre nuevo.

Nunca sobrescribe: si ya existe una biblioteca nueva, la antigua se deja intacta. Un fallo se registra en
el informe y no impide arrancar.
"""
from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_cache_dir, user_data_dir

from . import paths

LEGACY_APP = "musicapp"
DB_NAME = "library.db"


@dataclass
class Report:
    moved: list[str] = field(default_factory=list)       # elementos movidos a la carpeta nueva
    skipped: list[str] = field(default_factory=list)     # lo que no se tocó y por qué
    errors: list[str] = field(default_factory=list)
    rewritten_paths: int = 0                              # rutas de portadas reescritas en la base
    keyring_moved: bool = False

    @property
    def migrated(self) -> bool:
        return bool(self.moved)


def legacy_data_candidates() -> list[Path]:
    """Dónde pudo haber guardado datos la versión anterior (carpeta estándar y la de reserva de un venv)."""
    return [Path(user_data_dir(LEGACY_APP, appauthor=False)), Path.home() / f".{LEGACY_APP}" / "data"]


def legacy_cache_candidates() -> list[Path]:
    return [Path(user_cache_dir(LEGACY_APP, appauthor=False)), Path.home() / f".{LEGACY_APP}" / "cache"]


def _move_children(src: Path, dst: Path, report: Report, label: str) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for child in sorted(src.iterdir()):
        target = dst / child.name
        if target.exists():
            report.skipped.append(f"{label}/{child.name}: ya existe en la carpeta nueva")
            continue
        try:
            shutil.move(str(child), str(target))
            report.moved.append(f"{label}/{child.name}")
        except OSError as exc:
            report.errors.append(f"{label}/{child.name}: {exc}")
    try:
        src.rmdir()   # solo si quedó vacía
    except OSError:
        pass


def rewrite_cover_paths(db_path: Path, old_dir: Path, new_dir: Path) -> int:
    """Las portadas elegidas se guardan con ruta absoluta en `albums.cover_path`: se apunta a la carpeta nueva."""
    old, new = str(old_dir), str(new_dir)
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT id, cover_path FROM albums WHERE cover_path IS NOT NULL").fetchall()
        changes = [(new + value[len(old):], row_id) for row_id, value in rows
                   if value == old or value.startswith(old + "/") or value.startswith(old + "\\")]
        with conn:
            conn.executemany("UPDATE albums SET cover_path = ? WHERE id = ?", changes)
        return len(changes)
    finally:
        conn.close()


def _migrate_keyring(report: Report) -> None:
    try:
        import keyring

        from ..online import translate
        old = keyring.get_password(LEGACY_APP, translate.KEYRING_USER)
        if old and not keyring.get_password(translate.KEYRING_SERVICE, translate.KEYRING_USER):
            keyring.set_password(translate.KEYRING_SERVICE, translate.KEYRING_USER, old)
            keyring.delete_password(LEGACY_APP, translate.KEYRING_USER)
            report.keyring_moved = True
    except Exception:  # noqa: BLE001  (sin llavero disponible: la clave se vuelve a escribir y listo)
        pass


def migrate(legacy_data: list[Path], legacy_cache: list[Path], data: Path, cache: Path,
            keyring_too: bool = True) -> Report:
    """Mueve los datos antiguos a `data`/`cache`. Pensada para probarse con rutas explícitas."""
    report = Report()
    source = next((p for p in legacy_data if (p / DB_NAME).exists()), None)
    if source is not None and source.resolve() != data.resolve():
        if (data / DB_NAME).exists():
            report.skipped.append(f"{source}: ya hay una biblioteca en {data}; no se toca la antigua")
        else:
            _move_children(source, data, report, "datos")
            if (data / DB_NAME).exists():
                try:
                    report.rewritten_paths = rewrite_cover_paths(data / DB_NAME, source, data)
                except (sqlite3.Error, OSError) as exc:
                    report.errors.append(f"rutas de portadas: {exc}")
    cache_src = next((p for p in legacy_cache if p.is_dir() and any(p.iterdir())), None)
    if cache_src is not None and report.migrated and cache_src.resolve() != cache.resolve():
        _move_children(cache_src, cache, report, "cach\u00e9")
    if keyring_too and report.migrated:
        _migrate_keyring(report)
    return report


_done = False


def ensure_migrated() -> Report | None:
    """Se llama una vez al arrancar (app y CLI), antes de abrir la base. No hace nada si el usuario fijó
    las carpetas con SONOTECA_DATA_DIR / SONOTECA_CACHE_DIR (entonces no hay nada «antiguo» que mover)."""
    global _done
    if _done:
        return None
    _done = True
    if paths.env("DATA_DIR") or paths.env("CACHE_DIR"):
        return None
    try:
        return migrate(legacy_data_candidates(), legacy_cache_candidates(), paths.data_dir(), paths.cache_dir())
    except OSError:
        return None
