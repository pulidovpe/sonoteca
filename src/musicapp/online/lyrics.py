"""Letras de las pistas de la biblioteca: buscar en LRCLIB, guardar en la base y traducir.

Nunca modifica archivos ni tags. Lo que ya está guardado se usa sin internet; solo se consulta la
red si la letra nunca se buscó (o si el usuario pide buscar de nuevo).
"""
from __future__ import annotations

import sqlite3

from musicapp.core import lyrics as store
from musicapp.core.models import UNKNOWN_ALBUM, UNKNOWN_ARTIST

from . import lrclib
from .http import HttpClient, OnlineError
from .translate import DeepLTranslator, normalize_lang


def _track(conn: sqlite3.Connection, track_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT t.id, t.title, t.duration, ar.name AS artist, al.title AS album"
        " FROM tracks t JOIN artists ar ON ar.id = t.artist_id JOIN albums al ON al.id = t.album_id"
        " WHERE t.id = ?", (track_id,)).fetchone()
    if row is None:
        raise OnlineError("La pista ya no está en la biblioteca")
    return row


def fetch_lyrics(client: HttpClient, conn: sqlite3.Connection, track_id: int,
                 lang: str = "", force: bool = False) -> dict:
    """Documento de letra de la pista (ver `core.lyrics.lyrics_doc`). Consulta LRCLIB solo si
    hace falta; con `force` vuelve a buscar aunque ya hubiera una letra guardada."""
    stored = store.get_stored(conn, track_id)
    if not force and not store.should_retry(stored):
        return store.lyrics_doc(conn, track_id, lang)
    track = _track(conn, track_id)
    if track["artist"] == UNKNOWN_ARTIST:
        raise OnlineError("La pista no tiene artista en sus tags: corrígelo para poder buscar su letra")
    album = "" if track["album"] == UNKNOWN_ALBUM else track["album"]
    found = lrclib.find_lyrics(client, track["artist"], track["title"], album,
                               track["duration"] or 0.0)
    if found is None:
        if not store.has_lyrics(stored):  # con "buscar de nuevo" no se pierde la letra que ya había
            store.save_not_found(conn, track_id)
    elif not (stored and store.has_lyrics(stored) and stored["original_text"] == (found.plain or None)
              and stored["synced_lrc"] == (found.synced or None)
              and bool(stored["instrumental"]) == found.instrumental):
        store.save_lyrics(conn, track_id, plain=found.plain, synced=found.synced,
                          instrumental=found.instrumental, lrclib_id=found.id or None)
    return store.lyrics_doc(conn, track_id, lang)


def translate_lyrics(translator: DeepLTranslator, conn: sqlite3.Connection, track_id: int,
                     target_lang: str, force: bool = False) -> dict:
    """Traduce la letra guardada (línea por línea, alineada con la original) y la guarda."""
    lang = normalize_lang(target_lang)
    lines = store.stored_lines(conn, track_id)
    if not lines:
        raise OnlineError("Esta pista no tiene letra para traducir: búscala primero")
    cached = store.get_translation(conn, track_id, lang)
    if cached is not None and len(cached) == len(lines) and not force:
        return store.lyrics_doc(conn, track_id, lang)
    translated, detected = translator.translate_lines([line.text for line in lines], lang)
    store.save_translation(conn, track_id, lang, translated, translator.provider)
    if detected:
        store.set_language(conn, track_id, detected)
    return store.lyrics_doc(conn, track_id, lang)
