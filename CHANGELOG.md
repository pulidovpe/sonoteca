# Registro de cambios

Todos los cambios relevantes de **musicapp** (reproductor y organizador de música local, tipo Spotify,
solo para uso personal) se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el versionado
[SemVer](https://semver.org/lang/es/) (0.x: la interfaz y el esquema todavía pueden cambiar).

> **Nota sobre las versiones 0.1 a 0.4:** durante el desarrollo inicial el código mostraba siempre
> `0.1.0`. Los números de estas versiones se asignan de forma retroactiva a cada fase para ordenar
> el historial. Desde la `0.5.1` el número del código coincide con este registro
> (`musicapp --version`).

## [Sin publicar]

Trabajo ya escrito en el código pero todavía **no entregado ni etiquetado**.

### Añadido
- **Ventana de edición de tags:** muestra la portada actual del álbum asociado y, al elegir una
  nueva, la compara al lado ("Actual → Nueva"); también en la revisión de cambios y en
  *Portada e info* ("Actual → Seleccionada"). Si las canciones son de varios álbumes, lo indica.
- **Editar los tags de un artista completo** desde su página (botón *Editar tags del artista*).
- **Fase 6.1, letras (en desarrollo):** lector de letras sincronizadas LRC, cliente de LRCLIB
  (gratuito, sin clave), almacén de letras (también lee las incrustadas en el archivo: ID3 `USLT`,
  MP4 `©lyr`), esquema v5 y pantalla *Letra* que sigue la línea que suena. Pendiente: corregir
  avisos de QML al destruir la pantalla y su cobertura de pruebas.

### Pendiente
- Fase 6.2: traducción de letras (se evaluarán primero opciones gratuitas y sus límites).
- Importar y exportar listas en formato M3U; reordenar arrastrando.
- Empaquetado: binario para macOS y, después, Windows y Linux.

## [0.7.0] - Listas guardadas, fotos de artista
### Añadido
- **Listas de reproducción personalizadas** guardadas en la base de datos: crear, renombrar,
  eliminar (con confirmación), agregar, quitar, reordenar con flechas y reproducir. Los nombres son
  únicos sin distinguir mayúsculas; una canción puede repetirse; si una canción desaparece de la
  biblioteca sale sola de las listas.
- Sección **Listas** (Ctrl+5), *Nueva lista de reproducción…* (Ctrl+N), *Agregar a una lista…* en el
  menú de clic derecho de una canción, *Guardar en lista…* en cada álbum y *Guardar como lista…* en
  la Cola.
- **Editar tags desde la Cola y desde las listas** (fila con *Editar tags* y menú de clic derecho);
  tras editar, la cola, las listas y la barra de reproducción muestran el título nuevo.
- La **foto descargada del artista** se usa en la sección Artistas y en los resultados de búsqueda,
  con prioridad sobre las portadas de álbum. Las fotos se guardan ahora en la carpeta de datos
  (`artists/`); las de versiones anteriores en la caché se siguen usando.
### Cambiado
- Fila común de lista (`ListTrackRow`) para la Cola y las listas guardadas.

## [0.6.1] - Lista temporal (cola)
### Añadido
- La lista que suena es una **lista temporal** editable: *Reproducir ahora*, *Reproducir a
  continuación* y *Agregar a la lista actual* (clic derecho o texto "Más" sobre una canción),
  *Agregar a la lista* en cada álbum, *Nueva lista temporal* (conserva la canción que suena) y
  *Vaciar*.
- Sección **Cola** (Ctrl+4) con el orden real de reproducción: marca lo que suena, sube, baja y
  quita canciones, doble clic para reproducir desde ahí.
- Si no suena nada, agregar canciones arma una lista sin empezar a reproducir sola.
### Cambiado
- Los botones del álbum se acomodan en varias líneas en ventanas angostas.

## [0.6.0] - Fase 5.2: interfaz de las funciones en línea
### Añadido
- **Ficha del artista** (foto y resumen de Wikipedia con enlace a la fuente y licencia CC BY-SA),
  visible sin conexión una vez guardada.
- **Portada e info** de un álbum: candidatos de MusicBrainz con miniaturas ("Coincidencia
  probable", "Misma duración"); nada se cambia hasta confirmar; aplica con el mismo proceso del
  editor (respaldo, portada archivada, aviso breve).
- **Archivo ▸ Internet…** para activar el modo en línea (correo o web de contacto obligatorios) e
  indicador *En línea / Sin conexión* en la barra lateral.
- Todas las consultas corren en un hilo aparte (la interfaz no se congela).

## [0.5.5] - Búsqueda por canción, ajuste final
### Añadido
- `musicapp find-track <id_pista>`: busca los álbumes de una pista concreta (los ids de los grupos
  "Sin álbum" cambian al renombrar archivos).
### Cambiado
- Pide 100 grabaciones a MusicBrainz (máximo permitido).
- Orden de candidatos: álbum de estudio > EP > sencillo > en vivo, banda sonora o recopilación;
  luego misma duración (±5 s), luego el más antiguo y, al final, el más cercano al año del archivo.
- El año de un álbum es el más antiguo de todas sus ediciones (antes salía el de una reedición).
- `find-album` / `find-track` muestran 10 candidatos y `--all` para ver el resto.

## [0.5.4] - Consultas más tolerantes
### Cambiado
- Los tipos secundarios de MusicBrainz (Soundtrack, Live, Remix…) cuentan como "no original".
- Escalera de consultas: frase exacta con filtro oficial/álbum → sin filtro → palabras sueltas; el
  artista se busca por palabras y sin artículo inicial ("The Village People" = "Village People"); se
  limpian los títulos ("(Remastered)", "[Live]", "- Radio Edit"); se conservan los acentos.
- `find-album` indica qué canción usa en los grupos "Sin álbum" y acepta `--track`.

## [0.5.3] - Búsqueda por canción: duración y año
### Cambiado
- Para pistas "Sin álbum" se compara la duración (±5 s) y el año para poner primero el álbum
  original; la CLI deja de mostrar un "parecido" sin significado.

## [0.5.2] - Aviso de caché sin conexión
### Cambiado
- "Coincidencia probable" solo para el claro ganador (no para versiones en vivo o acústicas).
- Con el modo sin conexión activo, lo ya consultado sigue disponible desde la caché local y la CLI
  lo avisa.

## [0.5.1] - Fase 5.1: motor de consulta en línea (servicios gratuitos, sin clave)
### Añadido
- **MusicBrainz** (álbumes y artistas), **Cover Art Archive** (portadas) y **Wikipedia/Wikidata**
  (resumen e imagen del artista).
- Cliente HTTP con límite de tasa por servidor (MusicBrainz: 1 petición/segundo), reintentos con
  `Retry-After`, caché local de respuestas (también sirve sin conexión) y mensajes de error en
  español.
- **Modo sin conexión activo por defecto**; ajustes en `settings.json`
  (`MUSICAPP_OFFLINE`, `MUSICAPP_CONTACT`).
- CLI: `musicapp online status|on|off [--contact]`, `find-album`, `artist-info`.
- `musicapp --version` (muestra versión y ruta del código); `musicapp paths` muestra también la
  versión.
- Esquema **v4**: información de artista (`bio_url`, `bio_lang`, `image_url`, `info_fetched_at`).
### Corregido
- Una instalación no editable ejecutaba una copia vieja del código: la documentación indica
  instalar siempre con `pip install -e ".[ui,dev]"` o `uv sync --extra ui`.
- La CLI ya no muestra una traza al cortar la salida (`| head`).

## [0.4.4] - Textos largos en el editor
### Corregido
- Nombre de portada muy largo: se acorta por el medio y el botón *Quitar* no se sale del
  formulario; los campos muestran el principio del texto; los textos largos sin espacios se parten;
  mensaje claro si la imagen no existe o no se puede leer.

## [0.4.3] - Portadas en la carpeta del usuario
### Añadido
- Almacén de portadas en la carpeta de datos: `covers/chosen/` (copia de cada imagen elegida) y
  `covers/previous/` (la portada anterior de cada archivo, con `manifest.tsv`). Si no se puede
  archivar, el archivo no se modifica.
- Los datos y la caché **nunca** se guardan dentro de un entorno virtual (se usa `~/.musicapp`).
### Cambiado
- `musicapp paths` muestra la carpeta de portadas.

## [0.4.2] - Título mezclado con pista y artista
### Corregido
- Al editar archivos sin título en los tags (p. ej. `03- Ace Of Base - Happy Nation`) el título
  pasaba a ser el nombre completo. El nombre del archivo ahora rellena solo los campos que faltan
  (título, artista, nº de pista, año, álbum); tags completos nunca se tocan. Reconoce
  `03- Artista - Título`, `AAAA-Artista - Título`, `NN - Título`, `Artista - Álbum - NN - Título`
  y `Título - Artista`.
- Si solo cambian las mayúsculas de un artista o álbum al editar, gana la grafía nueva.
- Esquema **v3**: marca para releer las pistas cuyo título venía del nombre (basta `musicapp scan`).

## [0.4.1] - Aviso breve tras editar
### Cambiado
- Al terminar de guardar tags el editor se cierra solo y aparece un aviso breve (con el primer
  fallo si lo hubo); ya no hay ventana de resultado. La carpeta de respaldos se ve en
  *Ayuda ▸ Acerca de*.

## [0.4.0] - Fase 4: editor de tags
### Añadido
- Editor (álbum, pista o selección): formulario (solo se guardan los campos tocados) → revisión de
  cambios → guardado con progreso → resultado. Título y nº de pista solo para una pista.
- **Escritura segura:** copia temporal, relectura y verificación (campos y duración del audio) y
  reemplazo atómico; si algo falla el original queda intacto. ID3v2.3 por defecto (compatibilidad);
  conserva el total de `3/12`.
- Copias de respaldo opcionales y `musicapp restore <carpeta>`.
- Cambio de portada embebida (JPG/PNG).
- El guardado corre en un hilo aparte; las páginas se refrescan solas.
- Menú de aplicación (Archivo, Ver, Reproducción, Ayuda) con atajos y botón para limpiar el campo
  de búsqueda.

## [0.3.1] - Ajustes tras probar en la Mac
### Cambiado
- El botón verde del álbum refleja el estado (Reproducir / Pausar / Reanudar).
- **Artistas** como cuadrícula con portadas, igual que Álbumes.
- **Buscador nuevo:** ignora acentos y mayúsculas, combina palabras de campos distintos, ordena por
  relevancia y agrupa en Artistas / Álbumes / Canciones.
- Plurales corregidos ("1 pista").

## [0.3.0] - Fase 3: reproducción
### Añadido
- Reproducción de audio y video MP4 con QtMultimedia detrás de una interfaz propia
  (`PlayerBackend`, intercambiable por mpv o VLC).
- Cola con aleatorio y repetir (todo/una), barra de reproducción (progreso con búsqueda,
  volumen), botón *Reproducir* en cada álbum, pista actual resaltada, atajo Espacio, panel de video.
- Si un archivo falla o no existe, avisa y salta a la siguiente.

## [0.2.1] - Rutas
### Añadido
- `musicapp paths` y variables `MUSICAPP_DATA_DIR` / `MUSICAPP_CACHE_DIR`.

## [0.2.0] - Fase 2: interfaz QML
### Añadido
- Interfaz con PySide6 (Qt Quick / QML), tema oscuro y animaciones: Álbumes (cuadrícula, filtro por
  década), detalle de álbum, Artistas, *Por revisar* y búsqueda.
- Portadas: embebida, `cover.jpg`/`folder.jpg` de la carpeta o degradado de color; miniaturas
  (160/320/640 px) en caché de disco.
- `musicapp gui` y extra opcional `ui`.

## [0.1.1] - Fase 1.1: archivos sin tags
### Añadido
- Deducción de artista, título y año desde el nombre del archivo (`AAAA-Artista - Título`).
- `musicapp scan --force` y `musicapp incomplete`.
- Esquema **v2** (`tracks.inferred`) con migración automática.

## [0.1.0] - Fase 1: núcleo de biblioteca y CLI
### Añadido
- Lectura de tags de mp3 (ID3) y m4a/mp4 con `mutagen` y modelo unificado.
- Base de datos SQLite con esquema versionado (artistas, álbumes, archivos, pistas y tablas para
  letras, traducciones y listas).
- Escáner incremental (tamaño y fecha), elimina lo que desaparece y limpia álbumes/artistas
  huérfanos.
- CLI: `scan`, `stats`, `artists`, `albums`, `tracks`, `search`.
- Estructura `src/musicapp`, `pyproject.toml` y pruebas con archivos reales generados por `ffmpeg`.

## Decisiones técnicas que conviene recordar
- **Sin conexión por defecto:** la red solo se usa para portadas, datos de álbumes/artistas,
  resumen de artista y (en desarrollo) letras. Todo es gratuito y sin clave.
- **Los tags solo se escriben tras confirmar**, con verificación y respaldo opcional.
- **Qt y el GIL:** crear o destruir muchas imágenes del proveedor de portadas mientras Python tiene
  el GIL tomado puede bloquear la interfaz; por eso las señales de trabajos largos se emiten desde
  hilos de trabajo y el refresco lo dispara QML. Si volviera a ocurrir, la solución es servir las
  miniaturas como archivos precalculados.
- **Datos del usuario fuera del repositorio:** base de datos, portadas, fotos, respaldos y ajustes
  viven en las carpetas estándar del sistema (macOS: `~/Library/Application Support/musicapp`).
