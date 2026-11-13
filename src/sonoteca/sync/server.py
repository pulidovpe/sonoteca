"""Servidor HTTPS de sincronización (biblioteca de solo lectura + recepción de listas). Protocolo: docs/SYNC.md.

Solo biblioteca estándar más `cryptography` (certificado). Cada petición abre su propia conexión a SQLite."""
from __future__ import annotations

import json
import os
import re
import socket
import ssl
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

from ..core import content_hash
from ..core.db import connect
from . import API_VERSION, DEFAULT_PORT, merge, pairing, tls
from .manifest import build_manifest

MAX_BODY = 2 * 1024 * 1024
CHUNK = 256 * 1024
_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_ROUTE_TRACK = re.compile(rf"^/v1/tracks/({_UUID})/(file|cover|lyrics)$")
_ROUTE_PLAYLIST = re.compile(rf"^/v1/playlists/({_UUID})$")
_MIME = {".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".aac": "audio/aac", ".flac": "audio/flac",
         ".ogg": "audio/ogg", ".opus": "audio/ogg", ".wav": "audio/wav"}

CoverProvider = Callable[["object", int], "tuple[bytes, str] | None"]


def default_cover_provider(conn, track_id: int) -> tuple[bytes, str] | None:
    """Portada de la pista: la del álbum con el orden de la app (embebida, carpeta, descargada). Importa `covers`
    (y con él mutagen) solo si se pide una portada."""
    from ..core import covers

    row = conn.execute("SELECT album_id FROM tracks WHERE id = ?", (track_id,)).fetchone()
    if row is None:
        return None
    source = covers.album_cover_source(conn, row["album_id"])
    if source is None:
        return None
    kind, path = source
    data = covers.extract_embedded_cover(path) if kind == "embedded" else path.read_bytes()
    if not data:
        return None
    return data, "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"


def lan_addresses() -> list[str]:
    """Direcciones IPv4 probables de este equipo en la red local (sin enviar nada: solo consulta la ruta)."""
    found: list[str] = []
    for target in ("10.255.255.255", "192.168.255.255", "172.31.255.255"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((target, 1))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127.") and ip not in found:
                found.append(ip)
        except OSError:
            pass
        finally:
            sock.close()
    return found


class _Hasher:
    """Calcula en segundo plano las huellas que falten (un solo hilo a la vez)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def kick(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(target=self._run, name="sonoteca-hash", daemon=True)
            self._thread.start()

    def _run(self) -> None:
        conn = connect(self._db_path)
        try:
            content_hash.hash_missing(conn)
        finally:
            conn.close()

    def join(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread:
            thread.join(timeout)


class SyncServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], db_path: str, tls_dir: Path | None = None,
                 cover_provider: CoverProvider = default_cover_provider,
                 log: Callable[[str], None] | None = None, name: str | None = None) -> None:
        super().__init__(address, _Handler)
        self.db_path = str(db_path)
        self.pairing = pairing.PairingState()
        self.cover_provider = cover_provider
        self.log = log or (lambda message: None)
        self.server_name = name or socket.gethostname()
        self.hasher = _Hasher(self.db_path)
        cert, key, self.fingerprint = tls.ensure_certificate(tls_dir)
        # el apretón de manos TLS ocurre en el hilo de cada conexión, no en el que acepta (un cliente lento no bloquea)
        self.socket = tls.server_context(cert, key).wrap_socket(
            self.socket, server_side=True, do_handshake_on_connect=False)

    @property
    def port(self) -> int:
        return self.server_address[1]

    def pairing_url(self, host: str, code: str) -> str:
        query = urlencode({"host": host, "port": self.port, "fp": self.fingerprint, "code": code})
        return f"sonoteca-sync://pair?{query}"

    def handle_error(self, request, client_address) -> None:   # noqa: ARG002
        # apretones TLS fallidos, clientes que cortan, etc.: no son errores del servidor
        import sys

        exc = sys.exc_info()[1]
        if isinstance(exc, (ssl.SSLError, ConnectionError, TimeoutError, OSError)):
            return
        super().handle_error(request, client_address)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    timeout = 30
    server: SyncServer

    def log_message(self, format: str, *args) -> None:   # noqa: A002
        self.server.log(f"{self.address_string()} {format % args}")

    # --- respuestas -------------------------------------------------------------------------------------------------
    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY:
            self._error(400, "cuerpo ausente o demasiado grande")
            return None
        try:
            data = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, UnicodeDecodeError):
            self._error(400, "JSON inválido")
            return None
        if not isinstance(data, dict):
            self._error(400, "se esperaba un objeto JSON")
            return None
        return data

    def _authenticated(self, conn) -> bool:
        header = self.headers.get("Authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        if pairing.authenticate(conn, token) is None:
            self._error(401, "token inválido; vuelve a emparejar el dispositivo")
            return False
        return True

    # --- enrutado ---------------------------------------------------------------------------------------------------
    def do_GET(self) -> None:   # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/v1/ping":
            self._json(200, {"app": "sonoteca", "api": API_VERSION, "name": self.server.server_name})
            return
        conn = connect(self.server.db_path)
        try:
            if not self._authenticated(conn):
                return
            if path == "/v1/manifest":
                manifest = build_manifest(conn)
                if manifest["pending_hash"]:
                    self.server.hasher.kick()
                self._json(200, manifest)
                return
            match = _ROUTE_TRACK.match(path)
            if match:
                self._track_resource(conn, match.group(1), match.group(2))
                return
            self._error(404, "ruta desconocida")
        finally:
            conn.close()

    def do_POST(self) -> None:   # noqa: N802
        if self.path.split("?", 1)[0] != "/v1/pair":
            self._error(404, "ruta desconocida")
            return
        body = self._read_json()
        if body is None:
            return
        device_id, name = body.get("device_id"), body.get("device_name")
        if not isinstance(device_id, str) or not 8 <= len(device_id) <= 64 \
                or not isinstance(name, str) or not name.strip():
            self._error(400, "faltan device_id (8 a 64 caracteres) y device_name")
            return
        if not self.server.pairing.consume(body.get("code")):
            self._error(403, "código de emparejamiento inválido o caducado")
            return
        conn = connect(self.server.db_path)
        try:
            token = pairing.register_device(conn, device_id, name.strip()[:80])
        finally:
            conn.close()
        self.server.log(f"dispositivo emparejado: {name.strip()[:80]}")
        self._json(200, {"token": token, "fingerprint": self.server.fingerprint, "api": API_VERSION})

    def do_PUT(self) -> None:   # noqa: N802
        match = _ROUTE_PLAYLIST.match(self.path.split("?", 1)[0])
        if not match:
            self._error(404, "ruta desconocida")
            return
        conn = connect(self.server.db_path)
        try:
            if not self._authenticated(conn):
                return
            body = self._read_json()
            if body is None:
                return
            try:
                self._json(200, merge.apply_playlist(conn, match.group(1), body))
            except merge.MergeError as exc:
                self._error(400, str(exc))
            except merge.Conflict as exc:
                self._error(409, str(exc))
        finally:
            conn.close()

    def do_DELETE(self) -> None:   # noqa: N802
        match = _ROUTE_PLAYLIST.match(self.path.split("?", 1)[0])
        if not match:
            self._error(404, "ruta desconocida")
            return
        conn = connect(self.server.db_path)
        try:
            if not self._authenticated(conn):
                return
            body = self._read_json()
            if body is None:
                return
            try:
                self._json(200, merge.delete_playlist(conn, match.group(1), body.get("deleted_at")))
            except merge.MergeError as exc:
                self._error(400, str(exc))
            except merge.Conflict as exc:
                self._error(409, str(exc))
        finally:
            conn.close()

    # --- recursos de una pista --------------------------------------------------------------------------------------
    def _track_resource(self, conn, track_uuid: str, what: str) -> None:
        row = conn.execute("SELECT t.id, t.file_id, f.path, f.format FROM tracks t JOIN files f ON f.id = t.file_id"
                           " WHERE t.uuid = ? AND f.kind = 'audio'", (track_uuid,)).fetchone()
        if row is None:
            self._error(404, "pista desconocida")
            return
        if what == "file":
            self._send_file(conn, row)
        elif what == "cover":
            found = self.server.cover_provider(conn, row["id"])
            if found is None:
                self._error(404, "la pista no tiene portada")
                return
            data, mime = found
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, max-age=3600")
            self.end_headers()
            self.wfile.write(data)
        else:
            lyr = conn.execute("SELECT synced_lrc, original_text, language, instrumental FROM lyrics"
                               " WHERE track_id = ?", (row["id"],)).fetchone()
            if lyr is None or lyr["instrumental"] or not ((lyr["synced_lrc"] or "") or (lyr["original_text"] or "")):
                self._error(404, "la pista no tiene letra")
                return
            self._json(200, {"synced_lrc": lyr["synced_lrc"] or "", "original_text": lyr["original_text"] or "",
                             "language": lyr["language"] or ""})

    def _send_file(self, conn, row) -> None:
        digest = content_hash.ensure_hash(conn, row["file_id"])   # comprueba el archivo REAL (stat) antes de servirlo
        if digest is None:
            self._error(410, "el archivo ya no está disponible")
            return
        path = row["path"]
        try:
            size = os.stat(path).st_size
        except OSError:
            self._error(410, "el archivo ya no está disponible")
            return
        start, end = 0, size - 1
        status = 200
        range_header = self.headers.get("Range")
        if range_header:
            parsed = _parse_range(range_header, size)
            if parsed is None:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            start, end = parsed
            status = 206
        length = end - start + 1
        mime = _MIME.get(Path(path).suffix.lower(), "application/octet-stream")
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(length))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("ETag", f'"{digest}"')
        self.send_header("X-Sonoteca-Hash", digest)
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        remaining = length
        try:
            with open(path, "rb") as handle:
                handle.seek(start)
                while remaining > 0:
                    chunk = handle.read(min(CHUNK, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionError):
            self.close_connection = True
        if remaining > 0:   # el archivo se acortó a mitad de envío: la conexión no se puede reutilizar
            self.close_connection = True


def _parse_range(header: str, size: int) -> tuple[int, int] | None:
    """`bytes=a-b`, `bytes=a-` o `bytes=-n` -> (inicio, fin) inclusivos; None si no es satisfacible (un solo rango)."""
    match = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if not match or size <= 0:
        return None
    first, last = match.groups()
    if first == "" and last == "":
        return None
    if first == "":
        count = int(last)
        if count == 0:
            return None
        return max(0, size - count), size - 1
    start = int(first)
    end = size - 1 if last == "" else min(int(last), size - 1)
    if start >= size or end < start:
        return None
    return start, end


def make_server(db_path: str | Path, host: str = "0.0.0.0", port: int = DEFAULT_PORT, tls_dir: Path | None = None,
                cover_provider: CoverProvider = default_cover_provider,
                log: Callable[[str], None] | None = None) -> SyncServer:
    return SyncServer((host, port), str(db_path), tls_dir=tls_dir, cover_provider=cover_provider, log=log)
