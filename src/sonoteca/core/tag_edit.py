"""Edición de tags sobre pistas de la biblioteca: valores comunes, vista previa y aplicación."""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import cover_store, paths
from .library import get_track
from .models import UNKNOWN_ALBUM, UNKNOWN_ARTIST
from .scanner import finalize, reindex_file
from .tag_writer import (
    FIELDS,
    LABELS,
    SINGLE_TRACK_ONLY,
    TagWriteError,
    normalize_changes,
    read_cover_file,
    write_tags,
)

_UNKNOWN = {UNKNOWN_ARTIST, UNKNOWN_ALBUM}


def _rows(conn: sqlite3.Connection, track_ids: list[int]) -> list[sqlite3.Row]:
    marks = ",".join("?" * len(track_ids))
    return conn.execute(
        f"""
        SELECT t.id, t.title, t.track_no, t.disc_no, t.year, t.genre, t.inferred,
               ar.name AS artist, aa.name AS album_artist, al.title AS album, f.path AS path
        FROM tracks t
        JOIN files   f  ON f.id  = t.file_id
        JOIN artists ar ON ar.id = t.artist_id
        JOIN albums  al ON al.id = t.album_id
        JOIN artists aa ON aa.id = al.album_artist_id
        WHERE t.id IN ({marks})
        """,
        track_ids,
    ).fetchall()


def _clean(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    return "" if text in _UNKNOWN else text


def _unique(ids: list[int]) -> list[int]:
    return list(dict.fromkeys(int(i) for i in ids))


_DERIVED = ("title", "artist", "album", "year", "track_no")


def _derived(row: sqlite3.Row) -> dict:
    """Datos que la biblioteca dedujo del nombre del archivo (la pista está «por revisar») y que el editor
    muestra como si fueran tags. Si no se escriben, el archivo sigue sin ellos y la pista nunca sale de la lista."""
    if not row["inferred"]:
        return {}
    raw = {f: row[f] for f in _DERIVED if row[f] not in (None, "") and _clean(row[f]) != ""}
    out: dict = {}
    for key, value in raw.items():
        try:
            out.update(normalize_changes({key: value}))
        except ValueError:
            continue  # un dato deducido inválido simplemente no se escribe
    return out


def describe_location(paths: list[str]) -> str:
    """Dónde está guardado lo que se edita: la ruta completa si es un archivo; si son varios, cuántos y en qué carpeta."""
    unique = sorted({str(p) for p in paths if p})
    if not unique:
        return ""
    if len(unique) == 1:
        return unique[0]
    folders = sorted({os.path.dirname(p) for p in unique})
    if len(folders) == 1:
        return f"{len(unique)} archivos en {folders[0]}"
    try:
        common = os.path.commonpath(folders)
    except ValueError:                        # unidades distintas (Windows)
        common = ""
    useful = bool(common) and common != os.path.dirname(common)       # una raíz sola («/») no informa
    return f"{len(unique)} archivos en {len(folders)} carpetas" + (f"; carpeta común: {common}" if useful else "")


def common_values(conn: sqlite3.Connection, track_ids: list[int]) -> dict:
    """Valor de cada campo si es el mismo en todas las pistas; si no, vacío y `mixed=True`."""
    rows = _rows(conn, _unique(track_ids))
    out: dict = {"count": len(rows), "single": len(rows) == 1, "location": describe_location([r["path"] for r in rows])}
    for f in FIELDS:
        values = {_clean(r[f]) for r in rows}
        out[f] = {"value": next(iter(values)) if len(values) == 1 else "", "mixed": len(values) > 1}
    return out


def _check_scope(track_ids: list[int], changes: dict) -> None:
    if len(track_ids) > 1 and SINGLE_TRACK_ONLY & set(changes):
        raise ValueError("El título y el número de pista solo se pueden editar de una pista a la vez")


def preview(conn: sqlite3.Connection, track_ids: list[int], raw_changes: dict,
            cover_path: str = "") -> dict:
    """Líneas legibles de lo que cambiaría. Lanza ValueError si hay datos inválidos."""
    ids = _unique(track_ids)
    changes = normalize_changes(raw_changes)
    _check_scope(ids, changes)
    if cover_path:
        read_cover_file(cover_path)
    rows = _rows(conn, ids)
    lines = []
    for f in FIELDS:
        if f not in changes:
            continue
        old = sorted({_clean(r[f]) or "(vacío)" for r in rows})
        shown = ", ".join(f"«{v}»" for v in old[:3]) + (" y otros" if len(old) > 3 else "")
        new = "quitar" if changes[f] is None else f"«{changes[f]}»"
        lines.append(f"{LABELS[f]}: {shown} \u2192 {new}")
    if cover_path:
        lines.append(f"Portada: se reemplaza por {Path(cover_path).name}")
    derived = [(r, {k: v for k, v in _derived(r).items() if k not in changes}) for r in rows]
    derived = [(r, d) for r, d in derived if d]
    if len(derived) == 1:
        shown = ", ".join(f"{LABELS[k]} «{v}»" for k, v in derived[0][1].items())
        lines.append(f"Se escribirán también los datos deducidos del nombre del archivo: {shown}")
    elif derived:
        lines.append(f"En {len(derived)} pistas se escribirán también los datos deducidos del nombre del archivo "
                     "(título, artista, álbum, año o nº de pista que se ven en el editor)")
    return {"count": len(ids), "lines": lines}


@dataclass
class EditResult:
    updated: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)
    pending: int = 0          # archivos cuya escritura quedó aplazada (en uso): la app ya muestra los tags nuevos
    backup_dir: str = ""
    album_id: int = 0

    def to_dict(self) -> dict:
        return {
            "updated": self.updated,
            "failed": [{"path": p, "message": m} for p, m in self.failed],
            "pending": self.pending,
            "backupDir": self.backup_dir,
            "albumId": self.album_id,
        }


def apply_edit(conn: sqlite3.Connection, track_ids: list[int], raw_changes: dict,
               cover_path: str = "", backup: bool = True, id3_version: int = 3,
               progress: Callable[[int, int], None] | None = None,
               is_busy: Callable[[Path], bool] | None = None,
               defer_on_lock: bool = False) -> EditResult:
    """Escribe los cambios en los archivos y actualiza la base conservando los ids de pista.
    Un archivo en uso (`is_busy`) no se reemplaza: su escritura queda aplazada (`result.pending`), la base ya refleja los
    tags nuevos y el volcado al archivo lo hace `pending_tags.flush`.
    Un archivo que falla no detiene a los demás. Lanza ValueError si los datos son inválidos."""
    ids = _unique(track_ids)
    changes = normalize_changes(raw_changes)
    _check_scope(ids, changes)
    cover = read_cover_file(cover_path) if cover_path else None
    if cover is not None:
        cover_store.store_chosen(cover)  # copia propia en la carpeta de la app
    if not changes and cover is None:
        raise ValueError("No hay cambios que aplicar")

    result = EditResult()
    backup_dir = None
    if backup:
        backup_dir = paths.data_dir() / "backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
        result.backup_dir = str(backup_dir)
    for i, track_id in enumerate(ids, start=1):
        row = get_track(conn, track_id)
        if row is None:
            result.failed.append((f"#{track_id}", "La pista ya no está en la biblioteca"))
        else:
            path = Path(row["path"])
            try:
                if cover is not None:
                    cover_store.archive_embedded(path)  # si no se puede archivar, no se toca el archivo
                per_file = {**{k: v for k, v in _derived(_rows(conn, [track_id])[0]).items()
                               if k not in changes}, **changes}
                written = write_tags(path, per_file, cover, id3_version=id3_version, backup_dir=backup_dir,
                                     is_busy=is_busy, defer_on_lock=defer_on_lock)
                reindex_file(conn, path)        # lee de la copia pendiente si la escritura quedó aplazada
                if not written:
                    result.pending += 1
                result.updated += 1
            except (TagWriteError, OSError) as exc:
                result.failed.append((str(path), str(exc)))
        if progress:
            progress(i, len(ids))
    finalize(conn)
    if ids:
        first = conn.execute("SELECT album_id FROM tracks WHERE id = ?", (ids[0],)).fetchone()
        result.album_id = first["album_id"] if first else 0
    return result
