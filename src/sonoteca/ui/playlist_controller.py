"""Listas de reproducción personalizadas para QML (expuesto como `playlists`)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from sonoteca.core import folder_lists, library_folders
from sonoteca.core import playlists as store
from sonoteca.core.db import connect

from .controller import album_display


def _songs(n: int) -> str:
    return f"{n} canción" if n == 1 else f"{n} canciones"


class PlaylistController(QObject):
    changed = Signal()  # cambió alguna lista (nombre, contenido, altas o bajas)
    message = Signal(str)  # aviso breve para el usuario

    def __init__(self, db_path: Path | str | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._conn = connect(db_path)
        self._revision = 0
        self._members: set[int] | None = None      # pistas que están en alguna lista (se recalcula tras cada cambio)

    @Property(int, notify=changed)
    def revision(self) -> int:
        return self._revision

    @Property(int, notify=changed)
    def count(self) -> int:
        return len(store.list_playlists(self._conn))

    def _bump(self) -> None:
        self._revision += 1
        self._members = None
        self.changed.emit()

    @staticmethod
    def _result(**extra) -> dict:
        return {"ok": True, "error": "", **extra}

    @staticmethod
    def _error(exc: Exception) -> dict:
        return {"ok": False, "error": str(exc), "id": 0, "added": 0}

    # ---- lectura ----
    @Slot(result="QVariantList")
    def lists(self) -> list[dict]:
        return [dict(r) for r in store.list_playlists(self._conn)]

    @Slot(int, result="QVariantMap")
    def info(self, playlist_id: int) -> dict:
        row = store.get_playlist(self._conn, playlist_id)
        if not row:
            return {}
        return {**dict(row), "description": store.describe_artists(self._conn, playlist_id)}

    @Slot(int, result="QVariantList")
    def tracks(self, playlist_id: int) -> list[dict]:
        return [{"position": r["position"], "id": r["id"], "title": r["title"], "artist": r["artist"],
                 "album": album_display(r["album"]), "albumId": r["album_id"],
                 "duration": r["duration"], "year": str(r["year"] or "")}
                for r in store.tracks(self._conn, playlist_id)]

    @Slot(int, result="QVariantList")
    def coverAlbums(self, playlist_id: int) -> list[int]:
        """Hasta 4 álbumes de la lista: con 2 o más se dibuja un collage como portada."""
        return store.cover_album_ids(self._conn, playlist_id, 4)

    @Slot(int, result="QVariantList")
    def trackIds(self, playlist_id: int) -> list[int]:
        return store.track_ids(self._conn, playlist_id)

    # ---- cambios (devuelven {ok, error, ...}) ----
    @Slot(str, result="QVariantMap")
    def create(self, name: str) -> dict:
        try:
            playlist_id = store.create(self._conn, name)
        except ValueError as exc:
            return self._error(exc)
        self._bump()
        self.message.emit(f"Lista \u00ab{store.clean_name(name)}\u00bb creada")
        return self._result(id=playlist_id)

    @Slot(str, "QVariantList", result="QVariantMap")
    def createWithTracks(self, name: str, ids: list) -> dict:
        try:
            playlist_id = store.create_from_tracks(self._conn, name, [int(i) for i in ids])
        except ValueError as exc:
            return self._error(exc)
        self._bump()
        n = len(store.track_ids(self._conn, playlist_id))
        self.message.emit(f"Lista \u00ab{store.clean_name(name)}\u00bb creada con {_songs(n)}")
        return self._result(id=playlist_id, added=n)

    # ---- listas a partir de carpetas de la biblioteca ----
    @Slot(result="QVariantList")
    def folderCandidates(self) -> list:
        """Carpetas desde las que se puede crear una lista (las que registró «Buscar música» y sus carpetas madre)."""
        return library_folders.list_candidates(self._conn)

    @Slot("QVariantList", result="QVariantList")
    def planFolderLists(self, items: list) -> list:
        """Qué listas saldrían de [{path, sub}], y cuáles chocan de nombre con otra lista."""
        return folder_lists.plan(self._conn, [{"path": str(i["path"]), "sub": bool(i.get("sub"))} for i in items])

    @Slot("QVariantList", result="QVariantMap")
    def createFromFolders(self, decisions: list) -> dict:
        """Crea las listas con la decisión del usuario para cada una (create, rename, append o skip)."""
        clean = [{"path": str(d["path"]), "sub": bool(d.get("sub")), "name": str(d["name"]), "mode": str(d.get("mode", "create"))}
                 for d in decisions]
        result = folder_lists.apply(self._conn, clean)
        if result["created"] or result["appended"]:
            self._bump()
        tracks = sum(c["added"] for c in result["created"]) + sum(a["added"] for a in result["appended"])
        parts = []
        if result["created"]:
            parts.append(f"{len(result['created'])} " + ("lista creada" if len(result["created"]) == 1 else "listas creadas"))
        if result["appended"]:
            parts.append(f"{len(result['appended'])} " + ("lista ampliada" if len(result["appended"]) == 1 else "listas ampliadas"))
        text = (" y ".join(parts) + f" ({_songs(tracks)})") if parts else "No se creó ninguna lista"
        if result["errors"]:
            text += " \u00b7 " + str(len(result["errors"])) + " con problemas: " + result["errors"][0]
        return {"ok": not result["errors"], "message": text, **result}

    @Slot(int, str, result="QVariantMap")
    def rename(self, playlist_id: int, name: str) -> dict:
        try:
            store.rename(self._conn, playlist_id, name)
        except ValueError as exc:
            return self._error(exc)
        self._bump()
        return self._result(id=playlist_id)

    @Slot(int, result="QVariantMap")
    def remove(self, playlist_id: int) -> dict:
        info = store.get_playlist(self._conn, playlist_id)
        store.delete(self._conn, playlist_id)
        self._bump()
        if info:
            self.message.emit(f"Lista \u00ab{info['name']}\u00bb eliminada")
        return self._result()

    @Slot(int, result=bool)
    def inLists(self, track_id: int) -> bool:
        """¿Está la pista en alguna lista guardada? (columna «En lista»; el conjunto se guarda hasta el próximo cambio)"""
        if self._members is None:
            self._members = store.member_track_ids(self._conn)
        return track_id in self._members

    @Slot(int, result="QVariantList")
    def listNames(self, track_id: int) -> list:
        """Nombres de las listas que contienen la pista (tooltip de la columna «En lista»)."""
        return store.lists_with_track(self._conn, track_id)

    @Slot(int, "QVariantList", result=int)
    def existingCount(self, playlist_id: int, ids: list) -> int:
        """Cuántas de estas canciones ya están en la lista (para preguntar antes de repetirlas)."""
        try:
            return len(store.already_in(self._conn, playlist_id, [int(i) for i in ids]))
        except ValueError:
            return 0

    def _add(self, playlist_id: int, ids: list, skip_existing: bool) -> dict:
        try:
            added = store.add_tracks(self._conn, playlist_id, [int(i) for i in ids], skip_existing)
        except ValueError as exc:
            return self._error(exc)
        info = store.get_playlist(self._conn, playlist_id)
        if added:
            self._bump()
            self.message.emit(f"{_songs(added).capitalize()} agregada{'' if added == 1 else 's'} "
                              f"a \u00ab{info['name']}\u00bb")
        return self._result(added=added)

    @Slot(int, "QVariantList", result="QVariantMap")
    def addTracks(self, playlist_id: int, ids: list) -> dict:
        """Agrega todas, incluso las que ya estaban (la lista admite repetidas)."""
        return self._add(playlist_id, ids, False)

    @Slot(int, "QVariantList", result="QVariantMap")
    def addNewTracks(self, playlist_id: int, ids: list) -> dict:
        """Agrega solo las que aún no están en la lista."""
        return self._add(playlist_id, ids, True)

    @Slot(int, int, result="QVariantMap")
    def removeAt(self, playlist_id: int, position: int) -> dict:
        try:
            store.remove_at(self._conn, playlist_id, position)
        except (IndexError, sqlite3.Error) as exc:
            return self._error(exc)
        self._bump()
        return self._result()

    @Slot(int, int, int, result="QVariantMap")
    def moveTrack(self, playlist_id: int, src: int, dst: int) -> dict:
        try:
            store.move(self._conn, playlist_id, src, dst)
        except (IndexError, sqlite3.Error) as exc:
            return self._error(exc)
        self._bump()
        return self._result()
