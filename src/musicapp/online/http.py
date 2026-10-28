"""Cliente HTTP con límite de tasa por servidor, reintentos, caché en disco y modo sin conexión."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import httpx

from musicapp.core import paths

from .settings import Settings, load, user_agent

DAY = 24 * 3600
MAX_IMAGE_BYTES = 15 * 1024 * 1024

# Segundos mínimos entre peticiones al mismo servidor. MusicBrainz permite como máximo 1 por segundo.
MIN_INTERVAL = {
    "lrclib.net": 0.5,
    "musicbrainz.org": 1.1,
    "coverartarchive.org": 0.5,
    "archive.org": 0.3,
    "wikipedia.org": 0.25,
    "wikidata.org": 0.25,
    "wikimedia.org": 0.25,
}
SERVICE_NAMES = {
    "lrclib.net": "LRCLIB",
    "musicbrainz.org": "MusicBrainz",
    "coverartarchive.org": "Cover Art Archive",
    "wikipedia.org": "Wikipedia",
    "wikidata.org": "Wikidata",
    "wikimedia.org": "Wikimedia",
}


class OfflineError(Exception):
    """Hay que consultar internet pero el modo sin conexión está activo."""


class OnlineError(Exception):
    """Falló una consulta en línea; el mensaje está pensado para mostrarse al usuario."""


def _match(host: str, table: dict):
    for suffix, value in table.items():
        if host == suffix or host.endswith("." + suffix):
            return value
    return None


class RateLimiter:
    """Reserva turnos por servidor; es seguro usarlo desde varios hilos."""

    def __init__(self, clock=time.monotonic, sleep=time.sleep) -> None:
        self._clock, self._sleep = clock, sleep
        self._next: dict[str, float] = {}
        self._lock = threading.Lock()

    def wait(self, host: str) -> None:
        interval = _match(host, MIN_INTERVAL) or 0.5
        with self._lock:
            now = self._clock()
            ready = self._next.get(host, 0.0)
            delay = max(0.0, ready - now)
            self._next[host] = max(now, ready) + interval
        if delay > 0:
            self._sleep(delay)


class HttpClient:
    def __init__(self, settings: Settings | None = None, *, transport=None,
                 cache_dir: Path | None = None, limiter: RateLimiter | None = None,
                 sleep=time.sleep, clock=time.time) -> None:
        self.settings = settings or load()
        self._limiter = limiter or RateLimiter()
        self.cache_hits = 0  # respuestas servidas desde la caché local
        self.network_requests = 0  # consultas que sí salieron a internet
        self._sleep, self._clock = sleep, clock
        self._cache_dir = Path(cache_dir) if cache_dir else paths.cache_dir() / "http"
        self._client = httpx.Client(
            headers={"User-Agent": user_agent(self.settings.contact)},
            transport=transport, follow_redirects=True,
            timeout=httpx.Timeout(20.0, connect=5.0),
        )

    def close(self) -> None:
        self._client.close()

    # ---- caché de respuestas JSON (sirve también sin conexión) ----
    def _cache_file(self, url: str, params: dict | None) -> Path:
        key = json.dumps([url, sorted((params or {}).items())], ensure_ascii=False)
        return self._cache_dir / f"{hashlib.sha1(key.encode()).hexdigest()}.json"

    def _cache_read(self, path: Path, ttl: float):
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False, None
        if self._clock() - entry.get("t", 0) > ttl:
            return False, None
        return True, entry.get("data")

    def _cache_write(self, path: Path, data) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(json.dumps({"t": self._clock(), "data": data}, ensure_ascii=False),
                           encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            pass  # sin caché la app funciona igual

    # ---- peticiones ----
    def _request(self, url: str, params: dict | None, accept: str) -> httpx.Response | None:
        host = httpx.URL(url).host
        service = _match(host, SERVICE_NAMES) or host
        for attempt in range(3):
            self._limiter.wait(host)
            try:
                response = self._client.get(url, params=params, headers={"Accept": accept})
            except httpx.TimeoutException:
                if attempt < 2:
                    continue
                raise OnlineError(f"{service} tardó demasiado en responder") from None
            except httpx.HTTPError as exc:
                raise OnlineError(f"No se pudo conectar con {service}: {exc.__class__.__name__}") from exc
            if response.status_code == 404:
                return None
            if response.status_code in (429, 503):
                if attempt < 2:
                    try:
                        delay = float(response.headers.get("Retry-After", ""))
                    except ValueError:
                        delay = 2.0 * (attempt + 1)
                    self._sleep(min(delay, 10.0))
                    continue
                raise OnlineError(f"{service} está saturado (HTTP {response.status_code}); "
                                  "inténtalo más tarde")
            if response.status_code >= 400:
                raise OnlineError(f"{service} respondió con un error (HTTP {response.status_code})")
            return response
        raise OnlineError(f"{service} no respondió")  # no debería alcanzarse

    def get_json(self, url: str, params: dict | None = None, ttl: float = 7 * DAY,
                 cache: bool = True):
        """JSON de `url`, o None si el recurso no existe (404). Usa la caché antes que la red;
        sin conexión solo responde lo que ya está en la caché. Con `cache=False` no lee ni
        escribe la caché de respuestas (p. ej. las letras se guardan en la base, no aquí)."""
        cache_file = self._cache_file(url, params)
        if cache:
            hit, data = self._cache_read(cache_file, ttl)
            if hit:
                self.cache_hits += 1
                return data
        if self.settings.offline:
            raise OfflineError("Modo sin conexión activo")
        self.network_requests += 1
        response = self._request(url, params, "application/json")
        if response is None:
            if cache:
                self._cache_write(cache_file, None)  # recuerda el 404 para no repetirlo
            return None
        try:
            data = response.json()
        except ValueError as exc:
            raise OnlineError("La respuesta del servicio no es válida") from exc
        if cache:
            self._cache_write(cache_file, data)
        return data

    def get_bytes(self, url: str, params: dict | None = None,
                  max_bytes: int = MAX_IMAGE_BYTES) -> tuple[bytes, str] | None:
        """Bytes (p. ej. una imagen) y su tipo, o None si no existe. Requiere conexión."""
        if self.settings.offline:
            raise OfflineError("Modo sin conexión activo")
        self.network_requests += 1
        response = self._request(url, params, "image/*")
        if response is None:
            return None
        if len(response.content) > max_bytes:
            raise OnlineError("La imagen descargada es demasiado grande")
        return response.content, response.headers.get("content-type", "")
