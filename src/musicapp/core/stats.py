"""Contador de reproducciones por pista (tabla play_stats)."""
from __future__ import annotations

import sqlite3
from datetime import datetime

# Una reproducción cuenta apenas la pista suena unos segundos, sin importar cómo se inició
# (artista, álbum, lista, automático) ni si se oye completa. Los 3 s evitan contar un salto accidental.
COUNT_AFTER_MS = 3_000


def threshold_ms(duration_ms: int) -> int:
    """Tiempo escuchado a partir del cual la pista cuenta como una reproducción."""
    if duration_ms <= 0:
        return COUNT_AFTER_MS
    return max(1, min(COUNT_AFTER_MS, duration_ms))


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


# ---------------------------------------------------------------- más escuchado
def top_tracks(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT t.id, t.title, t.duration, al.id AS album_id, al.title AS album,
               ar.name AS artist, ps.plays AS plays
        FROM play_stats ps
        JOIN tracks t   ON t.id  = ps.track_id
        JOIN artists ar ON ar.id = t.artist_id
        JOIN albums al  ON al.id = t.album_id
        WHERE ps.plays > 0
        ORDER BY ps.plays DESC, ps.last_played DESC, t.title COLLATE NOCASE
        LIMIT ?
        """, (limit,)).fetchall()


def top_albums(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT al.id, al.title, ar.name AS artist, al.year, SUM(ps.plays) AS plays
        FROM play_stats ps
        JOIN tracks t   ON t.id  = ps.track_id
        JOIN albums al  ON al.id = t.album_id
        JOIN artists ar ON ar.id = al.album_artist_id
        WHERE ps.plays > 0
        GROUP BY al.id
        ORDER BY plays DESC, al.title COLLATE NOCASE
        LIMIT ?
        """, (limit,)).fetchall()


def top_artists(conn: sqlite3.Connection, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT ar.id, ar.name, SUM(ps.plays) AS plays,
               COUNT(DISTINCT t.album_id) AS albums, COUNT(DISTINCT t.id) AS tracks
        FROM play_stats ps
        JOIN tracks t   ON t.id  = ps.track_id
        JOIN artists ar ON ar.id = t.artist_id
        WHERE ps.plays > 0
        GROUP BY ar.id
        ORDER BY plays DESC, ar.name COLLATE NOCASE
        LIMIT ?
        """, (limit,)).fetchall()


def top_playlists(conn: sqlite3.Connection, limit: int = 8) -> list[sqlite3.Row]:
    """Listas ordenadas por lo escuchado de sus canciones (las no escuchadas, por nombre)."""
    return conn.execute(
        """
        SELECT p.id, p.name, COUNT(pt.track_id) AS tracks, COALESCE(SUM(ps.plays), 0) AS plays
        FROM playlists p
        LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.id
        LEFT JOIN play_stats ps ON ps.track_id = pt.track_id
        GROUP BY p.id
        ORDER BY plays DESC, p.name COLLATE NOCASE
        LIMIT ?
        """, (limit,)).fetchall()


def artist_top_tracks(conn: sqlite3.Connection, artist_id: int, per_album: int = 2,
                      limit: int = 12) -> list[sqlite3.Row]:
    """Hasta `per_album` canciones de cada álbum del artista (las más escuchadas de ese álbum),
    y todas juntas ordenadas por reproducciones."""
    return conn.execute(
        """
        SELECT * FROM (
            SELECT t.id, t.title, t.duration, al.id AS album_id, al.title AS album,
                   ar.name AS artist, COALESCE(ps.plays, 0) AS plays,
                   COALESCE(t.disc_no, 1) AS disc, COALESCE(t.track_no, 9999) AS no,
                   ROW_NUMBER() OVER (
                       PARTITION BY t.album_id
                       ORDER BY COALESCE(ps.plays, 0) DESC, COALESCE(t.disc_no, 1),
                                COALESCE(t.track_no, 9999), t.title COLLATE NOCASE) AS rn
            FROM tracks t
            JOIN albums al  ON al.id = t.album_id
            JOIN artists ar ON ar.id = t.artist_id
            LEFT JOIN play_stats ps ON ps.track_id = t.id
            WHERE al.album_artist_id = ? OR t.artist_id = ?
        ) WHERE rn <= ?
        ORDER BY plays DESC, album COLLATE NOCASE, disc, no
        LIMIT ?
        """, (artist_id, artist_id, per_album, limit)).fetchall()
