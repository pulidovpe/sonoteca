from conftest import make_cover, make_m4a, make_mp3, needs_ffmpeg

from musicapp.core.covers import (
    album_cover_source,
    artist_cover_album,
    extract_embedded_cover,
    find_folder_cover,
)
from musicapp.core.db import connect
from musicapp.core.scanner import scan

pytestmark = needs_ffmpeg

JPEG_MAGIC = b"\xff\xd8"


def test_extract_from_mp3_and_m4a(tmp_path):
    cover = make_cover(tmp_path / "c.jpg")
    mp3 = make_mp3(tmp_path / "a.mp3", cover, title="A")
    m4a = make_m4a(tmp_path / "a.m4a", cover, title="A")
    assert extract_embedded_cover(mp3).startswith(JPEG_MAGIC)
    assert extract_embedded_cover(m4a).startswith(JPEG_MAGIC)


def test_extract_without_cover_returns_none(tmp_path):
    assert extract_embedded_cover(make_mp3(tmp_path / "a.mp3", title="A")) is None
    bad = tmp_path / "roto.mp3"
    bad.write_bytes(b"basura" * 20)
    assert extract_embedded_cover(bad) is None


def test_find_folder_cover(tmp_path):
    assert find_folder_cover(tmp_path) is None
    make_cover(tmp_path / "Folder.JPG")
    assert find_folder_cover(tmp_path).name == "Folder.JPG"


def test_album_cover_source_prefers_embedded_then_folder(tmp_path):
    conn = connect(":memory:")
    cover = make_cover(tmp_path / "x.jpg")
    make_mp3(tmp_path / "A/1.mp3", cover, title="t1", artist="X", album="Con portada")
    make_mp3(tmp_path / "B/1.mp3", title="t2", artist="X", album="Con carpeta")
    make_cover(tmp_path / "B/cover.jpg")
    make_mp3(tmp_path / "C/1.mp3", title="t3", artist="X", album="Sin nada")
    scan(conn, tmp_path)
    ids = {r["title"]: r["id"] for r in conn.execute("SELECT id, title FROM albums")}
    assert album_cover_source(conn, ids["Con portada"])[0] == "embedded"
    assert album_cover_source(conn, ids["Con carpeta"])[0] == "folder"
    assert album_cover_source(conn, ids["Sin nada"]) is None


def test_artist_cover_prefers_album_with_embedded_cover(tmp_path):
    conn = connect(":memory:")
    cover = make_cover(tmp_path / "x.jpg")
    make_mp3(tmp_path / "A/1.mp3", title="t1", artist="X", album="Sin portada", date="1980")
    make_mp3(tmp_path / "B/1.mp3", cover, title="t2", artist="X", album="Con portada", date="1999")
    make_mp3(tmp_path / "C/1.mp3", title="t3", artist="Y", album="Otro")
    scan(conn, tmp_path)
    x = conn.execute("SELECT id FROM artists WHERE name='X'").fetchone()[0]
    expected = conn.execute("SELECT id FROM albums WHERE title='Con portada'").fetchone()[0]
    assert artist_cover_album(conn, x) == expected  # aunque el otro álbum sea más antiguo
    assert artist_cover_album(conn, 9999) is None


def _library_with_covers(tmp_path):
    """A: dos álbumes con la MISMA portada; B: otra portada; C: sin portada."""
    red = make_cover(tmp_path / "red.jpg", "0xcc3333")
    blue = make_cover(tmp_path / "blue.jpg", "0x3333cc")
    root = tmp_path / "music"
    make_mp3(root / "a1/1.mp3", red, title="A1", artist="Uno", album="Rojo 1")
    make_mp3(root / "a2/1.mp3", red, title="A2", artist="Uno", album="Rojo 2")
    make_mp3(root / "b/1.mp3", blue, title="B", artist="Dos", album="Azul")
    make_mp3(root / "c/1.mp3", title="C", artist="Tres", album="Sin imagen")
    conn = connect(":memory:")
    scan(conn, root)
    by_title = {r["title"]: r["id"] for r in conn.execute("SELECT id, title FROM tracks")}
    return conn, by_title


def test_current_cover_state(tmp_path):
    from musicapp.core.covers import current_cover_state

    conn, t = _library_with_covers(tmp_path)
    one = current_cover_state(conn, [t["B"]])
    assert one["state"] == "single" and one["albumId"]
    # dos álbumes con exactamente la misma imagen cuentan como una sola portada
    same = current_cover_state(conn, [t["A1"], t["A2"]])
    assert same["state"] == "single"
    # portadas distintas, o unas con portada y otras sin ella: "varias"
    assert current_cover_state(conn, [t["A1"], t["B"]])["state"] == "mixed"
    assert current_cover_state(conn, [t["A1"], t["C"]])["state"] == "mixed"
    # ninguna portada
    assert current_cover_state(conn, [t["C"]]) == {"state": "none", "albumId": 0}
    assert current_cover_state(conn, []) == {"state": "none", "albumId": 0}


def test_artist_has_image_and_artist_track_ids(tmp_path, monkeypatch):
    from musicapp.core import library
    from musicapp.core.covers import artist_has_image

    monkeypatch.setenv("MUSICAPP_DATA_DIR", str(tmp_path / "datos"))
    monkeypatch.setenv("MUSICAPP_CACHE_DIR", str(tmp_path / "cache"))
    conn, t = _library_with_covers(tmp_path)
    ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM artists")}
    assert artist_has_image(conn, ids["Uno"]) is True      # portada de uno de sus álbumes
    assert artist_has_image(conn, ids["Tres"]) is False    # nada que mostrar
    photo = tmp_path / "datos" / "artists" / f"{ids['Tres']}.jpg"
    make_cover(photo)
    assert artist_has_image(conn, ids["Tres"]) is True     # foto descargada
    assert sorted(library.list_artist_track_ids(conn, ids["Uno"])) == sorted([t["A1"], t["A2"]])
