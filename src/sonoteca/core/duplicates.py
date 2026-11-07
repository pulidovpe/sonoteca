"""Detección de archivos duplicados, de dos clases:

· **Idénticos** (`find_groups`): ver abajo. Se pueden eliminar con una verificación byte a byte.
· **Misma canción en otro bitrate o formato** (`find_similar_groups`): mismo artista y título (sin distinguir tildes ni
  mayúsculas) y duración casi igual (±2 s), pero archivos distintos (p. ej. un MP3 a 128 kbps y otro a 320 kbps, o un M4A).
  No se puede verificar el contenido, así que se listan aparte y la eliminación comprueba artista, título y duración al
  momento de borrar (`file_delete.delete_duplicates(mode="similar")`). Por defecto se conserva la de mayor bitrate.

Dos pistas son duplicadas si sus archivos son IDÉNTICOS byte a byte (mismo tamaño y mismo SHA-256), aunque tengan
otro nombre de archivo, otra carpeta o tags distintos (p. ej. «Canción.mp3» y «Canción (1).mp3», o una copia con los tags
sin corregir). Para no leer toda la biblioteca solo se calcula el SHA-256 de los archivos que comparten tamaño.
Esa es la misma prueba que `file_delete.delete_duplicates` repite antes de mover nada a la papelera, así que todo lo que se
lista se puede eliminar con seguridad. (Antes se exigía además mismo nombre de archivo, artista, título y duración: se
escapaban las copias renombradas.)

En cada grupo, la primera pista es la que se conserva por defecto: la que tiene mejores tags (artista y álbum
reales, no deducidos del nombre), con portada, mayor bitrate y, a igualdad, la más antigua y de ruta más corta."""
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from .file_delete import SIMILAR_DURATION_TOLERANCE, _sha256
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

    def audio_quality(self) -> tuple:
        """Para elegir qué copia conservar entre versiones distintas de la misma canción: primero el bitrate."""
        return (self.bitrate or 0, not self.inferred, self.artist != UNKNOWN_ARTIST, self.album != UNKNOWN_ALBUM,
                self.has_cover, self.size or 0, -self.mtime_ns, -len(self.path))


_SELECT = (
    "SELECT t.id, t.file_id, f.path, f.size, f.mtime_ns, t.title, t.duration, t.bitrate, t.has_cover, t.inferred,"
    "       ar.name AS artist, al.title AS album"
    " FROM tracks t JOIN files f ON f.id = t.file_id JOIN artists ar ON ar.id = t.artist_id"
    " JOIN albums al ON al.id = t.album_id")


def _member(r) -> Member:
    return Member(r["id"], r["file_id"], r["path"], r["size"], r["title"], r["artist"], r["album"], r["duration"] or 0,
                  r["bitrate"] or 0, bool(r["has_cover"]), bool(r["inferred"]), r["mtime_ns"])


def _same_content(members: list[Member]) -> bool:
    """True si todos los archivos son idénticos (ya salen en la lista de idénticos)."""
    if len({m.size for m in members}) != 1:
        return False
    try:
        return len({_sha256(m.path) for m in members}) == 1
    except OSError:
        return False


def find_similar_groups(conn: sqlite3.Connection) -> list[list[Member]]:
    """Grupos de la misma canción en archivos distintos (otro bitrate o formato), cada uno de mejor a peor copia por
    bitrate. Se excluyen las pistas sin artista conocido, sin título o sin duración (demasiado ambiguas) y los archivos que
    ya no existen; un grupo cuyos archivos son todos idénticos no se repite aquí (sale en la lista de idénticos)."""
    buckets: dict[tuple[str, str], list] = {}
    for r in conn.execute(_SELECT).fetchall():
        if not r["duration"] or r["duration"] <= 0 or r["artist"] == UNKNOWN_ARTIST:
            continue
        key = (normalize(r["artist"]), normalize(r["title"]))
        if key[1]:
            buckets.setdefault(key, []).append(r)
    groups: list[list[Member]] = []

    def close(cluster: list) -> None:
        members = [_member(r) for r in cluster if os.path.exists(r["path"])]
        if len(members) >= 2 and not _same_content(members):
            groups.append(sorted(members, key=Member.audio_quality, reverse=True))

    for rows in buckets.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda r: r["duration"])
        cluster = [rows[0]]
        for r in rows[1:]:
            if r["duration"] - cluster[0]["duration"] <= SIMILAR_DURATION_TOLERANCE:
                cluster.append(r)
            else:
                close(cluster)
                cluster = [r]
        close(cluster)
    return sorted(groups, key=lambda g: (normalize(g[0].artist), normalize(g[0].title)))


def find_groups(conn: sqlite3.Connection) -> list[list[Member]]:
    """Grupos de duplicados (2 o más pistas con archivos idénticos), cada uno ordenado de mejor a peor copia.
    Los grupos, por artista y título de su mejor copia. Los archivos que ya no existen en el disco no se pueden verificar y
    no se incluyen."""
    rows = conn.execute(_SELECT).fetchall()
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
            by_digest.setdefault(digest, []).append(_member(r))
        groups.extend(sorted(g, key=Member.quality, reverse=True) for g in by_digest.values() if len(g) > 1)
    return sorted(groups, key=lambda g: (normalize(g[0].artist), normalize(g[0].title)))
