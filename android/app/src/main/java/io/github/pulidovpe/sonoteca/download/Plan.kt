package io.github.pulidovpe.sonoteca.download

import io.github.pulidovpe.sonoteca.db.TrackEntity
import java.util.Locale

/** Margen que se deja libre en el teléfono: no se descarga si el espacio sobrante quedaría por debajo. */
const val FREE_SPACE_MARGIN_BYTES: Long = 200L * 1024 * 1024

/**
 * Qué falta por descargar de una selección. Una pista cuenta como descargada solo si la huella guardada coincide con la del
 * catálogo; si el escritorio la cambió (p. ej. editó sus tags) hay que volver a bajarla (`replacing`).
 */
data class DownloadPlan(
    val label: String,
    val totalTracks: Int,
    val pending: List<TrackEntity>,
    val replacing: Int,
    val freeBytes: Long,
    /** Pistas de la selección que tienen alguna descarga en el teléfono (aunque esté desactualizada): lo que se puede borrar. */
    val onPhone: Int = 0,
    /** Pistas de la selección que el escritorio aún no puede entregar (sin huella): no se descargan todavía. */
    val notReady: Int = 0,
) {
    val pendingBytes: Long = pending.sumOf { it.size }
    val alreadyDone: Int = totalTracks - pending.size - notReady
    val fits: Boolean = pendingBytes + FREE_SPACE_MARGIN_BYTES <= freeBytes
}

fun buildPlan(
    label: String,
    tracks: List<TrackEntity>,
    downloadedHashes: Map<String, String>,
    freeBytes: Long,
): DownloadPlan {
    val pending = tracks.filter { it.hash.isNotEmpty() && downloadedHashes[it.uuid] != it.hash }
    val notReady = tracks.count { it.hash.isEmpty() }
    val replacing = pending.count { downloadedHashes.containsKey(it.uuid) }
    val onPhone = tracks.count { downloadedHashes.containsKey(it.uuid) }
    return DownloadPlan(label, tracks.size, pending, replacing, freeBytes, onPhone, notReady)
}

fun formatBytes(bytes: Long): String {
    val kb = 1024.0
    val mb = kb * 1024
    val gb = mb * 1024
    return when {
        bytes >= gb -> String.format(Locale.ROOT, "%.1f GB", bytes / gb)
        bytes >= mb -> String.format(Locale.ROOT, "%.0f MB", bytes / mb)
        else -> String.format(Locale.ROOT, "%.0f KB", bytes / kb)
    }
}
