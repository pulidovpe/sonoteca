"""Listas personalizadas desde la interfaz: crear, agregar, ordenar, reproducir, guardar la cola,
y edición de tags desde la cola y las listas."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import time

import pytest

pytest.importorskip("PySide6.QtQml")

from conftest import make_cover, make_mp3, needs_ffmpeg

from sonoteca.core.db import connect
from sonoteca.core.scanner import scan

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


def track_ids(env):
    album = env.controller.albums(0, 0, 0)[0]["id"]
    return [t["id"] for t in env.controller.tracks(album)]


def titles(value):
    return list(value.toVariant())


def create_via_prompt(env, name):
    env.act("newPlaylist()", 250)
    env.act(f"namePrompt.fieldItem.text = '{name}'; namePrompt.submit()", 250)


def poll(env, cond_js, timeout=12.0):
    end = time.time() + timeout
    while time.time() < end:
        if env.js(cond_js):
            return True
        env.wait(200)
    return False


def test_create_a_playlist_with_validation(qml_env):
    env = qml_env
    js = env.js
    env.act("showSection('playlists')", 400)
    assert js("stack.currentItem.lists.length") == 0
    env.act("newPlaylist()", 250)
    assert js("namePrompt.visible") is True
    env.act("namePrompt.fieldItem.text = '  '; namePrompt.submit()", 200)
    assert "Escribe un nombre" in js("namePrompt.error") and js("namePrompt.visible") is True
    env.act("namePrompt.fieldItem.text = 'Rock'; namePrompt.submit()", 300)
    assert js("namePrompt.visible") is False and js("toastText.text") == "Lista «Rock» creada"
    assert js("stack.currentItem.lists.length") == 1 and js("playlists.count") == 1
    create_via_prompt(env, "rock")  # mismo nombre sin distinguir mayúsculas
    assert "Ya existe" in js("namePrompt.error") and js("namePrompt.visible") is True
    assert env.warnings == []


def test_picker_adds_tracks_and_can_create_a_new_list_with_them(qml_env):
    env = qml_env
    js, act = env.js, env.act
    ids = track_ids(env)
    pid = env.playlists.create("Mi lista")["id"]
    act(f"showPlaylistPicker([{ids[0]}, {ids[1]}])", 300)
    assert js("playlistPicker.visible") is True and js("playlistPicker.lists.length") == 1
    act(f"playlistPicker.add({pid})", 300)
    assert js("playlistPicker.visible") is False
    assert js("toastText.text") == "2 canciones agregadas a «Mi lista»"
    assert env.playlists.trackIds(pid) == ids[:2]
    # "Nueva lista…" desde el selector: crea la lista con esas canciones
    act(f"showPlaylistPicker([{ids[2]}]); playlistPicker.createNew()", 300)
    assert js("namePrompt.visible") is True
    act("namePrompt.fieldItem.text = 'Otra'; namePrompt.submit()", 300)
    other = next(lst for lst in env.playlists.lists() if lst["name"] == "Otra")
    assert env.playlists.trackIds(other["id"]) == [ids[2]]
    assert js("toastText.text") == "Lista «Otra» creada con 1 canción"
    assert env.warnings == []


def test_playlist_page_plays_reorders_removes_and_queues(qml_env):
    env = qml_env
    js, act = env.js, env.act
    ids = track_ids(env)
    pid = env.playlists.createWithTracks("L", ids)["id"]
    act("showSection('playlists')", 400)
    act(f"openPlaylist({pid})", 400)
    assert js("win.canBack") is True and js("stack.currentItem.info.name") == "L"
    assert titles(js("stack.currentItem.items.map(function (x) { return x.title })")) == [
        "Pista 1", "Pista 2", "Pista 3"]
    act(f"playlists.moveTrack({pid}, 0, 1)", 250)   # el reordenamiento ahora es solo arrastrando
    act(f"playlists.moveTrack({pid}, 2, 1)", 250)
    assert env.playlists.trackIds(pid) == [ids[1], ids[2], ids[0]]
    act("stack.currentItem.removeAt(1)", 250)
    assert env.playlists.trackIds(pid) == [ids[1], ids[0]]
    act("stack.currentItem.playAll()", 300)
    assert js("player.currentTrack.title") == "Pista 2" and js("player.playing")
    env.player.clearQueue()
    act("player.addToQueue(stack.currentItem.ids)", 250)
    assert js("player.queueLength") == 2
    assert env.warnings == []


def test_rename_and_delete_with_confirmation(qml_env):
    env = qml_env
    js, act = env.js, env.act
    pid = env.playlists.create("Vieja")["id"]
    env.playlists.create("Existente")
    act("showSection('playlists')", 400)
    act(f"openPlaylist({pid})", 400)
    act(f"renamePlaylist({pid}, 'Vieja')", 250)
    act("namePrompt.fieldItem.text = 'existente'; namePrompt.submit()", 250)
    assert "Ya existe" in js("namePrompt.error")
    act("namePrompt.fieldItem.text = 'Nueva'; namePrompt.submit()", 300)
    assert js("stack.currentItem.info.name") == "Nueva"
    act(f"deletePlaylist({pid}, 'Nueva')", 250)
    assert js("confirmDialog.visible") is True
    assert env.playlists.info(pid)["name"] == "Nueva"  # nada se borra hasta confirmar
    act("confirmDialog.confirm()", 400)
    assert env.playlists.info(pid) == {}
    assert js("win.section") == "playlists" and js("win.canForward") is True  # volvió a la lista de listas
    assert js("toastText.text") == "Lista «Nueva» eliminada"
    assert [lst["name"] for lst in env.playlists.lists()] == ["Existente"]
    assert env.warnings == []


def test_save_the_current_queue_as_a_playlist(qml_env):
    env = qml_env
    js, act = env.js, env.act
    ids = track_ids(env)
    env.player.addToQueue([ids[2], ids[0], ids[1]])
    act("showSection('queue')", 400)
    act("saveQueueAsPlaylist()", 250)
    assert js("namePrompt.visible") is True
    act("namePrompt.fieldItem.text = 'Guardada'; namePrompt.submit()", 300)
    saved = env.playlists.lists()[0]
    assert saved["name"] == "Guardada" and env.playlists.trackIds(saved["id"]) == [ids[2], ids[0], ids[1]]
    assert js("player.queueLength") == 3  # la lista temporal sigue ahí
    assert js("toastText.text") == "Lista «Guardada» creada con 3 canciones"
    assert env.warnings == []


def test_tags_can_be_edited_from_the_queue_and_the_playlist(qml_env, tmp_path):
    env = qml_env
    js, act = env.js, env.act
    ids = track_ids(env)
    env.player.playTrackIds(ids, 0)
    act("showSection('queue')", 400)
    act(f"stack.currentItem.editRequested([{ids[1]}])", 400)  # lo que emite el botón "Editar tags" de la fila
    assert js("tagEditor.visible") is True and js("tagEditor.info.title.value") == "Pista 2"
    act("tagEditor.close()", 300)
    # el menú de la fila ofrece "Editar tags…"
    act(f"stack.currentItem.menuRequested([{ids[0]}]); trackMenu.edit()", 400)
    assert js("tagEditor.visible") is True and js("tagEditor.info.title.value") == "Pista 1"
    act("tagEditor.close()", 300)
    # tras editar, la cola y la barra de reproducción muestran el título nuevo
    env.controller.applyEdit([ids[0]], {"title": "Título nuevo"}, "", False)
    assert poll(env, "player.currentTrack.title === 'Título nuevo'")
    assert titles(js("stack.currentItem.items.map(function (x) { return x.title })"))[0] == "Título nuevo"
    # y desde una lista guardada
    pid = env.playlists.createWithTracks("L", ids)["id"]
    act("showSection('playlists')", 400)
    act(f"openPlaylist({pid})", 400)
    act(f"stack.currentItem.editRequested([{ids[2]}])", 400)
    assert js("tagEditor.visible") is True and js("tagEditor.info.title.value") == "Pista 3"
    assert env.warnings == []


def test_downloading_artist_info_refreshes_the_artist_cards(qml_env, tmp_path):
    """Al llegar la foto de un artista se recargan las tarjetas (su URL de imagen cambia), y el
    proveedor de imágenes usa esa foto en la sección de artistas (probado en test_ui_smoke)."""
    import threading

    env = qml_env
    js, act = env.js, env.act
    artist = env.controller.artists()[0]["id"]
    act(f"openArtist({artist}, 'Artista')", 500)
    before = js("Theme.dataRevision")
    info = {"name": "Artista", "bio": "Resumen", "url": "", "lang": "es", "source": "Wikipedia",
            "imagePath": str(make_cover(tmp_path / "foto.jpg", "0x2288cc"))}
    # la señal real llega desde un hilo de trabajo (entrega en cola al bucle de eventos de QML)
    threading.Thread(target=lambda: env.online.artistInfoReady.emit(artist, info)).start()
    assert poll(env, f"Theme.dataRevision > {before}")
    assert js("stack.currentItem.artistHeaderItem.info.bio") is not None
    act("showSection('artists')", 500)
    assert js("stack.currentItem.artists.length") == 1
    assert env.warnings == []
