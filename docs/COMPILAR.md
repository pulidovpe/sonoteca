# Manual: generar el binario de Sonoteca en cada plataforma

Este manual explica cómo, a partir de la carpeta del proyecto, obtener un ejecutable para **macOS, Windows y Linux**
estando en una máquina distinta de la de desarrollo.

> **Estado.** Los scripts descritos aquí existen y su sintaxis está revisada, pero **la compilación con PyInstaller
> no se ha podido ejecutar en ninguna plataforma durante el desarrollo**. Trata la primera compilación en cada sistema
> como una prueba: la sección 8 explica qué hacer si algo falla.

---

## 1. Idea clave: cada sistema se compila en ese sistema

PyInstaller **no compila de forma cruzada**: un binario de Windows se genera en Windows, uno de macOS en macOS y uno de
Linux en Linux (o dentro de un contenedor Linux). Por eso necesitas acceso a una máquina (o máquina virtual) de cada
sistema que quieras entregar.

| Plataforma | Dónde compilar | Script | Resultado |
|---|---|---|---|
| macOS | un Mac | `packaging/build_mac.sh` | `dist/Sonoteca.app` y `dist/Sonoteca-<versión>-beta-macos-<arq>.zip` |
| Windows | un PC con Windows | `packaging/build_win.ps1` | `dist\sonoteca\sonoteca.exe` y `dist\Sonoteca-<versión>-beta-windows-x86_64.zip` |
| Linux | una máquina Linux **o Docker** (también desde Mac/Windows) | `packaging/build_linux_docker.sh` (o pasos manuales, §5) | `dist/Sonoteca-<versión>-beta-linux-<arq>.tar.gz` |

La arquitectura del binario es la de la máquina donde compilas: un `.app` hecho en un Mac con Apple Silicon (arm64) es
para Apple Silicon; uno hecho en un Mac Intel, para Intel. Lo mismo con Linux (x86_64 o arm64).

---

## 2. Antes de copiar el proyecto a otra máquina

Copia **solo el código**, no los entornos ni resultados de compilaciones anteriores: los entornos virtuales y las
carpetas `build/` y `dist/` son específicos de cada sistema y romperían la compilación.

**Excluye** siempre: `.venv/`, `venv/` (o como llames a tu entorno), `.venv-build/`, `build/`, `dist/`, `__pycache__/`, `*.egg-info/`, `.git/` (si no la necesitas).

Formas de llevarlo:

- **Desde el zip que te entrego** (`sonoteca-<versión>.zip`): ya viene limpio. Descomprímelo en la otra máquina.
- **Si tienes el repositorio en Git/GitLab**: en la otra máquina, `git clone <url>` (lo más limpio).
- **Desde tu carpeta de desarrollo** (macOS/Linux):
  ```bash
  cd /ruta/al/proyecto/..
  zip -r sonoteca-para-compilar.zip sonoteca \
      -x 'sonoteca/.venv/*' 'sonoteca/venv/*' 'sonoteca/.venv-build/*' 'sonoteca/build/*' 'sonoteca/dist/*' \
         '*/__pycache__/*' '*.egg-info/*' 'sonoteca/.git/*'
  ```
  (Sustituye `sonoteca` por el nombre real de tu carpeta.) En Windows, comprime la carpeta con el explorador y borra
  antes `.venv`, `.venv-build`, `build` y `dist`.

**No incluyas datos personales**: tu base de datos y tus portadas viven en la carpeta de datos del usuario
(fuera del proyecto), así que no viajan con el código. Aun así, el script de compilación comprueba que el paquete final no
lleve bases de datos, ajustes, letras ni portadas (`packaging/check_bundle.py`).

---

## 3. macOS

### 3.1 Requisitos (una sola vez)
1. **Herramientas de línea de comandos de Xcode**: `xcode-select --install`.
2. **Python 3.12** (3.11 o superior; se recomienda 3.12). Desde <https://www.python.org/downloads/macos/> o con
   Homebrew: `brew install python@3.12`.
3. **Conexión a internet** (descarga PySide6, PyInstaller y otras dependencias).
4. Varios GB libres en disco.

### 3.2 Compilar
```bash
cd ~/ruta/a/sonoteca            # la carpeta del proyecto (la que contiene pyproject.toml)
rm -rf .venv-build build dist   # evita restos de compilaciones anteriores
./packaging/build_mac.sh
```
Si el comando `python3` de tu Mac no es el 3.12, indica cuál usar: `PYTHON=python3.12 ./packaging/build_mac.sh`.
Si dice «permission denied», haz `chmod +x packaging/*.sh` y repite.

El script avisa de cada paso (`[1/7] … [7/7]`), guarda todo lo que muestra en `build.log` y, al terminar, imprime la ruta exacta de
`dist/Sonoteca.app`. **La carpeta `dist/` solo existe después de que el script termine con «✓ Binario listo»**: `sonoteca gui` no
compila nada. Si falla, el mensaje dice en qué paso; envía el final de `build.log`.

El script, en orden: crea un entorno virtual aislado (`.venv-build`), instala el proyecto con sus dependencias,
ejecuta PyInstaller, hace una **prueba de humo** (abre la app sin pantalla ~5 s), comprueba que **no haya datos personales**,
muestra el **tamaño** y crea el zip.

### 3.3 Resultado y primera ejecución
- `dist/Sonoteca.app` — la aplicación.
- `dist/Sonoteca-<versión>-beta-macos-<arq>.zip` — para compartirla.

La app **no está firmada ni notarizada**. En el mismo Mac donde la compilaste se abre normal; en otro Mac, macOS la
bloqueará la primera vez: **clic derecho ▸ Abrir ▸ Abrir**, o desde la terminal:
```bash
xattr -dr com.apple.quarantine /ruta/a/Sonoteca.app
```
Para distribuirla sin esos avisos haría falta una cuenta de desarrollador de Apple (firma y notarización); eso no está
automatizado en este proyecto.

---

## 4. Windows

### 4.1 Requisitos (una sola vez)
1. **Python 3.12 de 64 bits** desde <https://www.python.org/downloads/windows/>. En el instalador, marca
   **«Add python.exe to PATH»**. Comprueba en PowerShell: `python --version`.
2. **Conexión a internet** y varios GB libres.
3. Se asume Windows de 64 bits (x86_64). Windows en ARM no se ha considerado ni probado.

### 4.2 Compilar
Abre **PowerShell** en la carpeta del proyecto (la que contiene `pyproject.toml`):
```powershell
Remove-Item -Recurse -Force .venv-build, build, dist -ErrorAction SilentlyContinue
powershell -ExecutionPolicy Bypass -File .\packaging\build_win.ps1
```
(`-ExecutionPolicy Bypass` evita que Windows bloquee el script por la política de ejecución de scripts.)

El script hace lo mismo que el de macOS: entorno virtual, instalación, PyInstaller, prueba de humo, comprobación de datos
personales, tamaño y zip.

### 4.3 Resultado y primera ejecución
- `dist\sonoteca\sonoteca.exe` (con sus bibliotecas en la misma carpeta; **no muevas el .exe solo**).
- `dist\Sonoteca-<versión>-beta-windows-x86_64.zip` — descomprime y ejecuta `sonoteca\sonoteca.exe`.

El ejecutable **no está firmado**: Windows SmartScreen puede mostrar «Windows protegió su PC» (*Más información ▸ Ejecutar de
todas formas*), y algunos antivirus marcan por error los programas empaquetados con PyInstaller. Firmar el ejecutable
requiere un certificado de firma de código y no está automatizado aquí.

---

## 5. Linux

Hay dos caminos. El de **Docker** es el recomendado porque deja siempre el mismo entorno.

### 5.1 Con Docker (desde Linux, macOS o Windows)
1. Instala Docker (Docker Desktop en macOS/Windows; el paquete de tu distribución en Linux) y comprueba `docker run hello-world`.
2. En la carpeta del proyecto (macOS/Linux o Git Bash/WSL en Windows):
   ```bash
   ./packaging/build_linux_docker.sh                        # x86_64 (en un Mac Apple Silicon va emulado: lento)
   PLATFORM=linux/arm64 ./packaging/build_linux_docker.sh   # arm64 (nativo en Apple Silicon)
   ```
3. Resultado: `dist/Sonoteca-<versión>-beta-linux-<arquitectura>.tar.gz`.

El script compila dentro de un contenedor Debian 12 (`python:3.12-bookworm`), así que el binario resultante necesita
una versión de **glibc igual o mayor** que la de Debian 12 (2.36). Para distribuciones más antiguas habría que compilar en
una más antigua.

### 5.2 Sin Docker (directamente en una máquina Linux)
En Debian/Ubuntu (los nombres de paquetes pueden variar en otras distribuciones):
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip ffmpeg \
    libegl1 libgl1 libglib2.0-0 libxkbcommon0 libxkbcommon-x11-0 libdbus-1-3 libfontconfig1 libpulse0 libxcb-cursor0

cd /ruta/a/sonoteca
python3 -m venv .venv-build && source .venv-build/bin/activate
pip install --upgrade pip
pip install -e ".[ui,build]"
pyinstaller packaging/sonoteca.spec --noconfirm --clean

# prueba de humo, comprobación de datos personales y empaquetado
SONOTECA_SELFTEST=1 QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  SONOTECA_DATA_DIR=/tmp/d SONOTECA_CACHE_DIR=/tmp/c dist/sonoteca/sonoteca && echo "humo OK"
python packaging/check_bundle.py dist/sonoteca
tar -C dist -czf Sonoteca-beta-linux-$(uname -m).tar.gz sonoteca
```

### 5.3 Usarlo en otra máquina Linux
```bash
tar xzf Sonoteca-*-linux-*.tar.gz && ./sonoteca/sonoteca
```
Si al abrirlo aparece un error del tipo *«Could not load the Qt platform plugin "xcb"»*, instala las bibliotecas del sistema:
`libxcb-cursor0` y `libxkbcommon-x11-0` (y las de la lista de §5.2). Es un binario de carpeta: no mover el ejecutable solo.

---

## 6. Qué hace el empaquetado (para que sepas qué esperar)

- **Qué se empaqueta**: el código de `src/sonoteca` y las pantallas QML (`src/sonoteca/ui/qml`), junto con Python y Qt.
  **No** se empaqueta ninguna base de datos, lista, portada, letra ni ajuste.
- **Poda de Qt**: `packaging/sonoteca.spec` descarta los módulos de Qt que la aplicación no usa (WebEngine, 3D, Charts,
  estilos de controles distintos de Basic, traducciones de Qt…), porque PyInstaller no puede saber qué módulos QML se usan y
  de otro modo copiaría todos. La lista de lo descartado queda en `build/pruned.txt`. En una prueba en macOS el resultado
  fue de unos 175 MB sin comprimir.
- **Primer arranque del usuario**: la app crea una **biblioteca vacía** en su carpeta de datos
  (`~/Library/Application Support/sonoteca` en macOS, `%LOCALAPPDATA%\sonoteca` en Windows, `~/.local/share/sonoteca` en
  Linux) y abre «Buscar música».

### Icono de la aplicación
El icono ya está conectado; no tienes que copiar nada a mano. Los archivos viven en `assets/icons/` y se generan desde el
logo original (`assets/icons/original.png`) con `packaging/make_icons.py`:

| Archivo | Para qué sirve |
|---|---|
| `assets/icons/sonoteca.ico` | Icono del `.exe` en Windows (lo incrusta PyInstaller). |
| `assets/icons/sonoteca.icns` | Icono del `.app` en macOS (Finder y Dock). |
| `assets/icons/sonoteca.png` y `sonoteca-1024.png` | Imágenes de uso general (README, tienda, Linux). |
| `src/sonoteca/ui/icon.png` | Icono de la ventana en ejecución (barra de tareas / Dock); se empaqueta junto al QML. |

- **Cambiar el logo**: sustituye `assets/icons/original.png` (admite fondo blanco con márgenes; se recorta y se hace
  transparente) y ejecuta, con el entorno de desarrollo activado: `pip install pillow numpy && python packaging/make_icons.py`.
  Después vuelve a compilar.
- **Windows y macOS**: el icono queda en el propio ejecutable. Si ves el icono viejo, es la caché del sistema: en Windows
  reinicia el Explorador (o cambia el nombre del `.exe`); en macOS mueve el `.app` a otra carpeta o ejecuta
  `touch Sonoteca.app` y reabre el Finder.
- **Linux**: un binario ELF no puede llevar el icono incrustado. El `.tar.gz` incluye `sonoteca.png` y
  `sonoteca.desktop`; para tener un lanzador con icono, edita las rutas `Exec=` e `Icon=` del `.desktop` (deben ser absolutas)
  y cópialo a `~/.local/share/applications/`. La ventana sí muestra el icono por `icon.png`.
- **Ejecutando desde el código fuente** (`sonoteca gui`) la ventana usa también `icon.png`.

---

## 6b. Tamaño del binario
El código y los datos de Sonoteca pesan **menos de 1 MB** (el QML son ~420 KB). Casi todo el peso es Qt (PySide6) y lo que arrastra,
y *no se puede medir desde el código fuente*: se mide sobre el paquete compilado.

**Cómo medirlo.** Cada script de compilación termina con un informe (`packaging/size_report.py`) que agrupa el paquete por categoría
(FFmpeg, Qt Multimedia, QML y plugins de Qt, PyObjC, Python…), lista los archivos más pesados y lo guarda en
`dist/size-report-<sistema>.json`. En la compilación siguiente lo compara con el anterior: te dice cuántos MB creció cada categoría,
qué versiones de paquetes cambiaron (p. ej. `PySide6 6.8.1 → 6.10.0`) y qué archivos son nuevos o crecieron. A mano:
`python packaging/size_report.py dist/Sonoteca.app --compare dist/size-report-macos-arm64.prev.json`.

**Medido en macOS (0.14.2 con PySide6 6.12.0): 161,9 MB sin comprimir**, frente a los 179,2 MB de la 0.12. No se sabe cuánto se debe
a cada cambio (poda nueva, `AppKit`, versión de PySide6): el informe por categorías de la siguiente compilación lo dirá.

**PySide6 6.12:** el metapaquete `PySide6` instala también `PySide6_WebEngine` (~115 MB) y `PySide6_Pdf` (~20 MB) y la app no usa
ninguno. No entran en el binario (la poda los quita), pero engordaban el entorno de compilación. Desde la 0.14.3 el extra `ui` pide
solo `PySide6-Essentials` y `PySide6-Addons` (QtMultimedia está en Addons). Si ya tienes un entorno con el metapaquete:
`pip uninstall PySide6 PySide6_WebEngine PySide6_Pdf` y `pip install -e ".[ui,dev]"`.

**Qué suele pesar (hipótesis, sin medir):**
- **FFmpeg dentro de Qt Multimedia** (`libavcodec`, `libavformat`, `libswscale`…): lo trae PySide6 y es la categoría que más puede
  cambiar entre versiones de PySide6. Como `pyproject.toml` pedía `PySide6>=6.7` sin tope (ahora lo fija `build-constraints.txt`), cada compilación usaba la última, y era la
  causa más probable de que el binario «siga subiendo».
- **Bibliotecas y plugins de Qt** (QtQuick, QtQml, QtGui…): fijas, ya podadas (ver `PRUNE` en `packaging/sonoteca.spec`).
- **PyObjC en macOS**: `pyobjc-framework-MediaPlayer` arrastra otras envolturas de frameworks de Apple. Solo sirve a las teclas
  multimedia globales.

**Versiones fijas:** `packaging/build-constraints.txt` fija PySide6 a la versión verificada (6.12.0) para que una versión nueva no
cambie el peso sin que lo decidas. Para actualizar, cambia el número (o borra las líneas), compila y compara con el informe.

**Qué se recortó ya (0.14.2):** módulos QML que la app no importa (NativeStyle, Particles, Effects, LocalStorage + Qt SQL, Qt.labs),
las bibliotecas huérfanas de los estilos de Quick Controls podados, `AppKit` como importación forzada en macOS y paquetes de
herramientas (`setuptools`, `pip`, `numpy`, `PIL`). Es un ahorro **pequeño** (unos pocos MB); lo grande es PySide6/FFmpeg.

**Cosas que se descartaron a propósito:** *UPX* (no funciona en macOS arm64 y en Windows provoca falsos positivos de antivirus),
`strip` en macOS (invalida las firmas de las bibliotecas de Qt y el binario deja de abrir en arm64) y `optimize=2` (ahorra 1–3 MB
pero puede romper bibliotecas que leen docstrings).

**Si la poda diera problemas:** `SONOTECA_NO_PRUNE=1` la desactiva; `build/pruned.txt` lista lo que se quitó. Tras esta versión, si la
prueba de humo falla o los diálogos de archivos/carpetas no abren, avísame con ese archivo: lo primero que se revisaría son las
entradas nuevas de `PRUNE`.

## 7. Verificar que el binario funciona

1. **Prueba de humo** (ya la hace el script): abre la interfaz sin pantalla ~5 s y debe terminar con «OK». Si el QML no
   carga, falla de inmediato.
2. **Sin datos personales**: `python packaging/check_bundle.py <carpeta o .app>` debe decir «OK».
3. **Arranque limpio de verdad** (con ventana), usando carpetas de datos temporales para no tocar tu biblioteca:
   - macOS/Linux:
     ```bash
     SONOTECA_DATA_DIR=/tmp/sonoteca-limpio/data SONOTECA_CACHE_DIR=/tmp/sonoteca-limpio/cache \
       dist/Sonoteca.app/Contents/MacOS/sonoteca        # Linux: dist/sonoteca/sonoteca
     ```
   - Windows (PowerShell):
     ```powershell
     $env:SONOTECA_DATA_DIR="$env:TEMP\sonoteca-limpio\data"; $env:SONOTECA_CACHE_DIR="$env:TEMP\sonoteca-limpio\cache"
     .\dist\sonoteca\sonoteca.exe
     ```
   Debe abrir con la biblioteca vacía y la ventana «Buscar música». Elige una carpeta pequeña de música para probar el
   escaneo, la reproducción y (con internet activado) la descarga de portadas.
4. **Prueba en una máquina sin Python ni Qt instalados**: es la prueba que de verdad importa para un binario. Copia el
   zip allí y ábrelo.

---

## 8. Solución de problemas

| Síntoma | Qué probar |
|---|---|
| `command not found: python3` / `python` no se reconoce | Instala Python 3.12 (§3.1 / §4.1) y abre una terminal nueva. |
| Error al instalar `PySide6` (no hay versión compatible) | Usa Python 3.12 de 64 bits; las versiones muy nuevas o muy viejas pueden no tener ruedas de PySide6 todavía. |
| `permission denied` al ejecutar el `.sh` | `chmod +x packaging/*.sh` |
| Windows: «la ejecución de scripts está deshabilitada» | Usa `powershell -ExecutionPolicy Bypass -File .\packaging\build_win.ps1`. |
| La prueba de humo dice **FALLO** | Repite la compilación **sin la poda**: `SONOTECA_NO_PRUNE=1 ./packaging/build_mac.sh` (Windows: `$env:SONOTECA_NO_PRUNE="1"` antes del script). Si así funciona, la poda quitó algo necesario: guarda el mensaje de error y `build/pruned.txt`. |
| El binario arranca en la terminal pero no abre ventana / se cierra | Ejecútalo desde la terminal y copia el error. Compila de nuevo sin poda para descartar. |
| Linux: error del plugin de plataforma «xcb» | Instala `libxcb-cursor0` y `libxkbcommon-x11-0` (§5.3). |
| Linux: «GLIBC_x.xx not found» | El binario se compiló en una distribución más nueva que la de destino. Compila en una más antigua. |
| El binario es muy grande | Mira la lista «Carpetas más pesadas» que imprime el script de macOS y revisa `build/pruned.txt`. |
| `No such file or directory: '.../.venv-build/bin/python3.12'` | Es un `.venv-build` viejo o copiado de otra máquina (con enlaces rotos). Desde 0.9.2.1 el script lo borra solo; con una versión anterior: `rm -rf .venv-build` y repite. No tiene relación con tu carpeta `venv` de desarrollo (el nombre y el punto no importan). Lanza el script con `./packaging/build_mac.sh` o `bash packaging/build_mac.sh`. |
| Quedan restos de una compilación anterior | Borra `.venv-build`, `build` y `dist` y repite. |
| macOS: «la app está dañada» / no abre en otro Mac | Es el bloqueo de Gatekeeper por no estar firmada: `xattr -dr com.apple.quarantine Sonoteca.app`. |

Si pides ayuda, incluye: sistema y versión, `python --version`, y **el texto completo del error** (no una captura).

---

## 9. Alternativa: compilar con GitLab CI

El proyecto incluye `.gitlab-ci.yml` con trabajos `build:linux`, `build:windows` y `build:macos` que se lanzan a mano
(o al crear una etiqueta `v…`) y publican el resultado como *artefacto* de la tubería.

- **Linux** usa los *runners* gratuitos de GitLab.com.
- **Windows** usa un *runner* alojado en beta (etiqueta `saas-windows-medium-amd64`).
- **macOS** usa un *runner* alojado en beta (`saas-macos-medium-m1`) que, según la documentación de GitLab, solo está
  disponible en planes Premium/Ultimate o en el programa de código abierto; la imagen indicada en el archivo
  (`macos-14-xcode-15`) debe verificarse con la documentación vigente.

Estos trabajos **no se han ejecutado nunca**; es probable que la primera tubería necesite ajustes. Si no tienes acceso a
esos *runners*, compila localmente con los pasos de este manual.

---

## 10. Lista de comprobación antes de entregar un binario

- [ ] Compilado en la plataforma de destino, desde una carpeta limpia (sin `.venv`, `build`, `dist` previos).
- [ ] La prueba de humo dijo «OK» y `check_bundle.py` dijo «OK».
- [ ] Abierto con ventana usando carpetas de datos temporales: biblioteca vacía y «Buscar música».
- [ ] Probado escaneo, reproducción y (si aplica) descarga de portadas con una carpeta pequeña.
- [ ] Probado en una máquina **sin** Python instalado.
- [ ] El nombre del zip lleva versión, plataforma y arquitectura.
- [ ] Informas a quien lo reciba de que no está firmado (avisos de Gatekeeper / SmartScreen).
- [ ] Hay un archivo `LICENSE` (MIT) y el `CHANGELOG.md` está al día.

## Linux: la ventana no abre («EGL not available», «Failed to create RHI»)

Síntoma (Fedora + Wayland, paquete `.tar.gz` compilado en Docker/Debian 12): el programa se cae con `core dumped` y solo arranca
con `QPA_PLATFORM=xcb QT_QUICK_BACKEND=software`. Qt no puede crear el contexto OpenGL y no tiene alternativa automática.

Causa (confirmada con el informe de un Fedora 42 físico, Intel Iris Plus): el paquete llevaba la `libstdc++` de Debian 12
(`GLIBCXX_3.4.30`). Cargada antes que la del sistema, impedía abrir los controladores Mesa de Fedora (`libSPIRV-Tools` pide
`GLIBCXX_3.4.32`), así que EGL/GLX fallaban. Con la `libstdc++` del sistema por delante el arranque fue normal. Desde 0.14.13
`sonoteca.spec` **no empaqueta `libstdc++` en Linux** (requisito: la del sistema con `GLIBCXX_3.4.30` o superior, GCC 12+).
No se descartó nada más hasta verificar en la Mac/Fedora con un paquete nuevo. Si aun así falla, el diagnóstico sigue valiendo:

```bash
./diagnose.sh ~/Descargas/sonoteca            # informe + pruebas de arranque (abre y cierra ventanas)
./diagnose.sh ~/Descargas/sonoteca --no-run   # solo información
```

El argumento es la carpeta descomprimida del `.tar.gz` (la que contiene `sonoteca` y `_internal`); sin argumento se usa la
carpeta del propio script. El informe queda en `sonoteca-diagnostico.txt`, en la carpeta desde la que lo lances. Si el
tarball es anterior a 0.14.11 no incluye el script: se copia desde `packaging/linux/diagnose.sh` del zip del proyecto.

El informe compara `libstdc++` del paquete con la del sistema, lista dependencias que faltan y prueba el arranque con
`LD_PRELOAD` de las bibliotecas del sistema, con `xcb`, con render por software y con las combinaciones.
