"""LRCLIB (gratuito, sin clave): letras en texto plano y sincronizadas (LRC).

Documentación: https://lrclib.net/docs. `/api/get` busca por título, artista, álbum y duración
(tolera ±2 s) y responde 404 si no hay coincidencia; `/api/search` es más lento y menos preciso,
por eso solo se usa como plan B. Las letras no se guardan en la caché HTTP sino en la base de datos.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import servers
from .http import HttpClient
from .musicbrainz import clean_title, similarity

BASE = servers.DEFAULT_LYRICS   # predeterminado; el activo sale de servers.lyrics_base()
MAX_DURATION_GAP = 4.0  # segundos: más diferencia suele ser otra versión (en vivo, remix...)
MIN_SIMILARITY = 0.8  # parecido mínimo de título y de artista en los resultados de /api/search


@dataclass(slots=True)
class LyricsResult:
    id: int
    title: str
    artist: str
    album: str
    duration: float
    instrumental: bool
    plain: str
    synced: str

    @property
    def has_text(self) -> bool:
        return bool(self.plain.strip() or self.synced.strip())


def _parse(item) -> LyricsResult | None:
    if not isinstance(item, dict):
        return None
    try:
        return LyricsResult(
            id=int(item.get("id") or 0),
            title=str(item.get("trackName") or item.get("name") or ""),
            artist=str(item.get("artistName") or ""),
            album=str(item.get("albumName") or ""),
            duration=float(item.get("duration") or 0),
            instrumental=bool(item.get("instrumental")),
            plain=str(item.get("plainLyrics") or ""),
            synced=str(item.get("syncedLyrics") or ""),
        )
    except (TypeError, ValueError):
        return None


def _usable(result: LyricsResult | None) -> bool:
    return result is not None and (result.instrumental or result.has_text)


def get_exact(client: HttpClient, artist: str, title: str, album: str = "",
              duration: float = 0.0) -> LyricsResult | None:
    """`/api/get`: coincidencia exacta por metadatos, o None si LRCLIB responde 404."""
    params: dict[str, str | int] = {"track_name": title, "artist_name": artist}
    if album:
        params["album_name"] = album
    if 1 <= duration <= 3600:
        params["duration"] = int(round(duration))
    return _parse(client.get_json(f"{servers.lyrics_base()}/get", params, cache=False))


def search(client: HttpClient, artist: str, title: str) -> list[LyricsResult]:
    """`/api/search` por título y artista (hasta 20 resultados)."""
    data = client.get_json(f"{servers.lyrics_base()}/search", {"track_name": title, "artist_name": artist},
                           cache=False)
    if not isinstance(data, list):
        return []
    return [r for r in (_parse(item) for item in data) if r is not None]


def pick_best(results: list[LyricsResult], artist: str, title: str,
              duration: float = 0.0) -> LyricsResult | None:
    """Del resultado de una búsqueda, la letra de la misma canción y de duración parecida.
    Prefiere la sincronizada y, entre ellas, la de duración más cercana."""
    ranked = []
    for r in results:
        if not _usable(r):
            continue
        if similarity(clean_title(r.title), clean_title(title)) < MIN_SIMILARITY:
            continue
        if similarity(r.artist, artist) < MIN_SIMILARITY:
            continue
        gap = abs(r.duration - duration) if duration and r.duration else 0.0
        if duration and r.duration and gap > MAX_DURATION_GAP:
            continue
        ranked.append((not r.synced.strip(), gap, r))
    if not ranked:
        return None
    ranked.sort(key=lambda item: (item[0], item[1]))
    return ranked[0][2]


def find_lyrics(client: HttpClient, artist: str, title: str, album: str = "",
                duration: float = 0.0) -> LyricsResult | None:
    """La mejor letra disponible o None. Orden: coincidencia exacta con álbum, exacta sin álbum
    (el álbum de nuestros tags suele diferir del de LRCLIB) y, por último, la búsqueda."""
    clean = clean_title(title) or title
    attempts = [(title, album)]
    if album:
        attempts.append((title, ""))
    if clean != title:
        attempts.append((clean, ""))
    for attempt_title, attempt_album in attempts:
        found = get_exact(client, artist, attempt_title, attempt_album, duration)
        if _usable(found):
            return found
    return pick_best(search(client, artist, clean), artist, clean, duration)
