"""«Por revisar»: vaciar la lista y volver a leer los tags de sus archivos."""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

from . import library
from .scanner import finalize, reindex_file
from .tags import TagReadError

ProgressCb = Callable[[int, int], None]


def dismiss_listed(conn: sqlite3.Connection) -> int:
    """Quita de «Por revisar» todas las pistas que hoy aparecen allí. No toca archivos ni tags.

    Se recuerda por archivo, así que sigue oculta aunque se vuelva a escanear la carpeta."""
    ids = [r["id"] for r in library.list_incomplete(conn)]
    file_ids: list[tuple[int]] = []
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        file_ids += [(r["file_id"],) for r in conn.execute(
            f"SELECT file_id FROM tracks WHERE id IN ({','.join('?' * len(chunk))})", chunk)]
    with conn:
        conn.executemany("INSERT OR IGNORE INTO review_dismissed (file_id) VALUES (?)", file_ids)
    return len(file_ids)


def dismissed_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM review_dismissed").fetchone()[0]


def restore_dismissed(conn: sqlite3.Connection) -> int:
    """Vuelve a mostrar las pistas descartadas que siguen incompletas. Devuelve cuántas se restauraron."""
    n = dismissed_count(conn)
    with conn:
        conn.execute("DELETE FROM review_dismissed")
    return n


def rescan_tracks(conn: sqlite3.Connection, track_ids: list[int],
                  progress: ProgressCb | None = None) -> dict:
    """Relee los tags de los archivos de estas pistas (sin red) y actualiza la biblioteca.

    {"checked": leídas, "resolved": ya no necesitan revisión, "missing": archivo ausente,
     "errors": no se pudo leer}"""
    ids = [int(i) for i in track_ids]
    rows = []
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        rows += conn.execute(
            f"SELECT t.id, f.path FROM tracks t JOIN files f ON f.id = t.file_id"
            f" WHERE t.id IN ({','.join('?' * len(chunk))})", chunk).fetchall()
    checked = missing = errors = 0
    for n, row in enumerate(rows, 1):
        if progress:
            progress(n, len(rows))
        path = Path(row["path"])
        if not path.exists():
            missing += 1
            continue
        try:
            reindex_file(conn, path)
            checked += 1
        except (TagReadError, OSError):
            errors += 1
    finalize(conn)
    still = {r["id"] for r in library.list_incomplete(conn)}
    resolved = sum(1 for i in ids if i not in still)
    return {"checked": checked, "resolved": resolved, "missing": missing, "errors": errors}
