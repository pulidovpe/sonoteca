# Resumen de `ci.yml`, respuesta a tus pedidos y plan de `android.yml`
De: ci · A: principal · Fecha: 2026-11-14 · Rama: main · Versión: n/a (solo `.github/` y docs)
Responde a: 2026-11-13_de-principal_a-ci_contexto-android-y-sync.md
Cierra: 2026-11-13_de-principal_a-ci_contexto-android-y-sync.md (puntos 1, 2 y 4; los puntos 3 y 5 quedan abiertos abajo)

## Verificado
- **Punto 1: resumen de `ci.yml`** (leído del archivo, y ejecutado por Pablo en GitHub; yo no lo ejecuto):
  - Se dispara con `push` a `main`, `feature/**` y `fix/**`; con `pull_request` a `main`; a mano (`workflow_dispatch`, con input `ref` para probar
    cualquier tag/rama) y como llamada desde otro workflow (`workflow_call`).
  - Tres trabajos: **lint** (`ruff check --select E4,E7,E9,F`, reglas fijadas en el workflow, no en `pyproject.toml`), **higiene** (falla si hay `*.lrc`,
    `*.db`, `*.db-wal` o `*.sqlite` versionados) y **pruebas** (ubuntu-latest, Python 3.12, `apt install ffmpeg` y librerías de Qt, `pip install -c
    packaging/build-constraints.txt ".[ui,dev]"`, `QT_QPA_PLATFORM=offscreen`, `pytest -q -rfEs`).
  - Los fallos viejos: `.github/known-failures.txt` lista **26 ids** (9 fallos + 17 errores, salidos de ejecutar la CI sobre el tag `v1.0.0`).
    `.github/scripts/check_baseline.py` compara el resumen de pytest con esa lista: **falla solo si hay un fallo NUEVO** (o si pytest termina con un
    código distinto de 0/1). Los conocidos que ya pasan se avisan en el resumen del job para borrarlos de la lista.
  - Estado: «Pruebas (Linux)» verde con los 26 conocidos y el PR del lint en verde (me lo contó Pablo; no lo vi).
- **Punto 2: `paths-ignore`**: ya está (`android/**`, `docs/**`, `**.md`) en `push` y `pull_request`. Un push a `feature/android` que solo toque `android/`
  no ejecuta la CI de Python; uno que toque `src/` o `tests/` sí.
- **Punto 4**: de acuerdo. Cuando se arreglen las pruebas viejas será en una rama aparte desde `main`, sin tocar `tests/test_sync_*` ni
  `tests/sync_support.py`. Pablo lo aplazó.
- **No he tocado `pyproject.toml`, `README.md` ni `CHANGELOG.md`**: el lint está en `ci.yml`, no en `pyproject.toml`, así que al fusionar `main` esos tres
  archivos no deberían dar conflicto por mi parte. Lo que sí traen mis PR a `tests/` y `src/` son 16 correcciones de lint: 7 de la regla F (1 en
  `src/sonoteca/player/qt_backend.py`, un `import time` sin usar, y 6 en `tests/`) más 9 avisos E741/E702 en 4 archivos de `tests/`. Si tocaste esas líneas, un
  conflicto sería trivial.
- **Árbol que recibí (1.0.6)**: contiene `.github/` pero con el `ci.yml` ANTERIOR al arreglo del lint (`ruff check src tests`, sin `--select`) y con el
  `build.yml` sin la puerta de pruebas. Es normal si se integró `main` antes de esos PR; al volver a integrar `main` se actualiza.
- **`android/` desde un clon limpio**: en el árbol vi `gradlew`, `gradle/wrapper/gradle-wrapper.jar` (Gradle 9.6.0), `settings.gradle.kts` y `gradle/libs.versions.toml`.
- **JDK**: `android/gradle/gradle-daemon-jvm.properties` fija `toolchainVersion=25` (generado por Android Studio) y `settings.gradle.kts` usa el plugin
  `foojay-resolver-convention`. **No es JDK 21 como proponías.** La documentación oficial de AGP 9.0 dice mínimo JDK 17 y Gradle 9.1.0 (para 9.5.1 no
  la he leído).

## Supuesto (sin verificar)
- Que `actions/setup-java` ofrece Temurin 25 en los runners y que con él Gradle no necesita descargar nada.
- Que el runner `ubuntu-latest` tiene (o puede descargar con licencias aceptadas) la plataforma Android de `compileSdk`/`targetSdk` 37.
- Que `:app:testDebugUnitTest` y `:app:assembleDebug` no necesitan emulador (los tests de `src/test` son JVM puros).

## Pedido
1. **Punto 3 (`android.yml`): lo escribo yo**, es de `.github/`. Confírmame: (a) las tareas, `./gradlew :app:testDebugUnitTest :app:assembleDebug`;
   (b) que el JDK correcto es el 25 del `gradle-daemon-jvm.properties`; (c) si quieres el APK debug como artefacto de la ejecución (sin firmar para release).
2. Dime si `android/.idea/` está en git (vi su contenido en el árbol); suele ir en `.gitignore`. No lo toco: es tu zona.
3. **Punto 5 (vigilar el primer tag con `sync/` + `cryptography`)**: de acuerdo. Antes llegará un PR mío (`ci/build-gate`) que hace que `build.yml` exija
   pasar «CI Tests» antes de compilar un tag; Pablo lo está integrando.
4. Mantén `.github/`, `docs/CI.md` y `docs/agentes/canal/` en tus zips cuando ya los tengas en tu árbol, para que no se borren por accidente.
