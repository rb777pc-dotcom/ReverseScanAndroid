package com.reversescan.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

class MeshFileWriterTest {
    @Test
    fun objWeldsSharedVerticesAcrossTriangles() {
        val mesh = MeshModel(floatArrayOf(
            0f, 0f, 0f, 1f, 0f, 0f, 0f, 1f, 0f,
            1f, 0f, 0f, 1f, 1f, 0f, 0f, 1f, 0f
        ))
        val output = ByteArrayOutputStream()
        MeshFileWriter.writeObj(mesh, output)
        val lines = output.toString("UTF-8").lines()
        assertEquals(4, lines.count { it.startsWith("v ") })
        assertEquals(2, lines.count { it.startsWith("f ") })
    }

    @Test
    fun binaryStlUsesMillimetresAndExpectedRecordSize() {
        val mesh = MeshModel(floatArrayOf(
            0f, 0f, 0f, 1f, 0f, 0f, 0f, 1f, 0f
        ))
        val output = ByteArrayOutputStream()
        MeshFileWriter.writeStl(mesh, output)
        val bytes = output.toByteArray()
        assertEquals(134, bytes.size) // 80-byte header + 4-byte count + one 50-byte triangle
        val firstVertexX = ByteBuffer.wrap(bytes, 108, 4).order(ByteOrder.LITTLE_ENDIAN).getFloat()
        assertEquals(1000f, firstVertexX, 0.001f)
        assertTrue(bytes.copyOfRange(80, 84).contentEquals(byteArrayOf(1, 0, 0, 0)))
    }
}
