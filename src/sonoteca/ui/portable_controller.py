"""Exportar e importar la biblioteca (expuesto a QML como `portable`). Ver core/portable.py."""
from __future__ import annotations

import threading
from datetime import date
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from sonoteca.core import paths, portable
from sonoteca.core.db import connect, default_db_path


class PortableController(QObject):
    busyChanged = Signal()
    exportProgress = Signal(int, int)
    exportFinished = Signal("QVariantMap")   # ok, error, path, manifest

    def __init__(self, db_path: Path | str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path) if db_path else default_db_path()
        self._busy = False

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()

    @Slot(result=str)
    def defaultExportName(self) -> str:
        return f"sonoteca-{date.today():%Y-%m-%d}{portable.EXTENSION}"

    @Slot(str)
    def exportLibrary(self, path: str) -> None:
        if self._busy:
            return
        dest = Path(path)
        if dest.suffix != portable.EXTENSION:
            dest = dest.with_name(dest.name + portable.EXTENSION)
        self._set_busy(True)
        threading.Thread(target=self._export_worker, args=(dest,), daemon=True).start()

    def _export_worker(self, dest: Path) -> None:
        try:
            manifest = portable.export_library(self._db_path, dest, progress=self.exportProgress.emit)
            result = {"ok": True, "error": "", "path": str(dest), "manifest": manifest}
        except (OSError, portable.PortableError) as exc:
            result = {"ok": False, "error": str(exc), "path": str(dest), "manifest": {}}
        self._set_busy(False)
        self.exportFinished.emit(result)

    @Slot(str, result="QVariantMap")
    def inspectImport(self, path: str) -> dict:
        """Datos del archivo y de la biblioteca actual, para que el usuario confirme."""
        try:
            manifest = portable.inspect_bundle(path)
        except portable.PortableError as exc:
            return {"ok": False, "error": str(exc)}
        conn = connect(self._db_path)
        try:
            current = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
        finally:
            conn.close()
        return {"ok": True, "error": "", "manifest": manifest, "currentTracks": current}

    @Slot(str, str, result="QVariantMap")
    def stageImport(self, path: str, new_music_root: str) -> dict:
        """Deja la importación preparada; se aplica al volver a abrir la aplicación."""
        try:
            portable.stage_import(path, new_music_root or None, data=paths.data_dir())
        except portable.PortableError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "error": ""}

    @Slot(bool, result="QVariantMap")
    def stageReset(self, keep_backup: bool) -> dict:
        """Prepara «empezar desde cero»; se aplica al volver a abrir la aplicación."""
        try:
            portable.stage_reset(keep_backup, data=paths.data_dir())
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, "error": ""}
