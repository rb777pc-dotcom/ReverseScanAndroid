package com.reversescan.app

import java.io.OutputStream
import java.io.OutputStreamWriter
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Locale
import kotlin.math.sqrt
import kotlin.math.roundToInt

object MeshFileWriter {
    fun writeObj(mesh: MeshModel, output: OutputStream) {
        val vertexMap = HashMap<Long, Int>()
        val uniqueVertices = ArrayList<FloatArray>()
        val faces = ArrayList<IntArray>(mesh.triangleCount)
        var offset = 0
        while (offset + 8 < mesh.vertices.size) {
            val face = IntArray(3)
            for (corner in 0..2) {
                val i = offset + corner * 3
                val x = mesh.vertices[i]
                val y = mesh.vertices[i + 1]
                val z = mesh.vertices[i + 2]
                // Weld duplicate triangle-soup vertices within 0.1 mm for connected OBJ topology.
                val key = TsdfVolume.encode(
                    (x * 10_000f).roundToInt(),
                    (y * 10_000f).roundToInt(),
                    (z * 10_000f).roundToInt()
                )
                val index = vertexMap[key] ?: run {
                    val next = uniqueVertices.size + 1
                    vertexMap[key] = next
                    uniqueVertices.add(floatArrayOf(x, y, z))
                    next
                }
                face[corner] = index
            }
            faces.add(face)
            offset += 9
        }

        OutputStreamWriter(output, Charsets.UTF_8).buffered().use { writer ->
            writer.append("# ReverseScan triangle mesh; coordinates in metres; vertices welded to 0.1 mm\n")
            writer.append("o ReverseScan\n")
            for (vertex in uniqueVertices) {
                writer.append(String.format(Locale.US, "v %.6f %.6f %.6f\n",
                    vertex[0], vertex[1], vertex[2]))
            }
            for (face in faces) {
                writer.append("f ${face[0]} ${face[1]} ${face[2]}\n")
            }
        }
    }

    /** Binary STL conventionally uses millimetres; convert the scan's metre coordinates. */
    fun writeStl(mesh: MeshModel, output: OutputStream) {
        output.use { stream ->
            val header = ByteArray(80)
            "ReverseScan binary STL - millimetres".toByteArray(Charsets.US_ASCII).copyInto(header)
            stream.write(header)
            stream.write(ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN)
                .putInt(mesh.triangleCount).array())

            val record = ByteBuffer.allocate(50).order(ByteOrder.LITTLE_ENDIAN)
            var i = 0
            while (i + 8 < mesh.vertices.size) {
                val ax = mesh.vertices[i]; val ay = mesh.vertices[i + 1]; val az = mesh.vertices[i + 2]
                val bx = mesh.vertices[i + 3]; val by = mesh.vertices[i + 4]; val bz = mesh.vertices[i + 5]
                val cx = mesh.vertices[i + 6]; val cy = mesh.vertices[i + 7]; val cz = mesh.vertices[i + 8]
                val abx = bx - ax; val aby = by - ay; val abz = bz - az
                val acx = cx - ax; val acy = cy - ay; val acz = cz - az
                val nx = aby * acz - abz * acy
                val ny = abz * acx - abx * acz
                val nz = abx * acy - aby * acx
                val length = sqrt(nx * nx + ny * ny + nz * nz).coerceAtLeast(1e-12f)

                record.clear()
                record.putFloat(nx / length).putFloat(ny / length).putFloat(nz / length)
                record.putFloat(ax * 1000f).putFloat(ay * 1000f).putFloat(az * 1000f)
                record.putFloat(bx * 1000f).putFloat(by * 1000f).putFloat(bz * 1000f)
                record.putFloat(cx * 1000f).putFloat(cy * 1000f).putFloat(cz * 1000f)
                record.putShort(0)
                stream.write(record.array())
                i += 9
            }
        }
    }
}
