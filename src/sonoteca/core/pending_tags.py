"""Escrituras de tags aplazadas (Windows: el archivo que suena no se puede reemplazar mientras está abierto).

Idea: los tags nuevos se escriben y verifican en una copia oculta junto al archivo (`.nombre.sonoteca-pending.ext`). La
biblioteca y las portadas leen de esa copia (`effective_source`), así que la app los muestra al instante. Cuando el
archivo real queda libre (la canción termina, cambia la pista o se cierra la app) `flush` reemplaza el original por la copia.

Un diario (`pending_tags.json` en la carpeta de datos) recuerda qué archivos tienen copia pendiente, de modo que si la app
se cierra de golpe, el siguiente arranque termina el trabajo. Sin dependencias de Qt ni de mutagen.
"""
from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable, Iterable
from pathlib import Path

from . import paths

# Toda operación que decide entre «escribir ya» y «dejar pendiente» (o que vuelca lo pendiente) toma este cerrojo: evita
# que una edición y un volcado simultáneos se pisen la misma copia.
LOCK = threading.RLock()

JOURNAL_NAME = "pending_tags.json"


def pending_path(path: Path | str) -> Path:
    path = Path(path)
    return path.with_name(f".{path.stem}.sonoteca-pending{path.suffix}")


def has_pending(path: Path | str) -> bool:
    return pending_path(path).is_file()


def effective_source(path: Path | str) -> Path:
    """Dónde están hoy los tags de `path`: la copia pendiente si existe, y si no el propio archivo."""
    path = Path(path)
    pending = pending_path(path)
    return pending if pending.is_file() else path


def replace_with_retry(tmp: Path, path: Path, attempts: int = 12, delay: float = 0.15) -> None:
    """os.replace con reintentos. En Windows el reemplazo falla con PermissionError [WinError 5/32] mientras algo tiene el
    archivo abierto (el reproductor al soltarlo, el antivirus o el indexador); suele liberarse en menos de un segundo.
    Solo reintenta PermissionError; cualquier otro error sale de inmediato."""
    for attempt in range(attempts):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)


# ---- diario ----
def _journal_file() -> Path:
    return paths.data_dir() / JOURNAL_NAME


def registered() -> list[str]:
    """Rutas con copia pendiente según el diario (puede incluir alguna que ya no exista)."""
    try:
        data = json.loads(_journal_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [p for p in data if isinstance(p, str)] if isinstance(data, list) else []


def _save(items: Iterable[str]) -> None:
    target = _journal_file()
    items = sorted(set(items))
    try:
        if not items:
            target.unlink(missing_ok=True)
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        pass  # el diario es una red de seguridad: no debe romper la edición


def register(path: Path | str) -> None:
    with LOCK:
        _save([*registered(), str(path)])


def unregister(path: Path | str) -> None:
    with LOCK:
        current = registered()
        if str(path) in current:
            _save(p for p in current if p != str(path))


def pending_count() -> int:
    return len(registered())


# ---- volcado ----
def flush(path: Path | str, *, attempts: int = 12, delay: float = 0.15) -> str:
    """Reemplaza `path` por su copia pendiente.

    Devuelve «done» (reemplazado), «none» (no había nada pendiente o se descartó: el original ya no existe, no se debe
    recrear) o «locked» (sigue abierto: queda pendiente para el próximo intento)."""
    path = Path(path)
    with LOCK:
        pending = pending_path(path)
        if not pending.is_file():
            unregister(path)
            return "none"
        if not path.is_file():                       # el archivo se borró o movió: nunca se recrea
            pending.unlink(missing_ok=True)
            unregister(path)
            return "none"
        try:
            replace_with_retry(pending, path, attempts, delay)
        except PermissionError:
            return "locked"
        except OSError:
            return "locked"
        unregister(path)
        return "done"


def flush_all(keep: Iterable[Path | str] = (), *, attempts: int = 12, delay: float = 0.15,
              is_busy: Callable[[Path], bool] | None = None,
              on_done: Callable[[Path], None] | None = None) -> dict:
    """Vuelca todo lo pendiente salvo `keep` (lo que está sonando ahora) y lo que `is_busy` declare en uso.

    `on_done(ruta)` se llama por cada archivo reemplazado (p. ej. para actualizar tamaño/fecha en la base).
    Devuelve {"done": n, "locked": n, "skipped": n}."""
    skip = {str(Path(k)) for k in keep}
    out = {"done": 0, "locked": 0, "skipped": 0}
    for name in registered():
        path = Path(name)
        if str(path) in skip or (is_busy is not None and is_busy(path)):
            out["skipped"] += 1
            continue
        result = flush(path, attempts=attempts, delay=delay)
        if result == "done":
            out["done"] += 1
            if on_done is not None:
                on_done(path)
        elif result == "locked":
            out["locked"] += 1
    return out
