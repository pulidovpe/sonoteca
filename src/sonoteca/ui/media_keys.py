"""Teclas multimedia: reproducir/pausa, siguiente y anterior.

Dos vías, porque cada sistema las entrega de forma distinta:
  · Dentro de la aplicación (Windows, Linux y Mac con teclados que las envían): un filtro de eventos de Qt las
    reconoce cuando la ventana tiene el foco.
  · Globales, con la aplicación en segundo plano: en macOS, `MPRemoteCommandCenter` (ver media_keys_macos.py).
    En Windows y Linux (MPRIS) NO están implementadas todavía.
"""
from __future__ import annotations

import os
import sys

from PySide6.QtCore import QEvent, QObject, Qt, Signal

# Tecla de Qt -> acción. Play y Play/Pausa se tratan igual: en los teclados es la misma tecla.
KEY_COMMANDS = {
    "Key_MediaTogglePlayPause": "toggle",
    "Key_MediaPlay": "toggle",
    "Key_MediaPause": "pause",
    "Key_MediaNext": "next",
    "Key_MediaPrevious": "previous",
    "Key_MediaStop": "pause",
}


def _debug() -> bool:
    return bool(os.environ.get("SONOTECA_DEBUG_MEDIA"))


class _KeyFilter(QObject):
    def __init__(self, owner: "MediaKeys") -> None:
        super().__init__(owner)
        self._owner = owner
        self._keys = {getattr(Qt.Key, name): command for name, command in KEY_COMMANDS.items() if hasattr(Qt.Key, name)}

    def eventFilter(self, obj, event):  # noqa: N802  (nombre fijo de Qt)
        if event.type() == QEvent.Type.KeyPress and not event.isAutoRepeat():
            command = self._keys.get(event.key())
            if command:
                self._owner.dispatch(command, "teclado")
                return True
        return False


class MediaKeys(QObject):
    toggleRequested = Signal()
    pauseRequested = Signal()
    nextRequested = Signal()
    previousRequested = Signal()
    _remote = Signal(str)       # desde el sistema (posiblemente otro hilo): la conexión en cola lo pasa al hilo de Qt

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._filter = _KeyFilter(self)
        self._system = None
        self.status = "solo con la ventana en primer plano"
        self._remote.connect(lambda name: self.dispatch(name, "sistema"))

    def dispatch(self, command: str, origin: str = "") -> None:
        if _debug():
            print(f"[sonoteca] tecla multimedia: {command} ({origin})", file=sys.stderr)
        signal = {"toggle": self.toggleRequested, "play": self.toggleRequested, "pause": self.pauseRequested,
                  "next": self.nextRequested, "previous": self.previousRequested}.get(command)
        if signal is not None:
            signal.emit()

    def install(self, app: QObject) -> None:
        app.installEventFilter(self._filter)
        if sys.platform == "darwin":
            try:
                from .media_keys_macos import MacRemoteControls

                self._system = MacRemoteControls(self._remote.emit)
                self.status = "globales (macOS) y con la ventana en primer plano"
            except Exception as exc:  # noqa: BLE001  (sin PyObjC la app funciona igual, sin teclas globales)
                self.status = f"solo con la ventana en primer plano; teclas globales no disponibles ({exc})"
        if _debug() or self._system is None and sys.platform == "darwin":
            print(f"[sonoteca] teclas multimedia: {self.status}", file=sys.stderr)

    def publish(self, title: str, artist: str, album: str, duration_ms: int, position_ms: int, playing: bool,
                has_track: bool) -> None:
        """Informa al sistema de qué suena (macOS usa esto para enviarnos las teclas a nosotros)."""
        if self._system is None:
            return
        try:
            self._system.update(title, artist, album, duration_ms / 1000, position_ms / 1000, playing, has_track)
        except Exception as exc:  # noqa: BLE001
            self._system = None
            self.status = f"se desactivó la integración con el sistema ({exc})"
            print(f"[sonoteca] {self.status}", file=sys.stderr)
