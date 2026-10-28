"""Backend con QtMultimedia (FFmpeg en escritorio)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaDevices, QMediaPlayer

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
        self._device_id = ""  # "" = automática: sigue la salida predeterminada del sistema
        self._applied_default = ""
        if with_audio:
            self._audio = QAudioOutput(self)
            self._player.setAudioOutput(self._audio)
            self._devices = QMediaDevices(self)
            self._devices.audioOutputsChanged.connect(self._on_outputs_changed)
            # Algunos sistemas cambian la salida predeterminada (al conectar audífonos) sin avisar
            # con la señal anterior: se revisa cada par de segundos
            self._watch = QTimer(self)
            self._watch.setInterval(2000)
            self._watch.timeout.connect(self._follow_default)
            self._watch.start()
            self._follow_default()
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

    # ---- salida de audio ----
    @staticmethod
    def _id(device) -> str:
        return bytes(device.id()).decode("utf-8", "replace")

    def audio_devices(self) -> list[dict]:
        if self._audio is None:
            return []
        return [{"id": self._id(d), "name": d.description(), "isDefault": d.isDefault()}
                for d in QMediaDevices.audioOutputs()]

    def audio_device(self) -> str:
        return self._device_id

    def set_audio_device(self, device_id: str) -> bool:
        if self._audio is None:
            return False
        if not device_id:
            self._device_id = ""
            self._applied_default = ""
            self._follow_default()
            self.audioDevicesChanged.emit()
            return True
        for device in QMediaDevices.audioOutputs():
            if self._id(device) == device_id:
                self._device_id = device_id
                self._audio.setDevice(device)
                self.audioDevicesChanged.emit()
                return True
        return False

    def _follow_default(self) -> None:
        """En modo automático, usa siempre la salida predeterminada actual del sistema."""
        if self._audio is None or self._device_id:
            return
        default = QMediaDevices.defaultAudioOutput()
        key = self._id(default)
        if key != self._applied_default:
            self._applied_default = key
            self._audio.setDevice(default)
            self.audioDevicesChanged.emit()

    def _on_outputs_changed(self) -> None:
        if self._device_id and not any(self._id(d) == self._device_id for d in QMediaDevices.audioOutputs()):
            self._device_id = ""      # la salida elegida se desconectó: vuelve a automático
            self._applied_default = ""
        self._follow_default()
        self.audioDevicesChanged.emit()
