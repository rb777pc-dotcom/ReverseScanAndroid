package com.reversescan.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.MotionEvent
import android.view.View
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin

/** Rotatable preview of the accumulated scan points before surface reconstruction. */
class PointCloudPreviewView(context: Context, private val points: List<FloatArray>) : View(context) {
    private data class Projected(val x: Float, val y: Float, val depth: Float)

    private val pointPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(55, 235, 115) }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.LTGRAY
        textSize = 13f * resources.displayMetrics.density
    }
    private val center = FloatArray(3)
    private val scale: Float
    private var yaw = 0.65f
    private var pitch = -0.28f
    private var lastX = 0f
    private var lastY = 0f

    init {
        var minX = Float.POSITIVE_INFINITY
        var minY = Float.POSITIVE_INFINITY
        var minZ = Float.POSITIVE_INFINITY
        var maxX = Float.NEGATIVE_INFINITY
        var maxY = Float.NEGATIVE_INFINITY
        var maxZ = Float.NEGATIVE_INFINITY
        for (p in points) {
            if (p.size < 3) continue
            minX = minOf(minX, p[0]); maxX = maxOf(maxX, p[0])
            minY = minOf(minY, p[1]); maxY = maxOf(maxY, p[1])
            minZ = minOf(minZ, p[2]); maxZ = maxOf(maxZ, p[2])
        }
        if (points.isEmpty()) {
            minX = 0f; maxX = 1f; minY = 0f; maxY = 1f; minZ = 0f; maxZ = 1f
        }
        center[0] = (minX + maxX) * 0.5f
        center[1] = (minY + maxY) * 0.5f
        center[2] = (minZ + maxZ) * 0.5f
        val extent = max(maxX - minX, max(maxY - minY, maxZ - minZ)).coerceAtLeast(0.01f)
        scale = 1.8f / extent
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.rgb(18, 25, 36))
        if (points.isEmpty() || width == 0 || height == 0) return

        val maxDraw = 70_000
        val stride = max(1, (points.size + maxDraw - 1) / maxDraw)
        val projected = ArrayList<Projected>((points.size + stride - 1) / stride)
        val focal = minOf(width, height) * 0.82f
        val distance = 3.2f
        var index = 0
        for (p in points) {
            if (index++ % stride != 0 || p.size < 3) continue
            val x = (p[0] - center[0]) * scale
            val y = (p[1] - center[1]) * scale
            val z = (p[2] - center[2]) * scale
            val cy = cos(yaw); val sy = sin(yaw)
            val cx = cos(pitch); val sx = sin(pitch)
            val rx = x * cy + z * sy
            val rz = -x * sy + z * cy
            val ry = y * cx - rz * sx
            val rz2 = y * sx + rz * cx
            val depth = distance - rz2
            if (depth <= 0.2f) continue
            val perspective = focal / depth
            projected.add(Projected(width * 0.5f + rx * perspective, height * 0.48f - ry * perspective, depth))
        }
        projected.sortByDescending { it.depth }
        for (p in projected) {
            val radius = (2.3f - p.depth * 0.18f).coerceIn(1.1f, 2.4f) * resources.displayMetrics.density
            canvas.drawCircle(p.x, p.y, radius, pointPaint)
        }
        canvas.drawText("Накоплено точек: ${points.size}", 14f, 24f, textPaint)
        canvas.drawText("Проведите пальцем, чтобы осмотреть скан", 14f, height - 16f, textPaint)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                lastX = event.x
                lastY = event.y
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                yaw += (event.x - lastX) * 0.008f
                pitch = (pitch + (event.y - lastY) * 0.008f).coerceIn(-1.45f, 1.45f)
                lastX = event.x
                lastY = event.y
                invalidate()
                return true
            }
        }
        return true
    }
}
