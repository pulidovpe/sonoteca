#!/usr/bin/env bash
# Construye Sonoteca.app (arquitectura de tu Mac) y un .zip listo para compartir.
# Uso: ./packaging/build_mac.sh        (desde cualquier carpeta; requiere Python 3.11+ e internet)
#      SONOTECA_NO_PRUNE=1 ./packaging/build_mac.sh   -> sin podar módulos de Qt (si la poda diera problemas)
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
"$PY" -m venv .venv-build
# shellcheck disable=SC1091
source .venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[ui,build]"

pyinstaller packaging/sonoteca.spec --noconfirm --clean

APP="dist/Sonoteca.app"
echo
echo "== Prueba de humo (abre la app sin pantalla ~5 s; datos temporales) =="
TMP="$(mktemp -d)"
if SONOTECA_SELFTEST=1 QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
   SONOTECA_DATA_DIR="$TMP/data" SONOTECA_CACHE_DIR="$TMP/cache" "$APP/Contents/MacOS/sonoteca"; then
  echo "OK: la interfaz carga."
else
  echo "FALLO: la app empaquetada no arranca. Prueba con SONOTECA_NO_PRUNE=1 y envía el error." >&2
fi
rm -rf "$TMP"

echo
echo "== Datos personales en el paquete =="
python packaging/check_bundle.py "$APP" || echo "REVISA: el paquete no debe llevar datos personales." >&2

echo
echo "== Tamaño =="
du -sh "$APP"
echo "Carpetas más pesadas:"
du -sk "$APP"/Contents/*/* "$APP"/Contents/*/*/* 2>/dev/null | sort -nr | head -12 | awk '{printf "%8.1f MB  %s\n", $1/1024, $2}'

VERSION="$(python -c 'import sonoteca; print(sonoteca.__version__)')"
OUT="dist/Sonoteca-${VERSION}-alpha-macos-$(uname -m).zip"
rm -f "$OUT"
ditto -c -k --keepParent "$APP" "$OUT"
echo
echo "Listo: $APP"
echo "Zip:   $OUT ($(du -h "$OUT" | cut -f1))"
echo "En otra Mac (app sin firmar): clic derecho > Abrir, o xattr -dr com.apple.quarantine Sonoteca.app"
