"""Letras: lectura de archivos LRC, almacenamiento en la base y documento para la interfaz.

Sin red y sin Qt. Las letras tienen copyright: se guardan solo en la base de datos local del
usuario (uso personal) y nunca deben incluirse en el repositorio.
"""
from __future__ import annotations

import re
import sqlite3
from bisect import bisect_right
from dataclasses import dataclass
from datetime import datetime, timedelta

# [mm:ss], [mm:ss.xx], [mm:ss.xxx] o [mm:ss:xx]; admite varias marcas seguidas en una línea
_STAMP = re.compile(r"\[(\d{1,3}):(\d{2})(?:[.:](\d{1,3}))?\]")
# Marcas por palabra del LRC "enhanced": <mm:ss.xx>
_WORD_STAMP = re.compile(r"<\d{1,3}:\d{2}(?:[.:]\d{1,3})?>")

PROVIDER_LRCLIB = "LRCLIB"
NOT_FOUND_RETRY = timedelta(days=30)  # una letra "no encontrada" se reintenta pasado este tiempo


@dataclass(frozen=True)
class Line:
    time_ms: int | None  # None: letra sin sincronizar
    text: str


def _stamp_ms(minutes: str, seconds: str, fraction: str | None) -> int:
    ms = int(fraction.ljust(3, "0")[:3]) if fraction else 0  # ".5" = 500 ms, ".25" = 250 ms
    return (int(minutes) * 60 + int(seconds)) * 1000 + ms


def parse_lrc(text: str | None) -> list[Line]:
    """Líneas sincronizadas de un LRC, ordenadas por tiempo. Se ignoran las etiquetas de
    metadatos ([ar:...], [ti:...]) y las líneas sin marca de tiempo."""
    lines: list[Line] = []
    for raw in (text or "").splitlines():
        raw = raw.strip()
        stamps = list(_STAMP.finditer(raw))
        if not stamps or stamps[0].start() != 0:
            continue
        body = _WORD_STAMP.sub("", raw[stamps[-1].end():]).strip()
        for m in stamps:
            lines.append(Line(_stamp_ms(*m.groups()), body))
    lines.sort(key=lambda line: line.time_ms or 0)  # estable: conserva el orden de las empatadas
    return lines


def plain_lines(text: str | None) -> list[Line]:
    """Letra sin sincronizar: una línea por renglón (se conservan las líneas en blanco entre
    estrofas, pero no al principio ni al final)."""
    rows = [row.rstrip() for row in (text or "").replace("\r\n", "\n").split("\n")]
    while rows and not rows[0]:
        rows.pop(0)
    while rows and not rows[-1]:
        rows.pop()
    return [Line(None, row) for row in rows]


def build_lines(synced: str | None, plain: str | None) -> list[Line]:
    """Prefiere la letra sincronizada; si no hay (o no se puede leer), la de texto plano."""
    return parse_lrc(synced) or plain_lines(plain)


def line_index_at(times: list[int], position_ms: int) -> int:
    """Índice de la línea que suena en `position_ms` (-1 antes de la primera)."""
    return bisect_right(times, position_ms) - 1


# ---------------------------------------------------------------- almacenamiento

def get_stored(conn: sqlite3.Connection, track_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT track_id, language, original_text, synced_lrc, source, fetched_at,"
        " instrumental, lrclib_id FROM lyrics WHERE track_id = ?", (track_id,)).fetchone()


def has_lyrics(row: sqlite3.Row | None) -> bool:
    return bool(row and (row["original_text"] or row["synced_lrc"] or row["instrumental"]))


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def save_lyrics(conn: sqlite3.Connection, track_id: int, *, plain: str | None,
                synced: str | None, instrumental: bool = False, lrclib_id: int | None = None,
                source: str = PROVIDER_LRCLIB, language: str | None = None) -> None:
    """Guarda (o reemplaza) la letra de una pista. Las traducciones anteriores se descartan
    porque ya no corresponden al texto nuevo."""
    with conn:
        conn.execute(
            "INSERT INTO lyrics (track_id, language, original_text, synced_lrc, source,"
            " fetched_at, instrumental, lrclib_id) VALUES (?,?,?,?,?,?,?,?)"
            " ON CONFLICT(track_id) DO UPDATE SET language=excluded.language,"
            " original_text=excluded.original_text, synced_lrc=excluded.synced_lrc,"
            " source=excluded.source, fetched_at=excluded.fetched_at,"
            " instrumental=excluded.instrumental, lrclib_id=excluded.lrclib_id",
            (track_id, language, plain or None, synced or None, source, _now(),
             int(instrumental), lrclib_id))
        conn.execute("DELETE FROM translations WHERE track_id = ?", (track_id,))


def save_not_found(conn: sqlite3.Connection, track_id: int) -> None:
    """Recuerda que se buscó y no hubo letra (para no repetir la consulta a cada rato)."""
    save_lyrics(conn, track_id, plain=None, synced=None)


def should_retry(row: sqlite3.Row | None, now: datetime | None = None) -> bool:
    """¿Conviene consultar internet? Sí si nunca se buscó o si la búsqueda fallida es antigua."""
    if row is None:
        return True
    if has_lyrics(row):
        return False
    try:
        fetched = datetime.fromisoformat(row["fetched_at"])
    except (TypeError, ValueError):
        return True
    return (now or datetime.now()) - fetched >= NOT_FOUND_RETRY


def set_language(conn: sqlite3.Connection, track_id: int, language: str) -> None:
    with conn:
        conn.execute("UPDATE lyrics SET language = ? WHERE track_id = ?", (language, track_id))


def get_translation(conn: sqlite3.Connection, track_id: int, lang: str) -> list[str] | None:
    """Traducción alineada línea por línea con `build_lines` de la letra guardada."""
    row = conn.execute("SELECT text FROM translations WHERE track_id = ? AND target_lang = ?",
                       (track_id, lang.upper())).fetchone()
    return row["text"].split("\n") if row else None


def save_translation(conn: sqlite3.Connection, track_id: int, lang: str, lines: list[str],
                     provider: str) -> None:
    with conn:
        conn.execute(
            "INSERT INTO translations (track_id, target_lang, text, provider) VALUES (?,?,?,?)"
            " ON CONFLICT(track_id, target_lang) DO UPDATE SET text=excluded.text,"
            " provider=excluded.provider",
            (track_id, lang.upper(), "\n".join(lines), provider))


def stored_lines(conn: sqlite3.Connection, track_id: int) -> list[Line]:
    row = get_stored(conn, track_id)
    return build_lines(row["synced_lrc"], row["original_text"]) if row else []


def lyrics_doc(conn: sqlite3.Connection, track_id: int, lang: str = "") -> dict:
    """Todo lo que la interfaz necesita de la letra de una pista, sin consultar internet.

    {"stored": bool, "found": bool, "instrumental": bool, "synced": bool, "source", "language",
     "fetchedAt", "retry": bool, "translationLang", "hasTranslation": bool,
     "lines": [{"t": ms o -1, "text": str, "tr": str}]}
    """
    row = get_stored(conn, track_id)
    doc: dict = {
        "trackId": track_id, "stored": row is not None, "found": has_lyrics(row),
        "instrumental": bool(row and row["instrumental"]), "synced": False,
        "source": (row["source"] if row else "") or "", "language": (row["language"] if row else "") or "",
        "fetchedAt": (row["fetched_at"] if row else "") or "", "retry": should_retry(row),
        "translationLang": lang.upper(), "hasTranslation": False, "lines": [],
    }
    if not row or not has_lyrics(row):
        return doc
    lines = build_lines(row["synced_lrc"], row["original_text"])
    doc["synced"] = bool(lines) and lines[0].time_ms is not None
    translated = get_translation(conn, track_id, lang) if lang else None
    if translated is not None and len(translated) != len(lines):
        translated = None  # desalineada (no debería pasar): se ignora en vez de mostrar mal
    doc["hasTranslation"] = translated is not None
    doc["lines"] = [
        {"t": -1 if line.time_ms is None else line.time_ms, "text": line.text,
         "tr": translated[i] if translated else ""}
        for i, line in enumerate(lines)
    ]
    return doc
