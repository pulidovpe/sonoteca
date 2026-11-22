"""Parte C: menú ⋮ y clic derecho solo en las cajas de ÁLBUM (comprobación del texto de los QML, sin Qt)."""
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"
FORWARD = "onMenuRequested: page.menuRequested(library.albumTrackIds(modelData.id))"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_album_card_has_the_menu_button_and_right_click_only_for_albums():
    card = _read("AlbumCard.qml")
    assert "signal menuRequested()" in card and "Theme.iconMore" in card
    assert "Qt.RightButton" in card and "hasMenu: albumId > 0" in card        # las cajas de artistas (sin albumId) no
    assert "root.hasMenu" in card[card.index("Qt.RightButton"):][:200]


def test_the_three_pages_with_albums_forward_the_menu_with_every_track_of_the_album():
    for page in ("AlbumsPage.qml", "HomePage.qml", "SearchPage.qml"):
        assert _read(page).count(FORWARD) == 1, page                            # solo el delegado de álbumes
    assert FORWARD not in _read("ArtistsPage.qml")
