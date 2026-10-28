#!/usr/bin/env bash
# Crea (o recrea) el entorno de DESARROLLO e instala Sonoteca en modo editable. Útil tras actualizar el proyecto,
# mover la carpeta, cambiar de Python o cuando aparece «ModuleNotFoundError: No module named 'sonoteca'».
#
# Uso:  ./packaging/dev_setup.sh                    -> crea .venv
#       VENV_DIR=venv ./packaging/dev_setup.sh      -> usa/recrea la carpeta «venv» (sin punto)
#       PYTHON=python3.12 ./packaging/dev_setup.sh  -> elegir el Python
# No toca tus datos (base de datos, portadas): solo el entorno virtual.
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi
set -euo pipefail
cd "$(dirname "$0")/.."

VENV="${VENV_DIR:-.venv}"
if [ -n "${VIRTUAL_ENV:-}" ] && [ "$(cd "$VIRTUAL_ENV" 2>/dev/null && pwd -P)" = "$(mkdir -p "$VENV" && cd "$VENV" && pwd -P)" ]; then
  echo "El entorno '$VENV' está activo. Ejecuta primero:  deactivate   y vuelve a lanzar este script." >&2
  exit 1
fi

PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in python3.12 python3.13 python3.11 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then PY="$candidate"; break; fi
  done
fi
echo "Usando: $("$PY" --version) ($(command -v "$PY"))"

rm -rf "$VENV"
"$PY" -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -e ".[ui,dev]"

echo
echo "== Comprobación =="
python -c "import sonoteca; print('sonoteca', sonoteca.__version__, '->', sonoteca.__file__)"
sonoteca --version
echo
echo "Listo. Activa el entorno con:  source $VENV/bin/activate   y ejecuta:  sonoteca gui"
