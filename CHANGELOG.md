# Registro de cambios

Todos los cambios notables de Sonoteca (paquete `musicapp`) se documentan aquí.
El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y el proyecto usa
[versionado semántico](https://semver.org/lang/es/) mientras esté en alfa (0.x: la interfaz y la base de
datos pueden cambiar entre versiones; la base se migra sola con `PRAGMA user_version`).

## [0.12.15] - 2026-11-05
### Añadido
- **Almacén de preferencias de interfaz** (`core/prefs.py` + `ui/prefs_controller.py`, expuesto a QML como `prefs`): un JSON
  pequeño `ui_prefs.json` en la carpeta de datos (escritura atómica; archivo ausente o dañado = sin preferencias; si no se puede
  escribir, se conserva en memoria). Valores tipados `boolValue/intValue/stringValue` y `setBool/setInt/setString`. «Empezar
  desde cero» también lo borra. Primer uso: la **vista en cuadrícula de Listas ahora se recuerda entre sesiones**.
### Corregido
- **Las columnas de las listas se desalineaban de una canción a otra.** La duración, la etiqueta (VIDEO…) y las columnas de
  álbum/año/reproducciones cambiaban de ancho o desaparecían según los datos de cada fila. Ahora todas tienen ancho fijo
  (`Theme.durationColumn` = 60, alineada a la derecha; 48 en el panel estrecho); la columna de álbum y la de año existen en todas
  las filas de una página si la página las da (aunque una canción no tenga el dato); la etiqueta pasa al final de la columna del
  nombre. *(UI sin ejecutar; la lógica de preferencias, probada aquí con un script.)*

## [0.12.14] - 2026-11-05
### Añadido
- **Listas de reproducción en cuadrícula.** En la página Listas, dos botones (lista / cuadrícula) a la derecha de «Nueva lista»
  cambian la vista; la cuadrícula muestra la portada (collage) en tarjetas con nombre y número de canciones y duración, y se
  adapta al ancho. La vista elegida se conserva mientras la app esté abierta (aún no se guarda entre sesiones). Iconos nuevos
  `iconGrid` e `iconRows`. *(UI sin ejecutar.)*

## [0.12.13] - 2026-11-05
### Corregido
- **La app no arrancaba: «MiniPlayer.qml: id is not unique».** En la 0.12.12 reordené `MiniPlayer.qml` con un script y dejé
  la portada, el título y la animación duplicados. El archivo queda con una sola copia de cada bloque. Nuevo
  `tests/test_qml_ids.py`: ningún QML puede repetir un `id` ni tener llaves desbalanceadas. *(Ids y llaves de todos los QML
  comprobados aquí con un script; la app sin ejecutar.)*

## [0.12.12] - 2026-11-05
### Cambiado
- **Mini reproductor: el título va sobre la portada** (franja baja, con fondo oscuro de contraste y el texto en el color de
  acento) y la ventana baja a **236 px** de alto (antes 262; 328 en la 0.12.10). La portada mide 170 px y los botones quedan
  debajo.
- **Avisos emergentes arriba de la ventana** (antes abajo, donde los tapaba la barra de reproducción), incluido el de «tags
  actualizados». En el mini reproductor el aviso ya no se estrecha a 64 px. *(UI sin ejecutar.)*

## [0.12.11] - 2026-11-05
### Cambiado
- **Mini reproductor: alto al 80 %** (328 → 262 px) **y título debajo de la portada.** La portada (166 px, cuadrada) queda
  arriba, el título con desplazamiento justo debajo y la fila de botones al final. *(UI sin ejecutar.)*

## [0.12.10] - 2026-11-05
### Cambiado
- **Columnas de las listas: Nombre/Artista, Álbum, Año y Duración.** El año ahora se muestra desde filas de 360 px (antes
  solo desde 860), así también aparece en el panel «Reproduciendo» de la derecha; las reproducciones siguen en filas anchas.
  El álbum se lleva el 42 % del ancho libre (antes ~24 %, máx. 240 px), de modo que la columna del nombre ya no se estira por
  todo el espacio; los nombres largos se recortan con «…». *(UI sin ejecutar: conviene ajustar los porcentajes mirándolo.)*

## [0.12.9] - 2026-11-05
### Cambiado
- **Mini reproductor: título de la canción sobre una portada algo más pequeña.** El título va arriba en el color de acento
  (cian); si es más largo que el ancho se desplaza (pausa, recorre, pausa, vuelve) cada pocos segundos para verse completo, y si
  cabe queda centrado. La portada pasa a ser 48 px más estrecha que la ventana; el artista sigue como tooltip de la portada.
  *(UI sin ejecutar.)*

## [0.12.8] - 2026-11-05
### Añadido
- **Al guardar canciones en una lista se detecta si ya estaban.** Vale para el selector «Agregar a una lista» y para arrastrar
  canciones a una lista de la barra lateral. Si alguna ya está, un aviso pregunta: **Cancelar**, **Agregar solo las nuevas** o
  **Agregar todas** (repitiendo las que ya tiene); con una sola canción, o si todas ya estaban, **Agregar de nuevo**.
  Antes se repetían en silencio y el aviso «ya estaba» de arrastrar nunca llegaba a salir. Nuevo: `playlists.already_in`,
  `add_tracks(skip_existing=…)`, `existingCount` / `addNewTracks`. *(Lógica y UI sin ejecutar aquí.)*

## [0.12.7] - 2026-11-05
### Añadido
- **Resultados de búsqueda: botones «Nueva lista», «Guardar en lista…», «Portada e info» y «Editar tags».** Actúan sobre las
  canciones encontradas; si no hay canciones pero el resultado es un solo álbum o un solo artista, sobre las suyas.
  «Nueva lista» crea una lista de reproducción con ellas (pide el nombre); «Guardar en lista…» abre el selector de listas.
  «Portada e info» se activa cuando los resultados corresponden a un único álbum. *(UI sin ejecutar.)*

## [0.12.6] - 2026-11-05
### Corregido
- **Duplicados con nombres distintos no se encontraban**: se exigía el mismo nombre de archivo (además de artista, título,
  duración y tamaño). Ahora un duplicado es un archivo **idéntico byte a byte** (mismo tamaño y SHA-256) con cualquier
  nombre, carpeta o tags: «Canción.mp3» y «Canción (1).mp3», o una copia sin los tags corregidos. Solo se lee el contenido de
  los archivos que comparten tamaño. Es la misma prueba que ya repite el borrado, así que todo lo listado se puede eliminar con
  seguridad. Las canciones parecidas pero no idénticas (otro bitrate, otro formato) **no** se listan.
  *(Lógica probada aquí con un arnés; pytest y la UI sin ejecutar.)*

## [0.12.5] - 2026-11-05
### Cambiado
- **Icono de «Letra»**: ahora es «ABC» con dos líneas de letra debajo (antes, cuatro rayas).
### Corregido / diagnóstico
- Editar tags, arrastre por detrás (aparecía la etiqueta flotante con el título): el aviso de «editor abierto» se aplica también
  con un `Binding` en `Main.qml` (`tagEditor.visible || tagEditor.opened`), la etiqueta flotante no se muestra con el bloqueo
  activo y `DragState.begin` escribe en la consola `[arrastre] begin bloqueado=… pista=…`. Si la etiqueta sigue apareciendo,
  ese mensaje dirá si el bloqueo estaba activo. *(Sin ejecutar.)*

## [0.12.4] - 2026-11-05
### Corregido
- **Duplicados: «Unable to assign [undefined] to bool»** (`DuplicatesDialog.qml:197`): `visible` recibía `undefined` cuando el
  resultado aún no tenía `skipped`.
- **Menú de clic derecho con un espacio vacío al final** (p. ej. al eliminar un duplicado): las opciones «Eliminar archivo»
  ocupaban espacio según el momento en que se calculaba el alto. Ahora su alto es 0 si no aplican y el menú fuerza el cálculo
  de su lista (`forceLayout`) antes de mostrarse. *(Causa deducida; sin ejecutar.)*
- **Editar tags: aún se arrastraban las canciones de detrás.** Además del bloqueo de 0.12.3, ahora toda la columna principal
  se deshabilita (`enabled: !DragState.inputBlocked`) mientras el editor está abierto, y `DragState.begin` no inicia arrastres
  bloqueados. Efecto visible: los botones de detrás se ven atenuados bajo el velo. *(Sin ejecutar.)*

## [0.12.3] - 2026-11-05
### Corregido
- **Editar tags: los clics y la selección de texto en los campos afectaban a las canciones de detrás** (doble clic = reproducir,
  arrastre = arrastrar la canción). Mientras el editor está abierto, las filas de detrás ignoran clics, doble clics, hover y
  arrastres (`DragState.inputBlocked`), y el fondo del panel se traga los clics que no recibe ningún campo.
  *(Causa probable: el doble clic/arrastre de la selección de texto llegaba a `MouseArea`/`DragHandler` de las filas; no
  reproducido. QML sin ejecutar. Otros diálogos no se tocaron: basta la misma línea `onVisibleChanged` si presentan lo mismo.)*

## [0.12.2] - 2026-11-05
### Cambiado
- **«Aleatorio» en álbumes y listas ya no reproduce ni detiene nada**: solo reordena la lista de reproducción de la derecha
  (la canción que suena queda de primera) o, al quitarlo, la devuelve a su orden original. Lo que ya sonó no vuelve a
  aparecer. Lo añadido con «Reproducir a continuación» y aún sin sonar se queda justo detrás de la actual en ambos casos.
- «Reproducir» con Aleatorio activo empieza por una canción al azar. El botón «Aleatorio» se resalta mientras está activo
  (antes solo si esa lista sonaba). El panel de la derecha se actualiza al instante al activar/desactivar Aleatorio desde
  cualquier botón (páginas, barra de reproducción, mini reproductor).
*(Lógica de la cola probada aquí; la UI Qt, sin ejecutar.)*

## [0.12.1] - 2026-11-05
### Corregido
- **«Por revisar» seguía acumulando canciones con los tags ya corregidos.** Causa: para una pista sin tags de título/artista el
  editor muestra los valores deducidos del nombre del archivo, pero solo escribía los campos que el usuario cambiaba; si no
  tocaba el título o el artista, el archivo seguía sin ellos y la pista nunca salía de la lista. Ahora, al guardar una pista
  deducida, se escriben también los datos deducidos (título, artista, álbum, año, nº de pista) y la vista previa lo indica.
  *(Causa deducida leyendo el código; sin ejecutar en la Mac.)*

## [0.12.0] - 2026-10-31
Versión que cierra la tanda de «Por revisar» y doble clic (reúne la 0.11.0.1 y lo siguiente):
### Añadido
- **Eliminar archivos desde «Por revisar»**, siempre a la **papelera del sistema** (nunca borrado definitivo) y con
  confirmación:
  - **De uno en uno**: menú ⋮ ▸ *Eliminar archivo (a la papelera)…* (solo en Por revisar; desactivado con varias canciones
    seleccionadas). Sirve para archivos corruptos u otros.
  - **Duplicados por lotes**: *Buscar duplicados…* agrupa los archivos que coinciden en **artista, título, duración, nombre de
    archivo y tamaño**; en cada grupo se conserva una copia (por defecto la de mejores tags, con portada, mayor bitrate y la
    más antigua; se puede cambiar) y las demás van a la papelera tras un paso de confirmación. Antes de mover cada copia se
    **verifica su contenido (SHA-256)** contra la que se conserva; si difiere o la conservada no existe, no se toca.
- «Por revisar» incluye como **posible archivo dañado** las pistas sin duración.
- Lo que se elimina se quita también de la lista de reproducción (y se detiene si suena).
### Cambiado (0.11.0.1)
- Por revisar solo lista pistas sin artista o con artista/título deducidos del nombre; el doble clic conserva la lista e
  inserta la canción de primera (también con Aleatorio); menú con *Reproducir ahora (conserva la lista)* y *Vaciar y reproducir*.

## [0.11.0.1] - 2026-10-31
### Cambiado
- **Por revisar**: las canciones que ya tienen en sus tags el artista y el título salen de la lista aunque aún no tengan
  álbum ni portada. Solo quedan las que no tienen artista o cuyo artista/título se dedujo del nombre del archivo.
- **Doble clic en una canción** (lista, búsqueda, álbum, artista, Inicio): se conserva la lista de reproducción y esa canción
  se inserta de primera (también con *Aleatorio*); la que sonaba sale de la lista. Sin lista, empieza una solo con esa canción.
  Se eliminó la ventana de pregunta «vaciar o conservar».
- **Menú ⋮ de las canciones**: *Reproducir ahora (conserva la lista)* y *Vaciar y reproducir* (la lista queda solo con esas canciones).

## [0.11.0] - 2026-10-30
Versión que cierra la tanda posterior a la 0.10.0 (reúne la 0.10.0.1 y lo siguiente):
### Añadido
- **Listas y álbumes**: botón *Aleatorio* (activa el modo aleatorio y empieza por una canción al azar; si la lista ya suena,
  lo alterna) y el botón *Reproducir* pasa a **Detener** mientras suena esa lista (pausa y vuelve al inicio, sin tocar la
  lista de reproducción). Cada reproducción recuerda su origen (`player.sourceKey`: `album:<id>` / `playlist:<id>`).
- **Mini reproductor**: botones *Aleatorio* y *Silencio* (0.10.0.1).
### Cambiado
- **Doble clic en una canción** (álbum, búsqueda, artista, Inicio, Por revisar): a la lista de reproducción solo entra esa
  canción (si ya hay una lista, se pregunta si se vacía o se conserva, como antes).
- **Clic en una canción de una lista guardada**: la lista de reproducción queda con esa canción al principio y las anteriores
  desaparecen; con *Aleatorio* activo se conserva la lista completa, en orden aleatorio y empezando por esa canción.
### Corregido
- **Historial de navegación con estado**: Álbumes recuerda la década (y la posición), Artistas la posición y las páginas de
  los artistas visitados su estado (0.10.0.1).

## [0.10.0.1] - 2026-10-30
### Añadido
- **Mini reproductor**: botón *Aleatorio* (resaltado cuando está activo) y botón de **silencio**; la ventana mini pasa a 264 × 328.
### Corregido
- **Historial de navegación con estado**: al volver atrás/adelante, *Álbumes* recuerda la década que se estaba revisando
  (y la posición), *Artistas* la posición de la lista y las páginas de los artistas visitados su estado (canciones
  destacadas desplegadas y posición).

## [0.10.0] - 2026-10-29
Versión que cierra la tanda de ajustes pedida tras la 0.9.6; reúne los cambios de la 0.9.7 a la 0.9.12:
- Silencio total desde el icono de volumen, con tooltip (0.9.7) y «Agregar al final de la lista» (0.9.7).
- La lista de reproducción solo guarda lo que falta por sonar: lo que termina o se salta sale de ella (0.9.8).
- «Reproducir a continuación» se distingue con bandas de acento a ambos lados (0.9.9).
- Columnas responsivas en todas las listas: pista · nombre/artista · álbum · año · reproducciones (0.9.10).
- Mini reproductor: ventana compacta, siempre visible, con portada y botones (0.9.11).
- Formato estándar de servidores alternativos (descriptor v1) con importación (0.9.12).

## [0.9.12] - 2026-10-29
### Añadido
- **Formato estándar para servidores alternativos** (descriptor v1, `*.sonoteca-server.json`): un JSON versionado que
  declara un servidor de letras (protocolo `lrclib`) y/o de portadas e información (`musicbrainz-ws2`, `coverartarchive`,
  `mediawiki-rest`) y, opcionalmente, su `rate_limit`. Se importa con *Servidores de letras y portadas… ▸ Importar
  descriptor…* o `sonoteca server-import archivo.json`; valida con mensajes claros, agrega (o actualiza por `id`) y **nunca
  activa solo**. Documentación y esquema: `docs/SERVIDORES.md`, `docs/sonoteca-server.schema.json`, ejemplo en
  `docs/ejemplos/`.
- El limitador de tasa respeta el `min_interval_ms` declarado para los servidores alternativos activos.

## [0.9.11] - 2026-10-29
### Añadido
- **Mini reproductor**: un icono en la esquina derecha de la barra de reproducción (o Ver ▸ *Mini reproductor*,
  Ctrl+Shift+M) encoge la ventana principal a una ventana pequeña (240 × 304), siempre visible encima de las demás, con la
  **portada del álbum** (o la del artista si el álbum no tiene; un marcador si no hay ninguna) y los botones anterior,
  reproducir/pausar y siguiente. El título y el artista salen como tooltip de la portada. El icono de la esquina de la
  portada devuelve la ventana completa con su tamaño, posición y estado anteriores. Las teclas multimedia y los atajos
  siguen funcionando.

## [0.9.10] - 2026-10-29
### Cambiado
- **Columnas responsivas en todas las listas** (álbum, artista, inicio, búsqueda, listas guardadas y Reproduciendo): con la
  lista ancha (≥ 860 px) cada canción muestra *pista · nombre con el artista debajo · álbum · año · reproducciones*; al
  estrecharse (≥ 560 px) solo *pista · nombre/artista · álbum*; al mínimo, *pista · nombre/artista*. Se decide por el ancho
  de la propia lista, no de la ventana (el panel derecho ya reduce el centro). La duración y el menú ⋮ se mantienen siempre.
- El año de la canción usa el del álbum cuando la canción no lo tiene. Todas las filas comparten los umbrales y las
  anchuras de columna definidos en `Theme.qml`.

## [0.9.9] - 2026-10-28
### Añadido
- **«Reproducir a continuación» se distingue en la lista**: las canciones añadidas así llevan bandas de acento a ambos
  lados y un fondo tenue, distintas del resto de la lista y de la que suena. Lo último que se añade suena antes que lo
  añadido anteriormente, y entra en el mismo recuadro. La marca desaparece sola cuando la canción empieza a sonar
  (también al saltar a ella con doble clic). «Agregar al final de la lista» no marca.

## [0.9.8.1] - 2026-10-28
### Documentación
- `CONTEXT_COMPACT.md` reescrito y compactado (estado actual, trampas técnicas y pendientes ordenados).

## [0.9.8] - 2026-10-28
### Cambiado
- **La lista de reproducción solo guarda lo que falta por sonar**: cada canción que termina, y la que sonaba cuando se
  salta a otra (doble clic en la lista, en un álbum con «conservar la lista», siguiente…), sale de la lista. Al terminar
  la última, la lista queda vacía y la canción sigue visible en el reproductor. «Anterior» recupera lo último que sonó.
  Con repetir-todo las canciones pasan al final en lugar de salir (si no, no habría nada que repetir); con repetir-una no
  sale ninguna. Con aleatorio funciona igual.

## [0.9.7] - 2026-10-28
### Cambiado
- El icono de volumen es un botón con tooltip: activa y desactiva el **silencio total** (el volumen elegido se conserva; el
  deslizador muestra 0 mientras tanto y mover el volumen quita el silencio).
- La opción del menú ⋮ «Agregar a la lista actual» ahora dice «Agregar al final de la lista».

## [0.9.6] - 2026-10-28
### Cambiado
- **Panel derecho siempre presente**: muestra la lista *Reproduciendo*. *Letra* la reemplaza por la letra de la canción
  que suena y, al quitar la letra, vuelve la lista. El icono *Reproduciendo* (Ctrl+4) devuelve la lista desde la letra y,
  con la lista a la vista, pliega/despliega el panel. «Reproduciendo» deja de ser una página del centro: el centro queda
  libre para álbumes, artistas y búsquedas.
- La lista del panel tiene un modo compacto (título y botones más cortos, filas más estrechas; las acciones aparecen sobre
  la duración al pasar el ratón). «Ver letra» de una canción concreta sigue abriendo la letra en el centro.

## [0.9.5] - 2026-10-27
### Corregido
- **Teclas multimedia** (reproducir/pausa, siguiente, anterior) no se reconocían: la aplicación no tenía ningún manejador y
  macOS no las envía como eventos de teclado. Ahora un filtro de eventos las reconoce con la ventana en primer plano
  (todos los sistemas) y, en macOS, Sonoteca se registra en `MPRemoteCommandCenter`/`MPNowPlayingInfoCenter` para recibirlas
  también en segundo plano. Nueva dependencia solo en macOS: `pyobjc-framework-MediaPlayer`. `SONOTECA_DEBUG_MEDIA=1`
  muestra lo que se recibe. Pendiente: teclas globales en Windows (SMTC) y Linux (MPRIS).

## [0.9.4] - 2026-10-27
### Cambiado
- **Menú izquierdo con iconos**: la barra lateral pasa de 230 a 72 px. Cada sección (Inicio, Álbumes, Artistas, Listas,
  Reproduciendo, Letra, Por revisar) es un icono y su nombre aparece como *tooltip*; los contadores (listas, canciones en
  cola, pendientes de revisar) son insignias en la esquina del icono. Arriba va el logo (con las estadísticas de la
  biblioteca en su tooltip) y abajo el estado de la conexión (clic = alternar modo en línea).
- Las listas desplegables de la barra muestran su miniatura (el nombre y las canciones, en el tooltip) y siguen aceptando
  canciones arrastradas.
- Los tooltips de toda la aplicación usan el estilo del tema.

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
