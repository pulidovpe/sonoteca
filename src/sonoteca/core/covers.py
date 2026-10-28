"""Localización y extracción de portadas (sin dependencias de Qt)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from mutagen.id3 import ID3
from mutagen.mp4 import MP4

FOLDER_COVER_STEMS = ("cover", "folder", "front", "album", "albumart")
FOLDER_COVER_EXTS = (".jpg", ".jpeg", ".png")


def extract_embedded_cover(path: Path) -> bytes | None:
    """Bytes de la portada embebida (mp3: APIC, m4a/mp4: covr), o None."""
    try:
        ext = path.suffix.lower()
        if ext == ".mp3":
            frames = ID3(path).getall("APIC")
            if not frames:
                return None
            front = [f for f in frames if f.type == 3]  # 3 = portada frontal
            return bytes((front or frames)[0].data)
        if ext in {".m4a", ".mp4"}:
            covers = (MP4(path).tags or {}).get("covr")
            return bytes(covers[0]) if covers else None
    except Exception:  # noqa: BLE001  (archivo ilegible o sin tags: simplemente no hay portada)
        return None
    return None


def find_folder_cover(directory: Path) -> Path | None:
    """cover.jpg, folder.jpg, etc. dentro de la carpeta del álbum."""
    try:
        entries = {p.name.lower(): p for p in directory.iterdir() if p.is_file()}
    except OSError:
        return None
    for stem in FOLDER_COVER_STEMS:
        for ext in FOLDER_COVER_EXTS:
            if (stem + ext) in entries:
                return entries[stem + ext]
    return None


def album_cover_source(conn: sqlite3.Connection, album_id: int) -> tuple[str, Path] | None:
    """('embedded', archivo_de_audio) o ('folder', imagen). Orden: embebida, carpeta del álbum, descargada."""
    rows = conn.execute(
        "SELECT f.path, t.has_cover FROM tracks t JOIN files f ON f.id = t.file_id"
        " WHERE t.album_id = ? AND f.kind = 'audio'"
        " ORDER BY t.has_cover DESC, COALESCE(t.disc_no, 1), COALESCE(t.track_no, 9999) LIMIT 5",
        (album_id,),
    ).fetchall()
    if rows and rows[0]["has_cover"]:
        return "embedded", Path(rows[0]["path"])
    for row in rows:
        found = find_folder_cover(Path(row["path"]).parent)
        if found:
            return "folder", found
    # Última opción: la portada descargada automáticamente (nunca reemplaza a una que ya tengas)
    stored = conn.execute("SELECT cover_path FROM albums WHERE id = ?", (album_id,)).fetchone()
    if stored and stored["cover_path"] and Path(stored["cover_path"]).is_file():
        return "folder", Path(stored["cover_path"])
    return None


def artist_photo(artist_id: int) -> Path | None:
    """Foto descargada del artista, si existe (nueva carpeta de datos o la caché de versiones
    anteriores)."""
    from . import paths

    for folder in (paths.artists_dir(), paths.cache_dir() / "artists"):
        candidate = folder / f"{artist_id}.jpg"
        if candidate.exists():
            return candidate
    return None


def artist_cover_album(conn: sqlite3.Connection, artist_id: int) -> int | None:
    """Álbum cuya portada representa al artista: prefiere uno con portada embebida y,
    entre ellos, el más antiguo."""
    row = conn.execute(
        """
        SELECT t.album_id FROM tracks t JOIN albums al ON al.id = t.album_id
        WHERE t.artist_id = ? OR al.album_artist_id = ?
        GROUP BY t.album_id
        ORDER BY MAX(t.has_cover) DESC, MIN(COALESCE(al.year, 9999)), t.album_id
        LIMIT 1
        """,
        (artist_id, artist_id),
    ).fetchone()
    return row["album_id"] if row else None


def _cover_digest(source: tuple[str, Path]) -> str | None:
    """Huella del contenido de la portada de un álbum (None si no se puede leer)."""
    import hashlib

    kind, path = source
    try:
        data = extract_embedded_cover(path) if kind == "embedded" else path.read_bytes()
    except OSError:
        return None
    return hashlib.sha1(data).hexdigest() if data else None


MAX_ALBUMS_COMPARED = 40  # con más álbumes no se comparan las imágenes: se da por "varias"


def current_cover_state(conn: sqlite3.Connection, track_ids: list[int]) -> dict:
    """Portada que tienen hoy las pistas indicadas, para mostrarla en el editor de tags.

    Devuelve {"state": "none" | "single" | "mixed", "albumId": int}:
    - "single": todas comparten la misma portada (`albumId` es un álbum que la tiene);
    - "mixed": hay portadas distintas, o algunas pistas tienen y otras no;
    - "none": ninguna tiene portada (ni embebida ni cover.jpg en su carpeta).
    """
    ids = list(dict.fromkeys(int(i) for i in track_ids))
    if not ids:
        return {"state": "none", "albumId": 0}
    marks = ",".join("?" * len(ids))
    albums = [
        row["album_id"]
        for row in conn.execute(
            f"SELECT DISTINCT album_id FROM tracks WHERE id IN ({marks}) ORDER BY album_id", ids
        ).fetchall()
    ]
    if not albums:
        return {"state": "none", "albumId": 0}
    if len(albums) > MAX_ALBUMS_COMPARED:
        return {"state": "mixed", "albumId": 0}
    digests: dict[int, str | None] = {}
    for album_id in albums:
        source = album_cover_source(conn, album_id)
        digests[album_id] = _cover_digest(source) if source else None
    with_cover = [a for a in albums if digests[a]]
    if not with_cover:
        return {"state": "none", "albumId": 0}
    if len(with_cover) == len(albums) and len({digests[a] for a in albums}) == 1:
        return {"state": "single", "albumId": with_cover[0]}
    return {"state": "mixed", "albumId": 0}


def artist_has_image(conn: sqlite3.Connection, artist_id: int) -> bool:
    """¿Hay algo que mostrar como imagen del artista (foto descargada o portada de un álbum)?"""
    if artist_photo(artist_id) is not None:
        return True
    album_id = artist_cover_album(conn, artist_id)
    return bool(album_id and album_cover_source(conn, album_id))
