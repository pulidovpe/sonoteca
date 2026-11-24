"""Estadísticas de reproducción que el móvil anotó sin conexión (`POST /v1/plays`). Protocolo: docs/SYNC.md.

Cada reproducción llega como un EVENTO con id único. El id se guarda en `sync_play_events`, así que reenviar un lote (porque se
cortó la conexión antes de la respuesta) no cuenta dos veces. Cada evento nuevo suma 1 a `play_stats` (el mismo contador que usa la
app de escritorio) y adelanta `last_played` si es más reciente."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta, timezone

from .manifest import now_iso

MAX_EVENTS = 5000   # por petición (el servidor limita el cuerpo a 2 MB; un evento ocupa ~150 bytes)
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class PlaysError(ValueError):
    """Petición mal formada (se responde 400)."""


def _parse_utc(text: object) -> datetime | None:
    """Fecha ISO 8601 en UTC (`2026-11-18T10:00:00.000Z`) → datetime con zona; None si no es válida."""
    if not isinstance(text, str) or not 10 <= len(text) <= 40:
        return None
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment.astimezone(timezone.utc) if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _local_naive_iso(moment: datetime) -> str:
    """Como guarda `stats.record_play` la última escucha: hora local, sin zona, a segundos."""
    return moment.astimezone().replace(tzinfo=None).isoformat(timespec="seconds")


def apply_plays(conn: sqlite3.Connection, device_id: str, body: dict) -> dict:
    """Aplica un lote de eventos `{id, track_uuid, played_at}`. Devuelve `{accepted, duplicates, unknown, invalid}`:
    `unknown` = ids de eventos de pistas que ya no existen en el escritorio; `invalid` = ids mal formados. El móvil descarta
    todo el lote cuando recibe 200 (lo desconocido o inválido no se arreglaría reenviándolo)."""
    events = body.get("events")
    if not isinstance(events, list):
        raise PlaysError("falta la lista «events»")
    if len(events) > MAX_EVENTS:
        raise PlaysError(f"demasiados eventos en una petición (máximo {MAX_EVENTS})")
    accepted, duplicates = 0, 0
    unknown: list[str] = []
    invalid: list[str] = []
    received = now_iso()
    limit = datetime.now(timezone.utc) + timedelta(days=1)
    with conn:
        for event in events:
            if not isinstance(event, dict):
                invalid.append("")
                continue
            event_id, track_uuid = event.get("id"), event.get("track_uuid")
            moment = _parse_utc(event.get("played_at"))
            if not isinstance(event_id, str) or not 8 <= len(event_id) <= 64 or moment is None \
                    or not isinstance(track_uuid, str) or not _UUID.match(track_uuid):
                invalid.append(event_id if isinstance(event_id, str) else "")
                continue
            moment = min(moment, limit)   # un reloj del móvil adelantado no deja la «última escucha» en el futuro
            track = conn.execute("SELECT id FROM tracks WHERE uuid = ?", (track_uuid,)).fetchone()
            if track is None:
                unknown.append(event_id)
                continue
            inserted = conn.execute(
                "INSERT OR IGNORE INTO sync_play_events (event_id, device_id, track_uuid, played_at, received_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (event_id, device_id, track_uuid, moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z",
                 received)).rowcount
            if not inserted:
                duplicates += 1
                continue
            conn.execute(
                "INSERT INTO play_stats (track_id, plays, last_played) VALUES (?, 1, ?)"
                " ON CONFLICT(track_id) DO UPDATE SET plays = plays + 1,"
                " last_played = CASE WHEN last_played IS NULL OR last_played < excluded.last_played"
                " THEN excluded.last_played ELSE last_played END",
                (track["id"], _local_naive_iso(moment)))
            accepted += 1
    return {"accepted": accepted, "duplicates": duplicates, "unknown": unknown, "invalid": invalid}
