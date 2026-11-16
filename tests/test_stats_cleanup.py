"""0.8.1: contador de reproducciones y limpieza de álbumes/artistas vacíos (sin Qt)."""
import sqlite3

from sonoteca.core import library, stats
from sonoteca.core.cleanup import purge_missing, prune_empty
from sonoteca.core.db import SCHEMA_VERSION, connect


def add_track(conn, n, path, artist="X", album="Disco", album_artist=None):
    conn.execute("INSERT OR IGNORE INTO artists(name, sort_name) VALUES (?,?)", (artist, artist))
    aa = album_artist or artist
    conn.execute("INSERT OR IGNORE INTO artists(name, sort_name) VALUES (?,?)", (aa, aa))
    ar = conn.execute("SELECT id FROM artists WHERE name=?", (artist,)).fetchone()[0]
    aar = conn.execute("SELECT id FROM artists WHERE name=?", (aa,)).fetchone()[0]
    row = conn.execute("SELECT id FROM albums WHERE title=? AND album_artist_id=?", (album, aar)).fetchone()
    if row is None:
        conn.execute("INSERT INTO albums(title, album_artist_id) VALUES (?,?)", (album, aar))
        row = conn.execute("SELECT id FROM albums WHERE title=? AND album_artist_id=?", (album, aar)).fetchone()
    conn.execute("INSERT INTO files(path,size,mtime_ns,format,kind) VALUES (?,1,1,'mp3','audio')", (str(path),))
    fid = conn.execute("SELECT id FROM files WHERE path=?", (str(path),)).fetchone()[0]
    conn.execute("INSERT INTO tracks(file_id,album_id,artist_id,title,duration) VALUES (?,?,?,?,200)",
                 (fid, row[0], ar, f"Pista {n}"))
    conn.commit()
    return conn.execute("SELECT id FROM tracks WHERE file_id=?", (fid,)).fetchone()[0]


def test_play_counter_and_threshold():
    conn = connect(":memory:")
    assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
    t = add_track(conn, 1, "/a.mp3")
    assert stats.play_counts(conn, [t]) == {t: 0}
    assert stats.record_play(conn, t) == 1 and stats.record_play(conn, t) == 2
    assert stats.play_counts(conn, [t, 999]) == {t: 2, 999: 0}
    # cuenta a los 3 s de sonar (o la pista entera si dura menos), sin exigir oírla completa
    assert stats.threshold_ms(200_000) == 3_000
    assert stats.threshold_ms(600_000) == 3_000
    assert stats.threshold_ms(0) == 3_000
    assert stats.threshold_ms(1_000) == 1_000
    conn.execute("DELETE FROM tracks WHERE id=?", (t,))
    assert stats.play_counts(conn, [t]) == {t: 0}  # el contador sale con la pista (cascada)


def test_lists_hide_empty_albums_and_artists():
    conn = connect(":memory:")
    add_track(conn, 1, "/a.mp3")
    # álbum y artista sin ninguna canción
    conn.execute("INSERT INTO artists(name, sort_name) VALUES ('Fantasma','Fantasma')")
    conn.execute("INSERT INTO albums(title, album_artist_id) VALUES ('Vacío', (SELECT id FROM artists WHERE name='Fantasma'))")
    conn.commit()
    assert [r["name"] for r in library.list_artists(conn)] == ["X"]
    assert [r["title"] for r in library.list_albums(conn)] == ["Disco"]
    assert prune_empty(conn) == 2  # y además se borran de la base
    # un artista de álbum (p. ej. "Varios") sin pistas propias sigue apareciendo si su álbum tiene canciones
    add_track(conn, 2, "/b.mp3", artist="Cantante", album="Recopilatorio", album_artist="Varios")
    assert {r["name"] for r in library.list_artists(conn)} == {"X", "Cantante", "Varios"}


def test_purge_missing_removes_vanished_files_but_protects_against_unplugged_disk(tmp_path):
    conn = connect(":memory:")
    keep = [tmp_path / f"k{i}.mp3" for i in range(3)]
    for i, p in enumerate(keep):
        p.write_bytes(b"x")
        add_track(conn, i, p)
    gone = add_track(conn, 9, tmp_path / "borrada.mp3", artist="Solo", album="Solitario")
    r = purge_missing(conn)
    assert r == {"removed": 1, "pruned": 2, "skipped": 0}  # su álbum y su artista quedaron vacíos
    assert conn.execute("SELECT COUNT(*) FROM tracks WHERE id=?", (gone,)).fetchone()[0] == 0
    # si falta más de la mitad (disco desconectado) no se borra nada
    for p in keep[:2]:
        p.unlink()
    r = purge_missing(conn)
    assert r["removed"] == 0 and r["skipped"] == 2
    assert conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 3


def _plays(conn, track_id, n):
    for _ in range(n):
        stats.record_play(conn, track_id)


def test_artist_top_tracks_two_per_album_sorted_by_plays():
    conn = connect(":memory:")
    a1 = [add_track(conn, i, f"/a{i}.mp3", album="Uno") for i in range(1, 5)]
    b1 = [add_track(conn, i, f"/b{i}.mp3", album="Dos") for i in range(11, 14)]
    add_track(conn, 99, "/z.mp3", artist="Otro", album="Ajeno")
    _plays(conn, a1[2], 5); _plays(conn, a1[1], 2); _plays(conn, a1[0], 1)
    _plays(conn, b1[1], 9)
    artist = conn.execute("SELECT id FROM artists WHERE name='X'").fetchone()[0]
    rows = stats.artist_top_tracks(conn, artist)
    assert [(r["title"], r["plays"]) for r in rows] == [
        ("Pista 12", 9), ("Pista 3", 5), ("Pista 2", 2), ("Pista 11", 0)]  # 2 por álbum; Uno: las 2 más oídas
    assert {r["album"] for r in rows} == {"Uno", "Dos"}
    # sin reproducciones: se queda con las primeras de cada álbum, en orden
    conn2 = connect(":memory:")
    [add_track(conn2, i, f"/c{i}.mp3", album="Solo") for i in range(1, 4)]
    art2 = conn2.execute("SELECT id FROM artists").fetchone()[0]
    assert [r["title"] for r in stats.artist_top_tracks(conn2, art2)] == ["Pista 1", "Pista 2"]


def test_home_rankings():
    conn = connect(":memory:")
    t1 = add_track(conn, 1, "/1.mp3", artist="Uno", album="A1")
    t2 = add_track(conn, 2, "/2.mp3", artist="Dos", album="A2")
    t3 = add_track(conn, 3, "/3.mp3", artist="Dos", album="A2")
    assert stats.top_tracks(conn) == [] and stats.top_albums(conn) == [] and stats.top_artists(conn) == []
    _plays(conn, t1, 1); _plays(conn, t2, 2); _plays(conn, t3, 2)
    assert [r["name"] for r in stats.top_artists(conn)] == ["Dos", "Uno"]
    assert stats.top_artists(conn)[0]["plays"] == 4
    assert [(r["title"], r["plays"]) for r in stats.top_albums(conn)] == [("A2", 4), ("A1", 1)]
    assert [r["title"] for r in stats.top_tracks(conn)][2] == "Pista 1"
    # listas: se ordenan por lo escuchado de sus canciones; las no escuchadas, por nombre
    conn.execute("INSERT INTO playlists(name) VALUES ('Zeta'), ('Alfa'), ('Beta')")
    ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM playlists")}
    conn.execute("INSERT INTO playlist_tracks(playlist_id, track_id, position) VALUES (?,?,0)", (ids["Zeta"], t2))
    conn.execute("INSERT INTO playlist_tracks(playlist_id, track_id, position) VALUES (?,?,1)", (ids["Zeta"], t3))
    conn.commit()
    top = stats.top_playlists(conn)
    assert [(r["name"], r["plays"], r["tracks"]) for r in top] == [("Zeta", 4, 2), ("Alfa", 0, 0), ("Beta", 0, 0)]


def test_playlist_cover_albums_distinct_in_order_max_four():
    from sonoteca.core import playlists as store

    conn = connect(":memory:")
    tracks = [add_track(conn, i, f"/{i}.mp3", album=f"Disco {i // 2}") for i in range(12)]  # 6 álbumes
    conn.execute("INSERT INTO playlists(name) VALUES ('Mezcla'), ('Una sola'), ('Vacía')")
    ids = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM playlists")}
    for pos, t in enumerate([tracks[3], tracks[2], tracks[8], tracks[9], tracks[0], tracks[11], tracks[5]]):
        conn.execute("INSERT INTO playlist_tracks(playlist_id, track_id, position) VALUES (?,?,?)", (ids["Mezcla"], t, pos))
    conn.execute("INSERT INTO playlist_tracks(playlist_id, track_id, position) VALUES (?,?,0)", (ids["Una sola"], tracks[0]))
    conn.execute("INSERT INTO playlist_tracks(playlist_id, track_id, position) VALUES (?,?,1)", (ids["Una sola"], tracks[1]))
    conn.commit()
    album_of = {t: conn.execute("SELECT album_id FROM tracks WHERE id=?", (t,)).fetchone()[0] for t in tracks}
    got = store.cover_album_ids(conn, ids["Mezcla"])
    # Disco 1 (pistas 3 y 2), Disco 4 (8 y 9), Disco 0, Disco 5: en el orden en que aparecen, máximo 4
    assert got == [album_of[tracks[3]], album_of[tracks[8]], album_of[tracks[0]], album_of[tracks[11]]]
    assert store.cover_album_ids(conn, ids["Una sola"]) == [album_of[tracks[0]]]
    assert store.cover_album_ids(conn, ids["Vacía"]) == []
