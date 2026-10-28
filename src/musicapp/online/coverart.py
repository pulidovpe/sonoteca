"""Cover Art Archive (gratuito, sin clave): portadas de álbumes por su id de MusicBrainz."""
from __future__ import annotations

from musicapp.core.tag_writer import image_mime

from .http import HttpClient

BASE = "https://coverartarchive.org"
SIZES = (250, 500, 1200)  # tamaños que ofrece el servicio


def fetch_front(client: HttpClient, release_group_id: str, size: int = 500) -> bytes | None:
    """Portada frontal del grupo de lanzamientos (None si no hay). Sigue la redirección a archive.org."""
    if size not in SIZES:
        raise ValueError(f"Tamaño no disponible: {size}. Usa uno de {SIZES}")
    result = client.get_bytes(f"{BASE}/release-group/{release_group_id}/front-{size}")
    if result is None:
        return None
    data, _content_type = result
    image_mime(data)  # ValueError si el servicio no devolvió una imagen JPG/PNG
    return data


def fetch_best(client: HttpClient, release_group_id: str, sizes=(1200, 500)) -> bytes | None:
    """La imagen más grande disponible entre `sizes`."""
    for size in sizes:
        data = fetch_front(client, release_group_id, size)
        if data:
            return data
    return None
