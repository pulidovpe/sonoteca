package io.github.pulidovpe.sonoteca.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.RectangleShape
import androidx.compose.ui.unit.dp
import io.github.pulidovpe.sonoteca.cover.CoverKeys
import io.github.pulidovpe.sonoteca.cover.CoverLoader
import io.github.pulidovpe.sonoteca.db.CoverSample

/** Portada de una lista de reproducción: collage de hasta 4 portadas de sus álbumes, repartido como en el escritorio ([CollageLayout]). */
@Composable
fun PlaylistCollage(
    loader: CoverLoader,
    playlistUuid: String,
    loadSamples: suspend (String) -> List<CoverSample>,
    modifier: Modifier = Modifier,
    colored: Boolean = true,
) {
    val samples by produceState(emptyList<CoverSample>(), playlistUuid) { value = loadSamples(playlistUuid) }
    val tiles = CollageLayout.tiles(samples.size)
    BoxWithConstraints(modifier = modifier.clip(RoundedCornerShape(4.dp)).background(Neon.placeholder)) {
        val gap = if (tiles.size > 1) 1.dp else 0.dp
        tiles.forEachIndexed { index, tile ->
            val sample = samples[index]
            CoverThumb(
                loader = loader,
                key = CoverKeys.album(sample.artist, sample.album),
                sampleUuid = sample.sampleUuid,
                artist = false,
                modifier = Modifier.offset(maxWidth * tile.x, maxHeight * tile.y).size(maxWidth * tile.w - gap, maxHeight * tile.h - gap),
                shape = RectangleShape,
                colored = colored,
            )
        }
    }
}
