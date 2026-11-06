"""0.12.14: la página Listas se puede ver en lista (como siempre) o en cuadrícula."""
from pathlib import Path

QML = Path(__file__).resolve().parents[1] / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_playlists_page_has_list_and_grid_views_with_toggle():
    page = _read("PlaylistsPage.qml")
    assert "ListView {" in page and "GridView {" in page
    assert "visible: !page.gridMode" in page and "visible: page.gridMode" in page
    assert "onClicked: page.setGrid(false)" in page and "onClicked: page.setGrid(true)" in page
    assert 'prefs.boolValue("playlists.grid", false)' in page and 'prefs.setBool("playlists.grid", on)' in page
    assert page.count("page.openPlaylist(modelData.id)") == 2           # abrir una lista funciona en las dos vistas
    assert page.count("elide: Text.ElideRight") >= 4                     # nombres largos recortados con «…»


def test_theme_has_the_view_icons_and_state():
    theme = _read("Theme.qml")
    assert "readonly property string iconGrid:" in theme and "readonly property string iconRows:" in theme
    assert "playlistsGrid" not in theme                    # el estado vive en las preferencias, no en el tema
