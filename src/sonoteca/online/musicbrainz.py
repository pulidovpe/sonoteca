"""MusicBrainz (gratuito, sin clave): identificar álbumes y artistas."""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from sonoteca.core.search import normalize

from . import servers
from .http import HttpClient, OnlineError

BASE = servers.DEFAULT_MUSICBRAINZ   # predeterminado; el activo sale de servers.musicbrainz_base()
_YEAR = re.compile(r"(\d{4})")


@dataclass(slots=True)
class AlbumCandidate:
    release_group_id: str
    title: str
    artist: str
    artist_id: str | None
    year: int | None
    kind: str  # Album, Single, EP...
    mb_score: int  # 0-100, el que da MusicBrainz
    similarity: float  # 0-1, parecido de título y artista con lo que tenemos
    via: str = "album"  # "album" (por nombre de álbum) o "track" (por una canción)
    confident: bool = False  # coincidencia muy probable; solo puede serlo el primero de la lista
    length_match: bool = False  # la grabación dura lo mismo que nuestra pista (±5 s)


@dataclass(slots=True)
class ArtistCandidate:
    artist_id: str
    name: str
    mb_score: int
    similarity: float
    kind: str = ""
    country: str = ""
    begin_year: int | None = None
    disambiguation: str = ""


def phrase(text: str) -> str:
    """Texto como frase de una consulta Lucene (se escapan comillas y barras)."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _year(text) -> int | None:
    m = _YEAR.match(str(text or ""))
    return int(m.group(1)) if m else None


def _credit(credits) -> tuple[str, str | None]:
    """('Artista 1 & Artista 2', id del primero)."""
    if not credits:
        return "", None
    name = "".join(f"{c.get('name', '')}{c.get('joinphrase', '')}" for c in credits)
    first = credits[0].get("artist") or {}
    return name.strip(), first.get("id")


def _kind(rg: dict) -> str:
    """Tipo para mostrar y ordenar. Un álbum de estudio es "Album" a secas; los demás llevan su
    tipo secundario (Compilation, Soundtrack, Live, Remix...): MusicBrainz los marca así."""
    secondary = rg.get("secondary-types") or []
    if secondary:
        return secondary[0]
    return rg.get("primary-type") or ""


def _sort(items):
    return sorted(items, key=lambda c: (-c.mb_score, -c.similarity))


def _mark_confident(ordered: list[AlbumCandidate]) -> list[AlbumCandidate]:
    """Marca como "probable" solo al primero, y solo si el título es prácticamente idéntico, tiene
    buen puntaje y ningún otro empata con él (p. ej. ediciones en vivo o acústicas no cuentan).
    Aun así el usuario siempre confirma antes de aplicar."""
    if ordered:
        best = ordered[0]
        tied = len(ordered) > 1 and ordered[1].similarity >= best.similarity
        if best.mb_score >= 90 and best.similarity >= 0.95 and not tied \
                and best.kind in {"Album", "EP", "Single"}:
            best.confident = True
    return ordered


def search_albums(client: HttpClient, artist: str, album: str, limit: int = 6) -> list[AlbumCandidate]:
    """Busca el álbum por nombre y artista."""
    data = client.get_json(
        f"{servers.musicbrainz_base()}/release-group/",
        {"query": f"releasegroup:{phrase(album)} AND artist:{phrase(artist)}",
         "fmt": "json", "limit": limit}) or {}
    if not data.get("release-groups"):  # p. ej. "The X" frente a "X": palabras sueltas
        words = f"{tokens_clause('releasegroup', clean_title(album))} AND {tokens_clause('artist', artist)}"
        data = client.get_json(f"{servers.musicbrainz_base()}/release-group/",
                               {"query": words, "fmt": "json", "limit": limit}) or {}
    found = []
    for rg in data.get("release-groups", []):
        name, artist_id = _credit(rg.get("artist-credit"))
        sim = (similarity(album, rg.get("title", "")) * 0.7 + similarity(artist, name) * 0.3)
        found.append(AlbumCandidate(
            release_group_id=rg["id"], title=rg.get("title", ""), artist=name, artist_id=artist_id,
            year=_year(rg.get("first-release-date")), kind=_kind(rg),
            mb_score=int(rg.get("score", 0)), similarity=round(sim, 3)))
    return _mark_confident(_sort(found))


_KIND_ORDER = {"Album": 0, "EP": 1, "Single": 2}  # el resto (Live, Soundtrack...) va después
_ARTICLES = {"the", "el", "la", "los", "las", "a", "an"}
_TITLE_NOISE = re.compile(r"\s*[\(\[][^)\]]*[\)\]]")  # (Remastered), [Live]...
_TITLE_SUFFIX = re.compile(r"\s+-\s+(remaster\w*|live|version|.*\bmix\b|.*\bedit\b|feat\.?).*$", re.IGNORECASE)


def clean_title(title: str) -> str:
    """Quita lo que suele sobrar en un título de archivo: (Remastered), [Live], - Radio Edit..."""
    cleaned = _TITLE_SUFFIX.sub("", _TITLE_NOISE.sub("", title)).strip()
    return cleaned or title.strip()


_WORD = re.compile(r"[^\W_]+")


def _words(text: str) -> list[str]:
    """Palabras en minúsculas, sin signos y CONSERVANDO los acentos (no se sabe si el índice de
    MusicBrainz los ignora, así "José" o "Beyoncé" se buscan tal cual)."""
    return _WORD.findall(text.lower())


def tokens_clause(field: str, text: str) -> str:
    """field:(palabra AND palabra), ignorando mayúsculas, signos y un artículo inicial: así
    "The Village People" encuentra "Village People" y "Wham" encuentra "Wham!"."""
    words = _words(text)
    if len(words) > 1 and words[0] in _ARTICLES:
        words = words[1:]
    return f"{field}:({' AND '.join(words)})" if words else ""

DURATION_TOLERANCE = 5.0  # segundos: más de eso suele ser otra versión (en vivo, regrabada)


def search_by_track(client: HttpClient, artist: str, title: str, limit: int = 100,
                    duration: float | None = None, year: int | None = None) -> list[AlbumCandidate]:
    """Para pistas sin álbum: busca la canción y devuelve los álbumes donde aparece.

    Una canción suele estar en muchos lanzamientos (álbum original, recopilaciones, bandas
    sonoras, versiones en vivo o regrabadas). Para poner primero el álbum de estudio original se
    usa la duración de la pista (±5 s) y, si se conoce, el año; entre iguales gana el más antiguo.
    """
    clean = clean_title(title)
    artist_part = tokens_clause("artist", artist) or f"artist:{phrase(artist)}"
    base = f"recording:{phrase(clean)} AND {artist_part}"
    ladder = [f"{base} AND status:official AND primarytype:album",  # 1) solo álbumes oficiales
              base,                                                   # 2) sin filtros
              f"{tokens_clause('recording', clean)} AND {artist_part}"]  # 3) palabras sueltas
    params = {"fmt": "json", "limit": limit}
    data: dict = {}
    for query in ladder:
        try:
            data = client.get_json(f"{servers.musicbrainz_base()}/recording/", {**params, "query": query}) or {}
        except OnlineError:
            data = {}  # consulta no aceptada: se prueba la siguiente
        if data.get("recordings"):
            break
    found: dict[str, AlbumCandidate] = {}
    for rec in data.get("recordings", []):
        name, artist_id = _credit(rec.get("artist-credit"))
        base_sim = (similarity(title, rec.get("title", "")) * 0.5 + similarity(artist, name) * 0.5)
        length = rec.get("length")
        length_ok = bool(duration and length and abs(length / 1000 - duration) <= DURATION_TOLERANCE)
        for rel in rec.get("releases", []):
            rg = rel.get("release-group") or {}
            rg_id = rg.get("id")
            if not rg_id:
                continue
            candidate = AlbumCandidate(
                release_group_id=rg_id, title=rg.get("title") or rel.get("title", ""),
                artist=name, artist_id=artist_id, year=_year(rel.get("date")), kind=_kind(rg),
                mb_score=int(rec.get("score", 0)), similarity=round(base_sim, 3), via="track",
                length_match=length_ok)
            old = found.get(rg_id)
            if old is None:
                found[rg_id] = candidate
            else:  # mismo álbum por otra grabación o edición (p. ej. una reedición de 2024)
                years = [y for y in (old.year, candidate.year) if y]
                old.year = min(years) if years else None  # vale el año más antiguo
                old.length_match = old.length_match or candidate.length_match

    def rank(c: AlbumCandidate):
        # 1) álbum de estudio antes que EP, sencillo, en vivo, banda sonora o recopilación;
        # 2) una grabación de la misma duración; 3) el más antiguo (el original, no las reediciones);
        # 4) el más cercano al año del archivo, que no es del todo fiable (a veces es el del sencillo)
        distance = abs(c.year - year) if (year and c.year) else 50
        return (_KIND_ORDER.get(c.kind, 3), 0 if c.length_match else 1, c.year or 9999, distance,
                -c.mb_score)

    return sorted(found.values(), key=rank)


def search_artists(client: HttpClient, name: str, limit: int = 5) -> list[ArtistCandidate]:
    data = client.get_json(f"{servers.musicbrainz_base()}/artist/",
                           {"query": f"artist:{phrase(name)}", "fmt": "json", "limit": limit}) or {}
    out = []
    for a in data.get("artists", []):
        span = a.get("life-span") or {}
        out.append(ArtistCandidate(
            artist_id=a["id"], name=a.get("name", ""), mb_score=int(a.get("score", 0)),
            similarity=round(similarity(name, a.get("name", "")), 3), kind=a.get("type") or "",
            country=a.get("country") or "", begin_year=_year(span.get("begin")),
            disambiguation=a.get("disambiguation") or ""))
    return sorted(out, key=lambda c: (-c.mb_score, -c.similarity))


def artist_wikidata_id(client: HttpClient, mbid: str) -> str | None:
    """Q-id de Wikidata del artista (a partir de las relaciones de URL de MusicBrainz)."""
    data = client.get_json(f"{servers.musicbrainz_base()}/artist/{mbid}", {"inc": "url-rels", "fmt": "json"}) or {}
    for rel in data.get("relations", []):
        if rel.get("type") == "wikidata":
            resource = (rel.get("url") or {}).get("resource", "")
            qid = resource.rstrip("/").rsplit("/", 1)[-1]
            if re.fullmatch(r"Q\d+", qid):
                return qid
    return None
