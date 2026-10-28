"""Modelos de datos simples, independientes de la base de datos y de la UI."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

UNKNOWN_ARTIST = "Artista desconocido"
UNKNOWN_ALBUM = "Álbum desconocido"

AUDIO_EXTENSIONS = {".mp3", ".m4a"}
VIDEO_EXTENSIONS = {".mp4"}
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


@dataclass(slots=True)
class TrackMeta:
    """Metadatos normalizados de un archivo, sin importar el formato de origen."""

    path: Path
    format: str  # "mp3" | "m4a" | "mp4"
    kind: str  # "audio" | "video"
    title: str
    artist: str
    album_artist: str
    album: str
    year: int | None = None
    track_no: int | None = None
    disc_no: int | None = None
    genre: str | None = None
    duration: float = 0.0  # segundos
    bitrate: int | None = None  # bps
    has_cover: bool = False
    inferred: bool = False  # artista/título/año deducidos del nombre de archivo


@dataclass(slots=True)
class ScanResult:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    errors: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def total_seen(self) -> int:
        return self.added + self.updated + self.unchanged
