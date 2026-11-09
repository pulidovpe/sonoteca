"""Carpetas de la biblioteca y exclusiones.

«Buscar música» registra las carpetas (y subcarpetas) donde hay música. El usuario puede quitar una carpeta de la
biblioteca: sus pistas salen de la base de datos y la ruta se guarda como *excluida*, de modo que el escáner la salta
en los escaneos siguientes. **Nunca se toca ningún archivo del disco** (ni papelera ni borrado).
"""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass, field

from .cleanup import prune_empty

_CHUNK = 500


def _prefix(folder: str) -> str:
    """Prefijo para comparar «está dentro de»: la carpeta más el separador (sin duplicarlo en una raíz como «/»)."""
    return folder if folder.endswith(os.sep) else folder + os.sep


def is_within(path: str, folder: str) -> bool:
    """True si `path` es `folder` o está dentro de ella."""
    return path == folder or path.startswith(_prefix(folder))


@dataclass(frozen=True)
class Exclusions:
    """Rutas que el escáner debe saltar: archivos sueltos y carpetas completas (con todo lo que contienen)."""

    files: frozenset[str] = frozenset()
    folders: tuple[str, ...] = field(default_factory=tuple)

    def folder_excluded(self, path: str) -> bool:
        return any(is_within(path, f) for f in self.folders)

    def file_excluded(self, path: str) -> bool:
        return path in self.files


def load_exclusions(conn: sqlite3.Connection) -> Exclusions:
    rows = conn.execute("SELECT path, kind FROM excluded_paths").fetchall()
    return Exclusions(
        files=frozenset(r["path"] for r in rows if r["kind"] == "file"),
        folders=tuple(r["path"] for r in rows if r["kind"] == "folder"),
    )


def record_folders(conn: sqlite3.Connection, root: str, dirs: set[str]) -> None:
    """Tras escanear `root`: el registro bajo `root` pasa a ser exactamente las carpetas donde se vio música."""
    rows = conn.execute("SELECT path FROM library_folders").fetchall()
    with conn:
        for row in rows:
            if is_within(row["path"], root) and row["path"] not in dirs:
                conn.execute("DELETE FROM library_folders WHERE path = ?", (row["path"],))
        conn.executemany("INSERT OR IGNORE INTO library_folders (path) VALUES (?)", [(d,) for d in sorted(dirs)])


def list_folders(conn: sqlite3.Connection) -> list[dict]:
    """Carpetas registradas con música, en orden de ruta.

    Cada una: path, name, tracks (pistas directamente en ella), total (con subcarpetas) y depth (cuántas carpetas
    registradas la contienen). Se omiten las que ya no tienen pistas.
    """
    paths = [r["path"] for r in conn.execute("SELECT path FROM files")]
    direct: dict[str, int] = {}
    for p in paths:
        d = os.path.dirname(p)
        direct[d] = direct.get(d, 0) + 1
    registered = sorted((r["path"] for r in conn.execute("SELECT path FROM library_folders")),
                        key=lambda p: [part.casefold() for part in p.split(os.sep)])
    out: list[dict] = []
    for folder in registered:
        total = sum(1 for p in paths if is_within(p, folder))
        if total == 0:
            continue
        out.append({"path": folder, "name": folder, "tracks": direct.get(folder, 0), "total": total, "depth": 0})
    shown = {o["path"] for o in out}
    for o in out:   # el nombre corto solo cuando la carpeta contenedora también se muestra (si no, la ruta completa)
        o["depth"] = sum(1 for other in shown if other != o["path"] and is_within(o["path"], other))
        if o["depth"] > 0:
            o["name"] = os.path.basename(o["path"].rstrip(os.sep)) or o["path"]
    return out


def _natural_key(text: str) -> list:
    """Orden «natural»: «Disco 2» antes que «Disco 10», sin distinguir mayúsculas."""
    import re

    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", text)]


def path_key(path: str) -> list:
    return [_natural_key(part) for part in path.split(os.sep)]


def list_candidates(conn: sqlite3.Connection) -> list[dict]:
    """Carpetas desde las que se puede crear una lista (página Listas).

    Son las carpetas con música (`list_folders`) más las carpetas «madre» donde se bifurcan: una carpeta sin música propia
    que contiene al menos dos ramas con música (p. ej. «Beatles» con «Abbey Road» y «Revolver»). Las carpetas que solo
    llevan a una única rama se omiten (darían la misma lista que esa rama). Cada una: path, name, tracks (directas),
    total (con subcarpetas), depth y hasChildren (tiene subcarpetas con música).
    """
    base = list_folders(conn)
    have = {b["path"] for b in base}
    branches: dict[str, set[str]] = {}
    for folder in have:
        cur = folder
        while True:
            parent = os.path.dirname(cur)
            if parent == cur:
                break
            branches.setdefault(parent, set()).add(cur)
            cur = parent
    paths = [r["path"] for r in conn.execute("SELECT path FROM files")]
    items = [dict(b) for b in base]
    for ancestor, kids in branches.items():
        if ancestor not in have and len(kids) >= 2:
            total = sum(1 for p in paths if is_within(p, ancestor))
            if total > 0:
                items.append({"path": ancestor, "name": ancestor, "tracks": 0, "total": total, "depth": 0})
    items.sort(key=lambda i: path_key(i["path"]))
    shown = [i["path"] for i in items]
    for item in items:
        item["depth"] = sum(1 for other in shown if other != item["path"] and is_within(item["path"], other))
        item["name"] = os.path.basename(item["path"].rstrip(os.sep)) or item["path"] if item["depth"] > 0 else item["path"]
        item["hasChildren"] = item["total"] > item["tracks"]
    return items


def list_excluded(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT path, kind FROM excluded_paths").fetchall()
    items = [{"path": r["path"], "kind": r["kind"],
              "name": os.path.basename(r["path"].rstrip(os.sep)) or r["path"]} for r in rows]
    return sorted(items, key=lambda i: i["path"].casefold())


def _delete_file_rows(conn: sqlite3.Connection, ids: list[int]) -> None:
    for start in range(0, len(ids), _CHUNK):
        chunk = ids[start:start + _CHUNK]
        conn.execute(f"DELETE FROM files WHERE id IN ({','.join('?' * len(chunk))})", chunk)   # cascada: pista, listas…


def exclude_folder(conn: sqlite3.Connection, folder: str) -> dict:
    """Quita de la biblioteca todo lo que hay en `folder` (subcarpetas incluidas) y la excluye de futuros escaneos.

    No modifica el disco. Devuelve {"removed": pistas quitadas, "pruned": álbumes/artistas que quedaron vacíos}.
    """
    folder = str(folder)
    ids = [r["id"] for r in conn.execute("SELECT id, path FROM files") if is_within(r["path"], folder)]
    with conn:
        _delete_file_rows(conn, ids)
        for row in conn.execute("SELECT path FROM library_folders").fetchall():
            if is_within(row["path"], folder):
                conn.execute("DELETE FROM library_folders WHERE path = ?", (row["path"],))
        conn.execute("INSERT OR IGNORE INTO excluded_paths (path, kind) VALUES (?, 'folder')", (folder,))
    return {"removed": len(ids), "pruned": prune_empty(conn)}


def exclude_files(conn: sqlite3.Connection, track_ids: list[int]) -> dict:
    """Quita pistas concretas de la biblioteca y excluye sus archivos. No modifica el disco."""
    removed = 0
    with conn:
        for start in range(0, len(track_ids), _CHUNK):
            chunk = [int(t) for t in track_ids[start:start + _CHUNK]]
            rows = conn.execute(
                f"SELECT f.id, f.path FROM files f JOIN tracks t ON t.file_id = f.id"
                f" WHERE t.id IN ({','.join('?' * len(chunk))})", chunk).fetchall()
            conn.executemany("INSERT OR IGNORE INTO excluded_paths (path, kind) VALUES (?, 'file')",
                             [(r["path"],) for r in rows])
            _delete_file_rows(conn, [r["id"] for r in rows])
            removed += len(rows)
    return {"removed": removed, "pruned": prune_empty(conn)}


def include_again(conn: sqlite3.Connection, path: str) -> bool:
    """Deja de excluir `path` (exactamente esa entrada). Hace falta volver a «Buscar música» para traerla de vuelta."""
    with conn:
        cur = conn.execute("DELETE FROM excluded_paths WHERE path = ?", (str(path),))
    return cur.rowcount > 0
