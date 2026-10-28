"""Arranque de la interfaz QML."""
from __future__ import annotations

import os
import sys
from pathlib import Path

QML_DIR = Path(__file__).parent / "qml"
ICON_PATH = Path(__file__).parent / "icon.png"   # icono de la ventana (se empaqueta junto al QML)


def run(db_path: Path | str | None = None, argv: list[str] | None = None) -> int:
    # El estilo "Basic" permite personalizar los controles por completo
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine

    from sonoteca.player.qt_backend import QtPlayerBackend

    from .controller import LibraryController
    from .cover_provider import CoverProvider
    from .lyrics_controller import LyricsController
    from .online_controller import OnlineController
    from .harvest_controller import HarvestController
    from .player_controller import PlayerController
    from .portable_controller import PortableController
    from .servers_controller import ServersController
    from .playlist_controller import PlaylistController
    from .scan_controller import ScanController

    if db_path is None:   # arranque normal: traer los datos de la versión anterior («musicapp») si los hay
        from sonoteca.core import legacy

        report = legacy.ensure_migrated()
        if report is not None and (report.migrated or report.errors):
            print(f"[sonoteca] migraci\u00f3n desde musicapp: {len(report.moved)} elementos movidos, "
                  f"{report.rewritten_paths} rutas de portadas reescritas, errores: {report.errors}", file=sys.stderr)

        from sonoteca.core import portable

        applied = portable.apply_pending_import()   # importaci\u00f3n preparada en la sesi\u00f3n anterior (antes de abrir la base)
        if applied:
            print(f"[sonoteca] biblioteca importada; copia de la anterior en {applied['backup']}", file=sys.stderr)
        cleared = portable.apply_pending_reset()   # «empezar desde cero» preparado en la sesi\u00f3n anterior
        if cleared:
            print(f"[sonoteca] biblioteca vaciada (copia en {cleared['backup'] or 'ninguna'})", file=sys.stderr)

    app = QGuiApplication(argv if argv is not None else sys.argv)
    if ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(ICON_PATH)))   # barra de tareas / Dock / ventana (el icono del archivo lo pone el empaquetado)
    app.setApplicationName("sonoteca")
    app.setApplicationDisplayName("Sonoteca")
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
    harvester = HarvestController(db_path)
    engine.rootContext().setContextProperty("harvest", harvester)
    portable_io = PortableController(db_path)
    engine.rootContext().setContextProperty("portable", portable_io)
    server_config = ServersController()
    engine.rootContext().setContextProperty("serverConfig", server_config)
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        return 1
    return app.exec()


def main() -> int:
    return run()
