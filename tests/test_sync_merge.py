"""Fusión de listas que llegan del móvil: última modificación gana, tombstones, nombres repetidos."""
from __future__ import annotations

import pytest
from sync_support import add_track

from sonoteca.core import playlists
from sonoteca.core.db import connect
from sonoteca.sync import merge

P1 = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def env(tmp_path):
    conn = connect(tmp_path / "lib.db")
    ids = [add_track(conn, tmp_path / "m", n, track_no=i) for i, n in enumerate("abc", 1)]
    uuids = [conn.execute("SELECT uuid FROM tracks WHERE id = ?", (i,)).fetchone()[0] for i in ids]
    return conn, ids, uuids


def _names(conn):
    return [r["name"] for r in playlists.list_playlists(conn)]


def test_create_from_phone_keeps_order_and_timestamp(env):
    conn, ids, u = env
    r = merge.apply_playlist(conn, P1, {"name": "Móvil", "updated_at": "2026-11-12T10:00:00.000Z",
                                        "tracks": [u[2], u[0]]})
    assert r["applied"] and r["missing"] == []
    pid = conn.execute("SELECT id FROM playlists WHERE uuid = ?", (P1,)).fetchone()[0]
    assert playlists.track_ids(conn, pid) == [ids[2], ids[0]]
    assert conn.execute("SELECT updated_at FROM playlists WHERE uuid = ?", (P1,)).fetchone()[0] \
        == "2026-11-12T10:00:00.000Z"


def test_last_writer_wins(env):
    conn, ids, u = env
    merge.apply_playlist(conn, P1, {"name": "L", "updated_at": "2026-11-12T10:00:00.000Z", "tracks": [u[0]]})
    older = merge.apply_playlist(conn, P1, {"name": "Vieja", "updated_at": "2026-11-12T09:00:00.000Z",
                                            "tracks": [u[1]]})
    assert older["applied"] is False and older["name"] == "L"
    newer = merge.apply_playlist(conn, P1, {"name": "Nueva", "updated_at": "2026-11-12T11:00:00.000Z",
                                            "tracks": [u[1], u[2]]})
    assert newer["applied"] and _names(conn) == ["Nueva"]
    pid = conn.execute("SELECT id FROM playlists WHERE uuid = ?", (P1,)).fetchone()[0]
    assert playlists.track_ids(conn, pid) == [ids[1], ids[2]]


def test_unknown_tracks_are_reported_not_fatal(env):
    conn, ids, u = env
    ghost = "22222222-2222-4222-8222-222222222222"
    r = merge.apply_playlist(conn, P1, {"name": "L", "updated_at": "2026-11-12T10:00:00.000Z",
                                        "tracks": [u[0], ghost]})
    assert r["missing"] == [ghost]


def test_duplicate_name_gets_suffix_not_error(env):
    conn, ids, u = env
    playlists.create(conn, "Rock")
    r = merge.apply_playlist(conn, P1, {"name": "rock", "updated_at": "2026-11-12T10:00:00.000Z", "tracks": []})
    assert r["name"] == "rock (móvil)"


def test_deleted_on_desktop_blocks_older_version_but_allows_newer(env):
    conn, ids, u = env
    merge.apply_playlist(conn, P1, {"name": "L", "updated_at": "2020-01-01T00:00:00.000Z", "tracks": []})
    pid = conn.execute("SELECT id FROM playlists WHERE uuid = ?", (P1,)).fetchone()[0]
    playlists.delete(conn, pid)
    with pytest.raises(merge.Conflict):
        merge.apply_playlist(conn, P1, {"name": "L", "updated_at": "2020-06-01T00:00:00.000Z", "tracks": []})
    r = merge.apply_playlist(conn, P1, {"name": "L", "updated_at": "2099-01-01T00:00:00.000Z", "tracks": []})
    assert r["applied"]   # editada en el móvil DESPUÉS del borrado: revive (y 2099 se recorta a «mañana»)
    assert conn.execute("SELECT COUNT(*) FROM deleted_playlists WHERE uuid = ?", (P1,)).fetchone()[0] == 0


def test_far_future_timestamp_is_clamped(env):
    conn, ids, u = env
    r = merge.apply_playlist(conn, P1, {"name": "L", "updated_at": "2099-01-01T00:00:00.000Z", "tracks": []})
    assert r["updated_at"] < "2099"


def test_delete_from_phone(env):
    conn, ids, u = env
    merge.apply_playlist(conn, P1, {"name": "L", "updated_at": "2026-11-12T10:00:00.000Z", "tracks": []})
    with pytest.raises(merge.Conflict):   # se modificó en el escritorio después del borrado en el móvil
        merge.delete_playlist(conn, P1, "2026-11-12T09:00:00.000Z")
    assert merge.delete_playlist(conn, P1, "2026-11-12T12:00:00.000Z")["deleted"] is True
    assert merge.delete_playlist(conn, P1, "2026-11-12T12:00:00.000Z")["already_gone"] is True


@pytest.mark.parametrize("payload", [
    {"name": "", "updated_at": "2026-11-12T10:00:00.000Z", "tracks": []},
    {"name": "L", "updated_at": "ayer", "tracks": []},
    {"name": "L", "updated_at": "2026-11-12T10:00:00.000Z", "tracks": "x"},
    {"name": "L", "updated_at": "2026-11-12T10:00:00.000Z", "tracks": ["no-es-uuid"]},
])
def test_invalid_payloads_rejected(env, payload):
    with pytest.raises(merge.MergeError):
        merge.apply_playlist(env[0], P1, payload)


def test_invalid_uuid_rejected(env):
    with pytest.raises(merge.MergeError):
        merge.apply_playlist(env[0], "x", {"name": "L", "updated_at": "2026-11-12T10:00:00.000Z", "tracks": []})
