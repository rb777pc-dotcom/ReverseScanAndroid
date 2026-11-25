# ReverseScan 3D

**Android 3D object scanner · ARCore Depth API · PLY / OBJ / STL**

[Russian version](README_RU.md) · [Download APK](https://github.com/rb777pc-dotcom/ReverseScanAndroid/actions/workflows/reversescan-full-build.yml) · [Report a bug](https://github.com/rb777pc-dotcom/ReverseScanAndroid/issues/new/choose) · [All issues](https://github.com/rb777pc-dotcom/ReverseScanAndroid/issues)

## Latest build

**Current app version: 0.9.1**  
Open the workflow page below and choose the latest successful run.

To download the installable APK:

1. Open the latest successful workflow run.
2. Scroll to **Artifacts** at the bottom of the run page.
3. Download **ReverseScan-full** (do not choose `ReverseScan-native`; that is an internal preflight build).
4. Extract the ZIP and install `app-debug.apk` on an ARCore-compatible Android phone.

For a newer build, open [Actions](https://github.com/rb777pc-dotcom/ReverseScanAndroid/actions/workflows/reversescan-full-build.yml), select the latest successful **Build ReverseScan 3D scanner** run, and download its **ReverseScan-full** artifact.

> Actions artifacts are temporary downloads and expire according to the retention period. A permanent GitHub Release is not published yet. Do not download the automatically generated **Source code** ZIP as an APK.

## What it does

- Uses ARCore Depth API for multi-view depth capture.
- Lets the user outline the target object before scanning.
- Locks a conservative 3D target volume and rejects observations outside it.
- Accumulates depth points from overlapping viewpoints.
- Reconstructs a triangle mesh from the accumulated depth volume.
- Previews and rotates the reconstructed model.
- Exports point clouds as PLY and meshes as OBJ or STL.
- Imports supported PLY point-cloud files.

The scanner uses depth-based segmentation, not semantic AI object recognition. Results depend on device support, lighting, surface texture, reflectivity, tracking quality, and viewpoint coverage.

## Scan workflow

1. Install the APK and grant camera permission.
2. Wait for ARCore to initialise.
3. Outline the object inside the guide frame.
4. Start scanning and move slowly around the stationary object, keeping adjacent viewpoints overlapping.
5. Pause when coverage is complete. Capture additional viewpoints where the preview shows missing areas.
6. Inspect the accumulated point cloud, then build the 3D mesh.
7. Export the point cloud as PLY or the mesh as OBJ/STL.

Use the on-screen **Torch** control only when the device camera supports flash. The app interface currently uses Russian labels; this English guide uses English descriptions consistently.

## File formats

- **PLY** — depth-derived point cloud; not a surface mesh.
- **OBJ** — triangle mesh; coordinates in metres.
- **STL** — triangle mesh; coordinates in millimetres.

The output is not guaranteed to be watertight, manifold, dimensionally calibrated, or ready for manufacturing. Inspect and repair meshes in suitable 3D/CAD software before production. This phone-based scanner is not a metrology instrument; verify critical dimensions independently.

## Build information

The full installable scanner is assembled by the `Build ReverseScan 3D scanner` workflow. The repository's `app/` module is retained as an internal native preflight/test target; its APK artifact is **not** the full scanner.

- Workflow: [reversescan-full-build.yml](.github/workflows/reversescan-full-build.yml)
- Russian build notes: [BUILD_APK_RU.md](BUILD_APK_RU.md)
- Source branch used for the current full build: `fix-five-reported-defects`

## Support and feedback

Use [Issues](https://github.com/rb777pc-dotcom/ReverseScanAndroid/issues/new/choose) to report bugs, request features, or ask questions. Include your phone model, Android version, app build number, and the steps that reproduce the problem. Do not attach private data or scans of sensitive objects.

GitHub Discussions is currently disabled for this repository; Issues are the active support channel.
