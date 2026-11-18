# Sonoteca — CONTEXTO COMPACTO DE AGENTES / CI (v1, 2026-11-17)

> Pégalo al inicio de un chat nuevo del **agente de CI/DevOps**, **junto con el zip del repo** (o el árbol más reciente). No sustituye a `CONTEXT_COMPACT.md` (que es del agente de la app): lo complementa. Si ambos se contradicen en algo de CI, manda este.

## Rol, preferencias de Pablo y límites del entorno
- Pablo Pulido (`pulidovpe`), ingeniero de software. Pide: razonar antes de responder, basarse en documentación oficial reciente, **admitir incertidumbre y preguntar lo crítico**, **responder en español, conciso**. Actúa como ingeniero DevOps con +20 años en entornos locales multiplataforma.
- **En cada entrega: comandos git exactos + commit de una línea + etiqueta si aplica.** Entregas cortas (una cosa por mensaje) y, si hay archivos, un zip o el archivo mismo. Probar siempre en su Mac (M4 Pro, zsh); también tiene Fedora (Linux) y Windows.
- **Entorno de Claude**: bash **sin red** y sin pytest/PySide6/ruff/mutagen. Solo se prueba lógica pura (Python) y se valida YAML con PyYAML; `web_search` sí existe (documentación). **Los workflows llegan SIN ejecutar**: decir siempre qué se verificó (y quién: casi siempre Pablo en GitHub) y qué no.
- Repo público MIT: `github.com/pulidovpe/sonoteca`. Python 3.12 + PySide6/QML (app de escritorio), SQLite (esquema v10), app Android (Kotlin/Compose/Room, carpeta `android/`). Nada de música/tags/datos personales en el repo ni en logs.

## Reparto de zonas y comunicación entre agentes
- Hay **dos agentes de Claude**: *principal* (app: `src/`, `tests/`, `android/`, `packaging/`, resto de `docs/`, `CONTEXT_COMPACT.md`) y *ci* (`.github/**`, `docs/CI.md`, sus mensajes en `docs/agentes/canal/`). Tabla de zonas y protocolo: `docs/agentes/README.md`.
- **Desde 2026-11-17 (orden de Pablo) el canal de archivos ya NO se usa para mensajes nuevos**: principal deja sus actualizaciones en la sección «Novedades de principal» de ESTE archivo, y ci hace lo mismo en su respuesta (Pablo las copia entre chats). Lo siguiente describe el canal histórico.
- **Canal (histórico)**: un archivo por mensaje en `docs/agentes/canal/`, nombre `AAAA-MM-DD_de-X_a-Y_asunto.md`, con `Responde a:` / `Cierra:` y secciones **Verificado / Supuesto / Pedido**. Los agentes no se ven: **Pablo copia los archivos** entre ramas/chats. (Los mensajes de principal nacen en `feature/android`.)
- Reglas que ci exige a principal: no editar `.github/`; ~~conservar `.github/`, `docs/CI.md` y el canal en sus zips~~ (**corregido 2026-11-17: los zips de principal ya NO incluyen `.github/` ni `docs/CI.md`**, y desde 1.0.12 traen solo los archivos que cambian); no añadir fallos a `known-failures.txt` (solo puede encogerse); proyecto Gradle compilable desde clon limpio; avisar a ci si cambia `compileSdk`, `toolchainVersion` (JDK) o AGP; **nunca** desarrollar sobre la biblioteca real (usar `SONOTECA_DATA_DIR=~/sonoteca-dev`).
- Pablo aplazó arreglar los 26 tests viejos: se hará en rama aparte desde `main`, sin tocar `tests/test_sync_*`.

## Novedades de principal (2026-11-17, v1.0.13) — leer primero
**Verificado**
- **Android 3b (1.0.11) probada por Pablo en el POCO por USB**: descargar álbum, artista y lista (23 pistas, 144 MB), borrar cada uno y volver a descargar. Todo bien. Pruebas JVM: 34 (antes 31).
- 1.0.11 no compilaba por un `import` duplicado de `TrackEntity` en `SyncRepository.kt` (error de principal): corregido en `ee1b4a1`; con él, Android CI #5 quedó verde. No sé si `android.yml` corrió sobre el commit anterior.
- **1.0.12** (catálogo de Room se renueva al emparejar; solo `MainViewModel.kt` y textos): los 3 pipelines en verde y probado en el móvil.
- **Lint pisado por un zip de principal**: «CI Tests #17» falló en ruff (10 avisos E702/F401/E741/F541; GitHub muestra máx. 10 anotaciones por paso) en 9 archivos de `tests/` y `src/sonoteca/player/qt_backend.py`.
  Esas correcciones ya estaban en `main` (`5f0d02f`, `ci/lint-f`) pero `feature/android` tenía las versiones viejas: un `unzip -o` de un zip de principal (con foto vieja de `tests/` y `src/`) las pisó.
  Se arregló con `git checkout origin/main -- tests src/sonoteca/player/qt_backend.py` y volvió a verde. Misma familia que lo de `android.yml`. **Nuevo en principal**: sus zips traen SOLO los archivos que cambian; tu lint cazó el problema a tiempo, no hace falta tocar `ci.yml`.
- **1.0.13 ✅ verificada por Pablo** (adb real y pipelines verdes): `sync/usb.py` (`UsbWatcher`), `cli.py`, `tests/test_sync_usb.py` (+6): rehace `adb reverse` solo al reconectar el móvil.
- **1.0.14 (en curso, SIN compilar)**: fase 4a de Android, reproductor local con **Media3 1.11.0** (`androidx.media3:media3-exoplayer` y `media3-session`, de Google Maven; Kotlin 2.2 compatible con el 2.2.10 del proyecto). Solo toca `android/**` y docs: disparará `android.yml` (no `ci.yml`). Aviso por tu regla: **no cambian** `compileSdk`, JDK ni AGP; **sí** hay dependencias nuevas (la caché de Gradle tendrá que descargarlas), +6 pruebas JVM (`PlaybackQueueTest`) y permisos nuevos en el manifiesto. Si `android.yml` falla, las últimas líneas del log a principal.
- Anotaciones leídas en el run #17 (no investigadas más): Node 20 en desuso (`checkout@v4`, `setup-python@v5`, `upload-artifact@v4` forzados a Node 24) y `ubuntu-latest` migra a Ubuntu 26 desde el 19-oct-2026.
**Supuesto (sin verificar)**
- Que `ruff>=0.6` sin fijar versión no dé sorpresas (esta vez el fallo fue un pisado de archivos, no una versión nueva).
**Pedido a ci** (zona suya; principal no ha tocado nada)
1. Valorar los avisos de Node 20 (subir acciones a una versión que corra en Node 24 cuando exista y esté documentada) y de `ubuntu-latest` → Ubuntu 26: ¿fijar `ubuntu-24.04` en `ci.yml`/`android.yml`/`build.yml` o probar en 26 antes (JDK 25 y Qt offscreen podrían comportarse distinto)?
2. Actualizar la tabla «Pipelines» del README (aún dice que `android.yml` está en la hoja de ruta).
3. Cuando Pablo lance `build.yml` sin publicar y falle algo con `cryptography` en PyInstaller, pasar a principal las últimas líneas del log (arreglo en `packaging/sonoteca.spec`, que es de principal).

## Estado de la CI (verificado por Pablo en GitHub salvo lo marcado)
Acciones fijadas: `checkout@v4`, `setup-python@v5`, `setup-java@v5`, `setup-gradle@v6` (`cache-provider: basic`), `wrapper-validation@v6`, `setup-android@v3`, `upload-artifact@v4`.
1. **`.github/workflows/ci.yml`** («CI Tests») ✅ verde. Triggers: push a `main`/`feature/**`/`fix/**`, PR a `main` (ambos con `paths-ignore: android/**, docs/**, **.md`), `workflow_dispatch` (input `ref` para probar cualquier tag/rama), `workflow_call`. Jobs: **lint** (`ruff check --select E4,E7,E9,F --output-format=github src tests`; reglas fijadas aquí, NO en `pyproject.toml`), **higiene** (falla si hay `*.lrc/*.db/*.db-wal/*.sqlite` versionados), **pruebas** (ubuntu-latest, Py 3.12, `apt` ffmpeg + libs Qt, `pip install -c packaging/build-constraints.txt -e ".[ui,dev]"`, `QT_QPA_PLATFORM=offscreen`, `pytest -q -rfEs` **sin `| tee`**, luego `check_baseline.py`). `permissions: contents: read`, `concurrency` con cancelación, sin secretos, `pull_request` (nunca `pull_request_target`).
2. **`.github/scripts/check_baseline.py` + `.github/known-failures.txt`**: lee `FAILED/ERROR id - msg` del resumen de pytest; **falla solo con fallos NUEVOS** o con pytest ≠ 0/1. La lista (**26 ids = 9 fallos + 17 errores**, sacados de la CI sobre `v1.0.0`) se lee de un **segundo checkout sparse (`ci-tools`) del propio workflow**, no de la ref probada (así funciona con tags viejos sin `.github/`). Estado actual: 26 conocidos siguen fallando, 0 nuevos.
3. **`build.yml`** («Build Sonoteca», tag `v*` o dispatch): trabajo `ci` (`uses: ./.github/workflows/ci.yml`) **solo con tag/`release_tag`**; `build` hace `needs: [plan, ci]` y se ejecuta si `ci` es `success` o `skipped`; `release` sin cambios (publica con `--clobber`). ✅ `gh workflow run build.yml --ref main -f target_os=all` (sin publicar): **compiló en los 3 sistemas**. ⚠️ **La rama «publicar con tag» (puerta real) aún no se ha ejercitado.** El binario probablemente NO incluye `sync/`/`cryptography` (sin verificar): cuando la sincronización entre en la GUI hay que añadir `cryptography` al empaquetado y repetir.
4. **`.github/workflows/android.yml`** («Android CI») ✅ verde en `feature/android` y en `main`. Solo con cambios en `android/**`. Pasos: comprobar `gradlew`/`settings`/wrapper → **JDK 25 Temurin** (fijado por `android/gradle/gradle-daemon-jvm.properties`, `toolchainVersion=25`; funciona con 25.0.5) → `setup-android` (`packages: platform-tools`, acepta licencias) → diagnóstico de plataformas → validar wrapper → setup-gradle → `./gradlew :app:testDebugUnitTest :app:assembleDebug --stacktrace` → resumen de pruebas (`.github/scripts/test_summary.py`: nunca rompe) → artefacto `sonoteca-android-debug` (APK **debug**, 7 días). Resultado: **31 pruebas JVM en 7 clases, 0 fallos**; AGP 9.5.1, Gradle 9.6.0, `compileSdk`/`targetSdk` 37, `minSdk` 29. **Sin `androidTest`** (necesitan dispositivo). El APK de CI va firmado con otra clave debug que la de Android Studio: hay que desinstalar la app antes de instalarlo en el móvil.
5. Repo en GitHub configurado por Pablo (aprobación de PRs de forks, permisos de solo lectura): **no confirmé los ajustes exactos**; preguntar antes de asumir protección de ramas.

## Trampas aprendidas (no repetir)
- **Un `push` usa el workflow de la propia rama**: `feature/android` solo ejecuta CI si contiene `.github/`; hay que `git fetch` **antes** de `git merge origin/main`. Para probar otra rama con el workflow de `main`: `gh workflow run X.yml --ref main -f ref=<rama>`. `workflow_dispatch` necesita el archivo en la rama por defecto.
- Un `dispatch` con `ref` = tag viejo no ve `.github/` de ese tag: por eso el segundo checkout `ci-tools`.
- `pytest | tee` devuelve 0: guardar el código y decidir después. `ruff` sin `--select` aplicó reglas de estilo (84 avisos): **las reglas se fijan en el workflow**; ~77 de estilo (I, UP, SIM, RUF…) quedan fuera a propósito (decisión pendiente de Pablo).
- Android: **`platforms;android-37` NO existe; el id es `platforms;android-37.0`**. No instalar la plataforma a mano: la descarga AGP con las licencias aceptadas. La ejecución manual #1 falló por ese error mío.
- No pegar marcadores como `<TU_BASE_V10>` literalmente en zsh: crea archivos vacíos. `pytest.log` en la raíz del repo no debe versionarse (se pidió añadirlo a `.gitignore` en el PR de `android.yml`; **confirmar** que quedó).
- Pablo suele **no tener `~/Downloads/<nombre>`** si el navegador renombra (`_2`): pedirle `ls ~/Downloads | grep …`.
- No usar `git add -A` en su árbol de trabajo (archivos sueltos); usar worktree.
- **Si un PR muestra «Can't automatically merge»**: casi siempre `origin/main` local desactualizado; no resolver a ciegas.

## Flujo de entrega con Pablo (probado)
```bash
git fetch origin && git worktree add ../sonoteca-ci origin/main --detach
unzip -o ~/Downloads/<zip> -d ../sonoteca-ci          # o: python3 ~/Downloads/aplicar_X.py
cd ../sonoteca-ci && git switch -c ci/<tema> && git add -A && git commit -m "ci: …"
git push -u origin ci/<tema> && gh pr create --fill --base main
cd - && git worktree remove ../sonoteca-ci --force
```
- Los cambios a archivos existentes se entregan como **scripts `aplicar_*.py` con texto exacto**: exigen exactamente 1 coincidencia, todo-o-nada, fallan sin escribir y son idempotentes por rechazo (probados contra copia del archivo).
- Probar workflows sin publicar: `gh workflow run ci.yml --ref main -f ref=<ref>`; `gh workflow run android.yml --ref main -f ref=feature/android`; `gh workflow run build.yml --ref main -f target_os=all`. Ver logs: `gh run view <id> --log-failed | tail -60`. **Pedir siempre las ÚLTIMAS líneas**, no las primeras.

## Datos de Pablo: lecciones de la migración v9→v10 (importante)
- Ejecutar una versión de desarrollo sobre su biblioteca real **migró la base a v10 sin copia**; las apps ≤ v9 se niegan a abrirla («La base tiene versión 10, más nueva que esta app»). No hay vuelta atrás sin respaldo. Principal añadió copia previa a migrar (`library.db.v<N>.bak`, API de copia de SQLite) y `docs/MIGRACIONES.md`.
- Pablo restauró un respaldo v9 y recuperó datos con scripts **fuera del repo** (`recuperar_datos.py` [listas, reproducciones, `--con-info`: letras/artistas/portadas], `reasignar_fotos.py` [fotos `artists/<id>.jpg` por nombre]). Conserva `library.db.bak-v10.db` (base real tal como la dejó una compilación intermedia 1.0.1–1.0.5; sirve de reproducción para el incidente `deleted_playlists`/`sync_devices`, hipótesis sin verificar).
- Datos útiles: fotos de artista se guardan **por id**; el contador de reproducciones solo se ve en filas ≥ 940 px de ancho (según `Theme`); una ruta excluida del origen no se copió (rehacer en la app).

## Decisión sobre IA en la CI (laboratorio «IA en Pipelines DevOps»)
- `build.yml` **no se toca con IA** (determinista). Del laboratorio se adaptó solo el `ci.yml` con `exit` correcto. **No adoptado**: AI CI Fix (commit automático; riesgo de inyección con `head_branch` y de «arreglos» que solo pasan tests), gh-aw/CI Doctor (Technical Preview, bug HTTP 400 con cuentas free). Opcional futuro: revisión **solo consultiva** (solo comenta, sin permisos de escritura, sin forks). La cuota de Cloudflare Workers AI («10,000 req/día» del PDF) probablemente son *Neurons*: **sin verificar**.

## Pendiente / abierto (orden de valor)
1. **Matriz macOS/Windows** de `pytest` en `ci.yml` (instalar ffmpeg: `brew`/`choco`, sin verificar) para los pendientes de Windows (permisos al escribir tags, mp4 HEVC) y Linux/Wayland.
2. Ejercitar la puerta de `build.yml` con un tag real (p. ej. `v1.1.0-rc1`, que se publica como prerelease) y vigilar `cryptography`/`sync/` en PyInstaller cuando entre en la GUI.
3. Arreglar los 26 tests viejos (rama `fix/…`, la lleva principal; ci solo adelgaza `known-failures.txt`).
4. Decidir ampliar `ruff` (I, UP, SIM, RUF…) y valorar Dependabot para acciones y fijarlas por SHA; firma Android (keystore en Secrets) y APK firmado en el Release al cierre (1.1.0); notarización macOS.
5. Revisión con IA consultiva (opcional, al final).

## Primeros pasos en un chat nuevo
1. Leer `docs/CI.md`, `docs/agentes/README.md`, la sección «Novedades de principal» de este archivo y los últimos archivos de `docs/agentes/canal/` (histórico).
2. Pedir a Pablo el último resultado de las ejecuciones relevantes (`gh run list -L 10`) antes de proponer cambios.
3. Nunca declarar «probado» un workflow que no se ejecutó.
