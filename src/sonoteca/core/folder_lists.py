"""Listas de reproducción creadas a partir de carpetas de la biblioteca (página Listas).

Solo se usan carpetas que «Buscar música» ya registró (`library_folders`). Cada carpeta elegida da una lista con el nombre de
la carpeta; con «incluir subcarpetas» la lista lleva también la música de todas las subcarpetas. Dentro de la lista las
canciones van por carpeta (en orden natural) y, en cada carpeta, por disco y número de pista y después por nombre de archivo.
Si el nombre ya existe (o dos carpetas elegidas se llaman igual) el usuario decide: crear con otro nombre, agregar a la
existente u omitir.
"""
from __future__ import annotations

import os
import sqlite3

from . import playlists
from .library_folders import _natural_key, is_within, path_key

MODES = ("create", "rename", "append", "skip")
_BIG = 10**9


def folder_track_ids(conn: sqlite3.Connection, folder: str, include_sub: bool) -> list[int]:
    """Pistas de la carpeta (y de sus subcarpetas si `include_sub`), en el orden descrito arriba."""
    rows = conn.execute(
        "SELECT t.id, f.path, t.disc_no, t.track_no FROM tracks t JOIN files f ON f.id = t.file_id").fetchall()
    keep = []
    for r in rows:
        directory = os.path.dirname(r["path"])
        if (is_within(directory, folder) if include_sub else directory == folder):
            keep.append((path_key(directory), r["disc_no"] or 0,
                         r["track_no"] if r["track_no"] is not None else _BIG,
                         _natural_key(os.path.basename(r["path"])), r["id"]))
    keep.sort()
    return [k[-1] for k in keep]


def default_name(folder: str) -> str:
    name = os.path.basename(folder.rstrip(os.sep)) or folder
    return playlists.clean_name(name[: playlists.MAX_NAME])


def _existing_names(conn: sqlite3.Connection) -> dict[str, int]:
    return {r["name"].casefold(): r["id"] for r in conn.execute("SELECT id, name FROM playlists")}


def unique_name(conn: sqlite3.Connection, name: str) -> str:
    """`name` si está libre; si no, «name (2)», «name (3)»… (respetando el máximo de 80 caracteres)."""
    taken = _existing_names(conn)
    if name.casefold() not in taken:
        return name
    n = 2
    while True:
        suffix = f" ({n})"
        candidate = name[: playlists.MAX_NAME - len(suffix)].rstrip() + suffix
        if candidate.casefold() not in taken:
            return candidate
        n += 1


def plan(conn: sqlite3.Connection, items: list[dict]) -> list[dict]:
    """Qué listas saldrían. `items`: [{"path", "sub"}]. Cada resultado: path, sub, name, count, conflict.

    `conflict` es "" (sin problema), "existing" (ya hay una lista con ese nombre) o "batch" (otra carpeta elegida antes tiene
    el mismo nombre). Las carpetas sin canciones se omiten.
    """
    existing = _existing_names(conn)
    used: set[str] = set()
    out: list[dict] = []
    for item in items:
        folder, sub = str(item["path"]), bool(item.get("sub"))
        ids = folder_track_ids(conn, folder, sub)
        if not ids:
            continue
        name = default_name(folder)
        key = name.casefold()
        conflict = "existing" if key in existing else ("batch" if key in used else "")
        used.add(key)
        out.append({"path": folder, "sub": sub, "name": name, "count": len(ids), "conflict": conflict})
    return out


def apply(conn: sqlite3.Connection, decisions: list[dict]) -> dict:
    """Crea las listas. `decisions`: [{"path", "sub", "name", "mode"}] con mode en `MODES` (create = nombre libre)."""
    created: list[dict] = []
    appended: list[dict] = []
    skipped = 0
    errors: list[str] = []
    for d in decisions:
        mode = d.get("mode", "create")
        if mode not in MODES:
            errors.append(f"Modo desconocido para «{d.get('name', '')}»")
            continue
        if mode == "skip":
            skipped += 1
            continue
        ids = folder_track_ids(conn, str(d["path"]), bool(d.get("sub")))
        if not ids:
            skipped += 1
            continue
        name = playlists.clean_name(str(d["name"]))
        try:
            if mode == "append":
                target = _existing_names(conn).get(name.casefold())
                if target is not None:
                    added = playlists.add_tracks(conn, target, ids, skip_existing=True)
                    appended.append({"id": target, "name": name, "added": added})
                    continue
                mode = "create"      # la lista a la que se iba a agregar ya no existe (p. ej. se omitió la primera): se crea
            if mode == "rename":
                name = unique_name(conn, name)
            playlist_id = playlists.create_from_tracks(conn, name, ids)
            created.append({"id": playlist_id, "name": name, "added": len(ids)})
        except ValueError as exc:
            errors.append(str(exc))
    return {"created": created, "appended": appended, "skipped": skipped, "errors": errors}
