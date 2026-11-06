"""Detección de archivos duplicados.

Dos pistas son duplicadas si sus archivos son IDÉNTICOS byte a byte (mismo tamaño y mismo SHA-256), aunque tengan
otro nombre de archivo, otra carpeta o tags distintos (p. ej. «Canción.mp3» y «Canción (1).mp3», o una copia con los tags
sin corregir). Para no leer toda la biblioteca solo se calcula el SHA-256 de los archivos que comparten tamaño.
Esa es la misma prueba que `file_delete.delete_duplicates` repite antes de mover nada a la papelera, así que todo lo que se
lista se puede eliminar con seguridad. (Antes se exigía además mismo nombre de archivo, artista, título y duración: se
escapaban las copias renombradas.)

En cada grupo, la primera pista es la que se conserva por defecto: la que tiene mejores tags (artista y álbum
reales, no deducidos del nombre), con portada, mayor bitrate y, a igualdad, la más antigua y de ruta más corta."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .file_delete import _sha256
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
    """Grupos de duplicados (2 o más pistas con archivos idénticos), cada uno ordenado de mejor a peor copia.
    Los grupos, por artista y título de su mejor copia. Los archivos que ya no existen en el disco no se pueden verificar y
    no se incluyen."""
    rows = conn.execute(
        "SELECT t.id, t.file_id, f.path, f.size, f.mtime_ns, t.title, t.duration, t.bitrate, t.has_cover, t.inferred,"
        "       ar.name AS artist, al.title AS album"
        " FROM tracks t JOIN files f ON f.id = t.file_id JOIN artists ar ON ar.id = t.artist_id"
        " JOIN albums al ON al.id = t.album_id").fetchall()
    by_size: dict[int, list] = {}
    for r in rows:
        if r["size"]:
            by_size.setdefault(r["size"], []).append(r)
    groups: list[list[Member]] = []
    for same_size in by_size.values():
        if len(same_size) < 2:
            continue                                   # un tamaño único no puede estar duplicado: no se lee el archivo
        by_digest: dict[str, list[Member]] = {}
        for r in same_size:
            try:
                digest = _sha256(r["path"])
            except OSError:
                continue
            by_digest.setdefault(digest, []).append(Member(
                r["id"], r["file_id"], r["path"], r["size"], r["title"], r["artist"], r["album"], r["duration"] or 0,
                r["bitrate"] or 0, bool(r["has_cover"]), bool(r["inferred"]), r["mtime_ns"]))
        groups.extend(sorted(g, key=Member.quality, reverse=True) for g in by_digest.values() if len(g) > 1)
    return sorted(groups, key=lambda g: (normalize(g[0].artist), normalize(g[0].title)))
