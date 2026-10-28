"""0.8.1 con Qt: contador al reproducir, nombre «Reproduciendo» y badge En línea clicable."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtCore")

from conftest import needs_ffmpeg
from test_player_controller import env  # noqa: F401  (fixture)

pytestmark = needs_ffmpeg


def test_play_counts_after_listening_half_and_not_on_seek(env):  # noqa: F811
    ctrl, be, album, _, _ = env
    ctrl.playAlbum(album, 0)
    tid = ctrl.currentId
    rev = ctrl.statsRevision
    be.positionChanged.emit(0)
    be.positionChanged.emit(5000)          # salto con la barra: no cuenta como escuchar
    assert ctrl.playsOf(tid) == 0
    be.positionChanged.emit(5300)
    be.positionChanged.emit(5700)          # 700 ms escuchados >= mitad de ~1 s
    assert ctrl.playsOf(tid) == 1 and ctrl.statsRevision == rev + 1
    be.positionChanged.emit(5900)
    be.positionChanged.emit(6300)
    assert ctrl.playsOf(tid) == 1          # una sola vez por reproducción
    ctrl.playAlbum(album, 0)               # volver a empezar la pista cuenta otra
    be.positionChanged.emit(0); be.positionChanged.emit(400); be.positionChanged.emit(800)
    assert ctrl.playsOf(tid) == 2


def test_menu_says_reproduciendo_and_badge_toggles_offline(qml_env):
    env = qml_env
    assert env.js("actQueue.text") == "Reproduciendo"
    start = env.js("online.offline")
    env.act("badgeMouse.clicked(null)", 100)   # clic en la frase «En línea»
    assert env.js("online.offline") is (not start)
    assert ("Sin conexi" in env.js("onlineBadge.text")) == (not start)
    env.act("badgeMouse.clicked(null)", 100)
    assert env.js("online.offline") is start
