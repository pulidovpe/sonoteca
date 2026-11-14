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
- `.github/workflows/ci.yml` («CI Tests»): `ruff`, higiene del repo y `pytest` en Linux con PySide6 fijado por `packaging/build-constraints.txt`. Se dispara en push a `main`, `feature/**`, `fix/**`; en PR a `main`; a mano; y como llamada desde otro workflow.
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
2. ⏳ `build.yml` exige `ci.yml` antes de compilar un tag.
3. ⏳ `android.yml`: `assembleDebug` + pruebas JVM en `android/**`; APK debug como artefacto.
4. ⏳ Matriz macOS/Windows para los pendientes de Windows.
5. ⏳ Opcional: revisión con IA solo consultiva.
