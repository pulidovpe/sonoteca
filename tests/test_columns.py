"""Columnas responsivas de las listas: pista · nombre/artista · álbum · año · reproducciones."""
import re
import sqlite3
from pathlib import Path

from sonoteca.core import library, playlists, stats
from sonoteca.core.db import connect

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"


def _theme():
    return (QML / "Theme.qml").read_text(encoding="utf-8")


def test_tier_thresholds_and_helpers_match_the_spec():
    theme = _theme()
    assert "readonly property int tierWideMin: 860" in theme and "readonly property int tierMediumMin: 560" in theme
    assert "function tier(width) { return width >= tierWideMin ? 3 : (width >= tierMediumMin ? 2 : 1) }" in theme
    assert "function albumColumn(width)" in theme


def test_both_row_types_show_columns_by_tier_in_the_requested_order():
    for name in ("TrackRow.qml", "ListTrackRow.qml"):
        row = (QML / name).read_text(encoding="utf-8")
        assert "readonly property int tier: Theme.tier(width)" in row, name
        assert "tier >= 2 && album" in row and "tier >= 3 && year" in row and "tier >= 3 && plays" in row, name
        cells = row[row.index("Row {\n        id: cells") if "Row {\n        id: cells" in row else row.index("id: cells"):]
        order = [cells.index(k) for k in ("showAlbum", "showYear", "showPlays")]
        assert order == sorted(order), f"{name}: orden álbum, año, reproducciones"
        assert "line2" in row and "artist !== \"\" ? artist : subtitle" in row     # el artista va debajo del nombre


def test_every_list_passes_artist_album_and_year():
    for name in ("AlbumDetail", "AlbumsPage", "HomePage", "SearchPage", "TrackListPage", "PlaylistDetail", "QueuePage"):
        page = (QML / f"{name}.qml").read_text(encoding="utf-8")
        for field in ("artist:", "album:", "year:"):
            assert re.search(r"\n\s+" + field + r"\s", page), f"{name}: falta {field}"


def _library(tmp_path):
    conn = connect(tmp_path / "c.db")
    conn.row_factory = sqlite3.Row
    artist = conn.execute("INSERT INTO artists (name, sort_name) VALUES ('Banda', 'banda')").lastrowid
    album = conn.execute("INSERT INTO albums (title, album_artist_id, year) VALUES ('Disco', ?, 1999)", (artist,)).lastrowid
    ids = []
    for n, year in enumerate((2001, None), 1):          # una pista con año propio y otra que hereda el del álbum
        fid = conn.execute("INSERT INTO files (path, size, mtime_ns, format, kind) VALUES (?, 1, 1, 'mp3', 'audio')",
                           (f"/m/{n}.mp3",)).lastrowid
        ids.append(conn.execute(
            "INSERT INTO tracks (file_id, album_id, artist_id, title, duration, year) VALUES (?, ?, ?, ?, 1, ?)",
            (fid, album, artist, f"T{n}", year)).lastrowid)
        conn.execute("INSERT INTO play_stats (track_id, plays, last_played) VALUES (?, ?, '2026-01-01')", (ids[-1], n))
    conn.commit()
    return conn, album, artist, ids


def test_every_data_source_provides_a_year_falling_back_to_the_album_year(tmp_path):
    conn, album, artist, ids = _library(tmp_path)
    assert [r["year"] for r in library.list_tracks(conn, album_id=album)] == [2001, 1999]
    assert library.get_track(conn, ids[1])["year"] == 1999
    assert {r["title"]: r["year"] for r in stats.top_tracks(conn)} == {"T1": 2001, "T2": 1999}
    assert {r["title"]: r["year"] for r in stats.artist_top_tracks(conn, artist)} == {"T1": 2001, "T2": 1999}
    pid = playlists.create(conn, "L")
    playlists.add_tracks(conn, pid, ids)
    assert [r["year"] for r in playlists.tracks(conn, pid)] == [2001, 1999]
