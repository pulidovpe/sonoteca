import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtCore")

from test_playlists import conn as _seed_conn  # noqa: F401  (reutiliza los datos de ejemplo)

from musicapp.core.db import connect
from musicapp.ui.playlist_controller import PlaylistController


@pytest.fixture
def ctrl(tmp_path):
    db = tmp_path / "t.db"
    seed = connect(db)
    seed.executescript("""
    INSERT INTO artists (id, name, sort_name) VALUES (1, 'A', 'A');
    INSERT INTO albums (id, title, album_artist_id) VALUES (1, 'Disco', 1), (2, 'Álbum desconocido', 1);
    INSERT INTO files (id, path, size, mtime_ns, format, kind) VALUES
        (1,'/1.mp3',1,1,'mp3','audio'),(2,'/2.mp3',1,1,'mp3','audio');
    INSERT INTO tracks (id, file_id, album_id, artist_id, title, duration) VALUES
        (1, 1, 1, 1, 'Uno', 60), (2, 2, 2, 1, 'Dos', 120);
    """)
    seed.close()
    return PlaylistController(db)


def test_create_reports_errors_as_data_and_notifies(ctrl):
    msgs, changes = [], []
    ctrl.message.connect(msgs.append)
    ctrl.changed.connect(lambda: changes.append(1))
    r = ctrl.create(" Rock ")
    assert r["ok"] and r["id"] and ctrl.count == 1 and ctrl.revision == 1 and changes
    assert msgs == ["Lista «Rock» creada"]
    dup = ctrl.create("rock")
    assert dup["ok"] is False and "Ya existe" in dup["error"] and ctrl.revision == 1  # sin cambios
    assert ctrl.create("")["ok"] is False


def test_add_tracks_messages_and_listing(ctrl):
    msgs = []
    ctrl.message.connect(msgs.append)
    pid = ctrl.create("Mi lista")["id"]
    assert ctrl.addTracks(pid, [1])["added"] == 1
    assert msgs[-1] == "1 canción agregada a «Mi lista»"
    assert ctrl.addTracks(pid, [1, 2])["added"] == 2
    assert msgs[-1] == "2 canciones agregadas a «Mi lista»"
    assert ctrl.addTracks(pid, [999])["added"] == 0  # nada que agregar: sin aviso nuevo
    assert len(msgs) == 3
    row = ctrl.lists()[0]
    assert (row["name"], row["tracks"], row["duration"]) == ("Mi lista", 3, 240)
    assert [t["title"] for t in ctrl.tracks(pid)] == ["Uno", "Uno", "Dos"]
    assert ctrl.tracks(pid)[2]["album"] == "Sin álbum"  # como en el resto de la app
    assert ctrl.trackIds(pid) == [1, 1, 2] and ctrl.info(pid)["tracks"] == 3
    assert ctrl.addTracks(999, [1])["ok"] is False


def test_create_with_tracks_rename_move_remove_and_delete(ctrl):
    msgs = []
    ctrl.message.connect(msgs.append)
    pid = ctrl.createWithTracks("Cola guardada", [2, 1])["id"]
    assert msgs[-1] == "Lista «Cola guardada» creada con 2 canciones"
    assert ctrl.moveTrack(pid, 1, 0)["ok"] and ctrl.trackIds(pid) == [1, 2]
    assert ctrl.moveTrack(pid, 0, 9)["ok"] is False
    assert ctrl.removeAt(pid, 0)["ok"] and ctrl.trackIds(pid) == [2]
    assert ctrl.removeAt(pid, 5)["ok"] is False
    assert ctrl.rename(pid, "Otro nombre")["ok"] and ctrl.info(pid)["name"] == "Otro nombre"
    assert ctrl.createWithTracks("otro NOMBRE", [1])["ok"] is False
    assert ctrl.remove(pid)["ok"] and ctrl.count == 0 and msgs[-1] == "Lista «Otro nombre» eliminada"
    assert ctrl.info(pid) == {}
