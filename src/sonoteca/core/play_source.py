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
