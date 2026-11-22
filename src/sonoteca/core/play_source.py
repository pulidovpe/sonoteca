"""Nombre y tipo del origen de lo que suena: «album:3», «playlist:7» (ver PlayerController.sourceKey)."""
from __future__ import annotations

import sqlite3

_SOURCES = {"album": ("albums", "title"), "playlist": ("playlists", "name")}


def describe(conn: sqlite3.Connection, source: str) -> tuple[str, str]:
    """(tipo, nombre) del álbum o la lista de origen. ('', '') si no hay origen, no se entiende o ya no existe."""
    kind, _, raw = (source or "").partition(":")
    if kind not in _SOURCES or not raw.isdigit():
        return "", ""
    table, column = _SOURCES[kind]
    row = conn.execute(f"SELECT {column} FROM {table} WHERE id = ?", (int(raw),)).fetchone()
    if row is None or not row[0]:
        return "", ""
    return kind, row[0]


def whole_album(conn: sqlite3.Connection, ids: list[int]) -> int:
    """Id del álbum si `ids` (2 o más) son exactamente TODAS las pistas de un único álbum, sin importar el orden; 0 si no."""
    wanted = set(ids)
    if len(wanted) < 2:
        return 0
    row = conn.execute("SELECT album_id FROM tracks WHERE id = ?", (next(iter(wanted)),)).fetchone()
    if row is None:
        return 0
    everyone = {r[0] for r in conn.execute("SELECT id FROM tracks WHERE album_id = ?", (row[0],))}
    return row[0] if everyone == wanted else 0
