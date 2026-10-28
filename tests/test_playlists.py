import pytest

from sonoteca.core import playlists
from sonoteca.core.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    c.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'A', 'A');
    INSERT INTO albums (id, title, album_artist_id) VALUES (1, 'Disco', 1), (2, 'Álbum desconocido', 1);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES
        (1,'/1.mp3',1,1,'mp3','audio'),(2,'/2.mp3',1,1,'mp3','audio'),(3,'/3.mp3',1,1,'mp3','audio');
    INSERT INTO tracks (id, file_id, album_id, artist_id, title, duration) VALUES
        (1, 1, 1, 1, 'Uno', 60), (2, 2, 1, 1, 'Dos', 120), (3, 3, 2, 1, 'Tres', 30);
    """)
    return c


def titles(conn, pid):
    return [r["title"] for r in playlists.tracks(conn, pid)]


def test_create_validates_and_rejects_duplicates_ignoring_case(conn):
    pid = playlists.create(conn, "  Mi   lista  ")
    assert playlists.get_playlist(conn, pid)["name"] == "Mi lista"  # espacios normalizados
    with pytest.raises(ValueError, match="Ya existe una lista llamada «MI LISTA»"):
        playlists.create(conn, "MI LISTA")
    with pytest.raises(ValueError, match="Escribe un nombre"):
        playlists.create(conn, "   ")
    with pytest.raises(ValueError, match="demasiado largo"):
        playlists.create(conn, "x" * 81)


def test_rename_delete_and_missing_playlist(conn):
    a = playlists.create(conn, "A")
    b = playlists.create(conn, "B")
    playlists.rename(conn, a, "a")  # solo cambian las mayúsculas: se permite
    assert playlists.get_playlist(conn, a)["name"] == "a"
    with pytest.raises(ValueError, match="Ya existe"):
        playlists.rename(conn, a, "b")
    with pytest.raises(ValueError, match="ya no existe"):
        playlists.rename(conn, 999, "Z")
    playlists.delete(conn, b)
    assert [p["name"] for p in playlists.list_playlists(conn)] == ["a"]


def test_add_tracks_keeps_order_allows_duplicates_and_ignores_unknown(conn):
    pid = playlists.create(conn, "L")
    assert playlists.add_tracks(conn, pid, [2, 1]) == 2
    assert playlists.add_tracks(conn, pid, [2, 999, 3]) == 2  # el 999 no existe
    assert titles(conn, pid) == ["Dos", "Uno", "Dos", "Tres"]
    assert [r["position"] for r in playlists.tracks(conn, pid)] == [0, 1, 2, 3]
    with pytest.raises(ValueError, match="ya no existe"):
        playlists.add_tracks(conn, 999, [1])


def test_summary_counts_tracks_and_duration(conn):
    pid = playlists.create(conn, "L")
    empty = playlists.create(conn, "Vacía")
    playlists.add_tracks(conn, pid, [1, 2, 2])
    rows = {r["name"]: r for r in playlists.list_playlists(conn)}
    assert (rows["L"]["tracks"], rows["L"]["duration"]) == (3, 300)
    assert (rows["Vacía"]["tracks"], rows["Vacía"]["duration"]) == (0, 0)
    assert playlists.get_playlist(conn, empty)["tracks"] == 0
    assert playlists.get_playlist(conn, 999) is None


def test_remove_and_move_keep_positions_contiguous(conn):
    pid = playlists.create(conn, "L")
    playlists.add_tracks(conn, pid, [1, 2, 3])
    playlists.move(conn, pid, 2, 0)
    assert titles(conn, pid) == ["Tres", "Uno", "Dos"]
    playlists.move(conn, pid, 0, 1)
    assert titles(conn, pid) == ["Uno", "Tres", "Dos"]
    playlists.remove_at(conn, pid, 1)
    assert titles(conn, pid) == ["Uno", "Dos"]
    assert [r["position"] for r in playlists.tracks(conn, pid)] == [0, 1]
    with pytest.raises(IndexError):
        playlists.remove_at(conn, pid, 5)
    with pytest.raises(IndexError):
        playlists.move(conn, pid, 0, 9)


def test_replace_all_and_create_from_tracks(conn):
    pid = playlists.create_from_tracks(conn, "Desde la cola", [3, 1, 3])
    assert titles(conn, pid) == ["Tres", "Uno", "Tres"]
    playlists.replace_all(conn, pid, [2, 999])
    assert titles(conn, pid) == ["Dos"]
    with pytest.raises(ValueError):
        playlists.create_from_tracks(conn, "desde la cola", [1])  # nombre repetido
    assert len(playlists.list_playlists(conn)) == 1  # y no deja una lista a medias


def test_tracks_that_leave_the_library_leave_the_playlists(conn):
    pid = playlists.create(conn, "L")
    playlists.add_tracks(conn, pid, [1, 2, 3])
    with conn:
        conn.execute("DELETE FROM files WHERE id = 2")  # la pista 2 ya no está en disco
    assert titles(conn, pid) == ["Uno", "Tres"]
    assert playlists.get_playlist(conn, pid)["tracks"] == 2
