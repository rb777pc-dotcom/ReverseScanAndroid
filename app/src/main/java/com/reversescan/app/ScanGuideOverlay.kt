package com.reversescan.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.PointF
import android.graphics.RectF
import android.view.MotionEvent
import android.view.View
import kotlin.math.hypot

/** Camera guide and touch lasso used to select the object before its 3D lock is created. */
class ScanGuideOverlay(context: Context) : View(context) {
    private val density = resources.displayMetrics.density
    private val guidePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xE6FFFFFF.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 2.2f * density
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 12f * density
        setShadowLayer(4f * density, 1f, 1f, Color.BLACK)
    }
    private val cornerPaint = Paint(guidePaint).apply { strokeWidth = 4f * density }
    private val centerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF71F0C1.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 2f * density
        setShadowLayer(4f * density, 0f, 0f, Color.BLACK)
    }
    private val lassoPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF42E6A4.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 3.5f * density
        strokeJoin = Paint.Join.ROUND
        strokeCap = Paint.Cap.ROUND
        setShadowLayer(5f * density, 0f, 0f, Color.BLACK)
    }
    private val lassoFillPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0x3342E6A4
        style = Paint.Style.FILL
    }
    private val pointPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        style = Paint.Style.FILL
    }

    private val lassoPoints = ArrayList<PointF>()
    private var selectionMode = false
    var onSelectionComplete: ((FloatArray) -> Unit)? = null

    init {
        setWillNotDraw(false)
        isClickable = false
        isFocusable = false
    }

    fun beginSelection() {
        lassoPoints.clear()
        selectionMode = true
        invalidate()
    }

    fun cancelSelection() {
        selectionMode = false
        lassoPoints.clear()
        invalidate()
    }

    /** Hides the screen-space contour after it has been converted to a world-space lock. */
    fun hideSelectionPath() {
        selectionMode = false
        lassoPoints.clear()
        invalidate()
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (!selectionMode) return false
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                lassoPoints.clear()
                lassoPoints.add(PointF(event.x, event.y))
                parent?.requestDisallowInterceptTouchEvent(true)
                invalidate()
                return true
            }
            MotionEvent.ACTION_MOVE -> {
                val last = lassoPoints.lastOrNull()
                if (last == null || hypot(event.x - last.x, event.y - last.y) >= 5f * density) {
                    lassoPoints.add(PointF(event.x, event.y))
                    invalidate()
                }
                return true
            }
            MotionEvent.ACTION_UP -> {
                val last = lassoPoints.lastOrNull()
                if (last == null || hypot(event.x - last.x, event.y - last.y) >= 2f * density) {
                    lassoPoints.add(PointF(event.x, event.y))
                }
                selectionMode = false
                if (lassoPoints.size >= 6) {
                    val polygon = FloatArray(lassoPoints.size * 2)
                    lassoPoints.forEachIndexed { index, point ->
                        polygon[index * 2] = point.x
                        polygon[index * 2 + 1] = point.y
                    }
                    onSelectionComplete?.invoke(polygon)
                } else {
                    lassoPoints.clear()
                }
                parent?.requestDisallowInterceptTouchEvent(false)
                invalidate()
                return true
            }
            MotionEvent.ACTION_CANCEL -> {
                selectionMode = false
                lassoPoints.clear()
                parent?.requestDisallowInterceptTouchEvent(false)
                invalidate()
                return true
            }
        }
        return true
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val left = width * 0.16f
        val top = height * 0.18f
        val right = width * 0.84f
        val bottom = height * 0.82f
        val radius = 14f * density
        canvas.drawRoundRect(RectF(left, top, right, bottom), radius, radius, guidePaint)

        val corner = 22f * density
        canvas.drawLine(left, top + corner, left, top, cornerPaint)
        canvas.drawLine(left, top, left + corner, top, cornerPaint)
        canvas.drawLine(right - corner, top, right, top, cornerPaint)
        canvas.drawLine(right, top, right, top + corner, cornerPaint)
        canvas.drawLine(left, bottom - corner, left, bottom, cornerPaint)
        canvas.drawLine(left, bottom, left + corner, bottom, cornerPaint)
        canvas.drawLine(right - corner, bottom, right, bottom, cornerPaint)
        canvas.drawLine(right, bottom - corner, right, bottom, cornerPaint)

        if (selectionMode) {
            val label = "ОБВЕДИТЕ ПРЕДМЕТ ПАЛЬЦЕМ"
            canvas.drawText(label, (width - labelPaint.measureText(label)) * 0.5f, top - 10f * density, labelPaint)
        } else {
            val centerX = width * 0.5f
            val centerY = height * 0.5f
            val centerRadius = 8f * density
            canvas.drawCircle(centerX, centerY, centerRadius, centerPaint)
            canvas.drawLine(centerX - centerRadius * 1.8f, centerY, centerX + centerRadius * 1.8f, centerY, centerPaint)
            canvas.drawLine(centerX, centerY - centerRadius * 1.8f, centerX, centerY + centerRadius * 1.8f, centerPaint)
            val label = "СНАЧАЛА ВЫДЕЛИТЕ ПРЕДМЕТ"
            canvas.drawText(label, (width - labelPaint.measureText(label)) * 0.5f, top - 10f * density, labelPaint)
        }

        if (lassoPoints.isNotEmpty()) {
            val path = Path().apply {
                moveTo(lassoPoints.first().x, lassoPoints.first().y)
                for (index in 1 until lassoPoints.size) lineTo(lassoPoints[index].x, lassoPoints[index].y)
                if (!selectionMode && lassoPoints.size >= 3) close()
            }
            if (!selectionMode && lassoPoints.size >= 3) canvas.drawPath(path, lassoFillPaint)
            canvas.drawPath(path, lassoPaint)
            lassoPoints.forEach { canvas.drawCircle(it.x, it.y, 2.4f * density, pointPaint) }
            if (!selectionMode && lassoPoints.size >= 3) {
                val label = "КОНТУР ВЫБРАН"
                canvas.drawText(label, 12f * density, height - 18f * density, labelPaint)
            }
        }
    }
}
