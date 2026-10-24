#!/usr/bin/env python3
"""Generate a 1024x1024 app icon for Arcitae Dedupe."""
from PIL import Image, ImageDraw
import math, sys, os

SIZE = 1024
out = os.path.join(os.path.dirname(__file__), "icon-source.png")

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# ── background: dark navy rounded square ─────────────────────────
BG = "#141820"
r = 220  # corner radius (macOS adds its own rounding on top)
d.rounded_rectangle([0, 0, SIZE, SIZE], radius=r, fill=BG)

# ── helper: draw a photo-frame card ──────────────────────────────
def photo_card(draw, x, y, w, h, fill, border, border_w=10, cr=36,
               horizon_frac=0.55):
    """Rounded-corner photo card with a simple landscape inside."""
    # card body
    draw.rounded_rectangle([x, y, x+w, y+h], radius=cr, fill=fill, outline=border, width=border_w)
    # clip landscape to inner area
    pad = border_w + 4
    ix, iy, iw, ih = x+pad, y+pad, w-2*pad, h-2*pad
    hoz_y = iy + int(ih * horizon_frac)
    # sky block
    draw.rectangle([ix, iy, ix+iw, hoz_y], fill="#8AB5D1")
    # ground block
    draw.rectangle([ix, hoz_y, ix+iw, iy+ih], fill="#4A7C5A")
    # mountain (triangle)
    mx = ix + iw // 2
    peak_y = iy + int(ih * 0.18)
    bl = ix + int(iw * 0.12)
    br = ix + int(iw * 0.88)
    draw.polygon([(mx, peak_y), (bl, hoz_y), (br, hoz_y)], fill="#B8C8D8")
    # sun circle
    sun_x = ix + int(iw * 0.75)
    sun_y = iy + int(ih * 0.28)
    sr = int(iw * 0.09)
    draw.ellipse([sun_x-sr, sun_y-sr, sun_x+sr, sun_y+sr], fill="#F0D080")

# ── back card (slightly rotated via manual polygon) ───────────────
# We can't rotate a sub-image easily with Draw, so we composite a
# rotated card layer.
card_w, card_h = 540, 420
cx, cy = SIZE // 2, SIZE // 2 - 10  # center of the card stack

def make_card_layer(fill, border, angle_deg):
    layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ox = cx - card_w // 2
    oy = cy - card_h // 2
    photo_card(ld, ox, oy, card_w, card_h, fill=fill, border=border)
    return layer.rotate(angle_deg, resample=Image.BICUBIC, center=(cx, cy), expand=False)

# back card: lighter, rotated -12°
back = make_card_layer("#2E3650", "#4A5578", -12)
img = Image.alpha_composite(img, back)

# front card: crisp, no rotation
front_layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
fd = ImageDraw.Draw(front_layer)
ox = cx - card_w // 2
oy = cy - card_h // 2
photo_card(fd, ox, oy, card_w, card_h,
           fill="#2A3148", border="#5C6990")
img = Image.alpha_composite(img, front_layer)

# ── vermillion "×2" badge bottom-right ───────────────────────────
VERMILLION = "#D63B2F"
bd = ImageDraw.Draw(img)
bx, by, br2 = 688, 650, 100  # center x, y, radius
bd.ellipse([bx-br2, by-br2, bx+br2, by+br2], fill=VERMILLION)
# draw "2" using simple geometric shapes (avoid font dependency)
# Use a thick "2" drawn with rectangles/arcs — just use text via default font
try:
    from PIL import ImageFont
    # try to get a bold system font
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size=118)
except Exception:
    font = ImageFont.load_default()
tw_bbox = bd.textbbox((0, 0), "×2", font=font)
tw = tw_bbox[2] - tw_bbox[0]
th = tw_bbox[3] - tw_bbox[1]
bd.text((bx - tw//2, by - th//2 - 4), "×2", fill="white", font=font)

# ── save ─────────────────────────────────────────────────────────
img.save(out, "PNG")
print(f"Saved {out}  ({SIZE}×{SIZE})")
