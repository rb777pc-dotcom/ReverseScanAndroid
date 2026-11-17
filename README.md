# ReverseScan Android — v0.5.0

Native Android 3D scanning prototype built with Kotlin and Google ARCore Depth API. Intended first for depth-capable ARCore devices such as Samsung Galaxy S24 Ultra.

## Included in v0.5.0

- ARCore live camera preview with display-geometry correction.
- Camera autofocus requested through ARCore `FocusMode.AUTO`.
- ARCore automatic depth acquisition with confidence filtering.
- On-camera target frame; depth capture is restricted to its central region to reduce background collection.
- Live camera overlay: green points show accumulated scan data; yellow points show the latest depth capture; areas without points have not yet been captured.
- Live scan counters for captured viewpoints and depth samples.
- Rotatable point-cloud inspection dialog before triangle-mesh reconstruction.
- ARCore flash/torch toggle when the active camera configuration supports it.
- Continuous capture while scanning, plus manual single-view capture.
- Multi-view accumulation in a scan-local coordinate frame.
- Sparse projective TSDF volume integration.
- Marching-tetrahedra surface reconstruction from the accumulated TSDF.
- Interactive shaded mesh preview; drag to rotate the result.
- PLY point-cloud export.
- OBJ triangle-mesh export (coordinates in metres).
- Binary STL triangle-mesh export (coordinates converted to millimetres).
- System file picker for saving exports.
- Reset of the current scan and volume.

## Scan workflow

1. Install the APK and grant camera permission.
2. Wait until ARCore reports that the camera is ready.
3. Place the object in a well-lit, textured scene. Avoid glossy, transparent, black, or moving surfaces.
4. If needed, turn on **Фонарик**. It uses the active ARCore camera flash when supported.
5. Keep the object inside the on-screen frame and make it fill most of that frame. The scanner captures depth only inside this region; background outside it is ignored. Press **Начать скан** and move slowly around the stationary object using overlapping viewpoints.
6. Watch the live overlay: green points are accumulated data; yellow points are the latest depth frame; uncovered areas show no scan points. The status line reports accepted viewpoints and point counts.
7. Use **Пауза** to stop automatic capture. **Добавить ракурс** captures an additional depth view manually.
8. Inspect the live overlay before finishing. If a side has no points, move to that side and capture it.
9. Press **Просмотр скана** to rotate and inspect the accumulated point cloud before reconstruction. Close it and continue scanning if coverage is missing.
10. **Сохранить PLY** exports the accumulated point cloud. **Построить 3D** reconstructs a triangle surface from the TSDF volume.
11. Drag the mesh preview to inspect it. Export as OBJ or STL from the preview dialog.
12. Use **Новый скан — очистить данные** before scanning another object.

For a small object, start roughly 0.4–0.8 m away and adjust so the object fills most of the guide frame. ARCore Depth API's usable range and quality depend on device, firmware, light, texture, motion, and object material. ARCore Depth API's usable range and quality depend on device, firmware, light, texture, motion, and object material.

## Output formats

- **PLY**: depth-derived point cloud; not a surface mesh.
- **OBJ**: triangle surface mesh, coordinates in metres.
- **STL**: triangle surface mesh, coordinates written in millimetres.

The reconstructed surface is not guaranteed to be watertight, manifold, hole-free, dimensionally calibrated, or suitable for direct 3D printing. Open or missing areas can occur where depth observations do not overlap. Inspect and repair the mesh in MeshLab, Blender, or CAD/mesh software before manufacturing.

## Accuracy and limitations

This is a phone-based depth scanner, not a metrology instrument. ARCore tracking drift, depth noise, calibration, viewpoint coverage, and surface reflectivity affect dimensions and topology. Do not rely on it for engineering tolerances without scale calibration and independent measurement using appropriate instruments.

The current version does not provide CAD feature recognition, parametric modelling, STEP export, automatic hole filling, or guaranteed watertight mesh generation. STL export does not validate printability.

## Build and tests

The GitHub Actions workflow runs JVM unit tests for TSDF mesh extraction and builds the debug APK:

```bash
gradle --no-daemon --stacktrace testDebugUnitTest assembleDebug
```

Install and test on the physical ARCore-capable phone. The Android emulator cannot validate the camera depth pipeline.
