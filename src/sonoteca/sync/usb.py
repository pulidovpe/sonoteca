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


def reverse_all(port: int, adb: str | None = None, run: Callable = subprocess.run) -> list[tuple[str, bool, str]]:
    """Aplica `adb -s <serie> reverse tcp:<puerto> tcp:<puerto>` a cada dispositivo autorizado.
    Devuelve [(serie, ok, mensaje)]. Lanza FileNotFoundError si no encuentra `adb`."""
    adb = adb or find_adb()
    if adb is None:
        raise FileNotFoundError("No se encontró adb (ni en el PATH ni en el SDK de Android).")
    results = []
    for serial in list_devices(adb, run):
        proc = run([adb, "-s", serial, "reverse", f"tcp:{port}", f"tcp:{port}"],
                   capture_output=True, text=True, timeout=20)
        results.append((serial, proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or "")).strip()))
    return results
