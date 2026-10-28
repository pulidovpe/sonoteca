# Registro de cambios

Todos los cambios notables de Sonoteca (paquete `musicapp`) se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[versionado semántico](https://semver.org/lang/es/) mientras esté en alfa (0.x: la interfaz y la base de
datos pueden cambiar entre versiones; la base se migra sola con `PRAGMA user_version`).

## [0.9.3.1] - 2026-10-27
### Corregido
- La app no arrancaba con el tema nuevo (`Theme.qml: Cannot assign a value to a signal`): el token `onAccent` se
  interpretaba como manejador de señal. Se renombró a `textOnAccent` y una prueba impide nombres `on` + Mayúscula.

## [0.9.3] - 2026-10-27
### Añadido
- **Tema «Neón»** basado en la paleta del logo: fondo azul casi negro, acento cian `#00d0fc` y degradado cian → violeta en el
  botón de reproducir y en los deslizadores. Todos los colores están en `Theme.qml` como tokens (documentados en
  `docs/TEMA.md`); se eliminaron los ~40 colores fijos repartidos por las pantallas y una prueba impide que vuelvan.
### Cambiado
- Los botones principales y las fichas activas usan el acento cian; las portadas sin imagen toman tonos cian–violeta.

## [0.9.2.3] - 2026-10-27
### Cambiado
- `build_mac.sh` muestra los pasos `[1/7]…[7/7]`, guarda un `build.log`, indica en qué paso falla y al final imprime la
  ruta de `dist/Sonoteca.app` y del zip. Se corrigió un fallo latente: con `pipefail`, el listado de «carpetas más pesadas»
  podía abortar el script antes de crear el zip.
- Se silencia el aviso informativo `qt.multimedia.ffmpeg: Using Qt multimedia with FFmpeg…` (los errores se siguen mostrando).

## [0.9.2.2] - 2026-10-27
### Añadido
- `packaging/dev_setup.sh`: recrea el entorno de desarrollo e instala el proyecto en modo editable con una comprobación
  final (`VENV_DIR=venv` para una carpeta sin punto). Soluciona `ModuleNotFoundError: No module named 'sonoteca'`.
### Cambiado
- `.gitignore` y el manual de compilación excluyen también `venv/`, `build/` y `dist/`.

## [0.9.2.1] - 2026-10-27
### Corregido
- Al cerrar la ventana aparecían errores `Cannot call method 'stats' of null` / `Cannot read property 'revision' of null`:
  los controladores se destruían antes que la interfaz QML. Ahora el cierre es ordenado (`app.py`).
- `build_mac.sh`: fallaba con `No such file or directory: .venv-build/bin/python3.12` si existía un `.venv-build`
  antiguo o copiado de otra máquina. Ahora se borra y recrea siempre, elige un Python 3.12/3.13/3.11 disponible y se
  relanza con bash si se ejecutó con `sh`. Igual en `build_win.ps1`.

## [0.9.2] - 2026-10-26
### Añadido
- **Icono de la aplicación**: `assets/icons/` (logo original, PNG, `.ico` para Windows y `.icns` para macOS) generado con
  `packaging/make_icons.py` (fondo transparente, sin halo). El spec de PyInstaller lo incrusta en el `.exe` y en el `.app`;
  la ventana usa `src/sonoteca/ui/icon.png`; el paquete de Linux incluye `sonoteca.png` y una plantilla `sonoteca.desktop`.

## [0.9.1.1] - 2026-10-26
### Documentación
- `docs/COMPILAR.md`: manual para generar el binario en macOS, Windows y Linux (con Docker o sin él) desde una carpeta
  copiada a otra máquina: qué copiar, requisitos, comandos, verificación, solución de problemas y CI.

## [0.9.1] - 2026-10-24
### Añadido
- **Servidores alternativos** (Archivo ▸ *Servidores de letras y portadas…*): se pueden agregar servidores de letras
  (compatibles con la API de LRCLIB) y de portadas/información (compatibles con MusicBrainz, Cover Art Archive y/o
  Wikipedia) y usarlos **en lugar del servicio predeterminado**. Cada dirección se valida (http/https, sin usuario ni
  contraseña), hay botón *Probar* y se puede volver al predeterminado en cualquier momento. La fuente de las letras
  descargadas muestra el nombre del servidor.
- **Empezar desde cero** (Archivo ▸ *Empezar desde cero…* y `sonoteca reset --yes`): vacía la biblioteca (base de
  datos, portadas y fotos descargadas, caché de miniaturas) al volver a abrir la app. Guarda antes una copia en
  `backups/` (se puede desactivar) y conserva los ajustes y claves. No toca los archivos de música.
- El menú ⋮ de una canción tiene **Ir al artista** e **Ir al álbum** (si existen; con una sola canción seleccionada).
### Cambiado
- Se quitaron los botones de flecha arriba/abajo de las listas y de «Reproduciendo»: se reordena arrastrando.

## [0.9.0.1] - 2026-10-24
### Corregido
- `packaging/sonoteca.spec`: la poda de Qt maneja listas y TOC de PyInstaller de forma explícita.
### Documentación
- Guía de actualización desde `musicapp`: reinstalar en modo editable (`pip uninstall musicapp` y `pip install -e ".[ui,dev]"`)
  para que exista el comando `sonoteca`; alternativa sin instalar: `python -m sonoteca`.

## [0.9.0] - 2026-10-24
### Cambiado
- **Renombrado completo a Sonoteca**: paquete `sonoteca`, comando `sonoteca` (y `sonoteca-gui`), carpetas de datos y
  caché `sonoteca`, variables `SONOTECA_*` (las `MUSICAPP_*` se siguen aceptando).
- Al primer arranque se **migran los datos** de la instalación anterior (`musicapp`): se mueven a las carpetas
  nuevas la base de datos, portadas, fotos de artistas, copias de respaldo y ajustes; se reescriben las rutas de
  portadas guardadas en la base y se pasa la clave de DeepL del llavero. Nunca sobrescribe una biblioteca nueva.
- El paquete ejecutable arranca siempre con una **biblioteca vacía** en la carpeta de datos del usuario; el script
  `packaging/check_bundle.py` comprueba que no lleve bases de datos, ajustes, letras ni portadas.
### Añadido
- **Descarga automática de portadas y fotos** después de escanear: solo música bien identificada (tags reales) y solo
  lo que falta; coincidencias dudosas se dejan para elegir a mano. Muestra cuánto puede tardar (aviso destacado si
  son más de 5 minutos), se puede cancelar y ocultar, y no repite lo ya intentado durante 30 días.
  Archivo ▸ *Descargar portadas e información…* y `sonoteca harvest`. No modifica los archivos de música. Esquema **v8**.
- **Exportar / importar la biblioteca** (`.sonoteca`): base de datos, listas, letras, contadores y portadas/fotos
  descargadas; sin ajustes ni claves. Al importar se confirma, se guarda una copia de la biblioteca actual y se puede
  indicar la nueva carpeta de música. Archivo ▸ *Exportar/Importar biblioteca…*, `sonoteca export` y `sonoteca import`.

## [0.8.9] - 2026-10-24
### Añadido
- `CHANGELOG.md`.
- `packaging/build_linux_docker.sh`: binario de Linux (x86_64 o arm64) construido dentro de Docker.
- Prueba de humo del empaquetado (`MUSICAPP_SELFTEST=1`) en los scripts de compilación y en el CI.
### Cambiado
- Nombre visible de la aplicación: **Sonoteca** (título de ventana y `Sonoteca.app`). El paquete, el comando
  `musicapp` y las carpetas de datos conservan el nombre interno `musicapp`.
- Empaquetado más pequeño: el spec de PyInstaller poda los módulos QML y bibliotecas de Qt que la app no usa
  (WebEngine, 3D, Charts, estilos de Controls distintos de Basic, traducciones de Qt…). Lista en `build/pruned.txt`;
  `MUSICAPP_NO_PRUNE=1` lo desactiva.
- Licencia MIT a nombre de Pablo Pulido.

## [0.8.8] - 2026-10-24
### Añadido
- Botón **Cambiar imagen…** en la ficha del artista: cambia solo la foto (JPG/PNG, hasta 5 MB), sin internet y sin
  tocar la descripción; funciona aunque el artista no tenga descripción.
- Licencia MIT y README de la versión alfa; scripts `packaging/build_mac.sh` y `build_win.ps1`.

## [0.8.7] - 2026-10-24
### Cambiado
- **Vaciar la lista** de reproducción ya no detiene la pista que suena: queda como única de la lista.
- La salida de audio (icono de caja acústica, audífonos o pantalla) va aparte del volumen.
### Añadido
- La barra de reproducción muestra enlaces al **artista** y al **álbum** de la pista que suena (solo si existen),
  disponibles desde cualquier página.

## [0.8.6.1] - 2026-10-24
### Corregido
- La interfaz no cargaba: `IconButton.qml` usaba `ToolTip` sin importar `QtQuick.Controls`.

## [0.8.6] - 2026-10-24
### Añadido
- Botón **Ir al artista** en la página del álbum.
- **Por revisar**: *Re-escanear tags* (relee los archivos de la lista sin red), *Vaciar lista* (oculta sin tocar
  archivos ni tags; persiste tras escanear) y *Restaurar descartadas*. Esquema de base de datos **v7**.
- **Letra**: búsqueda automática con internet activo al abrir el panel o cambiar de canción, y botón
  *Agregar/Editar texto* para escribir o pegar la letra (con marcas `[mm:ss]` queda sincronizada; fuente «Manual»,
  nunca se reemplaza sola).
- Icono de la salida de audio activa (altavoz, audífonos o pantalla) con tooltip del dispositivo.
- Fase 7 iniciada: versión dinámica en `pyproject.toml`, spec de PyInstaller, `.gitlab-ci.yml`
  (lint, higiene del repositorio, pruebas y paquetes por sistema operativo).

## [0.8.5] - 2026-10-24
### Añadido
- Página de lista con cabecera como la de un álbum (portada o collage, «LISTA», nombre y descripción:
  «Con A, B y C» + número de canciones y duración).
- Al reproducir una canción suelta con una lista en marcha, un diálogo pregunta si se vacía la lista o se conserva
  (la canción suena ya y la lista continúa después).
- **Letra** en panel lateral derecho mientras suena una canción, para dejar libre el centro.

## [0.8.4]
### Añadido
- Canciones destacadas por artista: máximo 5 (si hay más, 4 + «Mostrar más»).
- Una reproducción cuenta tras 3 s de sonar, desde cualquier origen.
- Collage de portada en las listas (2-4 álbumes).
- «¿Artista equivocado?»: elegir otro artículo de Wikipedia o escribir descripción e imagen propias.
- Selección de la salida de audio (se recuerda y sigue la predeterminada al conectar audífonos).
- Ventana **Buscar música** (se abre sola con la biblioteca vacía; Ctrl+Shift+O).

## [0.8.3]
### Añadido
- Historial adelante/atrás (Alt+←/→, Ctrl+[ ]), canciones destacadas por artista, miniaturas en las listas y
  página **Inicio** (la app arranca ahí).

## [0.8.2]
### Añadido
- Listas desplegables en la barra lateral; arrastrar canciones a una lista y reordenarlas arrastrando; botón ⋮
  en las filas.
### Corregido
- Se perdía `__version__` por un archivo vaciado al escribirlo.

## [0.8.1]
### Añadido
- «Reproduciendo» (cola) con su menú y página; contador de reproducciones (esquema v6); el distintivo «En línea»
  alterna el modo; limpieza automática de álbumes y artistas vacíos.

## [0.8.0] — Fase 6
### Añadido
- Letras sincronizadas desde LRCLIB (línea resaltada, clic = ir a ese punto), traducción con DeepL alineada
  por línea, caché en la base y vistas original / traducción / ambas.
- El editor de tags muestra la portada actual y la nueva.

## [0.1 – 0.7] — Fases 1 a 5
Resumen por fase (no se registró el detalle por versión):
- **Fase 1**: núcleo y CLI: escaneo incremental de mp3/m4a/mp4 en SQLite, búsqueda y estadísticas.
- **Fase 2**: interfaz QML de navegación por álbum, artista y década.
- **Fase 3**: reproducción de audio y video.
- **Fase 4**: editor de tags con escritura sobre copia temporal y verificación, y respaldo restaurable.
- **Fase 5**: portadas e información en línea opcionales (MusicBrainz, Cover Art Archive, Wikipedia); la app
  funciona sin conexión por defecto.
