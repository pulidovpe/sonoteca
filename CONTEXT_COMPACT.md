# Sonoteca — CONTEXTO COMPACTO (v1.0.13)

> Pégalo al inicio de un chat nuevo del **agente principal** (app, sincronización, Android). Va **junto con el árbol del repo**: lo más seguro es
> `git archive --format=zip -o ~/Desktop/sonoteca-arbol.zip HEAD` desde la rama de trabajo, ya fusionada con `origin/main` (el zip de mis entregas
> no trae `.github/`, ni el `2.json` de Room que genera el build, ni lo que Pablo cambie fuera de mis zips). El agente de CI tiene SU propio contexto:
> `docs/agentes/CONTEXT_COMPACT_AGENTES.md`. Historial antiguo por versión: `docs/HISTORIAL_CONTEXTO.md`.

## Rol y forma de trabajar con Pablo (Pablo Pulido, `pulidovpe`)
- Actúa como arquitecto e ingeniero de software con +20 años en entornos locales multiplataforma: razonar antes de responder, basarse en documentación oficial reciente
  (puedes usar `web_search`: las versiones de Android/Gradle cambian y tu conocimiento termina antes), **admitir incertidumbre, preguntar lo crítico, no declarar «probado» lo
  que no se ejecutó**. **Responder en español, conciso.** Entregas en partes cortas (una cosa por mensaje).
- **En cada entrega: comandos git exactos + commit de una línea + zip descargable** (publícalo con `present_files`; sin eso no hay enlace) con CHANGELOG, versión
  (`src/sonoteca/__init__.py`, regex `\d+\.\d+\.\d+`) y este contexto al día. Cada vez decir **qué se verificó (y con qué) y qué no**.
- **Zips**: construirlos con lista explícita de rutas (`src tests docs packaging android assets README.md CHANGELOG.md CONTEXT_COMPACT.md pyproject.toml LICENSE .gitignore
  .gitlab-ci.yml`), **sin `.github/` ni `docs/CI.md`** (mi copia queda vieja y `unzip -o` pisaría la buena de `main`: pasó con `android.yml`), sin `__pycache__`, `.DS_Store`,
  `pytest.log`, carpetas `tmp*`/`hsperfdata_*` ni `build/`.
- **Orden de aplicación de un zip (decírselo siempre)**: commit de lo pendiente → `git fetch origin && git merge origin/main` → `unzip -o` → `git status` y `git diff --stat` (revisar que no cambie
  nada de `.github`/`docs/CI.md`; si cambia, `git checkout origin/main -- .github docs/CI.md`) → commit. Nunca copiar carpetas con Finder (reemplaza y borra: ya pasó).
- **Zips = SOLO los archivos que cambian en esa entrega** (más CHANGELOG, `__init__.py` y este contexto), no el árbol entero: mi copia de `tests/` y `src/` puede estar vieja y un `unzip -o` pisó
  las correcciones de lint de `main` (2026-11-17, 9 archivos; arreglado con `git checkout origin/main -- tests src/sonoteca/player/qt_backend.py`). Si `git diff --stat` muestra archivos que la entrega no menciona, restaurarlos desde `origin/main`.
  Pablo debe pasarme un árbol fresco (`git archive` tras fusionar `origin/main`) al empezar un chat nuevo.
- Nada se cambia en archivos/tags de música sin confirmar.
- **Entorno de Claude (limitado)**: bash sin red, Python con `cryptography`, `java` 21 (sin `javac`/Kotlin/Android SDK). **No hay pytest, PySide6, mutagen, ruff.** Se prueba la lógica pura de
  Python con un corredor propio (no está en el repo): módulo `pytest` falso (`fixture`, `raises(match=)`, `mark.parametrize`, `tmp_path`, `monkeypatch`) + `MagicMock` para los módulos de
  `mutagen`, con `PYTHONPATH=src:tests`. El Kotlin **nunca** se compila aquí: lo compila Pablo en Android Studio (y la CI). Se pueden validar protocolos con un programa Java de un solo archivo
  (`java Archivo.java`) contra el servidor Python. Usa rutas absolutas y `bash -c` (el shell por defecto es `sh`: sin `<( )`).

## Estado (2026-11-17)
- **App de escritorio** (Python 3.12 + PySide6/QML, SQLite **esquema v10**): ver «Qué es / Mapa / UI / Trampas» abajo. Versión actual **1.0.13**. `feature/android` ya se fusionó en `main` (PR #5).
- **Sincronización con Android** (HECHA y verificada por USB con tu biblioteca): servidor HTTPS en `src/sonoteca/sync/` (`manifest, merge, pairing, tls, server, usb`), comandos `sonoteca sync-serve [--solo-usb]
  [--sin-adb]` y `sync-devices`. Protocolo en `docs/SYNC.md`. Decisiones: identidad estable `tracks.uuid` + `files.content_hash` (SHA-256 con caché); **HTTPS autofirmado con la huella fijada** al
  emparejar (código de 6 dígitos de un solo uso → token); listas con `uuid`/`updated_at` y «última modificación gana» + `deleted_playlists`; manifiesto con `pending_hash` (si > 0, **no se borra nada local**);
  se sincroniza audio (portadas y letras existen en el servidor, sin cliente aún); **sin video**. `--solo-usb` ejecuta `adb reverse` solo (Intro lo repite y da código nuevo).
- **Migraciones** (`docs/MIGRACIONES.md`): `migrate()` copia a `library.db.v<N>.bak` (API de copia de SQLite) ANTES de subir el esquema; aparta tablas ajenas con nombre de v10 a `<nombre>_incompatible`;
  v10 se autorrepara. **Desarrollo siempre con `SONOTECA_DATA_DIR=$HOME/sonoteca-dev`**, nunca la biblioteca real (la real quedó en v10 por un descuido mío: el binario 1.0.0 ya no la abre;
  `~/Library/Application Support/sonoteca/library.db.v9.bak` es la vía de vuelta; hay otras copias manuales de Pablo y del otro agente: no tocar).
- **App Android** (`android/`, Kotlin 2.2.10 + Compose + Room; paquete `io.github.pulidovpe.sonoteca`): `net/` (PairingInfo, PinnedTls, SyncApi con HttpsURLConnection, ManifestModel), `db/` (Room **v2**,
  `AutoMigration(1,2)`: tracks, playlists, playlist_tracks, downloads), `download/` (Naming, Plan, FileDownloader reanudable con `Range` + SHA-256, TrackDownloader → MediaStore `Music/Sonoteca/<Artista>/<Álbum>/`),
  `Selection`, `SyncRepository`, `MainViewModel`, `MainActivity` (pestañas Artistas/Álbumes/Listas). **Toolchain verificada**: AGP 9.5.1 (Kotlin integrado: SIN plugin `kotlin-android`), Gradle 9.6.0, KSP 2.3.10,
  Room 2.8.5 (`androidx.room`; Room 3 existe, sin usar), Compose BOM 2026.02.01, **JDK 25** (`gradle-daemon-jvm.properties`), compileSdk/targetSdk 37, minSdk 29. Avisar al agente de CI si cambia compileSdk, JDK o AGP.
- **Fases Android**: 1 servidor+v10 ✅ · 2 proyecto, Room, TLS fijado, emparejado, manifiesto ✅ (1609 pistas y 11 listas en el POCO) · 3a descarga por artista ✅ (183 MB reales) · 3b álbum/listas/borrar del teléfono ✅ (1.0.11: Pablo verificó en el POCO por USB álbum, artista, lista, borrar y volver a descargar; CI Android verde, 34 pruebas JVM) ·
  1.0.12 catálogo se renueva solo al emparejar ✅ (pipelines verdes, probado en el POCO) ·
  **1.0.13 = `adb reverse` automático al reconectar el cable (`UsbWatcher`; SIN verificar con adb real)** · 4 reproductor Media3 + UI, crear/editar listas en el móvil y subirlas con `PUT` · 5 Wi-Fi/USB pulidos (NSD, QR, permiso `ACCESS_LOCAL_NETWORK` de Android 17
  por `targetSdk 37`) · 6 Windows/Linux · cierre **1.1.0** (etiqueta `v1.1.0`; APK firmado y PyInstaller con `cryptography`, aún sin probar).
- **Huecos conocidos**: descarga en segundo plano (WorkManager: versión sin verificar), limpiar descargas huérfanas, portadas/letras en el móvil, qué hace Android con los archivos de `Música/Sonoteca` tras desinstalar y reinstalar
  (sin verificar), pruebas de instrumentación (no hacen falta y fallan en Xiaomi).

## Entorno de Pablo (comandos que funcionan)
- Mac M4 Pro, zsh. Repo: `/Users/pulidovpe/workspace/mis-proyectos/sonoteca` (rama de trabajo `feature/android`). El comando `sonoteca` de su venv apunta a la carpeta VIEJA `musicapp/src` (1.0.0): usar
  `PYTHONPATH=src /Users/pulidovpe/workspace/mis-proyectos/musicapp/venv/bin/python -m sonoteca …` (a ese venv hubo que instalarle `cryptography`) o `VENV_DIR=venv ./packaging/dev_setup.sh`.
- Servidor: `export SONOTECA_DATA_DIR="$HOME/sonoteca-dev"` y `… -m sonoteca sync-serve --solo-usb` (la cabecera imprime la carpeta de datos: **comprobarla** en cada terminal nueva; sin el `export` usa la biblioteca real). GUI de prueba:
  igual con `… -m sonoteca gui`. Si el certificado cambia (otra carpeta de datos) el móvil rechaza: «Olvidar» y emparejar de nuevo.
- Móvil de pruebas: POCO X6 5G (Xiaomi 23122PCD1G, Android 16, HyperOS 3.0.302), serie adb `729d2b6f`; adb en `~/Library/Android/sdk/platform-tools/adb`; hay también el emulador `Medium_Phone_API_36.1` (con dos
  dispositivos adb exige `-s <serie>`). Android Studio «Rabbit 2 | 2026.2.2 Patch 1».
- Android Studio: ejecutar SIEMPRE con la configuración **`app`** (Android App, módulo `Sonoteca.app`; se creó a mano). **Nunca «Tests in…»/«All Tests»**: son pruebas de instrumentación, instalan y DESINSTALAN la app y en Xiaomi fallan por
  `INSTALL_GRANT_RUNTIME_PERMISSIONS`. Pruebas JVM: panel Gradle `app ▸ Tasks ▸ other ▸ testDebugUnitTest`. `adb reverse` se pierde al reiniciar adb o reconectar el cable. Tras Run, en Xiaomi la app puede no abrirse sola.
- Biblioteca: ~9 GB de música (1609 pistas, 11 listas); el POCO tiene 256 GB y ~90 GB libres.
- Pablo no responde siempre a todas las preguntas de un mensaje: confirmar lo crítico una a una. Pega marcadores como `<TU_BASE_V10>` literalmente si no se le avisa: dar comandos sin marcadores.

## Agentes y CI (resumen; detalle en `docs/agentes/` y `docs/CI.md`)
- Dos agentes: **principal** (yo: `src/ tests/ android/ packaging/` y el resto de `docs/`) y **ci** (`.github/**`, `docs/CI.md`, la sección «Pipelines» del README). No se ven: **Pablo copia los archivos**. **Desde 2026-11-17 (orden de Pablo) NO se crean más archivos en
  `docs/agentes/canal/`**: toda actualización para el agente de CI va SOLO en `docs/agentes/CONTEXT_COMPACT_AGENTES.md` (sección «Novedades de principal»; se actualiza ese archivo, no se crean otros).
  Al empezar una sesión, leer lo último del canal (histórico, hasta 2026-11-17) y atender lo dirigido a `principal` que siga abierto.
- CI verde en GitHub: `ci.yml` (ruff E4/E7/E9/F, higiene, pytest con 26 fallos heredados de v1.0.0 en `.github/known-failures.txt`: no añadir ninguno), `android.yml` (JDK 25; pruebas JVM + APK debug), `build.yml` (tag `v*`; compiló en los 3 sistemas a mano,
  la rama de publicar con tag NO se ha ejercitado; riesgo abierto: `sync/`/`cryptography` en PyInstaller, arreglo en `packaging/sonoteca.spec`, que es mío).
- Corregir los 26 tests viejos se aplazó (rama `fix/…` aparte, sin tocar `tests/test_sync_*`).

## Qué NO se ha verificado nunca (no afirmarlo)
`UsbWatcher` con adb real (formato de `adb reverse --list`); ejecución de las pruebas Python con pytest real/ruff en mis entregas (las verifica la CI); GUI/Qt; PyInstaller con `sync/`; Wi-Fi (solo USB probado); Android 17; WorkManager.


## Qué es
Reproductor/organizador **local** de música (mp3, m4a, mp4 video; ~2000 archivos) por artista/álbum/año, con editor de tags. Internet **solo** opcional (portadas, fichas de artista, letras, traducción); **modo sin conexión por defecto**. Python 3.12 + PySide6/QML, SQLite (`PRAGMA user_version`, esquema **v10**). Paquete `sonoteca` (antes `musicapp`; `core/legacy.py` migra datos viejos). Licencia MIT. Instalar: `VENV_DIR=venv ./packaging/dev_setup.sh` (o `pip install -e ".[ui,dev]"`); ejecutar `sonoteca gui`; `python -m sonoteca` sin instalar con `PYTHONPATH=src`. Variables: `SONOTECA_DATA_DIR/CACHE_DIR/NO_PRUNE/SELFTEST/DEBUG_MEDIA` (`MUSICAPP_*` aún aceptadas).

## Mapa (`src/sonoteca/`)
- `core/`: `db.py` (migraciones v1-v9), `library_folders.py` (registro de carpetas, exclusiones), `tags.py`, `scanner.py`, `library.py`, `covers.py` (embebida > carpeta > `albums.cover_path` descargada), `cover_store.py`, `tag_writer.py`, `tag_edit.py`, `search.py`, `playlists.py`, `lyrics.py` (LRC, `save_manual`), `stats.py`, `cleanup.py`, `review.py` (Por revisar: re-escanear/descartar), `portable.py` (exportar/importar `.sonoteca`, **reset “empezar de cero”**, se aplican al arrancar), `legacy.py`, `paths.py`.
- `online/`: `http.py` (límites por host, caché), `settings.py` (+servidores alternativos), `servers.py` (URL base activa de LRCLIB/MusicBrainz/CAA/Wikipedia), `musicbrainz/coverart/wikipedia/enrich/lrclib/lyrics/translate.py`, `harvest.py` (descarga automática de portadas/fotos tras escanear: solo música bien identificada, aviso de tiempo, cancelable).
- `player/`: `queue.py` (`PlayQueue`; **`consume_played`**), `backend.py`, `qt_backend.py`, `devices.py`.
- `ui/`: controladores expuestos a QML (`library`, `player`, `online`, `playlists`, `lyrics`, `scanner`, `harvest`, `portable`, `serverConfig`, **`prefs`** = preferencias de interfaz en `ui_prefs.json`, `core/prefs.py`; úsalo para cualquier preferencia nueva); `media_keys.py` + `media_keys_macos.py` (teclas multimedia; macOS vía PyObjC `MPRemoteCommandCenter`); `app.py`; `qml/*.qml`.
- `packaging/`: `sonoteca.spec` (PyInstaller + poda de Qt), `build_mac.sh` (7 pasos + `build.log`), `build_win.ps1`, `build_linux_docker.sh`, `dev_setup.sh`, `check_bundle.py` (sin datos personales), `make_icons.py`. `docs/COMPILAR.md` (manual), `docs/TEMA.md`. `assets/icons/`. `.gitlab-ci.yml` (nunca ejecutado).

## UI actual (resumen)
Barra lateral de **iconos** (72 px, `win.sidebarWidth`; `SideButton` icon+badge, texto = tooltip `AppToolTip`) · logo arriba (tooltip con estadísticas) · globo de conexión abajo · tema «Neón» (`Theme.qml`: cian `#00d0fc`, azul `#0396fd`, violeta `#9849fd`, magenta `#ba38fc`, fondo `#060e16`; **todos los colores son tokens**).
**Panel derecho siempre presente** (`rightPanel`, `rightMode` queue|lyrics, `rightCollapsed`): por defecto la lista **Reproduciendo** (`win.queuePage`, `QueuePage.panel`, `ListTrackRow.compact`); **Letra** la reemplaza y al quitarla vuelve la lista; el icono Reproduciendo (Ctrl+4) vuelve a la lista o pliega/despliega el panel. `showSection('queue')` ya no navega.
Barra de reproducción: enlaces a artista/álbum de la pista actual, icono de salida de audio (altavoz/audífonos/pantalla, tooltip), **icono de volumen = silencio total** (`player.muted/toggleMute`), slider y botón play con degradado cian→magenta.
Lista de reproducción: **`consume_played`** (lo que termina o se salta sale de la lista; «Anterior» recupera; repetir-todo rota al final; repetir-una no consume). «Vaciar» conserva la pista que suena. Menú ⋮: «Agregar al final de la lista», «Reproducir a continuación», «Ir al artista/álbum»; doble clic en canción suelta con lista en marcha ⇒ `QueueChoiceDialog` (vaciar o conservar). Reordenar solo arrastrando.
Archivo ▸ Internet, Servidores de letras y portadas, Descargar portadas, Exportar/Importar biblioteca, Empezar desde cero.

## Trampas técnicas (no repetir)
- **QML**: nunca nombrar una propiedad `on`+Mayúscula (`onAccent` rompió la carga; usar `textOnAccent`); cada QML nuevo va en `qmldir`; cada controlador nuevo se registra en `ui/app.py` **y** en `tests/conftest.py` (`qml_env`); `Action` no tiene `shortcuts`; no llamar `data` a una propiedad; no escribir `Theme.icon…` literal en comentarios (el test de tokens lo detecta); **sin colores fijos fuera de `Theme.qml`** (`tests/test_theme.py`); tooltips con `AppToolTip`; emitir señales desde hilos de trabajo; `Theme.dataRevision++` refresca páginas; escapes `\uXXXX` solo dentro de cadenas QML (no en comentarios); navegación: `stack.replace` desde `render(loc)` (sin push/pop).
- **Edición de QML con scripts**: nunca reordenar bloques con índices de texto sin releer el resultado (0.12.12 duplicó ids en `MiniPlayer.qml`); `tests/test_qml_ids.py` lo vigila.
- **Columnas de fila**: anchos fijos (`Theme.durationColumn`, `albumColumn`, `yearColumn`…); `album`/`year` de `TrackRow`/`ListTrackRow` son `var` (`undefined` = la página no tiene esa columna; si la tiene, existe en todas las filas).
- **Python**: `PlayQueue.items` es el almacén, no el orden: usar `order_ids()`; cierre ordenado en `app.py` (`del engine` antes de liberar controladores); nunca `open(f,"w").write(open(f).read())`; versión solo en `src/sonoteca/__init__.py` (regex `\d+\.\d+\.\d+(\.\d+)?`).
- **Empaquetado**: PyInstaller no compila de forma cruzada; `.venv-build` se recrea siempre; lanzar scripts con `./…` o `bash`.
- LRCLIB/DeepL según documentación; DeepL Free 500 000 car./mes (HTTP 456); sin verificar en vivo.
