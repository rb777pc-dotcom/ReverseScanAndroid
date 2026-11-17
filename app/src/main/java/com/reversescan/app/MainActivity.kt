package com.reversescan.app

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.net.Uri
import android.opengl.GLES11Ext
import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
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
import java.io.OutputStreamWriter
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.text.SimpleDateFormat
import java.util.Date
import java.util.LinkedHashMap
import java.util.Locale
import java.util.concurrent.atomic.AtomicBoolean
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10
import android.opengl.GLSurfaceView.Renderer
import kotlin.math.max
import kotlin.math.roundToInt

class MainActivity : Activity() {
    private var arSession: Session? = null
    private lateinit var glView: GLSurfaceView
    private lateinit var renderer: ScanRenderer
    private lateinit var status: TextView
    private lateinit var scanButton: Button
    private lateinit var captureButton: Button
    private lateinit var saveButton: Button
    private lateinit var meshButton: Button
    private lateinit var previewButton: Button
    private lateinit var torchButton: Button
    private var flashAvailable = false
    private var torchEnabled = false
    private var activityResumed = false
    private var installRequested = false
    private var scanning = false
    private var pendingExportPoints: List<FloatArray>? = null
    private var pendingMesh: MeshModel? = null
    private var pendingMeshFormat: String = "obj"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildUi()
        refreshDeviceStatus()
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).roundToInt()

    private fun buildUi() {
        val root = FrameLayout(this).apply { setPadding(0, dp(24), 0, dp(24)) }
        glView = GLSurfaceView(this).apply {
            setEGLContextClientVersion(2)
            setEGLConfigChooser(8, 8, 8, 8, 16, 0)
            preserveEGLContextOnPause = true
        }
        renderer = ScanRenderer(
            this,
            { message -> runOnUiThread { if (::status.isInitialized) status.text = message } },
            { snapshot ->
                runOnUiThread {
                    pendingExportPoints = snapshot
                    launchCreateDocument()
                }
            },
            { mesh ->
                runOnUiThread { showMeshPreview(mesh) }
            },
            { enabled, message ->
                runOnUiThread {
                    torchEnabled = enabled
                    if (::torchButton.isInitialized) torchButton.text = if (enabled) "Фонарик: вкл" else if (flashAvailable) "Фонарик: выкл" else "Фонарик недоступен"
                    if (message.isNotBlank() && ::status.isInitialized) status.text = message
                }
            },
            { snapshot -> runOnUiThread { showPointCloudPreview(snapshot) } }
        )
        glView.setRenderer(renderer)
        glView.renderMode = GLSurfaceView.RENDERMODE_CONTINUOUSLY
        root.addView(glView, FrameLayout.LayoutParams(-1, -1))

        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), dp(10), dp(12), dp(10))
            setBackgroundColor(0xE91A2230.toInt())
        }
        val title = TextView(this).apply {
            text = "ReverseScan · 3D SCAN"
            textSize = 18f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
        }
        status = TextView(this).apply {
            text = "Проверка ARCore…"
            textSize = 13f
            setTextColor(Color.WHITE)
            setPadding(dp(4), dp(8), dp(4), dp(8))
            maxLines = 4
        }
        val hint = TextView(this).apply {
            text = "Держите объект в кадре и медленно обходите его на расстоянии примерно 0,5–2 м. Для полного охвата снимайте со всех сторон."
            textSize = 12f
            setTextColor(0xFFD5DFEA.toInt())
            setPadding(dp(4), 0, dp(4), dp(6))
            maxLines = 3
        }

        val firstRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        scanButton = Button(this).apply {
            text = "Начать скан"
            isEnabled = false
            setOnClickListener {
                scanning = !scanning
                renderer.setScanning(scanning)
                text = if (scanning) "Пауза" else "Продолжить"
                status.text = if (scanning) {
                    "Идёт сканирование. Двигайтесь плавно, не вращайте телефон резко."
                } else {
                    "Сканирование приостановлено. Можно добавить ракурс или сохранить результат."
                }
            }
        }
        captureButton = Button(this).apply {
            text = "Добавить ракурс"
            isEnabled = false
            setOnClickListener { renderer.requestCapture() }
        }
        saveButton = Button(this).apply {
            text = "Сохранить PLY"
            isEnabled = false
            setOnClickListener {
                scanning = false
                renderer.setScanning(false)
                scanButton.text = "Начать скан"
                renderer.requestExport()
            }
        }
        firstRow.addView(scanButton, LinearLayout.LayoutParams(0, dp(48), 1f).apply { marginEnd = dp(3) })
        firstRow.addView(captureButton, LinearLayout.LayoutParams(0, dp(48), 1f).apply { marginStart = dp(3); marginEnd = dp(3) })
        firstRow.addView(saveButton, LinearLayout.LayoutParams(0, dp(48), 1f).apply { marginStart = dp(3) })

        meshButton = Button(this).apply {
            text = "Построить 3D-модель"
            isEnabled = false
            setOnClickListener {
                scanning = false
                renderer.setScanning(false)
                scanButton.text = "Начать скан"
                renderer.requestMesh()
            }
        }

        val resetButton = Button(this).apply {
            text = "Новый скан — очистить данные"
            isEnabled = true
            setOnClickListener {
                AlertDialog.Builder(this@MainActivity)
                    .setTitle("Начать новый скан?")
                    .setMessage("Текущие несохранённые точки будут удалены.")
                    .setNegativeButton("Отмена", null)
                    .setPositiveButton("Очистить") { _, _ ->
                        scanning = false
                        renderer.setScanning(false)
                        scanButton.text = "Начать скан"
                        pendingMesh = null
                        pendingExportPoints = null
                        renderer.requestReset()
                    }
                    .show()
            }
        }

        val header = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        header.addView(title, LinearLayout.LayoutParams(0, dp(44), 1f))
        torchButton = Button(this).apply {
            text = "Фонарик: выкл"
            isEnabled = false
            setOnClickListener { if (flashAvailable) renderer.requestFlashToggle() }
        }
        header.addView(torchButton, LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, dp(44)))
        panel.addView(header)
        panel.addView(status)
        panel.addView(hint)
        panel.addView(firstRow)
        previewButton = Button(this).apply {
            text = "Просмотр скана"
            isEnabled = false
            setOnClickListener {
                scanning = false
                renderer.setScanning(false)
                scanButton.text = "Продолжить"
                renderer.requestPointCloudPreview()
            }
        }
        meshButton.text = "Построить 3D"
        val inspectRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER
        }
        inspectRow.addView(previewButton, LinearLayout.LayoutParams(0, dp(46), 1f).apply { marginEnd = dp(3) })
        inspectRow.addView(meshButton, LinearLayout.LayoutParams(0, dp(46), 1f).apply { marginStart = dp(3) })
        panel.addView(inspectRow, LinearLayout.LayoutParams(-1, dp(46)).apply { topMargin = dp(4) })
        panel.addView(resetButton, LinearLayout.LayoutParams(-1, dp(46)).apply { topMargin = dp(4) })

        val panelParams = FrameLayout.LayoutParams(-1, FrameLayout.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM).apply {
            leftMargin = dp(8)
            rightMargin = dp(8)
            bottomMargin = dp(8)
        }
        root.addView(panel, panelParams)
        val legend = TextView(this).apply {
            text = "ЗЕЛЁНЫЕ точки — уже записано   •   ЖЁЛТЫЕ — глубина сейчас   •   без точек — ещё не захвачено"
            textSize = 11f
            setTextColor(Color.WHITE)
            setBackgroundColor(0xB91A2230.toInt())
            setPadding(dp(10), dp(8), dp(10), dp(8))
            gravity = Gravity.CENTER
        }
        root.addView(legend, FrameLayout.LayoutParams(-1, ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.TOP).apply {
            leftMargin = dp(8); rightMargin = dp(8); topMargin = dp(6)
        })
        setContentView(root)
    }

    private fun refreshDeviceStatus() {
        val availability = try { ArCoreApk.getInstance().checkAvailability(this) } catch (_: Exception) { null }
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            status.text = "Нужно разрешить доступ к камере."
            requestPermissions(arrayOf(Manifest.permission.CAMERA), 100)
            return
        }
        when {
            availability == null -> status.text = "Не удалось проверить ARCore. Установите Google Play Services for AR."
            availability.isSupported -> startArSession()
            availability.isTransient -> status.text = "ARCore проверяет совместимость. Подождите и откройте приложение снова."
            else -> status.text = "Это устройство или текущая конфигурация не поддерживает ARCore."
        }
    }

    private fun startArSession() {
        if (checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.CAMERA), 100)
            return
        }
        try {
            val install = ArCoreApk.getInstance().requestInstall(this, true)
            if (install == ArCoreApk.InstallStatus.INSTALL_REQUESTED) {
                installRequested = true
                status.text = "Устанавливается Google Play Services for AR. После установки приложение продолжит запуск."
                return
            }
            installRequested = false
            arSession?.close()
            val session = Session(this)
            val config = session.config
            if (!session.isDepthModeSupported(Config.DepthMode.AUTOMATIC)) {
                session.close()
                status.text = "На этом устройстве ARCore Depth API недоступен. Сканирование невозможно."
                return
            }
            config.depthMode = Config.DepthMode.AUTOMATIC
            config.focusMode = Config.FocusMode.AUTO
            config.flashMode = Config.FlashMode.OFF
            session.configure(config)
            arSession = session
            flashAvailable = try {
                val manager = getSystemService(CAMERA_SERVICE) as CameraManager
                manager.getCameraCharacteristics(session.cameraConfig.cameraId).get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
            } catch (_: Exception) { false }
            torchEnabled = false
            if (::torchButton.isInitialized) {
                torchButton.isEnabled = flashAvailable
                torchButton.text = if (flashAvailable) "Фонарик: выкл" else "Фонарик недоступен"
            }
            renderer.setSession(session)
            if (activityResumed) session.resume()
            scanButton.isEnabled = true
            captureButton.isEnabled = true
            saveButton.isEnabled = true
            meshButton.isEnabled = true
            previewButton.isEnabled = true
            status.text = "Камера готова. Запрошен автофокус. Нажмите «Начать скан» или добавляйте ракурсы вручную."
        } catch (e: Exception) {
            arSession?.close()
            arSession = null
            status.text = "Ошибка запуска ARCore: ${e.localizedMessage ?: e.javaClass.simpleName}"
        }
    }

    private fun launchCreateDocument() {
        val points = pendingExportPoints
        if (points.isNullOrEmpty()) {
            status.text = "Нет точек для сохранения. Сначала выполните сканирование."
            return
        }
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "application/octet-stream"
            putExtra(Intent.EXTRA_TITLE, "ReverseScan_$stamp.ply")
        }
        try {
            startActivityForResult(intent, CREATE_PLY_REQUEST)
        } catch (e: Exception) {
            pendingExportPoints = null
            status.text = "Не удалось открыть выбор места сохранения: ${e.localizedMessage}"
        }
    }

    private fun showMeshPreview(mesh: MeshModel) {
        if (mesh.isEmpty) {
            status.text = "Сетка не получилась: мало перекрывающихся данных глубины. Просканируйте объект с большим числом ракурсов."
            return
        }
        pendingMesh = mesh
        status.text = "3D-сетка построена: ${mesh.triangleCount} треугольников. Можно вращать модель пальцем и экспортировать OBJ или STL."
        val preview = MeshPreviewView(this, mesh).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                (resources.displayMetrics.heightPixels * 0.55f).toInt()
            )
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle("3D-модель · ${mesh.triangleCount} треугольников")
            .setView(preview)
            .setPositiveButton("Экспорт OBJ") { _, _ -> launchCreateMeshDocument("obj") }
            .setNeutralButton("Экспорт STL") { _, _ -> launchCreateMeshDocument("stl") }
            .setNegativeButton("Закрыть", null)
            .create()
        dialog.show()
        dialog.window?.setLayout((resources.displayMetrics.widthPixels * 0.94f).toInt(),
            (resources.displayMetrics.heightPixels * 0.72f).toInt())
    }

    private fun showPointCloudPreview(points: List<FloatArray>) {
        if (points.isEmpty()) {
            status.text = "Пока нет захваченных точек. Начните сканирование или добавьте ракурс."
            return
        }
        val preview = PointCloudPreviewView(this, points).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                (resources.displayMetrics.heightPixels * 0.58f).toInt()
            )
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle("Накопленный скан · ${points.size} точек")
            .setView(preview)
            .setPositiveButton("Продолжить сканирование") { _, _ ->
                scanning = true
                renderer.setScanning(true)
                scanButton.text = "Пауза"
            }
            .setNegativeButton("Закрыть", null)
            .create()
        dialog.show()
        dialog.window?.setLayout((resources.displayMetrics.widthPixels * 0.94f).toInt(),
            (resources.displayMetrics.heightPixels * 0.74f).toInt())
    }

    private fun launchCreateMeshDocument(format: String) {
        val mesh = pendingMesh
        if (mesh == null || mesh.isEmpty) {
            status.text = "Нет готовой 3D-сетки для экспорта."
            return
        }
        pendingMeshFormat = format
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val mime = "*/*"
        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = mime
            putExtra(Intent.EXTRA_TITLE, "ReverseScan_$stamp.$format")
        }
        try {
            startActivityForResult(intent, CREATE_MESH_REQUEST)
        } catch (e: Exception) {
            status.text = "Не удалось открыть выбор места сохранения модели: ${e.localizedMessage}"
        }
    }

    @Deprecated("Using the system document picker for broad Android compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == CREATE_MESH_REQUEST) {
            val uri = if (resultCode == RESULT_OK) data?.data else null
            val mesh = pendingMesh
            if (uri == null || mesh == null) {
                status.text = "Экспорт 3D-модели отменён."
                return
            }
            val format = pendingMeshFormat
            status.text = "Сохраняю ${mesh.triangleCount} треугольников в ${format.uppercase(Locale.ROOT)}…"
            Thread({
                try {
                    val output = contentResolver.openOutputStream(uri)
                        ?: throw IllegalStateException("Не удалось открыть выбранный файл")
                    if (format == "stl") MeshFileWriter.writeStl(mesh, output)
                    else MeshFileWriter.writeObj(mesh, output)
                    runOnUiThread { status.text = "3D-модель сохранена. Её можно открыть в Blender, MeshLab или CAD-программе." }
                } catch (e: Exception) {
                    runOnUiThread { status.text = "Ошибка экспорта модели: ${e.localizedMessage ?: e.javaClass.simpleName}" }
                }
            }, "ReverseScan-MeshExport").start()
            return
        }
        if (requestCode != CREATE_PLY_REQUEST) return
        val uri: Uri? = if (resultCode == RESULT_OK) data?.data else null
        val points = pendingExportPoints
        pendingExportPoints = null
        if (uri == null || points.isNullOrEmpty()) {
            status.text = "Сохранение отменено."
            return
        }
        status.text = "Сохраняю ${points.size} точек в PLY…"
        Thread({
            try {
                val output = contentResolver.openOutputStream(uri)
                    ?: throw IllegalStateException("Не удалось открыть выбранный файл")
                OutputStreamWriter(output, Charsets.UTF_8).buffered().use { writer ->
                    writer.append("ply\n")
                    writer.append("format ascii 1.0\n")
                    writer.append("comment Generated by ReverseScan; coordinates in metres\n")
                    writer.append("element vertex ${points.size}\n")
                    writer.append("property float x\nproperty float y\nproperty float z\n")
                    writer.append("end_header\n")
                    points.forEach { p ->
                        writer.append(p[0].toString()).append(' ')
                            .append(p[1].toString()).append(' ')
                            .append(p[2].toString()).append('\n')
                    }
                }
                runOnUiThread {
                    status.text = "Файл PLY сохранён: ${points.size} точек. Его можно открыть в MeshLab или Blender. Это облако точек, не готовая полигональная сетка."
                }
            } catch (e: Exception) {
                runOnUiThread {
                    status.text = "Ошибка записи PLY: ${e.localizedMessage ?: e.javaClass.simpleName}"
                }
            }
        }, "ReverseScan-PlyExport").start()
    }

    override fun onResume() {
        super.onResume()
        activityResumed = true
        if (::glView.isInitialized) glView.onResume()
        if (installRequested) {
            startArSession()
        } else {
            try { arSession?.resume() } catch (e: Exception) {
                status.text = "Не удалось возобновить ARCore: ${e.localizedMessage}"
            }
        }
    }

    override fun onPause() {
        activityResumed = false
        if (::glView.isInitialized) glView.onPause()
        try { arSession?.pause() } catch (_: Exception) { }
        super.onPause()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 100 && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            startArSession()
        } else if (requestCode == 100) {
            status.text = "Без разрешения на камеру сканирование невозможно."
        }
    }

    override fun onDestroy() {
        if (::renderer.isInitialized) renderer.setSession(null)
        arSession?.close()
        arSession = null
        super.onDestroy()
    }

    companion object {
        private const val CREATE_PLY_REQUEST = 501
        private const val CREATE_MESH_REQUEST = 502
    }
}

private class ScanRenderer(
    private val activity: Activity,
    private val report: (String) -> Unit,
    private val exportReady: (List<FloatArray>) -> Unit,
    private val meshReady: (MeshModel) -> Unit,
    private val flashChanged: (Boolean, String) -> Unit,
    private val cloudReady: (List<FloatArray>) -> Unit
) : Renderer {
    @Volatile private var session: Session? = null
    private val captureRequested = AtomicBoolean(false)
    private val exportRequested = AtomicBoolean(false)
    private val meshRequested = AtomicBoolean(false)
    private val meshBuilding = AtomicBoolean(false)
    private val resetRequested = AtomicBoolean(false)
    private val flashToggleRequested = AtomicBoolean(false)
    private val cloudPreviewRequested = AtomicBoolean(false)
    private var flashEnabled = false
    private val scanning = AtomicBoolean(false)
    private val points = LinkedHashMap<Long, FloatArray>()
    private val tsdf = TsdfVolume()
    private var viewsCaptured = 0
    private var textureId = -1
    private var program = 0
    private var positionHandle = 0
    private var texCoordHandle = 0
    private var textureHandle = 0
    private var pointProgram = 0
    private var pointPositionHandle = 0
    private var pointMvpHandle = 0
    private var pointColorHandle = 0
    private var pointSizeHandle = 0
    private var pointBuffer: FloatBuffer? = null
    private var pointVertexCount = 0
    private var cloudDirty = true
    private var latestDepthBuffer: FloatBuffer? = null
    private var latestDepthCount = 0
    private val viewMatrix = FloatArray(16)
    private val projectionMatrix = FloatArray(16)
    private val mvpMatrix = FloatArray(16)
    private var cameraTextureBound = false
    private val vertices = floatArrayOf(-1f, -1f, 1f, -1f, -1f, 1f, 1f, 1f)
    private val texCoords = FloatArray(8)
    private lateinit var vertexBuffer: FloatBuffer
    private lateinit var texBuffer: FloatBuffer
    private var surfaceWidth = 0
    private var surfaceHeight = 0
    private var lastDisplayRotation = -1
    private var lastSurfaceWidth = -1
    private var lastSurfaceHeight = -1
    private var lastAutoCaptureNs = 0L
    private var lastTrackingMessageNs = 0L

    fun setSession(value: Session?) {
        session = value
        cameraTextureBound = false
        lastDisplayRotation = -1
        lastSurfaceWidth = -1
        lastSurfaceHeight = -1
    }

    fun setScanning(value: Boolean) { scanning.set(value) }
    fun requestCapture() { captureRequested.set(true) }
    fun requestExport() { exportRequested.set(true) }
    fun requestMesh() {
        if (meshBuilding.compareAndSet(false, true)) meshRequested.set(true)
    }
    fun requestReset() { resetRequested.set(true) }
    fun requestFlashToggle() { flashToggleRequested.set(true) }
    fun requestPointCloudPreview() { cloudPreviewRequested.set(true) }

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        cameraTextureBound = false
        GLES20.glClearColor(0f, 0f, 0f, 1f)
        textureId = createExternalTexture()
        vertexBuffer = ByteBuffer.allocateDirect(vertices.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer().put(vertices).apply { position(0) }
        texBuffer = ByteBuffer.allocateDirect(texCoords.size * 4).order(ByteOrder.nativeOrder()).asFloatBuffer()
        program = createProgram(VERTEX_SHADER, FRAGMENT_SHADER)
        positionHandle = GLES20.glGetAttribLocation(program, "aPosition")
        texCoordHandle = GLES20.glGetAttribLocation(program, "aTexCoord")
        textureHandle = GLES20.glGetUniformLocation(program, "sTexture")
        pointProgram = createProgram(POINT_VERTEX_SHADER, POINT_FRAGMENT_SHADER)
        pointPositionHandle = GLES20.glGetAttribLocation(pointProgram, "aPosition")
        pointMvpHandle = GLES20.glGetUniformLocation(pointProgram, "uMvp")
        pointColorHandle = GLES20.glGetUniformLocation(pointProgram, "uColor")
        pointSizeHandle = GLES20.glGetUniformLocation(pointProgram, "uPointSize")
    }

    override fun onSurfaceChanged(gl: GL10?, width: Int, height: Int) {
        surfaceWidth = width
        surfaceHeight = height
        GLES20.glViewport(0, 0, width, height)
        lastSurfaceWidth = -1
        lastSurfaceHeight = -1
    }

    override fun onDrawFrame(gl: GL10?) {
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT or GLES20.GL_DEPTH_BUFFER_BIT)
        val active = session ?: return
        try {
            if (!cameraTextureBound) {
                active.setCameraTextureNames(intArrayOf(textureId))
                cameraTextureBound = true
            }
            val rotation = activity.windowManager.defaultDisplay.rotation
            if (surfaceWidth > 0 && surfaceHeight > 0 &&
                (rotation != lastDisplayRotation ||
                    surfaceWidth != lastSurfaceWidth ||
                    surfaceHeight != lastSurfaceHeight)) {
                active.setDisplayGeometry(rotation, surfaceWidth, surfaceHeight)
                lastDisplayRotation = rotation
                lastSurfaceWidth = surfaceWidth
                lastSurfaceHeight = surfaceHeight
            }

            if (flashToggleRequested.compareAndSet(true, false)) {
                try {
                    val next = !flashEnabled
                    val config = active.config
                    config.flashMode = if (next) Config.FlashMode.TORCH else Config.FlashMode.OFF
                    active.configure(config)
                    flashEnabled = next
                    flashChanged(next, if (next) "Фонарик включён." else "Фонарик выключен.")
                } catch (e: Exception) {
                    flashChanged(flashEnabled, "Не удалось переключить фонарик: " + (e.localizedMessage ?: e.javaClass.simpleName))
                }
            }
            val frame = active.update()
            if (frame.timestamp == 0L) return
            drawCamera(frame)
            drawPointOverlay(frame)

            if (resetRequested.compareAndSet(true, false)) {
                points.clear()
                tsdf.clear()
                viewsCaptured = 0
                cloudDirty = true
                pointBuffer = null
                pointVertexCount = 0
                latestDepthBuffer = null
                latestDepthCount = 0
                captureRequested.set(false)
                exportRequested.set(false)
                meshRequested.set(false)
                meshBuilding.set(false)
                report("Новый скан готов. Облако и объём глубины очищены.")
            }

            if (cloudPreviewRequested.compareAndSet(true, false)) {
                if (points.isEmpty()) report("Пока нет накопленных точек для просмотра.")
                else cloudReady(points.values.map { it.copyOf() })
            }

            if (exportRequested.compareAndSet(true, false)) {
                scanning.set(false)
                if (points.isEmpty()) {
                    report("Нет точек для сохранения. Сначала добавьте ракурс или запустите сканирование.")
                } else {
                    report("Подготовка PLY: ${points.size} точек…")
                    exportReady(points.values.toList())
                }
            }

            if (meshRequested.compareAndSet(true, false)) {
                scanning.set(false)
                val volumeSnapshot = tsdf.snapshot()
                if (volumeSnapshot.size < 8) {
                    meshBuilding.set(false)
                    report("Недостаточно данных для 3D-сетки. Сначала просканируйте объект с нескольких сторон.")
                } else {
                    report("Строю поверхность из ${volumeSnapshot.size} объёмных ячеек. Это может занять время…")
                    Thread({
                        try {
                            val model = MeshReconstructor.reconstruct(volumeSnapshot, tsdf.voxelSize)
                            meshBuilding.set(false)
                            activity.runOnUiThread {
                                if (model.isEmpty) {
                                    report("Поверхность не сформировалась. Нужны перекрывающиеся ракурсы, больше данных и ровное движение.")
                                } else {
                                    report("3D-сетка готова: ${model.triangleCount} треугольников.")
                                    meshReady(model)
                                }
                            }
                        } catch (e: Exception) {
                            meshBuilding.set(false)
                            activity.runOnUiThread {
                                report("Ошибка построения 3D-сетки: ${e.localizedMessage ?: e.javaClass.simpleName}")
                            }
                        } catch (e: OutOfMemoryError) {
                            meshBuilding.set(false)
                            activity.runOnUiThread {
                                report("Недостаточно памяти для этой сетки. Сканируйте меньший участок и попробуйте снова.")
                            }
                        }
                    }, "ReverseScan-Reconstruction").start()
                }
            }

            if (frame.camera.trackingState != TrackingState.TRACKING) {
                val now = System.nanoTime()
                if (now - lastTrackingMessageNs > 1_000_000_000L) {
                    report("Поиск трекинга ARCore… Медленно перемещайте телефон и наведите камеру на текстурированную поверхность.")
                    lastTrackingMessageNs = now
                }
                return
            }

            if (captureRequested.compareAndSet(true, false)) {
                captureDepth(frame)
            } else if (scanning.get()) {
                val now = System.nanoTime()
                if (now - lastAutoCaptureNs >= AUTO_CAPTURE_INTERVAL_NS) {
                    lastAutoCaptureNs = now
                    captureDepth(frame)
                }
            }
        } catch (e: Exception) {
            report("Ошибка ARCore: ${e.localizedMessage ?: e.javaClass.simpleName}")
            cameraTextureBound = false
        }
    }

    private fun drawCamera(frame: Frame) {
        GLES20.glDisable(GLES20.GL_DEPTH_TEST)
        GLES20.glDepthMask(false)
        val transformed = FloatArray(8)
        frame.transformCoordinates2d(
            Coordinates2d.OPENGL_NORMALIZED_DEVICE_COORDINATES,
            vertices,
            Coordinates2d.TEXTURE_NORMALIZED,
            transformed
        )
        texBuffer.clear()
        texBuffer.put(transformed)
        texBuffer.position(0)
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
        GLES20.glDepthMask(true)
    }

    private fun drawPointOverlay(frame: Frame) {
        if (points.isEmpty() && latestDepthCount == 0) return
        try {
            frame.camera.getViewMatrix(viewMatrix, 0)
            frame.camera.getProjectionMatrix(projectionMatrix, 0, 0.1f, 100f)
            Matrix.multiplyMM(mvpMatrix, 0, projectionMatrix, 0, viewMatrix, 0)
            if (cloudDirty) rebuildPointCloudBuffer()

            GLES20.glEnable(GLES20.GL_DEPTH_TEST)
            GLES20.glDepthFunc(GLES20.GL_LEQUAL)
            GLES20.glEnable(GLES20.GL_BLEND)
            GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE_MINUS_SRC_ALPHA)
            GLES20.glUseProgram(pointProgram)
            GLES20.glUniformMatrix4fv(pointMvpHandle, 1, false, mvpMatrix, 0)

            pointBuffer?.let { buffer ->
                if (pointVertexCount > 0) {
                    GLES20.glUniform4f(pointColorHandle, 0.12f, 1f, 0.28f, 0.82f)
                    GLES20.glUniform1f(pointSizeHandle, 5.5f)
                    buffer.position(0)
                    GLES20.glEnableVertexAttribArray(pointPositionHandle)
                    GLES20.glVertexAttribPointer(pointPositionHandle, 3, GLES20.GL_FLOAT, false, 0, buffer)
                    GLES20.glDrawArrays(GLES20.GL_POINTS, 0, pointVertexCount)
                    GLES20.glDisableVertexAttribArray(pointPositionHandle)
                }
            }
            latestDepthBuffer?.let { buffer ->
                if (latestDepthCount > 0) {
                    GLES20.glUniform4f(pointColorHandle, 1f, 0.72f, 0.05f, 0.98f)
                    GLES20.glUniform1f(pointSizeHandle, 7.5f)
                    buffer.position(0)
                    GLES20.glEnableVertexAttribArray(pointPositionHandle)
                    GLES20.glVertexAttribPointer(pointPositionHandle, 3, GLES20.GL_FLOAT, false, 0, buffer)
                    GLES20.glDrawArrays(GLES20.GL_POINTS, 0, latestDepthCount)
                    GLES20.glDisableVertexAttribArray(pointPositionHandle)
                }
            }
            GLES20.glDisable(GLES20.GL_BLEND)
            GLES20.glDisable(GLES20.GL_DEPTH_TEST)
        } catch (e: Exception) {
            report("Не удалось показать карту сканирования: " + (e.localizedMessage ?: e.javaClass.simpleName))
        }
    }

    private fun rebuildPointCloudBuffer() {
        cloudDirty = false
        if (points.isEmpty()) {
            pointBuffer = null
            pointVertexCount = 0
            return
        }
        val maxDrawPoints = 120_000
        val stride = max(1, (points.size + maxDrawPoints - 1) / maxDrawPoints)
        val drawCount = (points.size + stride - 1) / stride
        val bytes = ByteBuffer.allocateDirect(drawCount * 3 * 4).order(ByteOrder.nativeOrder())
        val buffer = bytes.asFloatBuffer()
        var index = 0
        for (point in points.values) {
            if (index % stride == 0) buffer.put(point, 0, 3)
            index++
        }
        buffer.flip()
        pointBuffer = buffer
        pointVertexCount = buffer.limit() / 3
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
            val focal = FloatArray(2)
            val principal = FloatArray(2)
            val imageSize = IntArray(2)
            intrinsics.getFocalLength(focal, 0)
            intrinsics.getPrincipalPoint(principal, 0)
            intrinsics.getImageDimensions(imageSize, 0)
            if (focal[0] <= 0f || focal[1] <= 0f) {
                report("Камера ещё не передала калибровку. Повторите ракурс через секунду.")
                return
            }
            val sx = width.toFloat() / max(1, imageSize[0])
            val sy = height.toFloat() / max(1, imageSize[1])
            val fx = focal[0] * sx
            val fy = focal[1] * sy
            val cx = principal[0] * sx
            val cy = principal[1] * sy
            val pose = frame.camera.pose
            var valid = 0
            var added = 0
            val step = if (width >= 320) 3 else 2
            val currentDepthPoints = FloatArray(((width + step - 1) / step) * ((height + step - 1) / step) * 3)
            var currentDepthCount = 0

            for (v in 0 until height step step) {
                for (u in 0 until width step step) {
                    val dOffset = v * depthRowStride + u * depthPixelStride
                    if (dOffset < 0 || dOffset + 1 >= depth.limit()) continue
                    val packed = depth.getShort(dOffset).toInt() and 0xFFFF
                    val millimetres = packed and 0x1FFF
                    if (millimetres == 0) continue
                    val cOffset = v * confRowStride + u * confPixelStride
                    if (cOffset < 0 || cOffset >= confidence.limit()) continue
                    val conf = confidence.get(cOffset).toInt() and 0xFF
                    if (conf < MIN_CONFIDENCE) continue
                    val z = millimetres / 1000f
                    if (z < MIN_DEPTH_METRES || z > MAX_DEPTH_METRES) continue
                    valid++
                    val rayX = (u - cx) / fx
                    val rayY = -(v - cy) / fy
                    val x = rayX * z
                    val y = rayY * z
                    val world = pose.transformPoint(floatArrayOf(x, y, -z))
                    if (currentDepthCount * 3 + 2 < currentDepthPoints.size) {
                        val offset = currentDepthCount * 3
                        currentDepthPoints[offset] = world[0]
                        currentDepthPoints[offset + 1] = world[1]
                        currentDepthPoints[offset + 2] = world[2]
                        currentDepthCount++
                    }
                    tsdf.integratePixel(pose, rayX, rayY, z, if (conf >= 200) 3 else 1)
                    val key = voxelKey(world[0], world[1], world[2])
                    if (!points.containsKey(key) && points.size < MAX_POINTS) {
                        points[key] = floatArrayOf(world[0], world[1], world[2])
                        added++
                    }
                }
            }

            latestDepthCount = currentDepthCount
            latestDepthBuffer = if (currentDepthCount > 0) {
                ByteBuffer.allocateDirect(currentDepthCount * 3 * 4).order(ByteOrder.nativeOrder())
                    .asFloatBuffer().apply {
                        put(currentDepthPoints, 0, currentDepthCount * 3)
                        position(0)
                    }
            } else null

            if (added > 0) {
                cloudDirty = true
                viewsCaptured++
                report("Ракурс #" + viewsCaptured + ": +" + added + " новых точек · всего " + points.size + " · глубина сейчас " + currentDepthCount + " точек. Зелёное — накоплено, жёлтое — текущий кадр.")
            } else if (valid == 0) {
                report("Мало качественных данных глубины. Включите фонарик при необходимости, держите объект в кадре и проверьте освещение.")
            } else {
                report("Новых точек почти нет. Смените угол обзора и направьте камеру на ещё не просканированную сторону.")
            }

            if (points.size >= MAX_POINTS) {
                scanning.set(false)
                report("Достигнут лимит ${MAX_POINTS} точек. Сохраните результат в PLY.")
            }
        } catch (e: Exception) {
            val reason = e.localizedMessage ?: "попробуйте изменить расстояние и освещение"
            report("Не удалось получить глубину: $reason")
        } finally {
            depthImage?.close()
            confidenceImage?.close()
        }
    }

    private fun voxelKey(x: Float, y: Float, z: Float): Long {
        val mask = 0x1FFFFFL
        val qx = (x / VOXEL_SIZE_METRES).roundToInt().coerceIn(-1_048_576, 1_048_575)
        val qy = (y / VOXEL_SIZE_METRES).roundToInt().coerceIn(-1_048_576, 1_048_575)
        val qz = (z / VOXEL_SIZE_METRES).roundToInt().coerceIn(-1_048_576, 1_048_575)
        return ((qx.toLong() and mask) shl 42) or
            ((qy.toLong() and mask) shl 21) or
            (qz.toLong() and mask)
    }

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
            GLES20.glAttachShader(p, vs)
            GLES20.glAttachShader(p, fs)
            GLES20.glLinkProgram(p)
            val status = IntArray(1)
            GLES20.glGetProgramiv(p, GLES20.GL_LINK_STATUS, status, 0)
            if (status[0] == 0) throw RuntimeException("OpenGL link error: ${GLES20.glGetProgramInfoLog(p)}")
        }
    }

    private fun compileShader(type: Int, source: String): Int = GLES20.glCreateShader(type).also { shader ->
        GLES20.glShaderSource(shader, source)
        GLES20.glCompileShader(shader)
        val status = IntArray(1)
        GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, status, 0)
        if (status[0] == 0) throw RuntimeException("OpenGL shader error: ${GLES20.glGetShaderInfoLog(shader)}")
    }

    companion object {
        private const val MIN_CONFIDENCE = 128
        private const val MIN_DEPTH_METRES = 0.25f
        private const val MAX_DEPTH_METRES = 5.0f
        private const val VOXEL_SIZE_METRES = 0.008f
        private const val MAX_POINTS = 600_000
        private const val AUTO_CAPTURE_INTERVAL_NS = 350_000_000L
        private const val VERTEX_SHADER = "attribute vec4 aPosition; attribute vec2 aTexCoord; varying vec2 vTexCoord; void main(){ gl_Position=aPosition; vTexCoord=aTexCoord; }"
        private const val FRAGMENT_SHADER = "#extension GL_OES_EGL_image_external : require\nprecision mediump float; uniform samplerExternalOES sTexture; varying vec2 vTexCoord; void main(){ gl_FragColor=texture2D(sTexture, vTexCoord); }"
        private const val POINT_VERTEX_SHADER = "attribute vec4 aPosition; uniform mat4 uMvp; uniform float uPointSize; void main(){ gl_Position=uMvp*aPosition; gl_PointSize=uPointSize; }"
        private const val POINT_FRAGMENT_SHADER = "precision mediump float; uniform vec4 uColor; void main(){ vec2 p=gl_PointCoord-vec2(0.5); if(dot(p,p)>0.25) discard; gl_FragColor=uColor; }"
    }
}
