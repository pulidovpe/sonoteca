"""Lista temporal (cola) desde la interfaz: menú de la canción, vista «Cola» y botones del álbum."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import pytest

pytest.importorskip("PySide6.QtQml")

from conftest import make_mp3, needs_ffmpeg

from musicapp.core.db import connect
from musicapp.core.scanner import scan

pytestmark = needs_ffmpeg


@pytest.fixture
def db_file(tmp_path):
    root = tmp_path / "music"
    for n in (1, 2, 3):
        make_mp3(root / f"A/{n}.mp3", title=f"Pista {n}", artist="Artista", album="Disco",
                 date="2000", track=f"{n}/3")
    db = tmp_path / "t.db"
    conn = connect(db)
    scan(conn, root)
    conn.close()
    return db


def ids(env):
    album = env.controller.albums(0, 0, 0)[0]["id"]
    return album, [t["id"] for t in env.controller.tracks(album)]


def page_titles(env):
    value = env.js("stack.currentItem.items.map(function (x) { return x.title })")
    return list(value.toVariant())  # PySide devuelve los arreglos de JS como QJSValue


def test_track_menu_adds_to_a_new_temporary_list_and_the_queue_page_shows_it(qml_env):
    env = qml_env
    js, act = env.js, env.act
    _, track_ids = ids(env)
    act("showSection('queue')", 400)
    assert js("stack.currentItem.items.length") == 0
    act(f"trackMenu.ids = [{track_ids[2]}]; trackMenu.addToList()", 300)
    assert "Lista temporal creada con 1 canción" in js("toastText.text")
    assert page_titles(env) == ["Pista 3"]
    act(f"trackMenu.ids = [{track_ids[0]}, {track_ids[1]}]; trackMenu.addToList()", 300)
    assert page_titles(env) == ["Pista 3", "Pista 1", "Pista 2"]
    assert js("toastText.text") == "2 canciones agregadas a la lista actual"
    assert js("player.queueLength") == 3 and not js("player.hasTrack")  # nada suena solo


def test_queue_page_reorders_removes_and_plays_from_a_row(qml_env):
    env = qml_env
    js, act = env.js, env.act
    _, track_ids = ids(env)
    env.player.addToQueue(track_ids)  # Pista 1, 2, 3
    act("showSection('queue')", 400)
    assert page_titles(env) == ["Pista 1", "Pista 2", "Pista 3"]
    act("stack.currentItem.moveDown(0)", 250)
    assert page_titles(env) == ["Pista 2", "Pista 1", "Pista 3"]
    act("stack.currentItem.moveUp(2)", 250)
    assert page_titles(env) == ["Pista 2", "Pista 3", "Pista 1"]
    act("stack.currentItem.removeAt(1)", 250)
    assert page_titles(env) == ["Pista 2", "Pista 1"]
    act("player.playQueueAt(1)", 300)
    assert js("player.currentTrack.title") == "Pista 1" and js("player.playing")
    assert js("stack.currentItem.items[1].current") is True  # la fila marca lo que suena
    act("stack.currentItem.moveUp(0)", 250)  # extremos: no hace nada
    act("stack.currentItem.moveDown(1)", 250)
    assert page_titles(env) == ["Pista 2", "Pista 1"]


def test_play_next_new_temporary_list_and_clear(qml_env):
    env = qml_env
    js, act = env.js, env.act
    album, track_ids = ids(env)
    env.player.playAlbum(album, 0)  # suena Pista 1; la lista es el álbum
    act("showSection('queue')", 400)
    act(f"trackMenu.ids = [{track_ids[2]}]; trackMenu.playLater()", 300)
    assert page_titles(env) == ["Pista 1", "Pista 3", "Pista 2", "Pista 3"]
    assert js("toastText.text") == "1 canción sonará a continuación"
    act("actNewList.trigger()", 300)  # lista nueva: se queda solo la que suena
    assert page_titles(env) == ["Pista 1"] and js("player.hasTrack")
    act("actClearList.trigger()", 300)
    assert page_titles(env) == [] and not js("player.hasTrack")
    assert js("actClearList.enabled") is False
    assert env.warnings == []


def test_album_page_can_add_the_whole_album_to_the_list(qml_env):
    env = qml_env
    js, act = env.js, env.act
    album, _ = ids(env)
    act(f"openAlbum({album})", 600)
    act("stack.currentItem.addAllToQueue()", 300)
    assert js("player.queueLength") == 3
    assert js("toastText.text").startswith("Lista temporal creada con 3 canciones")
    act("showSection('queue')", 400)
    assert page_titles(env) == ["Pista 1", "Pista 2", "Pista 3"]
    assert env.warnings == []


def test_menu_entries_depend_on_whether_there_is_a_list(qml_env):
    env = qml_env
    js = env.js
    _, track_ids = ids(env)
    assert js("trackMenu.itemAt(2).text") == "Agregar a una lista temporal nueva"
    assert js("trackMenu.itemAt(1).enabled") is False  # sin lista no hay "a continuación"
    env.player.addToQueue(track_ids[:1])
    assert js("trackMenu.itemAt(2).text") == "Agregar a la lista actual"
    assert js("trackMenu.itemAt(1).enabled") is True
    env.act(f"trackMenu.ids = [{track_ids[1]}]; trackMenu.playNow()", 300)
    assert js("player.currentTrack.title") == "Pista 2"  # "Reproducir ahora" reemplaza la lista
    assert env.warnings == []
