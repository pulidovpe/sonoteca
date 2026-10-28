"""Servicios en línea probados con respuestas simuladas (httpx.MockTransport) que siguen el
formato documentado de MusicBrainz, Cover Art Archive, Wikidata y Wikipedia."""
import json

import httpx
import pytest

from sonoteca.cli import main
from sonoteca.core.db import connect
from sonoteca.online import coverart, enrich, musicbrainz, wikipedia
from sonoteca.online import settings as online_settings
from sonoteca.online.http import HttpClient, OfflineError, OnlineError, RateLimiter
from sonoteca.online.settings import Settings

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64
ARTIST = {"id": "art-1", "name": "4 Non Blondes", "sort-name": "4 Non Blondes"}
CREDIT = [{"name": "4 Non Blondes", "joinphrase": "", "artist": ARTIST}]

RG_SEARCH = {"count": 2, "release-groups": [
    {"id": "rg-2", "score": 60, "primary-type": "Single", "title": "Bigger, Better, Faster, More! (promo)",
     "first-release-date": "1993", "artist-credit": CREDIT},
    {"id": "rg-1", "score": 100, "primary-type": "Album", "title": "Bigger, Better, Faster, More!",
     "first-release-date": "1992-10-13", "artist-credit": CREDIT},
]}
REC_SEARCH = {"recordings": [{"id": "rec-1", "score": 100, "title": "What's Up?", "artist-credit": CREDIT,
    "releases": [
        {"id": "rel-3", "title": "Now 25", "date": "1993",
         "release-group": {"id": "rg-3", "primary-type": "Album", "secondary-types": ["Compilation"],
                           "title": "Now 25"}},
        {"id": "rel-2", "title": "What's Up? (single)", "date": "1993-06",
         "release-group": {"id": "rg-4", "primary-type": "Single", "title": "What's Up?"}},
        {"id": "rel-1", "title": "Bigger, Better, Faster, More!", "date": "1992-10-13",
         "release-group": {"id": "rg-1", "primary-type": "Album", "title": "Bigger, Better, Faster, More!"}},
        {"id": "rel-1b", "title": "Bigger, Better, Faster, More!", "date": "1993",
         "release-group": {"id": "rg-1", "primary-type": "Album", "title": "Bigger, Better, Faster, More!"}},
    ]}]}
ARTIST_SEARCH = {"artists": [
    {"id": "art-9", "score": 40, "name": "Otra Banda", "type": "Group"},
    {"id": "art-1", "score": 100, "name": "4 Non Blondes", "type": "Group", "country": "US",
     "life-span": {"begin": "1989"}, "disambiguation": ""}]}
ARTIST_RELS = {"id": "art-1", "relations": [
    {"type": "official homepage", "url": {"resource": "http://example.org"}},
    {"type": "wikidata", "url": {"resource": "https://www.wikidata.org/wiki/Q215539"}}]}
WIKIDATA = {"entities": {"Q215539": {"sitelinks": {
    "eswiki": {"site": "eswiki", "title": "4 Non Blondes"},
    "enwiki": {"site": "enwiki", "title": "4 Non Blondes (band)"}}}}}


def wiki_summary(lang, title="4 Non Blondes", description="banda estadounidense de rock alternativo",
                 type_="standard"):
    return {"type": type_, "title": title, "description": description,
            "extract": f"Resumen en {lang} de {title}.",
            "content_urls": {"desktop": {"page": f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"}},
            "thumbnail": {"source": "https://upload.wikimedia.org/t.jpg"},
            "originalimage": {"source": "https://upload.wikimedia.org/o.jpg"}}


class FakeTime:
    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


class Net:
    """Servidor simulado: enruta por URL, cuenta peticiones y guarda las cabeceras."""

    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        for matcher, responder in self.routes.items():
            if matcher(request):
                return responder(request) if callable(responder) else responder
        return httpx.Response(404)

    def count(self, text):
        return sum(text in str(c.url) for c in self.calls)


def url_has(*parts):
    return lambda r: all(p in str(r.url) for p in parts)


def make_client(tmp_path, net, offline=False, time=None):
    time = time or FakeTime()
    client = HttpClient(Settings(offline=offline, contact="test@example.com"),
                        transport=httpx.MockTransport(net), cache_dir=tmp_path / "http",
                        limiter=RateLimiter(clock=time.clock, sleep=time.sleep),
                        sleep=time.sleep, clock=time.clock)
    return client


def js(data, status=200):
    return httpx.Response(status, json=data)


# ---------------- ajustes ----------------
def test_settings_default_offline_and_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("SONOTECA_OFFLINE", raising=False)
    monkeypatch.delenv("SONOTECA_CONTACT", raising=False)
    assert online_settings.load() == Settings(offline=True, contact="")
    online_settings.save(Settings(offline=False, contact="yo@correo.com"))
    assert online_settings.load() == Settings(offline=False, contact="yo@correo.com")
    monkeypatch.setenv("SONOTECA_OFFLINE", "1")
    monkeypatch.setenv("SONOTECA_CONTACT", "otro@correo.com")
    assert online_settings.load() == Settings(offline=True, contact="otro@correo.com")
    assert online_settings.load(apply_env=False).contact == "yo@correo.com"
    assert "yo@correo.com" in online_settings.user_agent("yo@correo.com")
    assert "uso personal" in online_settings.user_agent("")


# ---------------- HTTP ----------------
def test_rate_limiter_spaces_requests_per_host():
    t = FakeTime()
    lim = RateLimiter(clock=t.clock, sleep=t.sleep)
    lim.wait("musicbrainz.org")
    lim.wait("musicbrainz.org")
    lim.wait("musicbrainz.org")
    assert t.slept == [pytest.approx(1.1), pytest.approx(1.1)]  # 1 petición por segundo como máximo
    t.slept.clear()
    lim.wait("es.wikipedia.org")  # otro servidor no espera
    assert t.slept == []
    t.now += 5
    lim.wait("musicbrainz.org")  # pasó el tiempo: tampoco
    assert t.slept == []


def test_get_json_sends_user_agent_caches_and_works_offline_from_cache(tmp_path):
    net = Net({url_has("example.org/data"): js({"ok": 1})})
    client = make_client(tmp_path, net)
    assert client.get_json("https://example.org/data", {"a": "1"}) == {"ok": 1}
    assert client.get_json("https://example.org/data", {"a": "1"}) == {"ok": 1}
    assert len(net.calls) == 1  # la segunda salió de la caché
    ua = net.calls[0].headers["user-agent"]
    assert ua.startswith("sonoteca/") and "test@example.com" in ua
    # sin conexión: lo guardado se puede usar; lo nuevo no
    offline = make_client(tmp_path, Net(), offline=True)
    assert offline.get_json("https://example.org/data", {"a": "1"}) == {"ok": 1}
    with pytest.raises(OfflineError):
        offline.get_json("https://example.org/otro")
    with pytest.raises(OfflineError):
        offline.get_bytes("https://example.org/img.jpg")


def test_cache_expires(tmp_path):
    t = FakeTime()
    net = Net({url_has("example.org"): js({"v": 1})})
    client = make_client(tmp_path, net, time=t)
    client.get_json("https://example.org/x", ttl=100)
    t.now += 101
    client.get_json("https://example.org/x", ttl=100)
    assert len(net.calls) == 2


def test_404_is_none_and_remembered(tmp_path):
    net = Net()
    client = make_client(tmp_path, net)
    assert client.get_json("https://example.org/falta") is None
    assert client.get_json("https://example.org/falta") is None
    assert len(net.calls) == 1


def test_retries_503_honoring_retry_after_then_succeeds(tmp_path):
    t = FakeTime()
    answers = iter([httpx.Response(503, headers={"Retry-After": "3"}), js({"ok": True})])
    net = Net({url_has("example.org"): lambda r: next(answers)})
    client = make_client(tmp_path, net, time=t)
    assert client.get_json("https://example.org/x") == {"ok": True}
    assert 3.0 in t.slept and len(net.calls) == 2


def test_persistent_503_and_server_errors_have_friendly_messages(tmp_path):
    client = make_client(tmp_path, Net({url_has("musicbrainz.org"): httpx.Response(503)}))
    with pytest.raises(OnlineError, match="MusicBrainz está saturado"):
        client.get_json("https://musicbrainz.org/ws/2/x")
    client = make_client(tmp_path, Net({url_has("wikipedia.org"): httpx.Response(500)}))
    with pytest.raises(OnlineError, match="Wikipedia respondió con un error"):
        client.get_json("https://es.wikipedia.org/x")


def test_network_failures_are_mapped(tmp_path):
    def timeout(request):
        raise httpx.ReadTimeout("lento")

    def down(request):
        raise httpx.ConnectError("sin red")

    with pytest.raises(OnlineError, match="tardó demasiado"):
        make_client(tmp_path, timeout).get_json("https://musicbrainz.org/ws/2/x")
    with pytest.raises(OnlineError, match="No se pudo conectar con MusicBrainz"):
        make_client(tmp_path, down).get_json("https://musicbrainz.org/ws/2/y")


def test_get_bytes_limit_and_invalid_json(tmp_path):
    net = Net({url_has("big"): httpx.Response(200, content=b"x" * 100),
               url_has("broken"): httpx.Response(200, content=b"<html>")})
    client = make_client(tmp_path, net)
    with pytest.raises(OnlineError, match="demasiado grande"):
        client.get_bytes("https://example.org/big", max_bytes=10)
    with pytest.raises(OnlineError, match="no es válida"):
        client.get_json("https://example.org/broken")


# ---------------- MusicBrainz ----------------
def test_lucene_phrase_escaping():
    assert musicbrainz.phrase('Guns N\' Roses') == '"Guns N\' Roses"'
    assert musicbrainz.phrase('Weird "Al" Yankovic') == '"Weird \\"Al\\" Yankovic"'
    assert musicbrainz.phrase("a\\b") == '"a\\\\b"'


def test_search_albums_parses_ranks_and_sends_escaped_query(tmp_path):
    net = Net({url_has("musicbrainz.org/ws/2/release-group"): js(RG_SEARCH)})
    client = make_client(tmp_path, net)
    found = musicbrainz.search_albums(client, "4 Non Blondes", "Bigger, Better, Faster, More!")
    assert [c.release_group_id for c in found] == ["rg-1", "rg-2"]  # primero el probable
    best = found[0]
    assert (best.title, best.artist, best.year, best.kind) == (
        "Bigger, Better, Faster, More!", "4 Non Blondes", 1992, "Album")
    assert best.confident and not found[1].confident
    query = dict(net.calls[0].url.params)
    assert query["query"] == 'releasegroup:"Bigger, Better, Faster, More!" AND artist:"4 Non Blondes"'
    assert query["fmt"] == "json"


def test_search_by_track_dedupes_and_puts_compilations_last(tmp_path):
    net = Net({url_has("musicbrainz.org/ws/2/recording"): js(REC_SEARCH)})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "4 Non Blondes", "What's Up?")
    assert [(c.release_group_id, c.kind) for c in found] == [
        ("rg-1", "Album"), ("rg-4", "Single"), ("rg-3", "Compilation")]
    assert found[0].year == 1992 and found[0].via == "track"


def test_search_artists_and_wikidata_id(tmp_path):
    net = Net({url_has("ws/2/artist/art-1"): js(ARTIST_RELS),
               url_has("ws/2/artist/?"): js(ARTIST_SEARCH)})
    client = make_client(tmp_path, net)
    artists = musicbrainz.search_artists(client, "4 Non Blondes")
    assert artists[0].artist_id == "art-1" and artists[0].begin_year == 1989
    assert artists[0].similarity == 1.0
    assert musicbrainz.artist_wikidata_id(client, "art-1") == "Q215539"
    no_wd = Net({url_has("ws/2/artist/art-2"): js({"relations": [{"type": "wikidata", "url": {"resource": "x"}}]})})
    assert musicbrainz.artist_wikidata_id(make_client(tmp_path / "b", no_wd), "art-2") is None


# ---------------- Cover Art Archive ----------------
def test_cover_art_front_redirect_missing_and_invalid(tmp_path):
    def redirect(request):
        return httpx.Response(307, headers={"Location": "https://archive.org/download/mbid-1/front.jpg"})

    net = Net({url_has("coverartarchive.org/release-group/rg-1/front-500"): redirect,
               url_has("archive.org/download"): httpx.Response(200, content=JPEG,
                                                               headers={"content-type": "image/jpeg"}),
               url_has("rg-html"): httpx.Response(200, content=b"<html>no es imagen</html>")})
    client = make_client(tmp_path, net)
    assert coverart.fetch_front(client, "rg-1", 500) == JPEG  # siguió la redirección a archive.org
    assert coverart.fetch_front(client, "rg-sin-portada", 500) is None
    with pytest.raises(ValueError):
        coverart.fetch_front(client, "rg-html", 500)
    with pytest.raises(ValueError):
        coverart.fetch_front(client, "rg-1", 333)


def test_fetch_best_falls_back_to_smaller_size(tmp_path):
    net = Net({url_has("rg-1/front-500"): httpx.Response(200, content=JPEG)})
    assert coverart.fetch_best(make_client(tmp_path, net), "rg-1") == JPEG
    assert net.count("front-1200") == 1 and net.count("front-500") == 1


# ---------------- Wikipedia ----------------
def wiki_net(es=True, en=True):
    routes = {url_has("ws/2/artist/art-1"): js(ARTIST_RELS), url_has("wikidata.org/w/api.php"): js(WIKIDATA)}
    if es:
        routes[url_has("es.wikipedia.org/api/rest_v1/page/summary/4_Non_Blondes")] = js(wiki_summary("es"))
    if en:
        routes[url_has("en.wikipedia.org/api/rest_v1/page/summary/4_Non_Blondes_%28band%29")] = js(
            wiki_summary("en", "4 Non Blondes (band)", "American rock band"))
    return Net(routes)


def test_artist_info_via_wikidata_prefers_spanish_then_english(tmp_path):
    info = wikipedia.artist_info(make_client(tmp_path, wiki_net()), "4 Non Blondes", "art-1")
    assert (info.language, info.wikidata_id, info.mbid) == ("es", "Q215539", "art-1")
    assert info.summary.startswith("Resumen en es") and info.url.startswith("https://es.wikipedia.org")
    assert info.image_url == "https://upload.wikimedia.org/t.jpg"  # la miniatura, no la original
    only_en = wikipedia.artist_info(make_client(tmp_path / "b", wiki_net(es=False)), "4 Non Blondes", "art-1")
    assert only_en.language == "en" and "(band)" in only_en.name


def test_artist_info_search_fallback_accepts_only_musical_pages(tmp_path):
    def search(titles):
        return js({"query": {"search": [{"title": t} for t in titles]}})

    net = Net({
        url_has("es.wikipedia.org/w/api.php"): search(["Desambiguación X", "Planeta Rojo", "Los Tres"]),
        url_has("summary/Desambiguaci%C3%B3n_X"): js(wiki_summary("es", "Desambiguación X", type_="disambiguation")),
        url_has("summary/Planeta_Rojo"): js(wiki_summary("es", "Planeta Rojo", "cuerpo celeste del sistema solar")),
        url_has("summary/Los_Tres"): js(wiki_summary("es", "Los Tres", "banda chilena de rock")),
    })
    info = wikipedia.artist_info(make_client(tmp_path, net), "Los Tres")
    assert info and info.name == "Los Tres" and info.language == "es"
    # un artículo que no se parece al nombre buscado se descarta
    assert wikipedia.artist_info(make_client(tmp_path / "b", net), "Nombre Distinto") is None


# ---------------- orquestación ----------------
@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, '4 Non Blondes', '4 Non Blondes'),
        (2, 'Artista desconocido', 'Artista desconocido');
    INSERT INTO albums (id, title, album_artist_id) VALUES
        (1, 'Bigger, Better, Faster, More!', 1), (2, 'Álbum desconocido', 1), (3, 'X', 2);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES (1,'/1.mp3',1,1,'mp3','audio'),
        (2,'/2.mp3',1,1,'mp3','audio');
    INSERT INTO tracks (file_id, album_id, artist_id, title, track_no) VALUES
        (1, 1, 1, 'Pista', 1), (2, 2, 1, 'What''s Up?', 3);
    """)
    return c


def test_album_candidates_by_album_by_track_and_unknown_artist(tmp_path, conn):
    net = Net({url_has("release-group"): js(RG_SEARCH), url_has("ws/2/recording"): js(REC_SEARCH)})
    client = make_client(tmp_path, net)
    assert enrich.album_candidates(client, conn, 1)[0].release_group_id == "rg-1"
    by_track = enrich.album_candidates(client, conn, 2)  # "Sin álbum": busca por la canción
    assert by_track and by_track[0].via == "track" and net.count("recording") == 1
    assert enrich.album_candidates(client, conn, 3) == []  # artista desconocido: no se consulta
    assert enrich.album_candidates(client, conn, 999) == []


def test_preview_cover_is_cached_on_disk(tmp_path, conn, monkeypatch):
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    net = Net({url_has("rg-1/front-250"): httpx.Response(200, content=JPEG)})
    client = make_client(tmp_path, net)
    cand = musicbrainz.AlbumCandidate("rg-1", "T", "A", None, 1992, "Album", 100, 1.0)
    first = enrich.preview_cover(client, cand)
    assert first.read_bytes() == JPEG and first.parent == tmp_path / "cache" / "previews"
    assert enrich.preview_cover(client, cand) == first and len(net.calls) == 1
    missing = musicbrainz.AlbumCandidate("rg-x", "T", "A", None, None, "", 1, 1.0)
    assert enrich.preview_cover(client, missing) is None


def test_fetch_artist_info_persists_reuses_and_refreshes(tmp_path, conn):
    routes = dict(wiki_net().routes)
    routes[url_has("ws/2/artist/?")] = js(ARTIST_SEARCH)
    net = Net(routes)
    client = make_client(tmp_path, net)
    info = enrich.fetch_artist_info(client, conn, 1)
    assert info["bio_lang"] == "es" and info["mbid"] == "art-1" and info["bio_source"] == "Wikipedia"
    assert info["bio_url"].startswith("https://es.wikipedia.org") and info["info_fetched_at"]
    before = len(net.calls)
    assert enrich.fetch_artist_info(client, conn, 1)["bio"] == info["bio"]
    assert len(net.calls) == before  # reutiliza lo guardado, sin red
    enrich.fetch_artist_info(client, conn, 1, force=True)
    assert len(net.calls) > before or net.count("art-1") >= 1  # force vuelve a consultar (o a la caché)
    assert enrich.fetch_artist_info(client, conn, 2) is None  # artista desconocido


def test_low_confidence_artist_match_is_not_used_for_mbid(tmp_path, conn):
    weak = {"artists": [{"id": "art-9", "score": 99, "name": "Cuatro No Rubias", "type": "Group"}]}
    net = Net({url_has("ws/2/artist/?"): js(weak),
               url_has("es.wikipedia.org/w/api.php"): js({"query": {"search": []}}),
               url_has("en.wikipedia.org/w/api.php"): js({"query": {"search": []}})})
    assert enrich.fetch_artist_info(make_client(tmp_path, net), conn, 1) is None
    assert net.count("art-9") == 0  # no se siguió un mbid dudoso


# ---------------- esquema y CLI ----------------
def test_schema_v4_has_artist_info_columns():
    c = connect(":memory:")
    cols = {r["name"] for r in c.execute("PRAGMA table_info(artists)")}
    assert {"mbid", "bio", "bio_source", "bio_url", "bio_lang", "image_url", "info_fetched_at"} <= cols


def test_cli_online_toggle_and_offline_message(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.delenv("SONOTECA_OFFLINE", raising=False)
    monkeypatch.delenv("SONOTECA_CONTACT", raising=False)
    assert main(["online", "status"]) == 0
    assert "Modo sin conexión: SÍ" in capsys.readouterr().out
    assert main(["online", "on"]) == 0
    out = capsys.readouterr().out
    assert "Modo sin conexión: no" in out and "--contact" in out  # avisa que falta identificarse
    assert main(["online", "on", "--contact", "yo@correo.com"]) == 0
    assert "yo@correo.com" in capsys.readouterr().out
    assert main(["online", "off"]) == 0
    assert "Modo sin conexión: SÍ" in capsys.readouterr().out
    # con el modo sin conexión, las consultas avisan en vez de fallar
    db = tmp_path / "t.db"
    seed = connect(db)
    seed.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'X', 'X');
    INSERT INTO albums (id, title, album_artist_id) VALUES (1, 'Y', 1);
    """)
    seed.close()
    assert main(["--db", str(db), "find-album", "1"]) == 3
    assert "Modo sin conexión activo" in capsys.readouterr().err
    assert json.loads((tmp_path / "datos" / "settings.json").read_text())["offline"] is True


def test_only_a_clear_winner_is_marked_probable(tmp_path):
    """Caso real (Jagged Little Pill): las versiones en vivo y acústica no son "probables"."""
    def rg(i, title, score, kind="Album"):
        return {"id": i, "score": score, "primary-type": kind, "title": title,
                "first-release-date": "1995", "artist-credit": CREDIT}

    results = {"release-groups": [
        rg("a", "Jagged Little Pill", 100), rg("b", "Jagged Little Pill, Live", 93),
        rg("c", "Jagged Little Pill (acoustic)", 93),
        rg("d", "Jagged Little Pill (Original Broadway Cast Recording)", 81),
        rg("e", "Live @ VH1.com Presents Jagged Little Pill Acoustic", 78, "Broadcast")]}
    net = Net({url_has("release-group"): js(results)})
    found = musicbrainz.search_albums(make_client(tmp_path, net), "4 Non Blondes", "Jagged Little Pill")
    assert found[0].release_group_id == "a"
    assert [c.confident for c in found] == [True, False, False, False, False]
    # dos ediciones con el mismo título empatan: ninguna se marca
    twin = {"release-groups": [rg("x", "Disco", 100), rg("y", "Disco", 100)]}
    net2 = Net({url_has("release-group"): js(twin)})
    both = musicbrainz.search_albums(make_client(tmp_path / "b", net2), "4 Non Blondes", "Disco")
    assert not any(c.confident for c in both)
    # y una búsqueda por canción nunca asegura el álbum
    net3 = Net({url_has("ws/2/recording"): js(REC_SEARCH)})
    assert not any(c.confident for c in musicbrainz.search_by_track(
        make_client(tmp_path / "c", net3), "4 Non Blondes", "What's Up?"))


def test_cli_notes_when_results_come_from_cache_while_offline(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("SONOTECA_OFFLINE", raising=False)
    db = tmp_path / "t.db"
    seed = connect(db)
    seed.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, '4 Non Blondes', '4 Non Blondes'),
                                                     (2, 'Otro', 'Otro');
    INSERT INTO albums (id, title, album_artist_id) VALUES (1, 'Bigger, Better, Faster, More!', 1),
                                                           (2, 'Disco sin consultar', 2);
    """)
    # una consulta previa con conexión deja la respuesta en la caché local (misma que usa la CLI)
    real_time = FakeTime()
    real_time.now = __import__("time").time()  # la CLI usa el reloj real: la caché debe parecer reciente
    online = make_client(tmp_path, Net({url_has("release-group"): js(RG_SEARCH)}), time=real_time)
    online._cache_dir = tmp_path / "cache" / "http"
    enrich.album_candidates(online, seed, 1)
    seed.close()
    # sin conexión (por defecto): el resultado guardado se muestra, avisando de dónde viene
    assert main(["--db", str(db), "find-album", "1"]) == 0
    out = capsys.readouterr().out
    assert "Bigger, Better, Faster, More!" in out and "<- coincidencia probable" in out
    assert "guardado de una consulta anterior" in out
    # lo que nunca se consultó no se puede traer sin conexión
    assert main(["--db", str(db), "find-album", "2"]) == 3
    assert "Modo sin conexión activo" in capsys.readouterr().err


# ---------------- búsqueda por canción (caso real: Wheatus - Teenage Dirtbag) ----------------
def _rel(i, title, date, kind="Album", secondary=None):
    group = {"id": f"rg-{i}", "primary-type": kind, "title": title}
    if secondary:
        group["secondary-types"] = secondary
    return {"id": f"rel-{i}", "title": title, "date": date, "release-group": group}


WHEATUS_REC = {"recordings": [
    {"id": "rec-orig", "score": 100, "title": "Teenage Dirtbag", "length": 247000,
     "artist-credit": [{"name": "Wheatus", "artist": {"id": "art-w", "name": "Wheatus"}}],
     "releases": [_rel(1, "Endsessions 3", "2001"), _rel(2, "Mr Music Hits 2001-05", "2001"),
                  _rel(3, "Dad Songs", "2017", secondary=["Compilation"]),
                  _rel(4, "Wheatus", "2000-08-14")]},
    {"id": "rec-live", "score": 100, "title": "Teenage Dirtbag", "length": 331000,
     "artist-credit": [{"name": "Wheatus", "artist": {"id": "art-w", "name": "Wheatus"}}],
     "releases": [_rel(5, "Live in Europe", "2003")]},
]}


def titles_of(found):
    return [c.title for c in found]


def test_track_search_puts_original_album_first_using_duration_and_year(tmp_path):
    net = Net({url_has("ws/2/recording"): js(WHEATUS_REC)})
    client = make_client(tmp_path, net)
    found = musicbrainz.search_by_track(client, "Wheatus", "Teenage Dirtbag", duration=247.0, year=2000)
    assert found[0].title == "Wheatus" and found[0].length_match and found[0].year == 2000
    # álbumes de estudio primero (el más antiguo y con la misma duración); la recopilación al final
    assert titles_of(found) == ["Wheatus", "Endsessions 3", "Mr Music Hits 2001-05", "Live in Europe",
                                "Dad Songs"]
    assert [c.length_match for c in found] == [True, True, True, False, True]


def test_track_search_without_hints_prefers_albums_then_earliest(tmp_path):
    net = Net({url_has("ws/2/recording"): js(WHEATUS_REC)})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "Wheatus", "Teenage Dirtbag")
    assert titles_of(found)[0] == "Wheatus" and found[-1].kind == "Compilation"
    assert not any(c.length_match for c in found)


def test_track_search_tries_official_albums_first_then_falls_back(tmp_path):
    queries = []

    def responder(request):
        query = request.url.params["query"]
        queries.append(query)
        if "status:official" in query:
            return js({"recordings": []})  # el filtro estricto no encontró nada
        return js(WHEATUS_REC)

    net = Net({url_has("ws/2/recording"): responder})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "Wheatus", "Teenage Dirtbag")
    assert found and len(queries) == 2
    assert "status:official AND primarytype:album" in queries[0]
    assert "status:official" not in queries[1]


def test_track_search_survives_a_rejected_strict_query(tmp_path):
    def responder(request):
        return httpx.Response(400) if "status:official" in request.url.params["query"] else js(WHEATUS_REC)

    net = Net({url_has("ws/2/recording"): responder})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "Wheatus", "Teenage Dirtbag")
    assert titles_of(found)[0] == "Wheatus"


def test_unknown_album_search_passes_track_duration_and_year(tmp_path):
    c = connect(":memory:")
    c.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'Wheatus', 'Wheatus');
    INSERT INTO albums (id, title, album_artist_id, year) VALUES (1, 'Álbum desconocido', 1, 2000);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES (1, '/1.mp3', 1, 1, 'mp3', 'audio');
    INSERT INTO tracks (file_id, album_id, artist_id, title, year, duration)
        VALUES (1, 1, 1, 'Teenage Dirtbag', 2000, 247.3);
    """)
    net = Net({url_has("ws/2/recording"): js(WHEATUS_REC)})
    found = enrich.album_candidates(make_client(tmp_path, net), c, 1)
    assert found[0].title == "Wheatus" and found[0].length_match


def test_cli_explains_track_based_results(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    candidates = [
        musicbrainz.AlbumCandidate("rg-4", "Wheatus", "Wheatus", "a", 2000, "Album", 100, 1.0,
                                   via="track", length_match=True),
        musicbrainz.AlbumCandidate("rg-5", "Live in Europe", "Wheatus", "a", 2003, "Album", 100, 1.0,
                                   via="track")]
    monkeypatch.setattr(enrich, "album_candidates", lambda *a, **k: candidates)
    assert main(["--db", str(tmp_path / "t.db"), "find-album", "1"]) == 0
    out = capsys.readouterr().out
    assert "Pista sin álbum" in out and "1. Wheatus - Wheatus (2000, Album)" in out
    assert "<- misma duración" in out.split("2. Live in Europe")[0]
    assert "puntaje" not in out  # en la búsqueda por canción ese número no distingue nada


# ---------------- correcciones tras la prueba real con Wheatus / Village People ----------------
def test_soundtracks_and_live_albums_rank_after_the_studio_album(tmp_path):
    rec = {"recordings": [{"id": "r1", "score": 100, "title": "Teenage Dirtbag", "length": 247000,
           "artist-credit": [{"name": "Wheatus", "artist": {"id": "art-w", "name": "Wheatus"}}],
           "releases": [
               _rel(10, "Songs From Dawson's Creek", "2000", secondary=["Soundtrack"]),
               _rel(11, "Live at the Masonic Temple", "2000", secondary=["Live"]),
               _rel(12, "Wheatus", "2000-08-14")]}]}
    net = Net({url_has("ws/2/recording"): js(rec)})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "Wheatus", "Teenage Dirtbag",
                                        duration=247, year=2000)
    assert [(c.title, c.kind) for c in found] == [
        ("Wheatus", "Album"), ("Songs From Dawson's Creek", "Soundtrack"),
        ("Live at the Masonic Temple", "Live")]


def test_clean_title_and_tokens_clause():
    assert musicbrainz.clean_title("Y.M.C.A. (Remastered 2010)") == "Y.M.C.A."
    assert musicbrainz.clean_title("Careless Whisper - Radio Edit") == "Careless Whisper"
    assert musicbrainz.clean_title("Song [Live]") == "Song"
    assert musicbrainz.clean_title("(Intro)") == "(Intro)"  # si no quedara nada, se deja igual
    assert musicbrainz.tokens_clause("artist", "The Village People") == "artist:(village AND people)"
    assert musicbrainz.tokens_clause("artist", "Wham!") == "artist:(wham)"
    assert musicbrainz.tokens_clause("artist", "4 Non Blondes") == "artist:(4 AND non AND blondes)"
    assert musicbrainz.tokens_clause("artist", "!!!") == ""


def test_track_search_finds_artist_written_with_a_leading_article(tmp_path):
    queries = []

    def responder(request):
        query = request.url.params["query"]
        queries.append(query)
        # MusicBrainz solo conoce "Village People": la frase exacta "The Village People" no coincide
        return js(WHEATUS_REC) if "artist:(village AND people)" in query else js({"recordings": []})

    net = Net({url_has("ws/2/recording"): responder})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "The Village People",
                                        "Y.M.C.A. (Remastered)")
    assert found
    assert 'recording:"Y.M.C.A."' in queries[0] and "artist:(village AND people)" in queries[0]


def test_track_search_ladder_reaches_the_word_based_query(tmp_path):
    queries = []

    def responder(request):
        queries.append(request.url.params["query"])
        return js(WHEATUS_REC) if request.url.params["query"].startswith("recording:(") else js({})

    net = Net({url_has("ws/2/recording"): responder})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "Wheatus", "Teenage Dirtbag")
    assert found and len(queries) == 3
    assert "status:official" in queries[0] and "status:official" not in queries[1]
    assert queries[2].startswith("recording:(teenage AND dirtbag)")


def test_search_albums_retries_with_words_when_the_exact_phrase_finds_nothing(tmp_path):
    queries = []

    def responder(request):
        query = request.url.params["query"]
        queries.append(query)
        return js(RG_SEARCH) if "artist:(" in query else js({"release-groups": []})

    net = Net({url_has("release-group"): responder})
    found = musicbrainz.search_albums(make_client(tmp_path, net), "The 4 Non Blondes", "Bigger Better")
    assert found and len(queries) == 2 and "artist:(4 AND non AND blondes)" in queries[1]


def _unknown_album_db():
    c = connect(":memory:")
    c.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'Wheatus', 'Wheatus');
    INSERT INTO albums (id, title, album_artist_id, year) VALUES (1, 'Álbum desconocido', 1, 2000);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES
        (1, '/1.mp3', 1, 1, 'mp3', 'audio'), (2, '/2.mp3', 1, 1, 'mp3', 'audio');
    INSERT INTO tracks (id, file_id, album_id, artist_id, title, year, duration, track_no) VALUES
        (1, 1, 1, 1, 'Teenage Dirtbag', 2000, 247.3, 1), (2, 2, 1, 1, 'A Little Respect', 2000, 215, 2);
    """)
    return c


def test_pick_track_and_explicit_track_choice(tmp_path):
    c = _unknown_album_db()
    assert enrich.pick_track(c, 1)["title"] == "Teenage Dirtbag"  # por defecto, la primera
    assert enrich.pick_track(c, 1, 2)["title"] == "A Little Respect"
    assert enrich.pick_track(c, 1, 999) is None
    queries = []
    net = Net({url_has("ws/2/recording"): lambda r: (queries.append(r.url.params["query"]), js(WHEATUS_REC))[1]})
    enrich.album_candidates(make_client(tmp_path, net), c, 1, track_id=2)
    assert 'recording:"A Little Respect"' in queries[0]


def test_cli_says_which_song_it_is_searching_for(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    db = tmp_path / "t.db"
    seed = connect(db)
    seed.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'Wheatus', 'Wheatus');
    INSERT INTO albums (id, title, album_artist_id, year) VALUES (1, 'Álbum desconocido', 1, 2000);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES (1, '/1.mp3', 1, 1, 'mp3', 'audio');
    INSERT INTO tracks (id, file_id, album_id, artist_id, title, year, duration, track_no)
        VALUES (1, 1, 1, 1, 'Teenage Dirtbag', 2000, 247.3, 1);
    """)
    seed.close()
    seen = {}

    def fake(client, conn, album_id, limit=6, track_id=None):
        seen["track_id"] = track_id
        return []

    monkeypatch.setattr(enrich, "album_candidates", fake)
    assert main(["--db", str(db), "find-album", "1", "--track", "1"]) == 0
    out = capsys.readouterr().out
    assert "Buscando por la canción «Teenage Dirtbag» de Wheatus (4:07, año 2000) [pista 1]" in out
    assert seen["track_id"] == 1


def test_word_queries_keep_accents():
    assert musicbrainz.tokens_clause("artist", "José Luis Perales") == "artist:(josé AND luis AND perales)"
    assert musicbrainz.tokens_clause("artist", "Beyoncé") == "artist:(beyoncé)"
    assert musicbrainz.tokens_clause("recording", "Guns N' Roses") == "recording:(guns AND n AND roses)"


# ---------------- tercera prueba real: Village People, Within Temptation, find-track ----------------
def test_studio_album_ranks_before_a_single_even_if_only_the_single_matches_duration(tmp_path):
    """Caso real "Macho Man": el sencillo duraba igual, pero se busca el álbum para los tags."""
    credit = [{"name": "Village People", "artist": {"id": "a-vp", "name": "Village People"}}]
    rec = {"recordings": [
        {"id": "r-single", "score": 100, "title": "Macho Man", "length": 207000,
         "artist-credit": credit, "releases": [_rel(1, "Macho Man / Key West", "1978", "Single")]},
        {"id": "r-album", "score": 100, "title": "Macho Man", "length": 231000,
         "artist-credit": credit, "releases": [_rel(2, "Macho Man", "1978-08")]}]}
    net = Net({url_has("ws/2/recording"): js(rec)})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "The Village People", "Macho Man",
                                        duration=207.0)
    assert [(c.title, c.kind, c.length_match) for c in found] == [
        ("Macho Man", "Album", False), ("Macho Man / Key West", "Single", True)]


def test_year_is_the_earliest_among_all_releases_of_the_same_album(tmp_path):
    """Caso real "The Heart of Everything": salía 2024 por una reedición, y el álbum es de 2007."""
    credit = [{"name": "Within Temptation", "artist": {"id": "a-wt", "name": "Within Temptation"}}]
    rec = {"recordings": [{"id": "r1", "score": 100, "title": "Our Solemn Hour", "length": 256000,
           "artist-credit": credit, "releases": [
               _rel(7, "The Heart of Everything", "2024-03-01"),
               _rel(7, "The Heart of Everything", "2007-03-12"),
               {"id": "x", "title": "The Heart of Everything", "release-group":
                {"id": "rg-7", "primary-type": "Album", "title": "The Heart of Everything"}}]}]}
    net = Net({url_has("ws/2/recording"): js(rec)})
    found = musicbrainz.search_by_track(make_client(tmp_path, net), "Within Temptation",
                                        "Our solemn hour (Sanctus Espiritus)", duration=256)
    assert len(found) == 1 and found[0].year == 2007 and found[0].length_match
    # el paréntesis del título no estorba la búsqueda
    assert 'recording:"Our solemn hour"' in net.calls[0].url.params["query"]


def test_track_search_asks_for_100_recordings(tmp_path):
    net = Net({url_has("ws/2/recording"): js(WHEATUS_REC)})
    musicbrainz.search_by_track(make_client(tmp_path, net), "Wheatus", "Teenage Dirtbag")
    assert net.calls[0].url.params["limit"] == "100"


def _track_db():
    c = connect(":memory:")
    c.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'George Michael', 'George Michael'),
                                                     (2, 'Artista desconocido', 'x');
    INSERT INTO albums (id, title, album_artist_id, year) VALUES (1, 'Álbum desconocido', 1, 1984),
                                                                 (2, 'Álbum desconocido', 2, NULL);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES
        (1, '/1.mp3', 1, 1, 'mp3', 'audio'), (2, '/2.mp3', 1, 1, 'mp3', 'audio');
    INSERT INTO tracks (id, file_id, album_id, artist_id, title, year, duration) VALUES
        (7, 1, 1, 1, 'Careless whisper', 1984, 300.0), (8, 2, 2, 2, 'Sin artista', NULL, 100);
    """)
    return c


def test_track_candidates_use_the_tracks_own_data(tmp_path):
    queries = []
    net = Net({url_has("ws/2/recording"): lambda r: (queries.append(r.url.params["query"]), js(REC_SEARCH))[1]})
    client = make_client(tmp_path, net)
    c = _track_db()
    assert enrich.track_candidates(client, c, 7)
    assert 'recording:"Careless whisper"' in queries[0] and "artist:(george AND michael)" in queries[0]
    assert enrich.track_candidates(client, c, 8) == []  # artista desconocido
    assert enrich.track_candidates(client, c, 999) == []


def test_cli_find_track_prints_the_song_caps_output_and_all_shows_everything(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    db = tmp_path / "t.db"
    seed = connect(db)
    seed.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'George Michael', 'George Michael');
    INSERT INTO albums (id, title, album_artist_id, year) VALUES (1, 'Álbum desconocido', 1, 1984);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES (1, '/1.mp3', 1, 1, 'mp3', 'audio');
    INSERT INTO tracks (id, file_id, album_id, artist_id, title, year, duration)
        VALUES (7, 1, 1, 1, 'Careless whisper', 1984, 300.0);
    """)
    seed.close()
    many = [musicbrainz.AlbumCandidate(f"rg-{i}", f"Disco {i}", "George Michael", "a", 1984 + i, "Album",
                                       100, 1.0, via="track", length_match=(i == 0)) for i in range(12)]
    monkeypatch.setattr(enrich, "track_candidates", lambda *a, **k: many)
    assert main(["--db", str(db), "find-track", "7"]) == 0
    out = capsys.readouterr().out
    assert "Buscando por la canción «Careless whisper» de George Michael (5:00, año 1984) [pista 7]" in out
    assert "10. Disco 9" in out and "11. Disco 10" not in out and "... y 2 más" in out
    assert main(["--db", str(db), "find-track", "7", "--all"]) == 0
    assert "12. Disco 11" in capsys.readouterr().out
    assert main(["--db", str(db), "find-track", "999"]) == 0
    assert "No existe la pista 999" in capsys.readouterr().out
