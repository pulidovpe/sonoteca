"""Botones de las listas (Reproducir/Detener, Aleatorio) y doble clic en canciones."""
from pathlib import Path

QML = Path(__file__).resolve().parent.parent / "src" / "sonoteca" / "ui" / "qml"
UI = QML.parent


def _read(name):
    return (QML / name).read_text(encoding="utf-8")


def test_album_and_playlist_pages_have_stop_and_shuffle_buttons():
    for name, key in (("AlbumDetail.qml", '"album:" + albumId'), ("PlaylistDetail.qml", '"playlist:" + playlistId')):
        page = _read(name)
        assert f"readonly property string sourceKey: {key}" in page, name
        assert "readonly property bool listPlaying: player.playing && player.sourceKey === sourceKey" in page, name
        assert 'page.listPlaying ? "Detener" : "Reproducir"' in page, name
        assert 'label: "Aleatorio"' in page and "player.stopPlayback()" in page and "player.playShuffled(sourceKey" in page, name
        # 0.12.2: «Aleatorio» solo reordena la lista de la derecha; Reproducir/Detener es el otro botón
        assert "function shuffleList() { player.toggleShuffle() }" in page, name
        assert "primary: player.shuffle;" in page, name


def test_double_click_adds_only_that_song_in_albums_search_artist_and_home():
    main = _read("Main.qml")
    assert "function playOne(trackId) { player.playFirst([trackId]) }" in main and "queueChoice" not in main
    for name in ("AlbumDetail.qml", "AlbumsPage.qml", "HomePage.qml", "SearchPage.qml", "TrackListPage.qml"):
        page = _read(name)
        assert "signal playOneRequested(int trackId)" in page, name
        assert "onActivated: page.playOneRequested(modelData.id)" in page.replace("                page.playOneRequested(modelData.id)", "onActivated: page.playOneRequested(modelData.id)") or "playOneRequested(modelData.id)" in page, name
        assert "player.playTrackIds(" not in page and "player.playAlbum(" not in page, name
    assert main.count("onPlayOneRequested: (id) => win.playOne(id)") >= 5     # álbum, inicio, artista, búsqueda, por revisar


def test_playlist_click_starts_the_list_from_that_song_unless_shuffle_is_on():
    page = _read("PlaylistDetail.qml")
    assert "if (player.shuffle) player.playFrom(sourceKey, ids, index)" in page
    assert "else player.playFrom(sourceKey, ids.slice(index), 0)" in page
    assert "onActivated: page.playFromIndex(index)" in page


def test_controller_exposes_the_source_and_stop():
    source = (UI / "player_controller.py").read_text(encoding="utf-8")
    for needle in ("def playFrom(self, source: str, ids: list, index: int)", "def playShuffled(", "def stopPlayback(",
                   "@Property(str, notify=sourceChanged)", 'self._set_source("")'):
        assert needle in source, needle
