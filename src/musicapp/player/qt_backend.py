"""Backend con QtMultimedia (FFmpeg en escritorio)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

from .backend import PlayerBackend

_STATES = {
    QMediaPlayer.PlaybackState.PlayingState: "playing",
    QMediaPlayer.PlaybackState.PausedState: "paused",
    QMediaPlayer.PlaybackState.StoppedState: "stopped",
}


class QtPlayerBackend(PlayerBackend):
    def __init__(self, with_audio: bool = True, parent=None) -> None:
        """`with_audio=False` omite la salida de sonido (pruebas en máquinas sin audio)."""
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio: QAudioOutput | None = None
        if with_audio:
            self._audio = QAudioOutput(self)
            self._player.setAudioOutput(self._audio)
        # Qt emite qint64; las señales de PlayerBackend son int (ms alcanza de sobra)
        self._player.positionChanged.connect(lambda ms: self.positionChanged.emit(int(ms)))
        self._player.durationChanged.connect(lambda ms: self.durationChanged.emit(int(ms)))
        self._player.playbackStateChanged.connect(
            lambda s: self.stateChanged.emit(_STATES.get(s, "stopped")))
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(lambda _err, text: self.failed.emit(text))

    def _on_media_status(self, status) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.ended.emit()

    def load(self, path: Path) -> None:
        self._player.setSource(QUrl.fromLocalFile(str(path)))

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def seek(self, ms: int) -> None:
        self._player.setPosition(ms)

    def set_volume(self, volume: float) -> None:
        if self._audio is not None:
            # La percepción del volumen es logarítmica: una curva cuadrática se siente más natural
            self._audio.setVolume(max(0.0, min(1.0, volume)) ** 2)

    def set_video_sink(self, sink) -> None:
        self._player.setVideoSink(sink)
