"""Detección de archivos duplicados.

Dos pistas son duplicadas solo si COINCIDEN LAS CUATRO cosas: artista y título (sin importar mayúsculas ni tildes),
duración (en segundos redondeados), nombre de archivo (sin la carpeta) y tamaño en bytes. Es un criterio estricto a
propósito: antes de borrar nada, `file_delete.delete_duplicates` además comprueba el contenido (SHA-256).

En cada grupo, la primera pista es la que se conserva por defecto: la que tiene mejores tags (artista y álbum
reales, no deducidos del nombre), con portada, mayor bitrate y, a igualdad, la más antigua y de ruta más corta."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import PurePath

from .models import UNKNOWN_ALBUM, UNKNOWN_ARTIST
from .search import normalize


@dataclass
class Member:
    track_id: int
    file_id: int
    path: str
    size: int
    title: str
    artist: str
    album: str
    duration: float
    bitrate: int
    has_cover: bool
    inferred: bool
    mtime_ns: int

    def quality(self) -> tuple:
        return (not self.inferred, self.artist != UNKNOWN_ARTIST, self.album != UNKNOWN_ALBUM, self.has_cover,
                self.bitrate or 0, -self.mtime_ns, -len(self.path))


def find_groups(conn: sqlite3.Connection) -> list[list[Member]]:
    """Grupos de duplicados (2 o más pistas), cada uno ordenado de mejor a peor. Los grupos, por artista y título."""
    rows = conn.execute(
        "SELECT t.id, t.file_id, f.path, f.size, f.mtime_ns, t.title, t.duration, t.bitrate, t.has_cover, t.inferred,"
        "       ar.name AS artist, al.title AS album"
        " FROM tracks t JOIN files f ON f.id = t.file_id JOIN artists ar ON ar.id = t.artist_id"
        " JOIN albums al ON al.id = t.album_id").fetchall()
    buckets: dict[tuple, list[Member]] = {}
    for r in rows:
        key = (normalize(r["artist"]), normalize(r["title"]), round(r["duration"] or 0),
               PurePath(r["path"]).name.lower(), r["size"])
        buckets.setdefault(key, []).append(Member(
            r["id"], r["file_id"], r["path"], r["size"], r["title"], r["artist"], r["album"], r["duration"] or 0,
            r["bitrate"] or 0, bool(r["has_cover"]), bool(r["inferred"]), r["mtime_ns"]))
    groups = [sorted(g, key=Member.quality, reverse=True) for g in buckets.values() if len(g) > 1]
    return sorted(groups, key=lambda g: (normalize(g[0].artist), normalize(g[0].title)))
