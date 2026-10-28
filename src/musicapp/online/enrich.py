"""Orquesta las consultas en línea sobre la biblioteca. Nunca modifica archivos ni tags:
devuelve candidatos y el usuario confirma antes de aplicar nada."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path

from musicapp.core import paths
from musicapp.core.models import UNKNOWN_ALBUM, UNKNOWN_ARTIST

from . import coverart, musicbrainz, wikipedia
from .http import HttpClient
from .musicbrainz import AlbumCandidate
from .wikipedia import ArtistInfo


def pick_track(conn: sqlite3.Connection, album_id: int, track_id: int | None = None):
    """Pista usada para buscar un álbum "Sin álbum": la indicada o la primera del grupo."""
    sql = ("SELECT t.id, t.title, t.duration, COALESCE(t.year, al.year) AS year, ar.name AS artist"
           " FROM tracks t JOIN albums al ON al.id = t.album_id JOIN artists ar ON ar.id = t.artist_id"
           " WHERE t.album_id = ?")
    if track_id is not None:
        return conn.execute(sql + " AND t.id = ?", (album_id, track_id)).fetchone()
    return conn.execute(sql + " ORDER BY t.track_no, t.id LIMIT 1", (album_id,)).fetchone()


def track_candidates(client: HttpClient, conn: sqlite3.Connection, track_id: int) -> list[AlbumCandidate]:
    """Álbumes donde aparece una pista concreta (por su artista, título, duración y año)."""
    row = conn.execute(
        "SELECT t.id, t.title, t.duration, COALESCE(t.year, al.year) AS year, ar.name AS artist"
        " FROM tracks t JOIN albums al ON al.id = t.album_id JOIN artists ar ON ar.id = t.artist_id"
        " WHERE t.id = ?", (track_id,)).fetchone()
    if row is None or row["artist"] == UNKNOWN_ARTIST:
        return []
    return musicbrainz.search_by_track(client, row["artist"], row["title"],
                                       duration=row["duration"] or None, year=row["year"])


def album_candidates(client: HttpClient, conn: sqlite3.Connection, album_id: int,
                     limit: int = 6, track_id: int | None = None) -> list[AlbumCandidate]:
    """Posibles coincidencias en MusicBrainz para un álbum de la biblioteca. Si el álbum no tiene
    nombre ("Sin álbum"), se busca por una de sus canciones."""
    row = conn.execute(
        "SELECT al.title, ar.name AS artist FROM albums al JOIN artists ar ON ar.id = al.album_artist_id"
        " WHERE al.id = ?", (album_id,)).fetchone()
    if row is None or row["artist"] == UNKNOWN_ARTIST:
        return []
    if row["title"] != UNKNOWN_ALBUM:
        return musicbrainz.search_albums(client, row["artist"], row["title"], limit)
    track = pick_track(conn, album_id, track_id)
    if not track:
        return []
    return musicbrainz.search_by_track(client, track["artist"], track["title"],
                                       duration=track["duration"] or None, year=track["year"])


def preview_cover(client: HttpClient, candidate: AlbumCandidate, size: int = 250) -> Path | None:
    """Miniatura de la portada del candidato, en la caché (se puede borrar)."""
    folder = paths.cache_dir() / "previews"
    target = folder / f"{candidate.release_group_id}-{size}.jpg"
    if target.exists():
        return target
    data = coverart.fetch_front(client, candidate.release_group_id, size)
    if data is None:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)
    return target


def download_cover(client: HttpClient, candidate: AlbumCandidate) -> bytes | None:
    """La portada más grande disponible, lista para guardar con `cover_store`."""
    return coverart.fetch_best(client, candidate.release_group_id)


def stored_artist_info(conn: sqlite3.Connection, artist_id: int) -> dict | None:
    row = conn.execute(
        "SELECT name, mbid, bio, bio_source, bio_url, bio_lang, image_url, info_fetched_at"
        " FROM artists WHERE id = ?", (artist_id,)).fetchone()
    if row is None or not row["bio"]:
        return None
    return dict(row)


def fetch_artist_info(client: HttpClient, conn: sqlite3.Connection, artist_id: int,
                      force: bool = False) -> dict | None:
    """Información del artista: la guardada si existe; si no (o con force), la consulta y guarda."""
    if not force:
        stored = stored_artist_info(conn, artist_id)
        if stored:
            return stored
    row = conn.execute("SELECT name FROM artists WHERE id = ?", (artist_id,)).fetchone()
    if row is None or row["name"] == UNKNOWN_ARTIST:
        return None
    mbid = ""
    candidates = musicbrainz.search_artists(client, row["name"], limit=3)
    if candidates and candidates[0].similarity >= 0.9 and candidates[0].mb_score >= 85:
        mbid = candidates[0].artist_id  # solo si coincide claramente
    info: ArtistInfo | None = wikipedia.artist_info(client, row["name"], mbid)
    if info is None:
        return None
    with conn:
        conn.execute(
            "UPDATE artists SET mbid = ?, bio = ?, bio_source = ?, bio_url = ?, bio_lang = ?,"
            " image_url = ?, info_fetched_at = ? WHERE id = ?",
            (info.mbid or None, info.summary, "Wikipedia", info.url, info.language,
             info.image_url or None, datetime.now().isoformat(timespec="seconds"), artist_id))
    return stored_artist_info(conn, artist_id)
