# ReverseScan Android — v0.2.0 (capture prototype)

Target: Samsung Galaxy S24 Ultra. Native Android/Kotlin + Google ARCore.

## Implemented in this iteration
- Live ARCore camera background rendered with OpenGL ES 2.0.
- Camera permission and ARCore install/availability flow.
- ARCore Depth API support check and automatic depth configuration.
- Manual multi-view capture of Raw Depth 16-bit and Raw Depth Confidence images.
- Back-projection of depth pixels using camera intrinsics.
- Transform of sampled points into the ARCore world coordinate frame.
- Confidence filtering and point-cloud accumulation across captured views.
- ASCII PLY export in metres to the app-specific external files directory (`Android/data/com.reversescan.app/files/ReverseScan`).

## Important limitations
This is an early capture prototype, not a finished scanner or metrology instrument.
- It captures depth-derived points only; RGB photographs are currently displayed but not stored with the scan.
- Point-cloud registration relies on ARCore world tracking. Drift and scale/depth errors remain possible.
- No mesh reconstruction, hole filling, CAD editing, or STL/STEP export is implemented yet.
- A PLY point cloud is not a watertight printable mesh.
- The confidence threshold and sampling stride are prototype defaults and need calibration against measured artefacts on the actual S24 Ultra firmware.
- ARCore Raw Depth availability depends on device/runtime support. If unavailable, the app reports the capture failure.

## Build
1. Install Android Studio and Android SDK Platform 35.
2. Open this folder in Android Studio and allow Gradle sync.
3. Connect the physical Galaxy S24 Ultra with USB debugging enabled.
4. Build > Build Bundle(s) / APK(s) > Build APK(s), or run the app directly.
5. Install/update Google Play Services for AR when prompted.

The Android emulator is not a valid test target for the device depth pipeline.

## Scan workflow
1. Start the app and grant camera permission.
2. Wait for ARCore tracking to become active.
3. Move slowly around a textured, well-lit object; avoid motion blur and reflective/transparent surfaces.
4. Tap **Добавить ракурс** from multiple viewpoints. The app samples depth pixels and adds world-space points.
5. Tap **Завершить и сохранить PLY**.
6. Retrieve the file from the app-specific files folder using Android's file manager or Android Studio Device Explorer.

## Roadmap
### Next: capture quality and project format
- Persist per-view depth, confidence, camera intrinsics, camera pose, timestamps, and RGB frames.
- Add scan-session start/stop and a live tracking/coverage indicator.
- Add reference-scale calibration and measurement uncertainty reporting.
- Add point-cloud preview, voxel filtering, outlier removal, and downsampling.

### Reconstruction
- Multi-view registration refinement and loop closure.
- Surface reconstruction and mesh cleanup.
- Export OBJ/PLY/STL/3MF; STL/3MF only after mesh validation.

### Reverse engineering / CAD
- Fit planes, cylinders, circles, holes, and sections to the scan.
- Parametric sketches, extrusions, bores, offsets, shells, mating clearances.
- Integrate a solid CAD kernel for valid B-rep/STEP export.

## Accuracy policy
The app must never present phone-derived dimensions as guaranteed engineering tolerances. Depth-from-motion depends on texture, lighting, range, motion, camera calibration, and tracking quality. Critical fits require scale calibration and independent verification with calipers/micrometers plus a test print. Large objects require sectional scanning and registration; “any size” is a workflow target, not an unlimited single-scan capture promise.

## Build an APK

A GitHub Actions workflow is included at `.github/workflows/build-apk.yml`. Push this project to a GitHub repository, then open **Actions → Build Android APK**. Download the `ReverseScan-debug-apk` artifact from a successful run. Detailed Russian instructions and current limitations are in `BUILD_APK_RU.md`.
