package io.github.pulidovpe.sonoteca.download

/** Reglas de «cuánto está descargado» para colorear y filtrar (lógica pura, sin Android: se prueba en la JVM). */
object DownloadState {
    /** Completo = todas sus pistas están en el teléfono: se ve en color. Si falta alguna (también a medias) se ve en gris. */
    fun isComplete(tracks: Int, downloaded: Int): Boolean = tracks > 0 && downloaded >= tracks

    /** Tiene al menos una pista descargada: aparece en la pestaña «Descargado». */
    fun hasAny(downloaded: Int): Boolean = downloaded > 0
}
