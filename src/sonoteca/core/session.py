"""Estado del reproductor entre sesiones: lista, pista actual y punto, Aleatorio, repetir, volumen y silencio.

Se guarda en un JSON pequeño (`session.json`, carpeta de datos). La lista se guarda con RUTAS de archivo y no con ids de
pista: los ids pueden cambiar tras importar una biblioteca o empezar de cero, las rutas no. Es tolerante: archivo ausente o
dañado = «sin sesión»; lo que ya no está en la biblioteca simplemente se omite. Python puro, sin Qt.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections.abc import Iterable
from pathlib import Path

FILE_NAME = "session.json"
VERSION = 1
_REPEAT = {"off", "all", "one"}
_CHUNK = 500
_HISTORY = 50


def default_path() -> Path:
    from . import paths
    return paths.data_dir() / FILE_NAME


def paths_for_ids(conn: sqlite3.Connection, ids: Iterable[int]) -> dict[int, str]:
    wanted = list(dict.fromkeys(int(i) for i in ids))
    out: dict[int, str] = {}
    for start in range(0, len(wanted), _CHUNK):
        part = wanted[start:start + _CHUNK]
        marks = ",".join("?" * len(part))
        for row in conn.execute(
                f"SELECT t.id AS id, f.path AS path FROM tracks t JOIN files f ON f.id = t.file_id WHERE t.id IN ({marks})",
                part):
            out[row["id"]] = row["path"]
    return out


def ids_for_paths(conn: sqlite3.Connection, names: Iterable[str]) -> dict[str, int]:
    wanted = list(dict.fromkeys(str(n) for n in names))
    out: dict[str, int] = {}
    for start in range(0, len(wanted), _CHUNK):
        part = wanted[start:start + _CHUNK]
        marks = ",".join("?" * len(part))
        for row in conn.execute(
                f"SELECT t.id AS id, f.path AS path FROM tracks t JOIN files f ON f.id = t.file_id WHERE f.path IN ({marks})",
                part):
            out[row["path"]] = row["id"]
    return out


def build_state(snapshot: dict, id_to_path: dict[int, str], *, volume: float, muted: bool, position_ms: int) -> dict:
    """Estado serializable a partir de `PlayQueue.snapshot()`. Las pistas sin ruta conocida se omiten."""
    items, order = snapshot["items"], snapshot["order"]
    keep = [i for i, track in enumerate(items) if track in id_to_path]
    remap = {old: new for new, old in enumerate(keep)}
    pos = snapshot["pos"]
    new_pos = sum(1 for p, idx in enumerate(order) if p < pos and idx in remap) if pos >= 0 else -1
    current_kept = 0 <= pos < len(order) and order[pos] in remap
    return {
        "version": VERSION,
        "volume": float(volume),
        "muted": bool(muted),
        "shuffle": bool(snapshot["shuffle"]),
        "repeat": snapshot["repeat"],
        "position_ms": int(position_ms) if current_kept else 0,
        "queue": {
            "items": [id_to_path[items[i]] for i in keep],
            "order": [remap[idx] for idx in order if idx in remap],
            "pos": new_pos,
            "history": [id_to_path[t] for t in snapshot["history"][-_HISTORY:] if t in id_to_path],
        },
    }


def parse_state(data: object, path_to_id: dict[str, int]) -> dict | None:
    """Estado leído -> valores listos para restaurar (con ids), o None si no sirve. Lo que ya no está en la biblioteca se omite.

    Devuelve {volume, muted, shuffle, repeat, position_ms, items, order, pos, history, current_missing}."""
    if not isinstance(data, dict) or data.get("version") != VERSION:
        return None
    queue = data.get("queue") if isinstance(data.get("queue"), dict) else {}
    names = [n for n in queue.get("items", []) if isinstance(n, str)] if isinstance(queue.get("items"), list) else []
    order = queue.get("order") if isinstance(queue.get("order"), list) else []
    if sorted(order) != list(range(len(names))) or not all(isinstance(i, int) for i in order):
        order = list(range(len(names)))
    pos = queue.get("pos") if isinstance(queue.get("pos"), int) else -1
    kept = [i for i, name in enumerate(names) if name in path_to_id]
    remap = {old: new for new, old in enumerate(kept)}
    new_order = [remap[i] for i in order if i in remap]
    current_kept = 0 <= pos < len(order) and order[pos] in remap
    new_pos = sum(1 for p, i in enumerate(order) if p < pos and i in remap) if pos >= 0 else -1
    if new_order:
        new_pos = min(new_pos, len(new_order) - 1) if new_pos >= 0 else -1
    else:
        new_pos = -1
    volume = data.get("volume")
    repeat = data.get("repeat")
    position = data.get("position_ms")
    history = queue.get("history") if isinstance(queue.get("history"), list) else []
    return {
        "volume": min(1.0, max(0.0, float(volume))) if isinstance(volume, (int, float)) else 0.8,
        "muted": bool(data.get("muted", False)),
        "shuffle": bool(data.get("shuffle", False)),
        "repeat": repeat if repeat in _REPEAT else "off",
        "position_ms": max(0, int(position)) if isinstance(position, (int, float)) and current_kept else 0,
        "items": [path_to_id[names[i]] for i in kept],
        "order": new_order,
        "pos": new_pos,
        "history": [path_to_id[n] for n in history if isinstance(n, str) and n in path_to_id],
        "current_missing": not current_kept,
    }


def names_in(data: object) -> list[str]:
    """Rutas que menciona un estado leído (para consultarlas en la base de una sola vez)."""
    if not isinstance(data, dict) or not isinstance(data.get("queue"), dict):
        return []
    queue = data["queue"]
    out: list[str] = []
    for key in ("items", "history"):
        values = queue.get(key)
        if isinstance(values, list):
            out.extend(v for v in values if isinstance(v, str))
    return out


def load(path: Path | str) -> dict | None:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return raw if isinstance(raw, dict) else None


def save(path: Path | str, state: dict) -> bool:
    """Escritura atómica; si falla (disco de solo lectura) devuelve False sin romper nada."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".session-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, ensure_ascii=False)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return True
    except OSError:
        return False
