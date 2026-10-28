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


# ---- 0.8.6 ----
def test_manual_lyrics_roundtrip_and_sync_detection(tmp_path):
    from musicapp.core import lyrics as lyr
    conn = connect(tmp_path / "l.db")
    ids = _seed(conn, ["A"])
    tid = ids[0]
    lyr.save_manual(conn, tid, "Linea uno\nLinea dos")
    doc = lyr.lyrics_doc(conn, tid)
    assert doc["found"] and not doc["synced"] and doc["source"] == "Manual"
    assert [x["text"] for x in doc["lines"]] == ["Linea uno", "Linea dos"]
    lyr.save_manual(conn, tid, "[00:01.00]Uno\n[00:03.50]Dos")
    doc = lyr.lyrics_doc(conn, tid)
    assert doc["synced"] and [x["t"] for x in doc["lines"]] == [1000, 3500]
    assert lyr.raw_text(conn, tid).startswith("[00:01.00]")      # se edita el LRC tal cual
    assert not lyr.should_retry(lyr.get_stored(conn, tid))        # la manual nunca se vuelve a buscar sola
    lyr.save_manual(conn, tid, "   \n")                           # vacío = borrar
    assert lyr.lyrics_doc(conn, tid)["stored"] is False


def test_audio_device_classification():
    from musicapp.player.devices import classify_audio_device as c
    assert c("AirPods de Pablo") == "headphones" and c("Audífonos Bluetooth") == "headphones"
    assert c("LG HDMI") == "display" and c("MacBook Pro Speakers") == "speaker" and c("") == "speaker"


@needs_ffmpeg
def test_album_has_go_to_artist_button(qml_env):
    env = qml_env
    album, _ = _ids(env)
    info = env.controller.album(album)
    env.act(f"openAlbum({album})", 600)
    env.act("stack.currentItem.artistRequested(%d, 'Artista')" % info["artist_id"], 600)
    assert env.js("stack.currentItem.artistId") == info["artist_id"]
    assert env.warnings == []


@needs_ffmpeg
def test_review_page_dismiss_and_restore(qml_env):
    env = qml_env
    env.act("showSection('review')", 500)
    before = env.js("stack.currentItem.items.length")
    env.act("dismissReview(%d); confirmDialog.confirm()" % before, 400)
    assert env.js("stack.currentItem.items.length") == 0
    env.act("restoreReview()", 400)
    assert env.js("stack.currentItem.items.length") == before
    assert env.warnings == []


@needs_ffmpeg
def test_lyrics_page_has_manual_button_and_audio_button_tooltip(qml_env):
    env = qml_env
    album, ids = _ids(env)
    env.player.playTrackIds(ids, 0)
    env.act("showSection('albums')", 300)
    env.act("toggleLyrics()", 500)
    assert env.js("lyricsPanelShown") is True
    assert env.js("playerBar.audioButton.toolTip").startswith("Salida de audio")
    assert env.warnings == []


@needs_ffmpeg
def test_player_bar_links_to_artist_and_album_from_any_page(qml_env):
    env = qml_env
    album, ids = _ids(env)
    env.player.playTrackIds(ids, 0)
    env.act("showSection('home')", 400)
    assert env.js("playerBar.artistLink.linked") is True and env.js("playerBar.albumLink.linked") is True
    env.act("playerBar.albumRequested(player.currentTrack.albumId)", 600)
    assert env.js("stack.currentItem.albumId") == album
    env.act("playerBar.artistRequested(player.currentTrack.artistId, 'Artista')", 600)
    assert env.js("stack.currentItem.artistId") == env.player.currentTrack["artistId"]
    assert env.warnings == []


def test_set_artist_image_only_changes_the_photo(tmp_path, monkeypatch):
    pytest.importorskip("PySide6.QtCore")
    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("MUSICAPP_CACHE_DIR", str(tmp_path / "cache"))
    from musicapp.ui.online_controller import OnlineController
    db = tmp_path / "i.db"
    conn = connect(db)
    _seed(conn, ["Solo foto"])
    aid = conn.execute("SELECT id FROM artists WHERE name = 'Solo foto'").fetchone()["id"]
    conn.close()
    ctrl = OnlineController(db)
    png = tmp_path / "f.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
    out = ctrl.setArtistImage(aid, str(png))
    assert out["ok"] and out["info"]["imagePath"] and out["info"]["bio"] == ""   # sin descripción: solo foto
    bad = tmp_path / "x.txt"
    bad.write_bytes(b"no es imagen")
    assert ctrl.setArtistImage(aid, str(bad))["ok"] is False
