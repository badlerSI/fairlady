# 愛車 — the AiSha affection gauge

The 愛車 (AiSha — "ride or die") logo doubles as Ben's **affection gauge**: it fills up as Ace warms
to you and empties as she goes cold. Ben's TRADEMARKED real-calligraphy version is the hero asset —
white background → transparent, black strokes → glowing game-signature red (`#e23b2e`).

## STATUS — I need the file
The placeholders in `frontend/media/aisha_gauge/` (`aisha_lit_placeholder.png` / `aisha_dim_placeholder.png`)
are a **font stand-in (Hiragino), NOT Ben's calligraphy** — just so the gauge renders today. **Drop the
real PNG at `~/Downloads/aisha-calligraphy.png`** (or tell me where) and I'll run the recipe below to
produce the two hero assets.

## Processing recipe (run once the real PNG lands)
The source is black 愛車 strokes on white. Make a LIT version (glowing red, transparent) and a DIM base:
```bash
SRC=~/Downloads/aisha-calligraphy.png
OUT=frontend/media/aisha_gauge
RED='#e23b2e'
# 1) LIT: white→transparent, black strokes→red, soft outer glow
magick "$SRC" -colorspace Gray -negate -threshold 45% \
       -background none -alpha shape \
       -fill "$RED" -colorize 100 \
       \( +clone -background "$RED" -shadow 70x10+0+0 \) +swap -layers merge +repage \
       "$OUT/aisha_lit.png"
# 2) DIM base: same glyph, ~20% alpha, desaturated (the "empty" state)
magick "$OUT/aisha_lit.png" -channel A -evaluate multiply 0.20 +channel -modulate 55 \
       "$OUT/aisha_dim.png"
```
(`-threshold` may need tuning to the calligraphy's ink density; 40–55% is the usual range. If the seal
has a border box, add `-trim +repage` or mask it first.)

## Frontend rendering (the gauge)
Snapshot already ships **`affection_gauge`** (0.0–1.0 = `bond/100`) plus `bond`, `bond_band`,
`bond_armed`. Render the gauge as two stacked layers, the LIT revealed bottom-up by the gauge:
```html
<div class="aisha-gauge" title="愛車 — how she feels about you">
  <img class="aisha-base" src="media/aisha_gauge/aisha_dim.png">
  <img class="aisha-fill" src="media/aisha_gauge/aisha_lit.png">
</div>
```
```css
.aisha-gauge { position: relative; width: 64px; }
.aisha-gauge img { width: 100%; display: block; }
.aisha-fill { position: absolute; inset: 0;
  /* reveal from the bottom up, proportional to the gauge */
  clip-path: inset(calc((1 - var(--aisha, .55)) * 100%) 0 0 0);
  filter: drop-shadow(0 0 6px #e23b2e);
  transition: clip-path .6s ease; }
.aisha-gauge.armed .aisha-fill { animation: aisha-flicker 1.2s infinite; } /* COLD/anti-theft armed */
@keyframes aisha-flicker { 50% { opacity:.4 } }
```
```js
// per snapshot: set the fill level + the cold/armed flicker
gaugeEl.style.setProperty('--aisha', snap.affection_gauge);
gaugeEl.classList.toggle('armed', snap.bond_armed);
```
So: high affection → 愛車 fully lit and glowing red; low → it drains to the dim outline; COLD (armed
anti-theft) → it flickers. It "fills up or empties" exactly as Ben asked.

## What moves the gauge (engine, already wired)
- **Up, slowly:** any conversation with Ace (`bond.converse`, diminishing per place, resets on a drive).
- **Up, faster:** asking about HER — the build/specs, her origins, "tell me about yourself".
- Up: lore reveals, buying her, clean driving, giving her the wheel, peeling a respray.
- **Down:** stranding her, selling parts, bringing a date home, **spraying her (→ phone-home)**, and
  **marrying Alma** (the love triangle costs you with Ace).
- **The floor (Ben's ratchet):** on a rewind/failure, affection never drops more than `BOND_FLOOR_DROP`
  below its high-water mark — you never face a wall again with less than last time.
