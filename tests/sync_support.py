"""Ayudas de las pruebas de sincronización: biblioteca mínima sin mutagen ni ffmpeg (archivos de bytes y filas a mano)."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def add_track(conn: sqlite3.Connection, root: Path, name: str, artist: str = "Artista", album: str = "Álbum",
              title: str | None = None, content: bytes | None = None, kind: str = "audio", ext: str = ".mp3",
              track_no: int = 1) -> int:
    """Crea un archivo real y sus filas (artista, álbum, archivo, pista). Devuelve tracks.id."""
    path = root / f"{name}{ext}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if content is not None else (name * 500).encode())
    st = os.stat(path)
    with conn:
        ar = conn.execute("SELECT id FROM artists WHERE name = ?", (artist,)).fetchone()
        artist_id = ar["id"] if ar else conn.execute(
            "INSERT INTO artists (name, sort_name) VALUES (?, ?)", (artist, artist)).lastrowid
        al = conn.execute("SELECT id FROM albums WHERE title = ? AND album_artist_id = ?", (album, artist_id)).fetchone()
        album_id = al["id"] if al else conn.execute(
            "INSERT INTO albums (title, album_artist_id) VALUES (?, ?)", (album, artist_id)).lastrowid
        file_id = conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?,?,?,?,?)",
                               (str(path), st.st_size, st.st_mtime_ns, ext[1:], kind)).lastrowid
        return conn.execute(
            "INSERT INTO tracks (album_id, artist_id, title, track_no, duration, file_id) VALUES (?,?,?,?,?,?)",
            (album_id, artist_id, title or name, track_no, 60.0, file_id)).lastrowid


def downgrade_to_v9(conn: sqlite3.Connection) -> None:
    """Deja la base como la dejaba la versión 1.0.0 (sin columnas, tablas ni disparadores de v10)."""
    for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'").fetchall():
        conn.execute(f"DROP TRIGGER {name}")
    conn.execute("DROP INDEX idx_tracks_uuid")
    conn.execute("DROP INDEX idx_playlists_uuid")
    conn.execute("DROP TABLE deleted_playlists")
    conn.execute("DROP TABLE sync_devices")
    for col in ("content_hash", "hash_size", "hash_mtime_ns"):
        conn.execute(f"ALTER TABLE files DROP COLUMN {col}")
    conn.execute("ALTER TABLE tracks DROP COLUMN uuid")
    conn.execute("ALTER TABLE playlists DROP COLUMN uuid")
    conn.execute("ALTER TABLE playlists DROP COLUMN updated_at")
    conn.execute("PRAGMA user_version = 9")
    conn.commit()
