"""Servidores alternativos de letras y de portadas/información (expuesto a QML como `serverConfig`)."""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal, Slot

from sonoteca.online import servers
from sonoteca.online import settings as online_settings
from sonoteca.online.http import HttpClient, OfflineError


class ServersController(QObject):
    testFinished = Signal("QVariantMap")   # kind, ok, message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

    def _stored(self) -> online_settings.Settings:
        return online_settings.load(apply_env=False)   # lo que hay en el archivo, sin variables de entorno

    def _result(self, settings: online_settings.Settings | None, error: str = "") -> dict:
        return {"ok": not error, "error": error, "state": servers.state(settings or self._stored())}

    @Slot(result="QVariantMap")
    def state(self) -> dict:
        return servers.state(self._stored())

    @Slot(str, str, result="QVariantMap")
    def addLyrics(self, name: str, url: str) -> dict:
        s = self._stored()
        try:
            item = servers.add_lyrics_server(s, name, url)
        except ValueError as exc:
            return self._result(None, str(exc))
        online_settings.save(s)
        return {**self._result(s), "id": item["id"]}

    @Slot(str, str, str, str, result="QVariantMap")
    def addMeta(self, name: str, musicbrainz: str, coverart: str, wikipedia: str) -> dict:
        s = self._stored()
        try:
            item = servers.add_meta_server(s, name, musicbrainz, coverart, wikipedia)
        except ValueError as exc:
            return self._result(None, str(exc))
        online_settings.save(s)
        return {**self._result(s), "id": item["id"]}

    @Slot(str, str, result="QVariantMap")
    def remove(self, kind: str, server_id: str) -> dict:
        s = self._stored()
        servers.remove_server(s, kind, server_id)
        online_settings.save(s)
        return self._result(s)

    @Slot(str, str, result="QVariantMap")
    def setActive(self, kind: str, server_id: str) -> dict:
        s = self._stored()
        try:
            servers.set_active(s, kind, server_id)
        except ValueError as exc:
            return self._result(None, str(exc))
        online_settings.save(s)
        return self._result(s)

    @Slot(str, str)
    def testLyrics(self, url: str, _unused: str = "") -> None:
        threading.Thread(target=self._test, args=("lyrics", url, "", ""), daemon=True).start()

    @Slot(str, str)
    def testMeta(self, musicbrainz: str, wikipedia: str) -> None:
        threading.Thread(target=self._test, args=("meta", "", musicbrainz, wikipedia), daemon=True).start()

    def _test(self, kind: str, url: str, musicbrainz: str, wikipedia: str) -> None:
        client = None
        try:
            client = HttpClient()
            if kind == "lyrics":
                ok, message = servers.test_lyrics(client, url)
            else:
                ok, message = servers.test_meta(client, musicbrainz, wikipedia)
        except OfflineError:
            ok, message = False, "El modo sin conexi\u00f3n est\u00e1 activo: activa internet (Archivo \u25b8 Internet\u2026) para probar."
        except Exception as exc:  # noqa: BLE001  (se informa a la interfaz en vez de perderse en el hilo)
            ok, message = False, f"No se pudo probar: {exc}"
        finally:
            if client is not None:
                client.close()
        self.testFinished.emit({"kind": kind, "ok": ok, "message": message})
