"""Controlador de reproducción expuesto a QML como `player`."""
from __future__ import annotations

import random
import sys
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from sonoteca.core import library, paths, stats
from sonoteca.core.db import connect
from sonoteca.core.models import UNKNOWN_ALBUM, UNKNOWN_ARTIST
from sonoteca.player.backend import PlayerBackend
from sonoteca.player.devices import classify_audio_device
from sonoteca.player.queue import PlayQueue

from .controller import album_display


class PlayerController(QObject):
    playingChanged = Signal()
    positionChanged = Signal()
    durationChanged = Signal()
    volumeChanged = Signal()
    sourceChanged = Signal()
    shuffleChanged = Signal()
    repeatModeChanged = Signal()
    currentChanged = Signal()
    errorMessage = Signal(str)
    queueChanged = Signal()  # cambió la lista o la posición dentro de ella
    playsChanged = Signal()  # se contó una reproducción nueva
    audioChanged = Signal()  # cambió la lista de salidas de audio o la elegida
    queueMessage = Signal(str)  # aviso breve para mostrar al usuario

    def __init__(self, backend: PlayerBackend, db_path: Path | str | None = None,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._backend = backend
        self._conn = connect(db_path)
        self._queue = PlayQueue()
        self._queue.consume_played = True   # lo que ya sonó (o se saltó) sale de la lista de reproducción
        self._playing = False
        self._position = 0
        self._duration = 0
        self._volume = 0.8
        self._source = ""         # de qué lista/álbum viene lo que suena («album:3», «playlist:7»); vacío si no se sabe
        self._muted = False      # silencio total: el volumen elegido se conserva para recuperarlo
        self._current: dict = {}
        self._listened = 0  # ms realmente escuchados de la pista actual
        self._last_pos = -1
        self._counted = False
        self._stats_revision = 0
        self._error_streak = 0  # fallos seguidos, para no saltar en bucle por archivos rotos

        # Aviso si un video suena pero no llega ninguna imagen (códec sin decodificador en este equipo, p. ej. AV1 sin
        # hardware compatible en Linux): se revisa unos segundos después de empezar a sonar.
        self._video_warned: int | None = None
        self._resume: dict | None = None     # punto de la pista soltada para poder editar sus tags (Windows)
        self._video_check = QTimer(self)
        self._video_check.setSingleShot(True)
        self._video_check.setInterval(3000)
        self._video_check.timeout.connect(self._check_video)

        backend.positionChanged.connect(self._on_position)
        backend.durationChanged.connect(self._on_duration)
        backend.stateChanged.connect(self._on_state)
        backend.audioDevicesChanged.connect(self.audioChanged)
        self._restore_audio_device()
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

    # ---- salida de audio ----
    @staticmethod
    def _audio_file() -> Path:
        return paths.data_dir() / "audio_output.txt"

    def _restore_audio_device(self) -> None:
        """Vuelve a la salida que el usuario eligió; si ya no está conectada, queda en automático."""
        try:
            saved = self._audio_file().read_text(encoding="utf-8").strip()
        except OSError:
            return
        if saved:
            self._backend.set_audio_device(saved)

    @Slot(result="QVariantList")
    def audioDevices(self) -> list:
        """Salidas de audio disponibles; la primera es «Automático» (sigue la del sistema)."""
        current = self._backend.audio_device()
        out = [{"id": "", "name": "Autom\u00e1tico (la que use el sistema)", "current": current == ""}]
        for d in self._backend.audio_devices():
            out.append({"id": d["id"], "name": d["name"] + (" \u00b7 predeterminada" if d["isDefault"] else ""),
                        "current": d["id"] == current})
        return out

    @Slot(str)
    def setAudioDevice(self, device_id: str) -> None:
        if not self._backend.set_audio_device(device_id):
            self.queueMessage.emit("Esa salida de audio ya no est\u00e1 disponible")
            self.audioChanged.emit()
            return
        try:
            self._audio_file().parent.mkdir(parents=True, exist_ok=True)
            self._audio_file().write_text(device_id, encoding="utf-8")
        except OSError:
            pass  # no poder recordar la elección no impide usarla

    @Property(str, notify=audioChanged)
    def audioDeviceName(self) -> str:
        current = self._backend.audio_device()
        if not current:
            return "Autom\u00e1tico"
        for d in self._backend.audio_devices():
            if d["id"] == current:
                return d["name"]
        return "Autom\u00e1tico"

    def _active_audio_name(self) -> str:
        """Nombre de la salida que suena ahora: la elegida o, en automático, la predeterminada."""
        current = self._backend.audio_device()
        devices = self._backend.audio_devices()
        for d in devices:
            if current and d["id"] == current:
                return d["name"]
        for d in devices:
            if d["isDefault"]:
                return d["name"] + (" (autom\u00e1tico)" if not current else "")
        return ""

    @Property(str, notify=audioChanged)
    def audioActiveName(self) -> str:
        return self._active_audio_name()

    @Property(str, notify=audioChanged)
    def audioDeviceKind(self) -> str:
        """'speaker' | 'headphones' | 'display': el icono de la barra de reproducción."""
        return classify_audio_device(self._active_audio_name())

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

    @Slot(str, "QVariantList", int)
    def playFrom(self, source: str, ids: list, index: int) -> None:
        """Reproduce una lista desde `index` y recuerda su origen (para que su página muestre «Detener»)."""
        valid = [int(i) for i in ids]
        if not valid:
            return
        self._start(valid, index)
        self._set_source(source)

    @Slot(str, "QVariantList")
    def playShuffled(self, source: str, ids: list) -> None:
        """Activa el modo Aleatorio y reproduce la lista empezando por una canción al azar."""
        if not ids:
            return
        if not self._queue.shuffle:
            self.toggleShuffle()
        self.playFrom(source, ids, random.randrange(len(ids)))

    @Slot()
    def stopPlayback(self) -> None:
        """Detiene la reproducción: pausa y vuelve al inicio de la canción; la lista no se toca."""
        if self._current:
            self._backend.pause()
            self._backend.seek(0)

    @Property(str, notify=sourceChanged)
    def sourceKey(self) -> str:
        return self._source

    @Slot("QVariantList", int)
    def playTrackIds(self, ids: list, index: int) -> None:
        self._start([int(i) for i in ids], index)

    @Slot("QVariantList")
    def playFirst(self, ids: list) -> None:
        """Doble clic / «Reproducir ahora»: se CONSERVA la lista y estas canciones se insertan de primeras (también
        con Aleatorio) y suena ya la primera. La que sonaba sale de la lista; lo demás sigue después. Sin lista,
        empieza una nueva con ellas."""
        valid = self._existing(ids)
        if not valid:
            return
        if len(self._queue) == 0:
            self._start(valid, 0)
            return
        at = max(self._queue.position, -1) + 1
        self._queue.insert_next(valid)
        self._queue.jump_to(at)
        self._error_streak = 0
        self._play_current()

    @Slot(int)
    def playKeepingQueue(self, track_id: int) -> None:
        self.playFirst([track_id])

    @Slot(int)
    def playOnly(self, track_id: int) -> None:
        """Vacía la lista y reproduce solo esta canción."""
        valid = self._existing([track_id])
        if valid:
            self._start(valid, 0)

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
        self._muted = False       # mover el volumen quita el silencio
        self._backend.set_volume(self._volume)
        self.volumeChanged.emit()

    @Property(bool, notify=volumeChanged)
    def muted(self) -> bool:
        return self._muted

    @Slot()
    def toggleMute(self) -> None:
        """Silencio total (y volver al volumen anterior); no cambia el volumen elegido."""
        self._muted = not self._muted
        self._backend.set_volume(0.0 if self._muted else self._volume)
        self.volumeChanged.emit()

    @Slot()
    def toggleShuffle(self) -> None:
        """Aleatorio: reordena la lista de reproducción (aleatorio / orden original, sin lo que ya sonó). No reproduce
        ni detiene nada."""
        self._queue.set_shuffle(not self._queue.shuffle)
        self.shuffleChanged.emit()
        self.queueChanged.emit()          # el panel de la derecha muestra el nuevo orden

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
                               "Agregar al final de la lista.")

    @Slot()
    def clearQueue(self) -> None:
        """Vacía la lista. Si algo suena, esa pista sigue sonando (queda como única de la lista)."""
        if self._queue.current is not None:
            self._queue.clear(keep_current=True)
            self.queueChanged.emit()
            return
        self._stop_and_clear()

    def _stop_and_clear(self) -> None:
        self._queue.clear()
        self._backend.stop()
        self._current = {}
        self._position = 0
        self._duration = 0
        self.currentChanged.emit()
        self.positionChanged.emit()
        self.durationChanged.emit()
        self.queueChanged.emit()

    @Slot("QVariantList")
    def releaseFiles(self, ids: list) -> None:
        """Windows: la pista que suena mantiene el archivo abierto y no se puede reescribir al editar sus tags
        (PermissionError [WinError 5]). Se suelta antes de escribir y `restoreAfterEdit` la vuelve a cargar."""
        if sys.platform != "win32" or not self._current or self.currentId not in {int(i) for i in ids}:
            return
        self._resume = {"position": self._position, "playing": self._playing}
        if self._playing:
            self._backend.fade_out()       # unos 150 ms: evita el chasquido de cortar el sonido en seco
        self._backend.release()

    @Slot()
    def restoreAfterEdit(self) -> None:
        """Tras escribir los tags: vuelve a cargar la pista soltada, en el mismo punto y con el mismo estado."""
        resume, self._resume = self._resume, None
        if resume is None or not self._current:
            return
        row = library.get_track(self._conn, self.currentId)
        if row is None:
            self._backend.set_volume(self._volume)
            return
        self._backend.set_volume(0.0)      # entra en silencio y sube con un fundido (el fundido de salida dejó el volumen en 0)
        self._backend.load(Path(row["path"]))
        self._backend.play()
        position, playing = resume["position"], resume["playing"]

        def settle() -> None:
            if position > 0:
                self._backend.seek(position)
            if playing:
                self._backend.fade_in(self._volume)
            else:
                self._backend.pause()
                self._backend.set_volume(self._volume)

        QTimer.singleShot(300, settle)     # el motor necesita un instante para tener el archivo listo

    @Slot("QVariantList")
    def forgetTracks(self, ids: list) -> None:
        """Quita de la lista (y detiene, si suena) las pistas cuyo archivo se va a eliminar."""
        wanted = {int(i) for i in ids}
        for position in reversed(range(len(self._queue))):
            if self._queue.order_ids()[position] in wanted:
                self.removeFromQueue(position)
        if self._current is not None and self.currentId in wanted:
            self._stop_and_clear()

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
                self._stop_and_clear()  # era la última: no queda nada que sonar
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
                 "album": album_display(row["album"]), "albumId": row["album_id"],
                 "artistId": row["artist_id"], "hasAlbum": row["album"] != UNKNOWN_ALBUM,
                 "hasArtist": row["artist"] != UNKNOWN_ARTIST}
        if fresh != self._current:
            self._current = fresh
            self.currentChanged.emit()

    @Slot(result="QVariantList")
    def queueItems(self) -> list[dict]:
        """Lista en el orden en que sonará, para mostrarla."""
        current_pos = self._queue.position if self._queue.current is not None else -1
        up_next = self._queue.up_next_flags()      # añadidas con «Reproducir a continuación» y aún por sonar
        rows = []
        for position, track_id in enumerate(self._queue.order_ids()):
            row = library.get_track(self._conn, track_id)
            if row is None:
                continue
            rows.append({"position": position, "id": row["id"], "title": row["title"],
                         "artist": row["artist"], "album": album_display(row["album"]),
                         "albumId": row["album_id"], "duration": row["duration"], "year": str(row["year"] or ""),
                         "current": position == current_pos, "upNext": up_next[position]})
        return rows

    @Slot(QObject)
    def setVideoSink(self, sink: QObject) -> None:
        self._backend.set_video_sink(sink)

    # ---- internos ----
    def _set_source(self, source: str) -> None:
        if source != self._source:
            self._source = source
            self.sourceChanged.emit()

    def _start(self, ids: list[int], index: int) -> None:
        if not ids:
            return
        self._set_source("")        # cualquier otra forma de empezar a sonar olvida el origen
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
            "artistId": row["artist_id"],
            "hasAlbum": row["album"] != UNKNOWN_ALBUM,   # sin álbum / sin artista no hay enlace
            "hasArtist": row["artist"] != UNKNOWN_ARTIST,
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
            self.queueChanged.emit()     # al terminar la \u00faltima, sale de la lista
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

    def _check_video(self) -> None:
        if not (self._playing and self.isVideo and self._position >= 1500):
            return
        track_id = self._current.get("id")
        if self._backend.video_frames() != 0 or self._video_warned == track_id:
            return                     # -1 = el motor no lo sabe; >0 = se está viendo
        self._video_warned = track_id
        title = self._current.get("title", "")
        self.errorMessage.emit(f"No se puede mostrar el video de \u00ab{title}\u00bb en este equipo (c\u00f3dec sin "
                               f"soporte); se reproduce solo el audio")

    def _on_state(self, state: str) -> None:
        playing = state == "playing"
        if playing and self.isVideo and self._video_warned != self._current.get("id"):
            self._video_check.start()
        elif not playing:
            self._video_check.stop()
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
