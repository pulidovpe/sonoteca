package io.github.pulidovpe.sonoteca.playback

import androidx.media3.common.Player
import org.junit.Assert.assertEquals
import org.junit.Test

class PlaybackModesTest {
    @Test
    fun repeatCyclesOffAllOneOff() {
        assertEquals(PlaybackModes.REPEAT_ALL, PlaybackModes.nextRepeat(PlaybackModes.REPEAT_OFF))
        assertEquals(PlaybackModes.REPEAT_ONE, PlaybackModes.nextRepeat(PlaybackModes.REPEAT_ALL))
        assertEquals(PlaybackModes.REPEAT_OFF, PlaybackModes.nextRepeat(PlaybackModes.REPEAT_ONE))
    }

    @Test
    fun anUnknownRepeatModeFallsBackToOff() {
        assertEquals(PlaybackModes.REPEAT_OFF, PlaybackModes.nextRepeat(99))
    }

    @Test
    fun theConstantsMatchMedia3() {
        assertEquals(Player.REPEAT_MODE_OFF, PlaybackModes.REPEAT_OFF)
        assertEquals(Player.REPEAT_MODE_ONE, PlaybackModes.REPEAT_ONE)
        assertEquals(Player.REPEAT_MODE_ALL, PlaybackModes.REPEAT_ALL)
    }

    @Test
    fun labelsDescribeTheMode() {
        assertEquals("Repetir", PlaybackModes.repeatLabel(PlaybackModes.REPEAT_OFF))
        assertEquals("Repetir todas", PlaybackModes.repeatLabel(PlaybackModes.REPEAT_ALL))
        assertEquals("Repetir una", PlaybackModes.repeatLabel(PlaybackModes.REPEAT_ONE))
    }
}
