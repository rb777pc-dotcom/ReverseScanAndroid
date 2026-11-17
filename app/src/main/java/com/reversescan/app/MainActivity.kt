package com.reversescan.app

import android.Manifest
import android.app.Activity
import android.content.pm.PackageManager
import android.graphics.Color
import android.opengl.GLES11Ext
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.os.Bundle
import android.os.Environment
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.FrameLayout
import android.widget.LinearLayout
import android.widget.TextView
import com.google.ar.core.ArCoreApk
import com.google.ar.core.Config
import com.google.ar.core.Frame
import com.google.ar.core.Session
import com.google.ar.core.TrackingState
import com.google.ar.core.Coordinates2d
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.atomic.AtomicBoolean
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import android.opengl.GLSurfaceView.Renderer
import kotlin.math.max

class MainActivity : Activity() {
    private var arSession: Session? = null
    private lateinit var glView: GLSurfaceView
    private lateinit var renderer: ScanRenderer
    private lateinit var status: TextView
    private lateinit var captureButton: Button
    private lateinit var finishButton: Button
    private var activityResumed = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        refreshDeviceStatus()
    }

    private fun buildUi() {
        val root = FrameLayout(this)
        glView = GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            preserveEGLContextOnPause = true
        }
        renderer = ScanRenderer(this) { message -> runOnUiThread { status.text = message } }
        glView.setRenderer(renderer)
        glView.renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
        root.addView(glView, FrameLayout.LayoutParams(-1, -1))

        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(18, 18, 18, 18)
            setBackgroundColor(0xDD101820.toInt())
        }
        val title = TextView(this).apply {
            text = "ReverseScan · CAPTURE"
            textSize = 20f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }
        status = TextView(this).apply {
            text = "Проверка ARCore…"
            textSize = 13f
            setTextColor(Color.WHITE)
            setPadding(4, 10, 4, 10)
        }
        captureButton = Button(this).apply {
            text = "Добавить ракурс"
            isEnabled = false
            setOnClickListener { renderer.requestCapture() }
        }
        finishButton = Button(this).apply {
            text = "Завершить и сохранить PLY"
            isEnabled = false
            setOnClickListener { renderer.requestExport() }
        }
        panel.addView(title)
        panel.addView(status)
        panel.addView(captureButton)
        panel.addView(finishButton)
        val panelParams = FrameLayout.LayoutParams(-1, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM)
        root.addView(panel, panelParams)
        setContentView(root)
    }

    private fun refreshDeviceStatus() {
        val availability = try { ArCoreApk.getInstance().checkAvailability(this) } catch (_: Exception) { null }
        status.text = when {
            availability == null -> "Не удалось проверить ARCore. Установите Google Play Services for AR."
            availability.isSupported -> "ARCore поддерживается. Нажмите «Добавить ракурс» после запуска камеры."
            availability.isTransient -> "ARCore проверяет совместимость. Повторите запуск позже."
            else -> "ARCore недоступен. Проверьте поддержку и установите Google Play Services for AR."
        }
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.CAMERA), 100)
        } else if (availability?.isSupported == true) startArSession()
    }

    private fun startArSession() {
        try {
            val install = ArCoreApk.getInstance().requestInstall(this, true)
            if (install == ArCoreApk.InstallStatus.INSTALL_REQUESTED) {
                status.text = "Установите/обновите Google Play Services for AR и откройте приложение снова."
                return
            }
            arSession?.close()
            val session = Session(this)
            val config = session.config
            if (!session.isDepthModeSupported(Config.DepthMode.AUTOMATIC)) {
                session.close()
                status.text = "Depth API не поддерживается текущей конфигурацией устройства."
                return
            }
            config.depthMode = Config.DepthMode.AUTOMATIC
            session.configure(config)
            arSession = session
            renderer.setSession(session)
            if (activityResumed) session.resume()
            captureButton.isEnabled = true
            finishButton.isEnabled = true
            status.text = "Камера запускается. Медленно обойдите объект; добавляйте ракурсы с разных сторон."
        } catch (e: Exception) {
            status.text = "Ошибка запуска ARCore: ${e.localizedMessage ?: e.javaClass.simpleName}"
        }
    }

    override fun onResume() {
        super.onResume()
        activityResumed = true
        if (::glView.isInitialized) glView.onResume()
        try { arSession?.resume() } catch (e: Exception) { status.text = "Не удалось возобновить ARCore: ${e.localizedMessage}" }
    }

    override fun onPause() {
        activityResumed = false
        if (::glView.isInitialized) glView.onPause()
        try { arSession?.pause() } catch (_: Exception) { }
        super.onPause()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 100 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) startArSession()
        else status.text = "Для сканирования необходимо разрешить доступ к камере."
    }

    override fun onDestroy() {
        renderer.setSession(null)
        arSession?.close()
        arSession = null
        super.onDestroy()
    }
}

private class ScanRenderer(private val activity: Activity, private val report: (String) -> Unit) : Renderer {
    @Volatile private var session: Session? = null
    private val captureRequested = AtomicBoolean(false)
    private val exportRequested = AtomicBoolean(false)
    private val points = ArrayList<FloatArray>()
    private var textureId = -1
    private var program = 0
    private var positionHandle = 0
    private var texCoordHandle = 0
    private var textureHandle = 0
    private var cameraTextureBound = false
    private val vertices = floatArrayOf(-1f,-1f, 1f,-1f, -1f,1f, 1f,1f)
    private val texCoords = FloatArray(8)
    private lateinit var vertexBuffer: FloatBuffer
    private lateinit var texBuffer: FloatBuffer
    private var frameCount = 0

    fun setSession(value: Session?) { session = value; cameraTextureBound = false }
    fun requestCapture() { captureRequested.set(true) }
    fun requestExport() { exportRequested.set(true) }

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(0f, 0f, 0f, 1f)
        textureId = createExternalTexture()
        vertexBuffer = ByteBuffer.allocateDirect(vertices.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer().put(vertices).apply { position(0) }
        texBuffer = ByteBuffer.allocateDirect(texCoords.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer()
        program = createProgram(VERTEX_SHADER, FRAGMENT_SHADER)
        positionHandle = GLES20.glGetAttribLocation(program, "aPosition")
        texCoordHandle = GLES20.glGetAttribLocation(program, "aTexCoord")
        textureHandle = GLES20.glGetUniformLocation(program, "sTexture")
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) { GLES20.glViewport(0, 0, width, height) }

    override fun onDrawFrame(gl: GL10?) {
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
        val active = session ?: return
        try {
            if (!cameraTextureBound) {
                active.setCameraTextureNames(intArrayOf(textureId))
                cameraTextureBound = true
            }
            val frame = active.update()
            drawCamera(frame)
            if (frame.camera.trackingState != TrackingState.TRACKING) {
                report("Поиск трекинга… Держите телефон в движении и избегайте однотонных поверхностей.")
                return
            }
            frameCount++
            if (captureRequested.compareAndSet(true, false)) captureDepth(frame)
            if (exportRequested.compareAndSet(true, false)) exportPly()
        } catch (e: Exception) {
            report("Ошибка кадра ARCore: ${e.localizedMessage ?: e.javaClass.simpleName}")
            cameraTextureBound = false
        }
    }

    private fun drawCamera(frame: Frame) {
        val input = vertices
        val transformed = FloatArray(8)
        frame.transformCoordinates2d(Coordinates2d.OPENGL_NORMALIZED_DEVICE_COORDINATES, input, Coordinates2d.TEXTURE_NORMALIZED, transformed)
        texBuffer.clear(); texBuffer.put(transformed); texBuffer.position(0)
        GLES20.glUseProgram(program)
        GLES20.glEnableVertexAttribArray(positionHandle)
        GLES20.glVertexAttribPointer(positionHandle, 2, GLES20.GL_FLOAT, false, 0, vertexBuffer)
        GLES20.glEnableVertexAttribArray(texCoordHandle)
        GLES20.glVertexAttribPointer(texCoordHandle, 2, GLES20.GL_FLOAT, false, 0, texBuffer)
        GLES20.glActiveTexture(GLES20.GL_TEXTURE0)
        GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, textureId)
        GLES20.glUniform1i(textureHandle, 0)
        GLES20.glDrawArrays(GLES20.GL_TRIANGLE_STRIP, 0, 4)
        GLES20.glDisableVertexAttribArray(positionHandle)
        GLES20.glDisableVertexAttribArray(texCoordHandle)
    }

    private fun captureDepth(frame: Frame) {
        var depthImage: android.media.Image? = null
        var confidenceImage: android.media.Image? = null
        try {
            depthImage = frame.acquireRawDepthImage16Bits()
            confidenceImage = frame.acquireRawDepthConfidenceImage()
            val depthPlane = depthImage.planes[0]
            val confidencePlane = confidenceImage.planes[0]
            val depth = depthPlane.buffer.order(ByteOrder.LITTLE_ENDIAN)
            val confidence = confidencePlane.buffer
            val width = depthImage.width
            val height = depthImage.height
            val depthRowStride = depthPlane.rowStride
            val depthPixelStride = depthPlane.pixelStride
            val confRowStride = confidencePlane.rowStride
            val confPixelStride = confidencePlane.pixelStride
            val intrinsics = frame.camera.imageIntrinsics
            val focal = FloatArray(2); val principal = FloatArray(2); val imageSize = IntArray(2)
            intrinsics.getFocalLength(focal, 0)
            intrinsics.getPrincipalPoint(principal, 0)
            intrinsics.getImageDimensions(imageSize, 0)
            val sx = width.toFloat() / max(1, imageSize[0])
            val sy = height.toFloat() / max(1, imageSize[1])
            val fx = focal[0] * sx; val fy = focal[1] * sy
            val cx = principal[0] * sx; val cy = principal[1] * sy
            val pose = frame.camera.pose
            var accepted = 0
            val step = 3
            for (v in 0 until height step step) {
                for (u in 0 until width step step) {
                    val dOffset = v * depthRowStride + u * depthPixelStride
                    if (dOffset + 1 >= depth.limit()) continue
                    val packed = depth.getShort(dOffset).toInt() and 0xFFFF
                    val millimetres = packed and 0x1FFF
                    if (millimetres <= 0) continue
                    val cOffset = v * confRowStride + u * confPixelStride
                    if (cOffset >= confidence.limit()) continue
                    val conf = confidence.get(cOffset).toInt() and 0xFF
                    if (conf < 160) continue
                    val z = millimetres / 1000f
                    val x = (u - cx) * z / fx
                    val y = (v - cy) * z / fy
                    val world = pose.transformPoint(floatArrayOf(x, -y, -z))
                    points.add(floatArrayOf(world[0], world[1], world[2]))
                    accepted++
                }
            }
            report("Ракурс добавлен: +$accepted точек. Всего: ${points.size}. Продолжайте обход объекта.")
        } catch (e: Exception) {
            report("Не удалось получить Raw Depth: ${e.localizedMessage ?: "проверьте освещение и расстояние"}")
        } finally {
            depthImage?.close(); confidenceImage?.close()
        }
    }

    private fun exportPly() {
        if (points.isEmpty()) { report("Нет данных. Сначала добавьте хотя бы один ракурс."); return }
        try {
            val dir = File(getAppExportDirectory(), "ReverseScan")
            if (!dir.exists()) dir.mkdirs()
            val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
            val file = File(dir, "scan_$stamp.ply")
            FileOutputStream(file).bufferedWriter().use { out ->
                out.append("ply\nformat ascii 1.0\nelement vertex ${points.size}\n")
                out.append("property float x\nproperty float y\nproperty float z\nend_header\n")
                points.forEach { p -> out.append("${p[0]} ${p[1]} ${p[2]}\n") }
            }
            report("Сохранено ${points.size} точек: ${file.absolutePath}. Это облако точек, не готовая STL-сетка.")
        } catch (e: Exception) {
            report("Ошибка сохранения PLY: ${e.localizedMessage}")
        }
    }

    private fun getAppExportDirectory(): File = activity.getExternalFilesDir(null) ?: activity.filesDir

    private fun createExternalTexture(): Int {
        val textures = IntArray(1)
        GLES20.glGenTextures(1, textures, 0)
        GLES20.glBindTexture(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, textures[0])
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MIN_FILTER, GLES20.GL_LINEAR)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_MAG_FILTER, GLES20.GL_LINEAR)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_WRAP_S, GLES20.GL_CLAMP_TO_EDGE)
        GLES20.glTexParameteri(GLES11Ext.GL_TEXTURE_EXTERNAL_OES, GLES20.GL_TEXTURE_WRAP_T, GLES20.GL_CLAMP_TO_EDGE)
        return textures[0]
    }

    private fun createProgram(vertex: String, fragment: String): Int {
        val vs = compileShader(GLES20.GL_VERTEX_SHADER, vertex)
        val fs = compileShader(GLES20.GL_FRAGMENT_SHADER, fragment)
        return GLES20.glCreateProgram().also { p ->
            GLES20.glAttachShader(p, vs); GLES20.glAttachShader(p, fs); GLES20.glLinkProgram(p)
            val status = IntArray(1); GLES20.glGetProgramiv(p, GLES20.GL_LINK_STATUS, status, 0)
            if (status[0] == 0) throw RuntimeException("OpenGL link error: ${GLES20.glGetProgramInfoLog(p)}")
        }
    }

    private fun compileShader(type: Int, source: String): Int = GLES20.glCreateShader(type).also { shader ->
        GLES20.glShaderSource(shader, source); GLES20.glCompileShader(shader)
        val status = IntArray(1); GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, status, 0)
        if (status[0] == 0) throw RuntimeException("OpenGL shader error: ${GLES20.glGetShaderInfoLog(shader)}")
    }

    companion object {
        private const val VERTEX_SHADER = "attribute vec4 aPosition; attribute vec2 aTexCoord; varying vec2 vTexCoord; void main(){ gl_Position=aPosition; vTexCoord=aTexCoord; }"
        private const val FRAGMENT_SHADER = "#extension GL_OES_EGL_image_external : require\nprecision mediump float; uniform samplerExternalOES sTexture; varying vec2 vTexCoord; void main(){ gl_FragColor=texture2D(sTexture,vTexCoord); }"
    }
}
