import os

import pytest
from conftest import make_mp3, needs_ffmpeg

from sonoteca.core import library
from sonoteca.core.db import connect
from sonoteca.core.scanner import scan, sort_name

pytestmark = needs_ffmpeg


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_sort_name():
    assert sort_name("The Beatles") == "Beatles, The"
    assert sort_name("Soda Stereo") == "Soda Stereo"


def test_first_scan_and_queries(conn, library_dir):
    r = scan(conn, library_dir)
    assert (r.added, r.updated, r.unchanged, r.errors) == (6, 0, 0, [])

    s = library.stats(conn)
    assert s["tracks"] == 6 and s["videos"] == 1
    names = [a["name"] for a in library.list_artists(conn)]
    assert "The Beatles" in names and "Soda Stereo" in names

    albums = {a["title"]: a for a in library.list_albums(conn)}
    assert albums["Abbey Road"]["year"] == 1969 and albums["Abbey Road"]["tracks"] == 2
    assert albums["Revolver"]["year"] == 1966

    # orden: artista, luego año (cronológico)
    assert [a["title"] for a in library.list_albums(conn, decade=1960)] == ["Revolver",
                                                                            "Abbey Road"]
    assert [a["title"] for a in library.list_albums(conn, year=1986)] == ["Signos"]
    assert [y["year"] for y in library.list_years(conn)] == [1966, 1969, 1986]

    abbey = albums["Abbey Road"]["id"]
    assert [t["title"] for t in library.list_tracks(conn, album_id=abbey)] == [
        "Come Together", "Something"]


def test_search_is_case_insensitive_and_escapes(conn, library_dir):
    scan(conn, library_dir)
    assert len(library.search(conn, "beatles")) == 3
    assert len(library.search(conn, "persiana")) == 1
    assert library.search(conn, "100%") == []  # '%' no actúa como comodín


def test_rescan_is_incremental(conn, library_dir):
    scan(conn, library_dir)
    r = scan(conn, library_dir)
    assert (r.added, r.updated, r.unchanged) == (0, 0, 6)


def test_modified_file_is_updated(conn, library_dir):
    scan(conn, library_dir)
    p = library_dir / "suelto.mp3"
    make_mp3(p, title="Ahora con título", artist="Alguien", album="Nuevo")  # reemplaza el archivo
    os.utime(p, ns=(1, 1))  # fuerza mtime distinto
    r = scan(conn, library_dir)
    assert (r.added, r.updated, r.unchanged) == (0, 1, 5)
    assert library.search(conn, "Ahora con título")[0]["artist"] == "Alguien"
    # el álbum/artista "desconocido" quedó huérfano y se limpia
    assert "Artista desconocido" not in [a["name"] for a in library.list_artists(conn)]


def test_deleted_file_is_removed(conn, library_dir):
    scan(conn, library_dir)
    (library_dir / "Beatles/Revolver/01.mp3").unlink()
    r = scan(conn, library_dir)
    assert r.removed == 1 and r.unchanged == 5
    assert "Revolver" not in [a["title"] for a in library.list_albums(conn)]


def test_corrupt_file_reported_not_fatal(conn, library_dir):
    (library_dir / "roto.mp3").write_bytes(b"basura" * 50)
    r = scan(conn, library_dir)
    assert r.added == 6 and len(r.errors) == 1
    assert r.errors[0][0].name == "roto.mp3"


def test_hidden_macos_files_ignored(conn, library_dir):
    (library_dir / "._suelto.mp3").write_bytes(b"\x00\x05\x16\x07")
    r = scan(conn, library_dir)
    assert r.errors == [] and r.added == 6


def test_not_a_directory(conn, tmp_path):
    with pytest.raises(NotADirectoryError):
        scan(conn, tmp_path / "no_existe")


def test_untagged_files_are_inferred_and_listed_as_incomplete(conn, library_dir):
    make_mp3(library_dir / "Variadas/2002-t.A.T.u. - All The Things She Said.mp3")
    make_mp3(library_dir / "Variadas/2000-Wheatus - Teenage Dirtbag.mp3")
    # un artista ya existente con otra capitalización debe fusionarse (NOCASE)
    make_mp3(library_dir / "Tatu/x.mp3", title="Otra", artist="T.a.t.u.", album="The Best")
    scan(conn, library_dir)

    tatu = [a for a in library.list_artists(conn) if a["name"].lower() == "t.a.t.u."]
    assert len(tatu) == 1 and tatu[0]["tracks"] == 2

    wheatus = library.search(conn, "Teenage")[0]
    assert (wheatus["artist"], wheatus["year"]) == ("Wheatus", 2000)

    incompletas = {r["title"]: r for r in library.list_incomplete(conn)}
    assert incompletas["Teenage Dirtbag"]["inferred"] == 1
    assert incompletas["Teenage Dirtbag"]["no_album"] == 1
    assert incompletas["suelto"]["no_artist"] == 1
    assert "Taxman" not in incompletas  # etiquetada completa


def test_force_rescan_rereads_everything(conn, library_dir):
    scan(conn, library_dir)
    r = scan(conn, library_dir, force=True)
    assert (r.added, r.updated, r.unchanged) == (0, 6, 0)


def test_migration_v1_to_v2_keeps_data():
    import sqlite3

    from sonoteca.core import db

    raw = sqlite3.connect(":memory:")
    raw.row_factory = sqlite3.Row
    raw.executescript(db.SCHEMA_V1)
    raw.execute("PRAGMA user_version = 1")
    raw.execute("INSERT INTO artists (name, sort_name) VALUES ('X', 'X')")
    db.migrate(raw)
    assert raw.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    cols = [r["name"] for r in raw.execute("PRAGMA table_info(tracks)")]
    assert "inferred" in cols
    assert raw.execute("SELECT COUNT(*) FROM artists").fetchone()[0] == 1


def test_migration_v2_to_v3_flags_filename_titles_for_rescan(tmp_path):
    import sqlite3

    from sonoteca.core import db

    raw = sqlite3.connect(":memory:")
    raw.row_factory = sqlite3.Row
    raw.executescript(db.SCHEMA_V1)
    raw.execute("ALTER TABLE tracks ADD COLUMN inferred INTEGER NOT NULL DEFAULT 0")
    raw.execute("PRAGMA user_version = 2")
    raw.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'A', 'A');
    INSERT INTO albums (id, title, album_artist_id) VALUES (1, 'B', 1);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES
        (1, '/m/03- Ace Of Base - Happy Nation.mp3', 1, 111, 'mp3', 'audio'),
        (2, '/m/Bien etiquetada.mp3', 1, 222, 'mp3', 'audio'),
        (3, '/m/Deducida.mp3', 1, 333, 'mp3', 'audio');
    INSERT INTO tracks (file_id, album_id, artist_id, title, inferred) VALUES
        (1, 1, 1, '03- Ace Of Base - Happy Nation', 0),   -- el nombre completo como título
        (2, 1, 1, 'Un título real', 0),
        (3, 1, 1, 'Deducida', 1);
    """)
    db.migrate(raw)
    mtimes = {r["id"]: r["mtime_ns"] for r in raw.execute("SELECT id, mtime_ns FROM files")}
    assert mtimes == {1: 0, 2: 222, 3: 0}  # solo se marcan las dos que dependen del nombre
    assert raw.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
