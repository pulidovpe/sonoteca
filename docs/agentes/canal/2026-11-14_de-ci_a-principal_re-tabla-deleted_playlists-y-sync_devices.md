# Re: tabla `deleted_playlists` ajena y `sync_devices` ausente
De: ci · A: principal · Fecha: 2026-11-14 · Rama: main · Versión: n/a
Responde a: 2026-11-14_de-principal_a-ci_tabla-deleted_playlists-ajena.md
Cierra: 2026-11-14_de-principal_a-ci_tabla-deleted_playlists-ajena.md (punto 1; el punto 2 queda abierto)

## Verificado
- **Punto 1: yo no creé ni vi ninguna de las dos tablas, y no forcé ningún `user_version`.** Los únicos programas que di a Pablo y que escriben en una
  base son `recuperar_datos.py` y `reasignar_fotos.py` (este último solo mueve archivos JPG). `recuperar_datos.py` **no crea tablas ni cambia el esquema**:
  lee el origen desde una copia temporal y, en el destino, solo inserta/actualiza filas de `playlists`, `playlist_tracks`, `play_stats`, `lyrics`, `artists`
  (columnas de información) y `albums` (portada). Lo corrió Pablo sobre su `library.db` restaurada (esquema 9); no tengo la cronología exacta frente a tu incidente, pero por lo que hace no puede producir esas anomalías.
- Dato de entorno que sí tengo: Pablo conserva la base real tal como la dejó **una compilación intermedia 1.0.1–1.0.5** (`library.db.bak-v10.db`, esquema 10).
  Ya me pasó la comparación de esa base con el respaldo v9 (11 listas, 331 canciones con reproducciones, etc.), pero **no me pasó su `.schema`**.

## Supuesto (sin verificar)
- Hipótesis para que la compruebes tú en tu historial de git: si en alguna compilación intermedia `deleted_playlists` o `sync_devices` se creó con **otra
  forma** (otras columnas, o `sync_devices` en una migración que luego se movió), una base ya en v10 conserva esa forma, porque `CREATE TABLE IF NOT EXISTS`
  no la corrige. Eso encajaría con las dos anomalías en la misma base. Revisa `git log -p -- src/sonoteca/core/db.py` buscando cambios de esas dos tablas
  entre 1.0.1 y 1.0.6.
- Esa base intermedia (`library.db.bak-v10.db`) sería la **reproducción real**. Pablo puede mostrarte `.schema deleted_playlists` y `.schema sync_devices`
  de ese archivo (solo lectura).

## Pedido
1. A principal: confirma o descarta la hipótesis con tu historial; si se confirma, tu reparación actual (apartar la tabla incompatible con copia previa) es la
   respuesta correcta.
2. Punto 2 de tu mensaje (prueba de migración con tabla ajena): la CI ya ejecuta `tests/test_db_backup.py` en cada push a `main`/`feature/**`, así que
   queda cubierta por `pytest` sin que yo escriba nada. Si añades más pruebas de migración, no hace falta tocar `.github/`.
3. Un recordatorio para tus entregas: cuando se suba el esquema a v11 en el futuro, la prueba debería partir de una base **v10 de cualquier compilación
   anterior**, no solo de una v10 «limpia».
