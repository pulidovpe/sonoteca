# musicapp (nombre provisional)

[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green.svg)](LICENSE)
![Estado: alfa](https://img.shields.io/badge/estado-alfa-orange.svg)

Reproductor y organizador de **música local** de escritorio: tu biblioteca de mp3, m4a y mp4 (video) organizada por artista, álbum y año, con edición de tags. Funciona **sin conexión por defecto**; internet es opcional y solo se usa para portadas, información de artistas y álbumes, letras y traducción.

> **Versión alfa.** Pensada para usarse y probarse, pero puede tener errores. Haz copia de tu música antes de editar tags en masa (la app guarda una copia de respaldo en cada edición: `musicapp restore`).

## Funciones
- Biblioteca incremental (~miles de archivos) por **artista, álbum y década**, con búsqueda.
- Reproducción de audio y video, lista «Reproduciendo» (arrastrar para ordenar), listas guardadas con collage de portadas, historial adelante/atrás, salida de audio seleccionable.
- **Editor de tags** con verificación (escribe en una copia y comprueba antes de reemplazar) y sección **Por revisar** para canciones incompletas.
- Opcional en línea: portadas (MusicBrainz + Cover Art Archive), ficha del artista (Wikipedia; foto cambiable a mano), **letras sincronizadas** (LRCLIB) y traducción (DeepL con tu propia clave).
- Todo se guarda en una base SQLite local; nada se envía a servidores propios.

## Instalación (desde el código)
Requiere Python 3.11+ (se prueba con 3.12).

```bash
git clone <url-del-repositorio> && cd musicapp
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[ui,dev]"      # siempre editable (-e)
musicapp scan ~/Music            # indexa tu carpeta (incremental; --force relee todo)
musicapp gui                     # abre la interfaz
```
Otros comandos: `musicapp stats | artists | albums --decade 1990 | search "nombre" | incomplete | paths`.
Rutas: por defecto, las carpetas estándar del sistema; se fijan con `MUSICAPP_DATA_DIR` y `MUSICAPP_CACHE_DIR`.

## Aplicación empaquetada (alfa)
Aún no hay binarios publicados. Para generarlo en tu máquina (PyInstaller):

```bash
./packaging/build_mac.sh          # macOS  -> dist/musicapp.app y dist/musicapp-<versión>-alpha-macos-<arq>.zip
.\packaging\build_win.ps1         # Windows -> dist\musicapp\musicapp.exe y un .zip
```
La app **no está firmada**: en otra Mac, clic derecho ▸ *Abrir* la primera vez (o `xattr -dr com.apple.quarantine musicapp.app`). El primer arranque abre la ventana «Buscar música» si la biblioteca está vacía.

## Atajos
Espacio = pausa · doble clic = reproducir · Ctrl+0…6 = secciones (Inicio, Álbumes, Artistas, Por revisar, Reproduciendo, Listas, Letra) · Alt+←/→ = historial · Ctrl+Shift+O = Buscar música.

## Funciones en línea (opcionales, gratuitas)
Por defecto la app funciona sin conexión. **Archivo ▸ Internet…** las activa (MusicBrainz, Cover Art Archive y Wikipedia piden identificar la aplicación con un correo o URL). También por consola:

```bash
musicapp online on --contact tu@correo.com
musicapp find-album <id_álbum>      # candidatos de MusicBrainz
musicapp artist-info <id_artista>   # resumen de Wikipedia (se guarda para verlo sin conexión)
musicapp online off
```
En la página de un artista: *Actualizar información*, *¿Artista equivocado?* y *Cambiar imagen…* (JPG/PNG de hasta 5 MB). Nada se aplica sin confirmar.

## Letras y traducción (Fase 6, opcional)
**Letra** (Ctrl+6) muestra la letra de la canción que suena; también *Ver letra* en el clic derecho de una canción. Se busca en [LRCLIB](https://lrclib.net) (gratuito, sin clave; con letra sincronizada cuando existe: la línea que suena se resalta y un clic salta a ese momento) y se guarda en la base de datos para verla sin conexión. Requiere activar internet (Archivo ▸ Internet…). Con una canción sonando, **Letra** abre un panel a la derecha y, con internet activo, busca sola la letra si aún no la tiene; también puedes usar *Buscar letra*, o *Agregar texto* para escribir o pegar la letra a mano (con marcas `[mm:ss]` queda sincronizada).

**Traducción:** con DeepL y tu propia clave (plan gratuito «API Free»: 500 000 caracteres al mes; una letra usa ~1 500–2 500). La clave se guarda en el llavero del sistema (o en la variable `MUSICAPP_DEEPL_KEY`). Cada traducción se guarda y no se vuelve a pedir. Vistas: original / traducción / ambas.

Las letras tienen copyright: se guardan solo en tu base de datos local (uso personal), nunca en el repositorio.

## Por revisar
La sección **Por revisar** (Ctrl+3) lista las canciones sin artista o álbum, o deducidos del nombre del archivo. *Re-escanear tags* vuelve a leer los archivos de la lista; *Vaciar lista* las oculta sin tocar archivos ni tags; *Restaurar descartadas* las devuelve.

## Desarrollo
```bash
ruff check src tests && pytest     # pytest requiere ffmpeg para generar archivos de prueba
```
`.gitlab-ci.yml` ejecuta lint, pruebas y paquetes por sistema operativo. El repositorio **no debe contener letras** (tienen copyright; viven solo en la base local). Estado y decisiones del proyecto: `CONTEXT_COMPACT.md`.

Si un comando nuevo «no existe»: `musicapp --version` muestra de dónde se ejecuta el código; si apunta a `site-packages`, la instalación no es editable. Reinstala con `pip install -e ".[ui,dev]"`.

## Licencia
[MIT](LICENSE). Las letras, portadas y textos descargados pertenecen a sus titulares y a las fuentes indicadas (Wikipedia: CC BY-SA).
