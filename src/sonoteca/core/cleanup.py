"""Limpieza de la biblioteca: pistas cuyo archivo ya no existe y álbumes/artistas sin canciones."""
from __future__ import annotations

import os
import sqlite3

# Si faltan más archivos que esta fracción, se asume un disco desconectado y no se borra nada
MISSING_LIMIT = 0.5


def prune_empty(conn: sqlite3.Connection) -> int:
    """Elimina álbumes sin pistas y artistas sin pistas ni álbumes. Devuelve cuántos quitó."""
    before = conn.execute("SELECT (SELECT COUNT(*) FROM albums) + (SELECT COUNT(*) FROM artists)").fetchone()[0]
    with conn:
        conn.execute("DELETE FROM albums WHERE id NOT IN (SELECT DISTINCT album_id FROM tracks)")
        conn.execute("DELETE FROM artists WHERE id NOT IN (SELECT artist_id FROM tracks)"
                     " AND id NOT IN (SELECT album_artist_id FROM albums)")
    after = conn.execute("SELECT (SELECT COUNT(*) FROM albums) + (SELECT COUNT(*) FROM artists)").fetchone()[0]
    return before - after


def purge_missing(conn: sqlite3.Connection) -> dict:
    """Quita de la biblioteca los archivos que ya no existen y lo que quede vacío.

    {"removed": pistas quitadas, "pruned": álbumes/artistas vacíos quitados,
     "skipped": archivos ausentes NO quitados por parecer un disco desconectado}
    """
    rows = conn.execute("SELECT id, path FROM files").fetchall()
    missing = [r["id"] for r in rows if not os.path.exists(r["path"])]
    skipped = 0
    if rows and len(missing) > len(rows) * MISSING_LIMIT:
        skipped, missing = len(missing), []
    with conn:
        for start in range(0, len(missing), 500):
            chunk = missing[start:start + 500]
            conn.execute(f"DELETE FROM files WHERE id IN ({','.join('?' * len(chunk))})", chunk)
    return {"removed": len(missing), "pruned": prune_empty(conn), "skipped": skipped}
