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
sub_once(gradle, r'versionCode = \d+', 'versionCode = 12', "versionCode")
sub_once(gradle, r'versionName = ".*?"', 'versionName = "0.9.3"', "versionName")

sub_once(manifest, r'android:icon="@mipmap/ic_launcher"', 'android:icon="@drawable/reversescan_app_icon"', "launcher icon resource")
sub_once(strings, r'<string name="app_name">.*?</string>', '<string name="app_name">ReverseScan 3D</string>', "application label")
if settings.exists():
    sub_once(settings, r'rootProject.name = ".*?"', 'rootProject.name = "ReverseScan-3D"', "Gradle root project name")

# Decode the selected user-supplied RB emblem from the repository's text-safe asset.
import base64
asset_b64 = root / "assets/reversescan_rb_icon.webp.b64"
if not asset_b64.is_file():
    raise SystemExit("Missing selected RB launcher artwork: assets/reversescan_rb_icon.webp.b64")
encoded = "".join(asset_b64.read_text().split())
if len(encoded) < 16 or not encoded.startswith("UklGR"):
    raise SystemExit("Selected ReverseScan RB icon is not a valid WebP file")
header = base64.b64decode(encoded[:16], validate=True)
if header[:4] != b"RIFF" or header[8:12] != b"WEBP":
    raise SystemExit("Selected ReverseScan RB icon has an invalid WebP header")
expected = int.from_bytes(header[4:8], "little") + 8
encoded_length = ((expected + 2) // 3) * 4
icon_bytes = base64.b64decode(encoded[:encoded_length], validate=True)
if len(icon_bytes) != expected:
    raise SystemExit("Selected ReverseScan RB icon is truncated")

icon_path = app / "src/main/res/drawable-nodpi/reversescan_app_icon.webp"
icon_path.parent.mkdir(parents=True, exist_ok=True)
icon_path.write_bytes(icon_bytes)
print("ReverseScan 3D identity applied: selected RB artwork, app label, applicationId and version 0.9.3 (12).")
