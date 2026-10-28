"""Descarga automática de portadas y fotos tras escanear (expuesto a QML como `harvest`).

El plan se calcula sin internet; la descarga corre en un hilo aparte con su propia conexión y avisa con señales.
Ver online/harvest.py para los criterios (solo música bien identificada, solo lo que falta)."""
from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from sonoteca.core.db import connect
from sonoteca.online import harvest
from sonoteca.online import settings as online_settings
from sonoteca.online.http import HttpClient

LONG_RUN_SECONDS = 5 * 60   # a partir de aquí el aviso de tiempo se destaca


class HarvestController(QObject):
    busyChanged = Signal()
    progress = Signal(int, int, str, float)     # hechos, total, qué se procesa, segundos restantes estimados
    finished = Signal("QVariantMap")

    def __init__(self, db_path: Path | str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_arg = db_path
        self._conn = connect(db_path)
        self._busy = False
        self._cancel = threading.Event()

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    @Slot(result="QVariantMap")
    def plan(self) -> dict:
        """Qué se descargaría y cuánto tardaría (estimación). No usa internet."""
        work = harvest.plan(self._conn)
        return {
            "albums": len(work.albums), "artists": len(work.artists), "total": work.total,
            "seconds": work.seconds, "duration": harvest.format_duration(work.seconds),
            "long": work.seconds >= LONG_RUN_SECONDS,
            "offline": online_settings.load().offline,
        }

    @Slot()
    def start(self) -> None:
        if self._busy:
            return
        self._cancel.clear()
        self._set_busy(True)
        threading.Thread(target=self._worker, daemon=True).start()

    @Slot()
    def cancel(self) -> None:
        self._cancel.set()

    def _worker(self) -> None:
        summary: dict
        client = None
        try:
            conn = connect(self._db_arg)
            try:
                work = harvest.plan(conn)
                client = HttpClient()
                started = time.monotonic()

                def on_progress(done: int, total: int, label: str) -> None:
                    left = 0.0
                    if done > 0:
                        left = (time.monotonic() - started) / done * (total - done)
                    elif total:
                        left = work.seconds
                    self.progress.emit(done, total, label, left)

                summary = harvest.run(conn, client, work, progress=on_progress, cancelled=self._cancel.is_set)
                summary["error"] = ""
            finally:
                conn.close()
        except Exception as exc:  # noqa: BLE001  (se informa a la interfaz en vez de perderse en el hilo)
            summary = {"covers": 0, "artists": 0, "unsure": 0, "notfound": 0, "errors": 0, "done": 0, "total": 0,
                       "cancelled": False, "offline": False, "aborted": False, "error": str(exc)}
        finally:
            if client is not None:
                client.close()
        self._set_busy(False)
        self.finished.emit(summary)
