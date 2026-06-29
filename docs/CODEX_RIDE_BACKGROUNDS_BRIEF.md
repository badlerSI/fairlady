# CODEX BRIEF — RIDE OR DIE *ride & parking* backgrounds (the road she rides on)

**You nailed the location plates.** This is the companion set: the **environment behind the car**
while she's *driving between towns* and *parked in generic contexts* — the part that currently
looks flat next to your plates. The car sprite ("Ace", a digitized 240Z) is fine and stays; we
only need better **backgrounds** for her to ride on.

Same pixel pipeline as your location plates — **reuse `loc_palette.png`, `loc_plate_tool.py`, the
5-color cyan ramp, and the 320×200 dither**. The only thing that changes is the *subjects* and one
**new composition rule** (the car is composited on top — read §3).

---

## 0. Why this set exists (the gap, in one paragraph)

Every **POI** already has your beautiful cyan plate (`scenes_wm/<id>.png`). But the panel only ever
shows a **place** — when the player *drives a leg* it shows the origin's static plate, then snaps to
the destination's. There is **no "open road" art, no day/night, no weather, no parked-vs-moving
feel.** The fallback that *should* cover the road between towns is a crude procedural canvas loop
(`drive_desert` / `drive_city` / `drive_mountain` in `frontend/scenes.js`) plus three weak photo
skins (`gas.png`, `motel.png`, `drive_city.png`). Those are what look wrong. **This brief replaces
them with a small, painted, context-aware background set in your plate style.** Claude wires the
selection logic; you supply the art.

---

## 1. MASTER STYLE BLOCK  *(prepend verbatim to EVERY prompt — identical to the plates brief)*

> Retro 1980s computer-game location backdrop, single wide establishing shot, full-bleed,
> 16:10 landscape, no text, no logos, no watermark, **no cars or people in the foreground**, no UI,
> no border or frame. Photographic realism of the real place, slightly moody and cinematic, strong
> directional light (golden hour, blue-hour, or night), deep atmospheric haze in the distance, high
> tonal contrast with a **bright sky and dark land**. Composition reads instantly at thumbnail size:
> one clear subject, simple silhouette, generous sky. Painted from a real reference of the actual
> Southwest. SUBJECT:

Then append the **SUBJECT** string from §4. Keep `no text`, `no cars/people in foreground`,
`no frame/border`, `16:10 wide`, `single subject`, `bright sky` in every prompt — they're what make
the duotone ramp read after dithering.

---

## 2. THE LOOK + OUTPUT  *(unchanged from the location plates — same palette, same dither)*

- **Size:** **320×200**, opaque PNG, 8-bit indexed (PNG color-type 3). Generate large
  (1024×640, 16:10), then downscale + dither to 320×200. Never upscale.
- **Palette (cyan rest — the only 5 colors allowed):**

  | role | hex |
  |---|---|
  | shadow / land | `#0e0c0a` |
  | dark teal | `#13262a` |
  | mid teal | `#1f6f7d` |
  | cyan | `#38d6ec` |
  | sky highlight | `#b8f4ff` |

- **Dither:** the same deterministic post-process you locked on `virginia_city` — run every raw
  through `loc_plate_tool.py` (or the §2 ImageMagick one-liner from the plates brief) so these match
  the plates exactly. **Style anchor: `frontend/scenes_wm/virginia_city.png`** — match its contrast,
  banding, and ink coverage.
- **No `_4c` variant needed.** The `_4c` hover twins are only for **map tiles**; these are
  **scene-panel backgrounds** and are never hovered. Ship the **cyan plate only.** (If your tool
  emits `_4c` for free, fine — we just won't use it.)

---

## 3. ⚠️ THE ONE NEW RULE — leave room for the car

Unlike a location plate (where the car sits over a *place*), these backgrounds get the **opaque car
sprite composited on top, every frame**:

```
  [ your 320×200 background plate ]      ← what you paint
            +  road band  +              ← engine draws a thin ground strip
  [ Ace, ~138px wide, bottom-center ]    ← opaque sprite, tires at y≈196
  =  final panel
```

So for **every** plate in this set:

1. **NO car or vehicle in the foreground.** The engine *is* the car. (Distant traffic on a far
   freeway lane is fine; nothing in the bottom-center.)
2. **Keep the bottom-center ~140px-wide strip calm** — road surface, lot asphalt, garage floor,
   open ground, or receding distance. Ace sits there (roughly x 90→230, y 130→200) and **covers
   it**, so put no critical detail there. Think "stage floor for the car."
3. **Put the subject up and to the sides** — sign, pump canopy, storefronts, ranges, skyline,
   pillars, sky — in the **upper two-thirds and the left/right thirds**, framing the car like a
   proscenium.
4. **Bright sky, dark land** (the dither ramp depends on it), even at night (a luminous sky band
   over dark ground).
5. **Driving plates:** the road/lane should **fill the lower-center and recede toward the horizon**
   (a centered or gently left-leaning vanishing point reads best — Ace is a rear-¾ heading up-and-
   away). **Parked plates:** a stationary, head-on-ish setting with a flat foreground the car parks
   on.

---

## 4. THE ASSET LIST  (id · when it shows · SUBJECT)

Filename = `roi_ride_<id>.png` (e.g. `roi_ride_desert_road.png`). Deliver to a new
`media/transmission/ride/` folder with a `manifest.json` keyed by `<id>` (same schema as the loc
manifest: `{file, kind, when, status}`; top-level `palette/size/dir/style:"roi_loc_dither_v1"`).

### 4.1 Open-road backgrounds (the drive between towns)

| id | when it shows | SUBJECT (append to §1) |
|---|---|---|
| **`desert_road`** | the default open leg — NV/AZ/CA low desert (basin & range) | an empty two-lane desert highway running dead-ahead into a wide Mojave/Great Basin basin, creosote flats, a distant blue mountain range, telephone poles marching to a vanishing point, enormous sky; the road fills the lower-center and recedes; golden-hour low sun |
| **`desert_road_night`** | same leg, after dark (hour <6 or ≥19) | the same empty desert two-lane at night, deep blue-black land, a luminous band of stars and a thin sodium glow on the far horizon, the lane receding into darkness; bright starfield sky over dark ground |
| **`forest_road`** | a Sierra / Tahoe / redwood conifer leg | a two-lane mountain road threading tall dark conifers and granite, dappled low light through the trees, a sliver of bright sky above the canopy, the road curving gently up-and-away into the pines |
| **`winding_mountain_pass`** | climbing a Sierra/Wasatch grade | a switchbacking mountain-pass highway cut into a granite grade, guardrail and a sheer drop on one side, ridgelines stacking into haze, a bright cold sky; the road sweeps up and to the left toward a notch in the peaks |
| **`mountain_pass_snow`** | the pass when it's snowing / chains weather | the same alpine switchback under fresh snow, snow-laden conifers, plowed banks along a slushy lane, low flat storm light, a pale luminous sky; the road barely readable, climbing into white |
| **`interstate_vegas`** | the **first leg out of the Strip** (the "we're on the run now" establishing shot) | a wide multilane interstate (I-15) southbound leaving Las Vegas at blue hour, the casino skyline and neon glow receding small on the horizon behind, brake-light-free open lanes ahead opening into dark desert, big dusk sky |
| **`coast_road`** *(bonus)* | a Highway-1 / Big Sur coastal leg | a cliffside two-lane hugging the Pacific, fog rolling off a dark ocean far below, a bright marine sky, the road curving along the headland; ocean and sky bright, the cliff and road dark |
| **`redrock_road`** *(bonus)* | a UT/AZ red-rock canyon leg (Zion/Moab/Monument Valley country) | a desert highway running between towering sandstone buttes and mesas, layered canyon walls, a bright high-desert sky, the road threading the rock toward a distant gap |

### 4.2 Parked / context backgrounds

| id | when it shows | SUBJECT (append to §1) |
|---|---|---|
| **`at_gas_pump`** | parked at any working pump (replaces `gas.png`) | a lonely desert fuel island at dusk — a lit pump canopy, a single set of pumps, a tall illuminated price/brand sign, the dark desert and a bright dusk sky beyond; a flat empty forecourt across the foreground for the car to pull onto; no vehicles |
| **`at_gas_pump_night`** | the pump after dark | the same desert fuel island deep at night, the canopy fluorescents and price sign glowing hard against a black desert and a star-bright sky, wet-looking dark forecourt foreground |
| **`strip_mall_lot`** | parked in a generic town/city lot (replaces the parked use of `drive_city`) | a sun-bleached American strip-mall parking lot at golden hour — a low row of anonymous storefronts and signage across the back, light poles, palms or a water tower, a wide flat empty asphalt lot in the foreground; bright sky, dark storefronts; no parked cars in front |
| **`parking_garage`** | stashing the hot Z under cover in a camera-heavy city | the interior of a concrete multi-level parking structure — rows of square pillars and low ceiling, fluorescent strips, a bright ramp opening to daylight at the far end, empty painted stalls; a clear empty bay in the foreground; claustrophobic, cool, shadowed |
| **`motel_row`** *(replaces `motel.png`)* | a roadside-motel / sleep stop at night | a classic roadside motor-lodge at night — a tall mid-century neon motel sign (no legible letters), a low lit office and room doors along a covered walk, a dark empty front lot, a deep night sky; warm lit windows against dark |
| **`snow_stuck`** | snowed-in / stranded by cold (bad-luck "you got stuck" frame) | a lonely mountain pull-off buried in fresh snow under a flat white storm sky, drifts across an unplowed road, dark pines weighed with snow, tire tracks petering out; bleak, quiet, stranded; a snow-covered flat foreground |
| **`shoulder_stranded`** *(improves the existing `stranded`)* | out of gas / broken down on the shoulder | a desolate desert highway shoulder at dusk, the empty two-lane stretching to a far vanishing point, gravel and a lone mile marker, a vast indifferent sky going dark; nobody coming; gravel foreground |
| **`rest_overlook`** *(bonus)* | an off-grid pull-off to sleep in the car | a dirt scenic overlook off a desert highway at blue hour — a low guardrail or rock edge, a valley of distant town lights far below, a huge star-emerging sky; a flat gravel pull-off in the foreground; calm, safe, alone |

**Priority:** the **6 bold core ids** (`desert_road`, `winding_mountain_pass`, `at_gas_pump`,
`strip_mall_lot`, `parking_garage`, `snow_stuck`) ship first and prove the look; then the
night/snow variants; then the *bonus* set. ~16 plates total. If a few feel redundant after the core
6, cut from the bonus tier — Claude will note any that go unwired.

---

## 5. How Claude wires it (so you know the constraints are real)

You don't touch code — but here's the contract your art plugs into, so the composition rules above
aren't arbitrary:

- Selection lives in `frontend/scenes.js`. The per-POI plate (`scene` field → `wm_<poi>`) **always
  wins** — your ride backgrounds only fill the **open-road / generic-context gap** that the
  procedural `drive_*` loops fill today (the final fallback at `sceneIdFor` → `_driveEnv`, scenes.js
  ~line 1106). Claude swaps that fallback for a `_contextBg(snap)` resolver that returns these ids.
- **Already-available signals** (no backend work) pick most of them: `kind` (`gas`/`city`/…),
  `region` (`NV`/`CA`/`AZ`/`UT`), `services`/`gas_price` (a working pump), `weather.snowing` /
  `cold_start_needed` / `battery_dead` / `storm` (→ `snow_stuck`), `status==='stranded'` (→
  `shoulder_stranded`), and **`hour`** (→ the `_night` suffix). Day/night is the highest-leverage,
  zero-backend addition — that's why several plates want a night twin.
- A few want a **new backend signal** Claude will add: a `biome` tag on POIs
  (`forest`/`alpine`/`coast`/`redrock`/`desert`) for `forest_road` / `coast_road` / `redrock_road`;
  a `leaving_vegas`/`first_leg` flag for `interstate_vegas`; a `parked_under_cover` flag for
  `parking_garage`. Until those land, those plates simply won't fire — so they're safe to ship
  early and wire later.
- The car composites at `{ y:196, w:138 }`, bottom-center, **opaque** — which is the whole reason
  for the "calm bottom-center, subject up-and-to-the-sides" rule in §3.

---

## 6. QA checklist (per plate, before `status:"done"`)

- [ ] exactly **320×200**, opaque PNG, **only the 5 cyan-ramp colors** (run it through
      `loc_plate_tool.py qa`)
- [ ] **bright sky / dark land**; clear single subject readable at thumbnail size
- [ ] **no car, no people, no text, no border** survived the dither
- [ ] **bottom-center ~140px strip is calm** (road/lot/floor/ground) — a car-sized sprite dropped
      there would sit cleanly, not cover the subject
- [ ] driving plates: road fills lower-center and recedes; parked plates: flat foreground to park on
- [ ] same locked dither/contrast as `virginia_city` — drop it next to a real `scenes_wm/*.png` and
      it reads as the same set
- [ ] `manifest.json[<id>].status = "done"`

## 7. Deliver

Drop the finished set in `media/transmission/ride/` with its `manifest.json` (+ optional `_qa/`
contact sheets, same as the loc packet) and ping Claude. Claude copies the cyan plates into
`frontend/scenes_wm/ride_<id>.png`, adds the `_contextBg` resolver + the new backend signals, and
ships it to rideordie.badler.ai. **Anchor to match:** `frontend/scenes_wm/virginia_city.png`.
