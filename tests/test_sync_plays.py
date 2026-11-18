"""Estadísticas de reproducción del móvil: eventos con id único, idempotentes, sumados al contador del escritorio."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sync_support import add_track

from sonoteca.core import content_hash, stats
from sonoteca.core.db import connect
from sonoteca.sync import plays
from sonoteca.sync.manifest import build_manifest

GHOST = "99999999-9999-4999-8999-999999999999"


def _library(tmp_path):
    conn = connect(tmp_path / "lib.db")
    track = add_track(conn, tmp_path / "m", "uno")
    uuid = conn.execute("SELECT uuid FROM tracks WHERE id = ?", (track,)).fetchone()[0]
    return conn, track, uuid


def _event(event_id, uuid, played_at="2026-11-18T10:00:00.000Z"):
    return {"id": event_id, "track_uuid": uuid, "played_at": played_at}


def _plays_of(conn, track):
    return stats.play_counts(conn, [track])[track]


def test_new_events_are_added_to_the_play_counter(tmp_path):
    conn, track, uuid = _library(tmp_path)
    result = plays.apply_plays(conn, "poco-0001", {"events": [_event("evento-0001", uuid), _event("evento-0002", uuid)]})
    assert result == {"accepted": 2, "duplicates": 0, "unknown": [], "invalid": []}
    assert _plays_of(conn, track) == 2


def test_mobile_plays_are_added_to_the_desktop_ones(tmp_path):
    conn, track, uuid = _library(tmp_path)
    stats.record_play(conn, track)
    stats.record_play(conn, track)
    plays.apply_plays(conn, "poco-0001", {"events": [_event("evento-0001", uuid)]})
    assert _plays_of(conn, track) == 3


def test_resending_a_batch_does_not_count_twice(tmp_path):
    conn, track, uuid = _library(tmp_path)
    batch = {"events": [_event("evento-0001", uuid), _event("evento-0002", uuid)]}
    plays.apply_plays(conn, "poco-0001", batch)
    again = plays.apply_plays(conn, "poco-0001", batch)
    assert again["accepted"] == 0 and again["duplicates"] == 2
    assert _plays_of(conn, track) == 2
    assert conn.execute("SELECT COUNT(*) FROM sync_play_events").fetchone()[0] == 2


def test_a_batch_that_overlaps_a_previous_one_only_adds_the_new_events(tmp_path):
    conn, track, uuid = _library(tmp_path)
    plays.apply_plays(conn, "poco-0001", {"events": [_event("evento-0001", uuid)]})
    result = plays.apply_plays(conn, "poco-0001", {"events": [_event("evento-0001", uuid), _event("evento-0002", uuid)]})
    assert result["accepted"] == 1 and result["duplicates"] == 1
    assert _plays_of(conn, track) == 2


def test_unknown_tracks_and_invalid_events_are_reported_and_not_counted(tmp_path):
    conn, track, uuid = _library(tmp_path)
    events = [
        _event("evento-0001", GHOST),                    # la pista ya no existe en el escritorio
        _event("evento-0002", uuid, "no es una fecha"),  # fecha inválida
        _event("corto", uuid),                           # id demasiado corto
        {"id": "evento-0005", "track_uuid": "no-uuid", "played_at": "2026-11-18T10:00:00.000Z"},
        "basura",
        _event("evento-0006", uuid),                     # este sí
    ]
    result = plays.apply_plays(conn, "poco-0001", {"events": events})
    assert result["accepted"] == 1
    assert result["unknown"] == ["evento-0001"]
    assert set(result["invalid"]) == {"evento-0002", "corto", "evento-0005", ""}
    assert _plays_of(conn, track) == 1


def test_malformed_requests_are_rejected(tmp_path):
    conn, _, uuid = _library(tmp_path)
    with pytest.raises(plays.PlaysError, match="events"):
        plays.apply_plays(conn, "poco-0001", {})
    with pytest.raises(plays.PlaysError, match="events"):
        plays.apply_plays(conn, "poco-0001", {"events": "x"})
    too_many = [_event(f"evento-{i:06d}", uuid) for i in range(plays.MAX_EVENTS + 1)]
    with pytest.raises(plays.PlaysError, match="demasiados"):
        plays.apply_plays(conn, "poco-0001", {"events": too_many})
    assert conn.execute("SELECT COUNT(*) FROM sync_play_events").fetchone()[0] == 0


def test_last_played_keeps_the_most_recent_moment(tmp_path):
    conn, track, uuid = _library(tmp_path)
    newer = datetime(2020, 1, 1, 10, 0, tzinfo=timezone.utc)
    older = datetime(2020, 1, 1, 9, 0, tzinfo=timezone.utc)
    plays.apply_plays(conn, "poco-0001", {"events": [_event("evento-0001", uuid, "2020-01-01T10:00:00.000Z")]})
    plays.apply_plays(conn, "poco-0001", {"events": [_event("evento-0002", uuid, "2020-01-01T09:00:00.000Z")]})
    last = conn.execute("SELECT last_played FROM play_stats WHERE track_id = ?", (track,)).fetchone()[0]
    assert last == plays._local_naive_iso(newer) and last != plays._local_naive_iso(older)
    assert _plays_of(conn, track) == 2


def test_a_clock_in_the_future_is_clamped(tmp_path):
    conn, track, uuid = _library(tmp_path)
    plays.apply_plays(conn, "poco-0001", {"events": [_event("evento-0001", uuid, "2099-01-01T00:00:00.000Z")]})
    last = conn.execute("SELECT last_played FROM play_stats WHERE track_id = ?", (track,)).fetchone()[0]
    assert last < "2030"   # no queda en el futuro lejano: se recorta a «mañana» como mucho


def test_the_manifest_carries_the_total_plays_per_track(tmp_path):
    conn, track, uuid = _library(tmp_path)
    content_hash.ensure_hash(conn, conn.execute("SELECT file_id FROM tracks WHERE id = ?", (track,)).fetchone()[0])
    assert build_manifest(conn)["tracks"][0]["plays"] == 0
    stats.record_play(conn, track)
    plays.apply_plays(conn, "poco-0001", {"events": [_event("evento-0001", uuid)]})
    assert build_manifest(conn)["tracks"][0]["plays"] == 2


def test_an_existing_v10_database_without_the_events_table_is_repaired_and_backed_up(tmp_path):
    path = tmp_path / "lib.db"
    conn = connect(path)
    add_track(conn, tmp_path / "m", "uno")
    conn.execute("DROP TABLE sync_play_events")
    conn.commit()
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 10   # dice ser v10 pero le falta la tabla nueva
    conn.close()
    conn = connect(path)   # se repara sola
    assert conn.execute("SELECT COUNT(*) FROM sync_play_events").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 1
    assert (tmp_path / "lib.db.v10.bak").exists()   # copia previa a tocar el esquema
