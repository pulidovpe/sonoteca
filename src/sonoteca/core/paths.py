"""Rutas de datos y caché. Se pueden fijar con variables de entorno."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from platformdirs import user_cache_dir, user_data_dir

APP = "sonoteca"
ENV_PREFIX = "SONOTECA_"
LEGACY_ENV_PREFIX = "MUSICAPP_"   # nombre anterior a 0.9.0: se sigue aceptando


def env(name: str, default: str | None = None) -> str | None:
    """Variable de entorno SONOTECA_<name>; si no existe, la antigua MUSICAPP_<name>."""
    for prefix in (ENV_PREFIX, LEGACY_ENV_PREFIX):
        value = os.environ.get(prefix + name)
        if value is not None and value.strip() != "":
            return value
    return default


def inside_virtualenv(path: Path) -> bool:
    """True si `path` está dentro del entorno virtual activo (no aplica fuera de un venv)."""
    if sys.prefix == getattr(sys, "base_prefix", sys.prefix):
        return False
    prefix = Path(sys.prefix).resolve()
    resolved = Path(path).expanduser().resolve()
    return resolved == prefix or prefix in resolved.parents


def _outside_virtualenv(path: Path, kind: str) -> Path:
    """Los datos del usuario (portadas, copias de respaldo, base) nunca deben vivir dentro del
    entorno virtual: se borra con él. Si la ruta estándar cae ahí, se usa ~/.sonoteca/<kind>."""
    if inside_virtualenv(path):
        return Path.home() / f".{APP}" / kind
    return path


def data_dir() -> Path:
    """Base de datos, portadas guardadas y copias de respaldo.
    Prioridad: SONOTECA_DATA_DIR, luego la carpeta estándar del sistema."""
    override = env("DATA_DIR")
    if override:
        return Path(override).expanduser()
    return _outside_virtualenv(Path(user_data_dir(APP, appauthor=False)), "data")


def cache_dir() -> Path:
    """Miniaturas de portadas (regenerables). Prioridad: SONOTECA_CACHE_DIR, luego la estándar."""
    override = env("CACHE_DIR")
    if override:
        return Path(override).expanduser()
    return _outside_virtualenv(Path(user_cache_dir(APP, appauthor=False)), "cache")


def artists_dir() -> Path:
    """Fotos de artistas descargadas (se guardan con los datos del usuario, como las portadas)."""
    return data_dir() / "artists"


def covers_dir() -> Path:
    """Portadas que importan (a diferencia de las miniaturas de la caché, no se pueden regenerar):
    las que el usuario elige y las que se reemplazan en los archivos."""
    return data_dir() / "covers"
