"""OnlineController: consultas en línea en hilos aparte, con servidores simulados."""
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import httpx
import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QObject, Slot
from test_online import ARTIST_SEARCH, JPEG, RG_SEARCH, Net, js, make_client, url_has, wiki_net

from musicapp.core.db import connect
from musicapp.ui.online_controller import OFFLINE_MESSAGE, OnlineController


class Collector(QObject):
    def __init__(self):
        super().__init__()
        self.artist, self.candidates, self.covers, self.errors, self.messages = [], [], [], [], []

    @Slot(int, "QVariantMap")
    def on_artist(self, artist_id, data):
        self.artist.append((artist_id, data))

    @Slot(int, "QVariantList")
    def on_candidates(self, album_id, data):
        self.candidates.append((album_id, data))

    @Slot(str)
    def on_cover(self, path):
        self.covers.append(path)

    @Slot(str)
    def on_error(self, message):
        self.errors.append(message)

    @Slot(str)
    def on_progress(self, message):
        self.messages.append(message)


def wait_until(qapp, cond, timeout=10.0):
    end = time.time() + timeout
    while not cond() and time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)
    return cond()


@pytest.fixture
def env(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setenv("MUSICAPP_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("MUSICAPP_OFFLINE", raising=False)
    monkeypatch.delenv("MUSICAPP_CONTACT", raising=False)
    db = tmp_path / "t.db"
    seed = connect(db)
    seed.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, '4 Non Blondes', '4 Non Blondes');
    INSERT INTO albums (id, title, album_artist_id) VALUES (1, 'Bigger, Better, Faster, More!', 1);
    """)
    seed.close()
    routes = dict(wiki_net().routes)
    routes[url_has("ws/2/artist/?")] = js(ARTIST_SEARCH)
    routes[url_has("upload.wikimedia.org/t.jpg")] = httpx.Response(200, content=JPEG)
    routes[url_has("release-group", "ws/2")] = js(RG_SEARCH)
    routes[url_has("rg-1/front-250")] = httpx.Response(200, content=JPEG)
    routes[url_has("rg-1/front-1200")] = httpx.Response(200, content=JPEG)
    net = Net(routes)
    ctrl = OnlineController(db, client_factory=lambda: make_client(tmp_path, net))
    col = Collector()
    ctrl.artistInfoReady.connect(col.on_artist)
    ctrl.albumCandidatesReady.connect(col.on_candidates)
    ctrl.coverReady.connect(col.on_cover)
    ctrl.onlineError.connect(col.on_error)
    ctrl.progress.connect(col.on_progress)
    return ctrl, col, net, tmp_path


def finished(ctrl, qapp):
    return wait_until(qapp, lambda: not ctrl.busy)


def test_settings_roundtrip(env):
    ctrl, _, _, tmp_path = env
    assert ctrl.offline is True and ctrl.contact == ""  # sin conexión por defecto
    ctrl.setContact("  yo@correo.com ")
    ctrl.setOffline(False)
    assert ctrl.offline is False and ctrl.contact == "yo@correo.com"
    assert (tmp_path / "datos" / "settings.json").exists()


def test_artist_info_downloads_text_and_photo_and_is_stored(env, qapp):
    ctrl, col, _, _ = env
    assert ctrl.storedArtistInfo(1) == {}
    ctrl.requestArtistInfo(1, False)
    assert wait_until(qapp, lambda: col.artist) and finished(ctrl, qapp)
    artist_id, data = col.artist[0]
    assert artist_id == 1 and data["lang"] == "es" and data["source"] == "Wikipedia"
    assert data["bio"].startswith("Resumen en es") and data["url"].startswith("https://es.wikipedia.org")
    with open(data["imagePath"], "rb") as f:
        assert f.read() == JPEG
    assert col.messages  # avisó del progreso
    assert ctrl.storedArtistInfo(1)["bio"] == data["bio"]  # queda guardado para verlo sin conexión


def test_not_found_artist_returns_empty_map(env, qapp):
    ctrl, col, _, tmp_path = env
    routes = {url_has("ws/2/artist/?"): js({"artists": []}),
              url_has("wikipedia.org/w/api.php"): js({"query": {"search": []}})}
    ctrl.client_factory = lambda: make_client(tmp_path, Net(routes))
    ctrl.requestArtistInfo(1, False)
    assert wait_until(qapp, lambda: col.artist) and finished(ctrl, qapp)
    assert col.artist[0] == (1, {})


def test_offline_mode_reports_a_clear_message(env, qapp):
    ctrl, col, _, tmp_path = env
    ctrl.client_factory = lambda: make_client(tmp_path / "x", Net(), offline=True)
    ctrl.requestArtistInfo(1, False)
    assert wait_until(qapp, lambda: col.errors) and finished(ctrl, qapp)
    assert col.errors == [OFFLINE_MESSAGE] and col.artist == []


def test_only_one_query_at_a_time(env, qapp):
    ctrl, col, _, tmp_path = env
    gate = threading.Event()

    def slow(request):
        gate.wait(5)
        return js(ARTIST_SEARCH)

    ctrl.client_factory = lambda: make_client(tmp_path, Net({url_has("ws/2/artist/?"): slow}))
    ctrl.requestArtistInfo(1, False)
    assert ctrl.busy is True
    ctrl.requestCover("rg-1")  # mientras hay una en curso
    assert any("en curso" in m for m in col.errors)
    gate.set()
    assert finished(ctrl, qapp)


def test_album_candidates_with_thumbnails(env, qapp):
    ctrl, col, _, _ = env
    ctrl.requestAlbumCandidates(1, 0)
    assert wait_until(qapp, lambda: col.candidates) and finished(ctrl, qapp)
    album_id, items = col.candidates[0]
    assert album_id == 1 and [c["id"] for c in items] == ["rg-1", "rg-2"]
    best, other = items
    assert best["title"] == "Bigger, Better, Faster, More!" and best["year"] == 1992
    assert best["confident"] is True and other["confident"] is False
    with open(best["previewPath"], "rb") as f:
        assert f.read() == JPEG
    assert other["previewPath"] == ""  # sin miniatura: igual se puede elegir
    assert any("miniaturas" in m for m in col.messages)


def test_cover_is_saved_in_the_apps_own_folder(env, qapp):
    ctrl, col, _, tmp_path = env
    ctrl.requestCover("rg-1")
    assert wait_until(qapp, lambda: col.covers) and finished(ctrl, qapp)
    path = col.covers[0]
    assert path.startswith(str(tmp_path / "datos" / "covers" / "chosen"))
    with open(path, "rb") as f:
        assert f.read() == JPEG


def test_album_without_cover_reports_it(env, qapp):
    ctrl, col, _, _ = env
    ctrl.requestCover("rg-sin-portada")
    assert wait_until(qapp, lambda: col.errors) and finished(ctrl, qapp)
    assert "no tiene portada" in col.errors[0] and col.covers == []
