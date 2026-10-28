#!/usr/bin/env bash
# Construye Sonoteca.app (arquitectura de tu Mac) y un .zip listo para compartir.
#   ./packaging/build_mac.sh                       (desde cualquier carpeta; requiere Python 3.11+ e internet)
#   PYTHON=python3.12 ./packaging/build_mac.sh     -> elegir el Python a usar
#   SONOTECA_NO_PRUNE=1 ./packaging/build_mac.sh   -> sin podar módulos de Qt (si la poda diera problemas)
# Tarda varios minutos (descarga PySide6 y PyInstaller). Todo lo que muestra se guarda también en build.log.
# Resultado: dist/Sonoteca.app y dist/Sonoteca-<versión>-alpha-macos-<arq>.zip
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi   # lanzado con `sh script`: se relanza con bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

exec > >(tee build.log) 2>&1
trap 'echo; echo "✗ FALLÓ en el paso «${STEP:-inicio}» (línea $LINENO). Revisa el final de build.log y envíalo para ayudarte." >&2' ERR
STEP=""
step() { STEP="$2"; echo; echo "[$1/7] $2"; }

step 1 "Elegir Python"
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in python3.12 python3.13 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
  done
fi
echo "Usando: $("$PY" --version) ($(command -v "$PY"))"

step 2 "Crear el entorno de compilación (.venv-build)"
# Propio de este script y sin relación con tu entorno de desarrollo. Se borra siempre: uno viejo o copiado de otra
# máquina deja enlaces rotos («No such file ... .venv-build/bin/python3.12»).
rm -rf .venv-build
"$PY" -m venv --clear .venv-build
# shellcheck disable=SC1091
source .venv-build/bin/activate

step 3 "Instalar dependencias (PySide6, PyInstaller…; puede tardar)"
python -m pip install --upgrade pip
python -m pip install -e ".[ui,build]"

step 4 "Compilar con PyInstaller (varios minutos)"
pyinstaller packaging/sonoteca.spec --noconfirm --clean
APP="dist/Sonoteca.app"
[ -d "$APP" ] || { echo "No se generó $APP" >&2; exit 1; }

step 5 "Prueba de humo (abre la app sin pantalla ~5 s; datos temporales)"
TMP="$(mktemp -d)"
if SONOTECA_SELFTEST=1 QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
   SONOTECA_DATA_DIR="$TMP/data" SONOTECA_CACHE_DIR="$TMP/cache" "$APP/Contents/MacOS/sonoteca"; then
  echo "OK: la interfaz carga."
else
  echo "FALLO: la app empaquetada no arranca. Prueba con SONOTECA_NO_PRUNE=1 y envía el error." >&2
fi
rm -rf "$TMP"

step 6 "Comprobar que no lleva datos personales y medir el tamaño"
python packaging/check_bundle.py "$APP" || echo "REVISA: el paquete no debe llevar datos personales." >&2
du -sh "$APP"
echo "Carpetas más pesadas:"
{ du -sk "$APP"/Contents/*/* "$APP"/Contents/*/*/* 2>/dev/null | sort -nr | head -12 \
    | awk '{printf "%8.1f MB  %s\n", $1/1024, $2}'; } || true

step 7 "Crear el .zip"
VERSION="$(python -c 'import sonoteca; print(sonoteca.__version__)')"
OUT="dist/Sonoteca-${VERSION}-alpha-macos-$(uname -m).zip"
rm -f "$OUT"
ditto -c -k --keepParent "$APP" "$OUT"

trap - ERR
echo
echo "✓ Binario listo"
echo "  App: $(pwd)/$APP"
echo "  Zip: $(pwd)/$OUT ($(du -h "$OUT" | cut -f1))"
echo "  Mostrarla en el Finder:  open -R \"$APP\""
echo "  En otra Mac (app sin firmar): clic derecho > Abrir, o xattr -dr com.apple.quarantine Sonoteca.app"
