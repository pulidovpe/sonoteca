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
    audioDevicesChanged = Signal()  # cambió la lista de salidas o la que se está usando

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

    def fade_out(self, ms: int, done) -> None:
        """Baja el volumen a 0 en unos `ms` SIN bloquear y llama a `done()` al terminar (por defecto, de inmediato)."""
        done()

    def resume(self, path: Path, position_ms: int, playing: bool, volume: float) -> None:
        """Vuelve a cargar `path` en `position_ms`; suena (con fundido de entrada) si `playing`, y si no queda en pausa."""
        self.load(path)
        self.set_volume(volume)
        if playing:
            self.play()
        if position_ms > 0:
            self.seek(position_ms)
        if not playing:
            self.pause()

    def release(self) -> None:
        """Suelta el archivo actual (lo cierra) sin cambiar la lista; necesario en Windows para poder reescribirlo."""

    def video_frames(self) -> int:
        """Fotogramas de video válidos recibidos desde el último `load`; -1 si el backend no lo sabe."""
        return -1

    # ---- salida de audio (los backends sin soporte dejan estos valores) ----
    def audio_devices(self) -> list[dict]:
        """[{"id": str, "name": str, "isDefault": bool}] de las salidas disponibles."""
        return []

    def audio_device(self) -> str:
        """Id de la salida elegida; "" = automática (sigue la predeterminada del sistema)."""
        return ""

    def set_audio_device(self, device_id: str) -> bool:
        """"" = automática. Devuelve False si esa salida no existe (ya no está conectada)."""
        return False
