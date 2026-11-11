# Sonoteca

<p align="center"><img src="assets/icons/sonoteca.png" width="128" alt="Icono de Sonoteca"></p>

[![Licencia: MIT](https://img.shields.io/badge/licencia-MIT-green.svg)](LICENSE)
![Versión: 1.0](https://img.shields.io/badge/versi%C3%B3n-1.0-blue.svg)

Sonoteca es un reproductor y organizador de **música local** de escritorio: tu biblioteca de mp3, m4a y mp4 (video) organizada por artista, álbum y año, con edición de tags. Funciona **sin conexión por defecto**; internet es opcional y solo se usa para portadas, información de artistas y álbumes, letras y traducción.

> **Versión 1.0 (primera estable).** Las funciones principales están completas y se usan a diario. La interfaz se ha validado sobre todo en **macOS**; en **Windows** y **Linux** también funciona, con menos horas de uso (ver «Estado»). Haz copia de tu música antes de editar tags o eliminar archivos en masa (la app guarda una copia de respaldo en cada edición: `sonoteca restore`; los archivos eliminados van a la papelera, nunca se borran de forma definitiva).

## Funciones
- Biblioteca incremental (~miles de archivos) por **artista, álbum y década**, con búsqueda.
- Reproducción de audio y video, lista «Reproduciendo» (arrastrar para ordenar), **sesión recordada** (al abrir, vuelven en pausa la lista, la canción y el punto, Aleatorio, repetir y volumen), **mini reproductor**, historial adelante/atrás, salida de audio seleccionable y teclas multimedia.
- **Listas guardadas** con collage de portadas, en vista de lista o **cuadrícula**; avisa si una canción ya está en la lista. En cualquier lista de canciones: **ordenar por columna** (nombre, artista, álbum, año, más escuchadas), **álbum como enlace** y **selección de canciones concretas** para agregarlas a una lista.
- **Editor de tags** que muestra la ruta completa del archivo, con verificación (escribe en una copia y comprueba antes de reemplazar) y sección **Por revisar** para canciones incompletas, con búsqueda de **archivos duplicados** y eliminación segura a la papelera.
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

## Aplicación empaquetada
Aún no hay binarios publicados. PyInstaller no compila de forma cruzada: **cada sistema se construye en ese sistema** (o en Docker, para Linux).

**Tamaño del binario:** cada compilación termina con un informe de tamaño por categorías y lo compara con la anterior (`packaging/size_report.py`); si el binario crece, dice qué categoría y qué versión de PySide6 lo causó, y las versiones se pueden fijar para compilar (`packaging/build-constraints.txt`). Ver [`docs/COMPILAR.md`](docs/COMPILAR.md), «Tamaño del binario».

```bash
./packaging/build_mac.sh            # macOS   -> dist/Sonoteca.app + dist/Sonoteca-<versión>-macos-<arq>.zip
./packaging/build_linux_docker.sh   # Linux   -> dist/Sonoteca-<versión>-linux-<arq>.tar.gz (requiere Docker)
.\packaging\build_win.ps1            # Windows -> dist\sonoteca\sonoteca.exe + .zip (en una máquina Windows)
```
**Manual paso a paso para cada plataforma: [`docs/COMPILAR.md`](docs/COMPILAR.md).**
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

### Servidores alternativos
Por defecto se usan servicios públicos y gratuitos: **LRCLIB** para las letras y **MusicBrainz + Cover Art Archive + Wikipedia** para portadas e información. En Archivo ▸ *Servidores de letras y portadas…* puedes agregar los tuyos y elegir cuál usar **en lugar** del predeterminado:
- *Letras*: un servidor compatible con la API de LRCLIB (p. ej. una instancia propia): la dirección es la raíz de la API, como `https://mi-servidor/api`.
- *Portadas e información*: direcciones compatibles con MusicBrainz (`…/ws/2`), Cover Art Archive y/o Wikipedia (`https://{lang}.mi-wiki.org`; `{lang}` es el idioma de la ficha). Los que dejes vacíos siguen usando el servicio por defecto.

**Formato estándar:** un servidor se puede describir en un archivo `*.sonoteca-server.json` e importarlo con *Importar descriptor…* (o `sonoteca server-import`); ver [`docs/SERVIDORES.md`](docs/SERVIDORES.md).

Las direcciones deben ser `http://` o `https://` y no pueden llevar usuario ni contraseña; *Probar* comprueba que el servidor responde con el formato esperado. Se guardan en `settings.json`.

### Empezar desde cero
Archivo ▸ *Empezar desde cero…* (o `sonoteca reset --yes`) vacía la biblioteca —base de datos, listas, letras, portadas y fotos descargadas— y se completa al volver a abrir la aplicación. Antes guarda una copia en `backups/` (puedes desactivarla). No borra tus archivos de música y conserva tus ajustes y claves.

### Panel derecho
A la derecha siempre hay un panel: por defecto muestra la lista **Reproduciendo** (arrastra para reordenar, clic derecho para más acciones). Lo que se añade con **Reproducir a continuación** se resalta con bandas de acento a ambos lados hasta que le toca sonar. **Letra** (icono del menú o Ctrl+6) la reemplaza por la letra de la canción que suena; al volver a pulsarlo, vuelve Reproduciendo. El icono **Reproduciendo** (Ctrl+4) devuelve la lista si estaba la letra y, si ya está a la vista, pliega o despliega el panel para ganar espacio.

### Mini reproductor
El icono de la esquina de la barra de reproducción (o Ver ▸ *Mini reproductor*, Ctrl+Shift+M) encoge la ventana a un modo
compacto, siempre visible: la portada del álbum (o del artista) con el **título de la canción encima** (si es largo, se desplaza
cada pocos segundos para leerlo completo), y debajo los botones de aleatorio, anterior, reproducir/pausar, siguiente y silencio.
El icono de la esquina de la portada devuelve la ventana completa. Solo está disponible mientras hay una canción cargada.

### Reproducir desde una lista
- **Reproducir / Detener** en cada álbum y lista guardada («Detener» aparece mientras suena esa lista). **Aleatorio** no reproduce ni detiene nada: **reordena la lista «Reproduciendo»** de la derecha al azar (la canción que suena queda de primera) o la devuelve a su orden original; lo que ya sonó no vuelve a aparecer. Con Aleatorio activo, *Reproducir* empieza por una canción al azar.
- **Doble clic en una canción** de un álbum, búsqueda, artista o Inicio **conserva la lista de reproducción y pone esa canción
  de primera** (también con Aleatorio); sin lista, empieza una solo con esa canción. El menú ⋮ ofrece *Reproducir ahora (conserva
  la lista)* y *Vaciar y reproducir*.
- **Clic en una canción de una lista guardada**: la lista de reproducción empieza en esa canción (las anteriores no se
  añaden); con *Aleatorio* activo se conserva la lista completa, en orden aleatorio.

### Listas de canciones
Todas las listas muestran las canciones igual, con columnas de ancho fijo y alineadas: *pista · nombre con el artista debajo · álbum · año · reproducciones · en lista · duración* (en ventanas muy anchas el artista pasa a una columna propia). Al reducir la ventana (o abrir paneles) se ocultan primero el artista en columna, luego las reproducciones, «En lista», el álbum y, en paneles muy estrechos, el año. Los nombres largos se recortan con «…».
- **Ordenar:** la primera fila trae los títulos de columna (*Nombre, Artista, Álbum, Año, Más escuchadas*). Un clic ordena; otro invierte el sentido; el tercero vuelve al orden original (*Más escuchadas* empieza por las que más suenan). Las canciones sin dato (sin año o sin álbum) quedan al final. En una lista guardada el orden elegido es solo una vista: el orden guardado no cambia y mientras tanto no se puede reordenar arrastrando. La lista «Reproduciendo» de la derecha no lleva cabecera (su orden es el de reproducción). **Por revisar** solo muestra *Nombre, Tags* (¿ya tiene tags?), *Tipo* (video o música) y *Duración*, y las cuatro ordenan.
- **Álbum y artista como enlaces:** pulsar el álbum o el artista de una fila abre su página (Inicio, búsqueda, artistas, listas…). El artista tiene columna propia solo si la ventana es ancha; si no, va debajo del nombre.
- **En lista:** una columna con ✓ indica si la canción ya está en alguna lista guardada (el tooltip dice en cuáles).
- **Seleccionar canciones:** en un álbum o en los resultados de búsqueda, *Seleccionar canciones* pone una casilla en cada fila; la barra inferior permite *Seleccionar todas*, crear una *Nueva lista* o *Guardar en lista…* solo con las marcadas.
- **Resultados de búsqueda:** botones *Nueva lista*, *Guardar en lista…*, *Portada e info* (cuando los resultados son de un único álbum) y *Editar tags*.

### Listas guardadas
La página **Listas** se ve en lista o en **cuadrícula** (botones de la derecha; se recuerda entre sesiones). Al agregar canciones a una lista —desde el selector o arrastrándolas a la barra lateral— si alguna ya está, pregunta si agregar solo las nuevas, todas (repitiendo) o cancelar.

### Preferencias de interfaz
Las preferencias de la interfaz (como la vista de Listas) se guardan en `ui_prefs.json`, en la carpeta de datos (`sonoteca paths`). Es un archivo pequeño que puedes borrar sin riesgo; «Empezar desde cero» también lo borra.

### Teclas multimedia
Reproducir/pausa, siguiente y anterior del teclado funcionan con la ventana en primer plano en cualquier sistema. En **macOS**
también funcionan con la app en segundo plano: Sonoteca se registra como la aplicación de «Ahora suena» (necesita
`pyobjc-framework-MediaPlayer`, que se instala solo con `pip install -e ".[ui]"` en Mac). Mientras suene otra aplicación que
macOS considere «Ahora suena» más reciente (el navegador, Música…), las teclas irán a esa; empieza a reproducir en Sonoteca
para recuperarlas. En Windows y Linux las teclas globales (con la ventana sin foco) no están implementadas todavía.
Para diagnosticar: `SONOTECA_DEBUG_MEDIA=1 sonoteca gui` muestra cada tecla recibida y el estado de la integración.

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
La sección **Por revisar** (Ctrl+3) lista las canciones sin artista o con el artista/título deducidos del nombre del archivo; las que ya tienen artista y título en sus tags no aparecen, aunque les falte el álbum o la portada. Al guardar en el editor de tags una canción de esta lista se escriben también los datos deducidos del nombre del archivo (título, artista, álbum, año, nº de pista; la vista previa lo indica), así que sale de la lista. **Eliminar archivos:** en esta sección el menú ⋮ de una canción tiene *Eliminar archivo (a la papelera)…* (de uno en uno, con confirmación) y el botón *Buscar duplicados…* tiene dos pestañas: *Archivos idénticos* (exactamente el mismo contenido, aunque tengan otro nombre, carpeta o tags; se verifica el contenido antes de eliminar) y *Misma canción, otro bitrate o formato* (mismo artista y título y duración casi igual, p. ej. un MP3 a 128 y otro a 320 kbps; por defecto se conserva la de mayor bitrate y antes de eliminar se comprueba que siga siendo la misma canción). En ambos casos se mueven a la papelera, por lotes, las copias sobrantes que elijas. Nada se borra de forma definitiva: todo va a la papelera del sistema. *Re-escanear tags* vuelve a leer los archivos de la lista; *Vaciar lista* las oculta sin tocar archivos ni tags; *Restaurar descartadas* las devuelve.

## Estado
**Hecho:** biblioteca, reproducción, editor de tags verificado, Por revisar con duplicados, listas, letras y traducción, modo en línea opcional, exportar/importar, mini reproductor, teclas multimedia en macOS y empaquetado (PyInstaller) para macOS, Windows y Linux.

**Limitaciones conocidas:**
- La interfaz se valida a mano sobre todo en macOS; Windows y Linux funcionan pero tienen menos pruebas (compilación: `docs/COMPILAR.md`). En Windows, si editas los tags de la canción que suena, el archivo se actualiza al terminarla, cambiar de pista o cerrar la app (la app ya muestra los tags nuevos).
- Vídeo AV1/HEVC: según el equipo puede sonar sin imagen; la app lo avisa.
- La app de macOS no está firmada ni notarizada (clic derecho ▸ *Abrir* la primera vez).
- Teclas multimedia con la ventana sin foco: solo en macOS.
- Aún no hay: importar/exportar listas M3U, listas inteligentes, reproducción sin pausas entre pistas (gapless).
- Capturas de pantalla en este README: pendientes.

Si encuentras un error, abre una incidencia con la versión (`sonoteca --version`), el sistema operativo y, si la app no arranca, el mensaje que aparece al ejecutar `sonoteca gui` en una terminal.

## Desarrollo
```bash
ruff check src tests && pytest     # pytest requiere ffmpeg para generar archivos de prueba
```
`.gitlab-ci.yml` ejecuta lint, pruebas y paquetes por sistema operativo. Los cambios se registran en [`CHANGELOG.md`](CHANGELOG.md). El repositorio **no debe contener letras** (tienen copyright; viven solo en la base local). Estado y decisiones del proyecto: `CONTEXT_COMPACT.md`.

**Actualizando desde `musicapp`** (`zsh: command not found: sonoteca`): el entorno virtual sigue teniendo instalado el paquete antiguo. Dentro del proyecto y con el entorno activado:
```bash
pip uninstall -y musicapp && pip install -e ".[ui,dev]" && hash -r
sonoteca --version
```
(con `uv`: `uv sync --extra ui --extra dev` y `uv run sonoteca gui`). Sin instalar nada también sirve `PYTHONPATH=src python -m sonoteca gui`.

**`ModuleNotFoundError: No module named 'sonoteca'`** (el comando existe pero el paquete no se encuentra): el entorno virtual quedó desconectado del código (carpeta movida o sustituida, otro Python…). Se arregla recreándolo:
```bash
deactivate 2>/dev/null; VENV_DIR=venv ./packaging/dev_setup.sh    # sin VENV_DIR crea «.venv»
```

Si un comando nuevo «no existe»: `sonoteca --version` muestra de dónde se ejecuta el código; si apunta a `site-packages`, la instalación no es editable. Reinstala con `pip install -e ".[ui,dev]"`.

## Licencia y contacto
[MIT](LICENSE). Repositorio: <https://github.com/pulidovpe/sonoteca> · Contacto: pulidovpe.dev@gmail.com (también en «Acerca de Sonoteca»). Las letras, portadas y textos descargados pertenecen a sus titulares y a las fuentes indicadas (Wikipedia: CC BY-SA).
