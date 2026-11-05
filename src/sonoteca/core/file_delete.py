"""Eliminar archivos de música: SIEMPRE a la papelera del sistema (nunca borrado definitivo), y quitándolos de la biblioteca.

`trash` es una función `ruta -> bool` (en la aplicación, `QFile.moveToTrash`); se inyecta para poder probarlo.
Eliminar un archivo: de uno en uno. Eliminar duplicados: por lotes, comprobando antes que el contenido es idéntico."""
from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from pathlib import Path

from .scanner import finalize

Trash = Callable[[str], bool]
ProgressCb = Callable[[int, int], None]


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row(conn: sqlite3.Connection, track_id: int):
    return conn.execute("SELECT t.id, t.file_id, f.path, f.size FROM tracks t JOIN files f ON f.id = t.file_id"
                        " WHERE t.id = ?", (track_id,)).fetchone()


def _forget(conn: sqlite3.Connection, file_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM files WHERE id = ?", (file_id,))      # arrastra pista, listas y contadores (CASCADE)


def delete_track(conn: sqlite3.Connection, track_id: int, trash: Trash) -> tuple[bool, str]:
    """Mueve a la papelera el archivo de UNA pista y la quita de la biblioteca. Devuelve (ok, mensaje)."""
    row = _row(conn, track_id)
    if row is None:
        return False, "La pista ya no está en la biblioteca."
    path = Path(row["path"])
    if path.exists():
        if not trash(str(path)):
            return False, "No se pudo mover el archivo a la papelera; no se hizo ningún cambio."
    _forget(conn, row["file_id"])
    finalize(conn)
    return True, "Archivo movido a la papelera." if path.parent.exists() else "El archivo ya no existía; se quitó de la biblioteca."


def delete_duplicates(conn: sqlite3.Connection, plan: list[dict], trash: Trash,
                      progress: ProgressCb | None = None) -> dict:
    """Elimina lotes de duplicados. `plan`: [{"keep": id_de_pista, "remove": [ids…]}, …].

    Por cada copia a eliminar: la copia que se conserva debe existir, ninguna copia se elimina si su contenido
    (SHA-256) difiere del de la conservada, y solo entonces va a la papelera. Lo que no cumpla queda intacto y se
    informa en `skipped`. Devuelve {"deleted": [ids], "skipped": [(id, motivo)], "bytes": liberados}."""
    result: dict = {"deleted": [], "skipped": [], "bytes": 0}
    jobs = [(group["keep"], rid) for group in plan for rid in group.get("remove", [])]
    for n, (keep_id, remove_id) in enumerate(jobs, 1):
        if progress:
            progress(n - 1, len(jobs))
        if remove_id == keep_id:
            result["skipped"].append((remove_id, "es la copia que se conserva"))
            continue
        keep, victim = _row(conn, keep_id), _row(conn, remove_id)
        if victim is None:
            result["skipped"].append((remove_id, "ya no está en la biblioteca"))
            continue
        if keep is None or not Path(keep["path"]).exists():
            result["skipped"].append((remove_id, "la copia que se conserva no existe: no se elimina nada"))
            continue
        victim_path = Path(victim["path"])
        if victim_path.exists():
            if victim["size"] != keep["size"] or _sha256(str(victim_path)) != _sha256(keep["path"]):
                result["skipped"].append((remove_id, "su contenido no es idéntico al de la copia que se conserva"))
                continue
            if not trash(str(victim_path)):
                result["skipped"].append((remove_id, "no se pudo mover a la papelera"))
                continue
            result["bytes"] += victim["size"] or 0
        _forget(conn, victim["file_id"])
        result["deleted"].append(remove_id)
    finalize(conn)
    if progress:
        progress(len(jobs), len(jobs))
    return result
