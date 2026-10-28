"""Lectura de tags. Una sola interfaz (`read_tags`) para mp3 (ID3) y mp4/m4a (atoms).

La escritura de tags se implementará en la Fase 4 sobre esta misma capa.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from mutagen.mp3 import MP3
from mutagen.mp4 import MP4

from .models import SUPPORTED_EXTENSIONS, UNKNOWN_ALBUM, UNKNOWN_ARTIST, VIDEO_EXTENSIONS, TrackMeta
from .search import normalize

_YEAR_RE = re.compile(r"(\d{4})")
_LEADING_INT_RE = re.compile(r"\s*(\d+)")


class TagReadError(Exception):
    """El archivo no se pudo leer (corrupto, formato no soportado, etc.)."""


def supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def parse_year(value: object) -> int | None:
    """Extrae un año de '2019', '2019-05-03', '2019-05-03T00:00:00Z', etc."""
    if value is None:
        return None
    m = _YEAR_RE.search(str(value))
    if not m:
        return None
    year = int(m.group(1))
    return year if 1000 <= year <= 2999 else None


def parse_pair(value: object) -> int | None:
    """Primer número de '3/12' o '3'. None si no es válido o es 0."""
    if value is None:
        return None
    m = _LEADING_INT_RE.match(str(value))
    if not m:
        return None
    return int(m.group(1)) or None


_YEAR_PREFIX = re.compile(r"^(1[89]\d{2}|20\d{2})\s*-\s*(\S.*)$")  # "1991-Artista - Título"
_TRACK_PREFIX = re.compile(r"^(\d{1,3})\s*[-._)]\s*(\S.*)$")  # "03- Artista - Título", "03. Título"
_TRACK_ONLY = re.compile(r"^\d{1,3}$")
_SEPARATOR = re.compile(r"\s+-\s+")  # exige espacios: no parte "Eagle-Eye Cherry"


@dataclass(slots=True)
class FilenameInfo:
    """Lo que se puede deducir del nombre de un archivo sin tags."""

    title: str
    artist: str | None = None
    album: str | None = None
    track_no: int | None = None
    year: int | None = None


def parse_filename(stem: str) -> FilenameInfo:
    """Separa año, nº de pista, artista, álbum y título de un nombre de archivo.

    "03- Ace Of Base - Happy Nation"   -> pista 3, artista "Ace Of Base", título "Happy Nation"
    "1991-Spin Doctors - Two Princes"  -> año 1991, artista, título
    "Artista - Álbum - 03 - Título"    -> artista, álbum, pista 3, título
    "01 - Título" / "03. Título"       -> pista y título (sin artista)
    "99 Luftballons"                   -> título (no se confunde con un nº de pista)
    """
    text = stem.strip()
    year = track = None
    if m := _YEAR_PREFIX.match(text):
        year, text = int(m.group(1)), m.group(2)
    elif m := _TRACK_PREFIX.match(text):
        track, text = int(m.group(1)) or None, m.group(2)

    parts = [p.strip() for p in _SEPARATOR.split(text) if p.strip()]
    numeric_segment = False
    rest = []
    for part in parts:
        if track is None and len(parts) > 1 and _TRACK_ONLY.match(part):
            track, numeric_segment = int(part) or None, True
        else:
            rest.append(part)

    if not rest:
        return FilenameInfo(title=stem.strip(), track_no=track, year=year)
    if len(rest) == 1:
        return FilenameInfo(title=rest[0], track_no=track, year=year)
    if len(rest) == 2:
        return FilenameInfo(title=rest[1], artist=rest[0], track_no=track, year=year)
    # 3 o más partes: un nº de pista suelto indica el estilo "Artista - Álbum - NN - Título"
    if numeric_segment:
        return FilenameInfo(title=rest[-1], artist=rest[0], album=" - ".join(rest[1:-1]),
                            track_no=track, year=year)
    return FilenameInfo(title=" - ".join(rest[1:]), artist=rest[0], track_no=track, year=year)


def _title_and_artist_from_name(info: FilenameInfo, tag_artist: str | None):
    """(título, artista deducido). Contempla nombres "Título - Artista" cuando el tag de
    artista coincide con la segunda parte."""
    if (tag_artist and info.artist and normalize(info.artist) != normalize(tag_artist)
            and normalize(info.title) == normalize(tag_artist)):
        return info.artist, None
    return info.title, (None if tag_artist else info.artist)


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\x00", "").strip()
    return text or None


def _first(frame) -> str | None:
    """Primer texto de un frame ID3 (TextFrame.text es una lista)."""
    texts = getattr(frame, "text", None) if frame is not None else None
    return _clean(texts[0]) if texts else None


def read_tags(path: Path) -> TrackMeta:
    ext = path.suffix.lower()
    try:
        if ext == ".mp3":
            return _read_mp3(path)
        if ext in {".m4a", ".mp4"}:
            return _read_mp4(path)
    except Exception as exc:  # mutagen lanza muchas excepciones distintas
        raise TagReadError(f"{type(exc).__name__}: {exc}") from exc
    raise TagReadError(f"Extensión no soportada: {ext}")


def _build(path: Path, fmt: str, *, duration, bitrate, has_cover=False, title=None, artist=None,
           album_artist=None, album=None, year=None, track_no=None, disc_no=None,
           genre=None) -> TrackMeta:
    # Sin título en los tags, el nombre del archivo es la fuente para los campos que falten
    # (antes solo se usaba si faltaban título Y artista, y al añadir un artista el título pasaba
    # a ser el nombre completo del archivo). Con título, solo se confirma el artista.
    inferred = False
    info = parse_filename(path.stem)
    if title is None:
        title, guessed_artist = _title_and_artist_from_name(info, artist)
        inferred = title != path.stem
        if artist is None and guessed_artist:
            artist, inferred = guessed_artist, True
        if track_no is None and info.track_no:
            track_no, inferred = info.track_no, True
        if year is None and info.year:
            year, inferred = info.year, True
        if album is None and info.album:
            album, inferred = info.album, True
    elif artist is None and info.artist and normalize(info.title) == normalize(title):
        artist, inferred = info.artist, True
    artist = artist or UNKNOWN_ARTIST
    return TrackMeta(
        path=path,
        format=fmt,
        kind="video" if path.suffix.lower() in VIDEO_EXTENSIONS else "audio",
        title=title or path.stem,
        artist=artist,
        album_artist=album_artist or artist,
        album=album or UNKNOWN_ALBUM,
        year=year,
        track_no=track_no,
        disc_no=disc_no,
        genre=genre,
        duration=float(duration or 0.0),
        bitrate=int(bitrate) if bitrate else None,
        has_cover=has_cover,
        inferred=inferred,
    )


def _read_mp3(path: Path) -> TrackMeta:
    audio = MP3(path)  # lanza HeaderNotFoundError si no hay frames MPEG válidos
    tags = audio.tags  # ID3 o None
    if tags is None:
        return _build(path, "mp3", duration=audio.info.length, bitrate=audio.info.bitrate)
    # mutagen sube en memoria a ID3v2.4: TYER/TDAT -> TDRC. Se consulta TYER/TORY por si acaso.
    year = parse_year(_first(tags.get("TDRC")) or _first(tags.get("TYER")) or _first(tags.get("TORY")))
    return _build(
        path, "mp3",
        duration=audio.info.length,
        bitrate=audio.info.bitrate,
        has_cover=bool(tags.getall("APIC")),
        title=_first(tags.get("TIT2")),
        artist=_first(tags.get("TPE1")),
        album_artist=_first(tags.get("TPE2")),
        album=_first(tags.get("TALB")),
        year=year,
        track_no=parse_pair(_first(tags.get("TRCK"))),
        disc_no=parse_pair(_first(tags.get("TPOS"))),
        genre=_first(tags.get("TCON")),
    )


def _mp4_text(tags, key: str) -> str | None:
    values = tags.get(key)
    return _clean(values[0]) if values else None


def _mp4_number(tags, key: str) -> int | None:
    """trkn/disk vienen como [(n, total)]."""
    values = tags.get(key)
    if not values:
        return None
    first = values[0]
    num = first[0] if isinstance(first, tuple) else first
    try:
        return int(num) or None
    except (TypeError, ValueError):
        return None


def _read_mp4(path: Path) -> TrackMeta:
    audio = MP4(path)
    tags = audio.tags or {}
    return _build(
        path, path.suffix.lower().lstrip("."),
        duration=audio.info.length,
        bitrate=getattr(audio.info, "bitrate", None),
        has_cover=bool(tags.get("covr")),
        title=_mp4_text(tags, "\xa9nam"),
        artist=_mp4_text(tags, "\xa9ART"),
        album_artist=_mp4_text(tags, "aART"),
        album=_mp4_text(tags, "\xa9alb"),
        year=parse_year(_mp4_text(tags, "\xa9day")),
        track_no=_mp4_number(tags, "trkn"),
        disc_no=_mp4_number(tags, "disk"),
        genre=_mp4_text(tags, "\xa9gen"),
    )
