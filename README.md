# musicapp

Reproductor y organizador de música local (mp3, m4a, mp4). Fase 1: núcleo y CLI. Fase 2: interfaz QML de navegación. Fase 3: reproducción de audio y video. Fase 4: editor de tags. Fase 5: portadas e información en línea (opcional). Fase 6: letras y traducción (opcional).

```bash
uv sync --extra ui           # o: pip install -e ".[ui,dev]"  (siempre editable: -e)
musicapp scan ~/Music        # indexa (incremental; --force relee todo)
musicapp gui                 # abre la interfaz (Espacio = pausa; doble clic en una pista = reproducir)
musicapp stats | artists | albums --decade 1990 | search "nombre" | incomplete
musicapp restore <carpeta>    # deshace una edición de tags usando su copia de respaldo
musicapp paths                # dónde se guardan la base y la caché de portadas
pytest                       # requiere ffmpeg para generar archivos de prueba
```

Ver `CONTEXT_COMPACT.md` para el estado del proyecto.

Rutas: por defecto usan las carpetas estándar del sistema; se pueden fijar con `MUSICAPP_DATA_DIR` y `MUSICAPP_CACHE_DIR`.

## Funciones en línea (opcionales, gratuitas, sin clave)
Por defecto la app funciona sin conexión. Para activarlas (MusicBrainz, Cover Art Archive y Wikipedia piden identificar la aplicación con un correo o URL):

```bash
musicapp online on --contact tu@correo.com
musicapp find-album <id_álbum>      # candidatos de MusicBrainz para un álbum de la biblioteca
musicapp artist-info <id_artista>   # resumen de Wikipedia (se guarda para verlo sin conexión)
musicapp online off                 # volver al modo sin conexión
```

## Si un comando nuevo "no existe"
`musicapp --version` muestra la versión y de dónde se ejecuta el código. Si la ruta apunta a `.../site-packages/musicapp`
y no a tu carpeta del proyecto, la instalación no es editable y sigue ejecutando una copia vieja. Reinstala desde la carpeta
del proyecto: `pip install -e ".[ui,dev]"` (o `uv sync --extra ui`).

En la interfaz: **Archivo ▸ Internet…** activa el modo en línea; en la página de un artista aparece su ficha (Wikipedia) y en la de un álbum el botón **Portada e info** (MusicBrainz + Cover Art Archive). Nada se aplica sin confirmar.

**Lista temporal:** clic derecho en una canción (o "Agregar a la lista" en un álbum) la agrega a la lista que suena; la sección **Cola** (Ctrl+4) permite ordenarla, quitar canciones o empezar una lista nueva. No se guarda al cerrar la aplicación.

**Listas guardadas:** sección **Listas** (Ctrl+5); clic derecho en una canción ▸ *Agregar a una lista…*; en la **Cola**, *Guardar como lista…*. Los tags de cualquier canción se pueden editar desde la cola o desde una lista (*Editar tags* al pasar el ratón por la fila).

## Letras y traducción (Fase 6, opcional)
**Letra** (Ctrl+6) muestra la letra de la canción que suena; también *Ver letra* en el clic derecho de una canción. Se busca en [LRCLIB](https://lrclib.net) (gratuito, sin clave; con letra sincronizada cuando existe: la línea que suena se resalta y un clic salta a ese momento) y se guarda en la base de datos para verla sin conexión. Requiere activar internet (Archivo ▸ Internet…). Con una canción sonando, **Letra** abre un panel a la derecha y, con internet activo, busca sola la letra si aún no la tiene; también puedes usar *Buscar letra*, o *Agregar texto* para escribir o pegar la letra a mano (con marcas `[mm:ss]` queda sincronizada).

**Traducción:** con DeepL y tu propia clave (plan gratuito «API Free»: 500 000 caracteres al mes; una letra usa ~1 500–2 500). La clave se guarda en el llavero del sistema (o en la variable `MUSICAPP_DEEPL_KEY`). Cada traducción se guarda y no se vuelve a pedir. Vistas: original / traducción / ambas.

Las letras tienen copyright: se guardan solo en tu base de datos local (uso personal), nunca en el repositorio.

## Por revisar
La sección **Por revisar** (Ctrl+3) lista las canciones sin artista o álbum, o deducidos del nombre del archivo. *Re-escanear tags* vuelve a leer los archivos de la lista (sirve cuando ya corregiste los tags fuera de la app); *Vaciar lista* las oculta sin tocar archivos ni tags, y *Restaurar descartadas* las devuelve.

## Empaquetado y CI (Fase 7)
```bash
pip install -e ".[ui,build]"
pyinstaller packaging/musicapp.spec --noconfirm   # dist/musicapp/ (y dist/musicapp.app en macOS)
ruff check src tests && pytest                    # lo mismo que corre el CI
```
`.gitlab-ci.yml` define: `lint` (ruff), `repo-hygiene` (el repositorio no debe versionar letras `.lrc` ni bases de datos), `test` (pytest con Qt sin pantalla y ffmpeg) y `build:linux|windows|macos` (PyInstaller; se lanzan a mano o al crear una etiqueta). Los runners de Windows y macOS de GitLab.com están en beta y macOS requiere plan Premium/Ultimate o el programa de código abierto: sin ellos, compila en cada sistema con los comandos de arriba.

Las capturas de pantalla se añadirán a `docs/` cuando la interfaz esté probada.
