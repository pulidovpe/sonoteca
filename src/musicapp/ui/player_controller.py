"""Controlador de reproducción expuesto a QML como `player`."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from musicapp.core import library, stats
from musicapp.core.db import connect
from musicapp.player.backend import PlayerBackend
from musicapp.player.queue import PlayQueue

from .controller import album_display


class PlayerController(QObject):
    playingChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    volumeChanged = Signal()
    shuffleChanged = Signal()
    repeatModeChanged = Signal()
    currentChanged = Signal()
    errorMessage = Signal(str)
    queueChanged = Signal()  # cambió la lista o la posición dentro de ella
    playsChanged = Signal()  # se contó una reproducción nueva
    queueMessage = Signal(str)  # aviso breve para mostrar al usuario

    def __init__(self, backend: PlayerBackend, db_path: Path | str | None = None,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._conn = connect(db_path)
        self._queue = PlayQueue()
        self._playing = False
        self._position = 0
        self._duration = 0
        self._volume = 0.8
        self._current: dict = {}
        self._listened = 0  # ms realmente escuchados de la pista actual
        self._last_pos = -1
        self._counted = False
        self._stats_revision = 0
        self._error_streak = 0  # fallos seguidos, para no saltar en bucle por archivos rotos

        backend.positionChanged.connect(self._on_position)
        backend.durationChanged.connect(self._on_duration)
        backend.stateChanged.connect(self._on_state)
        backend.ended.connect(self._on_ended)
        backend.failed.connect(self._on_failed)
        backend.set_volume(self._volume)

    # ---- propiedades para QML ----
    @Property(bool, notify=playingChanged)
    def playing(self) -> bool:
        return self._playing

    @Property(int, notify=positionChanged)
    def position(self) -> int:
        return self._position

    @Property(int, notify=durationChanged)
    def duration(self) -> int:
        return self._duration

    @Property(float, notify=volumeChanged)
    def volume(self) -> float:
        return self._volume

    @Property(bool, notify=shuffleChanged)
    def shuffle(self) -> bool:
        return self._queue.shuffle

    @Property(str, notify=repeatModeChanged)
    def repeatMode(self) -> str:
        return self._queue.repeat.value

    @Property("QVariantMap", notify=currentChanged)
    def currentTrack(self) -> dict:
        return self._current

    @Property(int, notify=currentChanged)
    def currentId(self) -> int:
        return self._current.get("id", 0)

    @Property(int, notify=playsChanged)
    def statsRevision(self) -> int:
        return self._stats_revision

    @Slot(int, result=int)
    def playsOf(self, track_id: int) -> int:
        """Veces que se ha reproducido la pista (úsese junto a statsRevision para que se actualice)."""
        return stats.play_counts(self._conn, [track_id])[track_id]

    @Property(bool, notify=currentChanged)
    def hasTrack(self) -> bool:
        return bool(self._current)

    @Property(bool, notify=currentChanged)
    def isVideo(self) -> bool:
        return self._current.get("kind") == "video"

    @Property(int, notify=queueChanged)
    def queueLength(self) -> int:
        return len(self._queue)

    @Property(int, notify=queueChanged)
    def queuePosition(self) -> int:
        return self._queue.position

    # ---- acciones ----
    @Slot(int, int)
    def playAlbum(self, album_id: int, index: int) -> None:
        ids = [r["id"] for r in library.list_tracks(self._conn, album_id=album_id)]
        self._start(ids, index)

    @Slot("QVariantList", int)
    def playTrackIds(self, ids: list, index: int) -> None:
        self._start([int(i) for i in ids], index)

    @Slot()
    def toggle(self) -> None:
        if not self._current:
            return
        if self._playing:
            self._backend.pause()
        else:
            self._backend.play()

    @Slot()
    def next(self) -> None:
        self._advance(auto=False)

    @Slot()
    def previous(self) -> None:
        if not self._current:
            return
        if self._position > 3000:  # como en otros reproductores: primero reinicia la pista
            self.seek(0)
            return
        if self._queue.previous() is not None:
            self._play_current()

    @Slot(int)
    def seek(self, ms: int) -> None:
        self._backend.seek(max(0, ms))

    @Slot(float)
    def setVolume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        self._backend.set_volume(self._volume)
        self.volumeChanged.emit()

    @Slot()
    def toggleShuffle(self) -> None:
        self._queue.set_shuffle(not self._queue.shuffle)
        self.shuffleChanged.emit()

    @Slot()
    def cycleRepeat(self) -> None:
        self._queue.cycle_repeat()
        self.repeatModeChanged.emit()

    # ---- lista temporal (la cola que suena): agregar, quitar, ordenar ----
    def _existing(self, ids: list) -> list[int]:
        return [int(i) for i in ids if library.get_track(self._conn, int(i)) is not None]

    @staticmethod
    def _songs(n: int) -> str:
        return f"{n} canción" if n == 1 else f"{n} canciones"

    @Slot("QVariantList")
    def addToQueue(self, ids: list) -> None:
        """Agrega al final de la lista actual. Si no suena nada, queda como lista temporal nueva."""
        valid = self._existing(ids)
        if not valid:
            return
        was_empty = len(self._queue) == 0
        self._queue.append(valid)
        self.queueChanged.emit()
        if was_empty:
            self.queueMessage.emit(f"Lista temporal creada con {self._songs(len(valid))}. "
                                   "Ábrela en \u00abReproduciendo\u00bb.")
        else:
            self.queueMessage.emit(f"{self._songs(len(valid)).capitalize()} agregada"
                                   f"{'' if len(valid) == 1 else 's'} a la lista actual")

    @Slot("QVariantList")
    def playNext(self, ids: list) -> None:
        """Las canciones sonarán justo después de la actual."""
        valid = self._existing(ids)
        if not valid:
            return
        self._queue.insert_next(valid)
        self.queueChanged.emit()
        self.queueMessage.emit(f"{self._songs(len(valid)).capitalize()} sonar"
                               f"{'á' if len(valid) == 1 else 'án'} a continuación")

    @Slot()
    def newTemporaryList(self) -> None:
        """Empieza una lista temporal vacía; si algo suena, sigue sonando y es la primera."""
        self._queue.clear(keep_current=True)
        self.queueChanged.emit()
        self.queueMessage.emit("Lista temporal nueva. Agrega canciones con clic derecho \u25b8 "
                               "Agregar a la lista actual.")

    @Slot()
    def clearQueue(self) -> None:
        self._queue.clear()
        self._backend.stop()
        self._current = {}
        self._position = 0
        self._duration = 0
        self.currentChanged.emit()
        self.positionChanged.emit()
        self.durationChanged.emit()
        self.queueChanged.emit()

    @Slot(int)
    def removeFromQueue(self, position: int) -> None:
        was_current = position == self._queue.position and self._queue.current is not None
        try:
            self._queue.remove(position)
        except IndexError:
            return
        if was_current:
            if self._queue.current is not None:
                self._play_current()  # la siguiente ocupa su lugar
            else:
                self.clearQueue()  # era la última: no queda nada que sonar
                return
        self.queueChanged.emit()

    @Slot(int, int)
    def moveInQueue(self, src: int, dst: int) -> None:
        try:
            self._queue.move(src, dst)
        except IndexError:
            return
        self.queueChanged.emit()

    @Slot(int)
    def playQueueAt(self, position: int) -> None:
        try:
            self._queue.jump_to(position)
        except IndexError:
            return
        self._error_streak = 0
        self._play_current()

    @Slot(result="QVariantList")
    def queueTrackIds(self) -> list[int]:
        """Ids de la lista actual en el orden en que sonará (para guardarla como lista)."""
        return self._queue.order_ids()

    @Slot()
    def refreshCurrent(self) -> None:
        """Vuelve a leer los datos de la pista que suena (p. ej. tras editar sus tags)."""
        track_id = self._current.get("id")
        row = library.get_track(self._conn, track_id) if track_id else None
        if row is None:
            return
        fresh = {**self._current, "title": row["title"], "artist": row["artist"],
                 "album": album_display(row["album"]), "albumId": row["album_id"]}
        if fresh != self._current:
            self._current = fresh
            self.currentChanged.emit()

    @Slot(result="QVariantList")
    def queueItems(self) -> list[dict]:
        """Lista en el orden en que sonará, para mostrarla."""
        current_pos = self._queue.position if self._queue.current is not None else -1
        rows = []
        for position, track_id in enumerate(self._queue.order_ids()):
            row = library.get_track(self._conn, track_id)
            if row is None:
                continue
            rows.append({"position": position, "id": row["id"], "title": row["title"],
                         "artist": row["artist"], "album": album_display(row["album"]),
                         "albumId": row["album_id"], "duration": row["duration"],
                         "current": position == current_pos})
        return rows

    @Slot(QObject)
    def setVideoSink(self, sink: QObject) -> None:
        self._backend.set_video_sink(sink)

    # ---- internos ----
    def _start(self, ids: list[int], index: int) -> None:
        if not ids:
            return
        self._error_streak = 0
        self._queue.set_items(ids, index)
        self.queueChanged.emit()
        self._play_current()

    def _play_current(self) -> None:
        track_id = self._queue.current
        if track_id is None:
            self._finish()
            return
        row = library.get_track(self._conn, track_id)
        if row is None or not Path(row["path"]).exists():
            title = row["title"] if row else f"#{track_id}"
            self.errorMessage.emit(f"No se encuentra el archivo de \u00ab{title}\u00bb")
            self._handle_failure()
            return
        self._current = {
            "id": row["id"],
            "title": row["title"],
            "artist": row["artist"],
            "album": album_display(row["album"]),
            "albumId": row["album_id"],
            "kind": row["kind"],
            "duration": row["duration"],
        }
        self._position = 0
        self._listened, self._last_pos, self._counted = 0, -1, False
        self._duration = int(row["duration"] * 1000)
        self.currentChanged.emit()
        self.positionChanged.emit()
        self.durationChanged.emit()
        self.queueChanged.emit()
        self._backend.load(Path(row["path"]))
        self._backend.play()

    def _advance(self, auto: bool) -> None:
        if self._queue.next(auto=auto) is None:
            self._finish()
        else:
            self._play_current()

    def _finish(self) -> None:
        """Fin de la cola: se detiene, pero la última pista sigue mostrándose."""
        self._backend.stop()
        self._position = 0
        self.positionChanged.emit()

    def _handle_failure(self) -> None:
        self._error_streak += 1
        if self._error_streak < len(self._queue):
            self._advance(auto=True)
        else:
            self._finish()

    def _on_position(self, ms: int) -> None:
        self._position = ms
        if self._current and not self._counted:
            # solo suma el avance normal: saltar con la barra no cuenta como escuchar
            if 0 <= self._last_pos <= ms and ms - self._last_pos <= 2500:
                self._listened += ms - self._last_pos
            self._last_pos = ms
            if self._listened >= stats.threshold_ms(self._duration):
                self._counted = True
                stats.record_play(self._conn, self._current["id"])
                self._stats_revision += 1
                self.playsChanged.emit()
        self.positionChanged.emit()

    def _on_duration(self, ms: int) -> None:
        if ms > 0:
            self._duration = ms
            self.durationChanged.emit()

    def _on_state(self, state: str) -> None:
        playing = state == "playing"
        if playing:
            self._error_streak = 0
        if playing != self._playing:
            self._playing = playing
            self.playingChanged.emit()

    def _on_ended(self) -> None:
        self._advance(auto=True)

    def _on_failed(self, message: str) -> None:
        self.errorMessage.emit(f"No se pudo reproducir: {message}")
        self._handle_failure()
