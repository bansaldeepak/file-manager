#!/usr/bin/env python3
"""Export golden hash values for Rust parity tests.

Run after gen_fixtures.py. Reads images from tests/fixtures/images/ and
writes tests/fixtures/golden.json with sha256 and pixel_hash for each file.

Pixel hash algorithm matches app.py:signatures() exactly:
  - PIL ImageOps.exif_transpose
  - convert to RGBA
  - 8-byte big-endian width + 8-byte big-endian height prefix
  - SHA-256 of (prefix + raw RGBA bytes)
"""
import json
import hashlib
import struct
import sys
from pathlib import Path
from PIL import Image, ImageOps

FIXTURE_DIR = Path(__file__).parent / "images"
OUT = Path(__file__).parent / "golden.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pixel_hash(path: Path) -> str:
    with Image.open(path) as img:
        img.seek(0)
        img = ImageOps.exif_transpose(img).convert("RGBA")
        w, h = img.size
        # 8-byte BE width + 8-byte BE height prefix (matches app.py:53)
        prefix = w.to_bytes(8, "big") + h.to_bytes(8, "big")
        raw = img.tobytes()
        return hashlib.sha256(prefix + raw).hexdigest()


if not FIXTURE_DIR.exists() or not list(FIXTURE_DIR.iterdir()):
    print("ERROR: Run gen_fixtures.py first", file=sys.stderr)
    sys.exit(1)

records = {}
for p in sorted(FIXTURE_DIR.glob("*")):
    if p.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        continue
    records[p.name] = {
        "sha256": sha256_file(p),
        "pixel_hash": pixel_hash(p),
        "size": p.stat().st_size,
    }

OUT.write_text(json.dumps(records, indent=2))
print(f"Wrote {len(records)} fixtures to {OUT}")
for name, v in records.items():
    print(f"  {name}: sha256={v['sha256'][:16]}... pixel={v['pixel_hash'][:16]}...")
