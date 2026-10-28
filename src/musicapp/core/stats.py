"""Contador de reproducciones por pista (tabla play_stats)."""
from __future__ import annotations

import sqlite3
from datetime import datetime

# Una pista cuenta como reproducida al escuchar la mitad (máximo 4 minutos), como el scrobbling habitual
COUNT_CAP_MS = 240_000
COUNT_UNKNOWN_DURATION_MS = 30_000


def threshold_ms(duration_ms: int) -> int:
    """Tiempo escuchado a partir del cual la pista cuenta como una reproducción."""
    if duration_ms <= 0:
        return COUNT_UNKNOWN_DURATION_MS
    return max(1, min(duration_ms // 2, COUNT_CAP_MS))


def record_play(conn: sqlite3.Connection, track_id: int) -> int:
    """Suma una reproducción y devuelve el total."""
    with conn:
        conn.execute(
            "INSERT INTO play_stats (track_id, plays, last_played) VALUES (?, 1, ?)"
            " ON CONFLICT(track_id) DO UPDATE SET plays = plays + 1, last_played = excluded.last_played",
            (track_id, datetime.now().isoformat(timespec="seconds")))
    return play_counts(conn, [track_id])[track_id]


def play_counts(conn: sqlite3.Connection, track_ids: list[int]) -> dict[int, int]:
    ids = [int(i) for i in track_ids]
    out = {i: 0 for i in ids}
    if ids:
        marks = ",".join("?" * len(ids))
        for row in conn.execute(
                f"SELECT track_id, plays FROM play_stats WHERE track_id IN ({marks})", ids):
            out[row["track_id"]] = row["plays"]
    return out
