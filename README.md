# Sonoteca

[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green.svg)](LICENSE)
![Estado: alfa](https://img.shields.io/badge/estado-alfa-orange.svg)

Sonoteca es un reproductor y organizador de **música local** de escritorio: tu biblioteca de mp3, m4a y mp4 (video) organizada por artista, álbum y año, con edición de tags. Funciona **sin conexión por defecto**; internet es opcional y solo se usa para portadas, información de artistas y álbumes, letras y traducción.

> **Versión alfa.** Pensada para usarse y probarse, pero puede tener errores. Haz copia de tu música antes de editar tags en masa (la app guarda una copia de respaldo en cada edición: `sonoteca restore`).

## Funciones
- Biblioteca incremental (~miles de archivos) por **artista, álbum y década**, con búsqueda.
- Reproducción de audio y video, lista «Reproduciendo» (arrastrar para ordenar), listas guardadas con collage de portadas, historial adelante/atrás, salida de audio seleccionable.
- **Editor de tags** con verificación (escribe en una copia y comprueba antes de reemplazar) y sección **Por revisar** para canciones incompletas.
- Opcional en línea: portadas (MusicBrainz + Cover Art Archive), ficha del artista (Wikipedia; foto cambiable a mano), **letras sincronizadas** (LRCLIB) y traducción (DeepL con tu propia clave).
- Todo se guarda en una base SQLite local; nada se envía a servidores propios.

## Instalación (desde el código)
Requiere Python 3.11+ (se prueba con 3.12).

```bash
git clone <url-del-repositorio> && cd sonoteca
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ui,dev]"      # siempre editable (-e)
sonoteca scan ~/Music            # indexa tu carpeta (incremental; --force relee todo)
sonoteca gui                     # abre la interfaz
```
Otros comandos: `sonoteca stats | artists | albums --decade 1990 | search "nombre" | incomplete | harvest | export | import | paths`.
Rutas: por defecto, las carpetas estándar del sistema; se fijan con `SONOTECA_DATA_DIR` y `SONOTECA_CACHE_DIR`.

## Aplicación empaquetada (alfa)
Aún no hay binarios publicados. PyInstaller no compila de forma cruzada: **cada sistema se construye en ese sistema** (o en Docker, para Linux).

```bash
./packaging/build_mac.sh            # macOS   -> dist/Sonoteca.app + dist/Sonoteca-<versión>-alpha-macos-<arq>.zip
./packaging/build_linux_docker.sh   # Linux   -> dist/Sonoteca-<versión>-alpha-linux-<arq>.tar.gz (requiere Docker)
.\packaging\build_win.ps1            # Windows -> dist\sonoteca\sonoteca.exe + .zip (en una máquina Windows)
```
Cada script termina con una prueba de humo y muestra el tamaño. El tamaño se reduce podando los módulos de Qt que la app no usa (ver `packaging/sonoteca.spec`; `SONOTECA_NO_PRUNE=1` desactiva la poda).
En macOS la app **no está firmada**: en otra Mac, clic derecho ▸ *Abrir* la primera vez (o `xattr -dr com.apple.quarantine Sonoteca.app`). En Linux pueden hacer falta las bibliotecas del sistema `libxcb-cursor0` y `libxkbcommon-x11-0`. El primer arranque abre «Buscar música» si la biblioteca está vacía.

## Primer arranque y tus datos
Sonoteca (la aplicación empaquetada) arranca **con una biblioteca vacía**: crea su base de datos en la carpeta de datos del usuario (`~/Library/Application Support/sonoteca` en macOS, `%LOCALAPPDATA%\sonoteca` en Windows, `~/.local/share/sonoteca` en Linux; `sonoteca paths` la muestra) y abre la ventana **Buscar música** para elegir tus carpetas. El paquete no lleva bases de datos, listas ni portadas de nadie (`packaging/check_bundle.py` lo comprueba al compilar).

### Portadas y fotos automáticas
Al terminar de escanear, si hay álbumes sin portada y artistas sin foto **con tags bien identificados**, Sonoteca ofrece descargarlos (MusicBrainz, Cover Art Archive y Wikipedia) y **avisa cuánto puede tardar** según la cantidad; puedes ocultar la ventana, cancelar o dejarlo para después (Archivo ▸ *Descargar portadas e información…*, o `sonoteca harvest`). Reglas:
- Solo se aplican coincidencias claras; las dudosas se dejan para elegirlas a mano con *Buscar portada*.
- Nunca se modifican tus archivos de música: las portadas se guardan en la carpeta de datos y solo se muestran si el álbum no tiene portada propia (embebida o en su carpeta).
- Lo ya intentado no se repite hasta pasados 30 días. Requiere el modo en línea (Archivo ▸ *Internet…*).

### Exportar e importar la biblioteca
Archivo ▸ *Exportar biblioteca…* guarda un archivo `.sonoteca` con tu base (canciones, listas, letras, contadores) y las portadas y fotos descargadas; **no** incluye tu música, tu correo de contacto ni la clave de DeepL. Archivo ▸ *Importar biblioteca…* lo restaura: pide confirmación, guarda antes una copia de la biblioteca actual en `backups/` dentro de la carpeta de datos, permite indicar la nueva carpeta de música (si cambió la ruta) y se completa al volver a abrir la aplicación. También por consola: `sonoteca export copia` / `sonoteca import copia.sonoteca --carpeta-musica ~/Music`.

### Si venías de «musicapp»
Hasta la 0.8.x la aplicación se llamaba *musicapp*. Al primer arranque de Sonoteca se **mueven** tus datos (base, listas, portadas, fotos, copias de respaldo y ajustes) a las carpetas nuevas y se reescriben las rutas guardadas; si ya existe una biblioteca de Sonoteca, no se toca nada. Las variables `MUSICAPP_*` siguen funcionando, pero usa `SONOTECA_*`.

## Atajos
Espacio = pausa · doble clic = reproducir · Ctrl+0…6 = secciones (Inicio, Álbumes, Artistas, Por revisar, Reproduciendo, Listas, Letra) · Alt+←/→ = historial · Ctrl+Shift+O = Buscar música.

## Funciones en línea (opcionales, gratuitas)
Por defecto la app funciona sin conexión. **Archivo ▸ Internet…** las activa (MusicBrainz, Cover Art Archive y Wikipedia piden identificar la aplicación con un correo o URL). También por consola:

```bash
sonoteca online on --contact tu@correo.com
sonoteca find-album <id_álbum>      # candidatos de MusicBrainz
sonoteca artist-info <id_artista>   # resumen de Wikipedia (se guarda para verlo sin conexión)
sonoteca online off
```
En la página de un artista: *Actualizar información*, *¿Artista equivocado?* y *Cambiar imagen…* (JPG/PNG de hasta 5 MB). Nada se aplica sin confirmar.

## Letras y traducción (Fase 6, opcional)
**Letra** (Ctrl+6) muestra la letra de la canción que suena; también *Ver letra* en el clic derecho de una canción. Se busca en [LRCLIB](https://lrclib.net) (gratuito, sin clave; con letra sincronizada cuando existe: la línea que suena se resalta y un clic salta a ese momento) y se guarda en la base de datos para verla sin conexión. Requiere activar internet (Archivo ▸ Internet…). Con una canción sonando, **Letra** abre un panel a la derecha y, con internet activo, busca sola la letra si aún no la tiene; también puedes usar *Buscar letra*, o *Agregar texto* para escribir o pegar la letra a mano (con marcas `[mm:ss]` queda sincronizada).

**Traducción:** con DeepL y tu propia clave (plan gratuito «API Free»: 500 000 caracteres al mes; una letra usa ~1 500–2 500). La clave se guarda en el llavero del sistema (o en la variable `SONOTECA_DEEPL_KEY`). Cada traducción se guarda y no se vuelve a pedir. Vistas: original / traducción / ambas.

Las letras tienen copyright: se guardan solo en tu base de datos local (uso personal), nunca en el repositorio.

## Por revisar
La sección **Por revisar** (Ctrl+3) lista las canciones sin artista o álbum, o deducidos del nombre del archivo. *Re-escanear tags* vuelve a leer los archivos de la lista; *Vaciar lista* las oculta sin tocar archivos ni tags; *Restaurar descartadas* las devuelve.

## Desarrollo
```bash
ruff check src tests && pytest     # pytest requiere ffmpeg para generar archivos de prueba
```
`.gitlab-ci.yml` ejecuta lint, pruebas y paquetes por sistema operativo. Los cambios se registran en [`CHANGELOG.md`](CHANGELOG.md). El repositorio **no debe contener letras** (tienen copyright; viven solo en la base local). Estado y decisiones del proyecto: `CONTEXT_COMPACT.md`.

Si un comando nuevo «no existe»: `sonoteca --version` muestra de dónde se ejecuta el código; si apunta a `site-packages`, la instalación no es editable. Reinstala con `pip install -e ".[ui,dev]"`.

## Licencia
[MIT](LICENSE). Las letras, portadas y textos descargados pertenecen a sus titulares y a las fuentes indicadas (Wikipedia: CC BY-SA).
