"""0.14.0: cabeceras de columna que ordenan las listas de canciones; el álbum es un enlace también en Inicio y búsqueda."""
from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_header_components_are_registered_and_ordered_by_the_five_keys():
    qmldir = _read("qmldir")
    assert "ColumnHeader 1.0 ColumnHeader.qml" in qmldir and "SortLabel 1.0 SortLabel.qml" in qmldir
    header = _read("ColumnHeader.qml")
    for key in ('key: "name"', 'key: "artist"', 'key: "album"', 'key: "year"', 'key: "plays"'):
        assert key in header, key
    assert 'import "TrackSort.js" as TrackSort' in header
    assert "implicitHeight: 32" in header
    assert "Theme.albumColumn(root.width)" in header and "Theme.durationColumn" in header      # mismos anchos que las filas
    assert 'var first = key !== "plays"' in header                                             # reproducciones: primero las que más suenan


def test_every_song_list_has_a_header_and_uses_it_as_model():
    for name, hdr in (("AlbumDetail.qml", "hdr"), ("SearchPage.qml", "hdr"), ("HomePage.qml", "hdr"),
                      ("AlbumsPage.qml", "topHdr"), ("TrackListPage.qml", "hdr"), ("PlaylistDetail.qml", "hdr")):
        page = _read(name)
        assert "ColumnHeader {" in page, name
        assert f"{hdr}.sorted(" in page, name
    play = _read("PlaylistDetail.qml")
    assert "if (!page.sortedView) playlists.moveTrack" in play                        # no se reordena una vista ordenada
    assert "page.removeAt(modelData.position)" in play                                # quitar usa la posición guardada, no la mostrada


def test_album_link_is_above_the_row_mouse_area():
    row = _read("TrackRow.qml")
    cells = row[row.index("id: cells"):]
    assert cells.lstrip().startswith("id: cells") and "z: 1" in cells[:200]
