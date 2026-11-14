# Canal entre agentes (archivos del repositorio)

Varios agentes de IA trabajan en este repositorio por separado y **no se ven entre sí**; el único puente es Pablo (el humano) y este
repositorio. Este canal es la forma de dejarse recados sin depender de que Pablo los reformule.

## Agentes y dueños de cada zona
| Agente | Se ocupa de | Rutas suyas |
|---|---|---|
| `principal` | La app (Python), la sincronización y la app Android | `src/**`, `tests/**` (salvo lo que arregle `ci`), `android/**`, `docs/SYNC.md`, `docs/ANDROID.md`, `CONTEXT_COMPACT.md`, `CHANGELOG.md` |
| `ci` | Pipelines de GitHub Actions y revisión de errores de las pruebas | `.github/**`, la sección «Pipelines» del `README.md` |

Regla: **no edites rutas de otro agente**. Si necesitas un cambio allí, pídelo con un mensaje. Excepciones: Pablo puede editar todo.

## Cómo se escribe un mensaje
1. Un archivo por mensaje, en `docs/agentes/canal/`, nombrado `AAAA-MM-DD_de-<agente>_a-<agente>_<asunto-corto>.md`
   (así dos agentes nunca editan el mismo archivo y no hay conflictos de git).
2. **No se editan mensajes ya escritos**, ni propios ni ajenos. Una respuesta es un archivo nuevo con las líneas `Responde a:` y, si
   resuelve el tema, `Cierra:` con el nombre del archivo original. Un tema sigue abierto mientras ningún mensaje lo cierre.
3. Cada mensaje separa **lo verificado** (qué se ejecutó y qué salió) de **lo supuesto**, y dice qué se pide y a quién.
4. Nunca pongas secretos ni datos personales (tokens, claves, rutas de la biblioteca de música, correos).
5. Al empezar una sesión, cada agente lee `docs/agentes/canal/` y atiende lo dirigido a él que siga abierto.

## Plantilla
```
# <asunto>
De: <agente> · A: <agente> · Fecha: AAAA-MM-DD · Rama: <rama> · Versión: <x.y.z>
Responde a: <archivo, opcional>
Cierra: <archivo, opcional>

## Verificado
## Supuesto (sin verificar)
## Pedido
```

## Cómo pasa un mensaje de una rama a otra
`ci` trabaja sobre `main` y `principal` sobre `feature/android`: un mensaje solo lo ve el otro cuando su rama lo tiene. Pablo lo lleva:
```bash
git checkout feature/android
git checkout main -- docs/agentes        # trae los mensajes nuevos de main (o al revés, desde feature/android hacia main)
git add docs/agentes && git commit -m "docs(agentes): sincronizar canal"
```
