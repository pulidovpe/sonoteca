"""Informe de tamaño del paquete (packaging/size_report.py)."""
import importlib.util
import json
import os
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("size_report", Path(__file__).resolve().parents[1] / "packaging" / "size_report.py")
size_report = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(size_report)
MB = size_report.MB


def _make(root, name, mb):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0" * int(mb * MB))


def test_categories():
    c = size_report.categorize
    assert c("Contents/Frameworks/PySide6/Qt/lib/libavcodec.61.dylib") == "FFmpeg (libav*, libsw*)"
    assert c("sonoteca/_internal/PySide6/avformat-61.dll") == "FFmpeg (libav*, libsw*)"
    assert c("PySide6/Qt/plugins/multimedia/libffmpegmediaplugin.dylib") == "Qt Multimedia"
    assert c("PySide6/Qt/qml/QtQuick/Controls/Basic/Button.qml") == "QML de Qt"
    assert c("PySide6/Qt/plugins/platforms/libqcocoa.dylib") == "Plugins de Qt"
    assert c("AppKit/_AppKit.cpython-312-darwin.so") == "PyObjC (macOS)"
    assert c("PySide6/Qt/lib/QtCore.framework/Versions/A/QtCore") == "Bibliotecas de Qt"
    assert c("PySide6/QtGui.abi3.so") == "PySide6 y shiboken"
    assert c("libpython3.12.dylib") == "Python (intérprete y stdlib)"
    assert c("httpx/_client.pyc") == size_report.OTHER


def test_scan_counts_real_files_once_and_ignores_symlinks(tmp_path):
    _make(tmp_path, "a/real.bin", 1)
    os.symlink(tmp_path / "a" / "real.bin", tmp_path / "a" / "link.bin")
    os.link(tmp_path / "a" / "real.bin", tmp_path / "a" / "hard.bin")
    files = size_report.scan(tmp_path)
    assert sum(files.values()) == MB and len(files) == 1


def test_report_compare_and_budget(tmp_path, capsys):
    old = tmp_path / "old"
    new = tmp_path / "new"
    _make(old, "PySide6/Qt/lib/libavcodec.61.dylib", 10)
    _make(old, "PySide6/Qt/qml/QtQuick/x.qml", 1)
    _make(new, "PySide6/Qt/lib/libavcodec.61.dylib", 15)
    _make(new, "PySide6/Qt/lib/libavfilter.10.dylib", 3)
    _make(new, "PySide6/Qt/qml/QtQuick/x.qml", 1)
    saved = tmp_path / "old.json"
    assert size_report.main([str(old), "--save", str(saved)]) == 0
    data = json.loads(saved.read_text(encoding="utf-8"))
    assert data["total"] == 11 * MB and data["categories"]["FFmpeg (libav*, libsw*)"] == 10 * MB
    capsys.readouterr()
    assert size_report.main([str(new), "--compare", str(saved), "--budget-mb", "10"]) == 3          # 19 MB > 10 MB
    out = capsys.readouterr()
    assert "+8.0 MB" in out.out and "FFmpeg" in out.out and "libavfilter.10.dylib  (nuevo)" in out.out
    assert "AVISO" in out.err
    assert size_report.main([str(tmp_path / "no-existe")]) == 2
