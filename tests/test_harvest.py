"""Descarga automática de portadas/fotos: plan, criterios estrictos y reintentos."""
import sqlite3
from types import SimpleNamespace

import pytest

from sonoteca.core.db import connect
from sonoteca.online import enrich, harvest, musicbrainz, wikipedia
from sonoteca.online.http import OfflineError

IDS = {}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 40


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("SONOTECA_CACHE_DIR", str(tmp_path / "cache"))
    c = connect(tmp_path / "h.db")
    c.row_factory = sqlite3.Row

    def artist(name):
        return c.execute("INSERT INTO artists (name, sort_name) VALUES (?, ?)", (name, name.lower())).lastrowid

    def album(title, artist_id):
        return c.execute("INSERT INTO albums (title, album_artist_id) VALUES (?, ?)", (title, artist_id)).lastrowid

    def track(album_id, artist_id, inferred=0, n=[0]):
        n[0] += 1
        fid = c.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?, 1, 1, 'mp3', 'audio')",
                        (str(tmp_path / f"m{n[0]}.mp3"),)).lastrowid
        c.execute("INSERT INTO tracks (file_id, album_id, artist_id, title, duration, inferred) VALUES (?,?,?,?,1,?)",
                  (fid, album_id, artist_id, f"T{n[0]}", inferred))

    good = artist("Buena Banda")
    track(album("Disco Claro", good), good)                             # bien identificado
    track(album("Disco Deducido", good), good, inferred=1)              # deducido del nombre de archivo: no
    track(album("\u00c1lbum desconocido", good), good)                   # sin álbum: no
    comp = artist("Varios Artistas")
    track(album("Recopilatorio", comp), comp)                           # compilación: sin ficha de artista
    IDS.update(good=good, comp=comp)
    return c


def test_plan_only_includes_well_identified_missing_items(conn):
    p = harvest.plan(conn)
    titles = {conn.execute("SELECT title FROM albums WHERE id = ?", (i,)).fetchone()[0] for i in p.albums}
    assert titles == {"Disco Claro", "Recopilatorio"}
    assert p.artists == [IDS["good"]]
    assert p.seconds == pytest.approx(2 * harvest.ALBUM_SECONDS + harvest.ARTIST_SECONDS)


def test_format_duration():
    assert harvest.format_duration(20) == "menos de un minuto"
    assert harvest.format_duration(12 * 60) == "unos 12 minutos"
    assert harvest.format_duration(2.5 * 3600) == "unas 2 h 30 min"


class FakeClient:
    def get_bytes(self, url, **kw):
        return PNG, "image/png"


def _cand(confident):
    return musicbrainz.AlbumCandidate("rg1", "Disco Claro", "Buena Banda", None, 2000, "Album", 100, 1.0,
                                      confident=confident)


def test_run_downloads_confident_cover_and_skips_unsure(conn, monkeypatch):
    monkeypatch.setattr(enrich, "album_candidates", lambda *a, **k: [_cand(True)])
    monkeypatch.setattr(enrich, "download_cover", lambda *a, **k: PNG)
    monkeypatch.setattr(musicbrainz, "search_artists", lambda *a, **k: [
        SimpleNamespace(artist_id="mb1", name="Buena Banda", similarity=1.0, mb_score=100)])
    monkeypatch.setattr(wikipedia, "artist_info", lambda *a, **k: wikipedia.ArtistInfo(
        name="Buena Banda", summary="Una banda.", url="u", language="es", image_url="http://x/f.png", mbid="mb1"))
    work = harvest.plan(conn)
    out = harvest.run(conn, FakeClient(), work)
    assert out["covers"] == 2 and out["artists"] == 1 and out["errors"] == 0
    row = conn.execute("SELECT cover_path, cover_checked_at FROM albums WHERE title = 'Disco Claro'").fetchone()
    assert row["cover_path"].endswith(".png") and "downloaded" in row["cover_path"] and row["cover_checked_at"]
    assert (conn.execute("SELECT bio FROM artists WHERE id = ?", (IDS["good"],)).fetchone()[0]) == "Una banda."
    assert harvest.plan(conn).total == 0                  # lo hecho no se vuelve a buscar
    # la portada descargada solo se usa si no hay otra: ahora el álbum ya "tiene" portada
    from sonoteca.core.covers import album_cover_source
    assert album_cover_source(conn, work.albums[0])[0] == "folder"


def test_unsure_matches_are_left_alone_and_not_retried(conn, monkeypatch):
    monkeypatch.setattr(enrich, "album_candidates", lambda *a, **k: [_cand(False)])
    monkeypatch.setattr(musicbrainz, "search_artists", lambda *a, **k: [
        SimpleNamespace(artist_id="mb1", name="Otro", similarity=0.5, mb_score=60)])
    out = harvest.run(conn, FakeClient(), harvest.plan(conn))
    assert out["covers"] == 0 and out["artists"] == 0 and out["unsure"] == 3
    assert conn.execute("SELECT cover_path FROM albums WHERE title = 'Disco Claro'").fetchone()[0] is None
    assert harvest.plan(conn).total == 0                  # se intentó: no insistir hasta dentro de 30 días


def test_offline_and_cancel_and_error_streak(conn, monkeypatch):
    def offline(*a, **k):
        raise OfflineError()
    monkeypatch.setattr(enrich, "album_candidates", offline)
    out = harvest.run(conn, FakeClient(), harvest.plan(conn))
    assert out["offline"] and out["done"] == 0 and harvest.plan(conn).total == 3   # nada se marcó como intentado
    out = harvest.run(conn, FakeClient(), harvest.plan(conn), cancelled=lambda: True)
    assert out["cancelled"] and out["done"] == 0

    from sonoteca.online.http import OnlineError

    def broken(*a, **k):
        raise OnlineError("sin red")
    monkeypatch.setattr(enrich, "album_candidates", broken)
    monkeypatch.setattr(musicbrainz, "search_artists", broken)
    out = harvest.run(conn, FakeClient(), harvest.plan(conn))
    assert out["errors"] == 3 and harvest.plan(conn).total == 3                     # fallos de red: se podrá reintentar
