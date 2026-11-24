package io.github.pulidovpe.sonoteca.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.runtime.remember
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import io.github.pulidovpe.sonoteca.cover.CoverLoader

/**
 * Miniatura de la portada de un álbum o de la imagen de un artista. Mientras no hay imagen (o si el escritorio no tiene ninguna)
 * se ve la «cajita» de color plano del escritorio (`Neon.placeholder`).
 */
@Composable
fun CoverThumb(
    loader: CoverLoader,
    key: String,
    sampleUuid: String,
    artist: Boolean,
    modifier: Modifier = Modifier,
    shape: Shape = RoundedCornerShape(6.dp),
    colored: Boolean = true,
) {
    val image by produceState<ImageBitmap?>(initialValue = loader.cached(key), key, sampleUuid) {
        if (value == null && sampleUuid.isNotEmpty()) value = loader.load(key, sampleUuid, artist)
    }
    // lo que aún falta por descargar se ve en escala de grises; lo descargado, en color
    val filter = remember(colored) { if (colored) null else ColorFilter.colorMatrix(ColorMatrix().apply { setToSaturation(0f) }) }
    Box(modifier = modifier.clip(shape).background(Neon.placeholder)) {
        image?.let {
            Image(bitmap = it, contentDescription = null, contentScale = ContentScale.Crop, colorFilter = filter, modifier = Modifier.fillMaxSize())
        }
    }
}
