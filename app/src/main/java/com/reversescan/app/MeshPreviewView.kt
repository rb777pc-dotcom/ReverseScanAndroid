package com.reversescan.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.view.MotionEvent
import android.view.View
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/** Lightweight interactive shaded preview for the reconstructed triangle mesh. */
class MeshPreviewView(context: Context, private val mesh: MeshModel) : View(context) {
    private data class Point3(val x: Float, val y: Float, val z: Float)
    private data class Face(val xy: FloatArray, val depth: Float, val shade: Float)

    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.LTGRAY
        textSize = 13f * resources.displayMetrics.density
    }
    private val center = FloatArray(3)
    private val modelScale: Float
    private var yaw = 0.65f
    private var pitch = -0.28f
    private var lastX = 0f
    private var lastY = 0f

    init {
        val v = mesh.vertices
        var minX = Float.POSITIVE_INFINITY
        var minY = Float.POSITIVE_INFINITY
        var minZ = Float.POSITIVE_INFINITY
        var maxX = Float.NEGATIVE_INFINITY
        var maxY = Float.NEGATIVE_INFINITY
        var maxZ = Float.NEGATIVE_INFINITY
        var i = 0
        while (i + 2 < v.size) {
            minX = min(minX, v[i]); maxX = max(maxX, v[i])
            minY = min(minY, v[i + 1]); maxY = max(maxY, v[i + 1])
            minZ = min(minZ, v[i + 2]); maxZ = max(maxZ, v[i + 2])
            i += 3
        }
        center[0] = (minX + maxX) * 0.5f
        center[1] = (minY + maxY) * 0.5f
        center[2] = (minZ + maxZ) * 0.5f
        val extent = max(maxX - minX, max(maxY - minY, maxZ - minZ)).coerceAtLeast(0.001f)
        modelScale = 1.8f / extent
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.rgb(20, 27, 38))
        if (mesh.isEmpty || width == 0 || height == 0) return

        val faces = ArrayList<Face>()
        val stride = max(1, mesh.triangleCount / 12_000)
        val focal = min(width, height) * 0.95f
        val distance = 3.4f
        var triangle = 0
        while (triangle < mesh.triangleCount) {
            val base = triangle * 9
            val a = transform(base)
            val b = transform(base + 3)
            val c = transform(base + 6)
            val abx = b.x - a.x; val aby = b.y - a.y; val abz = b.z - a.z
            val acx = c.x - a.x; val acy = c.y - a.y; val acz = c.z - a.z
            val nx = aby * acz - abz * acy
            val ny = abz * acx - abx * acz
            val nz = abx * acy - aby * acx
            val length = sqrt(nx * nx + ny * ny + nz * nz).coerceAtLeast(1e-6f)
            val lightLength = sqrt(0.2f * 0.2f + 0.55f * 0.55f + 0.8f * 0.8f)
            val diffuse = abs((nx * 0.2f + ny * 0.55f + nz * 0.8f) / (length * lightLength))
            val shade = (0.28f + 0.72f * diffuse).coerceIn(0.25f, 1f)

            fun project(p: Point3): Pair<Float, Float> {
                val perspective = focal / (distance - p.z).coerceAtLeast(0.35f)
                return Pair(width * 0.5f + p.x * perspective, height * 0.47f - p.y * perspective)
            }
            val pa = project(a); val pb = project(b); val pc = project(c)
            faces.add(Face(
                floatArrayOf(pa.first, pa.second, pb.first, pb.second, pc.first, pc.second),
                (a.z + b.z + c.z) / 3f,
                shade
            ))
            triangle += stride
        }

        faces.sortBy { it.depth }
        for (face in faces) {
            val intensity = (70 + 150 * face.shade).toInt().coerceIn(0, 255)
            fill.color = Color.rgb((intensity / 1.04f).toInt().coerceIn(0, 255), intensity, (intensity * 1.08f).toInt().coerceIn(0, 255))
            val path = Path().apply {
                moveTo(face.xy[0], face.xy[1])
                lineTo(face.xy[2], face.xy[3])
                lineTo(face.xy[4], face.xy[5])
                close()
            }
            canvas.drawPath(path, fill)
        }
        canvas.drawText("Проведите пальцем, чтобы повернуть модель", 14f, height - 16f, text)
    }

    private fun transform(offset: Int): Point3 {
        val v = mesh.vertices
        val x = (v[offset] - center[0]) * modelScale
        val y = (v[offset + 1] - center[1]) * modelScale
        val z = (v[offset + 2] - center[2]) * modelScale
        val cy = kotlin.math.cos(yaw); val sy = kotlin.math.sin(yaw)
        val cx = kotlin.math.cos(pitch); val sx = kotlin.math.sin(pitch)
        val rx = x * cy + z * sy
        val rz = -x * sy + z * cy
        val ry = y * cx - rz * sx
        val rz2 = y * sx + rz * cx
        return Point3(rx, ry, rz2)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                lastX = event.x
                lastY = event.y
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                val dx = event.x - lastX
                val dy = event.y - lastY
                yaw += dx * 0.008f
                pitch = (pitch + dy * 0.008f).coerceIn(-1.45f, 1.45f)
                lastX = event.x
                lastY = event.y
                invalidate()
                return true
            }
        }
        return true
    }
}
