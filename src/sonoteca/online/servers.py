"""Servidores alternativos para letras y para portadas/información.

La app usa por defecto servicios públicos y gratuitos (LRCLIB; MusicBrainz + Cover Art Archive + Wikipedia). El
usuario puede añadir los suyos y elegir cuál usar EN LUGAR del predeterminado. Un servidor alternativo debe hablar
el mismo protocolo que el servicio al que sustituye, por ejemplo una instancia propia o un espejo:

  letras         API compatible con LRCLIB (https://lrclib.net/docs), p. ej. `https://mi-servidor/api`
  portadas/info  cualquiera de estos tres; los que se dejen vacíos siguen usando el servicio por defecto
                 · MusicBrainz  (API web v2, p. ej. `https://mi-espejo/ws/2`)
                 · Cover Art Archive (p. ej. `https://mi-espejo-caa`)
                 · Wikipedia/MediaWiki (p. ej. `https://{lang}.wikipedia.org`; `{lang}` = idioma de la ficha)

Las direcciones se guardan en settings.json y no pueden llevar usuario ni contraseña.
"""
from __future__ import annotations

import uuid
from urllib.parse import urlsplit

from . import settings as online_settings
from .http import HttpClient, OnlineError

DEFAULT_LYRICS = "https://lrclib.net/api"
DEFAULT_MUSICBRAINZ = "https://musicbrainz.org/ws/2"
DEFAULT_COVERART = "https://coverartarchive.org"
DEFAULT_WIKIPEDIA = "https://{lang}.wikipedia.org"
DEFAULT_ID = "default"
MAX_NAME = 40


def normalize_url(url: str, template: bool = False) -> str:
    """Valida una dirección http(s) y le quita la barra final. `template` permite `{lang}` en el host."""
    value = (url or "").strip().rstrip("/")
    probe = value.replace("{lang}", "es") if template else value
    if "{" in probe or "}" in probe:
        raise ValueError("La direcci\u00f3n contiene llaves no v\u00e1lidas" + (" (solo se admite {lang})." if template else "."))
    parts = urlsplit(probe)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("La direcci\u00f3n debe empezar por http:// o https:// e incluir el servidor.")
    if parts.username or parts.password:
        raise ValueError("La direcci\u00f3n no puede incluir usuario ni contrase\u00f1a.")
    if parts.query or parts.fragment:
        raise ValueError("La direcci\u00f3n no debe llevar \u00ab?\u00bb ni \u00ab#\u00bb: es la ra\u00edz de la API.")
    return value


def _clean_name(name: str) -> str:
    name = " ".join((name or "").split())
    if not name:
        raise ValueError("Escribe un nombre para el servidor.")
    if len(name) > MAX_NAME:
        raise ValueError(f"El nombre no puede pasar de {MAX_NAME} caracteres.")
    return name


def _find(items: list, server_id: str) -> dict | None:
    return next((x for x in items if x.get("id") == server_id), None)


# ---- resoluci\u00f3n: lo usan lrclib, musicbrainz, coverart y wikipedia en cada consulta ----
def lyrics_base(settings: online_settings.Settings | None = None) -> str:
    s = settings or online_settings.load()
    item = _find(s.lyrics_servers, s.lyrics_active)
    return item["url"] if item else DEFAULT_LYRICS


def lyrics_name(settings: online_settings.Settings | None = None) -> str:
    s = settings or online_settings.load()
    item = _find(s.lyrics_servers, s.lyrics_active)
    return item["name"] if item else "LRCLIB"


def _meta(key: str, default: str, settings) -> str:
    s = settings or online_settings.load()
    item = _find(s.meta_servers, s.meta_active)
    return (item.get(key) or default) if item else default


def musicbrainz_base(settings=None) -> str:
    return _meta("musicbrainz", DEFAULT_MUSICBRAINZ, settings)


def coverart_base(settings=None) -> str:
    return _meta("coverart", DEFAULT_COVERART, settings)


def wikipedia_base(lang: str, settings=None) -> str:
    return _meta("wikipedia", DEFAULT_WIKIPEDIA, settings).replace("{lang}", lang)


# ---- edici\u00f3n (la usa la interfaz) ----
def add_lyrics_server(s: online_settings.Settings, name: str, url: str) -> dict:
    item = {"id": uuid.uuid4().hex[:8], "name": _clean_name(name), "url": normalize_url(url)}
    s.lyrics_servers.append(item)
    return item


def add_meta_server(s: online_settings.Settings, name: str, musicbrainz: str = "", coverart: str = "",
                    wikipedia: str = "") -> dict:
    if not (musicbrainz.strip() or coverart.strip() or wikipedia.strip()):
        raise ValueError("Indica al menos una direcci\u00f3n (MusicBrainz, Cover Art o Wikipedia).")
    item = {
        "id": uuid.uuid4().hex[:8], "name": _clean_name(name),
        "musicbrainz": normalize_url(musicbrainz) if musicbrainz.strip() else "",
        "coverart": normalize_url(coverart) if coverart.strip() else "",
        "wikipedia": normalize_url(wikipedia, template=True) if wikipedia.strip() else "",
    }
    s.meta_servers.append(item)
    return item


def remove_server(s: online_settings.Settings, kind: str, server_id: str) -> None:
    """kind: 'lyrics' | 'meta'. Si se borra el activo, se vuelve al predeterminado."""
    if kind == "lyrics":
        s.lyrics_servers = [x for x in s.lyrics_servers if x.get("id") != server_id]
        if s.lyrics_active == server_id:
            s.lyrics_active = DEFAULT_ID
    else:
        s.meta_servers = [x for x in s.meta_servers if x.get("id") != server_id]
        if s.meta_active == server_id:
            s.meta_active = DEFAULT_ID


def set_active(s: online_settings.Settings, kind: str, server_id: str) -> None:
    items = s.lyrics_servers if kind == "lyrics" else s.meta_servers
    if server_id != DEFAULT_ID and _find(items, server_id) is None:
        raise ValueError("Ese servidor ya no existe.")
    if kind == "lyrics":
        s.lyrics_active = server_id
    else:
        s.meta_active = server_id


def state(s: online_settings.Settings) -> dict:
    """Para la interfaz: servidores de cada tipo (el predeterminado primero) y cu\u00e1l est\u00e1 activo."""
    lyrics = [{"id": DEFAULT_ID, "name": "LRCLIB (predeterminado)", "url": DEFAULT_LYRICS, "builtin": True}]
    lyrics += [{**x, "builtin": False} for x in s.lyrics_servers]
    meta = [{"id": DEFAULT_ID, "name": "MusicBrainz + Cover Art Archive + Wikipedia (predeterminado)",
             "url": DEFAULT_MUSICBRAINZ, "builtin": True}]
    for x in s.meta_servers:
        shown = " \u00b7 ".join(v for v in (x.get("musicbrainz"), x.get("coverart"), x.get("wikipedia")) if v)
        meta.append({**x, "url": shown, "builtin": False})
    return {"lyrics": lyrics, "lyricsActive": s.lyrics_active if _find(s.lyrics_servers, s.lyrics_active) else DEFAULT_ID,
            "meta": meta, "metaActive": s.meta_active if _find(s.meta_servers, s.meta_active) else DEFAULT_ID}


# ---- pruebas de conexi\u00f3n (sin cach\u00e9) ----
def test_lyrics(client: HttpClient, url: str) -> tuple[bool, str]:
    try:
        base = normalize_url(url)
        data = client.get_json(f"{base}/search", {"q": "test"}, cache=False)
    except ValueError as exc:
        return False, str(exc)
    except OnlineError as exc:
        return False, str(exc)
    if isinstance(data, list):
        return True, f"Responde como LRCLIB ({len(data)} resultados de prueba)."
    return False, "Respondi\u00f3, pero no con el formato de LRCLIB (se esperaba una lista en /search)."


def test_meta(client: HttpClient, musicbrainz: str = "", wikipedia: str = "") -> tuple[bool, str]:
    notes = []
    try:
        if musicbrainz.strip():
            base = normalize_url(musicbrainz)
            data = client.get_json(f"{base}/artist/", {"query": "artist:test", "limit": 1, "fmt": "json"}, cache=False)
            if not (isinstance(data, dict) and "artists" in data):
                return False, "MusicBrainz: respondi\u00f3, pero no con el formato esperado (falta \u00abartists\u00bb)."
            notes.append("MusicBrainz responde")
        if wikipedia.strip():
            base = normalize_url(wikipedia, template=True).replace("{lang}", "es")
            data = client.get_json(f"{base}/api/rest_v1/page/summary/Musica", cache=False)
            if not (isinstance(data, dict) and "extract" in data):
                return False, "Wikipedia: respondi\u00f3, pero no con el formato esperado (falta \u00abextract\u00bb)."
            notes.append("Wikipedia responde")
    except (ValueError, OnlineError) as exc:
        return False, str(exc)
    if not notes:
        return True, "Direcci\u00f3n v\u00e1lida (Cover Art Archive no se puede probar sin conocer un identificador)."
    return True, "; ".join(notes) + "."
