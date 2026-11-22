"""Parte C-bis: detectar que unas pistas son TODAS las de un álbum (sin Qt)."""
from sonoteca.core import play_source
from sonoteca.core.db import connect


def _library(tmp_path):
    conn = connect(tmp_path / "t.db")
    conn.execute("INSERT INTO artists (id, name, sort_name) VALUES (1, 'A', 'A')")
    for album in (1, 2):
        conn.execute("INSERT INTO albums (id, title, album_artist_id) VALUES (?, ?, 1)", (album, f"Disco {album}"))
    for tid, album in ((1, 1), (2, 1), (3, 1), (4, 2), (5, 2)):
        conn.execute("INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES (?, ?, 1, 1, 'mp3', 'audio')",
                     (tid, f"/{tid}.mp3"))
        conn.execute("INSERT INTO tracks (id, file_id, album_id, artist_id, title) VALUES (?, ?, ?, 1, ?)",
                     (tid, tid, album, f"Pista {tid}"))
    conn.commit()
    return conn


def test_whole_album_needs_every_track_of_exactly_one_album(tmp_path):
    conn = _library(tmp_path)
    assert play_source.whole_album(conn, [1, 2, 3]) == 1
    assert play_source.whole_album(conn, [3, 1, 2]) == 1                  # el orden no importa
    assert play_source.whole_album(conn, [4, 5]) == 2


def test_whole_album_is_zero_for_partial_mixed_single_or_unknown_selections(tmp_path):
    conn = _library(tmp_path)
    for ids in ([], [1], [1, 2], [1, 4], [1, 2, 3, 4], [99, 100]):
        assert play_source.whole_album(conn, ids) == 0, ids
