"""Carpetas de la biblioteca (expuesto a QML como `libraryFolders`): ver las carpetas con música, quitarlas de la
biblioteca (sin tocar el disco) y volver a incluir las excluidas."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from sonoteca.core import library_folders
from sonoteca.core.db import connect


class FoldersController(QObject):
    changed = Signal()   # se quitó o se volvió a incluir algo

    def __init__(self, db_path: Path | str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_arg = db_path

    @Slot(result="QVariantList")
    def folders(self) -> list:
        conn = connect(self._db_arg)
        try:
            return library_folders.list_folders(conn)
        finally:
            conn.close()

    @Slot(result="QVariantList")
    def excluded(self) -> list:
        conn = connect(self._db_arg)
        try:
            return library_folders.list_excluded(conn)
        finally:
            conn.close()

    @Slot(str, result="QVariantMap")
    def removeFolder(self, path: str) -> dict:
        """Quita la carpeta (y todo lo que contiene) de la biblioteca. No modifica ningún archivo del disco."""
        conn = connect(self._db_arg)
        try:
            result = library_folders.exclude_folder(conn, path)
        except Exception as exc:  # noqa: BLE001  (se informa a la interfaz)
            return {"ok": False, "error": str(exc), "removed": 0}
        finally:
            conn.close()
        self.changed.emit()
        return {"ok": True, "error": "", **result}

    @Slot(str, result=bool)
    def includeAgain(self, path: str) -> bool:
        conn = connect(self._db_arg)
        try:
            done = library_folders.include_again(conn, path)
        finally:
            conn.close()
        if done:
            self.changed.emit()
        return done
