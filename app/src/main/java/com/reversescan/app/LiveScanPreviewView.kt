package com.reversescan.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.MotionEvent
import android.view.View
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

data class ScanProgressSnapshot(
    val accumulatedPoints: List<FloatArray>,
    val currentFramePoints: List<FloatArray>,
    val viewsCaptured: Int,
    val acceptedPixels: Int,
    val seedDistanceMetres: Float
)

/** Small live 3D viewport: cyan is retained scan data, orange is the latest accepted frame. */
class LiveScanPreviewView(context: Context) : View(context) {
    private data class Projected(val x: Float, val y: Float, val depth: Float, val current: Boolean)

    private val density = resources.displayMetrics.density
    private val background = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0xE91A2533.toInt() }
    private val border = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF69D7C0.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 1.4f * density
    }
    private val retainedPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(55, 225, 190) }
    private val currentPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(255, 174, 65) }
    private val titlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 11f * density
        isFakeBoldText = true
    }
    private val detailPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFE2EAF2.toInt()
        textSize = 9f * density
    }
    private val hintPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFFFFC36B.toInt()
        textSize = 10f * density
        textAlign = Paint.Align.CENTER
    }

    private var snapshot = ScanProgressSnapshot(emptyList(), emptyList(), 0, 0, 0f)
    private var yaw = 0.65f
    private var pitch = -0.25f
    private var lastX = 0f
    private var lastY = 0f

    fun update(value: ScanProgressSnapshot) {
        snapshot = value
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val panel = RectF(0.5f * density, 0.5f * density, width - 0.5f * density, height - 0.5f * density)
        canvas.drawRoundRect(panel, 12f * density, 12f * density, background)
        canvas.drawRoundRect(panel, 12f * density, 12f * density, border)
        canvas.drawText("3D · ЧТО УЖЕ СНЯТО", 9f * density, 16f * density, titlePaint)

        val all = snapshot.accumulatedPoints
        val current = snapshot.currentFramePoints
        if (all.isEmpty() && current.isEmpty()) {
            hintPaint.textSize = 9f * density
            canvas.drawText("Предмет ещё не захвачен", width * 0.5f, height * 0.48f, hintPaint)
            canvas.drawText("Поместите его в центр рамки", width * 0.5f, height * 0.58f, detailPaint.apply { textAlign = Paint.Align.CENTER })
        } else {
            drawCloud(canvas, all, current)
        }

        detailPaint.textAlign = Paint.Align.LEFT
        canvas.drawText("СОХРАНЕНО: ${all.size} точек", 9f * density, height - 25f * density, detailPaint)
        val distance = if (snapshot.seedDistanceMetres > 0f) String.format(java.util.Locale.US, "%.2f м", snapshot.seedDistanceMetres) else "—"
        canvas.drawText("РАКУРСЫ: ${snapshot.viewsCaptured}   ДИСТАНЦИЯ: $distance", 9f * density, height - 11f * density, detailPaint)
    }

    private fun drawCloud(canvas: Canvas, retained: List<FloatArray>, current: List<FloatArray>) {
        var minX = Float.POSITIVE_INFINITY
        var minY = Float.POSITIVE_INFINITY
        var minZ = Float.POSITIVE_INFINITY
        var maxX = Float.NEGATIVE_INFINITY
        var maxY = Float.NEGATIVE_INFINITY
        var maxZ = Float.NEGATIVE_INFINITY
        fun bounds(points: List<FloatArray>) {
            for (p in points) if (p.size >= 3) {
                minX = min(minX, p[0]); maxX = max(maxX, p[0])
                minY = min(minY, p[1]); maxY = max(maxY, p[1])
                minZ = min(minZ, p[2]); maxZ = max(maxZ, p[2])
            }
        }
        bounds(retained)
        bounds(current)
        if (!minX.isFinite()) return
        val cx = (minX + maxX) * 0.5f
        val cy = (minY + maxY) * 0.5f
        val cz = (minZ + maxZ) * 0.5f
        val extent = max(max(maxX - minX, maxY - minY), maxZ - minZ).coerceAtLeast(0.04f)
        val plot = RectF(8f * density, 23f * density, width - 8f * density, height - 38f * density)
        val focal = min(plot.width(), plot.height()) * 0.72f / extent.coerceAtLeast(0.12f)
        val distance = 2.8f
        val projected = ArrayList<Projected>(retained.size + current.size)

        fun project(points: List<FloatArray>, isCurrent: Boolean, maxPoints: Int) {
            val stride = max(1, (points.size + maxPoints - 1) / maxPoints)
            var index = 0
            for (p in points) {
                if (index++ % stride != 0 || p.size < 3) continue
                val x = (p[0] - cx) / extent
                val y = (p[1] - cy) / extent
                val z = (p[2] - cz) / extent
                val c = cos(yaw); val s = sin(yaw)
                val rx = x * c + z * s
                val rz = -x * s + z * c
                val cp = cos(pitch); val sp = sin(pitch)
                val ry = y * cp - rz * sp
                val rz2 = y * sp + rz * cp
                val depth = distance - rz2
                if (depth <= 0.2f) continue
                val perspective = focal / depth
                projected.add(Projected(
                    plot.centerX() + rx * perspective,
                    plot.centerY() - ry * perspective,
                    depth,
                    isCurrent
                ))
            }
        }
        project(retained, false, 2600)
        project(current, true, 900)
        projected.sortByDescending { it.depth }
        for (p in projected) {
            val paint = if (p.current) currentPaint else retainedPaint
            val radius = if (p.current) 2.2f * density else 1.55f * density
            canvas.drawCircle(p.x, p.y, radius, paint)
        }
        canvas.drawText("● ГОТОВО", 9f * density, 32f * density, detailPaint.apply { color = retainedPaint.color })
        canvas.drawText("● СЕЙЧАС", 68f * density, 32f * density, detailPaint.apply { color = currentPaint.color })
        detailPaint.color = 0xFFE2EAF2.toInt()
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
                pitch = (pitch + (event.y - lastY) * 0.008f).coerceIn(-1.35f, 1.35f)
                lastX = event.x
                lastY = event.y
                invalidate()
                return true
            }
        }
        return true
    }
}
