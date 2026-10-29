import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtCore")

from conftest import make_mp3, make_mp4, needs_ffmpeg
from fakes import FakeBackend

from sonoteca.core import library
from sonoteca.core.db import connect
from sonoteca.core.scanner import scan
from sonoteca.ui.player_controller import PlayerController

pytestmark = needs_ffmpeg


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "music"
    for n in (1, 2, 3):
        make_mp3(root / f"A/{n}.mp3", title=f"Pista {n}", artist="X", album="Disco", track=f"{n}/3")
    make_mp4(root / "V/clip.mp4", title="Clip", artist="X", album="Videos")
    db = tmp_path / "t.db"
    conn = connect(db)
    scan(conn, root)
    album = conn.execute("SELECT id FROM albums WHERE title='Disco'").fetchone()[0]
    video = conn.execute("SELECT t.id FROM tracks t JOIN files f ON f.id=t.file_id"
                         " WHERE f.kind='video'").fetchone()[0]
    paths = {r["title"]: r["path"] for r in library.list_tracks(conn)}
    conn.close()
    backend = FakeBackend()
    ctrl = PlayerController(backend, db)
    return ctrl, backend, album, video, paths


def test_play_album_starts_first_track(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 0)
    assert str(be.loaded) == paths["Pista 1"]
    assert ctrl.playing and ctrl.hasTrack and not ctrl.isVideo
    assert ctrl.currentTrack["title"] == "Pista 1" and ctrl.currentTrack["album"] == "Disco"
    assert ctrl.duration == pytest.approx(1000, abs=250)


def test_start_from_index_and_auto_advance(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 1)
    assert str(be.loaded) == paths["Pista 2"]
    be.finish()
    assert str(be.loaded) == paths["Pista 3"]
    be.finish()  # fin de la cola sin repetir: se detiene pero sigue mostrando la última
    assert not ctrl.playing and ctrl.currentTrack["title"] == "Pista 3"


def test_repeat_one_and_all(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 2)
    ctrl.cycleRepeat()  # todo
    assert ctrl.repeatMode == "all"
    be.finish()
    assert str(be.loaded) == paths["Pista 1"]
    ctrl.cycleRepeat()  # una
    assert ctrl.repeatMode == "one"
    be.finish()
    assert str(be.loaded) == paths["Pista 1"] and ctrl.playing


def test_previous_restarts_then_goes_back(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 1)
    be.positionChanged.emit(5000)
    ctrl.previous()
    assert be.seeks[-1] == 0 and str(be.loaded) == paths["Pista 2"]
    be.positionChanged.emit(1000)
    ctrl.previous()
    assert str(be.loaded) == paths["Pista 1"]


def test_toggle_pause_resume(env):
    ctrl, be, album, _, _ = env
    ctrl.toggle()  # sin pista: no hace nada
    assert not ctrl.playing
    ctrl.playAlbum(album, 0)
    ctrl.toggle()
    assert be.state == "paused" and not ctrl.playing
    ctrl.toggle()
    assert be.state == "playing" and ctrl.playing


def test_missing_file_is_skipped_with_message(env):
    ctrl, be, album, _, paths = env
    os.remove(paths["Pista 1"])
    msgs = []
    ctrl.errorMessage.connect(msgs.append)
    ctrl.playAlbum(album, 0)
    assert str(be.loaded) == paths["Pista 2"]
    assert len(msgs) == 1 and "Pista 1" in msgs[0]


def test_all_files_missing_does_not_loop_forever(env):
    ctrl, _be, album, _, paths = env
    for t in ("Pista 1", "Pista 2", "Pista 3"):
        os.remove(paths[t])
    msgs = []
    ctrl.errorMessage.connect(msgs.append)
    ctrl.playAlbum(album, 0)
    assert len(msgs) == 3 and not ctrl.playing


def test_backend_failure_skips_to_next(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 0)
    msgs = []
    ctrl.errorMessage.connect(msgs.append)
    be.fail("codec no soportado")
    assert str(be.loaded) == paths["Pista 2"] and "codec" in msgs[0]


def test_volume_clamped_and_shuffle_toggle(env):
    ctrl, be, album, _, _ = env
    ctrl.setVolume(1.7)
    assert ctrl.volume == 1.0 and be.volume == 1.0
    ctrl.setVolume(-1)
    assert ctrl.volume == 0.0
    ctrl.playAlbum(album, 1)
    ctrl.toggleShuffle()
    assert ctrl.shuffle and ctrl.currentTrack["title"] == "Pista 2"


def test_video_track_flagged(env):
    ctrl, be, _, video, _ = env
    ctrl.playTrackIds([video], 0)
    assert ctrl.isVideo and be.loaded.suffix == ".mp4"


def test_play_empty_list_is_noop(env):
    ctrl, be, *_ = env
    ctrl.playTrackIds([], 0)
    assert be.loaded is None and not ctrl.hasTrack


# ---------------- lista temporal: agregar, quitar, ordenar ----------------
def titles(ctrl):
    return [r["title"] for r in ctrl.queueItems()]


def test_add_to_queue_while_playing_and_it_plays_after_the_album(env):
    ctrl, be, _album, _, paths = env
    msgs, changes = [], []
    ctrl.queueMessage.connect(msgs.append)
    ctrl.queueChanged.connect(lambda: changes.append(1))
    ctrl.playTrackIds([_ids(ctrl, "Pista 1")], 0)
    ctrl.addToQueue([_ids(ctrl, "Pista 3"), _ids(ctrl, "Pista 2")])
    assert titles(ctrl) == ["Pista 1", "Pista 3", "Pista 2"] and ctrl.queueLength == 3
    assert msgs[-1] == "2 canciones agregadas a la lista actual" and changes
    be.finish()
    assert str(be.loaded) == paths["Pista 3"]
    be.finish()
    assert str(be.loaded) == paths["Pista 2"]


def test_play_next_inserts_after_the_current_track(env):
    ctrl, be, album, _, _paths = env
    ctrl.playAlbum(album, 0)  # Pista 1, 2, 3
    msgs = []
    ctrl.queueMessage.connect(msgs.append)
    ctrl.playNext([_ids(ctrl, "Clip")])
    assert titles(ctrl) == ["Pista 1", "Clip", "Pista 2", "Pista 3"]
    assert msgs[-1] == "1 canción sonará a continuación"
    ctrl.next()
    assert be.loaded.suffix == ".mp4" and ctrl.isVideo


def test_building_a_temporary_list_without_playing_anything(env):
    ctrl, be, _album, _, paths = env
    msgs = []
    ctrl.queueMessage.connect(msgs.append)
    ctrl.addToQueue([_ids(ctrl, "Pista 2"), _ids(ctrl, "Pista 3")])
    assert not ctrl.hasTrack and be.loaded is None  # no empieza a sonar sola
    assert "Lista temporal creada con 2 canciones" in msgs[-1]
    assert all(not r["current"] for r in ctrl.queueItems())
    ctrl.playQueueAt(1)
    assert str(be.loaded) == paths["Pista 3"] and ctrl.queueItems()[1]["current"]
    ctrl.previous()
    assert str(be.loaded) == paths["Pista 2"]


def test_new_temporary_list_keeps_only_the_current_track(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 1)  # suena Pista 2
    ctrl.newTemporaryList()
    assert titles(ctrl) == ["Pista 2"] and ctrl.playing and ctrl.currentTrack["title"] == "Pista 2"
    ctrl.addToQueue([_ids(ctrl, "Pista 1")])
    be.finish()
    assert str(be.loaded) == paths["Pista 1"]
    ctrl.clearQueue()
    ctrl.newTemporaryList()  # sin nada sonando: queda vacía
    assert titles(ctrl) == [] and ctrl.queueLength == 0


def test_remove_from_queue_current_and_others(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 0)
    ctrl.removeFromQueue(2)  # una posterior
    assert titles(ctrl) == ["Pista 1", "Pista 2"] and ctrl.currentTrack["title"] == "Pista 1"
    ctrl.removeFromQueue(0)  # la que suena: pasa a sonar la siguiente
    assert titles(ctrl) == ["Pista 2"] and str(be.loaded) == paths["Pista 2"] and ctrl.playing
    ctrl.removeFromQueue(0)  # la última y actual: no queda nada
    assert ctrl.queueLength == 0 and not ctrl.hasTrack and not ctrl.playing
    ctrl.removeFromQueue(7)  # posición inexistente: no hace nada


def test_move_in_queue_keeps_the_playing_track(env):
    ctrl, _be, album, _, _paths = env
    ctrl.playAlbum(album, 0)
    ctrl.moveInQueue(2, 1)
    assert titles(ctrl) == ["Pista 1", "Pista 3", "Pista 2"] and ctrl.queuePosition == 0
    ctrl.moveInQueue(0, 2)  # mover la que suena
    assert titles(ctrl) == ["Pista 3", "Pista 2", "Pista 1"] and ctrl.currentTrack["title"] == "Pista 1"
    assert ctrl.queueItems()[2]["current"] is True
    ctrl.moveInQueue(9, 0)  # inválido: se ignora


def test_clear_queue_keeps_the_current_track_playing(env):
    ctrl, be, album, _, _ = env
    ctrl.playAlbum(album, 1)
    ctrl.clearQueue()
    assert titles(ctrl) == ["Pista 2"] and ctrl.playing and be.state == "playing"
    assert ctrl.currentTrack["title"] == "Pista 2" and ctrl.hasTrack
    ctrl.removeFromQueue(0)   # quitar la \u00fanica y actual s\u00ed la detiene
    assert not ctrl.hasTrack and not ctrl.playing and be.state == "stopped" and ctrl.queueLength == 0
    ctrl.addToQueue([_ids(ctrl, "Pista 1")])   # nada suena: vaciar la deja vac\u00eda
    ctrl.clearQueue()
    assert ctrl.queueLength == 0


def test_current_track_exposes_artist_and_album_links(env):
    ctrl, _be, album, _, _ = env
    ctrl.playAlbum(album, 0)
    cur = ctrl.currentTrack
    assert cur["albumId"] == album and cur["artistId"] > 0 and cur["hasAlbum"] and cur["hasArtist"]


def test_unknown_track_ids_are_ignored(env):
    ctrl, *_ = env
    ctrl.addToQueue([99999])
    ctrl.playNext([99999])
    assert ctrl.queueLength == 0


def _ids(ctrl, title):
    row = ctrl._conn.execute("SELECT id FROM tracks WHERE title = ?", (title,)).fetchone()
    return row["id"]


def test_queue_track_ids_and_refresh_current_after_a_tag_edit(env):
    ctrl, _be, album, _, _paths = env
    ctrl.playAlbum(album, 1)
    assert ctrl.queueTrackIds() == [r["id"] for r in ctrl._conn.execute(
        "SELECT t.id FROM tracks t WHERE t.album_id = ? ORDER BY t.track_no", (album,))]
    changed = []
    ctrl.currentChanged.connect(lambda: changed.append(1))
    ctrl.refreshCurrent()
    assert changed == []  # nada cambió: no se avisa de nada
    with ctrl._conn:
        ctrl._conn.execute("UPDATE tracks SET title = 'Título corregido' WHERE id = ?",
                           (ctrl.currentId,))
    ctrl.refreshCurrent()
    assert ctrl.currentTrack["title"] == "Título corregido" and changed == [1]


def test_mute_toggles_without_losing_the_chosen_volume(env):
    ctrl, be, *_ = env
    ctrl.setVolume(0.6)
    ctrl.toggleMute()
    assert ctrl.muted and be.volume == 0.0 and ctrl.volume == 0.6          # silencio total; el volumen elegido se conserva
    ctrl.toggleMute()
    assert not ctrl.muted and be.volume == 0.6
    ctrl.toggleMute()
    ctrl.setVolume(0.3)                                                    # mover el volumen quita el silencio
    assert not ctrl.muted and be.volume == 0.3
