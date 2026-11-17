package com.reversescan.app

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.View

/** On-camera guide for the central depth region used by the scanner. */
class ScanGuideOverlay(context: Context) : View(context) {
    private val guidePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xE6FFFFFF.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 2.2f * resources.displayMetrics.density
    }
    private val labelPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 12f * resources.displayMetrics.density
        setShadowLayer(4f * resources.displayMetrics.density, 1f, 1f, Color.BLACK)
    }
    private val cornerPaint = Paint(guidePaint).apply {
        strokeWidth = 4f * resources.displayMetrics.density
    }
    private val centerPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = 0xFF71F0C1.toInt()
        style = Paint.Style.STROKE
        strokeWidth = 2f * resources.displayMetrics.density
        setShadowLayer(4f * resources.displayMetrics.density, 0f, 0f, Color.BLACK)
    }

    init {
        setWillNotDraw(false)
        isClickable = false
        isFocusable = false
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val left = width * 0.22f
        val top = height * 0.22f
        val right = width * 0.78f
        val bottom = height * 0.78f
        val radius = 14f * resources.displayMetrics.density
        canvas.drawRoundRect(RectF(left, top, right, bottom), radius, radius, guidePaint)

        val corner = 22f * resources.displayMetrics.density
        canvas.drawLine(left, top + corner, left, top, cornerPaint)
        canvas.drawLine(left, top, left + corner, top, cornerPaint)
        canvas.drawLine(right - corner, top, right, top, cornerPaint)
        canvas.drawLine(right, top, right, top + corner, cornerPaint)
        canvas.drawLine(left, bottom - corner, left, bottom, cornerPaint)
        canvas.drawLine(left, bottom, left + corner, bottom, cornerPaint)
        canvas.drawLine(right - corner, bottom, right, bottom, cornerPaint)
        canvas.drawLine(right, bottom - corner, right, bottom, cornerPaint)

        // The centre mark is the depth-segmentation seed: keep the object itself here.
        val centerX = width * 0.5f
        val centerY = height * 0.5f
        val centerRadius = 8f * resources.displayMetrics.density
        canvas.drawCircle(centerX, centerY, centerRadius, centerPaint)
        canvas.drawLine(centerX - centerRadius * 1.8f, centerY, centerX + centerRadius * 1.8f, centerY, centerPaint)
        canvas.drawLine(centerX, centerY - centerRadius * 1.8f, centerX, centerY + centerRadius * 1.8f, centerPaint)

        val label = "ЦЕНТР — НАВЕДИТЕ НА ПРЕДМЕТ"
        val labelWidth = labelPaint.measureText(label)
        canvas.drawText(label, (width - labelWidth) * 0.5f, top - 10f * resources.displayMetrics.density, labelPaint)
    }
}
