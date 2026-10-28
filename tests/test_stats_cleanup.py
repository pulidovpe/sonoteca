"""0.8.1: contador de reproducciones y limpieza de álbumes/artistas vacíos (sin Qt)."""
import sqlite3

from musicapp.core import library, stats
from musicapp.core.cleanup import purge_missing, prune_empty
from musicapp.core.db import SCHEMA_VERSION, connect


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
    # mitad de la pista, con tope de 4 minutos; sin duración conocida, 30 s
    assert stats.threshold_ms(200_000) == 100_000
    assert stats.threshold_ms(600_000) == 240_000
    assert stats.threshold_ms(0) == 30_000
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
