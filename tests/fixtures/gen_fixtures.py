#!/usr/bin/env python3
"""Generate synthetic test fixtures: byte-identical pairs, re-encoded, resized."""
from PIL import Image
import shutil
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent / "images"
FIXTURE_DIR.mkdir(exist_ok=True)

# 100x100 red image
img = Image.new("RGB", (100, 100), color=(255, 0, 0))
img.save(FIXTURE_DIR / "red_100x100.jpg", "JPEG", quality=95)

# Byte-identical copy
shutil.copy(FIXTURE_DIR / "red_100x100.jpg", FIXTURE_DIR / "red_100x100_copy.jpg")

# Re-encoded (same visual content, different bytes)
img.save(FIXTURE_DIR / "red_100x100_reencoded.jpg", "JPEG", quality=90)

# 200x200 version
img_big = img.resize((200, 200), Image.LANCZOS)
img_big.save(FIXTURE_DIR / "red_200x200.jpg", "JPEG", quality=95)

# Pure PNG (lossless, ensures exact pixel round-trip)
img.save(FIXTURE_DIR / "red_100x100.png", "PNG")

import struct, zlib

def write_fake_huge_png(path, claimed_w, claimed_h):
    """Write a PNG with claimed huge dimensions but minimal data (T-008 OOM guard test)."""
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", claimed_w, claimed_h, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    idat_data = zlib.compress(b"")
    idat_crc = zlib.crc32(b"IDAT" + idat_data) & 0xFFFFFFFF
    idat = struct.pack(">I", len(idat_data)) + b"IDAT" + idat_data + struct.pack(">I", idat_crc)
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)
    with open(path, "wb") as f:
        f.write(sig + ihdr + idat + iend)

write_fake_huge_png(FIXTURE_DIR / "huge_100000x100000.png", 100000, 100000)

print("Fixtures written to", FIXTURE_DIR)
for p in sorted(FIXTURE_DIR.iterdir()):
    print(f"  {p.name}: {p.stat().st_size} bytes")
