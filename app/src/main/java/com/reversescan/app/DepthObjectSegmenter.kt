package com.reversescan.app

import java.util.ArrayDeque
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Extracts the depth-connected component containing the centre of the scan frame.
 * This keeps distant background surfaces from being accumulated with the target.
 */
object DepthObjectSegmenter {
    data class Result(val mask: BooleanArray, val seedDepthMetres: Float, val pixelCount: Int)

    fun select(
        depths: FloatArray,
        width: Int,
        height: Int,
        seedX: Int = width / 2,
        seedY: Int = height / 2,
        seedSearchRadius: Int = 8,
        minimumStepMetres: Float = 0.055f,
        relativeStep: Float = 0.04f
    ): Result? {
        if (width <= 0 || height <= 0 || depths.size != width * height) return null

        var seed = -1
        var bestDistance = Int.MAX_VALUE
        val left = max(0, seedX - seedSearchRadius)
        val right = min(width - 1, seedX + seedSearchRadius)
        val top = max(0, seedY - seedSearchRadius)
        val bottom = min(height - 1, seedY + seedSearchRadius)
        for (y in top..bottom) {
            for (x in left..right) {
                val index = y * width + x
                val depth = depths[index]
                if (depth <= 0f || !depth.isFinite()) continue
                val dx = x - seedX
                val dy = y - seedY
                val distance = dx * dx + dy * dy
                if (distance < bestDistance) {
                    bestDistance = distance
                    seed = index
                }
            }
        }
        if (seed < 0) return null

        val mask = BooleanArray(depths.size)
        val queue = ArrayDeque<Int>()
        queue.add(seed)
        mask[seed] = true
        var count = 0
        while (queue.isNotEmpty()) {
            val index = queue.removeFirst()
            count++
            val x = index % width
            val y = index / width
            val currentDepth = depths[index]
            val threshold = max(minimumStepMetres, currentDepth * relativeStep)
            for (dy in -1..1) {
                for (dx in -1..1) {
                    if (dx == 0 && dy == 0) continue
                    val nx = x + dx
                    val ny = y + dy
                    if (nx !in 0 until width || ny !in 0 until height) continue
                    val next = ny * width + nx
                    if (mask[next]) continue
                    val nextDepth = depths[next]
                    if (nextDepth <= 0f || !nextDepth.isFinite()) continue
                    if (abs(nextDepth - currentDepth) <= threshold) {
                        mask[next] = true
                        queue.add(next)
                    }
                }
            }
        }
        return Result(mask, depths[seed], count)
    }
}
