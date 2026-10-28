#!/usr/bin/env bash
# Construye musicapp.app (Apple Silicon o Intel, según tu Mac) y un .zip listo para compartir.
# Uso: ./packaging/build_mac.sh        (desde cualquier carpeta; requiere Python 3.11+ y conexión a internet)
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
"$PY" -m venv .venv-build
# shellcheck disable=SC1091
source .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[ui,build]"

pyinstaller packaging/musicapp.spec --noconfirm --clean

VERSION="$(python -c 'import musicapp; print(musicapp.__version__)')"
ARCH="$(uname -m)"
OUT="dist/musicapp-${VERSION}-alpha-macos-${ARCH}.zip"
rm -f "$OUT"
ditto -c -k --keepParent dist/musicapp.app "$OUT"
echo
echo "Listo: dist/musicapp.app"
echo "Zip:   $OUT"
echo "Primera vez en otra Mac (la app no está firmada): clic derecho > Abrir, o"
echo "  xattr -dr com.apple.quarantine /ruta/a/musicapp.app"
