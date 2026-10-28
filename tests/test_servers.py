"""Servidores alternativos de letras y de portadas/información."""
import pytest

from sonoteca.online import coverart, lrclib, musicbrainz, servers, wikipedia
from sonoteca.online import settings as online_settings
from sonoteca.online.http import OnlineError


class FakeClient:
    """Registra las URLs consultadas y responde lo que se le indique."""

    def __init__(self, json=None, raises=None):
        self.urls, self._json, self._raises = [], json, raises

    def get_json(self, url, params=None, **kw):
        self.urls.append(url)
        if self._raises:
            raise self._raises
        return self._json

    def get_bytes(self, url, **kw):
        self.urls.append(url)
        return None


def test_normalize_url_accepts_http_s_and_rejects_the_rest():
    assert servers.normalize_url(" https://mi.servidor/api/ ") == "https://mi.servidor/api"
    assert servers.normalize_url("http://192.168.1.5:3300/api") == "http://192.168.1.5:3300/api"
    assert servers.normalize_url("https://{lang}.wiki.example", template=True) == "https://{lang}.wiki.example"
    for bad in ("ftp://x", "mi.servidor/api", "https://", "https://u:p@host/api", "https://h/api?x=1", "https://h/{lang}"):
        with pytest.raises(ValueError):
            servers.normalize_url(bad)


def test_add_select_and_remove_servers():
    s = online_settings.Settings()
    lr = servers.add_lyrics_server(s, "Mi LRCLIB", "https://letras.casa/api/")
    assert lr["url"] == "https://letras.casa/api" and servers.lyrics_base(s) == servers.DEFAULT_LYRICS   # aún no activo
    servers.set_active(s, "lyrics", lr["id"])
    assert servers.lyrics_base(s) == "https://letras.casa/api" and servers.lyrics_name(s) == "Mi LRCLIB"
    meta = servers.add_meta_server(s, "Espejo", musicbrainz="https://mb.casa/ws/2", wikipedia="https://{lang}.wiki.casa")
    servers.set_active(s, "meta", meta["id"])
    assert servers.musicbrainz_base(s) == "https://mb.casa/ws/2"
    assert servers.coverart_base(s) == servers.DEFAULT_COVERART            # lo vacío usa el predeterminado
    assert servers.wikipedia_base("es", s) == "https://es.wiki.casa"
    st = servers.state(s)
    assert st["lyricsActive"] == lr["id"] and st["meta"][0]["builtin"] and len(st["meta"]) == 2
    servers.remove_server(s, "lyrics", lr["id"])                            # borrar el activo vuelve al predeterminado
    assert s.lyrics_active == "default" and servers.lyrics_base(s) == servers.DEFAULT_LYRICS
    with pytest.raises(ValueError):
        servers.add_meta_server(s, "Vac\u00edo")
    with pytest.raises(ValueError):
        servers.add_lyrics_server(s, "", "https://x.y/api")
    with pytest.raises(ValueError):
        servers.set_active(s, "lyrics", "no-existe")


def test_settings_roundtrip_and_modules_use_the_active_server(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    s = online_settings.load(apply_env=False)
    lr = servers.add_lyrics_server(s, "Mi LRCLIB", "https://letras.casa/api")
    servers.set_active(s, "lyrics", lr["id"])
    meta = servers.add_meta_server(s, "Espejo", "https://mb.casa/ws/2", "https://caa.casa", "https://{lang}.wiki.casa")
    servers.set_active(s, "meta", meta["id"])
    online_settings.save(s)
    again = online_settings.load(apply_env=False)
    assert again.lyrics_active == lr["id"] and again.meta_servers[0]["coverart"] == "https://caa.casa"

    c = FakeClient(json=None)
    lrclib.get_exact(c, "A", "T")
    assert c.urls[-1] == "https://letras.casa/api/get"
    c = FakeClient(json={})
    musicbrainz.search_artists(c, "Alguien")
    assert c.urls[-1].startswith("https://mb.casa/ws/2/artist")
    c = FakeClient()
    coverart.fetch_front(c, "rg-1")
    assert c.urls[0].startswith("https://caa.casa/release-group/rg-1/front-")
    c = FakeClient(json=None)
    wikipedia._summary(c, "es", "Alguien")
    assert c.urls[-1].startswith("https://es.wiki.casa/api/rest_v1/page/summary/")


def test_connection_tests_report_clear_messages():
    assert servers.test_lyrics(FakeClient(json=[]), "https://x.y/api")[0] is True
    ok, msg = servers.test_lyrics(FakeClient(json={"error": 1}), "https://x.y/api")
    assert not ok and "LRCLIB" in msg
    ok, msg = servers.test_lyrics(FakeClient(raises=OnlineError("sin respuesta")), "https://x.y/api")
    assert not ok and "sin respuesta" in msg
    assert servers.test_lyrics(FakeClient(json=[]), "nope")[0] is False
    assert servers.test_meta(FakeClient(json={"artists": []}), musicbrainz="https://mb.x/ws/2")[0] is True
    assert servers.test_meta(FakeClient(json={"x": 1}), musicbrainz="https://mb.x/ws/2")[0] is False
    assert servers.test_meta(FakeClient(json={"extract": "..."}), wikipedia="https://{lang}.w.x")[0] is True
