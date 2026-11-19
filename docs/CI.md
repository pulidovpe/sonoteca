# CI de Sonoteca — LÉEME PRIMERO (para personas y agentes de IA)

Hay **dos agentes de Claude** trabajando en paralelo, cada uno en su chat, más Pablo:

| Quién | Rama | Carpeta suya |
|---|---|---|
| Agente de la app (Python/Android) | `feature/android` | `android/`, `src/`, `tests/` |
| Agente de CI/DevOps | `main` (y `ci/*`) | `.github/`, `docs/CI.md` |

## Reglas para el agente de la app
1. **No edites** `.github/` (workflows, scripts, `known-failures.txt`). Si necesitas un cambio de CI (otro JDK, otra ruta, un paso nuevo), pídeselo a Pablo: lo hace el agente de CI.
2. **Los zips que entregues deben conservar `.github/` y `docs/CI.md`.** Si Pablo copia tu zip sobre el repo, nunca uses `rsync --delete` ni borres carpetas que no conoces.
3. Todo test nuevo debe **pasar**. La CI falla ante cualquier fallo que no esté en `.github/known-failures.txt`.
4. **No añadas fallos a esa lista.** Solo puede encogerse: cuando arregles una prueba, bórrala de la lista (la CI avisa cuáles ya pasan).
5. Mensajes de commit sobre CI: prefijo `ci:`. Los cambios solo de `android/`, `docs/` o `*.md` **no** disparan la CI de Python (`paths-ignore`).
6. Android: el proyecto Gradle debe ser **compilable desde un clon limpio** (con `gradlew`, `gradle/wrapper/gradle-wrapper.jar` y `settings.gradle.kts` versionados). Sin eso, el futuro `android.yml` no podrá compilar. Los secretos (keystore, claves) nunca van al repo.
7. Al entregar, di qué probaste y qué no; la CI es un segundo compilador, no un sustituto de tu prueba.

## Qué hace hoy
- `.github/workflows/ci.yml` («CI Tests»): `ruff` (solo reglas E4/E7/E9/F: errores reales; las de estilo —I, UP, SIM, RUF— están fuera a propósito, ~77 avisos pendientes de decidir), higiene del repo y `pytest` en Linux con PySide6 fijado por `packaging/build-constraints.txt`. Se dispara en push a `main`, `feature/**`, `fix/**`; en PR a `main`; a mano; y como llamada desde otro workflow.
- `.github/scripts/check_baseline.py`: compara los fallos con `.github/known-failures.txt`.
- `.github/workflows/build.yml`: compila y publica el release al subir un tag `v*`. No lo toques.

**Importante:** un `push` usa el workflow que exista *en esa rama*. `feature/android` solo ejecuta la CI cuando contiene `.github/`, es decir, tras `git merge origin/main`.

## Cómo lanzarla a mano sobre cualquier ref
```bash
gh workflow run ci.yml --ref main -f ref=<rama|tag|commit>
gh run watch "$(gh run list --workflow ci.yml -L1 --json databaseId -q '.[0].databaseId')"
```

## Hoja de ruta de CI (la lleva el agente de CI)
1. ✅ `ci.yml` con fallos conocidos (26 heredados de v1.0.0).
2. ✅ `build.yml` exige `ci.yml` antes de compilar un tag (solo al publicar).
3. ✅ `android.yml`: pruebas JVM + APK debug con cambios en `android/**` (JDK 25; AGP descarga la plataforma del `compileSdk`). Verde en `feature/android` (run #2) y en `main` (run #3) el 2026-11-16.
4. 🟡 Matriz macOS/Windows de `pytest` (informativa, a demanda): `gh workflow run ci.yml --ref main -f cross=true`. **Sin ejecutar aún.**
5. ⏳ Opcional: revisión con IA solo consultiva.

## Android CI (`android.yml`)
Se dispara por cambios en `android/**` (push a `main`, `feature/**`, `fix/**`; PR a `main`; o a mano con `gh workflow run android.yml --ref <rama>`).
Ejecuta `./gradlew :app:testDebugUnitTest :app:assembleDebug` y sube el APK **debug** como artefacto (7 días). No ejecuta `androidTest` (necesita dispositivo).
La rama debe contener `.github/workflows/android.yml` (un `push` usa el workflow de esa rama). Para compilar otra rama con el workflow de `main`: `gh workflow run android.yml --ref main -f ref=<rama>`.
El id real de la API 37 en sdkmanager es `platforms;android-37.0` (visto en el log del run #2); `platforms;android-37` no existe. No se instala a mano: la descarga AGP.
El paso «Resumen de pruebas JVM» escribe en el resumen del job cuántas pruebas se ejecutaron (`.github/scripts/test_summary.py`); solo avisa, nunca rompe el job. Si el JDK, AGP o `compileSdk` cambian,
hay que avisar al agente de CI: el workflow fija JDK 25 y la plataforma `android-37`.

## Runners, versiones y matriz de sistemas
- Linux fijado a `ubuntu-24.04` (en `ci.yml`, `android.yml` y `build.yml`). `ubuntu-latest` migra a 26.04 entre el 19-oct y el 19-nov-2026. La 26.04 se prueba a demanda:
  `gh workflow run ci.yml --ref main -f runner=ubuntu-26.04` (verificado verde el 2026-11-17: lint, higiene y pytest). Revisar la fijación cuando GitHub anuncie la retirada de 24.04.
- `ruff` fijado a la versión que usa la CI (0.17.5): subirla a propósito, no por sorpresa.
- **Matriz macOS/Windows** (informativa): `gh workflow run ci.yml --ref main -f cross=true`. Corre `pytest` en `macos-latest` y `windows-latest` en paralelo a Linux, con `continue-on-error`
  (nunca rompe el workflow) y sin lista propia de fallos conocidos: el resumen del job enseña los fallos «nuevos» frente a la lista de Linux, que son los propios de ese sistema.
  `ffmpeg` se instala con `brew` / `choco` (verificado). Los logs quedan en los artefactos `pytest-log-macos` y `pytest-log-windows`.
  Resultado (2026-11-18): **macOS = Linux** (26 conocidos, nada propio); **Windows = los 26 + 7 propios** (HOME frente a USERPROFILE, separadores de ruta, `WinError 123` en `duplicates_delete`, `find_adb` con rutas POSIX, una de `ui_edit`).
  Listas por sistema: `.github/known-failures-macos.txt` y `.github/known-failures-windows.txt` (el job las usa para avisar de regresiones, sin fallar).
  Al mirar `pytest.log` de Windows con shell, quitar los `\r` (`tr -d '\r'`): el log lleva saltos CRLF.
- `pytest` imprime las 15 pruebas más lentas (`--durations=15`) en el log y en el artefacto `pytest-log`.

## Datos de desarrollo ≠ datos reales
Ejecutar una versión de desarrollo sobre tu biblioteca real **migra su base** (esquema v10 desde 1.0.1) y las apps antiguas dejan de abrirla («La base tiene versión 10, más nueva que esta app»). No hay vuelta atrás automática. Para desarrollar o probar binarios viejos: `SONOTECA_DATA_DIR=~/sonoteca-dev ./sonoteca gui`.
