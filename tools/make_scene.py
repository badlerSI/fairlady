#!/usr/bin/env python3
"""Posterize Wikimedia photos into RIDE OR DIE scene sketches — the koiNOya treatment.

320×200, brand cyan on near-black, hard tonal bands with a Bayer-dithered seam between
them (the 'we only had 16 MB' look). Reads data/gazetteer/img/, writes
frontend/scenes_wm/<id>.png (tiny palettized PNGs).

    ./.venv/bin/python tools/make_scene.py <id>          # one place, writes a x3 preview too
    ./.venv/bin/python tools/make_scene.py --all         # everything in source.json
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
IMG_DIR = ROOT / "data" / "gazetteer" / "img"
OUT_DIR = ROOT / "frontend" / "scenes_wm"
W, H = 320, 200

# the brand ramp (retro.js INK)
BG = (14, 12, 10)
D1 = (19, 38, 42)
D2 = (31, 111, 125)
F = (56, 214, 236)
HOT = (184, 244, 255)

BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# Tonal bands are ADAPTIVE per image (percentiles of the luma histogram), so a blown-out
# desert noon and a dusk street both land at koi-crt ink coverage: ~38% shadow floor,
# a dim dither seam, bright ink above the 60th percentile, hot only in the top ~3%.
P_BG, P_SEAM, P_HOT = 38, 60, 97


def _percentile_thresholds(im: Image.Image):
    hist = im.histogram()
    total = sum(hist)
    cum, marks, found = 0, [P_BG, P_SEAM, P_HOT], []
    for v, n in enumerate(hist):
        cum += n
        while found != marks and len(found) < 3 and cum >= total * marks[len(found)] / 100.0:
            found.append(v / 255.0)
            if len(found) == 3:
                break
    while len(found) < 3:
        found.append(0.95)
    t1, t2, t3 = found
    # keep the bands sane on near-flat images
    t2 = max(t2, t1 + 0.08)
    t3 = max(min(t3, 0.97), t2 + 0.10)
    return t1, t2, t3


def posterize(src: Image.Image) -> Image.Image:
    im = ImageOps.exif_transpose(src).convert("L")
    im = ImageOps.autocontrast(im, cutoff=2)
    im = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.45))
    im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=120, threshold=4))
    T1, T2, T3 = _percentile_thresholds(im)
    px = im.load()
    out = Image.new("RGB", (W, H), BG)
    op = out.load()
    for y in range(H):
        for x in range(W):
            v = px[x, y] / 255.0
            th = (BAYER[y % 4][x % 4] + 0.5) / 16.0
            if v < T1:
                op[x, y] = BG
            elif v < T2:
                # the seam: dither between the dim cyans for texture
                frac = (v - T1) / (T2 - T1)
                op[x, y] = D2 if frac > th else D1
            elif v < T3:
                # main ink: a touch of dither at the bottom edge keeps gradients honest
                frac = (v - T2) / (T3 - T2)
                op[x, y] = F if (frac > 0.18 or frac > th * 0.4) else D2
            else:
                op[x, y] = HOT
    return out


def bake(pid: str, img_file: str, preview: bool = False) -> bool:
    src_path = IMG_DIR / img_file
    if not src_path.exists():
        return False
    try:
        out = posterize(Image.open(src_path))
    except Exception as e:
        print(f"  {pid}: {e}")
        return False
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.convert("P", palette=Image.ADAPTIVE, colors=8).save(OUT_DIR / f"{pid}.png", optimize=True)
    if preview:
        out.resize((W * 3, H * 3), Image.NEAREST).save(f"/tmp/scene_{pid}.png")
    return True


def main():
    db = json.loads((ROOT / "data" / "gazetteer" / "source.json").read_text())
    records = {**db["towns"], **db["existing"]}
    if len(sys.argv) > 1 and sys.argv[1] != "--all":
        for pid in sys.argv[1:]:
            r = records.get(pid, {})
            print(pid, "->", bake(pid, r.get("img_file", ""), preview=True))
        return
    done = skip = 0
    for pid, r in records.items():
        if r.get("img_file") and bake(pid, r["img_file"]):
            done += 1
        else:
            skip += 1
    print(f"baked {done} scenes, skipped {skip} (no/unreadable image)")


if __name__ == "__main__":
    main()
