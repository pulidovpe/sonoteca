"""0.14.5: el artista es un enlace en todas las listas, columnas «En lista», y Por revisar con Nombre · Tags · Tipo · Duración."""
import sqlite3
from pathlib import Path

from sonoteca.core import library, playlists
from sonoteca.core.db import connect

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_artist_is_a_link_everywhere_through_the_bus():
    bus = _read("NavBus.qml")
    assert "signal artistRequested(int artistId, string name)" in bus
    assert "function onArtistRequested(artistId, name) { win.openArtist(artistId, name) }" in _read("Main.qml")
    assert "LinkText 1.0 LinkText.qml" in _read("qmldir")
    for name, ref in (("TrackRow.qml", "root"), ("ListTrackRow.qml", "row")):
        row = _read(name)
        assert f"onClicked: {ref}.openArtist()" in row and "NavBus.artistRequested(info.artistId, info.artist)" in row, name
        assert f"linkEnabled: {ref}.line2IsArtist" in row, name                      # el artista de debajo del nombre
        assert f"visible: {ref}.showArtistColumn" in row, name                       # y el de la columna propia
        assert "width >= Theme.artistMin" in row, name


def test_artist_column_only_when_the_window_is_wide_and_in_list_column_after_plays():
    theme = _read("Theme.qml")
    assert "readonly property int artistMin: 1180" in theme and "readonly property int inListMin: 760" in theme
    assert "readonly property int playsMin: 940" in theme and "function artistColumn(width)" in theme
    row = _read("TrackRow.qml")
    assert "readonly property bool line2IsArtist: !showArtistColumn && artist !== undefined && artist !== \"\"" in row
    assert "readonly property bool inList: (playlists.revision, trackId > 0 && playlists.inLists(trackId))" in row
    header = _read("ColumnHeader.qml")
    assert 'text: "En lista"' in header and "root.showArtistColumn" in header
    assert 'text: "Nombre"' in header and 'text: "Artista"' in header


def test_saved_lists_do_not_show_the_in_list_column():
    assert "inListColumn: false" in _read("PlaylistDetail.qml") and "hasInList: false" in _read("PlaylistDetail.qml")


def test_review_page_has_only_name_tags_kind_and_duration():
    page = _read("TrackListPage.qml")
    row = page[page.index("delegate: TrackRow {"):page.index("ScrollBar.vertical")]
    assert "hasTags: modelData.hasTags" in row and "isVideo: modelData.isVideo" in row and "inListColumn: false" in row
    for gone in ("artist:", "album:", "year:"):
        assert gone not in row, gone                                                   # sin esas columnas el nombre ocupa el resto
    assert "review: true" in page
    header = _read("ColumnHeader.qml")
    for text in ('text: "Tags"', 'text: "Tipo"', 'key: root.review ? "duration" : ""'):
        assert text in header, text
    track_row = _read("TrackRow.qml")
    assert 'root.hasTags ? "Con tags" : "Sin tags"' in track_row and 'root.isVideo ? "Video" : "M\\u00fasica"' in track_row
    sorter = _read("TrackSort.js")
    assert 'key === "tags"' in sorter and 'key === "kind"' in sorter and 'key === "duration"' in sorter


def test_membership_queries_and_review_rows_carry_kind_and_duration(tmp_path):
    conn = connect(tmp_path / "t.db")
    conn.row_factory = sqlite3.Row
    conn.execute("INSERT INTO artists(id, name, sort_name) VALUES (1, 'Banda', 'banda')")
    conn.execute("INSERT INTO albums(id, title, album_artist_id, year) VALUES (1, 'Disco', 1, 2000)")
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tracks)")][:13]
    for i, (kind, inferred, duration) in enumerate([("audio", 0, 200.0), ("video", 1, 0.0), ("audio", 1, 180.0)], start=1):
        conn.execute("INSERT INTO files(id, path, size, mtime_ns, format, kind) VALUES (?, ?, 1, 1, 'mp3', ?)",
                     (i, str(tmp_path / f"{i}.mp3"), kind))
        conn.execute(f"INSERT INTO tracks({','.join(cols)}) VALUES ({','.join('?' * 13)})",
                     (i, i, 1, 1, f"T{i}", i, 1, 2000, duration, "Rock", 192, 1, inferred))
    conn.commit()
    one = playlists.create(conn, "Rock")
    two = playlists.create(conn, "Baladas")
    playlists.add_tracks(conn, one, [1, 3])
    playlists.add_tracks(conn, two, [3])
    assert playlists.member_track_ids(conn) == {1, 3}
    assert playlists.lists_with_track(conn, 3) == ["Baladas", "Rock"] and playlists.lists_with_track(conn, 2) == []
    rows = {r["id"]: r for r in library.list_incomplete(conn)}
    assert set(rows) == {2, 3}                                  # la 1 tiene tags y duración: no está por revisar
    assert rows[2]["kind"] == "video" and rows[3]["kind"] == "audio" and rows[3]["duration"] == 180.0
