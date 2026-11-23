"""Parte C3: menú ⋮ y clic derecho en las cajas de listas (comprobación del texto de los QML, sin Qt)."""
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_the_playlist_menu_is_registered_and_offers_play_rename_and_delete():
    assert "PlaylistMenu 1.0 PlaylistMenu.qml" in _read("qmldir")
    menu = _read("PlaylistMenu.qml")
    for text in ("Reproducir", "orden aleatorio", "continuaci\\u00f3n", "Renombrar", "Eliminar lista"):
        assert text in menu, text
    assert "signal renameRequested" in menu and "signal deleteRequested" in menu


def test_the_playlists_page_opens_the_menu_from_rows_and_cards_with_button_and_right_click():
    page = _read("PlaylistsPage.qml")
    assert "signal menuRequested(int playlistId, string name)" in page
    assert page.count("m.button === Qt.RightButton") == 2 and page.count("Theme.iconMore") == 2     # fila + caja
    assert page.count("page.menuRequested(modelData.id, modelData.name)") == 4              # clic derecho y ⋮, en ambas vistas


def test_main_wires_the_playlist_menu_to_the_existing_rename_and_delete():
    main = _read("Main.qml")
    assert "onMenuRequested: (id, name) => win.showPlaylistMenu(id, name)" in main
    assert "function showPlaylistMenu(id, name) { playlistMenu.openFor(id, name) }" in main
    assert "PlaylistMenu { id: playlistMenu; onRenameRequested: (id, name) => win.renamePlaylist(id, name);" in main
    assert "onDeleteRequested: (id, name) => win.deletePlaylist(id, name) }" in main
