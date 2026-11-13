"""Conexión SQLite y esquema. Las migraciones usan PRAGMA user_version."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from . import paths

SCHEMA_VERSION = 10

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
        # Con WAL, NORMAL no hace fsync en cada commit (solo al vaciar el WAL): no hay corrupción posible, y como mucho se
        # pierde lo último escrito si el sistema se cae. El escáner hace una transacción por archivo, así que esto lo acelera.
        conn.execute("PRAGMA synchronous = NORMAL")
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
    if version < 6:
        with conn:
            # v6: contador de reproducciones por pista
            conn.execute(
                "CREATE TABLE IF NOT EXISTS play_stats ("
                " track_id INTEGER PRIMARY KEY REFERENCES tracks(id) ON DELETE CASCADE,"
                " plays INTEGER NOT NULL DEFAULT 0, last_played TEXT)")
            conn.execute("PRAGMA user_version = 6")
    if version < 7:
        with conn:
            # v7: pistas que el usuario quitó de «Por revisar» (se conservan aunque se re-escanee)
            conn.execute(
                "CREATE TABLE IF NOT EXISTS review_dismissed ("
                " file_id INTEGER PRIMARY KEY REFERENCES files(id) ON DELETE CASCADE)")
            conn.execute("PRAGMA user_version = 7")
    if version < 8:
        with conn:
            # v8: cuándo se intentó la descarga automática de portada / información (no repetirla cada vez)
            conn.execute("ALTER TABLE albums ADD COLUMN cover_checked_at TEXT")
            conn.execute("ALTER TABLE artists ADD COLUMN info_checked_at TEXT")
            conn.execute("PRAGMA user_version = 8")
    if version < 9:
        with conn:
            # v9: registro de carpetas con música (las que encuentra «Buscar música») y rutas excluidas por el usuario
            # (el escáner las salta, así lo que se quita de la biblioteca no vuelve en el siguiente escaneo)
            conn.execute("CREATE TABLE IF NOT EXISTS library_folders (path TEXT PRIMARY KEY)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS excluded_paths ("
                " path TEXT PRIMARY KEY,"
                " kind TEXT NOT NULL CHECK (kind IN ('file', 'folder')))")
            _backfill_library_folders(conn)
            conn.execute("PRAGMA user_version = 9")
    if version < 10 or not _v10_complete(conn):
        # (la segunda condición repara una base que dice ser v10 pero a la que le faltan piezas: `_migrate_v10` es repetible)
        with conn:
            _migrate_v10(conn)


_V10_OBJECTS = frozenset({
    "deleted_playlists", "sync_devices", "idx_tracks_uuid", "idx_playlists_uuid", "trg_tracks_uuid", "trg_playlists_new",
    "trg_playlists_rename", "trg_playlist_tracks_add", "trg_playlist_tracks_del", "trg_playlists_gone"})


def _v10_complete(conn: sqlite3.Connection) -> bool:
    """¿Existen todas las tablas, índices, disparadores y columnas del esquema v10? (consulta barata)"""
    marks = ",".join("?" * len(_V10_OBJECTS))
    found = {r[0] for r in conn.execute(f"SELECT name FROM sqlite_master WHERE name IN ({marks})", tuple(_V10_OBJECTS))}
    if found != _V10_OBJECTS:
        return False
    wanted = (("files", {"content_hash", "hash_size", "hash_mtime_ns"}), ("tracks", {"uuid"}),
              ("playlists", {"uuid", "updated_at"}))
    return all(cols <= {r[1] for r in conn.execute(f"PRAGMA table_info({table})")} for table, cols in wanted)


# v10 (sincronización con el móvil): identidad estable de pistas y listas.
# `tracks.uuid` es la identidad entre dispositivos; `files.content_hash` (SHA-256, con caché por tamaño+fecha) detecta
# cambios de contenido. Las listas llevan `uuid` y `updated_at` (última modificación gana). Todo lo mantienen
# disparadores de SQLite, así que cualquier ruta de código (escáner, listas, importación) los respeta sin cambios.
_UUID_SQL = (
    "lower(hex(randomblob(4)) || '-' || hex(randomblob(2)) || '-4' || substr(hex(randomblob(2)), 2) || '-'"
    " || substr('89ab', abs(random()) % 4 + 1, 1) || substr(hex(randomblob(2)), 2) || '-' || hex(randomblob(6)))")
_NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"

SCHEMA_V10_TRIGGERS = (
    f"""CREATE TRIGGER IF NOT EXISTS trg_tracks_uuid AFTER INSERT ON tracks WHEN NEW.uuid IS NULL
    BEGIN UPDATE tracks SET uuid = {_UUID_SQL} WHERE id = NEW.id; END""",
    f"""CREATE TRIGGER IF NOT EXISTS trg_playlists_new AFTER INSERT ON playlists
    WHEN NEW.uuid IS NULL OR NEW.updated_at IS NULL
    BEGIN
        UPDATE playlists SET uuid = COALESCE(NEW.uuid, {_UUID_SQL}),
                             updated_at = COALESCE(NEW.updated_at, {_NOW_SQL})
        WHERE id = NEW.id;
    END""",
    f"""CREATE TRIGGER IF NOT EXISTS trg_playlists_rename AFTER UPDATE OF name ON playlists
    WHEN NEW.updated_at IS OLD.updated_at
    BEGIN UPDATE playlists SET updated_at = {_NOW_SQL} WHERE id = NEW.id; END""",
    f"""CREATE TRIGGER IF NOT EXISTS trg_playlist_tracks_add AFTER INSERT ON playlist_tracks
    BEGIN UPDATE playlists SET updated_at = {_NOW_SQL} WHERE id = NEW.playlist_id; END""",
    f"""CREATE TRIGGER IF NOT EXISTS trg_playlist_tracks_del AFTER DELETE ON playlist_tracks
    BEGIN UPDATE playlists SET updated_at = {_NOW_SQL} WHERE id = OLD.playlist_id; END""",
    f"""CREATE TRIGGER IF NOT EXISTS trg_playlists_gone AFTER DELETE ON playlists WHEN OLD.uuid IS NOT NULL
    BEGIN
        INSERT OR REPLACE INTO deleted_playlists (uuid, deleted_at) VALUES (OLD.uuid, {_NOW_SQL});
    END""",
)


def _add_column(conn: sqlite3.Connection, table: str, definition: str) -> None:
    """ALTER TABLE ... ADD COLUMN solo si falta (así la migración se puede repetir tras una interrupción)."""
    name = definition.split()[0]
    if name not in {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def _migrate_v10(conn: sqlite3.Connection) -> None:
    for column in ("content_hash TEXT", "hash_size INTEGER", "hash_mtime_ns INTEGER"):
        _add_column(conn, "files", column)
    _add_column(conn, "tracks", "uuid TEXT")
    _add_column(conn, "playlists", "uuid TEXT")
    _add_column(conn, "playlists", "updated_at TEXT")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS deleted_playlists ("
        " uuid TEXT PRIMARY KEY, deleted_at TEXT NOT NULL)")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sync_devices ("
        " device_id TEXT PRIMARY KEY, name TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,"
        " created_at TEXT NOT NULL, last_seen TEXT)")
    conn.execute(f"UPDATE tracks SET uuid = {_UUID_SQL} WHERE uuid IS NULL")
    conn.execute(f"UPDATE playlists SET uuid = {_UUID_SQL} WHERE uuid IS NULL")
    conn.execute(f"UPDATE playlists SET updated_at = {_NOW_SQL} WHERE updated_at IS NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tracks_uuid ON tracks(uuid)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_playlists_uuid ON playlists(uuid)")
    for statement in SCHEMA_V10_TRIGGERS:
        conn.execute(statement)
    conn.execute("PRAGMA user_version = 10")


def _backfill_library_folders(conn: sqlite3.Connection) -> None:
    """Bibliotecas anteriores a v9: registra las carpetas donde ya hay pistas."""
    import os

    dirs = {os.path.dirname(row[0]) for row in conn.execute("SELECT path FROM files")}
    conn.executemany("INSERT OR IGNORE INTO library_folders (path) VALUES (?)", [(d,) for d in sorted(dirs)])
