"""Traducción de letras con DeepL (clave propia del usuario, guardada en el llavero del sistema).

El plan gratuito de DeepL incluye 500 000 caracteres al mes y se detiene al llegar al límite (no
cobra por exceso); una letra típica ronda los 1 500-2 500 caracteres. Las claves del plan gratuito
terminan en ":fx" y usan otro servidor (api-free.deepl.com). Solo se envía el texto de las líneas
que hay que traducir; el resultado se guarda en la base y no se vuelve a pedir.
"""
from __future__ import annotations

import os
import re
import time

import httpx

from .http import OfflineError, OnlineError
from .settings import Settings, load, user_agent

KEYRING_SERVICE = "musicapp"
KEYRING_USER = "deepl-api-key"
ENV_KEY = "MUSICAPP_DEEPL_KEY"  # alternativa al llavero (p. ej. Linux sin entorno de escritorio)

FREE_HOST = "https://api-free.deepl.com"
PRO_HOST = "https://api.deepl.com"
BATCH_TEXTS = 50  # DeepL admite hasta 50 textos por petición
BATCH_BYTES = 100 * 1024  # el límite de DeepL es 128 KiB por petición
MAX_CHARS = 30_000  # protección: una letra normal es de unos pocos miles
_LANG = re.compile(r"^[A-Z]{2}(-[A-Z]{2,4})?$")
KEY_HELP = ("Falta la clave de DeepL. Consíguela gratis en deepl.com (plan «API Free», 500 000 "
            "caracteres al mes) y pégala en Letra \u25b8 Traducción.")


def normalize_lang(code: str) -> str:
    """'es' -> 'ES'. Lanza OnlineError si no parece un código de idioma de DeepL."""
    value = (code or "").strip().upper().replace("_", "-")
    if not _LANG.match(value):
        raise OnlineError(f"«{code}» no es un código de idioma válido (ejemplos: ES, EN-US, PT-BR)")
    return value


class KeyStore:
    """Clave de la API: variable MUSICAPP_DEEPL_KEY o, si no, el llavero del sistema."""

    def __init__(self, backend=None) -> None:
        self._backend = backend  # objeto con get/set/delete_password (las pruebas pasan uno falso)

    def _keyring(self):
        if self._backend is not None:
            return self._backend
        try:
            import keyring
        except ImportError as exc:
            raise OnlineError("Falta el paquete «keyring» (instala con pip install keyring) "
                              f"o define la variable {ENV_KEY}.") from exc
        return keyring

    def get(self) -> str:
        env = os.environ.get(ENV_KEY, "").strip()
        if env:
            return env
        try:
            return (self._keyring().get_password(KEYRING_SERVICE, KEYRING_USER) or "").strip()
        except Exception:  # noqa: BLE001  (sin llavero disponible = sin clave guardada)
            return ""

    def set(self, key: str) -> None:
        key = key.strip()
        if not key:
            raise OnlineError("La clave está vacía")
        try:
            self._keyring().set_password(KEYRING_SERVICE, KEYRING_USER, key)
        except OnlineError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise OnlineError("No se pudo guardar la clave en el llavero del sistema "
                              f"({exc.__class__.__name__}). Puedes definir {ENV_KEY} en su lugar.") from exc

    def delete(self) -> None:
        try:
            self._keyring().delete_password(KEYRING_SERVICE, KEYRING_USER)
        except Exception:  # noqa: BLE001  (si no había clave guardada no pasa nada)
            pass


def _batches(indices: list[int], lines: list[str]):
    batch: list[int] = []
    size = 0
    for i in indices:
        cost = len(lines[i].encode("utf-8")) + 64  # margen por el JSON
        if batch and (len(batch) >= BATCH_TEXTS or size + cost > BATCH_BYTES):
            yield batch
            batch, size = [], 0
        batch.append(i)
        size += cost
    if batch:
        yield batch


class DeepLTranslator:
    provider = "DeepL"

    def __init__(self, api_key: str, settings: Settings | None = None, *, transport=None,
                 sleep=time.sleep) -> None:
        self._key = (api_key or "").strip()
        if not self._key:
            raise OnlineError(KEY_HELP)
        self.settings = settings or load()
        self._sleep = sleep
        self._base = FREE_HOST if self._key.endswith(":fx") else PRO_HOST
        self.requests = 0  # peticiones enviadas (para las pruebas)
        self._client = httpx.Client(
            headers={"Authorization": f"DeepL-Auth-Key {self._key}",
                     "User-Agent": user_agent(self.settings.contact)},
            transport=transport, timeout=httpx.Timeout(30.0, connect=5.0))

    def close(self) -> None:
        self._client.close()

    def _call(self, method: str, path: str, payload: dict | None = None):
        if self.settings.offline:
            raise OfflineError("Modo sin conexión activo")
        for attempt in range(3):
            self.requests += 1
            try:
                response = self._client.request(method, self._base + path, json=payload)
            except httpx.TimeoutException:
                if attempt < 2:
                    continue
                raise OnlineError("DeepL tardó demasiado en responder") from None
            except httpx.HTTPError as exc:
                raise OnlineError(f"No se pudo conectar con DeepL: {exc.__class__.__name__}") from exc
            code = response.status_code
            if code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise OnlineError("La respuesta de DeepL no es válida") from exc
            if code in (429, 529):  # demasiadas peticiones / servidor ocupado: se reintenta
                if attempt < 2:
                    try:
                        delay = float(response.headers.get("Retry-After", ""))
                    except ValueError:
                        delay = 2.0 * (attempt + 1)
                    self._sleep(min(delay, 10.0))
                    continue
                raise OnlineError("DeepL está recibiendo demasiadas peticiones; inténtalo en unos minutos")
            if code == 403:
                raise OnlineError("DeepL rechazó la clave. Revisa que esté completa "
                                  "(en el plan gratuito termina en «:fx»).")
            if code == 456:
                raise OnlineError("Se agotó la cuota mensual de DeepL. Podrás traducir de nuevo "
                                  "cuando se renueve o si cambias de plan.")
            if code == 400:
                raise OnlineError("DeepL no aceptó la petición (revisa el idioma de destino)")
            if code >= 500:
                raise OnlineError(f"DeepL no está disponible en este momento (HTTP {code})")
            raise OnlineError(f"DeepL respondió con un error (HTTP {code})")
        raise OnlineError("DeepL no respondió")  # no debería alcanzarse

    def usage(self) -> dict:
        """{'used': int, 'limit': int} de caracteres del periodo actual."""
        data = self._call("GET", "/v2/usage")
        if not isinstance(data, dict):
            raise OnlineError("La respuesta de DeepL no es válida")
        return {"used": int(data.get("character_count", 0)), "limit": int(data.get("character_limit", 0))}

    def translate_lines(self, lines: list[str], target_lang: str) -> tuple[list[str], str]:
        """Traduce cada línea; devuelve (traducciones alineadas con `lines`, idioma detectado).
        Las líneas en blanco se conservan sin enviarlas (no consumen caracteres)."""
        target = normalize_lang(target_lang)
        indices = [i for i, text in enumerate(lines) if text.strip()]
        if sum(len(lines[i]) for i in indices) > MAX_CHARS:
            raise OnlineError("La letra es demasiado larga para traducirla de una vez")
        out = [""] * len(lines)
        detected = ""
        for batch in _batches(indices, lines):
            data = self._call("POST", "/v2/translate",
                              {"text": [lines[i] for i in batch], "target_lang": target})
            items = data.get("translations") if isinstance(data, dict) else None
            if not isinstance(items, list) or len(items) != len(batch):
                raise OnlineError("La respuesta de DeepL no es válida")
            for i, item in zip(batch, items, strict=True):
                out[i] = str(item.get("text", "")) if isinstance(item, dict) else ""
                if isinstance(item, dict) and not detected:
                    detected = str(item.get("detected_source_language") or "")
        return out, detected
