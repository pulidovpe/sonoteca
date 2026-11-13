"""Esquema v10: uuid de pistas y listas, disparadores, tombstones y huella con caché."""
from __future__ import annotations

import os
import re
import sqlite3

from sync_support import add_track

from sonoteca.core import content_hash, playlists
from sonoteca.core.db import SCHEMA_VERSION, connect, migrate

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def _db(tmp_path):
    return connect(tmp_path / "lib.db")


def test_schema_version_is_10(tmp_path):
    conn = _db(tmp_path)
    assert SCHEMA_VERSION == 10
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 10


def test_new_tracks_and_playlists_get_uuid(tmp_path):
    conn = _db(tmp_path)
    a = add_track(conn, tmp_path / "m", "a")
    b = add_track(conn, tmp_path / "m", "b")
    uuids = {conn.execute("SELECT uuid FROM tracks WHERE id = ?", (i,)).fetchone()[0] for i in (a, b)}
    assert len(uuids) == 2 and all(UUID.match(u) for u in uuids)
    pid = playlists.create(conn, "Mi lista")
    row = conn.execute("SELECT uuid, updated_at FROM playlists WHERE id = ?", (pid,)).fetchone()
    assert UUID.match(row["uuid"]) and row["updated_at"].endswith("Z")


def test_uuid_survives_updates_of_the_track_row(tmp_path):
    conn = _db(tmp_path)
    t = add_track(conn, tmp_path / "m", "a")
    before = conn.execute("SELECT uuid FROM tracks WHERE id = ?", (t,)).fetchone()[0]
    with conn:
        conn.execute("UPDATE tracks SET title = 'otro' WHERE id = ?", (t,))
    assert conn.execute("SELECT uuid FROM tracks WHERE id = ?", (t,)).fetchone()[0] == before


def test_playlist_edits_touch_updated_at_and_delete_leaves_tombstone(tmp_path):
    conn = _db(tmp_path)
    t = add_track(conn, tmp_path / "m", "a")
    pid = playlists.create(conn, "L")
    with conn:
        conn.execute("UPDATE playlists SET updated_at = '2000-01-01T00:00:00.000Z' WHERE id = ?", (pid,))
    playlists._rewrite(conn, pid, [t])
    assert conn.execute("SELECT updated_at FROM playlists WHERE id = ?", (pid,)).fetchone()[0] > "2020"
    with conn:
        conn.execute("UPDATE playlists SET updated_at = '2000-01-01T00:00:00.000Z' WHERE id = ?", (pid,))
    playlists.rename(conn, pid, "Nueva")
    assert conn.execute("SELECT updated_at FROM playlists WHERE id = ?", (pid,)).fetchone()[0] > "2020"
    uuid = conn.execute("SELECT uuid FROM playlists WHERE id = ?", (pid,)).fetchone()[0]
    playlists.delete(conn, pid)
    assert conn.execute("SELECT uuid FROM deleted_playlists").fetchone()[0] == uuid


def _downgrade_to_v9(conn):
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


def test_upgrade_from_v9_backfills_and_keeps_data(tmp_path):
    path = tmp_path / "old.db"
    conn = connect(path)
    t1 = add_track(conn, tmp_path / "m", "a")
    t2 = add_track(conn, tmp_path / "m", "b")
    pid = playlists.create(conn, "Vieja")
    playlists._rewrite(conn, pid, [t2, t1])
    _downgrade_to_v9(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 9
    conn.close()

    conn = connect(path)   # migra
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 10
    assert conn.execute("SELECT COUNT(*) FROM tracks WHERE uuid IS NULL").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 2
    assert playlists.track_ids(conn, pid) == [t2, t1]
    pl = conn.execute("SELECT uuid, updated_at FROM playlists WHERE id = ?", (pid,)).fetchone()
    assert UUID.match(pl["uuid"]) and pl["updated_at"]
    migrate(conn)   # repetir no rompe nada


def test_migration_is_resumable_after_partial_run(tmp_path):
    path = tmp_path / "partial.db"
    conn = connect(path)
    add_track(conn, tmp_path / "m", "a")
    _downgrade_to_v9(conn)
    conn.execute("ALTER TABLE files ADD COLUMN content_hash TEXT")   # como si se hubiera interrumpido a medias
    conn.commit()
    conn.close()
    conn = connect(path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 10


def test_hash_cache_and_invalidation(tmp_path):
    conn = _db(tmp_path)
    t = add_track(conn, tmp_path / "m", "a", content=b"hola mundo")
    fid = conn.execute("SELECT file_id FROM tracks WHERE id = ?", (t,)).fetchone()[0]
    path = conn.execute("SELECT path FROM files WHERE id = ?", (fid,)).fetchone()[0]
    assert content_hash.stale_file_ids(conn) == [fid]
    h1 = content_hash.ensure_hash(conn, fid)
    assert h1 == content_hash.sha256_file(path) and len(h1) == 64
    assert content_hash.stale_file_ids(conn) == []

    # sin cambios: no relee (si se corrompiera la caché sin tocar el archivo, devolvería la guardada)
    with conn:
        conn.execute("UPDATE files SET content_hash = 'cache' WHERE id = ?", (fid,))
    assert content_hash.ensure_hash(conn, fid) == "cache"

    # el archivo cambia (otro tamaño): la huella se recalcula
    with open(path, "wb") as handle:
        handle.write(b"contenido distinto y mas largo")
    os.utime(path, ns=(1, 1))
    h2 = content_hash.ensure_hash(conn, fid)
    assert h2 == content_hash.sha256_file(path) and h2 != h1


def test_hash_missing_file_returns_none_and_video_is_ignored(tmp_path):
    conn = _db(tmp_path)
    gone = add_track(conn, tmp_path / "m", "gone")
    vid = add_track(conn, tmp_path / "m", "clip", kind="video", ext=".mp4")
    fid = conn.execute("SELECT file_id FROM tracks WHERE id = ?", (gone,)).fetchone()[0]
    vid_file = conn.execute("SELECT file_id FROM tracks WHERE id = ?", (vid,)).fetchone()[0]
    os.remove(conn.execute("SELECT path FROM files WHERE id = ?", (fid,)).fetchone()[0])
    assert content_hash.ensure_hash(conn, fid) is None
    assert vid_file not in content_hash.stale_file_ids(conn)
    assert content_hash.hash_missing(conn) == 0


def test_db_marked_v10_but_missing_pieces_is_repaired(tmp_path):
    path = tmp_path / "broken.db"
    conn = connect(path)
    t = add_track(conn, tmp_path / "m", "a")
    conn.execute("DROP TABLE sync_devices")
    conn.execute("DROP TRIGGER trg_playlists_gone")
    conn.execute("DROP INDEX idx_tracks_uuid")
    conn.commit()
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 10   # dice ser v10, pero está incompleta
    conn.close()
    conn = connect(path)   # se repara sola
    assert conn.execute("SELECT COUNT(*) FROM sync_devices").fetchone()[0] == 0
    assert conn.execute("SELECT uuid FROM tracks WHERE id = ?", (t,)).fetchone()[0]
    pid = playlists.create(conn, "L")
    playlists.delete(conn, pid)
    assert conn.execute("SELECT COUNT(*) FROM deleted_playlists").fetchone()[0] == 1
