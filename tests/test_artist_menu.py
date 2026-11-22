"""Parte C-bis: menú ⋮ en las cajas de artistas, título del panel ajustado y origen «álbum» (comprobación de los QML, sin Qt)."""
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"
ARTIST = "onMenuRequested: page.menuRequested(library.artistTrackIds(modelData.id))"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_artist_boxes_forward_the_menu_with_every_track_of_the_artist():
    for page in ("ArtistsPage.qml", "HomePage.qml", "SearchPage.qml"):
        assert _read(page).count(ARTIST) == 1, page
    assert "signal menuRequested(var ids)" in _read("ArtistsPage.qml")
    assert "ArtistsPage { onArtistClicked: (id, name) => win.openArtist(id, name); onMenuRequested: (ids) => win.showTrackMenu(ids) }" in _read("Main.qml")


def test_every_box_with_a_menu_enables_it():
    assert _read("AlbumsPage.qml").count("menuEnabled: true") == 1
    assert _read("ArtistsPage.qml").count("menuEnabled: true") == 1
    for page in ("HomePage.qml", "SearchPage.qml"):
        assert _read(page).count("menuEnabled: true") == 2, page          # álbumes y artistas


def test_the_panel_title_wraps_and_replace_and_play_names_a_whole_album():
    queue = _read("QueuePage.qml")
    assert "wrapMode: Text.Wrap" in queue and "maximumLineCount: 2" in queue
    assert "library.wholeAlbumOf(ids)" in _read("TrackMenu.qml")
