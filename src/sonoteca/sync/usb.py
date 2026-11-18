"""Ayuda para el modo USB: `adb reverse` hacia el escritorio.

El redireccionamiento (`adb reverse`) NO es permanente: se pierde al reiniciar adb (p. ej. al reiniciar Android Studio) o al
reconectar el cable, y entonces el móvil falla con «No se pudo conectar». `sonoteca sync-serve --solo-usb` lo aplica solo.
Solo biblioteca estándar; `run`, `which` e `is_file` se pueden sustituir en las pruebas."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from pathlib import Path


def find_adb(env: Mapping[str, str] | None = None, which: Callable[[str], str | None] = shutil.which,
             is_file: Callable[[str], bool] = os.path.isfile) -> str | None:
    """Ruta de `adb`: primero el PATH y después las ubicaciones habituales del SDK de Android. None si no aparece."""
    env = os.environ if env is None else env
    found = which("adb")
    if found:
        return found
    home = Path(env.get("HOME") or env.get("USERPROFILE") or "~").expanduser()
    roots = [env.get("ANDROID_HOME"), env.get("ANDROID_SDK_ROOT"), str(home / "Library" / "Android" / "sdk"),
             str(home / "Android" / "Sdk")]
    if env.get("LOCALAPPDATA"):
        roots.append(str(Path(env["LOCALAPPDATA"]) / "Android" / "Sdk"))
    exe = "adb.exe" if sys.platform == "win32" else "adb"
    for root in roots:
        if root:
            candidate = str(Path(root) / "platform-tools" / exe)
            if is_file(candidate):
                return candidate
    return None


def list_devices(adb: str, run: Callable = subprocess.run) -> list[str]:
    """Series de los dispositivos AUTORIZADOS (estado `device`; se ignoran `unauthorized` y `offline`)."""
    out = run([adb, "devices"], capture_output=True, text=True, timeout=20).stdout or ""
    lines = out.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("List of devices")), -1) + 1
    serials = []
    for line in lines[start:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            serials.append(parts[0])
    return serials


def _reverse_one(adb: str, serial: str, port: int, run: Callable = subprocess.run) -> tuple[str, bool, str]:
    proc = run([adb, "-s", serial, "reverse", f"tcp:{port}", f"tcp:{port}"], capture_output=True, text=True, timeout=20)
    return serial, proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or "")).strip()


def reverse_all(port: int, adb: str | None = None, run: Callable = subprocess.run) -> list[tuple[str, bool, str]]:
    """Aplica `adb -s <serie> reverse tcp:<puerto> tcp:<puerto>` a cada dispositivo autorizado.
    Devuelve [(serie, ok, mensaje)]. Lanza FileNotFoundError si no encuentra `adb`."""
    adb = adb or find_adb()
    if adb is None:
        raise FileNotFoundError("No se encontró adb (ni en el PATH ni en el SDK de Android).")
    return [_reverse_one(adb, serial, port, run) for serial in list_devices(adb, run)]


def tunnel_state(adb: str, serial: str, port: int, run: Callable = subprocess.run) -> bool | None:
    """¿Tiene ese móvil el túnel del puerto? True/False según `adb reverse --list`; None si adb no lo pudo decir (no se actúa)."""
    proc = run([adb, "-s", serial, "reverse", "--list"], capture_output=True, text=True, timeout=20)
    if proc.returncode != 0:
        return None
    return f"tcp:{port}" in (proc.stdout or "")


class UsbWatcher:
    """Rehace `adb reverse` solo cuando un móvil se conecta de nuevo o pierde el túnel (cable, reinicio de adb/Android Studio).

    `step()` es un sondeo: devuelve [(serie, ok, mensaje)] solo de lo que HIZO. El primer sondeo solo toma nota de los móviles ya
    conectados (el arranque ya aplicó el túnel) y actúa únicamente si alguno no lo tiene. Un fallo se informa una sola vez por móvil
    hasta que vuelva a funcionar, para no repetirlo en cada sondeo.
    """

    def __init__(self, port: int, adb: str, run: Callable = subprocess.run) -> None:
        self.port, self.adb, self.run = port, adb, run
        self._known: set[str] | None = None
        self._failing: set[str] = set()

    def step(self) -> list[tuple[str, bool, str]]:
        serials = list_devices(self.adb, self.run)
        first = self._known is None
        known = self._known or set()
        events: list[tuple[str, bool, str]] = []
        for serial in serials:
            new = serial not in known and not first
            if not new and tunnel_state(self.adb, serial, self.port, self.run) is not False:
                continue
            serial, ok, message = _reverse_one(self.adb, serial, self.port, self.run)
            if ok:
                self._failing.discard(serial)
                events.append((serial, True, message))
            elif serial not in self._failing:
                self._failing.add(serial)
                events.append((serial, False, message))
        self._known = set(serials)
        self._failing &= self._known
        return events
