"""Wikipedia y Wikidata (gratuitos, sin clave): resumen e imagen de un artista.

Los textos de Wikipedia son CC BY-SA: siempre se guarda y muestra el enlace a la fuente.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from . import musicbrainz
from . import servers
from .http import HttpClient

MUSIC_WORDS = (
    "cantante", "banda", "música", "musical", "músico", "musico", "compositor", "dúo", "duo",
    "grupo", "rapero", "raper", "intérprete", "interprete", "orquesta", "cantautor",
    "singer", "band", "musician", "rapper", "songwriter", "composer", "vocalist", "group",
)


@dataclass(slots=True)
class ArtistInfo:
    name: str
    summary: str
    url: str
    language: str
    description: str = ""
    image_url: str = ""
    wikidata_id: str = ""
    mbid: str = ""


def _is_musical(description: str, extract: str) -> bool:
    text = f"{description} {extract[:300]}".lower()
    return any(word in text for word in MUSIC_WORDS)


def _summary(client: HttpClient, lang: str, title: str, mbid: str = "", qid: str = "",
             require_music: bool = False) -> ArtistInfo | None:
    url = f"{servers.wikipedia_base(lang)}/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}"
    data = client.get_json(url)
    if not data or data.get("type") == "disambiguation" or not data.get("extract"):
        return None
    description = data.get("description") or ""
    if require_music and not _is_musical(description, data["extract"]):
        return None
    image = (data.get("thumbnail") or data.get("originalimage") or {}).get("source", "")
    page = ((data.get("content_urls") or {}).get("desktop") or {}).get("page") or (
        f"{servers.wikipedia_base(lang)}/wiki/{quote(title.replace(' ', '_'))}")
    return ArtistInfo(name=data.get("title", title), summary=data["extract"].strip(), url=page,
                      language=lang, description=description, image_url=image,
                      wikidata_id=qid, mbid=mbid)


def sitelink_titles(client: HttpClient, qid: str, languages: tuple[str, ...]) -> dict[str, str]:
    """Título del artículo de Wikipedia en cada idioma, según Wikidata."""
    sites = "|".join(f"{lang}wiki" for lang in languages)
    data = client.get_json("https://www.wikidata.org/w/api.php", {
        "action": "wbgetentities", "ids": qid, "props": "sitelinks", "sitefilter": sites,
        "format": "json"}) or {}
    links = ((data.get("entities") or {}).get(qid) or {}).get("sitelinks") or {}
    return {lang: links[f"{lang}wiki"]["title"] for lang in languages if f"{lang}wiki" in links}


def search_title(client: HttpClient, lang: str, name: str) -> ArtistInfo | None:
    """Plan B sin Wikidata: busca en Wikipedia y acepta solo un artículo que parezca musical."""
    data = client.get_json(f"{servers.wikipedia_base(lang)}/w/api.php", {
        "action": "query", "list": "search", "srsearch": name, "srlimit": 3, "format": "json"}) or {}
    for hit in (data.get("query") or {}).get("search", []):
        info = _summary(client, lang, hit.get("title", ""), require_music=True)
        if info and musicbrainz.similarity(name, info.name.split(" (")[0]) >= 0.8:
            return info
    return None


def search_candidates(client: HttpClient, name: str, languages: tuple[str, ...] = ("es", "en"),
                      per_language: int = 4) -> list[ArtistInfo]:
    """Artículos de Wikipedia que podrían ser el artista (para que el usuario elija el correcto).
    Los que parecen de música van primero; no se descarta ninguno."""
    found: list[ArtistInfo] = []
    seen: set[str] = set()
    for lang in languages:
        data = client.get_json(f"{servers.wikipedia_base(lang)}/w/api.php", {
            "action": "query", "list": "search", "srsearch": name, "srlimit": per_language,
            "format": "json"}) or {}
        for hit in (data.get("query") or {}).get("search", []):
            info = _summary(client, lang, hit.get("title", ""))
            if info and info.url not in seen:
                seen.add(info.url)
                found.append(info)
    found.sort(key=lambda i: not _is_musical(i.description, i.summary))  # estable
    return found


def artist_info(client: HttpClient, name: str, mbid: str = "",
                languages: tuple[str, ...] = ("es", "en")) -> ArtistInfo | None:
    """Resumen del artista. Con `mbid` se llega por Wikidata (muy fiable); si no, por búsqueda."""
    if mbid:
        qid = musicbrainz.artist_wikidata_id(client, mbid)
        if qid:
            titles = sitelink_titles(client, qid, languages)
            for lang in languages:
                if lang in titles:
                    info = _summary(client, lang, titles[lang], mbid=mbid, qid=qid)
                    if info:
                        return info
    for lang in languages:
        info = search_title(client, lang, name)
        if info:
            info.mbid = mbid
            return info
    return None
