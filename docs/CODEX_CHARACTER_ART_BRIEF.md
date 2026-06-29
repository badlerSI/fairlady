# CODEX BRIEF — RIDE OR DIE *character & set-piece* art (batch 2)

Three new plates the new story beats need. Same **exact pipeline** as your location plates and the
ride-backgrounds brief — **320×200, opaque, the 5-color cyan-ink dither, anchored to
`frontend/scenes_wm/virginia_city.png`** (see `CODEX_RIDE_BACKGROUNDS_BRIEF.md` §1–§2 and
`CODEX_LOCATION_PLATES_BRIEF.md` §4 for the verbatim style block + the ImageMagick/`loc_plate_tool.py`
post-process). The only thing different here is the **subjects are characters**, not environments —
and unlike the ride backgrounds, **the car sprite is NOT composited over these** (Claude wires them
as full-panel scene swaps), so you may fill the whole 320×200 frame.

Palette (cyan rest, the only 5 colors): `#0e0c0a #13262a #1f6f7d #38d6ec #b8f4ff`. Keep the
bright-sky/dark-ground tonal split (here: a luminous subject out of a dark field) so the dither ramp
reads. `no text`, `no border/frame`, `no logos`. Cyan plate only — no `_4c` needed (these aren't map
tiles).

Deliver to `media/transmission/char/` with a `manifest.json` keyed by `<id>` (same schema as the loc
manifest). Filename `roi_char_<id>.png`.

---

## The three plates

### 1. `dream_ace` — the cyan woman who turns out to be Ace
**Used by:** the one-shot sleep dream (the 4th real-bed night). The cyan dream-woman dissolves and
it's **HER — Ace, as a person, with a face**, asking the driver not to sell her. *This is the first
and only time Ace is ever drawn as a human figure rather than the car* — it's the emotional hinge of
the whole love story, so it's the showcase plate.

> **SUBJECT:** a dream apparition of a young woman rendered in pure cyan light, as if she stepped out
> of a screen or out of sleep — calm, knowing, a half-smile, looking directly at the dreamer; close,
> head-and-shoulders, emerging from a deep black void with a soft cyan bloom around her. **A small
> tattoo curls up the left side of her neck** — keep it legible: a hand-inked **black spade (♠)** with
> a fine vine/linework tail climbing toward the jaw (the spade is Ace's emblem — it's hand-laid on the
> car's flank). Ethereal, intimate, a little haunting; she is made of the same cyan ink as everything
> else in this world. Bright luminous face/figure, near-black surround.

Notes: head-and-shoulders, centered, filling the upper two-thirds; the neck + spade tattoo must read
at thumbnail size (it's the whole point). Dreamlike soft edges are fine but keep the hard cyan
banding. No car.

### 2. `alma` — the femme fatale in the booth
**Used by:** the Vegas club reveal, the desert-hitchhiker pickup, and (optionally) as the dream
apparition before she resolves into Ace. One portrait, reused everywhere Alma appears.

> **SUBJECT:** a dangerous, beautiful woman in a dark Vegas back booth, lit from one side by cyan
> neon — "like she stepped out of a screen," smoke curling, a low tumbler in one hand, watching the
> viewer with amused, half-lidded appraisal; a half-step ahead of you and bored of most men. Glamour
> and threat in equal measure, tenderness only at the edges. Head-and-shoulders to mid-torso, the
> booth and bar-light falling away into dark behind her. She is NOT the dream-cyan of Ace — give her
> warmer modeling within the same 5-color ramp (more mid-teal skin tones, a hotter cyan rim light),
> so she reads as flesh-and-blood where dream-Ace reads as light. Bright face, dark surround.

Notes: she should look like a *real woman* (contrast with dream-Ace's apparition). No tattoo. No car.

### 3. `mayumi_shell` — the burnt-out 240Z
**Used by:** the desert-hitchhiker scene (the loaner that caught fire on the shoulder) and the
Livermore storage unit (Mayumi's scorched shell under a tarp — the previous car, the owner's grief).
One charred-husk plate serves both.

> **SUBJECT:** the burnt-out shell of a 1970s Datsun 240Z on a desert highway shoulder at cyan dusk —
> a scorched, gutted fastback, paint blistered to bare metal, glass gone, still ticking heat, a thin
> ghost of smoke; a long flat desert and a luminous dusk sky behind, the empty two-lane running off
> to a vanishing point. Desolate, quiet, a little mournful — a beautiful car reduced to a black
> skeleton. Bright sky, very dark wreck. (A second framing note for the Livermore use: it also reads
> as the same shell parked indoors under a half-thrown canvas tarp in a concrete storage unit — if
> you want to ship a `mayumi_shell_tarp` variant for that, great, but the desert version is the
> priority.)

Notes: a real wrecked-car silhouette, recognizably a 240Z fastback. Lower-center can hold the wreck;
keep the sky bright for the ramp.

---

### 4. `sema_back_hall` — the back of the North Hall (NO hero car)
**Used by:** the opening scene at `sema_north_hall`. The current plate is a stock photo of *another*
240Z on a turntable, so Ace's sprite composites on top → two cars, wrong setting. Replace with the
real spot: the **dead end of the North Hall, Automotive Electronics**, where nobody's voting on the
cars — **and crucially NO featured car in the frame** (Ace's own sprite is the only car; she sits
bottom-center over this).

> **SUBJECT:** the far back corner of a huge convention-center hall after the show's over — Automotive
> Electronics aisle: half-broken-down booths, backup-camera and subwoofer tables, a banner, hanging
> work-lights and the big dark ceiling trusses, a polished concrete floor reflecting the cyan light,
> the empty main floor receding behind. Late, emptied out, fluorescent-and-dusk. **No cars, no people
> in the foreground** — just the room. Keep the lower-center floor clear and calm (Ace parks there).

This one IS composited under the car (like a ride background) — leave the bottom-center clear.

---

## QA + wiring

- Per plate: exactly **320×200**, opaque, only the 5 cyan-ramp colors (`loc_plate_tool.py qa`); bright
  subject out of a dark field; reads at thumbnail; `dream_ace`'s neck-spade legible; no text/border.
- Deliver `roi_char_<id>.png` (+ manifest) to `media/transmission/char/` and ping Claude. Claude
  copies them to `frontend/scenes_wm/` and wires the scene swaps: `dream_ace` shows on the dream turn
  (the engine already sets `dream_scene='ace'`), `alma` shows on the club/hitchhiker reveal, and
  `mayumi_shell` replaces the live-car sprite in the Livermore storage scene + the hitchhiker's
  burnt-car beat. **These three are full-panel — Claude suppresses the car sprite over them.**
- Anchor to match: `frontend/scenes_wm/virginia_city.png`.
