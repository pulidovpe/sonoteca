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
    env = {"HOME": "/Users/p"}
    expected = "/Users/p/Library/Android/sdk/platform-tools/adb"
    assert usb.find_adb(env, which=lambda name: None, is_file=lambda p: p == expected) == expected
    assert usb.find_adb({"HOME": "/h", "ANDROID_HOME": "/opt/sdk"}, which=lambda name: None,
                        is_file=lambda p: p == "/opt/sdk/platform-tools/adb") == "/opt/sdk/platform-tools/adb"
    assert usb.find_adb(env, which=lambda name: None, is_file=lambda p: False) is None
