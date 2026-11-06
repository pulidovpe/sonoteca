"""Preferencias de interfaz (vista en cuadrícula, etc.): un JSON pequeño en la carpeta de datos del usuario.

Es independiente de la base de datos y de los ajustes de red (`online/settings.py`). Es tolerante: un archivo ausente o
dañado equivale a «sin preferencias», y si no se puede escribir (disco de solo lectura) los valores se conservan en memoria
mientras la app esté abierta. «Empezar desde cero» (`portable.py`) también las borra, porque viven en la carpeta de datos."""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from . import paths

log = logging.getLogger(__name__)
FILE_NAME = "ui_prefs.json"
_MISSING = object()


def default_path() -> Path:
    return paths.data_dir() / FILE_NAME


class Prefs:
    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else default_path()
        self._data: dict[str, Any] = self._load()

    @property
    def path(self) -> Path:
        return self._path

    def _load(self) -> dict[str, Any]:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _check_key(key: str) -> str:
        if not isinstance(key, str) or not key.strip() or len(key) > 80:
            raise ValueError("clave de preferencia no válida")
        return key

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """Guarda un valor (bool, número, texto, lista o dict). Devuelve True si cambió."""
        self._check_key(key)
        json.dumps(value)                                  # ValueError/TypeError si no es serializable
        if self._data.get(key, _MISSING) == value:
            return False
        self._data[key] = value
        self._save()
        return True

    def remove(self, key: str) -> bool:
        if key not in self._data:
            return False
        del self._data[key]
        self._save()
        return True

    def _save(self) -> None:
        """Escritura atómica (archivo temporal + reemplazo): una caída no deja el JSON a medias."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=self._path.parent, prefix=".ui_prefs-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(self._data, handle, ensure_ascii=False, indent=2, sort_keys=True)
                os.replace(tmp, self._path)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
        except OSError as exc:
            log.warning("no se pudieron guardar las preferencias de interfaz: %s", exc)
