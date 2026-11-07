# Rendimiento: qué se midió y cómo medir más

## Base de datos y búsqueda (medido, 0.14.3)
Prueba con una biblioteca sintética (esquema real de SQLite; esta máquina de desarrollo, no tu Mac):

| Operación | 2 000 canciones | 20 000 canciones |
|---|---|---|
| Listar artistas / álbumes | 0,2 / 0,5 ms | 2,6 / 5,3 ms |
| Pistas de un álbum, `get_track` ×100 | 0,02 ms, 0,4 ms | igual |
| Pistas «por revisar» | 0,5 ms | 5 ms |
| Construir el índice de búsqueda (una vez; se rehace tras cambios) | 16 ms | 205 ms |
| Una búsqueda (índice ya construido) | 0,6–5 ms | 6–50 ms |

Con ~2 000 archivos **la base de datos y la búsqueda no son un cuello de botella**: no hace falta cambiar índices ni consultas.
Lo que sí se cambió: `PRAGMA synchronous = NORMAL` (con WAL). El escáner hace una transacción por archivo; con el valor por
defecto cada una hace `fsync`. Medido aquí: 2 000 transacciones tardan 0,24 s con `FULL` y 0,02 s con `NORMAL`. En Windows y
en discos lentos la diferencia es mucho mayor. Riesgo: si el sistema se cae, puede perderse lo último escrito (nunca se corrompe).

## Arranque (medir en tu máquina)
`SONOTECA_DEBUG_TIMING=1 sonoteca gui` (o el binario desde la terminal) escribe en stderr, en ms desde que empieza `run()`:
imports de Qt y de la aplicación → base de datos y controladores listos → QML cargado → primer fotograma en pantalla.
No incluye lo que tarda el sistema en lanzar el proceso (en macOS, la primera vez con una app sin firmar, Gatekeeper la revisa).

## Fluidez de la interfaz (medir en tu máquina)
- `QSG_RENDER_TIMING=1`: tiempos de cada fotograma del scene graph.
- `QSG_VISUALIZE=overdraw` (o `batches`, `clip`, `changes`): colorea lo que se redibuja de más.
- `QSG_INFO=1`: qué API gráfica usa Qt (Metal, OpenGL, Vulkan, software).
- Si algo va lento, di en qué pantalla y cuántas canciones hay: así se sabe si es el QML, Python o el disco.
