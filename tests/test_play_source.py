"""Parte B: nombre del álbum o de la lista de donde sale lo que suena (sin Qt)."""
from sonoteca.core import play_source, playlists
from sonoteca.core.db import connect


def test_describe_names_the_album_and_the_playlist(tmp_path):
    conn = connect(tmp_path / "t.db")
    conn.execute("INSERT INTO artists (id, name, sort_name) VALUES (1, 'A', 'A')")
    conn.execute("INSERT INTO albums (id, title, album_artist_id) VALUES (3, 'Abbey Road', 1)")
    conn.commit()
    pid = playlists.create(conn, "  Mi   lista ")
    assert play_source.describe(conn, "album:3") == ("album", "Abbey Road")
    assert play_source.describe(conn, f"playlist:{pid}") == ("playlist", "Mi lista")


def test_describe_is_empty_when_there_is_no_origin_or_it_is_gone(tmp_path):
    conn = connect(tmp_path / "t.db")
    for source in ("", "album:", "album:x", "album:99", "playlist:99", "playlist:-1", "artist:1", "otra"):
        assert play_source.describe(conn, source) == ("", "")
