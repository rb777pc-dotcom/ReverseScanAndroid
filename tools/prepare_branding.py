#!/usr/bin/env python3
"""Apply the ReverseScan 3D public identity to the checked-out Android scanner."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent.parent
app = root / "scanner-engine" / "app"
gradle = app / "build.gradle.kts"
manifest = app / "src/main/AndroidManifest.xml"
strings = app / "src/main/res/values/strings.xml"
settings = root / "scanner-engine" / "settings.gradle.kts"

def sub_once(path, pattern, replacement, label):
    text = path.read_text()
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.M)
    if count != 1:
        raise SystemExit(f"Branding patch failed: expected exactly one {label} in {path}")
    path.write_text(updated)

# A stable store identity. Keep the Kotlin namespace unchanged; it is an internal package name.
sub_once(gradle, r'applicationId = ".*?"', 'applicationId = "com.reversescan.app"', "applicationId")
sub_once(gradle, r'versionCode = \\d+', 'versionCode = 12', "versionCode")
sub_once(gradle, r'versionName = ".*?"', 'versionName = "0.9.3"', "versionName")

sub_once(manifest, r'android:icon="@mipmap/ic_launcher"', 'android:icon="@drawable/reversescan_launcher"', "launcher icon resource")
sub_once(strings, r'<string name="app_name">.*?</string>', '<string name="app_name">ReverseScan 3D</string>', "application label")
if settings.exists():
    sub_once(settings, r'rootProject.name = ".*?"', 'rootProject.name = "ReverseScan-3D"', "Gradle root project name")

# Original vector artwork: deep-blue scan frame, metallic-white R and electric-blue B.
# This keeps the launcher icon sharp at all Android launcher densities.
drawable = app / "src/main/res/drawable/reversescan_launcher.xml"
drawable.parent.mkdir(parents=True, exist_ok=True)
drawable.write_text("""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp" android:height="108dp"
    android:viewportWidth="108" android:viewportHeight="108">
    <path android:fillColor="#030A18" android:pathData="M0,0h108v108h-108z"/>
    <path android:fillColor="#071B3B" android:strokeColor="#087BFF"
        android:strokeWidth="2.2" android:pathData="M14,3h80a11,11 0,0 1,11 11v80a11,11 0,0 1,-11 11h-80a11,11 0,0 1,-11 -11v-80a11,11 0,0 1,11 -11z"/>
    <path android:fillColor="#071B3B" android:strokeColor="#00BFFF"
        android:strokeWidth="1.1" android:pathData="M54,10a39,39 0,1 0,0.1 0z"/>
    <path android:fillColor="#DDEBFF" android:pathData="M20,27h25c13,0 20,6 20,17 0,8 -4,13 -11,16l14,22h-16l-12,-20h-6v20h-14z M34,39v11h10c5,0 7,-2 7,-6 0,-3 -2,-5 -7,-5z"/>
    <path android:fillColor="#00BFFF" android:pathData="M57,27h18c13,0 20,5 20,15 0,6 -3,10 -8,12 7,2 11,7 11,14 0,11 -8,17 -22,17h-19z M71,39v10h5c4,0 6,-2 6,-5 0,-3 -2,-5 -6,-5z M71,61v12h6c5,0 7,-2 7,-6 0,-4 -2,-6 -7,-6z"/>
    <path android:fillColor="#00BFFF" android:pathData="M13,91h82v2h-82z"/>
</vector>
""", encoding="utf-8")
print("ReverseScan 3D identity applied: app label, launcher icon, applicationId and version 0.9.3 (12).")
