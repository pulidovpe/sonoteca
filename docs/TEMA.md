# Tema «Neón»

El tema sale del logo de Sonoteca (`assets/icons/original.png`): fondo azul casi negro con un degradado cian → azul → violeta.
Todos los colores viven en **un solo archivo**, `src/sonoteca/ui/qml/Theme.qml`; las pantallas solo usan tokens
(`Theme.accent`, `Theme.surface`…). Una prueba (`tests/test_theme.py`) falla si alguien escribe un color fijo en otra pantalla
o usa un token que no existe.

## Colores de marca (muestreados del icono)
| Token | Valor | Uso |
|---|---|---|
| `cyan` (= `accent`) | `#00d0fc` | acento: botones principales, pista actual, selección |
| `blue` | `#0396fd` | centro del degradado |
| `violet` | `#9849fd` | extremo del degradado en los deslizadores |
| `magenta` | `#ba38fc` | extremo del degradado en el botón de reproducir |

## Superficies, líneas y texto
| Token | Valor | Uso |
|---|---|---|
| `bg` | `#060e16` | fondo de las páginas |
| `sidebar` / `bar` / `playerBar` | `#040a10` / `#050b11` / `#0a141d` | barra lateral, menú superior, reproductor |
| `surface` / `surfaceHover` / `surfaceRaised` | `#0c1822` / `#152536` / `#14212e` | tarjetas, hover, botones y campos |
| `panel` / `field` | `#0f1b27` / `#08121a` | diálogos y menús / campos de texto |
| `border` / `divider` / `track` | `#1e3043` / `#172636` / `#2b3d50` | bordes, separadores, ranuras |
| `text` / `textSoft` / `textDim` / `textFaint` | `#f4f9ff` / `#c9d6e2` / `#8da2b6` / `#5d7184` | texto normal, suave, secundario, deshabilitado |
| `warn` / `danger` / `textOnAccent` | `#f5c26b` / `#ff6b81` / `#031018` | avisos, errores, texto sobre el acento |

## Cómo cambiarlo
1. Edita los valores de `Theme.qml` (no hace falta tocar nada más).
2. Las portadas sin imagen usan `Theme.coverColor(id)`: un tono estable dentro de la gama cian → violeta.
3. Ejecuta `pytest tests/test_theme.py` para comprobar que no quedan colores sueltos.
