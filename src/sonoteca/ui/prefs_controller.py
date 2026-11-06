"""Preferencias de interfaz expuestas a QML como `prefs` (valores tipados; se guardan al instante en `ui_prefs.json`)."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from sonoteca.core.prefs import Prefs


class PrefsController(QObject):
    changed = Signal(str)                      # clave modificada

    def __init__(self, prefs: Prefs | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._prefs = prefs or Prefs()

    @Slot(str, bool, result=bool)
    def boolValue(self, key: str, default: bool) -> bool:
        value = self._prefs.get(key, default)
        return value if isinstance(value, bool) else default

    @Slot(str, int, result=int)
    def intValue(self, key: str, default: int) -> int:
        value = self._prefs.get(key, default)
        return value if isinstance(value, int) and not isinstance(value, bool) else default

    @Slot(str, str, result=str)
    def stringValue(self, key: str, default: str) -> str:
        value = self._prefs.get(key, default)
        return value if isinstance(value, str) else default

    def _set(self, key: str, value) -> None:
        try:
            if self._prefs.set(key, value):
                self.changed.emit(key)
        except (ValueError, TypeError):
            pass                               # clave no válida: se ignora (no debe romper la interfaz)

    @Slot(str, bool)
    def setBool(self, key: str, value: bool) -> None:
        self._set(key, bool(value))

    @Slot(str, int)
    def setInt(self, key: str, value: int) -> None:
        self._set(key, int(value))

    @Slot(str, str)
    def setString(self, key: str, value: str) -> None:
        self._set(key, str(value))
