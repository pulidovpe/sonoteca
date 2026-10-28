"""Letras (Fase 6): parser LRC, almacenamiento, LRCLIB y traducción con DeepL.

Los servicios se simulan con httpx.MockTransport siguiendo el formato documentado:
LRCLIB (`/api/get`, `/api/search`) y DeepL (`/v2/translate`, `/v2/usage`).
"""
import json
from datetime import datetime, timedelta

import httpx
import pytest
from test_online import FakeTime, Net, js, make_client, url_has

from musicapp.core import lyrics as store
from musicapp.core.db import SCHEMA_VERSION, connect
from musicapp.online import lrclib
from musicapp.online import lyrics as flow
from musicapp.online.http import OfflineError, OnlineError
from musicapp.online.settings import Settings
from musicapp.online.translate import DeepLTranslator, KeyStore, normalize_lang

LRC = "[ar:Wheatus]\n[00:01.50]First line\n[00:03.25]Second line\n[00:05.00]\n[00:07.00]Chorus"
PLAIN = "First line\nSecond line\n\nChorus"


def lrclib_item(**over):
    item = {"id": 11, "trackName": "Teenage Dirtbag", "artistName": "Wheatus", "albumName": "Wheatus",
            "duration": 241.0, "instrumental": False, "plainLyrics": PLAIN, "syncedLyrics": LRC}
    item.update(over)
    return item


def make_db(artist="Wheatus", album="Wheatus", title="Teenage Dirtbag", duration=241.0):
    conn = connect(":memory:")
    conn.execute("INSERT INTO artists(id,name,sort_name) VALUES (1,?,?)", (artist, artist))
    conn.execute("INSERT INTO albums(id,title,album_artist_id) VALUES (1,?,1)", (album,))
    conn.execute("INSERT INTO files(id,path,size,mtime_ns,format,kind) VALUES (1,'/x.mp3',1,1,'mp3','audio')")
    conn.execute("INSERT INTO tracks(id,file_id,album_id,artist_id,title,duration)"
                 " VALUES (1,1,1,1,?,?)", (title, duration))
    conn.commit()
    return conn


# ---------------- núcleo: LRC y almacenamiento ----------------
def test_parse_lrc_formats_and_metadata():
    lines = store.parse_lrc("[ar:X]\n[ti:Y]\n[00:01.5] Uno\n[00:03.25]Dos <00:03.50>palabra\n"
                            "[00:10.5][00:20.25]Coro\n[00:30.00]\nsin marca\n[01:02:50]Fin")
    assert [(ln.time_ms, ln.text) for ln in lines] == [
        (1500, "Uno"), (3250, "Dos palabra"), (10500, "Coro"), (20250, "Coro"),
        (30000, ""), (62500, "Fin")]
    assert store.parse_lrc("basura sin marcas") == [] and store.parse_lrc(None) == []


def test_plain_lines_trim_and_build_prefers_synced():
    assert [ln.text for ln in store.plain_lines("\n\nHola\nmundo\n\nadiós\n\n")] == [
        "Hola", "mundo", "", "adiós"]
    assert store.build_lines(LRC, PLAIN)[0].time_ms == 1500
    assert store.build_lines("roto", "a\nb")[0].time_ms is None  # LRC ilegible: cae al texto plano
    times = [1500, 3250, 5000]
    assert [store.line_index_at(times, ms) for ms in (0, 1500, 4000, 99999)] == [-1, 0, 1, 2]


def test_store_roundtrip_translation_and_not_found_retry():
    conn = make_db()
    assert store.should_retry(store.get_stored(conn, 1)) is True
    store.save_not_found(conn, 1)
    row = store.get_stored(conn, 1)
    assert not store.has_lyrics(row) and store.should_retry(row) is False
    assert store.should_retry(row, datetime.now() + timedelta(days=31)) is True
    store.save_lyrics(conn, 1, plain=PLAIN, synced=LRC, lrclib_id=11)
    store.save_translation(conn, 1, "es", ["Primera", "Segunda", "", "Coro"], "DeepL")
    doc = store.lyrics_doc(conn, 1, "ES")
    assert doc["found"] and doc["synced"] and doc["hasTranslation"]
    assert doc["lines"][1] == {"t": 3250, "text": "Second line", "tr": "Segunda"}
    # reemplazar la letra descarta las traducciones (ya no corresponden)
    store.save_lyrics(conn, 1, plain="Otra", synced=None)
    doc = store.lyrics_doc(conn, 1, "ES")
    assert not doc["hasTranslation"] and not doc["synced"] and doc["lines"][0]["t"] == -1
    # una traducción desalineada se ignora en vez de mostrarse mal
    store.save_translation(conn, 1, "ES", ["a", "b"], "DeepL")
    assert store.lyrics_doc(conn, 1, "ES")["hasTranslation"] is False
    conn.execute("DELETE FROM tracks WHERE id = 1")  # la letra sale con la pista (ON DELETE CASCADE)
    assert store.get_stored(conn, 1) is None


def test_schema_v5_migrates_from_v4():
    import sqlite3

    from musicapp.core import db

    raw = sqlite3.connect(":memory:")
    raw.row_factory = sqlite3.Row
    raw.executescript(db.SCHEMA_V1)
    raw.execute("ALTER TABLE tracks ADD COLUMN inferred INTEGER NOT NULL DEFAULT 0")
    for column in ("bio_url", "bio_lang", "image_url", "info_fetched_at"):
        raw.execute(f"ALTER TABLE artists ADD COLUMN {column} TEXT")
    raw.execute("PRAGMA user_version = 4")
    db.migrate(raw)
    assert raw.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    cols = {r["name"] for r in raw.execute("PRAGMA table_info(lyrics)")}
    assert {"fetched_at", "instrumental", "lrclib_id"} <= cols


# ---------------- LRCLIB ----------------
def test_get_exact_sends_documented_params_and_skips_http_cache(tmp_path):
    seen = {}

    def handler(request):
        seen.update(dict(request.url.params))
        return js(lrclib_item())

    net = Net({url_has("/api/get"): handler})
    client = make_client(tmp_path, net)
    result = lrclib.find_lyrics(client, "Wheatus", "Teenage Dirtbag", "Wheatus", 240.6)
    assert result.id == 11 and result.synced.startswith("[ar:Wheatus]")
    assert seen == {"track_name": "Teenage Dirtbag", "artist_name": "Wheatus",
                    "album_name": "Wheatus", "duration": "241"}
    assert "User-Agent" in net.calls[0].headers and "test@example.com" in net.calls[0].headers["user-agent"]
    assert not list((tmp_path / "http").glob("*.json"))  # las letras no se guardan en la caché HTTP


def test_find_lyrics_retries_without_album_then_searches(tmp_path):
    def get(request):
        return js(lrclib_item()) if "album_name" not in request.url.params else httpx.Response(404)

    net = Net({url_has("/api/get"): get})
    result = lrclib.find_lyrics(make_client(tmp_path, net), "Wheatus", "Teenage Dirtbag",
                                "Grandes éxitos", 241)
    assert result.id == 11 and net.count("/api/get") == 2 and net.count("/api/search") == 0

    wrong = lrclib_item(id=1, duration=275.0)                       # otra versión (más larga)
    plain_only = lrclib_item(id=2, syncedLyrics=None, duration=240.0)
    synced = lrclib_item(id=3, duration=243.0)
    other_song = lrclib_item(id=4, trackName="Another Song")
    net = Net({url_has("/api/get"): httpx.Response(404),
               url_has("/api/search"): js([wrong, plain_only, other_song, synced])})
    result = lrclib.find_lyrics(make_client(tmp_path, net), "Wheatus", "Teenage Dirtbag",
                                "", 241)
    assert result.id == 3  # sincronizada, misma canción y duración parecida


def test_find_lyrics_none_and_instrumental(tmp_path):
    net = Net({url_has("/api/get"): httpx.Response(404), url_has("/api/search"): js([])})
    assert lrclib.find_lyrics(make_client(tmp_path, net), "A", "B") is None
    inst = lrclib_item(instrumental=True, plainLyrics=None, syncedLyrics=None)
    net = Net({url_has("/api/get"): js(inst)})
    assert lrclib.find_lyrics(make_client(tmp_path, net), "A", "B").instrumental is True


def test_lrclib_overloaded_503_is_retried_with_retry_after(tmp_path):
    answers = [httpx.Response(503, headers={"Retry-After": "1"}), js(lrclib_item())]
    net = Net({url_has("/api/get"): lambda r: answers.pop(0)})
    time = FakeTime()
    client = make_client(tmp_path, net, time=time)
    assert lrclib.find_lyrics(client, "Wheatus", "Teenage Dirtbag").id == 11
    assert 1.0 in time.slept


# ---------------- orquestación (buscar y guardar) ----------------
def test_fetch_saves_then_serves_from_database_without_network(tmp_path):
    conn = make_db()
    net = Net({url_has("/api/get"): js(lrclib_item())})
    doc = flow.fetch_lyrics(make_client(tmp_path, net), conn, 1, lang="ES")
    assert doc["found"] and doc["synced"] and len(doc["lines"]) == 4 and net.count("/api/get") == 1
    # segunda vez: ni siquiera hace falta un cliente con conexión
    offline = make_client(tmp_path, Net(), offline=True)
    again = flow.fetch_lyrics(offline, conn, 1, lang="ES")
    assert again["found"] and again["lines"] == doc["lines"]


def test_fetch_not_found_is_remembered_and_force_keeps_existing_lyrics(tmp_path):
    conn = make_db()
    net = Net({url_has("/api/get"): httpx.Response(404), url_has("/api/search"): js([])})
    doc = flow.fetch_lyrics(make_client(tmp_path, net), conn, 1)
    assert doc["stored"] and not doc["found"] and doc["retry"] is False
    calls = len(net.calls)
    flow.fetch_lyrics(make_client(tmp_path, net), conn, 1)
    assert len(net.calls) == calls  # no repite la consulta fallida
    # con letra guardada, "buscar de nuevo" que no encuentra nada no la borra
    store.save_lyrics(conn, 1, plain=PLAIN, synced=LRC)
    doc = flow.fetch_lyrics(make_client(tmp_path, net), conn, 1, force=True)
    assert doc["found"] and len(doc["lines"]) == 4


def test_fetch_same_lyrics_again_keeps_translation(tmp_path):
    conn = make_db()
    net = Net({url_has("/api/get"): js(lrclib_item())})
    flow.fetch_lyrics(make_client(tmp_path, net), conn, 1)
    store.save_translation(conn, 1, "ES", ["a", "b", "", "d"], "DeepL")
    doc = flow.fetch_lyrics(make_client(tmp_path, net), conn, 1, lang="ES", force=True)
    assert doc["hasTranslation"] is True  # el texto no cambió: la traducción sigue valiendo


def test_fetch_offline_without_stored_lyrics_raises_and_unknown_artist_is_explained(tmp_path):
    conn = make_db()
    with pytest.raises(OfflineError):
        flow.fetch_lyrics(make_client(tmp_path, Net(), offline=True), conn, 1)
    conn = make_db(artist="Artista desconocido")
    with pytest.raises(OnlineError, match="sin artista|no tiene artista"):
        flow.fetch_lyrics(make_client(tmp_path, Net()), conn, 1)
    with pytest.raises(OnlineError, match="ya no está"):
        flow.fetch_lyrics(make_client(tmp_path, Net()), conn, 99)


# ---------------- DeepL ----------------
def deepl_handler(calls):
    def handler(request):
        calls.append(request)
        if request.url.path.endswith("/v2/usage"):
            return js({"character_count": 1234, "character_limit": 500000})
        body = json.loads(request.content)
        return js({"translations": [{"detected_source_language": "EN", "text": f"ES:{t}"}
                                    for t in body["text"]]})
    return handler


def translator(handler, key="abc123:fx", offline=False):
    return DeepLTranslator(key, Settings(offline=offline, contact="test@example.com"),
                           transport=httpx.MockTransport(handler), sleep=lambda s: None)


def test_deepl_free_host_headers_and_blank_lines_not_sent():
    calls = []
    t = translator(deepl_handler(calls))
    out, detected = t.translate_lines(["Hello", "", "World  ", "   "], "es")
    assert out == ["ES:Hello", "", "ES:World  ", ""] and detected == "EN"
    request = calls[0]
    assert request.url.host == "api-free.deepl.com" and request.url.path == "/v2/translate"
    assert request.headers["authorization"] == "DeepL-Auth-Key abc123:fx"
    assert json.loads(request.content) == {"text": ["Hello", "World  "], "target_lang": "ES"}
    assert translator(deepl_handler([]), key="clave-pro").requests == 0
    pro_calls = []
    translator(deepl_handler(pro_calls), key="clave-pro").translate_lines(["x"], "EN-US")
    assert pro_calls[0].url.host == "api.deepl.com"


def test_deepl_batches_of_50_and_usage():
    calls = []
    t = translator(deepl_handler(calls))
    lines = [f"line {i}" for i in range(120)]
    out, _ = t.translate_lines(lines, "ES")
    assert out == [f"ES:{x}" for x in lines] and len(calls) == 3
    assert [len(json.loads(c.content)["text"]) for c in calls] == [50, 50, 20]
    assert t.usage() == {"used": 1234, "limit": 500000}


@pytest.mark.parametrize("status, text", [
    (403, "rechazó la clave"), (456, "cuota mensual"), (400, "idioma"), (500, "no está disponible")])
def test_deepl_errors_have_clear_messages(status, text):
    t = translator(lambda r: httpx.Response(status))
    with pytest.raises(OnlineError, match=text):
        t.translate_lines(["hola"], "ES")


def test_deepl_429_retries_then_gives_up_and_offline_is_respected():
    answers = [httpx.Response(429, headers={"Retry-After": "2"}), httpx.Response(429), httpx.Response(429)]
    t = translator(lambda r: answers.pop(0))
    with pytest.raises(OnlineError, match="demasiadas peticiones"):
        t.translate_lines(["hola"], "ES")
    assert t.requests == 3
    calls = []
    with pytest.raises(OfflineError):
        translator(deepl_handler(calls), offline=True).translate_lines(["hola"], "ES")
    assert calls == []  # sin conexión no sale ninguna petición


def test_deepl_rejects_bad_responses_and_languages():
    t = translator(lambda r: js({"translations": []}))
    with pytest.raises(OnlineError, match="no es válida"):
        t.translate_lines(["hola"], "ES")
    with pytest.raises(OnlineError, match="código de idioma"):
        normalize_lang("español")
    assert normalize_lang(" en_us ") == "EN-US" and normalize_lang("es") == "ES"
    with pytest.raises(OnlineError, match="Falta la clave"):
        DeepLTranslator("  ", Settings(offline=False))
    with pytest.raises(OnlineError, match="demasiado larga"):
        translator(deepl_handler([])).translate_lines(["x" * 31000], "ES")


def test_translate_lyrics_caches_and_detects_language():
    conn = make_db()
    store.save_lyrics(conn, 1, plain=PLAIN, synced=LRC)
    calls = []
    t = translator(deepl_handler(calls))
    doc = flow.translate_lyrics(t, conn, 1, "es")
    assert doc["hasTranslation"] and doc["language"] == "EN"
    assert [ln["tr"] for ln in doc["lines"]] == ["ES:First line", "ES:Second line", "", "ES:Chorus"]
    assert len(calls) == 1
    flow.translate_lyrics(t, conn, 1, "ES")  # ya traducida: no vuelve a gastar caracteres
    assert len(calls) == 1
    flow.translate_lyrics(t, conn, 1, "ES", force=True)
    assert len(calls) == 2
    conn2 = make_db()
    with pytest.raises(OnlineError, match="búscala primero"):
        flow.translate_lyrics(t, conn2, 1, "ES")


# ---------------- clave ----------------
class FakeKeyring:
    def __init__(self):
        self.data = {}

    def get_password(self, service, user):
        return self.data.get((service, user))

    def set_password(self, service, user, password):
        self.data[(service, user)] = password

    def delete_password(self, service, user):
        self.data.pop((service, user), None)


def test_key_store_roundtrip_and_environment_priority(monkeypatch):
    monkeypatch.delenv("MUSICAPP_DEEPL_KEY", raising=False)
    store_ = KeyStore(FakeKeyring())
    assert store_.get() == ""
    store_.set("  mi-clave:fx  ")
    assert store_.get() == "mi-clave:fx"
    monkeypatch.setenv("MUSICAPP_DEEPL_KEY", "de-entorno")
    assert store_.get() == "de-entorno"
    monkeypatch.delenv("MUSICAPP_DEEPL_KEY")
    store_.delete()
    assert store_.get() == ""
    with pytest.raises(OnlineError, match="vacía"):
        store_.set("   ")

    class Broken(FakeKeyring):
        def get_password(self, *a):
            raise RuntimeError("sin llavero")

        def set_password(self, *a):
            raise RuntimeError("sin llavero")

    broken = KeyStore(Broken())
    assert broken.get() == ""  # sin llavero = sin clave, no un error
    with pytest.raises(OnlineError, match="MUSICAPP_DEEPL_KEY"):
        broken.set("x")
