"""Archivos o carpetas soltados sobre la ventana: qué canciones contienen, cómo llamar a la lista y si están en un dispositivo externo."""
from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path, PurePosixPath, PureWindowsPath
from urllib.parse import unquote, urlparse

from .library_folders import path_key
from .models import SUPPORTED_EXTENSIONS

DEFAULT_LIST_NAME = "Canciones soltadas"
_WIN_DRIVE_URL = re.compile(r"^/[A-Za-z]:")


def to_path(item: str | Path) -> Path:
    """Ruta local de lo que entrega QML: «file:///…» (con %XX) o una ruta normal."""
    text = str(item)
    if text.startswith("file:"):
        text = unquote(urlparse(text).path)
        if _WIN_DRIVE_URL.match(text):                 # file:///C:/Música → C:/Música
            text = text[1:]
    return Path(text)


def _walk(folder: Path) -> Iterator[Path]:
    """Mismas reglas que scanner.iter_media_files: salta lo oculto y solo da los formatos soportados."""
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if not name.startswith(".") and Path(name).suffix.lower() in SUPPORTED_EXTENSIONS:
                yield Path(dirpath) / name


def collect(items: Iterable[str | Path]) -> list[Path]:
    """Canciones (y videos) de lo soltado: archivos sueltos y el contenido de las carpetas (con subcarpetas),
    sin repetidos y en orden natural (carpeta y nombre; «2» antes que «10»)."""
    seen: dict[str, Path] = {}
    for item in items:
        path = to_path(item)
        if path.is_dir():
            found: Iterable[Path] = _walk(path)
        elif path.is_file() and not path.name.startswith(".") and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            found = [path]
        else:
            continue
        for file in found:
            seen.setdefault(os.path.normcase(os.path.abspath(file)), file)
    return sorted(seen.values(), key=lambda f: path_key(str(f)))


def default_list_name(items: Iterable[str | Path]) -> str:
    """Nombre propuesto para la lista: la carpeta soltada, o la carpeta común de los archivos; si no hay, «Canciones soltadas»."""
    paths = [p for p in (to_path(i) for i in items) if p.exists()]
    if len(paths) == 1 and paths[0].is_dir() and paths[0].name:
        return paths[0].name
    parents = {p.parent for p in paths}
    if len(parents) == 1 and next(iter(parents)).name:
        return next(iter(parents)).name
    return DEFAULT_LIST_NAME


def _is_boot_volume(volume: Path) -> bool:
    try:
        return volume.resolve() == Path("/")            # «Macintosh HD» es un enlace a «/»
    except OSError:
        return False


def _drive_type(root: str) -> int:
    """GetDriveTypeW de Windows (2 = extraíble, 3 = fijo, 4 = red, 5 = CD/DVD). 0 si no se puede saber."""
    if sys.platform != "win32":
        return 0
    import ctypes
    return int(ctypes.windll.kernel32.GetDriveTypeW(root))  # type: ignore[attr-defined]


def is_external(path: str | Path, platform: str | None = None, *,
                is_boot_volume: Callable[[Path], bool] | None = None,
                drive_type: Callable[[str], int] | None = None) -> bool:
    """¿Está en un dispositivo externo (pendrive, disco USB, CD)? Heurística por sistema:
    macOS = bajo /Volumes salvo el disco de arranque; Linux = bajo /media, /run/media o /mnt; Windows = unidad extraíble o de CD.
    Las unidades de red NO cuentan como externas."""
    platform = platform or sys.platform
    if platform == "darwin":
        parts = PurePosixPath(str(path)).parts
        if len(parts) >= 3 and parts[1] == "Volumes":
            return not (is_boot_volume or _is_boot_volume)(Path("/Volumes") / parts[2])
        return False
    if platform.startswith("linux"):
        return str(path).startswith(("/media/", "/run/media/", "/mnt/"))
    if platform == "win32":
        drive = PureWindowsPath(str(path)).drive
        if len(drive) == 2 and drive[1] == ":":
            return (drive_type or _drive_type)(drive[0].upper() + ":\\") in (2, 5)
    return False
