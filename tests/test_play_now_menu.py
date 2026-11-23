"""Menú de álbumes («Reproducir ahora» vacía la lista) y título «Reproduciendo <canción>» (comprobación de los QML, sin Qt)."""
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_in_an_album_menu_the_first_item_replaces_the_list_and_the_second_keeps_it():
    menu = _read("TrackMenu.qml")
    assert "readonly property int wholeAlbum:" in menu
    assert menu.count("root.wholeAlbum > 0") >= 4
    assert "if (root.wholeAlbum > 0) root.replaceAndPlay(); else root.playNow()" in menu      # 1.ª opción
    assert "if (root.wholeAlbum > 0) root.playNow(); else root.replaceAndPlay()" in menu      # 2.ª opción


def test_the_panel_title_names_the_playing_song_when_there_is_no_single_origin():
    assert '"Reproduciendo " + player.currentTrack.title' in _read("QueuePage.qml")
