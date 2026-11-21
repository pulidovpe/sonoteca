"""Parte B con Qt: PlayerController.sourceInfo() (lo que muestra el título del panel «Reproduciendo»)."""
from test_player_controller import env  # noqa: F401  (fixture)

from sonoteca.core import playlists


def test_source_info_names_the_album_or_playlist_and_forgets_it(env):
    ctrl, _be, album, *_ = env
    ctrl.playAlbum(album, 0)
    ids = ctrl.queueTrackIds()
    assert ctrl.sourceInfo() == {"kind": "", "title": ""}                # canciones sin lista
    ctrl.playFrom(f"album:{album}", ids, 0)
    assert ctrl.sourceInfo() == {"kind": "album", "title": "Disco"}
    pid = playlists.create(ctrl._conn, "Mi lista")
    ctrl.playFrom(f"playlist:{pid}", ids, 0)
    assert ctrl.sourceInfo() == {"kind": "playlist", "title": "Mi lista"}
    playlists.rename(ctrl._conn, pid, "Otro nombre")
    assert ctrl.sourceInfo()["title"] == "Otro nombre"
    ctrl.playTrackIds(ids, 0)                                            # otra forma de empezar: olvida el origen
    assert ctrl.sourceInfo() == {"kind": "", "title": ""}
