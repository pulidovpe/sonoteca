# App Android de Sonoteca (carpeta `android/`)

> **Pruebas con el escritorio**: ejecuta `sonoteca sync-serve` solo con `SONOTECA_DATA_DIR` apuntando a un directorio de desarrollo
> (copia segura de la biblioteca en [`docs/MIGRACIONES.md`](MIGRACIONES.md)), nunca con la biblioteca real.

Kotlin nativo: Jetpack Compose (UI), Room con KSP (base local), Media3 (audio, fase 4). Protocolo con el escritorio: `docs/SYNC.md`.
Toolchain verificada (2026-11): AGP 9.5.1 con Kotlin integrado (no se aplica el plugin `kotlin-android`), Gradle 9.6.0, Kotlin 2.2.10,
KSP 2.3.10, Room 2.8.5 (`androidx.room`; Room 3 `androidx.room3` queda para más adelante), compileSdk/targetSdk 37, minSdk 29.

## Estado por fases
| Fase | Contenido | Estado |
|---|---|---|
| 1 | Esquema v10 y servidor de sincronización (Python) | hecha (1.0.1) |
| 2 | Proyecto Android, Room, cliente HTTPS con huella fijada, emparejado, manifiesto, lista de artistas | hecha y verificada en el POCO (1609 pistas, 11 listas) |
| 3a | Descarga por artista: motor reanudable con verificación SHA-256, publicación en `Music/Sonoteca/` (MediaStore), resumen y confirmación | hecha y verificada en el POCO (183 MB) |
| 3b | Pestañas Artistas / Álbumes / Listas con descarga en cada nivel y «Borrar del teléfono» con confirmación | 1.0.11, **verificada** en el POCO por USB (álbum, artista, lista, borrar); 1.0.12 renueva el catálogo al emparejar, sin verificar |
| 3c | Descarga en segundo plano (WorkManager), limpiar descargas huérfanas, portadas y letras | pendiente |
| 4a | **Reproductor local** (Media3 1.11.0): toca lo descargado en el teléfono, sin servidor ni cable; mini reproductor, notificación y segundo plano | 1.0.14: compila y reproduce en el POCO (pestaña Descargado, sin servidor, pantalla apagada y bloqueada); notificación, bloqueo, auriculares y llamadas ✅; **1.0.18** añade aleatorio, repetir y cola, sin verificar |
| ~~4b~~ | ~~Crear/editar listas en el móvil~~ | aplazada por decisión de Pablo (2026-11-18) |
| 4c | **Estadísticas**: el móvil anota las reproducciones sin conexión y las sube al escritorio al conectar | servidor 1.0.15 ✅ (CI verde); móvil 1.0.16, **sin verificar** |
| 5 | Wi-Fi y USB pulidos (NSD, QR, permiso de red local) | pendiente |
| 6 | Windows y Linux | pendiente |

## Estructura (`app/src/main/java/io/github/pulidovpe/sonoteca/`)
- `net/`: `PairingInfo` (URL `sonoteca-sync://pair?...`), `PinnedTls` (confianza por huella SHA-256 del certificado),
  `SyncApi` (HttpsURLConnection), `ManifestModel` (parser). Sin clases de Android → se prueban en la JVM.
- `db/`: entidades Room (`tracks`, `playlists`, `playlist_tracks`), `LibraryDao`, `AppDatabase`.
- `playback/`: `PlaybackQueue` y `PlayCounter` (lógica pura: recorte de la cola, URI permitidas, formato de tiempo, cuándo cuenta una reproducción; se prueban en la JVM), `PlaybackService` (`MediaSessionService` + ExoPlayer) y
  `PlayerController` (MediaController + estado para la UI).
- `SyncRepository`, `MainViewModel`, `PairingStore` (SharedPreferences privadas), `MainActivity` (Compose).
- Pruebas JVM: `app/src/test/.../net/` (usan un certificado y un manifiesto generados por el servidor real).

## Decisiones y salvedades
- Si el manifiesto trae `pending_hash > 0`, NO se borran pistas locales (las que aún no tienen huella no aparecen en él).
- El esquema de Room es v1 y no hay migraciones todavía: al cambiarlo durante el desarrollo, desinstala la app del móvil.
- El token de emparejamiento queda en `SharedPreferences` privadas de la app (almacenamiento protegido por Android, sin cifrado adicional).
- **Red local (Android 17)**: con `targetSdk = 37` el acceso a la LAN queda bloqueado por defecto en Android 17; hará falta declarar y pedir
  `ACCESS_LOCAL_NETWORK` (o usar el selector de NSD). En Android 16 (el POCO) la LAN está abierta. Se resuelve en la fase 5. Por USB
  (`adb reverse`) la app habla con `localhost`.

## Reproductor (fase 4a)
- Solo reproduce **lo descargado en el teléfono** (entradas de MediaStore que la app publicó) y **no necesita servidor, cable ni Wi-Fi**. Sin streaming.
- Cuatro pestañas: Artistas, Álbumes, Listas y **Descargado** (todas las pistas bajadas, en orden de artista/álbum/pista; tocar una la reproduce y sigue con las siguientes).
  Desde el resumen de un artista/álbum/lista, **«Reproducir las N descargadas»** (las listas suenan en su orden).
- Mini reproductor abajo: título, artista, barra de avance con salto, anterior/pausa/siguiente, y (1.0.18) **Aleatorio**, **Repetir** (sin repetir → todas → una, como en el escritorio) y **Cola (N)**.
  Aleatorio y repetir se recuerdan entre sesiones. El servicio (`PlaybackService`) sigue sonando con la pantalla apagada o la app en segundo plano,
  con notificación y controles de pantalla de bloqueo/auriculares; se pausa solo con llamadas y al desconectar los auriculares. En Android 13+ se pide el permiso de notificaciones al primer «reproducir».
- **Cola** (hoja inferior «Reproduciendo»): toda la lista con la pista que suena resaltada; tocar una pista salta a ella; «Quitar» saca una (no la que suena); «Vaciar» deja solo la que suena (como en el escritorio).
  En la pestaña «Descargado», el menú ⋮ de cada pista ofrece «Reproducir a continuación» y «Agregar al final de la cola»; el resumen de un artista/álbum/lista, lo mismo con todo lo descargado.
  **Diferencia con el escritorio:** aquí lo ya reproducido NO sale de la lista (queda en la cola y se puede volver a ella); y todavía no se reordena arrastrando.
- La cola se recorta a 500 pistas alrededor de la elegida (los mensajes entre la app y el servicio no deben ser enormes).
- Sin emparejamiento: con catálogo guardado la biblioteca se muestra igual («Sin emparejar») y se puede reproducir; «Descargar» queda desactivado y aparece «Emparejar».
- El servicio solo abre URIs `content://media/…` (la sesión puede recibir peticiones de otras apps).
- Salvedades (sin verificar): Xiaomi/HyperOS puede cerrar el servicio con la batería «optimizada» (ajusta la app a «Sin restricciones»); si borras del teléfono lo que está sonando, el reproductor
  mostrará un error de reproducción; no se reordena la cola arrastrando todavía.

## Estadísticas de reproducción (fase 4c)
- El servicio de reproducción cuenta una reproducción **a los 5 s de avance normal** (decisión de Pablo, igual que el escritorio desde 1.0.17; saltar con la barra, retroceder o pausar no suma; una pista de menos de 5 s cuenta entera;
  como mucho una vez por reproducción; repetir la misma pista cuenta otra). Cuenta aunque la app esté cerrada. Cada una se guarda en Room (`play_events`: id único, pista, fecha UTC) sin necesidad de red.
- Se suben al escritorio (`POST /v1/plays`, docs/SYNC.md) **al abrir la app** si el escritorio está al alcance (en silencio), al **sincronizar** (antes del catálogo) y al **emparejar**. Se borran del móvil solo al recibir el 200;
  si falla, quedan guardadas y se reintentan (el escritorio ignora las repetidas: no se cuenta doble). La pantalla principal muestra «N reproducciones por subir».
- Aún sin verificar en el móvil. El total de reproducciones por pista que trae el manifiesto (`plays`) no se usa todavía: servirá para el «Inicio» («más escuchado»).

## Descargas (fase 3a)
- Se elige un artista (fila de la lista) → resumen (pistas que faltan, tamaño, espacio libre; se deja un margen de 200 MB) → «Descargar».
- Cada pista se baja a `cache/downloads/<uuid>.part` con `Range` (se **reanuda** si se corta), se comprueba tamaño y SHA-256 contra el catálogo y **solo
  entonces** se publica en `Música/Sonoteca/<Artista>/<Álbum>/NN - Título.ext` con MediaStore. Nunca queda un archivo a medias en la música del teléfono.
- Una pista cuenta como descargada si la huella guardada coincide con la del catálogo; si el escritorio la cambió, se baja de nuevo (se borra antes la anterior).
- Room v2 (`downloads`): migración automática desde v1. Al compilar aparece `app/schemas/.../2.json`: **debe versionarse** (base de futuras migraciones).
- Room v3 (`play_events`, 1.0.16): `AutoMigration(2, 3)` (solo una tabla nueva; usa el `2.json` versionado). Al compilar aparece `app/schemas/.../3.json`: **hay que versionarlo** (`git add android/app/schemas`).
- Salvedades: la descarga vive en la app en primer plano (si Android la detiene, se reanuda al repetir; el segundo plano llega en 3b); no se detecta lo que
  una instalación anterior dejó en `Música/Sonoteca` (el catálogo de descargas es de Room: desinstalar y reinstalar puede duplicar; **sin verificar** cómo
  trata Android la propiedad de esos archivos); no se borra nada de lo descargado desde la app todavía.

## Pestañas y borrado (fase 3b)
- Tres pestañas: **Artistas** (agrupa por artista del álbum), **Álbumes** y **Listas**. Cada fila muestra `descargadas/total`; tocarla abre el mismo resumen de la fase 3a.
- Una lista descarga sus pistas **sin repetir** y solo las que ya están en el catálogo (una pista aún sin huella en el escritorio no cuenta hasta la próxima sincronización).
- Si hay algo descargado de la selección, el resumen ofrece **«Borrar N descargadas del teléfono»** → confirmación → borra la entrada de MediaStore y el registro de Room. **No toca el escritorio ni el
  catálogo.** Una pista cuenta «en el teléfono» aunque su descarga esté desactualizada. Si Android no deja borrar un archivo, se informa cuántos fallaron y se conserva su registro.
