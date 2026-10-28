from pathlib import Path

from sonoteca.player.backend import PlayerBackend


class FakeBackend(PlayerBackend):
    """Backend de prueba: registra llamadas y permite simular eventos."""

    def __init__(self):
        super().__init__()
        self.loaded: Path | None = None
        self.state = "stopped"
        self.volume = None
        self.seeks: list[int] = []
        self.sink = None

    def load(self, path):
        self.loaded = Path(path)

    def play(self):
        self.state = "playing"
        self.stateChanged.emit("playing")

    def pause(self):
        self.state = "paused"
        self.stateChanged.emit("paused")

    def stop(self):
        self.state = "stopped"
        self.stateChanged.emit("stopped")

    def seek(self, ms):
        self.seeks.append(ms)
        self.positionChanged.emit(ms)

    def set_volume(self, volume):
        self.volume = volume

    def set_video_sink(self, sink):
        self.sink = sink

    # ayudas para simular eventos del motor
    def finish(self):
        self.ended.emit()

    def fail(self, message="error"):
        self.failed.emit(message)
