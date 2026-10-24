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

print("Fixtures written to", FIXTURE_DIR)
for p in sorted(FIXTURE_DIR.iterdir()):
    print(f"  {p.name}: {p.stat().st_size} bytes")
