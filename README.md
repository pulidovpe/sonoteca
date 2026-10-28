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

Ver `CONTEXT.md` para el plan completo y el estado del proyecto.

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
**Letra** (Ctrl+6) muestra la letra de la canción que suena; también *Ver letra* en el clic derecho de una canción. Se busca en [LRCLIB](https://lrclib.net) (gratuito, sin clave; con letra sincronizada cuando existe: la línea que suena se resalta y un clic salta a ese momento) y se guarda en la base de datos para verla sin conexión. Requiere activar internet (Archivo ▸ Internet…) y la búsqueda es manual (botón *Buscar letra*).

**Traducción:** con DeepL y tu propia clave (plan gratuito «API Free»: 500 000 caracteres al mes; una letra usa ~1 500–2 500). La clave se guarda en el llavero del sistema (o en la variable `MUSICAPP_DEEPL_KEY`). Cada traducción se guarda y no se vuelve a pedir. Vistas: original / traducción / ambas.

Las letras tienen copyright: se guardan solo en tu base de datos local (uso personal), nunca en el repositorio.
