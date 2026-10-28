"""Letras y traducción para la interfaz (expuesto a QML como `lyrics`).

Lo guardado en la base se lee sin red. Buscar la letra (LRCLIB) y traducirla (DeepL) corren en un
hilo aparte y avisan con señales emitidas desde ese hilo (Qt las entrega en cola al hilo
principal), así la interfaz nunca se congela esperando a internet.
"""
from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Property, QObject, Signal, Slot

from musicapp.core import lyrics as store
from musicapp.core.db import connect
from musicapp.online import lyrics as flow
from musicapp.online import settings as online_settings
from musicapp.online.http import HttpClient, OfflineError, OnlineError
from musicapp.online.translate import KEY_HELP, DeepLTranslator, KeyStore, normalize_lang

OFFLINE_MESSAGE = "El modo sin conexión está activo. Actívalo en Archivo \u25b8 Internet\u2026"


class LyricsController(QObject):
    busyChanged = Signal()
    keyChanged = Signal()
    langChanged = Signal()
    progress = Signal(str)
    lyricsReady = Signal(int, "QVariantMap")  # id de pista, documento (ver core.lyrics.lyrics_doc)
    lyricsError = Signal(str)

    def __init__(self, db_path: Path | str | None = None,
                 client_factory: Callable[[], HttpClient] = HttpClient,
                 translator_factory: Callable[[str], DeepLTranslator] = DeepLTranslator,
                 key_store: KeyStore | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db_arg = db_path
        self.client_factory = client_factory  # las pruebas lo reemplazan por un servidor simulado
        self.translator_factory = translator_factory
        self._keys = key_store or KeyStore()
        self._conn = connect(db_path)
        self._busy = False
        self._has_key: bool | None = None  # se consulta una vez (el llavero puede pedir permiso)

    # ---- propiedades ----
    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(bool, notify=keyChanged)
    def hasKey(self) -> bool:
        if self._has_key is None:
            self._has_key = bool(self._keys.get())
        return self._has_key

    @Property(str, notify=langChanged)
    def translateLang(self) -> str:
        return online_settings.load().translate_lang

    # ---- ajustes ----
    @Slot(str, result=str)
    def setTranslateLang(self, code: str) -> str:
        """Devuelve un mensaje de error, o '' si se guardó."""
        try:
            lang = normalize_lang(code)
        except OnlineError as exc:
            return str(exc)
        stored = online_settings.load(apply_env=False)
        stored.translate_lang = lang
        online_settings.save(stored)
        self.langChanged.emit()
        return ""

    @Slot(str, result=str)
    def setApiKey(self, key: str) -> str:
        """Guarda la clave de DeepL en el llavero del sistema. Devuelve un error, o ''."""
        try:
            self._keys.set(key)
        except OnlineError as exc:
            return str(exc)
        self._has_key = True
        self.keyChanged.emit()
        return ""

    @Slot()
    def clearApiKey(self) -> None:
        self._keys.delete()
        self._has_key = bool(self._keys.get())  # puede seguir existiendo la variable de entorno
        self.keyChanged.emit()

    # ---- lectura local (sin red) ----
    @Slot(int, result="QVariantMap")
    def stored(self, track_id: int) -> dict:
        return store.lyrics_doc(self._conn, track_id, self.translateLang)

    @Slot(int, result=str)
    def rawText(self, track_id: int) -> str:
        """Texto guardado para editarlo a mano (vacío si no hay letra)."""
        return store.raw_text(self._conn, track_id)

    @Slot(int, str, result="QVariantMap")
    def saveManual(self, track_id: int, text: str) -> dict:
        """Guarda la letra escrita por el usuario (vacío = borrarla) y devuelve el documento nuevo."""
        store.save_manual(self._conn, track_id, text)
        return store.lyrics_doc(self._conn, track_id, self.translateLang)

    # ---- consultas en línea ----
    def _spawn(self, work: Callable[[object], None]) -> bool:
        if self._busy:
            self.lyricsError.emit("Ya hay una consulta en curso; espera un momento.")
            return False
        self._busy = True
        self.busyChanged.emit()

        def run() -> None:
            try:
                conn = connect(self._db_arg)  # cada hilo usa su propia conexión SQLite
                try:
                    work(conn)
                finally:
                    conn.close()
            except OfflineError:
                self.lyricsError.emit(OFFLINE_MESSAGE)
            except OnlineError as exc:
                self.lyricsError.emit(str(exc))
            except Exception as exc:  # noqa: BLE001  (se informa a la interfaz en vez de perderse)
                self.lyricsError.emit(f"Error inesperado: {exc}")
            finally:
                self._busy = False
                self.busyChanged.emit()

        threading.Thread(target=run, daemon=True).start()
        return True

    @Slot(int, bool)
    def request(self, track_id: int, force: bool) -> None:
        """Busca la letra en LRCLIB (si ya está guardada, solo la lee) y la guarda."""
        lang = self.translateLang

        def work(conn) -> None:
            self.progress.emit("Buscando la letra en LRCLIB\u2026")
            client = self.client_factory()
            try:
                doc = flow.fetch_lyrics(client, conn, track_id, lang=lang, force=force)
            finally:
                client.close()
            self.lyricsReady.emit(track_id, doc)

        self._spawn(work)

    @Slot(int, bool)
    def translate(self, track_id: int, force: bool) -> None:
        """Traduce la letra guardada al idioma elegido con DeepL y guarda el resultado."""
        lang = self.translateLang

        def work(conn) -> None:
            key = self._keys.get()
            if not key:
                raise OnlineError(KEY_HELP)
            self.progress.emit("Traduciendo con DeepL\u2026")
            translator = self.translator_factory(key)
            try:
                doc = flow.translate_lyrics(translator, conn, track_id, lang, force=force)
            finally:
                translator.close()
            self.lyricsReady.emit(track_id, doc)

        self._spawn(work)
