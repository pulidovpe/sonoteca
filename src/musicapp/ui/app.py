"""Arranque de la interfaz QML."""
from __future__ import annotations

import os
import sys
from pathlib import Path

QML_DIR = Path(__file__).parent / "qml"


def run(db_path: Path | str | None = None, argv: list[str] | None = None) -> int:
    # El estilo "Basic" permite personalizar los controles por completo
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine

    from musicapp.player.qt_backend import QtPlayerBackend

    from .controller import LibraryController
    from .cover_provider import CoverProvider
    from .lyrics_controller import LyricsController
    from .online_controller import OnlineController
    from .player_controller import PlayerController
    from .playlist_controller import PlaylistController
    from .scan_controller import ScanController

    app = QGuiApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("musicapp")
    engine = QQmlApplicationEngine()
    controller = LibraryController(db_path)
    provider = CoverProvider(db_path)
    engine.addImageProvider("cover", provider)
    backend = QtPlayerBackend()
    player = PlayerController(backend, db_path)
    engine.rootContext().setContextProperty("library", controller)
    online = OnlineController(db_path)
    engine.rootContext().setContextProperty("player", player)
    playlists = PlaylistController(db_path)
    engine.rootContext().setContextProperty("online", online)
    engine.rootContext().setContextProperty("playlists", playlists)
    lyrics = LyricsController(db_path)
    engine.rootContext().setContextProperty("lyrics", lyrics)
    scan = ScanController(db_path)
    engine.rootContext().setContextProperty("scanner", scan)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


def main() -> int:
    return run()
