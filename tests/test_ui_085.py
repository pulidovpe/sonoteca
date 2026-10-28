"""0.8.5: cabecera de lista, pregunta al reproducir una canción suelta y letra en panel lateral."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest

from conftest import needs_ffmpeg

from musicapp.core import playlists as store
from musicapp.core.db import connect




def _seed(conn, artists):
    """Una pista por cada artista de `artists` (con repeticiones) y devuelve los ids de pista."""
    ids = []
    known = {}
    base = conn.execute("INSERT INTO artists (name, sort_name) VALUES ('Base', 'base')").lastrowid
    conn.execute("INSERT INTO albums (id, title, album_artist_id) VALUES (1, 'Al', ?)", (base,))
    for n, name in enumerate(artists, 1):
        if name not in known:
            known[name] = conn.execute("INSERT INTO artists (name, sort_name) VALUES (?, ?)", (name, name.lower())).lastrowid
        fid = conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?, 1, 1, 'mp3', 'audio')",
                           (f"/x/{n}.mp3",)).lastrowid
        ids.append(conn.execute("INSERT INTO tracks (file_id, album_id, artist_id, title, duration) VALUES (?, 1, ?, ?, 1)",
                                (fid, known[name], f"T{n}")).lastrowid)
    conn.commit()
    return ids


def test_describe_artists_orders_by_count_and_summarises(tmp_path):
    conn = connect(tmp_path / "d.db")
    pid = store.create(conn, "L")
    assert store.describe_artists(conn, pid) == ""
    ids = _seed(conn, ["A", "B", "B", "C", "D", "E"])
    store.add_tracks(conn, pid, ids[:1])
    assert store.describe_artists(conn, pid) == "Con A"
    store.add_tracks(conn, pid, ids[1:3])
    assert store.describe_artists(conn, pid) == "Con B y A"       # B tiene 2 canciones
    store.add_tracks(conn, pid, ids[3:4])
    assert store.describe_artists(conn, pid) == "Con B, A y C"
    store.add_tracks(conn, pid, ids[4:])
    assert store.describe_artists(conn, pid) == "Con B, A, C y 2 m\u00e1s"


@pytest.fixture
def db_file(tmp_path):
    pytest.importorskip("PySide6.QtQml")
    from conftest import make_mp3
    from musicapp.core.scanner import scan
    root = tmp_path / "music"
    for n in (1, 2, 3):
        make_mp3(root / f"A/{n}.mp3", title=f"Pista {n}", artist="Artista", album="Disco",
                 date="2000", track=f"{n}/3")
    db = tmp_path / "t.db"
    conn = connect(db)
    scan(conn, root)
    conn.close()
    return db


def _ids(env):
    album = env.controller.albums(0, 0, 0)[0]["id"]
    return album, [t["id"] for t in env.controller.tracks(album)]


@needs_ffmpeg
def test_playlist_header_shows_cover_name_and_description(qml_env):
    env = qml_env
    album, ids = _ids(env)
    pid = env.playlists.createWithTracks("Mi lista", ids)["id"]
    env.act("showSection('playlists')", 400)
    env.act(f"openPlaylist({pid})", 600)
    assert env.js("stack.currentItem.nameText.text") == "Mi lista"
    assert "Artista" in env.js("stack.currentItem.descriptionText.text")
    assert "3 canciones" in env.js("stack.currentItem.descriptionText.text")
    assert env.js("stack.currentItem.cover.width") == 190 and env.js("stack.currentItem.cover.height") == 190
    assert env.warnings == []


@needs_ffmpeg
def test_single_track_with_a_running_list_asks_to_replace_or_keep(qml_env):
    env = qml_env
    album, ids = _ids(env)
    env.act(f"openAlbum({album})", 600)
    env.act("stack.currentItem.playOneRequested(%d)" % ids[1], 300)   # sin lista: no hay diálogo
    env.player.playTrackIds(ids, 0)
    env.act("stack.currentItem.playOneRequested(%d)" % ids[2], 300)
    assert env.js("queueChoice.visible") is True
    env.act("queueChoice.keepList()", 300)
    assert env.player.queueTrackIds() == [ids[0], ids[2], ids[1], ids[2]]   # suena ya; la lista sigue después
    assert env.player.currentId == ids[2]
    env.act("queueChoice.ask(%d); queueChoice.replaceList()" % ids[1], 300)
    assert env.player.queueTrackIds() == [ids[1]]
    assert env.warnings == []


@needs_ffmpeg
def test_lyrics_opens_in_a_side_panel_while_playing(qml_env):
    env = qml_env
    album, ids = _ids(env)
    env.act("toggleLyrics()", 400)               # sin canción: página completa
    assert env.js("win.section") == "lyrics" and env.js("lyricsPanelShown") is False
    env.act("showSection('albums')", 400)
    env.player.playTrackIds(ids, 0)
    env.act("toggleLyrics()", 500)
    assert env.js("lyricsPanelShown") is True and env.js("win.section") == "albums"   # el centro no cambia
    assert env.js("lyricsPanel.width") > 0
    env.act("toggleLyrics()", 500)
    assert env.js("lyricsPanelShown") is False
    assert env.warnings == []
