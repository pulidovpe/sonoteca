"""Manifiesto de sincronización: lo que el móvil necesita saber de la biblioteca (sin tocar archivos ni internet)."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from . import API_VERSION
from ..core.db import SCHEMA_VERSION

# Huella vigente: la calculada con el tamaño y la fecha ACTUALES del archivo (si no, el contenido pudo cambiar y no se anuncia).
_HASH_CURRENT = "(f.content_hash IS NOT NULL AND f.hash_size IS f.size AND f.hash_mtime_ns IS f.mtime_ns)"

_TRACKS = f"""
    SELECT t.uuid, CASE WHEN {_HASH_CURRENT} THEN f.content_hash END AS hash,
           CASE WHEN {_HASH_CURRENT} THEN f.hash_size END AS size, f.format, f.path AS path, t.title,
           ar.name AS artist, aa.name AS album_artist, al.title AS album,
           t.track_no, t.disc_no, COALESCE(t.year, al.year) AS year, t.duration, t.genre, t.has_cover,
           COALESCE((SELECT ps.plays FROM play_stats ps WHERE ps.track_id = t.id), 0) AS plays,
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
    """TODAS las pistas de audio, listas (con el orden de sus pistas por uuid) y listas borradas.

    Una pista sin huella vigente se anuncia igual, con `hash` y `size` en null (se cuenta en `pending_hash` y la huella se
    calcula en segundo plano): así el móvil ve el catálogo completo y puede borrar con seguridad lo que ya no existe
    (`complete: true`). Antes solo se anunciaban las pistas con huella, y mientras hubiera pendientes el móvil no borraba
    nada: no aparecían las novedades y seguían viéndose artistas y nombres viejos."""
    tracks, pending, missing = [], 0, 0
    for row in conn.execute(_TRACKS + " ORDER BY al.id, t.disc_no, t.track_no, t.id"):
        item = dict(row)
        path = item.pop("path")
        item["has_cover"] = bool(item["has_cover"])
        item["has_lyrics"] = bool(item["has_lyrics"])
        # Una pista cuyo archivo ya NO está en el disco del escritorio (borrado, movido, disco externo desconectado) se anuncia
        # como no disponible: sigue en el catálogo del móvil (lo ya descargado no se pierde), pero no se ofrece para descargar
        # (pedirla daría 410) y NO cuenta como «huella pendiente» para siempre.
        item["available"] = os.path.exists(path)
        if not item["available"]:
            item["hash"], item["size"] = None, None
            missing += 1
        elif item["hash"] is None:
            pending += 1
        tracks.append(item)
    video = conn.execute("SELECT COUNT(*) FROM tracks t JOIN files f ON f.id = t.file_id WHERE f.kind <> 'audio'").fetchone()[0]

    playlists = []
    for pl in conn.execute("SELECT id, uuid, name, updated_at FROM playlists ORDER BY name COLLATE NOCASE"):
        uuids = [r["uuid"] for r in conn.execute(
            "SELECT t.uuid FROM playlist_tracks pt JOIN tracks t ON t.id = pt.track_id"
            " JOIN files f ON f.id = t.file_id WHERE pt.playlist_id = ? AND f.kind = 'audio' ORDER BY pt.position",
            (pl["id"],))]
        playlists.append({"uuid": pl["uuid"], "name": pl["name"], "updated_at": pl["updated_at"], "tracks": uuids})
    deleted = [dict(r) for r in conn.execute("SELECT uuid, deleted_at FROM deleted_playlists ORDER BY deleted_at")]
    return {"api": API_VERSION, "schema": SCHEMA_VERSION, "generated_at": now_iso(), "pending_hash": pending, "complete": True,
            "missing_files": missing, "video_tracks": video,
            "tracks": tracks, "playlists": playlists, "deleted_playlists": deleted}
