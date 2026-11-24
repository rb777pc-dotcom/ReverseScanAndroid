#!/usr/bin/env python3
"""Fail the full APK build if upstream product branding leaks into app UI."""
from pathlib import Path
import base64
import re

ROOT = Path(__file__).resolve().parent.parent / "strata"
APP = ROOT / "app/src/main"
RES = APP / "res"
manifest = (APP / "AndroidManifest.xml").read_text(errors="ignore")
if 'android:label="@string/app_name"' not in manifest:
    raise SystemExit("Brand audit: Android launcher label is not bound to ReverseScan app_name")
strings_xml = (RES / "values/strings.xml").read_text(errors="ignore")
match = re.search(r'<string\s+name="app_name">(.*?)</string>', strings_xml, re.S)
if not match or re.sub(r"\s+", " ", match.group(1)).strip() != "ReverseScan 3D":
    raise SystemExit("Brand audit: app_name must be exactly ReverseScan 3D")
info_file = RES / "values/strings_info.xml"
if info_file.exists() and re.search(r'<string\s+name="credit_[^"]+"', info_file.read_text(errors="ignore")):
    raise SystemExit("Brand audit: obsolete component-credit resources remain in the app")

# Legal notice documents are excluded and must remain intact.
banned = re.compile(r"Strata\s*:\s*3D|David\s+Morales|damzenquis|nini1294", re.I)
legal_parts = {"license", "licenses", "notice", "notices", "third_party", "third-party", "copying", "copyright"}
hits = []
for path in APP.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in {".kt", ".java", ".xml", ".json", ".txt", ".html", ".md"}:
        continue
    if any(part.lower() in legal_parts for part in path.parts):
        continue
    try:
        body = path.read_text(errors="ignore")
    except OSError:
        continue
    for number, line in enumerate(body.splitlines(), 1):
        if banned.search(line):
            hits.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()[:180]}")
if hits:
    print("\n".join(hits))
    raise SystemExit("Brand audit failed: upstream branding is still present outside legal notices")

brand_b64 = Path(__file__).resolve().parent.parent / "assets/reversescan_rb_icon.webp.b64"
expected = base64.b64decode("".join(brand_b64.read_text().split()), validate=True)
icon = RES / "mipmap-nodpi/ic_launcher.webp"
if not icon.is_file() or icon.read_bytes() != expected:
    raise SystemExit("Brand audit: launcher icon is not the supplied ReverseScan RB artwork")
print("Brand audit passed: ReverseScan 3D identity is used; legal notices are preserved.")
