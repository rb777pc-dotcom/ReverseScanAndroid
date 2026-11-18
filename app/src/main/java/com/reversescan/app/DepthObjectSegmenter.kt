package com.reversescan.app

import java.util.ArrayDeque
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Extracts a depth-connected component, constrained to the user's lasso polygon.
 * The polygon prevents a connected wall/table from becoming part of the target.
 */
object DepthObjectSegmenter {
    data class Result(val mask: BooleanArray, val seedDepthMetres: Float, val pixelCount: Int)

    fun selectWithinPolygon(
        depths: FloatArray,
        width: Int,
        height: Int,
        polygon: FloatArray,
        minimumStepMetres: Float = 0.055f,
        relativeStep: Float = 0.04f
    ): Result? {
        if (width <= 0 || height <= 0 || depths.size != width * height || polygon.size < 6 || polygon.size % 2 != 0) return null

        val inside = BooleanArray(depths.size)
        var centerX = 0f
        var centerY = 0f
        val vertexCount = polygon.size / 2
        for (i in 0 until vertexCount) {
            centerX += polygon[i * 2]
            centerY += polygon[i * 2 + 1]
        }
        centerX /= vertexCount
        centerY /= vertexCount

        var seed = -1
        var bestDistance = Float.POSITIVE_INFINITY
        for (y in 0 until height) {
            for (x in 0 until width) {
                if (!insidePolygon(x + 0.5f, y + 0.5f, polygon)) continue
                val index = y * width + x
                inside[index] = true
                val depth = depths[index]
                if (depth <= 0f || !depth.isFinite()) continue
                val dx = x + 0.5f - centerX
                val dy = y + 0.5f - centerY
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
                    if (!inside[next] || mask[next]) continue
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

    /**
     * Selects the depth-connected component inside a world-space projected target mask.
     * The seed is the projected centre of the fixed AR target, not the screen centre.
     */
    fun selectWithinMask(
        depths: FloatArray,
        width: Int,
        height: Int,
        allowed: BooleanArray,
        seedX: Int,
        seedY: Int,
        minimumStepMetres: Float = 0.055f,
        relativeStep: Float = 0.04f
    ): Result? {
        if (width <= 0 || height <= 0 || depths.size != width * height || allowed.size != depths.size) return null
        var seed = -1
        var bestDistance = Float.POSITIVE_INFINITY
        for (i in allowed.indices) {
            if (!allowed[i]) continue
            val z = depths[i]
            if (z <= 0f || !z.isFinite()) continue
            val dx = i % width - seedX
            val dy = i / width - seedY
            val distance = dx.toFloat() * dx + dy.toFloat() * dy
            if (distance < bestDistance) {
                bestDistance = distance
                seed = i
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
            for (dy in -1..1) for (dx in -1..1) {
                if (dx == 0 && dy == 0) continue
                val nx = x + dx
                val ny = y + dy
                if (nx !in 0 until width || ny !in 0 until height) continue
                val next = ny * width + nx
                if (!allowed[next] || mask[next]) continue
                val nextDepth = depths[next]
                if (nextDepth <= 0f || !nextDepth.isFinite()) continue
                if (abs(nextDepth - currentDepth) <= threshold) {
                    mask[next] = true
                    queue.add(next)
                }
            }
        }
        return Result(mask, depths[seed], count)
    }

    /** Kept for focused tests and diagnostics; selects a component around a centre seed. */
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
        for (y in top..bottom) for (x in left..right) {
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
            for (dy in -1..1) for (dx in -1..1) {
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
        return Result(mask, depths[seed], count)
    }

    private fun insidePolygon(x: Float, y: Float, polygon: FloatArray): Boolean {
        var inside = false
        val count = polygon.size / 2
        var j = count - 1
        for (i in 0 until count) {
            val xi = polygon[i * 2]
            val yi = polygon[i * 2 + 1]
            val xj = polygon[j * 2]
            val yj = polygon[j * 2 + 1]
            val intersects = (yi > y) != (yj > y) &&
                x < (xj - xi) * (y - yi) / ((yj - yi).let { if (abs(it) < 1e-6f) 1e-6f else it }) + xi
            if (intersects) inside = !inside
            j = i
        }
        return inside
    }
}
