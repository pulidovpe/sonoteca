"""Búsqueda en memoria: ignora acentos y mayúsculas, combina palabras de varios campos
y ordena por relevancia. Con ~2000 pistas responde en milisegundos."""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field

_JOIN_CHARS = re.compile(r"[.'\u2019`\u00b4]")  # se eliminan sin separar: "T.a.t.u." -> "tatu"
_SEPARATORS = re.compile(r"[\W_]+")  # el resto de signos separa palabras ("AC/DC" -> "ac dc")


def normalize(text: object) -> str:
    """Minúsculas, sin acentos ni signos: 'José Luis Perales' -> 'jose luis perales'."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", str(text)).casefold()
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SEPARATORS.sub(" ", _JOIN_CHARS.sub("", stripped)).strip()


def tokenize(text: object) -> list[str]:
    return normalize(text).split()


def _score(tokens: list[str], primary: str, secondary: str) -> int | None:
    """None si algún término no aparece. Más alto = más relevante."""
    haystack = f"{primary} {secondary}"
    if any(tok not in haystack for tok in tokens):
        return None
    words = primary.split()
    score = 0
    for tok in tokens:
        if any(w.startswith(tok) for w in words):
            score += 3  # inicio de palabra en el nombre/título
        elif tok in primary:
            score += 2
        else:
            score += 1  # solo aparece en el campo secundario (artista, álbum)
    phrase = " ".join(tokens)
    if primary == phrase:
        score += 20
    elif primary.startswith(phrase):
        score += 10
    return score


@dataclass(slots=True)
class SearchResults:
    artists: list[dict] = field(default_factory=list)
    albums: list[dict] = field(default_factory=list)
    tracks: list[dict] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.artists or self.albums or self.tracks)


class SearchIndex:
    def __init__(self, artists: list[dict], albums: list[dict], tracks: list[dict]) -> None:
        for row in artists:
            row["_n"] = normalize(row["name"])
        for row in albums:
            row["_n"], row["_n2"] = normalize(row["title"]), normalize(row["artist"])
        for row in tracks:
            row["_n"] = normalize(row["title"])
            row["_n2"] = normalize(f"{row['artist']} {row['album']}")
        self._artists, self._albums, self._tracks = artists, albums, tracks

    @classmethod
    def build(cls, conn: sqlite3.Connection) -> SearchIndex:
        artists = [dict(r) for r in conn.execute(
            """SELECT ar.id, ar.name, ar.sort_name,
                      (SELECT COUNT(*) FROM albums al WHERE al.album_artist_id = ar.id) AS albums,
                      (SELECT COUNT(*) FROM tracks t WHERE t.artist_id = ar.id) AS tracks
               FROM artists ar""")]
        albums = [dict(r) for r in conn.execute(
            """SELECT al.id, al.title, al.year, ar.id AS artist_id, ar.name AS artist,
                      ar.sort_name AS sort_name,
                      (SELECT COUNT(*) FROM tracks t WHERE t.album_id = al.id) AS tracks
               FROM albums al JOIN artists ar ON ar.id = al.album_artist_id""")]
        tracks = [dict(r) for r in conn.execute(
            """SELECT t.id, t.title, t.track_no, t.duration, t.year, ar.id AS artist_id,
                      ar.name AS artist, ar.sort_name AS sort_name, al.id AS album_id,
                      al.title AS album, f.path, f.kind, f.format
               FROM tracks t
               JOIN artists ar ON ar.id = t.artist_id
               JOIN albums  al ON al.id = t.album_id
               JOIN files   f  ON f.id  = t.file_id""")]
        return cls(artists, albums, tracks)

    def query(self, text: str, max_artists: int = 8, max_albums: int = 12,
              max_tracks: int = 100) -> SearchResults:
        tokens = tokenize(text)
        if not tokens:
            return SearchResults()

        def ranked(rows, n1, n2, tiebreak, limit):
            scored = []
            for row in rows:
                s = _score(tokens, row[n1], row.get(n2, ""))
                if s is not None:
                    scored.append((-s, tiebreak(row), row))
            scored.sort(key=lambda x: (x[0], x[1]))
            return [self._clean(r) for _, _, r in scored[:limit]]

        return SearchResults(
            artists=ranked(self._artists, "_n", "_n2", lambda r: normalize(r["sort_name"]),
                           max_artists),
            albums=ranked(self._albums, "_n", "_n2",
                          lambda r: (normalize(r["sort_name"]), r["year"] or 9999, r["_n"]),
                          max_albums),
            tracks=ranked(self._tracks, "_n", "_n2",
                          lambda r: (normalize(r["sort_name"]), r["_n2"], r["track_no"] or 9999,
                                     r["_n"]),
                          max_tracks),
        )

    @staticmethod
    def _clean(row: dict) -> dict:
        return {k: v for k, v in row.items() if not k.startswith("_")}
