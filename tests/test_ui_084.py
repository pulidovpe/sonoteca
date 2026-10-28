"""0.8.4 con Qt: salida de audio, búsqueda de música, elegir artista y collage."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

import time

import pytest

pytest.importorskip("PySide6.QtQml")

from conftest import make_cover, make_mp3, needs_ffmpeg
from fakes import FakeBackend
from test_ui_edit import album_ids

from sonoteca.ui.player_controller import PlayerController
from sonoteca.ui.scan_controller import ScanController, suggested_folders


class AudioBackend(FakeBackend):
    """Backend con dos salidas de audio simuladas."""
    def __init__(self):
        super().__init__()
        self.outputs = [{"id": "spk", "name": "Parlantes", "isDefault": True},
                        {"id": "bt", "name": "Audífonos Bluetooth", "isDefault": False}]
        self.chosen = ""

    def audio_devices(self): return list(self.outputs)
    def audio_device(self): return self.chosen
    def set_audio_device(self, device_id):
        if device_id and device_id not in [o["id"] for o in self.outputs]:
            return False
        self.chosen = device_id
        self.audioDevicesChanged.emit()
        return True


@pytest.fixture
def audio_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    from sonoteca.core.db import connect
    db = tmp_path / "a.db"
    connect(db).close()
    return AudioBackend(), db, tmp_path


def test_audio_devices_list_choice_is_remembered_and_unplugged_falls_back(qapp, audio_env):
    be, db, tmp = audio_env
    ctrl = PlayerController(be, db)
    devices = ctrl.audioDevices()
    assert [d["id"] for d in devices] == ["", "spk", "bt"] and devices[0]["current"] is True
    assert "predeterminada" in devices[1]["name"]
    ctrl.setAudioDevice("bt")
    assert be.chosen == "bt" and ctrl.audioDeviceName == "Audífonos Bluetooth"
    assert [d["id"] for d in ctrl.audioDevices() if d["current"]] == ["bt"]
    # la elección se recuerda para la próxima vez
    be2 = AudioBackend()
    PlayerController(be2, db)
    assert be2.chosen == "bt"
    # una salida que ya no está conectada: aviso y se sigue en automático
    msgs = []
    ctrl.queueMessage.connect(msgs.append)
    be.outputs = [be.outputs[0]]
    ctrl.setAudioDevice("bt")
    assert msgs and "ya no está disponible" in msgs[-1]
    ctrl.setAudioDevice("")
    assert be.chosen == "" and ctrl.audioDeviceName == "Automático"


def test_scan_controller_scans_folders_and_reports(qapp, tmp_path, monkeypatch):
    if not os.path.exists("/usr/bin/ffmpeg") and not any(os.access(os.path.join(p, "ffmpeg"), os.X_OK) for p in os.environ["PATH"].split(os.pathsep)):
        pytest.skip("necesita ffmpeg")
    monkeypatch.setenv("SONOTECA_DATA_DIR", str(tmp_path / "datos"))
    cover = make_cover(tmp_path / "c.jpg")
    make_mp3(tmp_path / "musica/Artista/1.mp3", cover, title="Uno", artist="Artista", album="Disco")
    make_mp3(tmp_path / "musica/Artista/2.mp3", cover, title="Dos", artist="Artista", album="Disco")
    db = tmp_path / "s.db"
    c = ScanController(db)
    results, errors = [], []
    c.scanFinished.connect(results.append)
    c.scanError.connect(errors.append)
    c.scan([])
    assert errors == ["Elige al menos una carpeta"]
    c.scan([str(tmp_path / "musica")])
    end = time.time() + 20
    while not results and time.time() < end:
        qapp.processEvents(); time.sleep(0.02)
    assert results and results[0]["added"] == 2 and results[0]["folders"] == 1
    from sonoteca.core.db import connect
    assert connect(db).execute("SELECT COUNT(*) FROM tracks").fetchone()[0] == 2


def test_suggested_folders_only_existing(qapp):
    for folder in suggested_folders():
        assert os.path.isdir(folder["path"]) and isinstance(folder["checked"], bool)


@needs_ffmpeg
def test_scan_dialog_and_home_after_menu_action(qml_env):
    env = qml_env
    env.act("actScan.trigger()", 400)
    assert env.js("scanDialog.visible") is True and env.js("scanDialog.firstRun") is False
    env.act("scanDialog.addFolder('/tmp/musica-x')", 200)
    assert env.js("scanDialog.selectedPaths().indexOf('/tmp/musica-x') >= 0") is True
    env.act("scanDialog.close()", 200)
    assert env.warnings == []


@needs_ffmpeg
def test_artist_manual_description_and_wrong_artist_dialog(qml_env, tmp_path):
    env = qml_env
    artist = env.controller.artists()[0]
    photo = make_cover(tmp_path / "foto.jpg")
    result = env.online.saveManualArtistInfo(artist["id"], "  Una descripción propia.  ", str(photo))
    assert result["ok"] and result["info"]["bio"] == "Una descripción propia." and result["info"]["source"] == "Manual"
    assert result["info"]["imagePath"].endswith(".jpg")
    bad = env.online.saveManualArtistInfo(artist["id"], "   ", "")
    assert bad["ok"] is False and "vacía" in bad["error"]
    env.act(f"openArtist({artist['id']}, 'X')", 500)
    assert env.warnings == []


@needs_ffmpeg
def test_home_list_cards_use_collage_component(qml_env):
    env = qml_env
    _, ids = album_ids(env.controller)
    pid = env.playlists.createWithTracks("Collage", ids)["id"]
    assert len(env.playlists.coverAlbums(pid)) == 1          # una sola fuente: portada simple
    env.act("showSection('home')", 500)
    assert env.js("stack.currentItem.homeData.lists.length") == 1
    assert env.warnings == []
