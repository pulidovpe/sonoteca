"""Manifiesto de sincronización: lo que el móvil necesita saber de la biblioteca (sin tocar archivos ni internet)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import API_VERSION
from ..core.db import SCHEMA_VERSION

_TRACKS = """
    SELECT t.uuid, f.content_hash AS hash, f.hash_size AS size, f.format, t.title,
           ar.name AS artist, aa.name AS album_artist, al.title AS album,
           t.track_no, t.disc_no, COALESCE(t.year, al.year) AS year, t.duration, t.genre, t.has_cover,
           EXISTS (SELECT 1 FROM lyrics l WHERE l.track_id = t.id AND l.instrumental = 0
                   AND (COALESCE(l.synced_lrc, '') <> '' OR COALESCE(l.original_text, '') <> '')) AS has_lyrics
    FROM tracks t
    JOIN files f    ON f.id  = t.file_id
    JOIN artists ar ON ar.id = t.artist_id
    JOIN albums al  ON al.id = t.album_id
    JOIN artists aa ON aa.id = al.album_artist_id
    WHERE f.kind = 'audio'
"""


def now_iso() -> str:
    moment = datetime.now(timezone.utc)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def build_manifest(conn: sqlite3.Connection) -> dict:
    """Pistas de audio con huella vigente, listas (con el orden de sus pistas por uuid) y listas borradas.

    Las pistas sin huella vigente no se anuncian todavía: se cuentan en `pending_hash` y el móvil vuelve a pedir el
    manifiesto más tarde (la huella se calcula en segundo plano)."""
    tracks, pending = [], 0
    for row in conn.execute(_TRACKS + " AND f.hash_size IS f.size AND f.hash_mtime_ns IS f.mtime_ns"
                                      " AND f.content_hash IS NOT NULL ORDER BY al.id, t.disc_no, t.track_no, t.id"):
        item = dict(row)
        item["has_cover"] = bool(item["has_cover"])
        item["has_lyrics"] = bool(item["has_lyrics"])
        tracks.append(item)
    pending = conn.execute(
        "SELECT COUNT(*) FROM files WHERE kind = 'audio' AND (content_hash IS NULL OR hash_size IS NOT size"
        " OR hash_mtime_ns IS NOT mtime_ns)").fetchone()[0]

    playlists = []
    for pl in conn.execute("SELECT id, uuid, name, updated_at FROM playlists ORDER BY name COLLATE NOCASE"):
        uuids = [r["uuid"] for r in conn.execute(
            "SELECT t.uuid FROM playlist_tracks pt JOIN tracks t ON t.id = pt.track_id"
            " JOIN files f ON f.id = t.file_id WHERE pt.playlist_id = ? AND f.kind = 'audio' ORDER BY pt.position",
            (pl["id"],))]
        playlists.append({"uuid": pl["uuid"], "name": pl["name"], "updated_at": pl["updated_at"], "tracks": uuids})
    deleted = [dict(r) for r in conn.execute("SELECT uuid, deleted_at FROM deleted_playlists ORDER BY deleted_at")]
    return {"api": API_VERSION, "schema": SCHEMA_VERSION, "generated_at": now_iso(), "pending_hash": pending,
            "tracks": tracks, "playlists": playlists, "deleted_playlists": deleted}
