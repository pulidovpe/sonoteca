"""Prueba del backend real de QtMultimedia SIN salida de audio (el CI/sandbox puede no tener)."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6.QtMultimedia")

from conftest import make_mp3, make_mp4, needs_ffmpeg
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtGui import QGuiApplication

from sonoteca.player.qt_backend import QtPlayerBackend

pytestmark = needs_ffmpeg


def wait_for(signal, timeout_ms=5000):
    loop = QEventLoop()
    got = []
    signal.connect(lambda *a: (got.append(a), loop.quit()))
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    return got


def test_loads_mp3_and_reports_duration(tmp_path):
    QGuiApplication.instance() or QGuiApplication([])
    be = QtPlayerBackend(with_audio=False)
    be.load(make_mp3(tmp_path / "a.mp3", title="A"))
    got = wait_for(be.durationChanged)
    assert got, "el backend no informó la duración"
    assert got[0][0] == pytest.approx(1000, abs=250)


def test_missing_file_reports_failure(tmp_path):
    QGuiApplication.instance() or QGuiApplication([])
    be = QtPlayerBackend(with_audio=False)
    be.load(tmp_path / "no_existe.mp3")
    assert wait_for(be.failed), "debería informar un error"


def test_loads_mp4_video_and_reports_duration(tmp_path):
    """Comprueba que el Qt instalado decodifica MP4 (H.264 + AAC) con su backend FFmpeg."""
    QGuiApplication.instance() or QGuiApplication([])
    be = QtPlayerBackend(with_audio=False)
    be.load(make_mp4(tmp_path / "v.mp4", title="V"))
    got = wait_for(be.durationChanged)
    assert got, "el backend no informó la duración del video"
    assert got[0][0] == pytest.approx(1000, abs=300)
