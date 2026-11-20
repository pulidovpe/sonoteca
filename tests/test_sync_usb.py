"""`adb reverse` automático del modo USB (sin adb real: se sustituye el ejecutor de procesos)."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from sonoteca.sync import usb

DEVICES = """* daemon not running; starting now at tcp:5037
* daemon started successfully
List of devices attached
729d2b6f        device
emulator-5554   device
0123456789      unauthorized
ABCDEF          offline

"""


def _runner(calls, devices_out=DEVICES, fail_for=()):
    def run(cmd, **kwargs):
        calls.append(cmd)
        if cmd[1] == "devices":
            return SimpleNamespace(stdout=devices_out, stderr="", returncode=0)
        failed = cmd[2] in fail_for
        return SimpleNamespace(stdout="", stderr="error: closed" if failed else "", returncode=1 if failed else 0)
    return run


def test_only_authorized_devices_are_listed_ignoring_daemon_noise():
    assert usb.list_devices("adb", _runner([])) == ["729d2b6f", "emulator-5554"]


def test_no_devices_lists_nothing():
    assert usb.list_devices("adb", _runner([], "List of devices attached\n\n")) == []


def test_reverse_is_applied_to_every_authorized_device_with_the_right_arguments():
    calls = []
    results = usb.reverse_all(8765, adb="/sdk/adb", run=_runner(calls))
    assert results == [("729d2b6f", True, ""), ("emulator-5554", True, "")]
    assert ["/sdk/adb", "-s", "729d2b6f", "reverse", "tcp:8765", "tcp:8765"] in calls
    assert ["/sdk/adb", "-s", "emulator-5554", "reverse", "tcp:8765", "tcp:8765"] in calls


def test_a_failing_device_is_reported_without_stopping_the_others():
    results = usb.reverse_all(8765, adb="adb", run=_runner([], fail_for=("729d2b6f",)))
    assert results[0][:2] == ("729d2b6f", False) and "closed" in results[0][2]
    assert results[1][:2] == ("emulator-5554", True)


def test_reverse_without_adb_raises_a_clear_error(monkeypatch):
    monkeypatch.setattr(usb, "find_adb", lambda *a, **k: None)
    with pytest.raises(FileNotFoundError, match="adb"):
        usb.reverse_all(8765)


def test_find_adb_prefers_path_then_sdk_locations():
    assert usb.find_adb({}, which=lambda name: "/usr/bin/adb") == "/usr/bin/adb"
    exe = "adb.exe" if usb.sys.platform == "win32" else "adb"     # find_adb arma las rutas con Path y adb.exe en Windows
    env = {"HOME": "/Users/p"}
    expected = str(usb.Path("/Users/p") / "Library" / "Android" / "sdk" / "platform-tools" / exe)
    assert usb.find_adb(env, which=lambda name: None, is_file=lambda p: p == expected) == expected
    sdk_adb = str(usb.Path("/opt/sdk") / "platform-tools" / exe)
    assert usb.find_adb({"HOME": "/h", "ANDROID_HOME": "/opt/sdk"}, which=lambda name: None,
                        is_file=lambda p: p == sdk_adb) == sdk_adb
    assert usb.find_adb(env, which=lambda name: None, is_file=lambda p: False) is None


class FakeAdb:
    """adb simulado con estado: móviles conectados y túneles activos (se pierden como en la vida real)."""

    def __init__(self, port=8765):
        self.port, self.devices, self.tunnels, self.fail, self.list_fails, self.calls = port, [], set(), set(), False, []

    def __call__(self, cmd, **kwargs):
        self.calls.append(cmd)
        if cmd[1] == "devices":
            out = "List of devices attached\n" + "".join(f"{serial}\tdevice\n" for serial in self.devices)
            return SimpleNamespace(stdout=out, stderr="", returncode=0)
        serial = cmd[2]
        if cmd[4] == "--list":
            if self.list_fails:
                return SimpleNamespace(stdout="", stderr="error", returncode=1)
            lines = "".join(f"host-1 tcp:{port} tcp:{port}\n" for s, port in self.tunnels if s == serial)
            return SimpleNamespace(stdout=lines, stderr="", returncode=0)
        if serial in self.fail:
            return SimpleNamespace(stdout="", stderr="error: closed", returncode=1)
        self.tunnels.add((serial, self.port))
        return SimpleNamespace(stdout="", stderr="", returncode=0)

    def reverse_calls(self):
        return [c for c in self.calls if len(c) > 4 and c[3] == "reverse" and c[4].startswith("tcp:")]


def test_watcher_does_nothing_when_the_tunnel_is_already_there():
    adb = FakeAdb()
    adb.devices, adb.tunnels = ["729d2b6f"], {("729d2b6f", 8765)}
    watcher = usb.UsbWatcher(8765, "adb", adb)
    assert watcher.step() == [] and watcher.step() == []
    assert adb.reverse_calls() == []


def test_watcher_rebuilds_the_tunnel_when_the_phone_is_plugged_back_in():
    adb = FakeAdb()
    adb.devices, adb.tunnels = ["729d2b6f"], {("729d2b6f", 8765)}
    watcher = usb.UsbWatcher(8765, "adb", adb)
    watcher.step()
    adb.devices, adb.tunnels = [], set()          # se desconecta el cable: el túnel se pierde
    assert watcher.step() == []
    adb.devices = ["729d2b6f"]                    # se vuelve a conectar
    assert watcher.step() == [("729d2b6f", True, "")]
    assert adb.reverse_calls() == [["adb", "-s", "729d2b6f", "reverse", "tcp:8765", "tcp:8765"]]
    assert watcher.step() == []                   # ya está: no se repite


def test_watcher_first_step_fixes_a_phone_that_has_no_tunnel():
    adb = FakeAdb()
    adb.devices = ["729d2b6f"]
    assert usb.UsbWatcher(8765, "adb", adb).step() == [("729d2b6f", True, "")]


def test_watcher_restores_a_tunnel_lost_while_still_connected():
    adb = FakeAdb()
    adb.devices, adb.tunnels = ["729d2b6f"], {("729d2b6f", 8765)}
    watcher = usb.UsbWatcher(8765, "adb", adb)
    watcher.step()
    adb.tunnels.clear()                           # adb reiniciado: el móvil sigue conectado pero sin túnel
    assert watcher.step() == [("729d2b6f", True, "")]


def test_watcher_reports_a_failure_once_and_recovers():
    adb = FakeAdb()
    adb.devices, adb.fail = ["729d2b6f"], {"729d2b6f"}
    watcher = usb.UsbWatcher(8765, "adb", adb)
    first = watcher.step()
    assert first[0][:2] == ("729d2b6f", False) and "closed" in first[0][2]
    assert watcher.step() == [] and watcher.step() == []   # sigue fallando: no se repite el aviso
    adb.fail = set()
    assert watcher.step() == [("729d2b6f", True, "")]


def test_watcher_does_not_act_when_adb_cannot_list_tunnels():
    adb = FakeAdb()
    adb.devices, adb.list_fails = ["729d2b6f"], True
    watcher = usb.UsbWatcher(8765, "adb", adb)
    adb.tunnels = {("729d2b6f", 8765)}
    watcher.step()
    assert watcher.step() == [] and adb.reverse_calls() == []
