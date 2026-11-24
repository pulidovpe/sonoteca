# Migraciones de la base de datos: reglas

La biblioteca de Pablo es de verdad y las versiones antiguas de la app **no abren** una base más nueva que ellas. Por eso:

1. **Copia antes de migrar.** `migrate()` (en `core/db.py`) crea `library.db.v<N>.bak` ANTES de subir el esquema, donde `<N>` es la versión
   de la que se parte. Usa la API de copia de SQLite (consistente, incluye lo que aún está en el `-wal`; no hace falta copiar `-wal`/`-shm`).
   No sobrescribe una copia que ya exista y, si no puede crearla, **aborta sin tocar la base**. No se crea con bases nuevas ni en memoria.
2. **Toda subida de esquema lleva una prueba** que migre una base de la versión anterior y compruebe que los datos sobreviven y que se
   deja la copia (`tests/test_sync_schema.py`, `tests/test_db_backup.py`).
3. **En desarrollo, nunca la biblioteca real**: usa siempre `SONOTECA_DATA_DIR`.

## Directorio de desarrollo con datos reales (copia segura)
```bash
mkdir -p "$HOME/sonoteca-dev"
sqlite3 "$HOME/Library/Application Support/sonoteca/library.db" ".backup '$HOME/sonoteca-dev/library.db'"   # solo lee la real
export SONOTECA_DATA_DIR="$HOME/sonoteca-dev"
sonoteca paths          # comprueba que apunta a sonoteca-dev
```
Con la app cerrada y en una terminal nueva para cada sesión. Ojo: la copia conserva las **rutas de tu música real**; el servidor de
sincronización solo la lee, pero editar tags desde la app de escritorio SÍ modificaría esos archivos.

## Volver a la versión anterior desde la copia
```bash
cd "$HOME/Library/Application Support/sonoteca"          # o la carpeta que muestre `sonoteca paths`
# con ninguna app abierta:
mv library.db library.db.descartada
rm -f library.db-wal library.db-shm                        # un -wal viejo sobre otra base la corrompe
cp library.db.v9.bak library.db
```
Lo creado en la base nueva después de la migración (listas, reproducciones) se pierde al volver: la copia es de antes de migrar.
Si falta `sync_devices` u otra pieza de v10 con la versión en 10, se repara sola al abrir (y se deja `library.db.v10.bak`).
**1.0.15** añadió a v10 la tabla `sync_play_events` (reproducciones del móvil, idempotentes) **sin subir el esquema**: una base v10 anterior que no la tiene se repara sola al abrir, con la copia previa
`library.db.v10.bak` (si ya existe una `.v10.bak`, se conserva la más antigua: no se pisa). El resto de la base no cambia.
