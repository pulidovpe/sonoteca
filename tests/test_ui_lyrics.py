"""Letras desde la UI: controlador (hilo de trabajo) y página QML, con servidores simulados."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import json
import time

import httpx
import pytest

pytest.importorskip("PySide6.QtQml")

from conftest import make_cover, make_mp3, needs_ffmpeg
from PySide6.QtCore import QObject, Slot
from test_online import Net, js, make_client, url_has

from musicapp.core import lyrics as store
from musicapp.core.db import connect
from musicapp.core.scanner import scan
from musicapp.online.settings import Settings
from musicapp.online.translate import DeepLTranslator
from musicapp.ui.controller import LibraryController
from musicapp.ui.lyrics_controller import LyricsController

pytestmark = needs_ffmpeg

LRC = "[00:01.00]First line\n[00:03.00]Second line\n[00:05.00]Third line"
ITEM = {"id": 5, "trackName": "Pista 1", "artistName": "Wheatus", "albumName": "Wheatus",
        "duration": 1.0, "instrumental": False, "plainLyrics": "First line\nSecond line\nThird line",
        "syncedLyrics": LRC}


class Fake(dict):
    """Llavero falso."""
    def get_password(self, s, u): return self.get((s, u))
    def set_password(self, s, u, p): self[(s, u)] = p
    def delete_password(self, s, u): self.pop((s, u), None)


class Collector(QObject):
    def __init__(self):
        super().__init__()
        self.docs, self.errors = [], []

    @Slot(int, "QVariantMap")
    def on_ready(self, track_id, doc): self.docs.append((track_id, doc))

    @Slot(str)
    def on_error(self, message): self.errors.append(message)


def wait_until(qapp, cond, timeout=10.0):
    end = time.time() + timeout
    while not cond() and time.time() < end:
        qapp.processEvents()
        time.sleep(0.01)
    return cond()


@pytest.fixture
def lib(tmp_path, monkeypatch):
    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setenv("MUSICAPP_OFFLINE", "0")
    monkeypatch.delenv("MUSICAPP_DEEPL_KEY", raising=False)
    cover = make_cover(tmp_path / "c.jpg")
    make_mp3(tmp_path / "music/A/1.mp3", cover, title="Pista 1", artist="Wheatus", album="Wheatus")
    db = tmp_path / "t.db"
    conn = connect(db)
    scan(conn, tmp_path / "music")
    conn.close()
    return db


@pytest.fixture
def db_file(lib):
    return lib


def first_track(db):
    return LibraryController(db).tracks(LibraryController(db).albums(0, 0, 0)[0]["id"])[0]["id"]


def make_controller(db, tmp_path, net, keyring=None):
    def translate_handler(request):
        body = json.loads(request.content)
        return js({"translations": [{"detected_source_language": "EN", "text": "ES:" + t}
                                    for t in body["text"]]})

    def translator(key):
        return DeepLTranslator(key, Settings(offline=False), sleep=lambda s: None,
                               transport=httpx.MockTransport(translate_handler))

    return LyricsController(db, client_factory=lambda: make_client(tmp_path, net),
                            translator_factory=translator, key_store=_keys(keyring))


def _keys(keyring):
    from musicapp.online.translate import KeyStore
    return KeyStore(keyring if keyring is not None else Fake())


def test_controller_request_translate_and_key_flow(qapp, lib, tmp_path):
    tid = first_track(lib)
    net = Net({url_has("/api/get"): js(ITEM)})
    c = make_controller(lib, tmp_path, net)
    col = Collector()
    c.lyricsReady.connect(col.on_ready)
    c.lyricsError.connect(col.on_error)
    assert c.stored(tid)["stored"] is False and c.hasKey is False and c.translateLang == "ES"
    c.request(tid, False)
    assert wait_until(qapp, lambda: col.docs), col.errors
    assert col.docs[0][1]["found"] and col.docs[0][1]["synced"] and len(col.docs[0][1]["lines"]) == 3
    assert c.stored(tid)["found"] is True  # quedó guardada: se lee sin red
    # traducir sin clave: mensaje claro, sin salir a la red
    assert wait_until(qapp, lambda: not c.busy)
    c.translate(tid, False)
    assert wait_until(qapp, lambda: col.errors)
    assert "clave de DeepL" in col.errors[0]
    # guardar la clave y traducir
    assert c.setApiKey("   ") != "" and c.setApiKey("abc:fx") == "" and c.hasKey is True
    assert wait_until(qapp, lambda: not c.busy)
    c.translate(tid, False)
    assert wait_until(qapp, lambda: len(col.docs) == 2), col.errors
    doc = col.docs[1][1]
    assert doc["hasTranslation"] and doc["lines"][0]["tr"] == "ES:First line"
    assert c.setTranslateLang("xx yy") != "" and c.setTranslateLang("pt-br") == "" and c.translateLang == "PT-BR"
    assert c.stored(tid)["hasTranslation"] is False  # esa traducción es al español, no a PT-BR
    c.clearApiKey()
    assert c.hasKey is False


def test_controller_reports_offline_and_busy(qapp, lib, tmp_path, monkeypatch):
    tid = first_track(lib)
    monkeypatch.setenv("MUSICAPP_OFFLINE", "1")
    c = make_controller(lib, tmp_path, Net())

    def offline_client():
        return make_client(tmp_path, Net(), offline=True)

    c.client_factory = offline_client
    col = Collector()
    c.lyricsError.connect(col.on_error)
    c.request(tid, False)
    assert wait_until(qapp, lambda: col.errors)
    assert "sin conexión" in col.errors[0]


def test_lyrics_page_shows_stored_lyrics_and_follows_position(qml_env, tmp_path):
    env = qml_env
    js_, act, wait = env.js, env.act, env.wait
    conn = connect(env.controller._db_path)
    tid = first_track(env.controller._db_path)
    store.save_lyrics(conn, tid, plain="a\nb\nc", synced=LRC)
    store.save_translation(conn, tid, "ES", ["uno", "dos", "tres"], "DeepL")
    conn.close()
    act(f"win.showLyrics({tid})", 500)
    assert js_("stack.currentItem.doc.found") is True
    assert js_("stack.currentItem.listItem.count") == 3
    assert js_("stack.currentItem.mode") == "both"
    assert js_("stack.currentItem.indexFor(0)") == -1
    assert js_("stack.currentItem.indexFor(3500)") == 1
    act("stack.currentItem.viewMode = 'original'", 200)
    assert js_("stack.currentItem.mode") == "original"
    # sin pista que suene, la sección Letra pide reproducir algo
    act("win.showSection('lyrics')", 400)
    assert "Reproduce" in js_("stack.currentItem.emptyMessage")
    assert env.warnings == []


def test_lyrics_page_unsearched_track_offers_search(qml_env):
    env = qml_env
    tid = first_track(env.controller._db_path)
    env.act(f"win.showLyrics({tid})", 500)
    assert env.js("stack.currentItem.doc.stored") is False
    assert env.js("stack.currentItem.searchButton.label") == "Buscar letra"
    assert env.warnings == []
