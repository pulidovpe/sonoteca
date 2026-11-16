"""Emparejamiento de dispositivos: código de 6 dígitos de un solo uso -> token de acceso.

El token se entrega UNA vez al móvil; en la base solo queda su SHA-256 (`sync_devices.token_hash`)."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import threading
import time

from .manifest import now_iso

CODE_TTL = 300.0       # el código vale 5 minutos
MAX_ATTEMPTS = 5       # tras 5 fallos el código se invalida


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class PairingState:
    """Código de emparejamiento vigente (en memoria: no se guarda en disco)."""

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._code: str | None = None
        self._expires = 0.0
        self._attempts = 0

    def new_code(self) -> str:
        with self._lock:
            self._code = f"{secrets.randbelow(1_000_000):06d}"
            self._expires = self._clock() + CODE_TTL
            self._attempts = 0
            return self._code

    def consume(self, candidate: object) -> bool:
        """True si `candidate` es el código vigente (y lo gasta). Los fallos cuentan: a los 5 se invalida."""
        with self._lock:
            if self._code is None or self._clock() > self._expires:
                self._code = None
                return False
            self._attempts += 1
            ok = isinstance(candidate, str) and hmac.compare_digest(candidate, self._code)
            if ok or self._attempts >= MAX_ATTEMPTS:
                self._code = None
            return ok


def register_device(conn: sqlite3.Connection, device_id: str, name: str) -> str:
    """Da de alta (o re-empareja) un dispositivo y devuelve su token nuevo."""
    token = secrets.token_urlsafe(32)
    with conn:
        conn.execute("DELETE FROM sync_devices WHERE device_id = ?", (device_id,))
        conn.execute("INSERT INTO sync_devices (device_id, name, token_hash, created_at) VALUES (?, ?, ?, ?)",
                     (device_id, name, hash_token(token), now_iso()))
    return token


def authenticate(conn: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    """Dispositivo dueño del token, o None. Anota la última conexión."""
    if not token:
        return None
    row = conn.execute("SELECT device_id, name FROM sync_devices WHERE token_hash = ?",
                       (hash_token(token),)).fetchone()
    if row is not None:
        with conn:
            conn.execute("UPDATE sync_devices SET last_seen = ? WHERE device_id = ?", (now_iso(), row["device_id"]))
    return row


def list_devices(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT device_id, name, created_at, last_seen FROM sync_devices ORDER BY created_at").fetchall()


def revoke(conn: sqlite3.Connection, device_id: str) -> bool:
    with conn:
        return conn.execute("DELETE FROM sync_devices WHERE device_id = ?", (device_id,)).rowcount > 0
