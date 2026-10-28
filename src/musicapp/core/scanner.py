"""Escaneo incremental de carpetas hacia la base SQLite."""
from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Callable, Iterator
from pathlib import Path

from .models import SUPPORTED_EXTENSIONS, ScanResult, TrackMeta
from .tags import TagReadError, read_tags

ProgressCb = Callable[[int, Path], None]


def sort_name(name: str) -> str:
    """'The Beatles' -> 'Beatles, The' para ordenar alfabéticamente."""
    m = re.match(r"^(the|el|la|los|las)\s+(.+)$", name.strip(), re.IGNORECASE)
    if m:
        return f"{m.group(2)}, {m.group(1).title()}"
    return name.strip()


def iter_media_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if name.startswith("."):  # incluye los '._*' de macOS en discos externos
                continue
            p = Path(dirpath) / name
            if p.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield p


def _get_artist(conn: sqlite3.Connection, name: str, fix_case: bool = False) -> int:
    row = conn.execute("SELECT id, name FROM artists WHERE name = ?", (name,)).fetchone()
    if row:
        if fix_case and row["name"] != name:  # mismo nombre con otras mayúsculas: gana lo nuevo
            conn.execute("UPDATE artists SET name = ?, sort_name = ? WHERE id = ?",
                         (name, sort_name(name), row["id"]))
        return row["id"]
    cur = conn.execute(
        "INSERT INTO artists (name, sort_name) VALUES (?, ?)", (name, sort_name(name))
    )
    return cur.lastrowid


def _get_album(conn: sqlite3.Connection, title: str, artist_id: int, fix_case: bool = False) -> int:
    row = conn.execute(
        "SELECT id, title FROM albums WHERE title = ? AND album_artist_id = ?", (title, artist_id)
    ).fetchone()
    if row:
        if fix_case and row["title"] != title:
            conn.execute("UPDATE albums SET title = ? WHERE id = ?", (title, row["id"]))
        return row["id"]
    cur = conn.execute(
        "INSERT INTO albums (title, album_artist_id) VALUES (?, ?)", (title, artist_id)
    )
    return cur.lastrowid


def _upsert(conn: sqlite3.Connection, meta: TrackMeta, size: int, mtime_ns: int,
            fix_case: bool = False) -> bool:
    """Inserta o actualiza un archivo y su pista. Devuelve True si ya existía."""
    path_str = str(meta.path)
    existing = conn.execute("SELECT id FROM files WHERE path = ?", (path_str,)).fetchone()
    if existing:
        file_id = existing["id"]
        conn.execute(
            "UPDATE files SET size=?, mtime_ns=?, format=?, kind=? WHERE id=?",
            (size, mtime_ns, meta.format, meta.kind, file_id),
        )
    else:
        file_id = conn.execute(
            "INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?,?,?,?,?)",
            (path_str, size, mtime_ns, meta.format, meta.kind),
        ).lastrowid

    artist_id = _get_artist(conn, meta.artist, fix_case)
    album_artist_id = _get_artist(conn, meta.album_artist, fix_case)
    album_id = _get_album(conn, meta.album, album_artist_id, fix_case)

    values = (
        album_id, artist_id, meta.title, meta.track_no, meta.disc_no, meta.year,
        meta.duration, meta.genre, meta.bitrate, int(meta.has_cover), int(meta.inferred),
    )
    if existing:
        conn.execute(
            "UPDATE tracks SET album_id=?, artist_id=?, title=?, track_no=?, disc_no=?, year=?,"
            " duration=?, genre=?, bitrate=?, has_cover=?, inferred=? WHERE file_id=?",
            (*values, file_id),
        )
    else:
        conn.execute(
            "INSERT INTO tracks (album_id, artist_id, title, track_no, disc_no, year, duration,"
            " genre, bitrate, has_cover, inferred, file_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (*values, file_id),
        )
    return existing is not None


def _refresh_album_years(conn: sqlite3.Connection) -> None:
    """El año del álbum es el menor año no nulo entre sus pistas."""
    conn.execute(
        "UPDATE albums SET year = (SELECT MIN(t.year) FROM tracks t"
        " WHERE t.album_id = albums.id AND t.year IS NOT NULL)"
    )


def _prune_orphans(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM albums WHERE id NOT IN (SELECT DISTINCT album_id FROM tracks)")
    conn.execute(
        "DELETE FROM artists WHERE id NOT IN (SELECT artist_id FROM tracks)"
        " AND id NOT IN (SELECT album_artist_id FROM albums)"
    )


def reindex_file(conn: sqlite3.Connection, path: Path) -> None:
    """Relee un solo archivo (p. ej. tras editar sus tags) y actualiza su fila conservando el id."""
    path = Path(path)
    meta = read_tags(path)
    st = path.stat()
    with conn:
        _upsert(conn, meta, st.st_size, st.st_mtime_ns, fix_case=True)  # edición: manda la grafía nueva


def finalize(conn: sqlite3.Connection) -> None:
    """Recalcula años de álbum y elimina álbumes/artistas que quedaron sin pistas."""
    with conn:
        _refresh_album_years(conn)
        _prune_orphans(conn)


def scan(conn: sqlite3.Connection, root: Path | str, progress: ProgressCb | None = None,
         force: bool = False) -> ScanResult:
    """Indexa `root`. Solo relee archivos nuevos o modificados (tamaño o mtime distintos).

    Con `force=True` relee todos los archivos aunque no hayan cambiado.
    Los archivos bajo `root` que ya no existen se eliminan de la base. Los de otras
    carpetas raíz no se tocan.
    """
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(root)

    result = ScanResult()
    known = {
        row["path"]: (row["size"], row["mtime_ns"])
        for row in conn.execute("SELECT path, size, mtime_ns FROM files")
    }
    seen: set[str] = set()

    for i, path in enumerate(iter_media_files(root), start=1):
        path_str = str(path)
        seen.add(path_str)
        if progress:
            progress(i, path)
        try:
            st = path.stat()
        except OSError as exc:
            result.errors.append((path, f"OSError: {exc}"))
            continue
        if not force and known.get(path_str) == (st.st_size, st.st_mtime_ns):
            result.unchanged += 1
            continue
        try:
            meta = read_tags(path)
        except TagReadError as exc:
            result.errors.append((path, str(exc)))
            continue
        with conn:  # una transacción por archivo: un fallo no deja datos a medias
            was_known = _upsert(conn, meta, st.st_size, st.st_mtime_ns)
        if was_known:
            result.updated += 1
        else:
            result.added += 1

    prefix = str(root) + os.sep
    with conn:
        for path_str in known:
            if path_str.startswith(prefix) and path_str not in seen:
                conn.execute("DELETE FROM files WHERE path = ?", (path_str,))
                result.removed += 1
        _refresh_album_years(conn)
        _prune_orphans(conn)
    return result
