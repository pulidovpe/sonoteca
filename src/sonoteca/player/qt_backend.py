"""Backend con QtMultimedia (FFmpeg en escritorio)."""
from __future__ import annotations

import time
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
        self._frames = 0       # fotogramas de video válidos desde el último load (para avisar si el códec no se decodifica)
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
        self._frames = 0
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
        sink.videoFrameChanged.connect(self._on_video_frame)

    def _on_video_frame(self, frame) -> None:
        if frame.isValid():
            self._frames += 1

    def video_frames(self) -> int:
        return self._frames

    def fade_out(self, ms: int = 150) -> None:
        if self._audio is None:
            return
        start, steps = self._audio.volume(), 6
        for i in range(1, steps + 1):
            self._audio.setVolume(start * (1 - i / steps))
            time.sleep(ms / 1000 / steps)

    def fade_in(self, volume: float, ms: int = 250) -> None:
        if self._audio is None:
            return
        steps = 10
        if getattr(self, "_fade_timer", None) is not None:
            self._fade_timer.stop()
        timer = self._fade_timer = QTimer(self)
        timer.setInterval(max(1, ms // steps))
        count = [0]

        def tick() -> None:
            count[0] += 1
            self.set_volume(volume * min(1.0, count[0] / steps))
            if count[0] >= steps:
                timer.stop()

        timer.timeout.connect(tick)
        timer.start()

    def release(self) -> None:
        self._frames = 0
        self._player.stop()
        self._player.setSource(QUrl())

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
