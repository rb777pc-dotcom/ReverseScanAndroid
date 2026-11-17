package com.reversescan.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class DepthObjectSegmenterTest {
    @Test
    fun centreSeedKeepsForegroundObjectAndRejectsDistantBackground() {
        val width = 40
        val height = 30
        val depths = FloatArray(width * height) { 1.8f }
        var expectedObjectPixels = 0
        for (y in 8..21) {
            for (x in 10..29) {
                depths[y * width + x] = 0.82f
                expectedObjectPixels++
            }
        }

        val result = DepthObjectSegmenter.select(depths, width, height)
        assertNotNull(result)
        assertEquals(expectedObjectPixels, result!!.pixelCount)
        for (y in 0 until height) {
            for (x in 0 until width) {
                val isObject = x in 10..29 && y in 8..21
                assertEquals("Unexpected background selection at ($x,$y)", isObject, result.mask[y * width + x])
            }
        }
    }

    @Test
    fun emptyDepthMapDoesNotInventAnObject() {
        val result = DepthObjectSegmenter.select(FloatArray(100), 10, 10)
        assertTrue(result == null)
    }
}
