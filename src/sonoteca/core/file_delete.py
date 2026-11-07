"""Eliminar archivos de música: SIEMPRE a la papelera del sistema (nunca borrado definitivo), y quitándolos de la biblioteca.

`trash` es una función `ruta -> bool` (en la aplicación, `QFile.moveToTrash`); se inyecta para poder probarlo.
Eliminar un archivo: de uno en uno. Eliminar duplicados: por lotes, comprobando antes que el contenido es idéntico."""
from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Callable
from pathlib import Path

from .scanner import finalize
from .search import normalize

Trash = Callable[[str], bool]
ProgressCb = Callable[[int, int], None]

SIMILAR_DURATION_TOLERANCE = 2.0        # s: dos codificaciones de la misma canción no suelen diferir más (silencios, cabeceras)


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row(conn: sqlite3.Connection, track_id: int):
    return conn.execute("SELECT t.id, t.file_id, f.path, f.size FROM tracks t JOIN files f ON f.id = t.file_id"
                        " WHERE t.id = ?", (track_id,)).fetchone()


def _song_key(conn: sqlite3.Connection, track_id: int):
    """(artista, título, duración) de la pista tal como está AHORA en la biblioteca."""
    row = conn.execute("SELECT ar.name, t.title, t.duration FROM tracks t JOIN artists ar ON ar.id = t.artist_id"
                       " WHERE t.id = ?", (track_id,)).fetchone()
    return (normalize(row[0]), normalize(row[1]), row[2] or 0.0) if row else None


def _not_same_song(conn: sqlite3.Connection, keep_id: int, remove_id: int) -> str | None:
    """Motivo por el que `remove_id` NO es otra copia de la canción `keep_id` (None si sí lo es). Para duplicados que no son
    idénticos byte a byte (otro bitrate o formato): mismo artista, mismo título y duración casi igual, leídos de la biblioteca
    en el momento de eliminar, no de lo que mostró la pantalla."""
    keep, victim = _song_key(conn, keep_id), _song_key(conn, remove_id)
    if keep is None or victim is None:
        return "ya no está en la biblioteca"
    if not keep[1] or keep[:2] != victim[:2]:
        return "ya no coincide en artista y título con la copia que se conserva"
    if not keep[2] or not victim[2] or abs(keep[2] - victim[2]) > SIMILAR_DURATION_TOLERANCE:
        return "su duración ya no coincide con la de la copia que se conserva"
    return None


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
                      progress: ProgressCb | None = None, mode: str = "exact") -> dict:
    """Elimina lotes de duplicados. `plan`: [{"keep": id_de_pista, "remove": [ids…]}, …].

    Por cada copia a eliminar: la copia que se conserva debe existir, ninguna copia se elimina si su contenido
    (SHA-256) difiere del de la conservada, y solo entonces va a la papelera. Lo que no cumpla queda intacto y se
    informa en `skipped`. Devuelve {"deleted": [ids], "skipped": [(id, motivo)], "bytes": liberados}.

    `mode="similar"`: la misma canción en archivos que NO son idénticos (otro bitrate o formato). No se puede comparar el
    contenido, así que se exige que la copia a eliminar siga coincidiendo con la conservada en artista, título y duración
    (±2 s) y que sea otro archivo; todo lo demás (la copia conservada existe, papelera, nada definitivo) es igual."""
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
        if mode == "similar":
            why = "es el mismo archivo que la copia que se conserva" if victim["path"] == keep["path"] \
                else _not_same_song(conn, keep_id, remove_id)
            if why:
                result["skipped"].append((remove_id, why))
                continue
        if victim_path.exists():
            if mode != "similar" and (victim["size"] != keep["size"] or _sha256(str(victim_path)) != _sha256(keep["path"])):
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
