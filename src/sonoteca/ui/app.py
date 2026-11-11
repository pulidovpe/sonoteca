"""Arranque de la interfaz QML."""
from __future__ import annotations

import os
import sys
from pathlib import Path

QML_DIR = Path(__file__).parent / "qml"
ICON_PATH = Path(__file__).parent / "icon.png"   # icono de la ventana (se empaqueta junto al QML)


def run(db_path: Path | str | None = None, argv: list[str] | None = None) -> int:
    # SONOTECA_DEBUG_TIMING=1: escribe en stderr cuánto tarda cada fase del arranque (desde que empieza `run`)
    import time

    t0 = time.perf_counter()
    timing = bool(os.environ.get("SONOTECA_DEBUG_TIMING"))

    def mark(label: str) -> None:
        if timing:
            print(f"[tiempos] {label}: {(time.perf_counter() - t0) * 1000:.0f} ms", file=sys.stderr)

    # El estilo "Basic" permite personalizar los controles por completo
    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
    # Silencia el aviso informativo de Qt Multimedia («Using Qt multimedia with FFmpeg…»); los avisos de error siguen saliendo
    os.environ.setdefault("QT_LOGGING_RULES", "qt.multimedia.ffmpeg.info=false")
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine

    from sonoteca.core import session
    from sonoteca.player.qt_backend import QtPlayerBackend

    from .controller import LibraryController
    from .cover_provider import CoverProvider
    from .lyrics_controller import LyricsController
    from .online_controller import OnlineController
    from .harvest_controller import HarvestController
    from .player_controller import PlayerController
    from .media_keys import MediaKeys
    from .portable_controller import PortableController
    from .servers_controller import ServersController
    from .playlist_controller import PlaylistController
    from .prefs_controller import PrefsController
    from .scan_controller import ScanController
    from .folders_controller import FoldersController

    mark("imports de Qt y de la aplicación")
    if db_path is None:   # arranque normal: traer los datos de la versión anterior («musicapp») si los hay
        from sonoteca.core import legacy

        report = legacy.ensure_migrated()
        if report is not None and (report.migrated or report.errors):
            print(f"[sonoteca] migración desde musicapp: {len(report.moved)} elementos movidos, "
                  f"{report.rewritten_paths} rutas de portadas reescritas, errores: {report.errors}", file=sys.stderr)

        from sonoteca.core import portable

        applied = portable.apply_pending_import()   # importación preparada en la sesión anterior (antes de abrir la base)
        if applied:
            print(f"[sonoteca] biblioteca importada; copia de la anterior en {applied['backup']}", file=sys.stderr)
        cleared = portable.apply_pending_reset()   # «empezar desde cero» preparado en la sesión anterior
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
    player = PlayerController(backend, db_path, state_path=session.default_path())
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
    library_folders = FoldersController(db_path)
    engine.rootContext().setContextProperty("libraryFolders", library_folders)
    harvester = HarvestController(db_path)
    engine.rootContext().setContextProperty("harvest", harvester)
    portable_io = PortableController(db_path)
    engine.rootContext().setContextProperty("portable", portable_io)
    server_config = ServersController()
    engine.rootContext().setContextProperty("serverConfig", server_config)
    ui_prefs = PrefsController()
    engine.rootContext().setContextProperty("prefs", ui_prefs)

    # Teclas multimedia (reproducir/pausa, siguiente, anterior): en la app y, en macOS, tambi\u00e9n globales
    media = MediaKeys()
    media.toggleRequested.connect(player.toggle)
    media.pauseRequested.connect(lambda: player.toggle() if player.playing else None)
    media.nextRequested.connect(player.next)
    media.previousRequested.connect(player.previous)

    def publish_now_playing() -> None:
        track = player.currentTrack or {}
        media.publish(track.get("title", ""), track.get("artist", ""), track.get("album", ""), player.duration,
                      player.position, player.playing, player.hasTrack)

    # Windows: la escritura de tags de la pista que suena se aplaza (core/pending_tags.py) y se vuelca al quedar libre el
    # archivo: al cambiar de pista, terminar la lista, cerrar la app o, si la app se cerró de golpe, al arrancar.
    controller.set_busy_check(player.isLoaded)
    player.pendingFlush.connect(controller.flushPending)
    controller.flushPendingNow(attempts=3)       # restos de una sesión anterior (nada suena todavía)
    player.restoreState()                        # lista, pista (en pausa), Aleatorio y volumen de la sesión anterior
    player.playingChanged.connect(publish_now_playing)
    player.currentChanged.connect(publish_now_playing)
    player.durationChanged.connect(publish_now_playing)
    media.install(app)
    mark("base de datos y controladores listos")
    engine.load(QUrl.fromLocalFile(str(QML_DIR / "Main.qml")))
    if not engine.rootObjects():
        return 1
    mark("QML cargado")
    if timing:
        try:
            window = engine.rootObjects()[0]

            def first_frame() -> None:
                mark("primer fotograma en pantalla")
                window.frameSwapped.disconnect(first_frame)

            window.frameSwapped.connect(first_frame)
        except Exception as exc:  # noqa: BLE001  (solo diagnóstico: nunca debe impedir el arranque)
            print(f"[tiempos] no se pudo medir el primer fotograma: {exc}", file=sys.stderr)
    code = app.exec()
    player.saveState()                           # lista, pista, punto, Aleatorio, volumen…
    player.releaseAll()                          # suelta el archivo que suena y vuelca los tags aplazados antes de salir
    controller.flushPendingNow()
    # Cierre ordenado: primero se destruye la interfaz QML y después los controladores. Si Python libera los
    # controladores antes, los enlaces QML que siguen vivos leen `library` o `playlists` ya destruidos y salen
    # errores como «Cannot call method 'stats' of null» al cerrar la ventana.
    del engine
    return code


def main() -> int:
    return run()
