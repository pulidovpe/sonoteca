#!/usr/bin/env bash
# Diagnóstico de arranque de Sonoteca en Linux (gráficos / Wayland / EGL).
# Uso:  ./diagnose.sh /ruta/a/la/carpeta/sonoteca      (la que contiene el ejecutable «sonoteca» y la carpeta «_internal»)
#       ./diagnose.sh                                   (si el script está dentro de esa carpeta)
#       añade --no-run para solo recoger información, sin abrir la aplicación (por defecto abre y cierra ventanas unos segundos)
# Escribe sonoteca-diagnostico.txt en la carpeta desde la que lo lances y también lo muestra. No modifica nada.
DIR="$(cd "$(dirname "$0")" && pwd)"
RUN=1
for arg in "$@"; do
  if [ "$arg" = "--no-run" ]; then RUN=0
  elif [ -d "$arg" ]; then DIR="$(cd "$arg" && pwd)"
  else echo "Argumento no reconocido o carpeta inexistente: $arg" >&2; exit 2
  fi
done
OUT="$PWD/sonoteca-diagnostico.txt"
BIN="$DIR/sonoteca"; INT="$DIR/_internal"
EGLPLUGIN="$INT/PySide6/Qt/plugins/wayland-graphics-integration-client/libqt-plugin-wayland-egl.so"
if [ ! -x "$BIN" ] || [ ! -d "$INT" ]; then
  echo "ATENCION: en $DIR no hay ejecutable 'sonoteca' ni carpeta '_internal'." >&2
  echo "Pasa como argumento la carpeta descomprimida del .tar.gz, p. ej.: ./diagnose.sh ~/Descargas/sonoteca" >&2
  exit 2
fi

sec() { printf '\n===== %s =====\n' "$1"; }
glibcxx() { grep -a -o 'GLIBCXX_3\.4\.[0-9]*' "$1" 2>/dev/null | sort -V | tail -1; }

report() {
  echo "Sonoteca diagnostico  $(date '+%Y-%m-%d %H:%M:%S')"
  sec "Sistema"
  . /etc/os-release 2>/dev/null && echo "Distro: ${PRETTY_NAME:-?}"
  echo "Kernel: $(uname -rm)"
  echo "Sesion: XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-?}  WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}  DISPLAY=${DISPLAY:-}"
  echo "Escritorio: ${XDG_CURRENT_DESKTOP:-?}"
  command -v systemd-detect-virt >/dev/null && echo "Virtualizacion: $(systemd-detect-virt 2>&1)"
  command -v lspci >/dev/null && lspci -nn 2>/dev/null | grep -Ei 'vga|3d|display'
  [ -d /dev/dri ] && echo "/dev/dri: $(ls /dev/dri | tr '\n' ' ')" || echo "/dev/dri: no existe (sin aceleracion 3D)"
  echo "Variables Qt/GL: $(env | grep -E '^(QT_|QSG_|LIBGL_|MESA_|__GLX|EGL_|LD_)' | tr '\n' ' ')"

  sec "Paquete (bibliotecas incluidas que suelen chocar con el sistema)"
  if [ -d "$INT" ]; then
    ls "$INT" | grep -Ei '^lib(EGL|GL|GLX|GLdispatch|OpenGL|gbm|drm|wayland|stdc|gcc_s|xcb|X11)' || echo "(ninguna de esa lista)"
    echo "libstdc++ del paquete: $(glibcxx "$INT"/libstdc++.so.6) | del sistema: $(glibcxx "$(ldconfig -p 2>/dev/null | awk '/libstdc\+\+\.so\.6 /{print $NF; exit}')")"
  else
    echo "No existe $INT"
  fi

  sec "Dependencias que faltan o chocan (plugin Wayland-EGL)"
  if [ -f "$EGLPLUGIN" ]; then
    LD_LIBRARY_PATH="$INT:${LD_LIBRARY_PATH:-}" ldd "$EGLPLUGIN" 2>&1 | grep -Ei 'not found|version' || echo "(sin faltas)"
  else
    echo "Plugin no encontrado: $EGLPLUGIN"
  fi

  sec "EGL del sistema cargado con las bibliotecas del paquete"
  for lib in $(ldconfig -p 2>/dev/null | awk '/libEGL_mesa\.so|libEGL\.so\.1 |libgbm\.so\.1 /{print $NF}' | sort -u); do
    echo "-- $lib"
    LD_LIBRARY_PATH="$INT:${LD_LIBRARY_PATH:-}" ldd "$lib" 2>&1 | grep -Ei 'not found|version' || echo "   (sin faltas)"
  done
  echo "-- Vendors EGL (glvnd):"; ls /usr/share/glvnd/egl_vendor.d /etc/glvnd/egl_vendor.d 2>&1 | head

  if [ "$RUN" = 1 ] && [ -x "$BIN" ]; then
    sec "Pruebas de arranque (cada una se cierra sola a los 6 s; 124 = arranco bien, 134/139 = se cayo)"
    HOSTCXX="$(ldconfig -p 2>/dev/null | awk '/libstdc\+\+\.so\.6 /{print $NF; exit}')"
    HOSTEGL="$(ldconfig -p 2>/dev/null | awk '/libEGL\.so\.1 /{print $NF; exit}')"
    DATA="$(mktemp -d)"
    try() {
      local label="$1"; shift
      local log; log="$(env SONOTECA_DATA_DIR="$DATA" SONOTECA_CACHE_DIR="$DATA/c" "$@" timeout 6 "$BIN" 2>&1)"; local rc=$?
      echo "[$label] codigo=$rc"; echo "$log" | tail -3 | sed 's/^/    /'
    }
    try "1 por defecto"
    [ -n "$HOSTCXX" ] && try "2 libstdc++ del sistema primero" LD_PRELOAD="$HOSTCXX"
    [ -n "$HOSTCXX" ] && [ -n "$HOSTEGL" ] && try "3 libstdc++ y libEGL del sistema" LD_PRELOAD="$HOSTCXX $HOSTEGL"
    try "4 xcb (X11/XWayland)" QT_QPA_PLATFORM=xcb
    try "5 render por software" QT_QUICK_BACKEND=software
    try "6 xcb + software" QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software
    try "7 xcb + software + sensores" QT_QPA_PLATFORM=xcb QT_QUICK_BACKEND=software QSENSORS_BACKEND=software
    rm -rf "$DATA"
  fi
  echo; echo "Fin. Envia el archivo: $OUT"
}
report 2>&1 | tee "$OUT"
