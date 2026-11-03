"""«Por revisar»: solo lo que NO tiene tags de artista y título (o está deducido del nombre del archivo)."""
import sqlite3

from sonoteca.core import library
from sonoteca.core.db import connect
from sonoteca.core.models import UNKNOWN_ALBUM, UNKNOWN_ARTIST


def _add(conn, n, artist, album, inferred):
    artist_id = conn.execute("SELECT id FROM artists WHERE name = ?", (artist,)).fetchone()
    artist_id = artist_id[0] if artist_id else conn.execute(
        "INSERT INTO artists (name, sort_name) VALUES (?, ?)", (artist, artist.lower())).lastrowid
    album_id = conn.execute("SELECT id FROM albums WHERE title = ? AND album_artist_id = ?", (album, artist_id)).fetchone()
    album_id = album_id[0] if album_id else conn.execute(
        "INSERT INTO albums (title, album_artist_id) VALUES (?, ?)", (album, artist_id)).lastrowid
    fid = conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?, 1, 1, 'mp3', 'audio')", (f"/m/{n}.mp3",)).lastrowid
    return conn.execute("INSERT INTO tracks (file_id, album_id, artist_id, title, duration, inferred) VALUES (?, ?, ?, ?, 1, ?)",
                        (fid, album_id, artist_id, f"T{n}", inferred)).lastrowid


def test_tracks_with_artist_and_title_tags_leave_the_list_even_without_album(tmp_path):
    conn = connect(tmp_path / "r.db")
    conn.row_factory = sqlite3.Row
    complete = _add(conn, 1, "Banda", "Disco", 0)
    no_album = _add(conn, 2, "Banda", UNKNOWN_ALBUM, 0)            # artista y título en los tags; falta el álbum
    inferred = _add(conn, 3, "Otro", UNKNOWN_ALBUM, 1)             # deducido del nombre del archivo
    no_artist = _add(conn, 4, UNKNOWN_ARTIST, "Disco", 0)          # sin artista
    conn.commit()
    listed = {r["id"] for r in library.list_incomplete(conn)}
    assert listed == {inferred, no_artist}
    assert complete not in listed and no_album not in listed
