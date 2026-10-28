"""Conexión SQLite y esquema. Las migraciones usan PRAGMA user_version."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import paths

SCHEMA_VERSION = 5

SCHEMA_V1 = """
CREATE TABLE artists (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    sort_name TEXT NOT NULL,
    mbid      TEXT,
    bio       TEXT,
    bio_source TEXT
);

CREATE TABLE albums (
    id              INTEGER PRIMARY KEY,
    title           TEXT NOT NULL COLLATE NOCASE,
    album_artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
    year            INTEGER,
    mbid            TEXT,
    cover_path      TEXT,
    UNIQUE (title, album_artist_id)
);

CREATE TABLE files (
    id       INTEGER PRIMARY KEY,
    path     TEXT NOT NULL UNIQUE,
    size     INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    format   TEXT NOT NULL,
    kind     TEXT NOT NULL CHECK (kind IN ('audio', 'video'))
);

CREATE TABLE tracks (
    id       INTEGER PRIMARY KEY,
    file_id  INTEGER NOT NULL UNIQUE REFERENCES files(id) ON DELETE CASCADE,
    album_id INTEGER NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
    title    TEXT NOT NULL,
    track_no INTEGER,
    disc_no  INTEGER,
    year     INTEGER,
    duration REAL NOT NULL DEFAULT 0,
    genre    TEXT,
    bitrate  INTEGER,
    has_cover INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_tracks_album  ON tracks(album_id);
CREATE INDEX idx_tracks_artist ON tracks(artist_id);
CREATE INDEX idx_albums_year   ON albums(year);

-- Tablas para fases posteriores (se crean ya para fijar el esquema)
CREATE TABLE lyrics (
    track_id      INTEGER PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,
    language      TEXT,
    original_text TEXT,
    synced_lrc    TEXT,
    source        TEXT
);

CREATE TABLE translations (
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    target_lang TEXT NOT NULL,
    text        TEXT NOT NULL,
    provider    TEXT,
    PRIMARY KEY (track_id, target_lang)
);

CREATE TABLE playlists (
    id   INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE playlist_tracks (
    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
    track_id    INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position    INTEGER NOT NULL,
    PRIMARY KEY (playlist_id, position)
);
"""


def _flag_filename_titles_for_rescan(conn: sqlite3.Connection) -> None:
    """v3: el analizador de nombres cambió. Las pistas cuyo título salió del nombre del archivo
    (deducido, o el nombre completo como último recurso) se marcan para que el próximo `scan`
    las relea, sin necesidad de --force."""
    rows = conn.execute("SELECT t.file_id, t.title, t.inferred, f.path FROM tracks t"
                        " JOIN files f ON f.id = t.file_id").fetchall()
    stale = [r["file_id"] for r in rows
             if r["inferred"] or r["title"] == Path(r["path"]).stem]
    conn.executemany("UPDATE files SET mtime_ns = 0 WHERE id = ?", [(i,) for i in stale])


def default_db_path() -> Path:
    return paths.data_dir() / "library.db"


def connect(path: Path | str | None = None) -> sqlite3.Connection:
    """Abre (y migra si hace falta) la base. `":memory:"` sirve para pruebas."""
    if path is None:
        path = default_db_path()
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version > SCHEMA_VERSION:
        raise RuntimeError(
            f"La base tiene versión {version}, más nueva que esta app ({SCHEMA_VERSION})."
        )
    if version < 1:
        with conn:
            conn.executescript(SCHEMA_V1)
            conn.execute("PRAGMA user_version = 1")
    if version < 2:
        with conn:
            # v2: marca las pistas cuyos datos se dedujeron del nombre de archivo
            conn.execute("ALTER TABLE tracks ADD COLUMN inferred INTEGER NOT NULL DEFAULT 0")
            conn.execute("PRAGMA user_version = 2")
    if version < 3:
        with conn:
            _flag_filename_titles_for_rescan(conn)
            conn.execute("PRAGMA user_version = 3")
    if version < 4:
        with conn:
            # v4: información de artista obtenida en línea (se guarda para verla sin conexión)
            for column in ("bio_url", "bio_lang", "image_url", "info_fetched_at"):
                conn.execute(f"ALTER TABLE artists ADD COLUMN {column} TEXT")
            conn.execute("PRAGMA user_version = 4")
    if version < 5:
        with conn:
            # v5: letras obtenidas en línea (se guardan para verlas sin conexión)
            conn.execute("ALTER TABLE lyrics ADD COLUMN fetched_at TEXT")
            conn.execute("ALTER TABLE lyrics ADD COLUMN instrumental INTEGER NOT NULL DEFAULT 0")
            conn.execute("ALTER TABLE lyrics ADD COLUMN lrclib_id INTEGER")
            conn.execute("PRAGMA user_version = 5")
