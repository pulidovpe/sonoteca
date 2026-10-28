"""Descarga automática de portadas de álbumes y de fotos/información de artistas.

Se usa después de escanear la música: solo toma lo que está BIEN IDENTIFICADO (artista y álbum con tags reales,
no deducidos del nombre del archivo) y solo lo que falta. Criterios estrictos, porque nadie confirma cada caso:
  · álbum: la primera coincidencia de MusicBrainz debe ser «probable» (título casi idéntico, buen puntaje, sin
    empates); si hay dudas se deja para elegir a mano desde «Buscar portada».
  · artista: coincidencia clara en MusicBrainz y su ficha de Wikipedia (por Wikidata).
Nunca modifica los archivos de música ni sus tags: las portadas se guardan en la carpeta de datos de la app
(`covers/downloaded`) y se muestran solo si el álbum no tiene portada propia (embebida o de carpeta).
Lo que ya se intentó no se repite hasta pasados RETRY_DAYS días.
"""
from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sonoteca.core import cover_store, paths
from sonoteca.core.covers import album_cover_source, artist_photo
from sonoteca.core.models import UNKNOWN_ALBUM, UNKNOWN_ARTIST
from sonoteca.core.tag_writer import image_mime

from . import enrich, musicbrainz, wikipedia
from .http import HttpClient, OfflineError, OnlineError

# Estimaciones de planificación (no medidas): MusicBrainz admite 1 consulta cada 1,1 s; un álbum son ~2 consultas
# a MusicBrainz + 1-2 descargas; un artista, 2 a MusicBrainz + 3 a Wikipedia/Wikidata + la foto.
ALBUM_SECONDS = 3.5
ARTIST_SECONDS = 4.0
RETRY_DAYS = 30
MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_CONSECUTIVE_ERRORS = 5
_COMPILATION_ARTISTS = {"various artists", "varios artistas", "varios", "va", "v.a."}

ProgressCb = Callable[[int, int, str], None]


@dataclass
class Plan:
    albums: list[int] = field(default_factory=list)
    artists: list[int] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.albums) + len(self.artists)

    @property
    def seconds(self) -> float:
        return len(self.albums) * ALBUM_SECONDS + len(self.artists) * ARTIST_SECONDS


def format_duration(seconds: float) -> str:
    """'menos de un minuto', 'unos 12 minutos', 'unas 2 h 30 min'."""
    minutes = round(seconds / 60)
    if seconds < 60:
        return "menos de un minuto"
    if minutes < 60:
        return f"unos {minutes} minutos" if minutes != 1 else "alrededor de 1 minuto"
    hours, rest = divmod(minutes, 60)
    return f"unas {hours} h {rest:02d} min" if rest else f"unas {hours} h"


def _cutoff(now: datetime | None) -> str:
    return ((now or datetime.now()) - timedelta(days=RETRY_DAYS)).isoformat(timespec="seconds")


def plan(conn: sqlite3.Connection, now: datetime | None = None) -> Plan:
    """Qué falta y vale la pena buscar. No usa internet."""
    cutoff = _cutoff(now)
    album_rows = conn.execute(
        "SELECT al.id FROM albums al JOIN artists ar ON ar.id = al.album_artist_id"
        " WHERE al.title != ? AND ar.name != ?"
        "   AND (al.cover_checked_at IS NULL OR al.cover_checked_at < ?)"
        "   AND EXISTS (SELECT 1 FROM tracks t WHERE t.album_id = al.id)"
        "   AND NOT EXISTS (SELECT 1 FROM tracks t WHERE t.album_id = al.id AND t.inferred = 1)"
        " ORDER BY al.id", (UNKNOWN_ALBUM, UNKNOWN_ARTIST, cutoff)).fetchall()
    albums = [r["id"] for r in album_rows if album_cover_source(conn, r["id"]) is None]
    artist_rows = conn.execute(
        "SELECT ar.id, ar.name FROM artists ar WHERE ar.name != ? AND ar.info_fetched_at IS NULL"
        "   AND (ar.info_checked_at IS NULL OR ar.info_checked_at < ?)"
        "   AND EXISTS (SELECT 1 FROM tracks t WHERE t.artist_id = ar.id AND t.inferred = 0)"
        " ORDER BY ar.id", (UNKNOWN_ARTIST, cutoff)).fetchall()
    artists = [r["id"] for r in artist_rows
               if r["name"].strip().lower() not in _COMPILATION_ARTISTS and artist_photo(r["id"]) is None]
    return Plan(albums, artists)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _store_artist_photo(artist_id: int, data: bytes) -> None:
    image_mime(data)   # solo JPG/PNG
    target = paths.artists_dir() / f"{artist_id}.jpg"
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, target)


def _do_album(client: HttpClient, conn: sqlite3.Connection, album_id: int) -> str:
    """'cover' | 'unsure' | 'notfound'. Marca el álbum como intentado cuando la respuesta es definitiva."""
    candidates = enrich.album_candidates(client, conn, album_id, limit=4)
    outcome = "notfound"
    if candidates:
        best = candidates[0]
        if not best.confident:
            outcome = "unsure"
        else:
            data = enrich.download_cover(client, best)
            if data:
                stored = cover_store.store_downloaded(data)
                with conn:
                    conn.execute("UPDATE albums SET cover_path = ? WHERE id = ?", (str(stored), album_id))
                outcome = "cover"
    with conn:
        conn.execute("UPDATE albums SET cover_checked_at = ? WHERE id = ?", (_now(), album_id))
    return outcome


def _do_artist(client: HttpClient, conn: sqlite3.Connection, artist_id: int) -> str:
    """'info' | 'unsure' | 'notfound'."""
    name = conn.execute("SELECT name FROM artists WHERE id = ?", (artist_id,)).fetchone()["name"]
    candidates = musicbrainz.search_artists(client, name, limit=3)
    outcome = "unsure"
    if candidates and candidates[0].similarity >= 0.9 and candidates[0].mb_score >= 85:
        info = wikipedia.artist_info(client, name, candidates[0].artist_id)
        if info is None:
            outcome = "notfound"
        else:
            enrich.apply_artist_info(conn, artist_id, info)
            if info.image_url and artist_photo(artist_id) is None:
                try:
                    result = client.get_bytes(info.image_url, max_bytes=MAX_PHOTO_BYTES)
                    if result:
                        _store_artist_photo(artist_id, result[0])
                except (OnlineError, ValueError, OSError):
                    pass   # la foto es opcional
            outcome = "info"
    with conn:
        conn.execute("UPDATE artists SET info_checked_at = ? WHERE id = ?", (_now(), artist_id))
    return outcome


def run(conn: sqlite3.Connection, client: HttpClient, work: Plan, progress: ProgressCb | None = None,
        cancelled: Callable[[], bool] = lambda: False) -> dict:
    """Ejecuta el plan. Devuelve un resumen; un fallo de red aislado no detiene el proceso (5 seguidos, sí)."""
    summary = {"covers": 0, "artists": 0, "unsure": 0, "notfound": 0, "errors": 0, "done": 0,
               "total": work.total, "cancelled": False, "offline": False, "aborted": False}
    jobs = [("album", i) for i in work.albums] + [("artist", i) for i in work.artists]
    streak = 0
    for n, (kind, item_id) in enumerate(jobs, 1):
        if cancelled():
            summary["cancelled"] = True
            break
        if kind == "album":
            row = conn.execute("SELECT al.title, ar.name FROM albums al JOIN artists ar ON ar.id = al.album_artist_id"
                               " WHERE al.id = ?", (item_id,)).fetchone()
            label = f"\u00c1lbum: {row['name']} \u2014 {row['title']}" if row else "\u00c1lbum"
        else:
            row = conn.execute("SELECT name FROM artists WHERE id = ?", (item_id,)).fetchone()
            label = f"Artista: {row['name']}" if row else "Artista"
        if progress:
            progress(n - 1, len(jobs), label)
        try:
            outcome = _do_album(client, conn, item_id) if kind == "album" else _do_artist(client, conn, item_id)
        except OfflineError:
            summary["offline"] = True
            break
        except (OnlineError, ValueError, OSError, sqlite3.Error):
            summary["errors"] += 1
            streak += 1
            if streak >= MAX_CONSECUTIVE_ERRORS:
                summary["aborted"] = True
                break
            continue
        streak = 0
        summary["done"] += 1
        if outcome == "cover":
            summary["covers"] += 1
        elif outcome == "info":
            summary["artists"] += 1
        elif outcome == "unsure":
            summary["unsure"] += 1
        else:
            summary["notfound"] += 1
    if progress:
        progress(summary["done"], len(jobs), "")
    return summary
