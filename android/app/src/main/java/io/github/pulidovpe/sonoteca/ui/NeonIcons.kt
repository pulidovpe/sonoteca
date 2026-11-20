package io.github.pulidovpe.sonoteca.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.material3.LocalContentColor
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathFillType
import androidx.compose.ui.graphics.drawscope.scale
import androidx.compose.ui.graphics.vector.PathParser
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/** Iconos del escritorio (`Theme.qml`): trazos SVG en una cuadrícula de 24×24. Generado a partir de ese archivo; `NeonParityTest` los compara. */
object NeonIcons {
    const val _ALBUM = "M12 3 A9 9 0 1 0 12 21 A9 9 0 1 0 12 3 Z M12 6.5 A5.5 5.5 0 1 1 12 17.5 A5.5 5.5 0 1 1 12 6.5 Z M12 10 A2 2 0 1 0 12 14 A2 2 0 1 0 12 10 Z"
    const val _ARTIST = "M12 4 A4 4 0 1 0 12 12 A4 4 0 1 0 12 4 Z M4 20 C4 15.5 8 14 12 14 C16 14 20 15.5 20 20 Z"
    const val _LIST = "M9 6 H21 V8 H9 Z M9 11 H21 V13 H9 Z M9 16 H21 V18 H9 Z M3 6 H6 V8 H3 Z M3 11 H6 V13 H3 Z M3 16 H6 V18 H3 Z"
    const val _QUEUE = "M4 12 H8 V20 H4 Z M10 4 H14 V20 H10 Z M16 9 H20 V20 H16 Z"
    const val _HEADPHONES = "M12 3 A9 9 0 0 0 3 12 V19 A2 2 0 0 0 5 21 H7 V13 H5 V12 A7 7 0 0 1 19 12 V13 H17 V21 H19 A2 2 0 0 0 21 19 V12 A9 9 0 0 0 12 3 Z"
    const val _DISPLAY = "M3 4 H21 V16 H3 Z M5 6 V14 H19 V6 Z M8 18 H16 V20 H8 Z"
    const val _PLAY = "M8 4 L20 12 L8 20 Z"
    const val _PAUSE = "M6 4 H10 V20 H6 Z M14 4 H18 V20 H14 Z"
    const val _NEXT = "M5 4 L16 12 L5 20 Z M17 4 H20 V20 H17 Z"
    const val _PREV = "M19 4 L8 12 L19 20 Z M4 4 H7 V20 H4 Z"
    const val _HOME = "M12 3 L2 12 H5 V20 H10 V15 H14 V20 H19 V12 H22 Z"
    const val _GLOBE = "M12 3 A9 9 0 1 0 12 21 A9 9 0 1 0 12 3 Z M12 4.8 A7.2 7.2 0 1 1 12 19.2 A7.2 7.2 0 1 1 12 4.8 Z M4.8 11 H19.2 V13 H4.8 Z M12 4.8 A3.5 7.2 0 1 0 12 19.2 A3.5 7.2 0 1 0 12 4.8 Z M12 6.3 A2 5.7 0 1 1 12 17.7 A2 5.7 0 1 1 12 6.3 Z"

    /** Nombre en `Theme.qml` → trazo. */
    val all: Map<String, String> = mapOf(
        "iconAlbum" to _ALBUM,
        "iconArtist" to _ARTIST,
        "iconList" to _LIST,
        "iconQueue" to _QUEUE,
        "iconHeadphones" to _HEADPHONES,
        "iconDisplay" to _DISPLAY,
        "iconPlay" to _PLAY,
        "iconPause" to _PAUSE,
        "iconNext" to _NEXT,
        "iconPrev" to _PREV,
        "iconHome" to _HOME,
        "iconGlobe" to _GLOBE,
    )
}

/** Dibuja un icono del escritorio con relleno par-impar (como las formas de QtQuick), escalado desde la cuadrícula de 24×24. */
@Composable
fun PathIcon(pathData: String, modifier: Modifier = Modifier, size: Dp = 24.dp, tint: Color = LocalContentColor.current, description: String? = null) {
    val path = remember(pathData) { PathParser().parsePathString(pathData).toPath().apply { fillType = PathFillType.EvenOdd } }
    val semantic = if (description != null) Modifier.semantics { this.contentDescription = description } else Modifier
    Canvas(modifier.size(size).then(semantic)) {
        scale(scale = this.size.minDimension / 24f, pivot = Offset.Zero) { drawPath(path, color = tint) }
    }
}
