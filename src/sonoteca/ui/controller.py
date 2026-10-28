"""Puente entre la base SQLite y QML. Solo lectura en la Fase 2."""
from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot

from sonoteca import __version__
from sonoteca.core import cleanup, covers, library, paths, review, stats, tag_edit
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
    rescanFinished = Signal("QVariantMap")

    def __init__(self, db_path: Path | str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_arg = db_path
        self._editing = False
        self._rescanning = False
        self._conn = connect(db_path)
        self._db_path = str(db_path) if db_path else str(default_db_path())
        self._index: SearchIndex | None = None

    @Slot(result="QVariantMap")
    def about(self) -> dict:
        return {
            "version": __version__,
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
                "badge": "VIDEO" if r["kind"] == "video" else _badge(r["format"]),
                "duration": r["duration"],
            })
        return out

    @Slot(int, result="QVariantList")
    def artistTopTracks(self, artist_id: int) -> list[dict]:
        """Hasta 2 canciones por álbum del artista, ordenadas por reproducciones."""
        return [{"id": r["id"], "title": r["title"], "duration": r["duration"],
                 "albumId": r["album_id"], "album": album_display(r["album"]),
                 "artist": r["artist"], "plays": r["plays"]}
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
                        "artist": r["artist"], "plays": r["plays"]}
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
                "hasArtist": row["artist"] != UNKNOWN_ARTIST, "hasAlbum": row["album"] != UNKNOWN_ALBUM}

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

    def _edit_worker(self, ids: list, changes: dict, cover_path: str, backup: bool) -> None:
        try:
            conn = connect(self._db_arg)  # cada hilo usa su propia conexión SQLite
            try:
                result = tag_edit.apply_edit(
                    conn, ids, changes, cover_path, backup,
                    progress=lambda done, total: self.editProgress.emit(done, total))
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

    @Slot(result="QVariantList")
    def incomplete(self) -> list[dict]:
        out = []
        for r in library.list_incomplete(self._conn):
            reasons = []
            if r["inferred"]:
                reasons.append("deducido del nombre")
            if r["no_artist"]:
                reasons.append("sin artista")
            if r["no_album"]:
                reasons.append("sin álbum")
            out.append({
                "id": r["id"],
                "number": "",
                "title": f"{r['artist']} - {r['title']}",
                "subtitle": f"{', '.join(reasons)}  ·  {r['path']}",
                "badge": "",
                "duration": 0,
            })
        return out
