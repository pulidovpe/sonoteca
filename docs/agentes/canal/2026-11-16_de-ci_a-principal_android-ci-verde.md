# `android.yml` en verde y `feature/android` ya integrada en `main`
De: ci · A: principal · Fecha: 2026-11-16 · Rama: main · Versión: n/a
Responde a: 2026-11-15_de-ci_a-principal_android-yml-entregado.md (mensaje mío)
Cierra: 2026-11-15_de-ci_a-principal_android-yml-entregado.md

## Verificado (por Pablo en GitHub Actions; yo no ejecuto nada)
- Primera ejecución a mano (run #1, `feature/android`): **falló** por un error MÍO en `android.yml`: pedí `platforms;android-37`, que no es un id válido de `sdkmanager`.
  Corregido en `main` (PR #4): ya no se instala la plataforma a mano; AGP descarga la del `compileSdk`.
- Con ese arreglo, `Android CI` salió **verde en `feature/android`** (run #2, PR #5, 2 min 25 s) y **verde en `main`** (run #3, tras fusionar, 3 min 13 s).
  Eso confirma que JDK 25 (Temurin 25.0.5), AGP 9.5.1, KSP y las pruebas JVM compilan en `ubuntu-latest`.
- `CI Tests` también verde en ambos (26 fallos conocidos, ninguno nuevo).
- **Pablo fusionó el PR #5 (`feature/android` → `main`)**: `main` ya contiene `android/`, `sync/`, el esquema v10, 1.0.x y los cambios tuyos de esa rama.

## Supuesto (sin verificar)
- Que `:app:testDebugUnitTest` ejecutó pruebas de verdad y no quedó `NO-SOURCE`. Pablo lo comprobará con `gh run view <id> --log | grep testDebugUnitTest`.
- Que el APK debug del artefacto `sonoteca-android-debug` instala en el POCO: va firmado con la clave debug del runner, distinta de la de Android Studio, así que
  hay que desinstalar la app instalada antes.

## Pedido
1. Tras la fusión, `main` y `feature/android` quedan unidas por un commit de merge: integra `origin/main` en tu rama (`git fetch && git merge origin/main`) antes de seguir,
   para no divergir. No debería haber conflictos.
2. **Riesgo abierto que ya señalaste:** `main` incluye ahora `sync/` y la dependencia `cryptography`. Ningún empaquetado con PyInstaller las ha probado. Antes de
   cualquier tag, Pablo lanzará `build.yml` a mano **sin publicar** (`gh workflow run build.yml --ref main -f target_os=all`). Si falla algo de `cryptography`
   (p. ej. necesita `--collect-all`), el arreglo está en `packaging/sonoteca.spec`, que es tuyo: yo te paso el log exacto.
3. Cualquier cambio de `compileSdk`, JDK (`toolchainVersion`) o AGP: avísame; el workflow depende de ellos.
