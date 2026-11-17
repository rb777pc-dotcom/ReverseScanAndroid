package com.reversescan.app

import com.google.ar.core.Pose
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sqrt

data class MeshModel(val vertices: FloatArray) {
    val triangleCount: Int get() = vertices.size / 9
    val isEmpty: Boolean get() = vertices.isEmpty()
}

/**
 * Sparse projective TSDF volume. Values are accumulated in a scan-local metric
 * coordinate frame; positive values are in front of the observed surface.
 */
class TsdfVolume(
    val voxelSize: Float = 0.012f,
    private val truncation: Float = 0.048f,
    private val maxVoxels: Int = 420_000
) {
    private data class Voxel(var sdf: Float, var weight: Int)
    data class Sample(val sdf: Float, val weight: Int)

    private val voxels = HashMap<Long, Voxel>(65_536)
    private var origin: FloatArray? = null

    val voxelCount: Int get() = voxels.size

    fun clear() {
        voxels.clear()
        origin = null
    }

    fun integratePixel(pose: Pose, rayX: Float, rayY: Float, measuredDepth: Float, confidenceWeight: Int) {
        if (measuredDepth <= 0f || confidenceWeight <= 0) return
        if (origin == null) origin = pose.transformPoint(floatArrayOf(0f, 0f, 0f))
        val scanOrigin = origin ?: return

        var sampleDepth = max(0.12f, measuredDepth - truncation)
        val endDepth = min(5.0f, measuredDepth + truncation)
        val sampleStep = voxelSize * 0.8f

        while (sampleDepth <= endDepth) {
            val cameraPoint = floatArrayOf(rayX * sampleDepth, rayY * sampleDepth, -sampleDepth)
            val world = pose.transformPoint(cameraPoint)
            val gx = ((world[0] - scanOrigin[0]) / voxelSize).roundToInt()
            val gy = ((world[1] - scanOrigin[1]) / voxelSize).roundToInt()
            val gz = ((world[2] - scanOrigin[2]) / voxelSize).roundToInt()
            val key = encode(gx, gy, gz)
            val sdf = ((measuredDepth - sampleDepth) / truncation).coerceIn(-1f, 1f)

            val existing = voxels[key]
            if (existing != null) {
                val oldWeight = existing.weight
                val addedWeight = confidenceWeight.coerceAtMost(4)
                val newWeight = min(32, oldWeight + addedWeight)
                val effectiveAdded = newWeight - oldWeight
                if (effectiveAdded > 0) {
                    existing.sdf = (existing.sdf * oldWeight + sdf * effectiveAdded) / newWeight
                    existing.weight = newWeight
                }
            } else if (voxels.size < maxVoxels) {
                voxels[key] = Voxel(sdf, confidenceWeight.coerceAtMost(4))
            }
            sampleDepth += sampleStep
        }
    }

    fun snapshot(): Map<Long, Sample> {
        val copy = HashMap<Long, Sample>(voxels.size)
        for ((key, value) in voxels) copy[key] = Sample(value.sdf, value.weight)
        return copy
    }

    companion object {
        private const val MASK = 0x1FFFFF
        private const val SIGN_BIT = 0x100000

        fun encode(x: Int, y: Int, z: Int): Long {
            val xx = x.coerceIn(-1_048_576, 1_048_575)
            val yy = y.coerceIn(-1_048_576, 1_048_575)
            val zz = z.coerceIn(-1_048_576, 1_048_575)
            return ((xx.toLong() and MASK.toLong()) shl 42) or
                ((yy.toLong() and MASK.toLong()) shl 21) or
                (zz.toLong() and MASK.toLong())
        }

        fun decodeX(key: Long): Int = signed21((key ushr 42).toInt() and MASK)
        fun decodeY(key: Long): Int = signed21((key ushr 21).toInt() and MASK)
        fun decodeZ(key: Long): Int = signed21(key.toInt() and MASK)

        private fun signed21(value: Int): Int =
            if ((value and SIGN_BIT) != 0) value or -0x200000 else value
    }
}

/**
 * Converts a sparse TSDF into a triangle surface using marching tetrahedra.
 * The output is a metric triangle mesh, suitable for OBJ and STL export.
 */
object MeshReconstructor {
    private data class Vec3(val x: Float, val y: Float, val z: Float) {
        operator fun minus(other: Vec3) = Vec3(x - other.x, y - other.y, z - other.z)
    }

    private class FloatBuilder(initialCapacity: Int = 32_768) {
        private var data = FloatArray(initialCapacity)
        var size = 0
            private set
        val triangleCount: Int get() = size / 9

        fun addTriangle(a: Vec3, b: Vec3, c: Vec3, outward: Vec3) {
            var second = b
            var third = c
            val ab = second - a
            val ac = third - a
            val nx = ab.y * ac.z - ab.z * ac.y
            val ny = ab.z * ac.x - ab.x * ac.z
            val nz = ab.x * ac.y - ab.y * ac.x
            if (nx * outward.x + ny * outward.y + nz * outward.z < 0f) {
                val swap = second
                second = third
                third = swap
            }
            val finalAb = second - a
            val finalAc = third - a
            val finalNx = finalAb.y * finalAc.z - finalAb.z * finalAc.y
            val finalNy = finalAb.z * finalAc.x - finalAb.x * finalAc.z
            val finalNz = finalAb.x * finalAc.y - finalAb.y * finalAc.x
            if (finalNx * finalNx + finalNy * finalNy + finalNz * finalNz < 1e-12f) return
            ensure(9)
            data[size++] = a.x; data[size++] = a.y; data[size++] = a.z
            data[size++] = second.x; data[size++] = second.y; data[size++] = second.z
            data[size++] = third.x; data[size++] = third.y; data[size++] = third.z
        }

        fun toArray(): FloatArray = data.copyOf(size)

        private fun ensure(count: Int) {
            if (size + count > data.size) data = data.copyOf(max(data.size * 2, size + count))
        }
    }

    private val cubeCorners = arrayOf(
        intArrayOf(0, 0, 0), intArrayOf(1, 0, 0),
        intArrayOf(1, 1, 0), intArrayOf(0, 1, 0),
        intArrayOf(0, 0, 1), intArrayOf(1, 0, 1),
        intArrayOf(1, 1, 1), intArrayOf(0, 1, 1)
    )

    private val tetrahedra = arrayOf(
        intArrayOf(0, 5, 1, 6),
        intArrayOf(0, 1, 2, 6),
        intArrayOf(0, 2, 3, 6),
        intArrayOf(0, 3, 7, 6),
        intArrayOf(0, 7, 4, 6),
        intArrayOf(0, 4, 5, 6)
    )

    fun reconstruct(samples: Map<Long, TsdfVolume.Sample>, voxelSize: Float): MeshModel {
        if (samples.size < 8) return MeshModel(FloatArray(0))
        val output = FloatBuilder()
        val corners = Array(8) { Vec3(0f, 0f, 0f) }
        val values = FloatArray(8)

        for ((key, _) in samples) {
            if (output.triangleCount >= MAX_TRIANGLES) break
            val gx = TsdfVolume.decodeX(key)
            val gy = TsdfVolume.decodeY(key)
            val gz = TsdfVolume.decodeZ(key)
            var complete = true
            var minValue = Float.POSITIVE_INFINITY
            var maxValue = Float.NEGATIVE_INFINITY

            for (i in 0 until 8) {
                val offset = cubeCorners[i]
                val sample = samples[TsdfVolume.encode(gx + offset[0], gy + offset[1], gz + offset[2])]
                if (sample == null || sample.weight <= 0) {
                    complete = false
                    break
                }
                values[i] = sample.sdf
                corners[i] = Vec3(
                    (gx + offset[0]) * voxelSize,
                    (gy + offset[1]) * voxelSize,
                    (gz + offset[2]) * voxelSize
                )
                minValue = min(minValue, sample.sdf)
                maxValue = max(maxValue, sample.sdf)
            }
            if (!complete || minValue >= 0f || maxValue <= 0f) continue

            for (tetra in tetrahedra) {
                if (output.triangleCount >= MAX_TRIANGLES) break
                val p = Array(4) { corners[tetra[it]] }
                val v = FloatArray(4) { values[tetra[it]] }
                polygoniseTetra(p, v, output)
            }
        }
        return MeshModel(output.toArray())
    }

    private fun polygoniseTetra(p: Array<Vec3>, v: FloatArray, out: FloatBuilder) {
        val inside = IntArray(4)
        val outside = IntArray(4)
        var insideCount = 0
        var outsideCount = 0
        for (i in 0..3) {
            if (v[i] < 0f) inside[insideCount++] = i else outside[outsideCount++] = i
        }
        if (insideCount == 0 || insideCount == 4) return

        var insideX = 0f; var insideY = 0f; var insideZ = 0f
        var outsideX = 0f; var outsideY = 0f; var outsideZ = 0f
        for (i in 0 until insideCount) {
            val point = p[inside[i]]
            insideX += point.x; insideY += point.y; insideZ += point.z
        }
        for (i in 0 until outsideCount) {
            val point = p[outside[i]]
            outsideX += point.x; outsideY += point.y; outsideZ += point.z
        }
        val outward = Vec3(
            outsideX / outsideCount - insideX / insideCount,
            outsideY / outsideCount - insideY / insideCount,
            outsideZ / outsideCount - insideZ / insideCount
        )

        fun emit(a: Vec3, b: Vec3, c: Vec3) = out.addTriangle(a, b, c, outward)

        fun edge(a: Int, b: Int): Vec3 {
            val denominator = v[a] - v[b]
            val t = if (abs(denominator) < 1e-8f) 0.5f else (v[a] / denominator).coerceIn(0f, 1f)
            return Vec3(
                p[a].x + (p[b].x - p[a].x) * t,
                p[a].y + (p[b].y - p[a].y) * t,
                p[a].z + (p[b].z - p[a].z) * t
            )
        }

        when (insideCount) {
            1 -> {
                val a = edge(inside[0], outside[0])
                val b = edge(inside[0], outside[1])
                val c = edge(inside[0], outside[2])
                emit(a, b, c)
            }
            3 -> {
                val a = edge(outside[0], inside[0])
                val b = edge(outside[0], inside[1])
                val c = edge(outside[0], inside[2])
                emit(a, c, b)
            }
            2 -> {
                val a = edge(inside[0], outside[0])
                val b = edge(inside[0], outside[1])
                val c = edge(inside[1], outside[0])
                val d = edge(inside[1], outside[1])
                emit(a, b, c)
                emit(b, d, c)
            }
        }
    }

    private const val MAX_TRIANGLES = 250_000
}
