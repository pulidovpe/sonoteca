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


def test_finished_and_skipped_tracks_leave_the_queue(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 0)                                   # Pista 1, 2, 3
    be.finish()
    assert titles(ctrl) == ["Pista 2", "Pista 3"] and ctrl.currentTrack["title"] == "Pista 2"
    ctrl.playQueueAt(1)                                        # doble clic en la última: la que sonaba sale
    assert titles(ctrl) == ["Pista 3"] and str(be.loaded) == paths["Pista 3"]
    be.finish()                                                # termina la última: sale, pero sigue mostrándose
    assert titles(ctrl) == [] and ctrl.queueLength == 0
    assert ctrl.currentTrack["title"] == "Pista 3" and not ctrl.playing


def test_previous_after_consuming_brings_the_track_back(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 0)
    be.finish()                                                # sale Pista 1; suena Pista 2
    be.positionChanged.emit(1000)
    ctrl.previous()
    assert str(be.loaded) == paths["Pista 1"] and titles(ctrl) == ["Pista 1", "Pista 2", "Pista 3"]


def test_play_next_rows_are_flagged_until_they_start_playing(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 0)                                   # Pista 1, 2, 3
    ctrl.playNext([_ids(ctrl, "Pista 3")])
    ctrl.playNext([_ids(ctrl, "Pista 2")])                     # la última añadida suena antes que la anterior
    rows = ctrl.queueItems()
    assert [r["upNext"] for r in rows] == [False, True, True, False, False]
    assert [r["title"] for r in rows][1:3] == ["Pista 2", "Pista 3"]
    be.finish()                                                # empieza a sonar la primera «a continuación»
    rows = ctrl.queueItems()
    assert rows[0]["current"] and rows[0]["upNext"] is False and rows[1]["upNext"] is True


def test_play_from_remembers_the_source_and_other_starts_forget_it(env):
    ctrl, be, album, _, paths = env
    ids = [_ids(ctrl, f"Pista {n}") for n in (1, 2, 3)]
    ctrl.playFrom("playlist:7", ids[1:], 0)                    # clic en una canción: la lista empieza ahí
    assert ctrl.sourceKey == "playlist:7" and titles(ctrl) == ["Pista 2", "Pista 3"]
    ctrl.playOnly(ids[0])                                      # cualquier otra forma de empezar olvida el origen
    assert ctrl.sourceKey == "" and titles(ctrl) == ["Pista 1"]


def test_stop_playback_pauses_and_rewinds_without_touching_the_queue(env):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 0)
    be.positionChanged.emit(12000)
    ctrl.stopPlayback()
    assert not ctrl.playing and be.position == 0 and titles(ctrl) == ["Pista 1", "Pista 2", "Pista 3"]


def test_play_shuffled_turns_shuffle_on_and_keeps_every_song(env):
    ctrl, be, album, _, paths = env
    ids = [_ids(ctrl, f"Pista {n}") for n in (1, 2, 3)]
    ctrl.playShuffled("album:1", ids)
    assert ctrl.shuffle and ctrl.sourceKey == "album:1" and sorted(ctrl.queueTrackIds()) == sorted(ids)


def test_play_first_keeps_the_list_and_inserts_the_songs_first_even_with_shuffle(env):
    ctrl, be, album, _, paths = env
    ids = [_ids(ctrl, f"Pista {n}") for n in (1, 2, 3)]
    ctrl.playFrom("album:1", ids[:2], 0)                       # suena Pista 1; sigue Pista 2
    ctrl.playFirst([ids[2]])
    assert ctrl.currentTrack["title"] == "Pista 3" and titles(ctrl) == ["Pista 3", "Pista 2"]   # la que sonaba sale
    ctrl.toggleShuffle()
    ctrl.playFirst([ids[0]])                                   # con Aleatorio también va de primera
    assert ctrl.currentTrack["title"] == "Pista 1" and sorted(titles(ctrl)) == ["Pista 1", "Pista 2"]
    ctrl.clearQueue()
    ctrl.playFirst([ids[1]])
    assert ctrl.currentTrack["title"] == "Pista 2"


def _as_playing_video(ctrl, frames, position=2000, track_id=7):
    ctrl._current = {"id": track_id, "title": "Clip", "kind": "video"}
    ctrl._playing = True
    ctrl._position = position
    ctrl._backend.video_frames = lambda: frames


def test_video_without_frames_warns_once(env):
    ctrl, be, *_ = env
    msgs = []
    ctrl.errorMessage.connect(msgs.append)
    _as_playing_video(ctrl, frames=0)
    ctrl._check_video()
    ctrl._check_video()
    assert len(msgs) == 1 and "Clip" in msgs[0] and "solo el audio" in msgs[0]


def test_video_with_frames_or_unknown_engine_or_too_early_does_not_warn(env):
    ctrl, be, *_ = env
    msgs = []
    ctrl.errorMessage.connect(msgs.append)
    for frames, position in ((5, 2000), (-1, 2000), (0, 800)):    # se ve / el motor no lo sabe / aún es pronto
        _as_playing_video(ctrl, frames, position)
        ctrl._check_video()
    assert msgs == []


def test_audio_track_never_warns_about_video(env):
    ctrl, be, *_ = env
    msgs = []
    ctrl.errorMessage.connect(msgs.append)
    _as_playing_video(ctrl, frames=0)
    ctrl._current["kind"] = "audio"
    ctrl._check_video()
    assert msgs == []


def _track_path(ctrl):
    from sonoteca.core import library
    return library.get_track(ctrl._conn, ctrl.currentId)["path"]


@pytest.fixture
def flushes(env, tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    ctrl, be, album, _, paths = env
    got = []
    ctrl.pendingFlush.connect(got.append)
    return got


def _mark_pending(path):
    from pathlib import Path

    from sonoteca.core import pending_tags
    pending_tags.pending_path(Path(path)).write_bytes(b"x")


def test_is_loaded_and_flush_is_requested_when_the_track_changes(env, flushes):
    ctrl, be, album, _, paths = env
    ctrl.playAlbum(album, 0)
    assert ctrl.isLoaded(paths["Pista 1"]) and not ctrl.isLoaded(paths["Pista 2"])
    assert flushes == [paths["Pista 1"]]                     # al cargar una pista se pide volcar lo anterior (menos ella)
    be.finish()
    assert ctrl.isLoaded(paths["Pista 2"]) and not ctrl.isLoaded(paths["Pista 1"])
    assert flushes[-1] == paths["Pista 2"]


def test_end_of_queue_releases_a_file_with_deferred_tags_and_play_reloads_it(env, flushes):
    ctrl, be, album, _, paths = env
    released = []
    be.release = lambda: released.append(1)
    ctrl.playAlbum(album, 2)                                 # la última pista
    _mark_pending(paths["Pista 3"])
    be.finish()                                              # termina la lista
    assert released == [1] and not ctrl.isLoaded(paths["Pista 3"])
    assert flushes[-1] == ""                                 # nada sigue abierto: se puede volcar todo
    ctrl.toggle()                                            # play: se vuelve a cargar
    assert str(be.loaded) == paths["Pista 3"] and ctrl.isLoaded(paths["Pista 3"]) and ctrl.playing


def test_end_of_queue_keeps_the_file_loaded_when_nothing_is_pending(env, flushes):
    ctrl, be, album, _, paths = env
    released = []
    be.release = lambda: released.append(1)
    ctrl.playAlbum(album, 2)
    be.finish()
    assert released == [] and ctrl.isLoaded(paths["Pista 3"])
    assert flushes[-1] == paths["Pista 3"]


def test_refresh_current_releases_a_stopped_track_with_deferred_tags(env, flushes):
    ctrl, be, album, _, paths = env
    released = []
    be.release = lambda: released.append(1)
    ctrl.playAlbum(album, 2)
    be.finish()                                              # terminó; sigue cargada (sin pendientes)
    _mark_pending(paths["Pista 3"])                          # se edita estando parada
    ctrl.refreshCurrent()
    assert released == [1] and not ctrl.isLoaded(paths["Pista 3"])


def test_release_all_on_quit(env, flushes):
    ctrl, be, album, _, paths = env
    released = []
    be.release = lambda: released.append(1)
    ctrl.playAlbum(album, 0)
    ctrl.releaseAll()
    assert released == [1] and not ctrl.isLoaded(paths["Pista 1"])


def test_session_is_saved_and_restored_paused(env, tmp_path):
    import json
    ctrl, be, album, _, paths = env
    state = tmp_path / "session.json"
    ctrl2 = PlayerController(be, ctrl._conn.execute("PRAGMA database_list").fetchone()[2], state_path=state)
    ctrl2.playAlbum(album, 1)                                # suena «Pista 2»; quedan 2 y 3 en la lista
    ctrl2.setVolume(0.3)
    ctrl2.toggleShuffle()
    ctrl2.cycleRepeat()
    ctrl2._position = 5000
    ctrl2.saveState()
    saved = json.loads(state.read_text(encoding="utf-8"))
    assert saved["volume"] == 0.3 and saved["shuffle"] is True and saved["repeat"] == "all"
    assert paths["Pista 2"] in saved["queue"]["items"]

    fresh_be = FakeBackend()
    fresh = PlayerController(fresh_be, ctrl._conn.execute("PRAGMA database_list").fetchone()[2], state_path=state)
    assert fresh.restoreState() is True
    assert fresh.volume == 0.3 and fresh.shuffle and fresh.repeatMode == "all"
    assert fresh.currentTrack["title"] == "Pista 2" and not fresh.playing    # recuperada, pero sin sonar sola
    assert fresh.queueTrackIds() == ctrl2.queueTrackIds()
    assert fresh_be.state == "paused" and fresh_be.seeks == [5000]
    assert fresh.position == 5000


def test_restore_without_a_saved_session_does_nothing(env, tmp_path):
    ctrl, be, *_ = env
    other = PlayerController(FakeBackend(), ctrl._conn.execute("PRAGMA database_list").fetchone()[2],
                             state_path=tmp_path / "nada.json")
    assert other.restoreState() is False and not other.hasTrack
    assert PlayerController(FakeBackend(), None).restoreState() is False     # sin state_path no hay sesión
