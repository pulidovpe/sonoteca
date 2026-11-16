"""Huella de contenido (SHA-256) de los archivos de audio, con caché en la base (esquema v10).

La huella sirve para dos cosas: verificar que una descarga a otro dispositivo llegó íntegra y detectar que el contenido
de una pista cambió (p. ej. tras editar sus tags). La identidad estable de una pista entre dispositivos es
`tracks.uuid`; la huella NO lo es, porque cambia cada vez que se reescribe el archivo.

La caché vale mientras el tamaño y la fecha de modificación del archivo coincidan con los guardados al calcularla
(`files.hash_size`, `files.hash_mtime_ns`). No depende de Qt ni de mutagen.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from collections.abc import Callable

CHUNK = 1 << 20


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stamp(path: str) -> tuple[int, int] | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_size, st.st_mtime_ns


def ensure_hash(conn: sqlite3.Connection, file_id: int) -> str | None:
    """Huella vigente del archivo: la de la caché si el archivo no cambió; si no, la calcula y la guarda.

    None si el archivo no existe, no se pudo leer o cambió mientras se leía (se reintentará en la próxima pasada)."""
    row = conn.execute("SELECT path, content_hash, hash_size, hash_mtime_ns FROM files WHERE id = ?",
                       (file_id,)).fetchone()
    if row is None:
        return None
    before = _stamp(row["path"])
    if before is None:
        return None
    if row["content_hash"] and (row["hash_size"], row["hash_mtime_ns"]) == before:
        return row["content_hash"]
    try:
        digest = sha256_file(row["path"])
    except OSError:
        return None
    if _stamp(row["path"]) != before:
        return None
    with conn:
        conn.execute("UPDATE files SET content_hash = ?, hash_size = ?, hash_mtime_ns = ? WHERE id = ?",
                     (digest, before[0], before[1], file_id))
    return digest


def stale_file_ids(conn: sqlite3.Connection) -> list[int]:
    """Archivos de audio sin huella vigente según lo que dice la base (el disco se comprueba en `ensure_hash`)."""
    rows = conn.execute(
        "SELECT id FROM files WHERE kind = 'audio' AND (content_hash IS NULL OR hash_size IS NOT size"
        " OR hash_mtime_ns IS NOT mtime_ns) ORDER BY id").fetchall()
    return [r["id"] for r in rows]


def hash_missing(conn: sqlite3.Connection, progress: Callable[[int, int], None] | None = None,
                 should_stop: Callable[[], bool] | None = None) -> int:
    """Calcula las huellas que faltan o quedaron viejas. Devuelve cuántas se calcularon.

    Una transacción por archivo: si se interrumpe, lo ya hecho se conserva."""
    ids = stale_file_ids(conn)
    done = 0
    for n, file_id in enumerate(ids, 1):
        if should_stop and should_stop():
            break
        if ensure_hash(conn, file_id):
            done += 1
        if progress:
            progress(n, len(ids))
    return done
