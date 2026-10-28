"""Consultas en línea para la interfaz (expuesto a QML como `online`).

Todo lo que usa la red corre en un hilo aparte y avisa con señales emitidas desde ese hilo (Qt las
entrega en cola al hilo principal), así la interfaz nunca se congela esperando a internet.
"""
from __future__ import annotations

import os
import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot

from sonoteca.core import cover_store, paths
from sonoteca.core.covers import artist_photo
from sonoteca.core.db import connect
from sonoteca.core.tag_writer import image_mime
from sonoteca.online import coverart, enrich
from sonoteca.online import settings as online_settings
from sonoteca.online.http import HttpClient, OfflineError, OnlineError
from sonoteca.online.wikipedia import ArtistInfo

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_CANDIDATES = 8
OFFLINE_MESSAGE = "El modo sin conexión está activo. Actívalo en Archivo \u25b8 Internet\u2026"


def artist_photo_path(artist_id: int) -> Path:
    """Dónde se guarda la foto descargada (datos del usuario, no la caché)."""
    return paths.artists_dir() / f"{artist_id}.jpg"


class OnlineController(QObject):
    offlineChanged = Signal()
    contactChanged = Signal()
    busyChanged = Signal()
    progress = Signal(str)
    artistInfoReady = Signal(int, "QVariantMap")  # id de artista, datos ({} si no se encontró)
    albumCandidatesReady = Signal(int, "QVariantList")
    artistCandidatesReady = Signal(int, "QVariantList")  # id de artista, artículos posibles
    coverReady = Signal(str)  # ruta de la portada ya guardada en la carpeta de la app
    onlineError = Signal(str)

    def __init__(self, db_path: Path | str | None = None,
                 client_factory: Callable[[], HttpClient] = HttpClient,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_arg = db_path
        self.client_factory = client_factory  # las pruebas lo reemplazan por un servidor simulado
        self._conn = connect(db_path)
        self._busy = False

    # ---- ajustes ----
    @Property(bool, notify=offlineChanged)
    def offline(self) -> bool:
        return online_settings.load().offline

    @Property(str, notify=contactChanged)
    def contact(self) -> str:
        return online_settings.load().contact

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Slot(bool)
    def setOffline(self, value: bool) -> None:
        stored = online_settings.load(apply_env=False)
        stored.offline = value
        online_settings.save(stored)
        self.offlineChanged.emit()

    @Slot(str)
    def setContact(self, value: str) -> None:
        stored = online_settings.load(apply_env=False)
        stored.contact = value.strip()
        online_settings.save(stored)
        self.contactChanged.emit()

    @Slot(str, result=str)
    def fileUrl(self, path: str) -> str:
        """Ruta local -> URL file:// que entiende QML."""
        return QUrl.fromLocalFile(path).toString()

    # ---- lectura local (sin red) ----
    @Slot(int, result="QVariantMap")
    def storedArtistInfo(self, artist_id: int) -> dict:
        info = enrich.stored_artist_info(self._conn, artist_id)
        if info:
            return self._artist_payload(artist_id, info)
        if artist_photo(artist_id):   # solo foto (p. ej. elegida a mano), sin descripci\u00f3n
            row = self._conn.execute("SELECT name FROM artists WHERE id = ?", (artist_id,)).fetchone()
            if row:
                return self._artist_payload(artist_id, {"name": row["name"], "bio": "", "bio_url": "",
                                                        "bio_lang": "", "bio_source": ""})
        return {}

    @Slot(int, str, result="QVariantMap")
    def setArtistImage(self, artist_id: int, image_path: str) -> dict:
        """Cambia solo la foto del artista con un archivo JPG/PNG (no usa internet ni toca la descripci\u00f3n)."""
        try:
            data = Path(image_path).read_bytes()
            if len(data) > MAX_PHOTO_BYTES:
                raise ValueError("La imagen pesa m\u00e1s de 5 MB")
            self._store_photo(artist_id, data)
        except (ValueError, OSError) as exc:
            return {"ok": False, "error": str(exc), "info": {}}
        return {"ok": True, "error": "", "info": self.storedArtistInfo(artist_id)}

    @staticmethod
    def _artist_payload(artist_id: int, info: dict) -> dict:
        photo = artist_photo(artist_id)
        return {
            "name": info["name"], "bio": info["bio"], "url": info["bio_url"] or "",
            "lang": info["bio_lang"] or "", "source": info["bio_source"] or "Wikipedia",
            "imagePath": str(photo) if photo else "",
        }

    # ---- consultas en línea ----
    def _spawn(self, work: Callable[[HttpClient, object], None]) -> bool:
        if self._busy:
            self.onlineError.emit("Ya hay una consulta en curso; espera un momento.")
            return False
        self._busy = True
        self.busyChanged.emit()

        def run() -> None:
            client = None
            try:
                client = self.client_factory()
                conn = connect(self._db_arg)  # cada hilo usa su propia conexión SQLite
                try:
                    work(client, conn)
                finally:
                    conn.close()
            except OfflineError:
                self.onlineError.emit(OFFLINE_MESSAGE)
            except OnlineError as exc:
                self.onlineError.emit(str(exc))
            except Exception as exc:  # noqa: BLE001  (se informa a la interfaz en vez de perderse)
                self.onlineError.emit(f"Error inesperado: {exc}")
            finally:
                if client is not None:
                    client.close()
                self._busy = False
                self.busyChanged.emit()

        threading.Thread(target=run, daemon=True).start()
        return True

    @Slot(int, bool)
    def requestArtistInfo(self, artist_id: int, force: bool) -> None:
        def work(client: HttpClient, conn) -> None:
            self.progress.emit("Consultando MusicBrainz y Wikipedia\u2026")
            info = enrich.fetch_artist_info(client, conn, artist_id, force=force)
            if info and info.get("image_url") and (force or not artist_photo(artist_id)):
                self._download_photo(client, artist_id, info["image_url"])
            self.artistInfoReady.emit(artist_id, self._artist_payload(artist_id, info) if info else {})

        self._spawn(work)

    @staticmethod
    def _store_photo(artist_id: int, data: bytes) -> None:
        image_mime(data)  # solo JPG/PNG (ValueError si no lo es)
        target = artist_photo_path(artist_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)

    @staticmethod
    def _download_photo(client: HttpClient, artist_id: int, url: str) -> None:
        try:
            result = client.get_bytes(url, max_bytes=MAX_PHOTO_BYTES)
            if result is None:
                return
            OnlineController._store_photo(artist_id, result[0])
        except (OnlineError, ValueError, OSError):
            pass  # la foto es opcional

    @Slot(int, str)
    def requestArtistCandidates(self, artist_id: int, query: str) -> None:
        """Artículos de Wikipedia que podrían ser el artista, para elegir el correcto."""
        def work(client: HttpClient, conn) -> None:
            self.progress.emit("Buscando en Wikipedia\u2026")
            found = enrich.artist_candidates(client, conn, artist_id, query)
            self.artistCandidatesReady.emit(artist_id, [
                {"name": c.name, "summary": c.summary, "description": c.description,
                 "url": c.url, "language": c.language, "imageUrl": c.image_url}
                for c in found])

        self._spawn(work)

    @Slot(int, "QVariantMap")
    def applyArtistCandidate(self, artist_id: int, candidate: dict) -> None:
        """Usa el artículo elegido: reemplaza la ficha y la foto anteriores."""
        def work(client: HttpClient, conn) -> None:
            info = ArtistInfo(name=str(candidate.get("name", "")), summary=str(candidate.get("summary", "")),
                              url=str(candidate.get("url", "")), language=str(candidate.get("language", "")),
                              description=str(candidate.get("description", "")),
                              image_url=str(candidate.get("imageUrl", "")))
            if not info.summary:
                raise OnlineError("El artículo elegido no tiene texto")
            enrich.apply_artist_info(conn, artist_id, info)
            old = artist_photo(artist_id)
            if old:
                old.unlink(missing_ok=True)  # la foto anterior era del artista equivocado
            if info.image_url:
                self._download_photo(client, artist_id, info.image_url)
            stored = enrich.stored_artist_info(conn, artist_id)
            self.artistInfoReady.emit(artist_id, self._artist_payload(artist_id, stored) if stored else {})

        self._spawn(work)

    @Slot(int, str, str, result="QVariantMap")
    def saveManualArtistInfo(self, artist_id: int, text: str, image_path: str) -> dict:
        """Descripción propia (y foto opcional). No usa internet."""
        try:
            enrich.set_manual_artist_info(self._conn, artist_id, text)
            if image_path:
                data = Path(image_path).read_bytes()
                if len(data) > MAX_PHOTO_BYTES:
                    raise ValueError("La imagen pesa m\u00e1s de 5 MB")
                self._store_photo(artist_id, data)
        except (ValueError, OSError) as exc:
            return {"ok": False, "error": str(exc), "info": {}}
        info = enrich.stored_artist_info(self._conn, artist_id)
        return {"ok": True, "error": "", "info": self._artist_payload(artist_id, info) if info else {}}

    @Slot(int, int)
    def requestAlbumCandidates(self, album_id: int, track_id: int) -> None:
        def work(client: HttpClient, conn) -> None:
            self.progress.emit("Buscando en MusicBrainz\u2026")
            found = enrich.album_candidates(client, conn, album_id, track_id=track_id or None)
            found = found[:MAX_CANDIDATES]
            out = []
            for i, c in enumerate(found, start=1):
                self.progress.emit(f"Descargando miniaturas ({i}/{len(found)})\u2026")
                try:
                    preview = enrich.preview_cover(client, c)
                except (OnlineError, ValueError):
                    preview = None  # sin miniatura, el candidato igual se puede elegir
                out.append({
                    "id": c.release_group_id, "title": c.title, "artist": c.artist,
                    "year": c.year or 0, "kind": c.kind, "confident": c.confident,
                    "lengthMatch": c.length_match, "via": c.via,
                    "previewPath": str(preview) if preview else "",
                })
            self.albumCandidatesReady.emit(album_id, out)

        self._spawn(work)

    @Slot(str)
    def requestCover(self, release_group_id: str) -> None:
        def work(client: HttpClient, conn) -> None:
            self.progress.emit("Descargando la portada\u2026")
            data = coverart.fetch_best(client, release_group_id)
            if not data:
                self.onlineError.emit("Ese álbum no tiene portada en Cover Art Archive.")
                return
            self.coverReady.emit(str(cover_store.store_chosen(data)))  # copia propia en la app

        self._spawn(work)
