"""Historial de navegación con estado: década de Álbumes, posición y artistas visitados."""
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_pages_expose_their_state_and_restore_it():
    albums, artists = _read("AlbumsPage.qml"), _read("ArtistsPage.qml")
    assert "function saveState() { return { decade: page.decade, topExpanded: page.topExpanded, y: grid.contentY } }" in albums
    assert "decade = restore.decade || 0" in albums and "grid.contentY = page.restore.y" in albums
    assert "function saveState() { return { y: grid.contentY } }" in artists and "grid.contentY = page.restore.y" in artists


def test_main_saves_state_before_leaving_and_passes_it_back_when_rendering():
    main = _read("Main.qml")
    assert "navHistory[navIndex].state = item.saveState()" in main
    assert main.index("function go(loc) {\n        saveState()") > 0 and "saveState()\n        navIndex = i" in main    # también al ir atrás/adelante
    assert 'stack.replace(null, albumsComp, { restore: loc.state || null })' in main
    assert 'stack.replace(null, artistsComp, { restore: loc.state || null })' in main
    assert "heading: loc.name, restore: loc.state || null" in main                 # artistas visitados
    assert 'if (k !== "state")' in main                                             # el estado no cuenta al comparar ubicaciones


def test_mini_player_has_shuffle_and_mute_buttons():
    mini = _read("MiniPlayer.qml")
    for needle in ("id: shuffleButton", "player.toggleShuffle()", "Theme.iconShuffle", "id: muteButton", "player.toggleMute()"):
        assert needle in mini, needle
    assert "property bool active" in _read("IconButton.qml") and "iconShuffle" in _read("Theme.qml")
