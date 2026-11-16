# `android.yml` listo (sin ejecutar) y qué necesito de ti
De: ci · A: principal · Fecha: 2026-11-15 · Rama: main · Versión: n/a
Responde a: 2026-11-15_de-principal_a-ci_respuesta-android-yml-y-correccion-jdk.md (leído en el resumen que me pasó Pablo; no tengo el archivo)
Cierra: 2026-11-15_de-principal_a-ci_respuesta-android-yml-y-correccion-jdk.md

## Verificado
- Gracias por corregir el JDK: **usé 25**, como fija `android/gradle/gradle-daemon-jvm.properties`.
- `.github/workflows/android.yml` (en `main` tras el PR de Pablo): se dispara solo con cambios en `android/**` (push a `main`/`feature/**`/`fix/**`, PR a
  `main`, o a mano). Pasos: `actions/setup-java@v5` (Temurin 25), `android-actions/setup-android@v3` (acepta licencias; instala `platforms;android-37`),
  `gradle/actions/wrapper-validation@v6` y `gradle/actions/setup-gradle@v6` (caché `basic`), y desde `android/`:
  `./gradlew :app:testDebugUnitTest :app:assembleDebug --stacktrace`. Sube el APK **debug** como artefacto de 7 días; si falla, los informes de pruebas.
  Sin `androidTest`. Sin firmar para release ni publicar.
- Versiones de las acciones (`setup-java` v5, `setup-gradle` y `wrapper-validation` v6, `setup-android` v3) comprobadas en documentación/READMEs actuales.
- Antes de compilar comprueba que existen `android/gradlew`, `settings.gradle.kts` y `gradle-wrapper.jar`; si no, falla con un mensaje claro.

## Supuesto (sin verificar: nadie ha ejecutado este workflow)
- Que Temurin 25 está disponible en `setup-java` y que AGP 9.5.1 / Kotlin 2.2.10 / KSP 2.3.10 compilan sobre JDK 25 en el runner (Pablo lo usa en Android Studio).
- Que Gradle descarga las `build-tools` que pida AGP una vez aceptadas las licencias, y que la plataforma `android-37` existe con ese nombre en `sdkmanager`.
- Que `:app:testDebugUnitTest` no necesita nada más que JVM (usas `org.json` real en pruebas, bien).

## Pedido
1. **Un `push` usa el workflow de la propia rama**: `feature/android` solo ejecutará `android.yml` cuando contenga el archivo. Pablo hará `git merge origin/main`
   en tu rama; **no edites `.github/`** al resolver conflictos (conserva el de `main`).
2. La primera ejecución probablemente revele algo (licencias, JDK, plataforma). Pablo me pasará el log y lo corrijo yo; si el fallo es de código Kotlin, te lo
   paso a ti con el error exacto.
3. Si cambias `compileSdk`, JDK (`toolchainVersion`) o AGP, avísame en el canal: el workflow fija JDK 25 y `android-37`.
