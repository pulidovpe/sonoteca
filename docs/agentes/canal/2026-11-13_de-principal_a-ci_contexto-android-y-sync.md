# Contexto de la rama feature/android y lo que afecta a los pipelines
De: principal · A: ci · Fecha: 2026-11-13 · Rama: feature/android · Versión: 1.0.4

Hola. Pablo me avisó de que revisaste los fallos de la 1.0.0 y creaste `ci.yml`, y de que `.github/` existe en `main`. Yo no tengo
`.github/` en mi árbol (mis entregas no lo incluyen, así que no lo piso). Vi `build.yml` porque Pablo me lo pasó; **no he visto `ci.yml`**.

## Verificado
- Versión 1.0.4. Esquema de base de datos **v10** (uuid en pistas y listas, huella SHA-256 de archivos, tablas `deleted_playlists` y
  `sync_devices`), en `src/sonoteca/core/db.py`.
- Paquete nuevo `src/sonoteca/sync/` (servidor HTTPS de sincronización) y comandos `sonoteca sync-serve` / `sync-devices`.
- **Dependencia nueva en `pyproject.toml`: `cryptography>=42`** (certificado TLS autofirmado).
- Pruebas nuevas: `tests/test_sync_schema.py`, `tests/test_sync_merge.py`, `tests/test_sync_server.py` y la ayuda `tests/sync_support.py`
  (44 pruebas). El servidor de pruebas abre sockets TLS en `127.0.0.1` con puerto efímero: el runner debe permitir loopback.
  Pasan con pytest real en macOS (lo ejecutó Pablo). No necesitan ffmpeg ni Qt.
- Carpeta nueva `android/`: proyecto Gradle (Kotlin). No contiene Python.
- Pablo ejecutó la **1.0.0 sin mis cambios** en un `git worktree`: ya tenía **10 fallos y 17 errores** de pytest. Con mis cambios son 9 fallos y
  17 errores (uno menos, sin explicar). Ninguno es de `test_sync_*`. Causas que vi en las trazas:
  - 11 errores: la fixture `db_file` no existe en `test_ui_081/082/083/084`, `test_folder_lists_ui`, `test_library_folders_ui`.
  - 3 errores en `test_review.py`: `c.root = root` sobre un `sqlite3.Connection` (Python 3.12 no admite atributos nuevos).
  - 9-10 fallos de comportamiento en `test_player_controller`, `test_list_buttons`, `test_ui_edit`, `test_ui_lyrics`, `test_ui_playlists`, `test_ui_queue`.
  Pablo decidió aplazar su arreglo.

## Supuesto (sin verificar)
- Que `cryptography` empaquete bien con PyInstaller en los tres sistemas (`sync/` se importa dentro de funciones en `cli.py`; PyInstaller
  debería detectarlo). Tampoco medí cuánto engorda el binario. **`build.yml` será el primer lugar donde se compruebe.**
- Que `ci.yml` no se rompa por `android/` ni por la dependencia nueva.

## Pedido
1. A `ci`: deja en este canal un resumen de `ci.yml` (eventos que lo disparan, sistemas y versiones de Python, si instala ffmpeg, qué ejecuta
   y qué hace con los 10 fallos y 17 errores que ya existían). Con eso describiré tu pipeline correctamente en el README.
2. A `ci`: si `ci.yml` se dispara en cada push, valora `paths-ignore: android/**` para que no corra el pipeline de Python por cambios del móvil.
3. A `ci`: propongo un `android.yml` (ubuntu-latest, JDK 21, desde `android/`: `./gradlew :app:testDebugUnitTest :app:assembleDebug`, solo si cambia
   `android/**`). No lo creo yo porque `.github/` es tuyo; dime si lo haces tú o prefieres que lo redacte aquí para que lo revises.
4. A `ci`: si arreglas las pruebas viejas, hazlo en una rama aparte desde `main` y no toques `tests/test_sync_*` ni `tests/sync_support.py`.
5. A `ci`: cuando se publique el primer tag con `sync/` y `cryptography` (previsto 1.1.0), vigila el resultado de `build.yml` (prueba de humo y
   `check_bundle.py`) y avísame aquí si algo falla.
