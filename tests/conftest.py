"""Genera archivos multimedia reales y mínimos con ffmpeg (se omiten las pruebas si no hay)."""
from __future__ import annotations

import gc
import os
import shutil
import subprocess
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")

FFMPEG = shutil.which("ffmpeg")

needs_ffmpeg = pytest.mark.skipif(FFMPEG is None, reason="ffmpeg no disponible")


def make_cover(path: Path, color: str = "0x3366cc") -> Path:
    """JPEG cuadrado de un solo color (para pruebas de portadas)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"color=c={color}:s=600x600:d=1", "-frames:v", "1", str(path)], check=True)
    return path


def make_audio(path: Path, codec: str, cover: Path | None = None, **meta: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1"]
    if cover:
        cmd += ["-i", str(cover), "-map", "0:a", "-map", "1:v", "-c:v", "copy"]
        if path.suffix == ".m4a":
            cmd += ["-disposition:v:0", "attached_pic"]
    cmd += ["-c:a", codec]
    if path.suffix == ".mp3":
        cmd += ["-id3v2_version", "3"]
    for k, v in meta.items():
        cmd += ["-metadata", f"{k}={v}"]
    subprocess.run([*cmd, str(path)], check=True)
    return path


def make_mp3(path: Path, cover: Path | None = None, **meta: str) -> Path:
    return make_audio(path, "libmp3lame", cover, **meta)


def make_m4a(path: Path, cover: Path | None = None, **meta: str) -> Path:
    return make_audio(path, "aac", cover, **meta)


def make_mp4(path: Path, **meta: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "lavfi", "-i",
           "color=c=blue:s=64x64:d=1", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"]
    for k, v in meta.items():
        cmd += ["-metadata", f"{k}={v}"]
    subprocess.run([*cmd, str(path)], check=True)
    return path


@pytest.fixture
def library_dir(tmp_path: Path) -> Path:
    """Biblioteca de prueba: 2 álbumes de un artista + 1 m4a + 1 mp4 + 1 mp3 sin tags."""
    root = tmp_path / "music"
    make_mp3(root / "Beatles/Abbey Road/01.mp3", title="Come Together", artist="The Beatles",
             album="Abbey Road", date="1969", track="1/17", disc="1/1", genre="Rock")
    make_mp3(root / "Beatles/Abbey Road/02.mp3", title="Something", artist="The Beatles",
             album="Abbey Road", date="1969", track="2/17")
    make_mp3(root / "Beatles/Revolver/01.mp3", title="Taxman", artist="The Beatles",
             album="Revolver", date="1966-08-05", track="1/14")
    make_m4a(root / "Soda/Signos/01.m4a", title="Persiana Americana", artist="Soda Stereo",
             album="Signos", date="1986", track="3/9")
    make_mp4(root / "Videos/clip.mp4", title="Clip", artist="Soda Stereo", album="Videos")
    make_mp3(root / "suelto.mp3")  # sin tags
    return root


@pytest.fixture(scope="session")
def qapp():
    pytest.importorskip("PySide6.QtGui")
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def qml_env(qapp, db_file, tmp_path):
    """Motor QML con la ventana principal sobre la base `db_file` (cada módulo la define).

    Se destruye de forma explícita al terminar: si Python lo liberara en medio de otra prueba,
    podría bloquearse con los hilos de carga de imágenes.
    """
    from types import SimpleNamespace

    from fakes import FakeBackend
    from PySide6.QtCore import QCoreApplication, QEvent, QEventLoop, QTimer, QUrl
    from PySide6.QtQml import QQmlApplicationEngine, QQmlExpression

    from musicapp.ui.app import QML_DIR
    from musicapp.ui.controller import LibraryController
    from musicapp.ui.cover_provider import CoverProvider
    from musicapp.ui.lyrics_controller import LyricsController
    from musicapp.ui.online_controller import OnlineController
    from musicapp.ui.player_controller import PlayerController
    from musicapp.ui.playlist_controller import PlaylistController

    gc.collect()
    engine = QQmlApplicationEngine()
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
    controller = LibraryController(db_file)
    player = PlayerController(FakeBackend(), db_file)
    provider = CoverProvider(db_file, cache_dir=tmp_path / "cache")
    engine.addImageProvider("cover", provider)
    engine.rootContext().setContextProperty("library", controller)
    online = OnlineController(db_file)
    engine.rootContext().setContextProperty("player", player)
    playlists = PlaylistController(db_file)
    engine.rootContext().setContextProperty("online", online)
    engine.rootContext().setContextProperty("playlists", playlists)
    lyrics = LyricsController(db_file)
    engine.rootContext().setContextProperty("lyrics", lyrics)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    assert engine.rootObjects(), warnings
    win = engine.rootObjects()[0]

    def wait(ms):
        loop = QEventLoop()
        QTimer.singleShot(ms, loop.quit)
        loop.exec()

    def js(code):
        # Se deja terminar la carga de portadas antes de evaluar: destruir tarjetas con imágenes
        # en carga mientras Python tiene el GIL tomado puede bloquearse (no ocurre con app.exec()).
        wait(150)
        expr = QQmlExpression(engine.contextForObject(win), win, code)
        value, _undefined = expr.evaluate()  # PySide6 devuelve (valor, es_indefinido)
        assert not expr.hasError(), expr.error().toString()
        return value

    def act(code, settle=450):
        """Ejecuta `code` desde el bucle de eventos de QML (Qt.callLater), no desde Python:
        así la UI crea/destruye portadas sin que Python tenga el GIL tomado, como en la app real."""
        js("Qt.callLater(function () { " + code + " })")
        wait(settle)

    yield SimpleNamespace(engine=engine, win=win, controller=controller, player=player, online=online, playlists=playlists,
                          lyrics=lyrics, warnings=warnings, wait=wait, js=js, act=act)

    wait(500)  # deja terminar las cargas de imágenes pendientes antes de destruir el motor
    engine.deleteLater()
    for _ in range(10):
        qapp.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    del provider, controller, player, online, playlists, lyrics
    gc.collect()
