"""Aviso tras actualizar la base de datos y mensajes claros cuando no se puede abrir o actualizar (sin Qt)."""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from sonoteca.core import db

_NEWER = re.compile(r"versi[óo]n\s+(\d+).*\((\d+)\)")


def peek_version(path: Path | str) -> int:
    """Versión del esquema de la base SIN abrirla para migrar (0 si no existe o no se puede leer). Solo lectura."""
    p = Path(path)
    if not p.is_file():
        return 0
    try:
        conn = sqlite3.connect(f"{p.resolve().as_uri()}?mode=ro", uri=True)
    except sqlite3.Error:
        return 0
    try:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def _folder_url(path: Path) -> str:
    try:
        return path.resolve().parent.as_uri()
    except (OSError, ValueError):
        return ""


def after_open(path: Path | str, before: int) -> dict:
    """Qué pasó con la base al abrirla: `before` es lo que devolvió peek_version antes de abrir."""
    now = peek_version(path)
    if before <= 0 or now <= before:
        return {"migrated": False}
    backup = db.backup_path(Path(path), before)
    info = {"migrated": True, "fromVersion": before, "toVersion": now, "backup": "", "folderUrl": ""}
    if backup.exists():
        info.update(backup=str(backup), folderUrl=_folder_url(backup))
    return info


def latest_backup(path: Path | str) -> Path | None:
    """La copia de seguridad más reciente (library.db.v<N>.bak) junto a la base, si hay alguna."""
    p = Path(path)
    found = sorted(p.parent.glob(p.name + ".v*.bak"), key=lambda f: f.stat().st_mtime)
    return found[-1] if found else None


def describe_failure(path: Path | str, exc: BaseException, before: int = 0) -> dict:
    """Mensaje para el usuario cuando no se pudo abrir o actualizar la base. `kind`: newer, locked, damaged u other."""
    p = Path(path)
    text = str(exc)
    info = {"kind": "other", "title": "No se pudo abrir o actualizar tu biblioteca", "message": "", "backup": "",
            "folderUrl": _folder_url(p), "dbPath": str(p), "details": f"{type(exc).__name__}: {text}"}
    newer = _NEWER.search(text) if isinstance(exc, RuntimeError) else None
    if newer:
        found, known = int(newer.group(1)), int(newer.group(2))
        info.update(kind="newer", title="Esta biblioteca es de una versión más nueva de Sonoteca")
        info["message"] = (f"Tu base de datos está en el formato v{found} y esta versión de Sonoteca solo conoce hasta el v{known}. "
                           "Ábrela con una versión más reciente de Sonoteca. No se ha cambiado nada.")
        backup = db.backup_path(p, known)
        if backup.exists():
            info["backup"] = str(backup)
            info["message"] += (f" Si prefieres volver a esta versión, la actualización dejó una copia en el formato v{known}: "
                                f"cierra Sonoteca y sustituye «{p.name}» por la copia «{backup.name}».")
        return info
    if isinstance(exc, sqlite3.OperationalError) and "locked" in text.lower():
        info.update(kind="locked", title="La biblioteca está en uso")
        info["message"] = ("Otra ventana de Sonoteca u otro programa está usando la base de datos. "
                           "Ciérralos y vuelve a abrir Sonoteca.")
        return info
    if isinstance(exc, sqlite3.DatabaseError):
        info.update(kind="damaged", title="No se pudo leer tu biblioteca")
        info["message"] = f"El archivo «{p.name}» parece dañado o no es una base de datos de Sonoteca."
        backup = latest_backup(p)
        if backup is not None:
            info["backup"] = str(backup)
            info["message"] += " En la carpeta de datos hay copias de seguridad de actualizaciones anteriores; la más reciente se muestra abajo."
        return info
    info["message"] = "Ocurrió un error al abrir la base de datos."
    backup = db.backup_path(p, before) if before > 0 else None
    if backup is not None and backup.exists():
        info["backup"] = str(backup)
        info["message"] += " Antes de actualizar, Sonoteca guardó una copia de tu biblioteca (ruta abajo); puedes volver a ella."
    return info
