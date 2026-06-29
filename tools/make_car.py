#!/usr/bin/env python3
"""Digitize Ben's real 240Z (rear-3/4) into a 1-bit CYAN ink sprite — koiNOya 'there or not there'.
OPAQUE: anything inside the photo cutout renders solid (dark glass/tires opaque, body cyan), so the
car sits on the top layer and the road never shows through her. Bakes frontend/car_sprite.js with
anchors for the fender mirror and the rear glass (for the moving reflection)."""
import sys, base64, io, json
from PIL import Image, ImageOps

SRC = "/tmp/z_src.png"
CY = (56, 214, 236); HOT = (184, 244, 255); DARK = (19, 38, 42)
INK_T, HOT_T = 0.47, 0.80

def load_car():
    im = Image.open(SRC).convert("RGBA")
    bb = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
    return im.crop(bb)

def threshold(im, tw):
    th = round(tw * im.height / im.width)
    im = im.resize((tw, th), Image.LANCZOS)
    a = im.getchannel("A"); L = ImageOps.autocontrast(im.convert("L"), cutoff=2)
    lo, ao = L.load(), a.load()
    g = [[None]*tw for _ in range(th)]
    for y in range(th):
        for x in range(tw):
            if ao[x, y] < 120:      # outside the cutout
                continue
            v = lo[x, y] / 255.0
            g[y][x] = 2 if v >= HOT_T else (1 if v >= INK_T else 0)
    # denoise speckle on the lit pixels only (keep the opaque silhouette intact)
    def nb(x, y):
        n = 0
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                if (dx or dy) and 0 <= x+dx < tw and 0 <= y+dy < th and g[y+dy][x+dx]:
                    n += 1
        return n
    g2 = [row[:] for row in g]
    for y in range(th):
        for x in range(tw):
            if g[y][x] and g[y][x] >= 1 and nb(x, y) <= 1 and ao[x,y] >= 120:
                # only drop a truly isolated lit pixel back to opaque-dark, never to transparent
                g2[y][x] = 0
    out = Image.new("RGBA", (tw, th), (0,0,0,0)); po = out.load()
    for y in range(th):
        for x in range(tw):
            if g2[y][x] is None: continue            # transparent (outside)
            po[x,y] = (*HOT,255) if g2[y][x]==2 else ((*CY,255) if g2[y][x]==1 else (*DARK,255))
    return out

def main():
    tw = int(sys.argv[1]) if len(sys.argv) > 1 else 188
    spr = threshold(load_car(), tw)
    bg = Image.new("RGBA", spr.size, (14,12,10,255)); bg.alpha_composite(spr)
    bg.convert("RGB").resize((spr.size[0]*3, spr.size[1]*3), Image.NEAREST).save("/tmp/car_preview.png")
    print("opaque sprite", spr.size)
    if "--bake" in sys.argv:
        buf = io.BytesIO(); spr.save(buf, "PNG"); b64 = base64.b64encode(buf.getvalue()).decode()
        meta = {"w": spr.size[0], "h": spr.size[1], "anchors": {
            "mirror": [0.10, 0.15],            # driver-side fender bullet mirror
            "rearGlass": [0.18, 0.06, 0.30, 0.27],  # x,y,w,h — the back windshield (reflection sweep)
            "ground": 0.97}}
        open("frontend/car_sprite.js","w").write(
            "// Ace — 1-bit cyan ink (opaque), digitized by tools/make_car.py. Do not hand-edit.\n"
            f"const CAR_META={json.dumps(meta)};\n"
            f'const CAR_PNG=\"data:image/png;base64,{b64}\";\n')
        print("baked (", len(b64), "b64 )")

if __name__ == "__main__":
    import os
    if not os.path.exists(SRC):
        sys.exit(f"make_car: no source photo at {SRC} — drop the car photo there (PNG with alpha) first.")
    main()
