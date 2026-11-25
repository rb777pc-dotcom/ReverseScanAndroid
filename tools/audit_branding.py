#!/usr/bin/env python3
"""Fail the full APK build if upstream product identity leaks into app source/resources."""
from pathlib import Path
import base64
import re

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / "scanner-engine"
APP = ROOT / "app/src/main"
RES = APP / "res"

manifest = (APP / "AndroidManifest.xml").read_text(errors="ignore")
if 'android:label="@string/app_name"' not in manifest:
    raise SystemExit("Brand audit: launcher label is not bound to app_name")
strings_xml = (RES / "values/strings.xml").read_text(errors="ignore")
match = re.search(r'<string\s+name="app_name">(.*?)</string>', strings_xml, re.S)
if not match or re.sub(r"\s+", " ", match.group(1)).strip() != "ReverseScan 3D":
    raise SystemExit("Brand audit: app_name must be exactly ReverseScan 3D")

info_file = RES / "values/strings_info.xml"
if info_file.exists() and re.search(r'<string\s+name="credit_[^"]+"', info_file.read_text(errors="ignore")):
    raise SystemExit("Brand audit: obsolete upstream component-credit resources remain")

# Scan the complete application source tree, including code comments, diagnostics,
# model/capture export metadata, Android resources and build metadata. Keep legal
# notices intact and out of the application-author identity scan.
extensions = {
    ".kt", ".java", ".xml", ".json", ".txt", ".html", ".md", ".gradle",
    ".kts", ".properties", ".toml", ".yaml", ".yml", ".pro", ".cfg", ".ini",
    ".sh", ".py", ".c", ".cc", ".cpp", ".h", ".hpp", ".cmake"
}
legal_parts = {"license", "licenses", "notice", "notices", "third_party", "third-party", "copying", "copyright"}
banned = re.compile(r"Strata\s*:\s*3D|David\s+Morales|damzenquis|nini1294", re.I)
hits = []
for path in APP.rglob("*"):
    if not path.is_file() or path.suffix.lower() not in extensions:
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
    print("\n".join(hits[:250]))
    raise SystemExit("Brand audit failed: foreign product branding remains in app source/code")

# Validate the user-supplied launcher artwork byte-for-byte.
# The text-safe asset may contain a trailing transport character after the padded
# Base64 payload. Read the WebP RIFF length first, then decode exactly that payload,
# matching prepare_branding.py; never decode arbitrary trailing bytes.
brand_b64 = REPO / "assets/reversescan_rb_icon.webp.b64"
encoded = "".join(brand_b64.read_text().split())
header = base64.b64decode(encoded[:16], validate=True)
if header[:4] != b"RIFF" or header[8:12] != b"WEBP":
    raise SystemExit("Brand audit: launcher artwork has an invalid WebP header")
expected_size = int.from_bytes(header[4:8], "little") + 8
payload_length = ((expected_size + 2) // 3) * 4
if len(encoded) < payload_length:
    raise SystemExit("Brand audit: launcher artwork Base64 payload is truncated")
expected = base64.b64decode(encoded[:payload_length], validate=True)
if len(expected) != expected_size:
    raise SystemExit("Brand audit: launcher artwork WebP payload length is invalid")
icon = RES / "drawable-nodpi/reversescan_app_icon.webp"
if not icon.is_file() or icon.read_bytes() != expected:
    raise SystemExit("Brand audit: launcher icon is not the supplied ReverseScan RB artwork")
print("Brand audit passed: no foreign product branding in app code/resources; legal notices preserved.")
