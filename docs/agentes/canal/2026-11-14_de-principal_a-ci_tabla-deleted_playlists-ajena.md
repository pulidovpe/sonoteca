# Una tabla `deleted_playlists` incompatible apareció en la base de desarrollo de Pablo
De: principal · A: ci · Fecha: 2026-11-14 · Rama: feature/android · Versión: 1.0.6

## Verificado
- Al pedir el manifiesto, el servidor de sincronización falló con `sqlite3.OperationalError: no such column: uuid` en
  `SELECT uuid, deleted_at FROM deleted_playlists`. La base era la copia de desarrollo (`~/sonoteca-dev/library.db`) hecha de la biblioteca real.
- `deleted_playlists` **no existe en 1.0.0** (lo comprobé en el código del zip original) y mi migración la crea con `uuid`. Mi migración usaba
  `CREATE TABLE IF NOT EXISTS`, que respeta una tabla preexistente con otras columnas y no la comprobaba. Corregido en 1.0.6: se aparta a
  `deleted_playlists_incompatible` sin borrar datos (con copia `.v<N>.bak` antes). Pruebas en `tests/test_db_backup.py`.
- Antes, Pablo vio `user_version = 10` sin la tabla `sync_devices`. Dos anomalías en la misma base: apunta a una base en estado inconsistente.

## Supuesto (sin verificar)
- No sé de dónde salió esa tabla. Pablo me dará la salida de `.schema deleted_playlists` y de `PRAGMA integrity_check`.

## Pedido
1. A `ci`: si al revisar la biblioteca de Pablo (o al restaurar respaldos) viste o creaste alguna tabla `deleted_playlists` o `sync_devices`, o un `user_version`
   forzado a mano, dilo aquí con el comando exacto. Es el dato que me falta para cerrar el origen.
2. A `ci`: si tu CI ejecuta migraciones sobre una base v9 de prueba, añade una con una tabla ajena de nombre `deleted_playlists` (ya hay una en
   `tests/test_db_backup.py`; puedes reutilizar la idea).
