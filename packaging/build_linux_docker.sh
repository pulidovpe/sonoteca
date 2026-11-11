#!/usr/bin/env bash
# Construye el binario de Linux dentro de Docker (sirve desde macOS o Windows con Docker Desktop).
# Uso: ./packaging/build_linux_docker.sh                 -> x86_64 (emulado en Apple Silicon: lento)
#      PLATFORM=linux/arm64 ./packaging/build_linux_docker.sh   -> arm64 nativo en Apple Silicon
# Resultado: dist/Sonoteca-<versión>-linux-<arquitectura>.tar.gz
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist

# En Linux con SELinux (Fedora, RHEL...) el contenedor no puede leer la carpeta montada sin la etiqueta ":z"
# («tar: /src: Cannot open: Permission denied»). En macOS/Windows (Docker Desktop) no se usa.
VOL_OPTS=""
[ "$(uname -s)" = "Linux" ] && VOL_OPTS=":z"

docker run --rm --platform "${PLATFORM:-linux/amd64}" -v "$PWD":/src"$VOL_OPTS" python:3.12-bookworm bash -euc '
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends libegl1 libgl1 libglib2.0-0 libxkbcommon0 \
      libxkbcommon-x11-0 libdbus-1-3 libfontconfig1 libpulse0 libxcb-cursor0
  mkdir /work
  tar -C /src --exclude=.venv-build --exclude=dist --exclude=build --exclude=.git -cf - . | tar -C /work -xf -
  cd /work
  python -m venv /tmp/venv && . /tmp/venv/bin/activate
  pip install -q --upgrade pip && pip install -q -c packaging/build-constraints.txt -e ".[ui,build]"
  pyinstaller packaging/sonoteca.spec --noconfirm --clean
  SONOTECA_SELFTEST=1 QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    SONOTECA_DATA_DIR=/tmp/d SONOTECA_CACHE_DIR=/tmp/c dist/sonoteca/sonoteca && echo "Prueba de humo: OK"
  python packaging/check_bundle.py dist/sonoteca
  cp assets/icons/sonoteca.png dist/sonoteca/sonoteca.png && cp packaging/linux/sonoteca.desktop dist/sonoteca/sonoteca.desktop
  cp packaging/linux/diagnose.sh dist/sonoteca/diagnose.sh && chmod +x dist/sonoteca/diagnose.sh
  V=$(python -c "import sonoteca; print(sonoteca.__version__)")
  tar -C dist -czf "/src/dist/Sonoteca-$V-linux-$(uname -m).tar.gz" sonoteca
  du -sh dist/sonoteca
  R="/src/dist/size-report-linux-$(uname -m).json"
  [ -f "$R" ] && mv -f "$R" "${R%.json}.prev.json" || true
  python packaging/size_report.py dist/sonoteca --top 20 --save "$R" --compare "${R%.json}.prev.json" || true
'
ls -lh dist/*.tar.gz
