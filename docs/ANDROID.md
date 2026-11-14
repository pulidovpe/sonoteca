# App Android de Sonoteca (carpeta `android/`)

Kotlin nativo: Jetpack Compose (UI), Room con KSP (base local), Media3 (audio, fase 4). Protocolo con el escritorio: `docs/SYNC.md`.
Toolchain verificada (2026-11): AGP 9.5.1 con Kotlin integrado (no se aplica el plugin `kotlin-android`), Gradle 9.6.0, Kotlin 2.2.10,
KSP 2.3.10, Room 2.8.5 (`androidx.room`; Room 3 `androidx.room3` queda para más adelante), compileSdk/targetSdk 37, minSdk 29.

## Estado por fases
| Fase | Contenido | Estado |
|---|---|---|
| 1 | Esquema v10 y servidor de sincronización (Python) | hecha (1.0.1) |
| 2 | Proyecto Android, Room, cliente HTTPS con huella fijada, emparejado, manifiesto, lista de artistas | **esta** (1.0.3) |
| 3 | Descarga de música (MediaStore `Music/Sonoteca/`, reanudable, SHA-256) | pendiente |
| 4 | Reproductor Media3 + UI por artista, álbum y listas (creadas o nuevas) | pendiente |
| 5 | Wi-Fi y USB pulidos (NSD, QR, permiso de red local) | pendiente |
| 6 | Windows y Linux | pendiente |

## Estructura (`app/src/main/java/io/github/pulidovpe/sonoteca/`)
- `net/`: `PairingInfo` (URL `sonoteca-sync://pair?...`), `PinnedTls` (confianza por huella SHA-256 del certificado),
  `SyncApi` (HttpsURLConnection), `ManifestModel` (parser). Sin clases de Android → se prueban en la JVM.
- `db/`: entidades Room (`tracks`, `playlists`, `playlist_tracks`), `LibraryDao`, `AppDatabase`.
- `SyncRepository`, `MainViewModel`, `PairingStore` (SharedPreferences privadas), `MainActivity` (Compose).
- Pruebas JVM: `app/src/test/.../net/` (usan un certificado y un manifiesto generados por el servidor real).

## Decisiones y salvedades
- Si el manifiesto trae `pending_hash > 0`, NO se borran pistas locales (las que aún no tienen huella no aparecen en él).
- El esquema de Room es v1 y no hay migraciones todavía: al cambiarlo durante el desarrollo, desinstala la app del móvil.
- El token de emparejamiento queda en `SharedPreferences` privadas de la app (almacenamiento protegido por Android, sin cifrado adicional).
- **Red local (Android 17)**: con `targetSdk = 37` el acceso a la LAN queda bloqueado por defecto en Android 17; hará falta declarar y pedir
  `ACCESS_LOCAL_NETWORK` (o usar el selector de NSD). En Android 16 (el POCO) la LAN está abierta. Se resuelve en la fase 5. Por USB
  (`adb reverse`) la app habla con `localhost`.
