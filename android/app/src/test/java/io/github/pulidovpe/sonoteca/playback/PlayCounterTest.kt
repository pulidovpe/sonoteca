package io.github.pulidovpe.sonoteca.playback

import org.junit.Assert.assertEquals
import org.junit.Test

class PlayCounterTest {
    private val counted = mutableListOf<String>()
    private val counter = PlayCounter { counted += it }

    private fun play(from: Long, to: Long, step: Long = 500, duration: Long = 200_000) {
        var position = from
        while (position <= to) {
            counter.onPosition(position, duration)
            position += step
        }
    }

    @Test
    fun countsAfterThreeSecondsOfNormalPlayback() {
        counter.startItem("u1")
        play(0, 2_500)
        assertEquals(emptyList<String>(), counted)
        play(3_000, 3_000)
        assertEquals(listOf("u1"), counted)
    }

    @Test
    fun countsOnlyOncePerPlay() {
        counter.startItem("u1")
        play(0, 60_000)
        assertEquals(listOf("u1"), counted)
    }

    @Test
    fun seekingDoesNotCountAsListening() {
        counter.startItem("u1")
        play(0, 1_000)
        play(90_000, 90_500)      // salto con la barra: no suma
        play(10_000, 10_500)      // retroceso: tampoco
        assertEquals(emptyList<String>(), counted)
    }

    @Test
    fun pausingDoesNotAddTime() {
        counter.startItem("u1")
        play(0, 1_000)
        repeat(20) { counter.onPosition(1_000, 200_000) }   // en pausa la posición no cambia
        assertEquals(emptyList<String>(), counted)
    }

    @Test
    fun shortTracksCountWhenFullyHeard() {
        counter.startItem("u1")
        play(0, 1_000, step = 500, duration = 1_500)
        assertEquals(emptyList<String>(), counted)
        counter.onPosition(1_500, 1_500)
        assertEquals(listOf("u1"), counted)
    }

    @Test
    fun theThresholdIsThreeSecondsOrTheDurationIfShorter() {
        assertEquals(3_000L, PlayCounter.threshold(0))
        assertEquals(3_000L, PlayCounter.threshold(200_000))
        assertEquals(1_500L, PlayCounter.threshold(1_500))
        assertEquals(1L, PlayCounter.threshold(1))
    }

    @Test
    fun startingAnotherTrackOrTheSameAgainStartsOver() {
        counter.startItem("u1")
        play(0, 3_000)
        counter.startItem("u2")
        play(0, 2_500)
        assertEquals(listOf("u1"), counted)
        counter.startItem("u1")   // repetir la misma pista cuenta otra reproducción
        play(0, 3_000)
        assertEquals(listOf("u1", "u1"), counted)
    }

    @Test
    fun nothingCountsWithoutATrack() {
        counter.startItem(null)
        play(0, 10_000)
        assertEquals(emptyList<String>(), counted)
    }

    @Test
    fun timestampsUseTheProtocolFormat() {
        assertEquals("1970-01-01T00:00:00.000Z", PlayEvents.timestamp(0))
        assertEquals("2025-11-18T10:00:00.123Z", PlayEvents.timestamp(1_763_460_000_123L))
    }
}
