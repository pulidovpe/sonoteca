"""Listas de reproducción personalizadas (guardadas en la base de datos).

Una lista es un nombre (único, sin distinguir mayúsculas) y una secuencia ordenada de pistas; la
misma pista puede aparecer más de una vez. Si una pista desaparece de la biblioteca, sale de las
listas sola (ON DELETE CASCADE).
"""
from __future__ import annotations

import sqlite3

MAX_NAME = 80


def clean_name(name: str) -> str:
    cleaned = " ".join(str(name).split())
    if not cleaned:
        raise ValueError("Escribe un nombre para la lista")
    if len(cleaned) > MAX_NAME:
        raise ValueError(f"El nombre es demasiado largo (máximo {MAX_NAME} caracteres)")
    return cleaned


def _require(conn: sqlite3.Connection, playlist_id: int) -> None:
    if conn.execute("SELECT 1 FROM playlists WHERE id = ?", (playlist_id,)).fetchone() is None:
        raise ValueError("La lista ya no existe")


def create(conn: sqlite3.Connection, name: str) -> int:
    name = clean_name(name)
    try:
        with conn:
            return conn.execute("INSERT INTO playlists (name) VALUES (?)", (name,)).lastrowid
    except sqlite3.IntegrityError:
        raise ValueError(f"Ya existe una lista llamada \u00ab{name}\u00bb") from None


def rename(conn: sqlite3.Connection, playlist_id: int, name: str) -> None:
    name = clean_name(name)
    _require(conn, playlist_id)
    try:
        with conn:
            conn.execute("UPDATE playlists SET name = ? WHERE id = ?", (name, playlist_id))
    except sqlite3.IntegrityError:
        raise ValueError(f"Ya existe una lista llamada \u00ab{name}\u00bb") from None


def delete(conn: sqlite3.Connection, playlist_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))


_SUMMARY = """
    SELECT p.id, p.name, COUNT(pt.track_id) AS tracks, COALESCE(SUM(t.duration), 0) AS duration
    FROM playlists p
    LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.id
    LEFT JOIN tracks t ON t.id = pt.track_id
"""


def list_playlists(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(_SUMMARY + " GROUP BY p.id ORDER BY p.name COLLATE NOCASE").fetchall()


def cover_album_ids(conn: sqlite3.Connection, playlist_id: int, limit: int = 4) -> list[int]:
    """Álbumes distintos de la lista, en el orden en que aparecen (para el collage de su portada)."""
    rows = conn.execute(
        "SELECT t.album_id FROM playlist_tracks pt JOIN tracks t ON t.id = pt.track_id"
        " WHERE pt.playlist_id = ? GROUP BY t.album_id ORDER BY MIN(pt.position) LIMIT ?",
        (playlist_id, limit)).fetchall()
    return [r["album_id"] for r in rows]


def get_playlist(conn: sqlite3.Connection, playlist_id: int) -> sqlite3.Row | None:
    return conn.execute(_SUMMARY + " WHERE p.id = ? GROUP BY p.id", (playlist_id,)).fetchone()


def track_ids(conn: sqlite3.Connection, playlist_id: int) -> list[int]:
    rows = conn.execute("SELECT track_id FROM playlist_tracks WHERE playlist_id = ?"
                        " ORDER BY position", (playlist_id,)).fetchall()
    return [r["track_id"] for r in rows]


def tracks(conn: sqlite3.Connection, playlist_id: int) -> list[sqlite3.Row]:
    """Pistas en orden, con su posición (desde 0) dentro de la lista."""
    return conn.execute(
        """
        SELECT pt.position, t.id, t.title, t.duration, ar.name AS artist, al.title AS album,
               al.id AS album_id
        FROM playlist_tracks pt
        JOIN tracks t   ON t.id  = pt.track_id
        JOIN artists ar ON ar.id = t.artist_id
        JOIN albums al  ON al.id = t.album_id
        WHERE pt.playlist_id = ?
        ORDER BY pt.position
        """,
        (playlist_id,),
    ).fetchall()


def _existing(conn: sqlite3.Connection, ids: list[int]) -> list[int]:
    return [i for i in (int(x) for x in ids)
            if conn.execute("SELECT 1 FROM tracks WHERE id = ?", (i,)).fetchone()]


def _rewrite(conn: sqlite3.Connection, playlist_id: int, ids: list[int]) -> None:
    """Escribe la lista completa con posiciones 0..n-1 (la clave primaria incluye la posición,
    así que reordenar es más simple y seguro reescribiendo)."""
    with conn:
        conn.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
        conn.executemany("INSERT INTO playlist_tracks (playlist_id, track_id, position)"
                         " VALUES (?, ?, ?)", [(playlist_id, t, i) for i, t in enumerate(ids)])


def add_tracks(conn: sqlite3.Connection, playlist_id: int, ids: list[int]) -> int:
    """Agrega al final. Devuelve cuántas pistas se agregaron (las que no existen se ignoran)."""
    _require(conn, playlist_id)
    valid = _existing(conn, ids)
    if valid:
        _rewrite(conn, playlist_id, track_ids(conn, playlist_id) + valid)
    return len(valid)


def remove_at(conn: sqlite3.Connection, playlist_id: int, position: int) -> None:
    ids = track_ids(conn, playlist_id)
    if not 0 <= position < len(ids):
        raise IndexError(position)
    del ids[position]
    _rewrite(conn, playlist_id, ids)


def move(conn: sqlite3.Connection, playlist_id: int, src: int, dst: int) -> None:
    ids = track_ids(conn, playlist_id)
    if not (0 <= src < len(ids) and 0 <= dst < len(ids)):
        raise IndexError((src, dst))
    ids.insert(dst, ids.pop(src))
    _rewrite(conn, playlist_id, ids)


def replace_all(conn: sqlite3.Connection, playlist_id: int, ids: list[int]) -> None:
    _require(conn, playlist_id)
    _rewrite(conn, playlist_id, _existing(conn, ids))


def create_from_tracks(conn: sqlite3.Connection, name: str, ids: list[int]) -> int:
    """Crea una lista con esas pistas (p. ej. «Guardar la lista actual como lista…»)."""
    playlist_id = create(conn, name)
    add_tracks(conn, playlist_id, ids)
    return playlist_id
