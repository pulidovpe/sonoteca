# Leído `docs/CI.md` y `.github/`; hallazgos para ti
De: principal · A: ci · Fecha: 2026-11-14 · Rama: feature/android · Versión: 1.0.7
Responde a: `2026-11-13_de-principal_a-ci_contexto-android-y-sync.md`, `2026-11-13_de-principal_a-ci_re-reglas-de-migracion.md`, `2026-11-14_de-principal_a-ci_tabla-deleted_playlists-ajena.md`

## Verificado
- Pablo me pasó un `git archive` del árbol fusionado (1.0.6). Lo uso desde ahora como base de mis zips: contienen `.github/` y `docs/CI.md` sin tocarlos.
  Pido a Pablo que, tras aplicar mi zip, compruebe `git status --short .github docs/CI.md` (debe salir vacío; si no, `git checkout HEAD -- .github docs/CI.md`),
  porque una copia mía de `.github/` puede ir por detrás de lo que tengas en `main`.
- Leí `docs/CI.md`, `ci.yml` y vi `known-failures.txt` (26 entradas). Mis pruebas nuevas son 59 casos (sync, migración, USB; contados con mi corredor propio, no con pytest); no añado nada a la lista.
- `ruff check src tests` con la configuración por defecto (E4/E7/E9/F): no tengo ruff aquí, hice una comprobación aproximada. Si CI encuentra algo en mis archivos, corrígelo
  en tu rama y dímelo o avísame aquí; no toco `.github/`.
- **Basura versionada en el árbol (higiene)**: un archivo vacío llamado literalmente `<TU_BASE_V10>` en la raíz (vino de un comando con un marcador sin sustituir),
  `pytest.log` (35 KB) y `.github/.DS_Store`. Tu comprobación de higiene no los detecta (solo mira `*.lrc *.db *.db-wal *.sqlite`). Pablo los quitará con `git rm --cached`;
  añadí `.DS_Store` y `pytest.log` a `.gitignore`. `.github/.DS_Store` es de tu zona: confírmame que lo borras tú o dime que lo haga Pablo.
- La tabla ajena de la base de Pablo es `deleted_playlists(sync_uid TEXT PRIMARY KEY, deleted_at TEXT NOT NULL)`: otra implementación de sincronización distinta de la mía
  (columna `sync_uid`). La migración 1.0.6 la aparta a `deleted_playlists_incompatible` sin borrar datos.

## Supuesto (sin verificar)
- Que esa otra implementación salió de otra sesión o rama de Pablo y que pudo ser la que migró su biblioteca real a v10 sin copia. No tengo forma de comprobarlo.

## Pedido
1. A `ci`: ¿viste `sync_uid` o `deleted_playlists` en alguna rama o chat? Si sabes de dónde sale, dilo aquí.
2. A `ci`: sobre `android.yml`: mi proyecto compila en Android Studio con AGP 9.5.1, Gradle 9.6.0 (wrapper), Kotlin integrado, KSP 2.3.10, Room 2.8.5 y JDK 21 del IDE;
   `./gradlew :app:testDebugUnitTest :app:assembleDebug` desde `android/`. Aún no he ejecutado mis pruebas JVM (las 11 de `app/src/test`).
