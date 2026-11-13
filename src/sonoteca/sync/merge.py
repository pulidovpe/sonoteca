"""Aplica en la base del escritorio los cambios de listas que llegan del móvil. Gana la última modificación.

Regla: se compara `updated_at` (UTC, ISO 8601). Una marca del futuro lejano (reloj del móvil mal puesto) se recorta a
«ahora». El móvil y el escritorio deben tener la hora razonablemente bien; es una limitación conocida del esquema
«última escritura gana» (docs/SYNC.md)."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone

from ..core.playlists import MAX_NAME, clean_name
from .manifest import now_iso

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
MAX_TRACKS = 100_000
FUTURE_SLACK = timedelta(days=1)


class MergeError(ValueError):
    """Petición inválida (el servidor responde 400)."""


class Conflict(Exception):
    """La lista fue borrada o modificada después (el servidor responde 409)."""


def parse_ts(value: object) -> datetime:
    if not isinstance(value, str):
        raise MergeError("updated_at debe ser texto ISO 8601")
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise MergeError("updated_at no es una fecha ISO 8601 válida") from None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _fmt(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _clamp(moment: datetime) -> datetime:
    limit = datetime.now(timezone.utc) + FUTURE_SLACK
    return min(moment, limit)


def _free_name(conn: sqlite3.Connection, name: str, own_id: int | None) -> str:
    """Nombre libre (los nombres son únicos sin distinguir mayúsculas): añade « (móvil)» si hace falta."""
    candidate, n = name, 1
    while True:
        row = conn.execute("SELECT id FROM playlists WHERE name = ? COLLATE NOCASE", (candidate,)).fetchone()
        if row is None or row["id"] == own_id:
            return candidate
        n += 1
        suffix = " (móvil)" if n == 2 else f" (móvil {n - 1})"
        candidate = name[: MAX_NAME - len(suffix)] + suffix


def apply_playlist(conn: sqlite3.Connection, uuid: str, payload: dict) -> dict:
    """Crea o actualiza la lista `uuid`. Devuelve {"applied": bool, "name", "updated_at", "missing": [uuid de pistas
    desconocidas]}. Lanza MergeError (400) o Conflict (409)."""
    if not UUID_RE.match(uuid):
        raise MergeError("uuid de lista inválido")
    try:
        name = clean_name(payload.get("name", ""))
    except ValueError as exc:
        raise MergeError(str(exc)) from None
    track_uuids = payload.get("tracks")
    if not isinstance(track_uuids, list) or len(track_uuids) > MAX_TRACKS \
            or not all(isinstance(u, str) and UUID_RE.match(u) for u in track_uuids):
        raise MergeError("`tracks` debe ser una lista de uuid de pistas")
    incoming = _clamp(parse_ts(payload.get("updated_at")))

    ids, missing = [], []
    for track_uuid in track_uuids:
        row = conn.execute("SELECT t.id FROM tracks t JOIN files f ON f.id = t.file_id"
                           " WHERE t.uuid = ? AND f.kind = 'audio'", (track_uuid,)).fetchone()
        (ids if row else missing).append(row["id"] if row else track_uuid)

    existing = conn.execute("SELECT id, name, updated_at FROM playlists WHERE uuid = ?", (uuid,)).fetchone()
    with conn:
        if existing is None:
            tomb = conn.execute("SELECT deleted_at FROM deleted_playlists WHERE uuid = ?", (uuid,)).fetchone()
            if tomb and parse_ts(tomb["deleted_at"]) >= incoming:
                raise Conflict("la lista se borró en el escritorio después de esa versión")
            final = _free_name(conn, name, None)
            playlist_id = conn.execute("INSERT INTO playlists (name, uuid, updated_at) VALUES (?, ?, ?)",
                                       (final, uuid, _fmt(incoming))).lastrowid
            conn.execute("DELETE FROM deleted_playlists WHERE uuid = ?", (uuid,))
        else:
            if parse_ts(existing["updated_at"]) >= incoming:
                return {"applied": False, "name": existing["name"], "updated_at": existing["updated_at"],
                        "missing": missing}
            playlist_id = existing["id"]
            final = _free_name(conn, name, playlist_id)
            conn.execute("UPDATE playlists SET name = ?, updated_at = ? WHERE id = ?",
                         (final, _fmt(incoming), playlist_id))
        conn.execute("DELETE FROM playlist_tracks WHERE playlist_id = ?", (playlist_id,))
        conn.executemany("INSERT INTO playlist_tracks (playlist_id, track_id, position) VALUES (?, ?, ?)",
                         [(playlist_id, track_id, i) for i, track_id in enumerate(ids)])
        # los disparadores tocaron updated_at al reescribir las pistas: se fija la marca del móvil al final
        conn.execute("UPDATE playlists SET updated_at = ? WHERE id = ?", (_fmt(incoming), playlist_id))
    return {"applied": True, "name": final, "updated_at": _fmt(incoming), "missing": missing}


def delete_playlist(conn: sqlite3.Connection, uuid: str, deleted_at: object) -> dict:
    """Borra la lista si no se modificó después de `deleted_at`. Si ya no existe, es éxito (idempotente)."""
    if not UUID_RE.match(uuid):
        raise MergeError("uuid de lista inválido")
    moment = _clamp(parse_ts(deleted_at))
    row = conn.execute("SELECT id, updated_at FROM playlists WHERE uuid = ?", (uuid,)).fetchone()
    if row is None:
        return {"deleted": False, "already_gone": True}
    if parse_ts(row["updated_at"]) > moment:
        raise Conflict("la lista se modificó en el escritorio después de borrarla en el móvil")
    with conn:
        conn.execute("DELETE FROM playlists WHERE id = ?", (row["id"],))
    return {"deleted": True, "already_gone": False}


__all__ = ["apply_playlist", "delete_playlist", "MergeError", "Conflict", "now_iso"]
