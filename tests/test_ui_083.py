"""0.8.3: historial adelante/atrás, Inicio, artista con canciones destacadas y miniaturas en listas."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest

pytest.importorskip("PySide6.QtQml")

from conftest import needs_ffmpeg
from test_ui_edit import album_ids

from sonoteca.core import stats

pytestmark = needs_ffmpeg


def test_history_back_forward_and_discarding_forward_branch(qml_env):
    env = qml_env
    js, act = env.js, env.act
    album, _ = album_ids(env.controller)
    assert js("win.canBack") is False and js("win.canForward") is False
    act("showSection('artists')", 300)
    act(f"openAlbum({album})", 300)
    assert js("win.navIndex") == 2 and js("stack.currentItem.albumId") == album
    act("win.back()", 300)
    assert js("win.section") == "artists" and js("win.canForward") is True
    act("win.forward()", 300)
    assert js("stack.currentItem.albumId") == album and js("win.canForward") is False
    # ir atrás y navegar a otro sitio descarta lo que había "adelante"
    act("win.back()", 200)
    act("showSection('review')", 300)
    assert js("win.canForward") is False and js("win.navHistory.length") == 3
    # abrir la misma ubicación dos veces seguidas no duplica la entrada
    act("showSection('review')", 200)
    assert js("win.navHistory.length") == 3
    assert env.warnings == []


def test_typing_in_search_does_not_flood_history_and_back_leaves_search(qml_env):
    env = qml_env
    act, js = env.act, env.js
    act("win.runSearch('Pi')", 300)
    n = js("win.navHistory.length")
    act("win.runSearch('Pis')", 300)
    act("win.runSearch('Pist')", 300)
    assert js("win.navHistory.length") == n and js("searching") is True
    act("win.back()", 300)
    assert js("searching") is False
    assert env.warnings == []


def test_back_skips_deleted_playlist(qml_env):
    env = qml_env
    act, js = env.act, env.js
    pid = env.playlists.create("Efimera")["id"]
    act("showSection('playlists')", 200)
    act(f"openPlaylist({pid})", 300)
    act("showSection('review')", 200)
    env.playlists.remove(pid)
    act("win.back()", 300)           # la lista ya no existe: salta a «Listas»
    assert js("win.section") == "playlists" and js("win.navIndex") == 1


def test_home_page_ranks_listened_content(qml_env):
    env = qml_env
    act, js = env.act, env.js
    album, ids = album_ids(env.controller)
    pid = env.playlists.createWithTracks("Mi mezcla", ids[:2])["id"]
    act("showSection('home')", 400)
    assert js("stack.currentItem.homeData.albums.length") == 0 and js("stack.currentItem.homeData.lists.length") == 1
    for _ in range(3):
        stats.record_play(env.controller._conn, ids[0])
    act("Theme.dataRevision++", 400)
    home = "stack.currentItem.homeData"
    assert js(f"{home}.albums[0].id") == album and js(f"{home}.albums[0].plays") == 3
    assert js(f"{home}.tracks[0].id") == ids[0] and js(f"{home}.lists[0].plays") == 3
    assert js(f"{home}.artists[0].plays") == 3
    assert env.warnings == []


def test_artist_page_top_tracks_and_queue_thumbnails(qml_env):
    env = qml_env
    act, js = env.act, env.js
    album, ids = album_ids(env.controller)
    artist = env.controller.artists()[0]
    stats.record_play(env.controller._conn, ids[1])
    act(f"openArtist({artist['id']}, 'X')", 400)
    top = js("stack.currentItem.topTracks.map(function (t) { return t.id })")
    assert top[0] == ids[1]                    # la más escuchada va primero
    assert js("stack.currentItem.showTop") is True    # la lista destacada se muestra siempre
    # las listas muestran la portada de cada canción
    env.player.playAlbum(album, 0)
    assert env.player.queueItems()[0]["albumId"] == album
    assert env.playlists.tracks(env.playlists.createWithTracks("T", ids)["id"])[0]["albumId"] == album
