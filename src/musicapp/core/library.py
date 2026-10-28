"""Consultas de solo lectura sobre la biblioteca (las usará la UI en la Fase 2)."""
from __future__ import annotations

import sqlite3

from .models import UNKNOWN_ALBUM, UNKNOWN_ARTIST


def list_artists(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT ar.id, ar.name, ar.sort_name,
               COUNT(DISTINCT al.id) AS albums,
               (SELECT COUNT(*) FROM tracks t WHERE t.artist_id = ar.id) AS tracks
        FROM artists ar
        LEFT JOIN albums al ON al.album_artist_id = ar.id
        WHERE EXISTS (SELECT 1 FROM tracks t WHERE t.artist_id = ar.id)
           OR EXISTS (SELECT 1 FROM albums a2 JOIN tracks t2 ON t2.album_id = a2.id
                      WHERE a2.album_artist_id = ar.id)
        GROUP BY ar.id
        ORDER BY ar.sort_name COLLATE NOCASE
        """
    ).fetchall()


def list_albums(conn: sqlite3.Connection, *, artist_id: int | None = None,
                year: int | None = None, decade: int | None = None) -> list[sqlite3.Row]:
    """`decade` es el año inicial de la década (ej. 1990)."""
    where, params = [], []
    if artist_id is not None:
        where.append("al.album_artist_id = ?")
        params.append(artist_id)
    if year is not None:
        where.append("al.year = ?")
        params.append(year)
    if decade is not None:
        where.append("al.year BETWEEN ? AND ?")
        params.extend([decade, decade + 9])
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    return conn.execute(
        f"""
        SELECT al.id, al.title, al.year, al.cover_path, ar.name AS artist,
               COUNT(t.id) AS tracks, COALESCE(SUM(t.duration), 0) AS duration
        FROM albums al
        JOIN artists ar ON ar.id = al.album_artist_id
        LEFT JOIN tracks t ON t.album_id = al.id
        {clause}
        GROUP BY al.id
        HAVING COUNT(t.id) > 0
        ORDER BY ar.sort_name COLLATE NOCASE, al.year, al.title COLLATE NOCASE
        """,
        params,
    ).fetchall()


def list_tracks(conn: sqlite3.Connection, *, album_id: int | None = None,
                artist_id: int | None = None) -> list[sqlite3.Row]:
    where, params = [], []
    if album_id is not None:
        where.append("t.album_id = ?")
        params.append(album_id)
    if artist_id is not None:
        where.append("t.artist_id = ?")
        params.append(artist_id)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    return conn.execute(
        f"""
        SELECT t.id, t.title, t.track_no, t.disc_no, t.year, t.duration, t.genre,
               ar.name AS artist, al.title AS album, f.path, f.format, f.kind
        FROM tracks t
        JOIN artists ar ON ar.id = t.artist_id
        JOIN albums  al ON al.id = t.album_id
        JOIN files   f  ON f.id  = t.file_id
        {clause}
        ORDER BY al.title COLLATE NOCASE, COALESCE(t.disc_no, 1), COALESCE(t.track_no, 9999),
                 t.title COLLATE NOCASE
        """,
        params,
    ).fetchall()


def list_artist_track_ids(conn: sqlite3.Connection, artist_id: int) -> list[int]:
    """Pistas de los álbumes del artista (las mismas que muestra su página) más las que canta él."""
    rows = conn.execute(
        """
        SELECT t.id FROM tracks t JOIN albums al ON al.id = t.album_id
        WHERE al.album_artist_id = ? OR t.artist_id = ?
        ORDER BY al.title COLLATE NOCASE, COALESCE(t.disc_no, 1), COALESCE(t.track_no, 9999),
                 t.title COLLATE NOCASE
        """,
        (artist_id, artist_id),
    ).fetchall()
    return [r["id"] for r in rows]


def list_incomplete(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Pistas con tags faltantes: sin artista o álbum, o con datos deducidos del nombre."""
    return conn.execute(
        """
        SELECT t.id, t.title, t.inferred, ar.name AS artist, al.title AS album, f.path,
               (ar.name = ?) AS no_artist, (al.title = ?) AS no_album
        FROM tracks t
        JOIN artists ar ON ar.id = t.artist_id
        JOIN albums  al ON al.id = t.album_id
        JOIN files   f  ON f.id  = t.file_id
        WHERE (t.inferred = 1 OR ar.name = ? OR al.title = ?)
          AND t.file_id NOT IN (SELECT file_id FROM review_dismissed)
        ORDER BY f.path
        """,
        (UNKNOWN_ARTIST, UNKNOWN_ALBUM, UNKNOWN_ARTIST, UNKNOWN_ALBUM),
    ).fetchall()


def get_album(conn: sqlite3.Connection, album_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT al.id, al.title, al.year, ar.id AS artist_id, ar.name AS artist,
               COUNT(t.id) AS tracks, COALESCE(SUM(t.duration), 0) AS duration
        FROM albums al
        JOIN artists ar ON ar.id = al.album_artist_id
        LEFT JOIN tracks t ON t.album_id = al.id
        WHERE al.id = ?
        GROUP BY al.id
        """,
        (album_id,),
    ).fetchone()


def get_track(conn: sqlite3.Connection, track_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT t.id, t.title, t.duration, ar.name AS artist, ar.id AS artist_id, al.id AS album_id,
               al.title AS album, f.path, f.kind, f.format
        FROM tracks t
        JOIN artists ar ON ar.id = t.artist_id
        JOIN albums  al ON al.id = t.album_id
        JOIN files   f  ON f.id  = t.file_id
        WHERE t.id = ?
        """,
        (track_id,),
    ).fetchone()


def list_decades(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT (year / 10) * 10 AS decade, COUNT(*) AS albums FROM albums"
        " WHERE year IS NOT NULL GROUP BY decade ORDER BY decade"
    ).fetchall()


def list_years(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT year, COUNT(*) AS albums FROM albums WHERE year IS NOT NULL"
        " GROUP BY year ORDER BY year"
    ).fetchall()


def search(conn: sqlite3.Connection, text: str, limit: int = 50) -> list[dict]:
    """Pistas que coinciden con el texto (sin acentos ni mayúsculas, varias palabras)."""
    from .search import SearchIndex

    return SearchIndex.build(conn).query(text, max_tracks=limit).tracks


def stats(conn: sqlite3.Connection) -> dict[str, float]:
    row = conn.execute(
        """
        SELECT (SELECT COUNT(*) FROM tracks)  AS tracks,
               (SELECT COUNT(*) FROM albums)  AS albums,
               (SELECT COUNT(*) FROM artists) AS artists,
               (SELECT COUNT(*) FROM files WHERE kind='video') AS videos,
               (SELECT COALESCE(SUM(duration),0) FROM tracks) AS seconds,
               (SELECT COALESCE(SUM(size),0) FROM files) AS bytes
        """
    ).fetchone()
    return dict(row)
