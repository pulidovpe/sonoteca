"""Informe de tamaño de un paquete (dist/...): qué pesa y qué ha crecido desde la compilación anterior.

Uso:
  python packaging/size_report.py dist/Sonoteca.app [--top 20] [--save dist/size-report.json]
                                  [--compare dist/size-report.prev.json] [--budget-mb 250]

Agrupa los archivos por categoría (FFmpeg, Qt Multimedia, QML y plugins de Qt, PyObjC, Python…), muestra los más pesados y, con
`--compare`, qué categorías, paquetes (versión de PySide6…) y archivos cambiaron entre dos compilaciones. Mide tamaño sin comprimir
(bytes de cada archivo; los enlaces simbólicos y los enlaces duros se cuentan una sola vez). Código de salida 3 si supera `--budget-mb`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from importlib import metadata
from pathlib import Path

MB = 1024 * 1024
PACKAGES = ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "pyobjc-core", "pyobjc-framework-MediaPlayer",
            "pyobjc-framework-Cocoa", "httpx", "keyring", "mutagen", "pyinstaller")

# (nombre, expresión sobre la ruta relativa en minúsculas y con «/»); gana la primera que coincida
FFMPEG = r"(^|/)(lib)?(avcodec|avformat|avutil|avfilter|avdevice|swscale|swresample|postproc)[-.\d]"
PYOBJC_NAMES = ("objc|appkit|foundation|mediaplayer|avfoundation|cocoa|coredata|corefoundation|quartz|coreaudio|coremedia|"
                "corevideo|coretext|coreimage|corelocation|corebluetooth|avkit|security|systemconfiguration")
CATEGORIES: list[tuple[str, str]] = [
    ("FFmpeg (libav*, libsw*)", FFMPEG),
    ("Qt Multimedia", r"qtmultimedia|qt6multimedia|plugins/multimedia"),
    ("QML de Qt", r"(^|/)qml/"),
    ("Plugins de Qt", r"(^|/)plugins/"),
    ("PyObjC (macOS)", rf"pyobjc|(^|/)({PYOBJC_NAMES})(/|\.|$)"),
    ("Bibliotecas de Qt", r"qt6[a-z0-9]*|(^|/)qt[a-z0-9]+\.framework|(^|/)qt[a-z0-9]+\.(dll|so|dylib)"),
    ("PySide6 y shiboken", r"pyside6|shiboken"),
    ("Python (intérprete y stdlib)", r"libpython|python3|lib-dynload|base_library|(^|/)python[0-9.]*(/|$)"),
]
OTHER = "Otros (httpx, keyring, mutagen, datos…)"


def categorize(rel: str) -> str:
    path = rel.replace("\\", "/").lower()
    for name, pattern in CATEGORIES:
        if re.search(pattern, path):
            return name
    return OTHER


def scan(root: Path) -> dict[str, int]:
    """{ruta relativa: bytes} de los archivos reales (sin enlaces simbólicos; los enlaces duros, una vez)."""
    files: dict[str, int] = {}
    seen: set[tuple[int, int]] = set()
    for dirpath, _dirs, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(dirpath) / name
            try:
                st = path.lstat()
            except OSError:
                continue
            if path.is_symlink() or not path.is_file():
                continue
            key = (st.st_dev, st.st_ino)
            if st.st_ino and key in seen:
                continue
            seen.add(key)
            files[str(path.relative_to(root)).replace("\\", "/")] = st.st_size
    return files


def totals(files: dict[str, int]) -> dict[str, int]:
    out: dict[str, int] = {}
    for rel, size in files.items():
        out[categorize(rel)] = out.get(categorize(rel), 0) + size
    return out


def package_versions() -> dict[str, str]:
    found = {}
    for name in PACKAGES:
        try:
            found[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return found


def _mb(size: float) -> str:
    return f"{size / MB:8.1f} MB"


def format_report(files: dict[str, int], packages: dict[str, str], top: int = 20, previous: dict | None = None) -> str:
    total = sum(files.values())
    cats = totals(files)
    lines = [f"Tamaño total: {total / MB:.1f} MB en {len(files)} archivos", "", "Por categoría:"]
    for name, size in sorted(cats.items(), key=lambda kv: -kv[1]):
        lines.append(f"  {_mb(size)}  {size / total * 100:5.1f} %  {name}")
    lines += ["", f"Los {top} archivos más pesados:"]
    for rel, size in sorted(files.items(), key=lambda kv: -kv[1])[:top]:
        lines.append(f"  {_mb(size)}  {rel}")
    if packages:
        lines += ["", "Paquetes: " + ", ".join(f"{k} {v}" for k, v in sorted(packages.items()))]
    if previous:
        old_total = previous.get("total", 0)
        lines += ["", f"Frente a la compilación anterior: {(total - old_total) / MB:+.1f} MB ({old_total / MB:.1f} → {total / MB:.1f} MB)"]
        old_cats = previous.get("categories", {})
        for name in sorted(set(cats) | set(old_cats), key=lambda n: -abs(cats.get(n, 0) - old_cats.get(n, 0))):
            delta = cats.get(name, 0) - old_cats.get(name, 0)
            if abs(delta) >= 0.05 * MB:
                lines.append(f"  {delta / MB:+8.1f} MB  {name}")
        old_pkgs = previous.get("packages", {})
        changed = [f"{n}: {old_pkgs.get(n, '—')} → {packages.get(n, '—')}" for n in sorted(set(packages) | set(old_pkgs))
                   if packages.get(n) != old_pkgs.get(n)]
        if changed:
            lines += ["", "Versiones que cambiaron: " + "; ".join(changed)]
        old_files = previous.get("files", {})
        growth = sorted(((size - old_files.get(rel, 0), rel) for rel, size in files.items()), reverse=True)[:10]
        growth = [(d, rel) for d, rel in growth if d >= 0.05 * MB]
        if growth:
            lines += ["", "Archivos que más crecieron o son nuevos:"]
            lines += [f"  {d / MB:+8.1f} MB  {rel}{'  (nuevo)' if rel not in old_files else ''}" for d, rel in growth]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Informe de tamaño de un paquete de Sonoteca")
    parser.add_argument("root", type=Path, help="dist/Sonoteca.app o dist/sonoteca")
    parser.add_argument("--top", type=int, default=20)
    parser.add_argument("--save", type=Path, help="guarda el informe (JSON) para compararlo después")
    parser.add_argument("--compare", type=Path, help="informe JSON de una compilación anterior")
    parser.add_argument("--budget-mb", type=float, help="avisa (código 3) si el paquete supera este tamaño")
    args = parser.parse_args(argv)
    if not args.root.exists():
        print(f"No existe: {args.root}", file=sys.stderr)
        return 2
    files = scan(args.root)
    packages = package_versions()
    previous = None
    if args.compare and args.compare.exists():
        try:
            previous = json.loads(args.compare.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            previous = None
    print(format_report(files, packages, args.top, previous))
    total = sum(files.values())
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        args.save.write_text(json.dumps({"total": total, "categories": totals(files), "packages": packages, "files": files},
                                        ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    if args.budget_mb and total > args.budget_mb * MB:
        print(f"\nAVISO: supera el presupuesto de {args.budget_mb:.0f} MB ({total / MB:.1f} MB).", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
