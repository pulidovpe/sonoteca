"""Comprueba que un paquete (dist/...) NO lleva datos personales: bases de datos, ajustes, letras, portadas
ni fotos de artistas descargadas. Uso: python packaging/check_bundle.py dist/Sonoteca.app  (código 1 si hay algo)."""
from __future__ import annotations

import sys
from pathlib import Path

FORBIDDEN_SUFFIXES = (".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".lrc", ".sonoteca")
FORBIDDEN_NAMES = {"settings.json", "library.db", "manifest.tsv"}
FORBIDDEN_DIRS = {"covers", "artists", "backups", "pending_import"}   # carpetas de datos del usuario


def find_personal_data(root: Path) -> list[str]:
    found = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        name = path.name.lower()
        parts = {p.lower() for p in rel.parts[:-1]}
        if name.endswith(FORBIDDEN_SUFFIXES) or name in FORBIDDEN_NAMES or (parts & FORBIDDEN_DIRS and "qml" not in parts):
            found.append(str(rel))
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    root = Path(argv[1])
    if not root.exists():
        print(f"No existe: {root}")
        return 2
    found = find_personal_data(root)
    if found:
        print(f"ERROR: el paquete incluye {len(found)} archivos que parecen datos personales:")
        for item in found[:20]:
            print("  ", item)
        return 1
    print("OK: el paquete no incluye bases de datos, ajustes, letras ni portadas descargadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
