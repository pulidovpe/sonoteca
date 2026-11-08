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
        assert "tier >= 2 && album" in row and "width >= Theme.yearMin && year" in row and "width >= Theme.playsMin && plays" in row, name
        cells = row[row.index("Row {\n        id: cells") if "Row {\n        id: cells" in row else row.index("id: cells"):]
        order = [cells.index(k) for k in ("showArtistColumn", "showAlbum", "showYear", "showPlays", "showInList")]
        assert order == sorted(order), f"{name}: orden artista, álbum, año, reproducciones, en lista"
        assert "line2" in row and "line2IsArtist ? artist : subtitle" in row           # sin columna propia, el artista va debajo del nombre


def test_every_list_passes_artist_album_and_year():
    for name in ("AlbumDetail", "AlbumsPage", "HomePage", "SearchPage", "PlaylistDetail", "QueuePage"):     # Por revisar: ver test_artist_link_and_columns
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


def test_year_column_also_in_narrow_lists_and_album_takes_a_share_of_the_free_width():
    theme = (QML / "Theme.qml").read_text(encoding="utf-8")
    assert "readonly property int yearMin: 360" in theme and "Math.round((width - 300) * (wide ? 0.30 : 0.42))" in theme
    compact = (QML / "ListTrackRow.qml").read_text(encoding="utf-8")
    assert "width: row.compact ? Theme.yearColumnCompact : Theme.yearColumn" in compact


def test_columns_have_fixed_widths_so_they_align_between_songs():
    """0.12.15: la duración, el año, el álbum y las reproducciones no dependen del contenido de cada fila."""
    theme = _theme()
    assert "readonly property int durationColumn: 60" in theme and "readonly property int durationColumnCompact: 48" in theme
    for name in ("TrackRow.qml", "ListTrackRow.qml"):
        row = (QML / name).read_text(encoding="utf-8")
        cells = row[row.index("id: cells"):]
        assert "implicitWidth" not in cells, name                          # ningún ancho depende del texto de la fila
        assert "horizontalAlignment: Text.AlignRight" in cells, name       # duraciones alineadas a la derecha
        assert 'album !== ""' not in row and 'year !== ""' not in row, name   # la columna no desaparece si falta el dato
        assert "album !== undefined" in row and "year !== undefined" in row, name
    track = (QML / "TrackRow.qml").read_text(encoding="utf-8")
    assert "width: Theme.durationColumn" in track
    assert "id: badgeBox" in track and "id: badgeBox" not in track[track.index("id: cells"):]   # la etiqueta va en la columna del nombre
    assert "width: row.compact ? Theme.durationColumnCompact : Theme.durationColumn" in (QML / "ListTrackRow.qml").read_text(encoding="utf-8")
