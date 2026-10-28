"""Interfaz del motor de audio/video. La app solo depende de esto, no de QtMultimedia,
así se puede cambiar a mpv o VLC si hiciera falta (p. ej. por reproducción sin pausas)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal


class PlayerBackend(QObject):
    positionChanged = Signal(int)  # ms
    durationChanged = Signal(int)  # ms
    stateChanged = Signal(str)  # "playing" | "paused" | "stopped"
    ended = Signal()  # la pista terminó de forma natural
    failed = Signal(str)  # mensaje de error

    def load(self, path: Path) -> None:
        raise NotImplementedError

    def play(self) -> None:
        raise NotImplementedError

    def pause(self) -> None:
        raise NotImplementedError

    def stop(self) -> None:
        raise NotImplementedError

    def seek(self, ms: int) -> None:
        raise NotImplementedError

    def set_volume(self, volume: float) -> None:
        """0.0 a 1.0 (posición del control, el backend aplica la curva)."""
        raise NotImplementedError

    def set_video_sink(self, sink) -> None:
        raise NotImplementedError
