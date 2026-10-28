#!/usr/bin/env bash
# Construye el binario de Linux dentro de Docker (sirve desde macOS o Windows con Docker Desktop).
# Uso: ./packaging/build_linux_docker.sh                 -> x86_64 (emulado en Apple Silicon: lento)
#      PLATFORM=linux/arm64 ./packaging/build_linux_docker.sh   -> arm64 nativo en Apple Silicon
# Resultado: dist/Sonoteca-<versión>-alpha-linux-<arquitectura>.tar.gz
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p dist

docker run --rm --platform "${PLATFORM:-linux/amd64}" -v "$PWD":/src python:3.12-bookworm bash -euc '
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends libegl1 libgl1 libglib2.0-0 libxkbcommon0 \
      libxkbcommon-x11-0 libdbus-1-3 libfontconfig1 libpulse0 libxcb-cursor0
  mkdir /work
  tar -C /src --exclude=.venv-build --exclude=dist --exclude=build --exclude=.git -cf - . | tar -C /work -xf -
  cd /work
  python -m venv /tmp/venv && . /tmp/venv/bin/activate
  pip install -q --upgrade pip && pip install -q -e ".[ui,build]"
  pyinstaller packaging/musicapp.spec --noconfirm --clean
  MUSICAPP_SELFTEST=1 QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
    MUSICAPP_DATA_DIR=/tmp/d MUSICAPP_CACHE_DIR=/tmp/c dist/musicapp/musicapp && echo "Prueba de humo: OK"
  V=$(python -c "import musicapp; print(musicapp.__version__)")
  tar -C dist -czf "/src/dist/Sonoteca-$V-alpha-linux-$(uname -m).tar.gz" musicapp
  du -sh dist/musicapp
'
ls -lh dist/*.tar.gz
