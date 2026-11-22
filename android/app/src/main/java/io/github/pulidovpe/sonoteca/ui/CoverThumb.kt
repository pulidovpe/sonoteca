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
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.layout.ContentScale
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
) {
    val image by produceState<ImageBitmap?>(initialValue = loader.cached(key), key, sampleUuid) {
        if (value == null && sampleUuid.isNotEmpty()) value = loader.load(key, sampleUuid, artist)
    }
    Box(modifier = modifier.clip(shape).background(Neon.placeholder)) {
        image?.let { Image(bitmap = it, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize()) }
    }
}
