"""Puente entre la base SQLite y QML. Solo lectura en la Fase 2."""
from __future__ import annotations

import sys
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QFile, QObject, QUrl, Signal, Slot

from sonoteca import CONTACT_EMAIL, COPYRIGHT, LICENSE_NAME, REPO_URL, __version__
from sonoteca.core import (cleanup, covers, duplicates, file_delete, library, library_folders, paths, pending_tags,
                           review, scanner, stats, tag_edit)
from sonoteca.core.db import connect, default_db_path
from sonoteca.core.models import UNKNOWN_ALBUM, UNKNOWN_ARTIST
from sonoteca.core.search import SearchIndex, normalize


def album_display(title: str) -> str:
    return "Sin álbum" if title == UNKNOWN_ALBUM else title


def _badge(fmt: str) -> str:
    return "" if fmt == "mp3" else fmt.upper()


class LibraryController(QObject):
    """Expone la biblioteca a QML como `library`. Devuelve listas/mapas simples."""

    # Se emiten desde el hilo de trabajo: Qt las entrega en cola al hilo principal, de modo que
    # los manejadores QML corren desde el bucle de eventos (sin tener tomado el GIL de Python).
    editProgress = Signal(int, int)
    editFinished = Signal("QVariantMap")
    rescanProgress = Signal(int, int)
    duplicatesProgress = Signal(int, int)
    duplicatesDeleted = Signal("QVariantMap")
    rescanFinished = Signal("QVariantMap")

    def __init__(self, db_path: Path | str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_arg = db_path
        self._editing = False
        self._rescanning = False
        self._deleting = False
        self._conn = connect(db_path)
        self._db_path = str(db_path) if db_path else str(default_db_path())
        self._index: SearchIndex | None = None
        # Windows: la pista que suena no se puede reemplazar. Su escritura se aplaza (core/pending_tags.py) y se vuelca al
        # quedar libre. `_busy(ruta)` lo aporta el reproductor (`set_busy_check`); en otros sistemas no hay aplazamiento.
        self._busy: Callable[[Path], bool] | None = None
        self._defer = sys.platform == "win32"
        self._flush_lock = threading.Lock()

    def set_busy_check(self, check: Callable[[Path], bool]) -> None:
        self._busy = check

    @Slot(result="QVariantMap")
    def about(self) -> dict:
        return {
            "version": __version__,
            "license": LICENSE_NAME,
            "copyright": COPYRIGHT,
            "repoUrl": REPO_URL,
            "contactEmail": CONTACT_EMAIL,
            "dbPath": self._db_path,
            "cacheDir": str(paths.cache_dir() / "covers"),
            "backupsDir": str(paths.data_dir() / "backups"),
            "coversDir": str(paths.covers_dir()),
        }

    @Slot(result="QVariantMap")
    def stats(self) -> dict:
        s = library.stats(self._conn)
        s["incomplete"] = len(library.list_incomplete(self._conn))
        return s

    @Slot(result="QVariantList")
    def artists(self) -> list[dict]:
        return [dict(r) for r in library.list_artists(self._conn)]

    @Slot(int, int, int, result="QVariantList")
    def albums(self, artist_id: int, year: int, decade: int) -> list[dict]:
        rows = library.list_albums(
            self._conn, artist_id=artist_id or None, year=year or None, decade=decade or None
        )
        out = []
        for r in rows:
            d = dict(r)
            d["displayTitle"] = album_display(d["title"])
            out.append(d)
        return out

    @Slot(int, int, result=str)
    def coverKind(self, album_id: int, artist_id: int) -> str:
        """'album' | 'artist' | '': qué imagen existe para la pista (mini reproductor)."""
        return covers.cover_kind(self._conn, album_id, artist_id)

    @Slot(int, result="QVariantMap")
    def album(self, album_id: int) -> dict:
        row = library.get_album(self._conn, album_id)
        if row is None:
            return {}
        d = dict(row)
        d["displayTitle"] = album_display(d["title"])
        return d

    @Slot(result="QVariantList")
    def decades(self) -> list[dict]:
        return [dict(r) for r in library.list_decades(self._conn)]

    @Slot(int, result="QVariantList")
    def tracks(self, album_id: int) -> list[dict]:
        info = library.get_album(self._conn, album_id)
        album_artist = (info["artist"] if info else "").lower()
        out = []
        for r in library.list_tracks(self._conn, album_id=album_id):
            no = r["track_no"]
            if no and (r["disc_no"] or 1) > 1:
                number = f"{r['disc_no']}-{no}"
            else:
                number = str(no) if no else "–"
            out.append({
                "id": r["id"],
                "number": number,
                "title": r["title"],
                # en compilaciones se muestra el artista de cada pista
                "subtitle": r["artist"] if r["artist"].lower() != album_artist else "",
                "artist": r["artist"], "album": album_display(r["album"]), "year": str(r["year"] or ""),
                "badge": "VIDEO" if r["kind"] == "video" else _badge(r["format"]),
                "duration": r["duration"],
            })
        return out

    @Slot(int, result="QVariantList")
    def artistTopTracks(self, artist_id: int) -> list[dict]:
        """Hasta 2 canciones por álbum del artista, ordenadas por reproducciones."""
        return [{"id": r["id"], "title": r["title"], "duration": r["duration"],
                 "albumId": r["album_id"], "album": album_display(r["album"]),
                 "artist": r["artist"], "plays": r["plays"], "year": str(r["year"] or "")}
                for r in stats.artist_top_tracks(self._conn, artist_id, limit=30)]

    @Slot(result="QVariantMap")
    def home(self) -> dict:
        """Lo más escuchado, para la página Inicio."""
        return {
            "albums": [{**dict(r), "displayTitle": album_display(r["title"])}
                       for r in stats.top_albums(self._conn, 12)],
            "artists": [dict(r) for r in stats.top_artists(self._conn, 12)],
            "tracks": [{"id": r["id"], "title": r["title"], "duration": r["duration"],
                        "albumId": r["album_id"], "album": album_display(r["album"]),
                        "artist": r["artist"], "plays": r["plays"], "year": str(r["year"] or "")}
                       for r in stats.top_tracks(self._conn, 10)],
            "lists": [dict(r) for r in stats.top_playlists(self._conn, 12)],
        }

    @Slot(result="QVariantMap")
    def cleanup(self) -> dict:
        """Quita pistas de archivos que ya no existen y álbumes/artistas sin canciones."""
        return cleanup.purge_missing(self._conn)

    @Slot(int, result="QVariantMap")
    def trackInfo(self, track_id: int) -> dict:
        """Título, artista y álbum de una pista (para encabezados); {} si ya no existe."""
        row = library.get_track(self._conn, track_id)
        if row is None:
            return {}
        return {"id": row["id"], "title": row["title"], "artist": row["artist"],
                "album": album_display(row["album"]), "duration": row["duration"],
                "artistId": row["artist_id"], "albumId": row["album_id"],
                "hasArtist": row["artist"] != UNKNOWN_ARTIST, "hasAlbum": row["album"] != UNKNOWN_ALBUM,
                "path": row["path"]}

    @Slot(str, result=str)
    def localPath(self, url: str) -> str:
        """file:///ruta/imagen.jpg -> /ruta/imagen.jpg (también en Windows)."""
        return QUrl(url).toLocalFile()

    @Slot("QVariantList", result="QVariantMap")
    def tagValues(self, ids: list) -> dict:
        return tag_edit.common_values(self._conn, [int(i) for i in ids])

    @Slot("QVariantList", int, result="QVariantMap")
    def coverPreview(self, ids: list, artist_id: int) -> dict:
        """Imagen que tienen hoy las pistas (o el artista, si `artist_id` > 0) para el editor.

        {state: "none" | "single" | "mixed", source: "image://cover/..." (solo en "single")}
        """
        if artist_id > 0:
            if covers.artist_has_image(self._conn, artist_id):
                return {"state": "single", "source": f"image://cover/artist/{artist_id}"}
            return {"state": "none", "source": ""}
        state = covers.current_cover_state(self._conn, [int(i) for i in ids])
        source = f"image://cover/{state['albumId']}" if state["state"] == "single" else ""
        return {"state": state["state"], "source": source}

    @Slot(int, result="QVariantList")
    def artistTrackIds(self, artist_id: int) -> list:
        return library.list_artist_track_ids(self._conn, artist_id)

    @Slot("QVariantList", "QVariantMap", str, result="QVariantMap")
    def previewEdit(self, ids: list, changes: dict, cover_path: str) -> dict:
        try:
            result = tag_edit.preview(self._conn, [int(i) for i in ids], dict(changes), cover_path)
        except (ValueError, OSError) as exc:
            return {"error": str(exc), "count": 0, "lines": []}
        result["error"] = "" if result["lines"] else "No hay cambios que aplicar"
        return result

    @Slot("QVariantList", "QVariantMap", str, bool)
    def applyEdit(self, ids: list, changes: dict, cover_path: str, backup: bool) -> None:
        """Escribe los tags en un hilo aparte; avisa con editProgress y editFinished."""
        if self._editing:
            self.editFinished.emit({"updated": 0, "backupDir": "", "albumId": 0, "failed": [
                {"path": "", "message": "Ya hay una edición en curso"}]})
            return
        self._editing = True
        args = ([int(i) for i in ids], dict(changes), cover_path, backup)
        threading.Thread(target=self._edit_worker, args=args, daemon=True).start()

    # ---- escrituras aplazadas (Windows) ----
    @Slot(str)
    def flushPending(self, keep: str = "") -> None:
        """Vuelca en un hilo aparte las escrituras aplazadas cuyo archivo ya quedó libre (`keep` = el que suena ahora)."""
        if self._defer and pending_tags.registered():
            threading.Thread(target=self.flushPendingNow, args=(keep, 12), daemon=True).start()

    def flushPendingNow(self, keep: str = "", attempts: int = 12) -> dict:
        """Igual, pero sincrónico (arranque y cierre). Devuelve {"done", "locked", "skipped"}."""
        with self._flush_lock:
            conn = connect(self._db_arg)
            try:
                return pending_tags.flush_all(
                    keep=[keep] if keep else [], attempts=attempts, is_busy=self._busy,
                    on_done=lambda p: scanner.refresh_file_stat(conn, p))
            except Exception:  # noqa: BLE001  (red de seguridad: queda en el diario y se reintenta después)
                return {"done": 0, "locked": 0, "skipped": 0}
            finally:
                conn.close()

    def _edit_worker(self, ids: list, changes: dict, cover_path: str, backup: bool) -> None:
        try:
            conn = connect(self._db_arg)  # cada hilo usa su propia conexión SQLite
            try:
                result = tag_edit.apply_edit(
                    conn, ids, changes, cover_path, backup,
                    progress=lambda done, total: self.editProgress.emit(done, total),
                    is_busy=self._busy if self._defer else None, defer_on_lock=self._defer)
            finally:
                conn.close()
            payload = result.to_dict()
        except Exception as exc:  # noqa: BLE001  (se informa a la interfaz en vez de perderse)
            payload = {"updated": 0, "backupDir": "", "albumId": 0,
                       "failed": [{"path": "", "message": str(exc)}]}
        self._index = None  # el índice de búsqueda quedó desactualizado
        self._editing = False
        self.editFinished.emit(payload)

    @Slot()
    def reload(self) -> None:
        """Descarta el índice de búsqueda (p. ej. tras volver a escanear la biblioteca)."""
        self._index = None

    @Slot(str, result="QVariantMap")
    def searchAll(self, text: str) -> dict:
        """Resultados agrupados: artistas, álbumes y canciones."""
        if len(normalize(text)) < 2:
            return {"artists": [], "albums": [], "tracks": []}
        if self._index is None:
            self._index = SearchIndex.build(self._conn)
        res = self._index.query(text)
        return {
            "artists": [
                {"id": a["id"], "name": a["name"],
                 "subtitle": f"{a['albums']} {'álbum' if a['albums'] == 1 else 'álbumes'}"
                             f" · {a['tracks']} {'pista' if a['tracks'] == 1 else 'pistas'}"}
                for a in res.artists
            ],
            "albums": [
                {"id": a["id"], "title": album_display(a["title"]), "artist": a["artist"],
                 "subtitle": a["artist"] + (f" · {a['year']}" if a["year"] else "")}
                for a in res.albums
            ],
            "tracks": [
                {"id": t["id"], "number": "", "title": t["title"],
                 "subtitle": f"{t['artist']} · {album_display(t['album'])}",
                 "artist": t["artist"], "album": album_display(t["album"]), "year": str(t["year"] or ""),
                 "badge": "VIDEO" if t["kind"] == "video" else "", "duration": t["duration"]}
                for t in res.tracks
            ],
        }

    @Slot(result=int)
    def dismissedCount(self) -> int:
        return review.dismissed_count(self._conn)

    @Slot(result=int)
    def dismissReview(self) -> int:
        """Vacía «Por revisar» (no toca archivos ni tags). Devuelve cuántas pistas quitó."""
        return review.dismiss_listed(self._conn)

    @Slot(result=int)
    def restoreDismissed(self) -> int:
        return review.restore_dismissed(self._conn)

    @Slot()
    def rescanReview(self) -> None:
        """Relee los tags de los archivos de «Por revisar» en un hilo aparte (sin red)."""
        if self._rescanning:
            return
        self._rescanning = True
        ids = [r["id"] for r in library.list_incomplete(self._conn)]
        threading.Thread(target=self._rescan_worker, args=(ids,), daemon=True).start()

    def _rescan_worker(self, ids: list) -> None:
        try:
            conn = connect(self._db_arg)
            try:
                result = review.rescan_tracks(
                    conn, ids, progress=lambda done, total: self.rescanProgress.emit(done, total))
            finally:
                conn.close()
            result["total"] = len(ids)
            result["error"] = ""
        except Exception as exc:  # noqa: BLE001  (se informa a la interfaz en vez de perderse)
            result = {"total": len(ids), "checked": 0, "resolved": 0, "missing": 0, "errors": 0,
                      "error": str(exc)}
        self._index = None
        self._rescanning = False
        self.rescanFinished.emit(result)

    # ---- eliminar archivos (siempre a la papelera del sistema) ----
    @staticmethod
    def _trash(path: str) -> bool:
        result = QFile.moveToTrash(path)          # PySide6 devuelve bool o (bool, ruta_en_la_papelera)
        return bool(result[0] if isinstance(result, tuple) else result)

    @Slot(int, result="QVariantMap")
    def deleteTrackFile(self, track_id: int) -> dict:
        """Mueve a la papelera el archivo de UNA pista y la quita de la biblioteca."""
        ok, message = file_delete.delete_track(self._conn, track_id, self._trash)
        self._index = None
        return {"ok": ok, "message": message}

    @Slot("QVariantList", result="QVariantMap")
    def removeFromLibrary(self, ids: list) -> dict:
        """Quita pistas de la biblioteca SIN tocar sus archivos y las excluye de los escaneos siguientes."""
        result = library_folders.exclude_files(self._conn, [int(i) for i in ids])
        self._index = None
        n = result["removed"]
        text = ("1 canción quitada" if n == 1 else f"{n} canciones quitadas") + " de la biblioteca (los archivos siguen en el disco)"
        return {"ok": True, "message": text, **result}

    @staticmethod
    def _group_dicts(groups: list) -> list:
        out = []
        for number, members in enumerate(groups):
            out.append({
                "key": number,
                "title": f"{members[0].artist} \u2014 {members[0].title}",
                "items": [{"id": m.track_id, "path": m.path, "size": m.size, "album": album_display(m.album),
                           "bitrate": m.bitrate, "hasCover": m.has_cover, "inferred": m.inferred,
                           "format": Path(m.path).suffix.lstrip(".").upper(), "duration": m.duration} for m in members],
            })
        return out

    @Slot(result="QVariantList")
    def duplicateGroups(self) -> list:
        """Grupos de duplicados (archivos idénticos, con cualquier nombre). Cada grupo: `items`,
        de mejor a peor copia; la primera es la que se conserva por defecto."""
        return self._group_dicts(duplicates.find_groups(self._conn))

    @Slot(result="QVariantList")
    def similarGroups(self) -> list:
        """Grupos de la misma canción en archivos distintos (otro bitrate o formato); la primera es la de mayor bitrate."""
        return self._group_dicts(duplicates.find_similar_groups(self._conn))

    @Slot("QVariantList")
    def deleteDuplicates(self, plan: list) -> None:
        """Mueve a la papelera, por lotes y en un hilo aparte, las copias indicadas (tras verificar su contenido)."""
        self._start_delete(plan, "exact")

    @Slot("QVariantList")
    def deleteSimilar(self, plan: list) -> None:
        """Igual, para la misma canción en otro bitrate o formato (se verifica artista, título y duración)."""
        self._start_delete(plan, "similar")

    def _start_delete(self, plan: list, mode: str) -> None:
        if self._deleting:
            return
        self._deleting = True
        clean = [{"keep": int(g["keep"]), "remove": [int(i) for i in g["remove"]]} for g in plan]
        threading.Thread(target=self._delete_worker, args=(clean, mode), daemon=True).start()

    def _delete_worker(self, plan: list, mode: str = "exact") -> None:
        try:
            conn = connect(self._db_arg)
            try:
                out = file_delete.delete_duplicates(
                    conn, plan, self._trash, progress=lambda done, total: self.duplicatesProgress.emit(done, total),
                    mode=mode)
            finally:
                conn.close()
            result = {"deleted": out["deleted"], "skipped": [{"id": i, "reason": r} for i, r in out["skipped"]],
                      "bytes": out["bytes"], "error": ""}
        except Exception as exc:  # noqa: BLE001  (se informa a la interfaz en vez de perderse)
            result = {"deleted": [], "skipped": [], "bytes": 0, "error": str(exc)}
        self._index = None
        self._deleting = False
        self.duplicatesDeleted.emit(result)

    @Slot(result="QVariantList")
    def incomplete(self) -> list[dict]:
        out = []
        for r in library.list_incomplete(self._conn):
            reasons = []
            if r["inferred"]:
                reasons.append("deducido del nombre")
            if r["no_artist"]:
                reasons.append("sin artista")
            if r["damaged"]:
                reasons.append("posible archivo dañado (sin duración)")
            out.append({
                "id": r["id"],
                "number": "",
                "title": f"{r['artist']} - {r['title']}",
                "subtitle": f"{', '.join(reasons)}  ·  {r['path']}",
                "badge": "",
                "duration": r["duration"] or 0,
                # «tags»: el artista y el título salen de los tags (no se deducen del nombre del archivo)
                "hasTags": not (r["inferred"] or r["no_artist"]),
                "isVideo": r["kind"] == "video",
            })
        return out
