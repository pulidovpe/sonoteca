"""Interfaz de las funciones en línea (ficha del artista, buscar portada, Internet…) con servidores
simulados. Las acciones que crean páginas o imágenes se lanzan con `act` (desde el bucle de QML)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import httpx
import pytest

pytest.importorskip("PySide6.QtQml")

from pathlib import Path

from conftest import make_cover, make_mp3, needs_ffmpeg
from test_online import ARTIST_SEARCH, RG_SEARCH, Net, js, make_client, url_has, wiki_net

from sonoteca.core import library
from sonoteca.core.db import connect
from sonoteca.core.scanner import scan
from sonoteca.core.tags import read_tags

pytestmark = needs_ffmpeg


@pytest.fixture
def db_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("SONOTECA_OFFLINE", raising=False)
    monkeypatch.delenv("SONOTECA_CONTACT", raising=False)
    root = tmp_path / "music"
    for n in (1, 2):
        make_mp3(root / f"A/{n}.mp3", title=f"Pista {n}", artist="4 Non Blondes",
                 album="What's Up?", date="1993", track=f"{n}/2")
    db = tmp_path / "t.db"
    conn = connect(db)
    scan(conn, root)
    conn.close()
    return db


def server(tmp_path, cover=True):
    jpeg = make_cover(tmp_path / "real.jpg", "0x3366cc").read_bytes()  # imagen real: QML la decodifica
    routes = dict(wiki_net().routes)
    routes[url_has("ws/2/artist/?")] = js(ARTIST_SEARCH)
    routes[url_has("upload.wikimedia.org/t.jpg")] = httpx.Response(200, content=jpeg)
    routes[url_has("release-group", "ws/2")] = js(RG_SEARCH)
    routes[url_has("rg-1/front-250")] = httpx.Response(200, content=jpeg)
    if cover:
        routes[url_has("rg-1/front-1200")] = httpx.Response(200, content=jpeg)
    return Net(routes)


def go_online(env, tmp_path, cover=True):
    net = server(tmp_path, cover)
    env.online.client_factory = lambda: make_client(tmp_path, net)
    env.online.setContact("yo@correo.com")
    env.online.setOffline(False)
    return net


def poll(env, cond_js, timeout=12.0):
    import time

    end = time.time() + timeout
    while time.time() < end:
        if env.js(cond_js):
            return True
        env.wait(200)
    return False


def album_and_tracks(env):
    album = env.controller.albums(0, 0, 0)[0]["id"]
    return album, [t["id"] for t in env.controller.tracks(album)]


def test_internet_dialog_validates_contact_and_switches_mode(qml_env):
    env = qml_env
    js, act = env.js, env.act
    assert js("online.offline") is True and "Sin conexi" in js("onlineBadge.text")
    act("actInternet.trigger()", 300)
    assert js("onlineSettings.visible") is True
    act("onlineSettings.useInternetItem.checked = true; "
        "onlineSettings.contactItem.text = 'sin arroba'; onlineSettings.save()", 300)
    assert "correo" in js("onlineSettings.error") and js("online.offline") is True
    act("onlineSettings.contactItem.text = 'yo@correo.com'; onlineSettings.save()", 400)
    assert js("online.offline") is False and js("online.contact") == "yo@correo.com"
    assert js("onlineSettings.visible") is False and "En l" in js("onlineBadge.text")
    assert env.warnings == []


def test_artist_header_fetches_stores_and_shows_info(qml_env, tmp_path):
    env = qml_env
    js, act = env.js, env.act
    go_online(env, tmp_path)
    act("openArtist(1, '4 Non Blondes')", 500)
    header = "stack.currentItem.artistHeaderItem"
    assert js(f"{header}.visible") is True and js(f"{header}.info.bio") is None
    act(f"{header}.search()", 200)
    assert poll(env, f"!{header}.searching && !!{header}.info.bio")
    assert js(f"{header}.info.bio").startswith("Resumen en es")
    assert js(f"{header}.info.lang") == "es" and js(f"{header}.info.source") == "Wikipedia"
    assert Path(js(f"{header}.info.imagePath")).exists()  # foto guardada para verla sin conexión
    # ya guardado: sigue disponible aunque se vuelva a sin conexión
    env.online.setOffline(True)
    assert env.online.storedArtistInfo(1)["bio"].startswith("Resumen en es")
    assert env.warnings == []


def test_artist_header_offline_opens_the_internet_dialog(qml_env):
    env = qml_env
    env.act("openArtist(1, '4 Non Blondes')", 500)
    env.act("stack.currentItem.artistHeaderItem.search()", 400)
    assert env.js("onlineSettings.visible") is True
    assert env.warnings == []


def test_album_lookup_applies_cover_album_and_year_after_confirmation(qml_env, tmp_path):
    env = qml_env
    js, act = env.js, env.act
    go_online(env, tmp_path)
    album, ids = album_and_tracks(env)
    act(f"lookupAlbum({album}, {ids}, false)", 300)
    assert js("albumLookup.visible") is True
    assert poll(env, "albumLookup.step === 1 && albumLookup.candidates.length === 2")
    assert js("albumLookup.candidates[0].title") == "Bigger, Better, Faster, More!"
    # el nombre de nuestro álbum ("What's Up?") no se parece al candidato: no se afirma coincidencia
    assert js("albumLookup.candidates[0].confident") is False and js("albumLookup.selected") == 0
    # nada cambia hasta confirmar
    assert read_tags(Path(library.get_track(connect(env.controller._db_path), ids[0])["path"])).album == "What's Up?"
    act("albumLookup.updateTagsItem.checked = true; albumLookup.apply()", 200)
    assert poll(env, "toastText.text.indexOf('actualizados') >= 0")
    assert js("toastText.text") == "2 archivos actualizados"
    conn = connect(env.controller._db_path)
    for t in ids:
        meta = read_tags(Path(library.get_track(conn, t)["path"]))
        assert (meta.album, meta.year, meta.has_cover) == ("Bigger, Better, Faster, More!", 1992, True)
    assert list((tmp_path / "datos" / "covers" / "chosen").iterdir())  # copia propia de la portada
    assert js("albumLookup.visible") is False
    assert env.warnings == []


def test_album_lookup_offline_asks_to_enable_internet(qml_env):
    env = qml_env
    album, ids = album_and_tracks(env)
    env.act(f"lookupAlbum({album}, {ids}, false)", 400)
    assert env.js("albumLookup.visible") is False and env.js("onlineSettings.visible") is True
    assert env.warnings == []


def test_album_without_cover_shows_the_reason_and_applies_nothing(qml_env, tmp_path):
    env = qml_env
    js, act = env.js, env.act
    go_online(env, tmp_path, cover=False)
    album, ids = album_and_tracks(env)
    act(f"lookupAlbum({album}, {ids}, false)", 300)
    assert poll(env, "albumLookup.step === 1 && albumLookup.candidates.length === 2")
    act("albumLookup.apply()", 200)  # solo portada, y ese álbum no tiene
    assert poll(env, "albumLookup.error.indexOf('no tiene portada') >= 0")
    assert js("albumLookup.visible") is True and js("albumLookup.step") == 1
    conn = connect(env.controller._db_path)
    assert read_tags(Path(library.get_track(conn, ids[0])["path"])).has_cover is False
    assert env.warnings == []
