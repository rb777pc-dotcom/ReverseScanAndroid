package com.reversescan.app

import java.io.OutputStream
import java.io.OutputStreamWriter
import java.util.Locale
import kotlin.math.sqrt

object MeshFileWriter {
    fun writeObj(mesh: MeshModel, output: OutputStream) {
        OutputStreamWriter(output, Charsets.UTF_8).buffered().use { writer ->
            writer.append("# ReverseScan triangle mesh; units: metres\n")
            writer.append("o ReverseScan\n")
            var i = 0
            while (i < mesh.vertices.size) {
                writer.append(String.format(Locale.US, "v %.6f %.6f %.6f\n",
                    mesh.vertices[i], mesh.vertices[i + 1], mesh.vertices[i + 2]))
                i += 3
            }
            var index = 1
            repeat(mesh.triangleCount) {
                writer.append("f $index ${index + 1} ${index + 2}\n")
                index += 3
            }
        }
    }

    fun writeStl(mesh: MeshModel, output: OutputStream) {
        OutputStreamWriter(output, Charsets.US_ASCII).buffered().use { writer ->
            writer.append("solid ReverseScan_mm\n")
            writer.append("  // STL coordinates exported in millimetres\n")
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
                writer.append(String.format(Locale.US, " facet normal %.6f %.6f %.6f\n", nx / length, ny / length, nz / length))
                writer.append("  outer loop\n")
                writer.append(String.format(Locale.US, "   vertex %.6f %.6f %.6f\n", ax * 1000f, ay * 1000f, az * 1000f))
                writer.append(String.format(Locale.US, "   vertex %.6f %.6f %.6f\n", bx * 1000f, by * 1000f, bz * 1000f))
                writer.append(String.format(Locale.US, "   vertex %.6f %.6f %.6f\n", cx * 1000f, cy * 1000f, cz * 1000f))
                writer.append("  endloop\n endfacet\n")
                i += 9
            }
            writer.append("endsolid ReverseScan_mm\n")
        }
    }
}
