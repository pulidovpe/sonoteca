"""Copia de seguridad previa a migrar el esquema (regla de docs/MIGRACIONES.md): nunca se migra sin copia."""
from __future__ import annotations

import sqlite3

import pytest
from sync_support import add_track, downgrade_to_v9

from sonoteca.core import playlists
from sonoteca.core.db import backup_path, connect


def _v9_library(tmp_path):
    """Biblioteca con datos, en el estado de la 1.0.0 (v9). Devuelve (ruta, conexión abierta)."""
    path = tmp_path / "library.db"
    conn = connect(path)
    t = add_track(conn, tmp_path / "m", "a", artist="Ana")
    pid = playlists.create(conn, "Mi lista")
    playlists._rewrite(conn, pid, [t])
    downgrade_to_v9(conn)
    return path, conn


def _version(path):
    raw = sqlite3.connect(path)
    try:
        return raw.execute("PRAGMA user_version").fetchone()[0]
    finally:
        raw.close()


def test_migrating_from_v9_leaves_a_v9_copy_with_the_data(tmp_path):
    path, conn = _v9_library(tmp_path)
    conn.close()
    connect(path).close()
    bak = backup_path(path, 9)
    assert bak.name == "library.db.v9.bak" and bak.is_file()
    assert _version(path) == 10 and _version(bak) == 9
    raw = sqlite3.connect(bak)
    try:
        assert raw.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 1
        assert raw.execute("SELECT name FROM playlists").fetchone()[0] == "Mi lista"
        assert "uuid" not in {r[1] for r in raw.execute("PRAGMA table_info(tracks)")}   # estado anterior intacto
    finally:
        raw.close()


def test_copy_includes_changes_still_sitting_in_the_wal(tmp_path):
    path, conn = _v9_library(tmp_path)
    with conn:   # confirmado pero sin volcar al archivo principal (otra conexión lo mantiene abierto)
        conn.execute("INSERT INTO artists (name, sort_name) VALUES ('Reciente', 'Reciente')")
    connect(path).close()
    raw = sqlite3.connect(backup_path(path, 9))
    try:
        assert raw.execute("SELECT COUNT(*) FROM artists WHERE name = 'Reciente'").fetchone()[0] == 1
    finally:
        raw.close()
        conn.close()


def test_an_existing_copy_is_never_overwritten(tmp_path):
    path, conn = _v9_library(tmp_path)
    conn.close()
    bak = backup_path(path, 9)
    bak.write_bytes(b"copia antigua")
    connect(path).close()
    assert bak.read_bytes() == b"copia antigua"


def test_fresh_in_memory_and_up_to_date_databases_make_no_copy(tmp_path):
    connect(tmp_path / "nueva.db").close()
    connect(tmp_path / "nueva.db").close()
    connect(":memory:").close()
    assert [p.name for p in tmp_path.iterdir() if p.name.endswith(".bak")] == []


def test_repairing_an_incomplete_v10_also_keeps_a_copy(tmp_path):
    path = tmp_path / "library.db"
    conn = connect(path)
    conn.execute("DROP TABLE sync_devices")
    conn.commit()
    conn.close()
    connect(path).close()
    assert backup_path(path, 10).is_file()


def test_if_the_copy_cannot_be_made_the_database_is_not_touched(tmp_path):
    path, conn = _v9_library(tmp_path)
    conn.close()
    (tmp_path / "library.db.v9.bak.tmp").mkdir()   # estorba: no se puede crear la copia parcial
    with pytest.raises(RuntimeError, match="copia de seguridad"):
        connect(path)
    assert _version(path) == 9
