package com.reversescan.app

import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.sqrt

class MeshReconstructionTest {
    @Test
    fun packedGridCoordinatesRoundTripIncludingNegativeValues() {
        val key = TsdfVolume.encode(-12345, 6789, -42)
        assertTrue(TsdfVolume.decodeX(key) == -12345)
        assertTrue(TsdfVolume.decodeY(key) == 6789)
        assertTrue(TsdfVolume.decodeZ(key) == -42)
    }

    @Test
    fun sphereTsdfProducesTriangleSurface() {
        val voxel = 0.02f
        val radius = 0.12f
        val center = 10
        val truncation = 0.08f
        val samples = HashMap<Long, TsdfVolume.Sample>()

        for (x in 2..18) {
            for (y in 2..18) {
                for (z in 2..18) {
                    val dx = (x - center) * voxel
                    val dy = (y - center) * voxel
                    val dz = (z - center) * voxel
                    val distance = sqrt(dx * dx + dy * dy + dz * dz) - radius
                    val sdf = (distance / truncation).coerceIn(-1f, 1f)
                    samples[TsdfVolume.encode(x, y, z)] = TsdfVolume.Sample(sdf, 3)
                }
            }
        }

        val mesh = MeshReconstructor.reconstruct(samples, voxel)
        assertTrue("Expected a non-empty mesh from a closed sphere TSDF", mesh.triangleCount > 0)
        assertTrue("Mesh vertex buffer must contain complete triangles", mesh.vertices.size % 9 == 0)
        assertTrue("Mesh coordinates must be finite", mesh.vertices.all { it.isFinite() })
    }
}
