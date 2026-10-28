"""Búsqueda de música local desde la interfaz (expuesto a QML como `scanner`).

El escaneo corre en un hilo aparte con su propia conexión a la base; las señales se emiten desde
ese hilo y Qt las entrega en cola al hilo principal, así la ventana nunca se congela.
"""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from PySide6.QtCore import Property, QObject, QStandardPaths, QStorageInfo, Signal, Slot

from musicapp.core import scanner
from musicapp.core.db import connect

_EXTERNAL_PREFIXES = ("/Volumes/", "/media/", "/run/media/", "/mnt/")


def _standard(location: QStandardPaths.StandardLocation) -> str:
    found = QStandardPaths.standardLocations(location)
    return found[0] if found else ""


def suggested_folders() -> list[dict]:
    """Carpetas donde suele haber música: Música, Descargas, Escritorio, Documentos, Películas y
    discos externos. Solo las que existen. `checked` marca la que se escaneará por defecto."""
    options = [
        (QStandardPaths.StandardLocation.MusicLocation, "Música", True),
        (QStandardPaths.StandardLocation.DownloadLocation, "Descargas", False),
        (QStandardPaths.StandardLocation.DesktopLocation, "Escritorio", False),
        (QStandardPaths.StandardLocation.DocumentsLocation, "Documentos", False),
        (QStandardPaths.StandardLocation.MoviesLocation, "Películas / videos", False),
    ]
    out: list[dict] = []
    seen: set[str] = set()
    for location, label, checked in options:
        path = _standard(location)
        if path and Path(path).is_dir() and path not in seen:
            seen.add(path)
            out.append({"path": path, "label": label, "checked": checked})
    for volume in QStorageInfo.mountedVolumes():
        root = volume.rootPath()
        if volume.isValid() and volume.isReady() and not volume.isRoot() and root not in seen \
                and (root.startswith(_EXTERNAL_PREFIXES) or (os.name == "nt" and len(root) <= 3)):
            seen.add(root)
            out.append({"path": root, "label": f"Disco: {volume.displayName() or root}", "checked": False})
    return out


class ScanController(QObject):
    busyChanged = Signal()
    progress = Signal(int, str)           # archivos revisados, carpeta que se está recorriendo
    scanFinished = Signal("QVariantMap")  # resumen: added, updated, removed, errors, folders
    scanError = Signal(str)

    def __init__(self, db_path: Path | str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_arg = db_path
        self._busy = False

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Slot(result="QVariantList")
    def suggestedFolders(self) -> list:
        return suggested_folders()

    @Slot("QVariantList")
    def scan(self, folders: list) -> None:
        """Indexa las carpetas indicadas (solo relee archivos nuevos o modificados)."""
        paths_ = [str(p) for p in folders if str(p)]
        if self._busy:
            self.scanError.emit("Ya hay una búsqueda en curso")
            return
        if not paths_:
            self.scanError.emit("Elige al menos una carpeta")
            return
        self._busy = True
        self.busyChanged.emit()

        def run() -> None:
            totals = {"added": 0, "updated": 0, "removed": 0, "errors": 0, "folders": 0}
            seen_before = 0
            try:
                conn = connect(self._db_arg)
                try:
                    for folder in paths_:
                        last = [0.0]

                        def report(count: int, path: Path, base=seen_before, last=last) -> None:
                            now = time.monotonic()
                            if now - last[0] >= 0.1:   # no inundar la interfaz con una señal por archivo
                                last[0] = now
                                self.progress.emit(base + count, str(path.parent))

                        try:
                            result = scanner.scan(conn, folder, progress=report)
                        except NotADirectoryError:
                            self.scanError.emit(f"«{folder}» no es una carpeta")
                            continue
                        seen_before += result.total_seen
                        totals["folders"] += 1
                        totals["added"] += result.added
                        totals["updated"] += result.updated
                        totals["removed"] += result.removed
                        totals["errors"] += len(result.errors)
                finally:
                    conn.close()
                self.scanFinished.emit(totals)
            except Exception as exc:  # noqa: BLE001  (se informa a la interfaz en vez de perderse)
                self.scanError.emit(f"Error al buscar música: {exc}")
            finally:
                self._busy = False
                self.busyChanged.emit()

        threading.Thread(target=run, daemon=True).start()
