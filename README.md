# FAIRLADY ◇ 240Z

A free-roaming, retrofuturistic text road-trip across the American West, played in a CRT terminal.
You drove a talking 1972 Datsun 240Z — **FAIRLADY** — off the SEMA show floor at 5:37 PM on Friday,
November 7, 2025. She isn't magic: a little stack of compute behind the dash gave her a voice and a
map of every street address and most points of interest in **Nevada, California, Arizona, and Utah**.
Now it's the two of you, a 40-liter tank, ~20 miles to the gallon, a credit card that leaves a trail,
and a car somebody already reported missing.

Point her at Zion straight off your opening splash of gas and you'll end the night stranded on the
shoulder in a car you can't report stolen. The whole game is that tension: **fuel, money, nightfall,
and heat.**

> _"Buy some gas before you point me at the horizon, or we'll be a very pretty paperweight on the shoulder."_

---

## Run it

```bash
./run.sh                       # plays fully offline (deterministic stub narrator), real OSM routing
FAIRLADY_ADAPTER=ace ./run.sh  # FAIRLADY's real voice: Nemotron Nano + Kokoro via rop1's Ace stack
```

Open **http://127.0.0.1:8739/**. Type commands, or just talk to her.

> Live OSM routing needs Python built against **OpenSSL 3.x**. macOS system Python ships LibreSSL 2.8
> and fails the TLS handshake to the OSRM/Nominatim demo servers — use Homebrew `python@3.12+`
> (`PYTHON=/opt/homebrew/bin/python3.12 ./run.sh`). On Linux (rop1) the default Python is fine.

### How you play — voice first

The interface is **Where in the USA is Carmen Sandiego?** in SOUL Interface cyan: a location chip + day/time
chip, a framed dithered graphic of wherever you are, a compact dash, and a text panel. **There is no
button grid** — you *talk to her* (🎤, browser speech here / Ace `/asr` in production) or type as backup.
She answers, narrates, and the world only renders what the engine knows is true. Things you can say:

```
drive to <place>      'drive to zion', 'go to the petersen', any NV/CA/AZ/UT address. 'fast' to push it.
drive me home         she'll take you to the Oakland garage (her home) — or "home is <place>" to set yours
fill / gas $20 / 30 L  buy fuel (40 L tank, ~20 mpg, ~211 mi full)
pay cash | pay card    cash leaves no trail; the card does
sleep / motel          rest for the night — you must, most nights
talk                   speak with the locals where the language isn't English
who owned you before / where were you born / where'd you grow up   — her story, filled in over time
map / look / tow / new
```

---

## How it's built

```
backend/
  app.py              FastAPI: serves the terminal + game API
  config.py           every tunable knob (physics, economy, heat, env overrides)
  engine/
    state.py          GameState — the single source of truth
    rules.py          deterministic core: driving, fuel, time, heat, sleep, the law
    world.py          POI registry + real OSM geocoding/routing (cached, offline fallback)
    economy.py        gas pricing, fueling math, cash-vs-card
    commands.py       intent parser (the LLM never decides what happens)
    game.py           orchestration: new game, snapshots, suggested moves, turns
    save.py           JSON save/load
  adapters/
    base.py           Narrator interface
    stub.py           offline, deterministic FAIRLADY (default; powers the tests)
    ace.py            rop1 Ace stack: /chat (Nemotron+Kokoro), /translate_speak (Japanese NPCs)
  content/
    pois.json         128 hand-verified POIs with real coordinates (+ Easter eggs + lore origins)
    voices.json       Kokoro female voice per language
    car.json          the 240Z spec + FAIRLADY's persona
    intro.md          the SEMA opening
frontend/
  index.html crt.css terminal.js   the cyan-phosphor CRT terminal (no build step)
  retro.js                         320x200 monochrome scene engine: 5x7 font, Bayer dither, anim loop
  car_sprite.js                    Ace, digitized from Ben's real photo (baked PNG + anchor points)
  scenes.js                        prop sprites + drawAce (the hero) + 40+ location backdrops
tools/make_car.py     build tool: photo → cyan pixel sprite (posterizes, bakes car_sprite.js)
backend/tests/        33 deterministic-core tests
```

### The one rule that makes it work

**The engine owns all state; the LLM only narrates it.** Every turn, the deterministic rules compute
fuel burned, miles driven, money spent, time passed, and heat gained, then hand the narrator a *snapshot*
plus plain situational cues. FAIRLADY (Nemotron) writes one or two sentences of voice on top — she can
recite the true range when asked, but she can never invent a full tank or move the car somewhere it
didn't go. The dashboard is always real.

### The math

- **Tank:** 40 L. **Economy:** 20 mpg. 1 gal = 3.78541 L → **~211 mi on a full tank.**
- Each mile burns `(3.78541 / 20)` L ≈ 0.189 L, times a terrain multiplier on mountain legs
  (Zion, Tioga Pass, Bryce…) and 1.15× if you push hard.
- **Gas** is priced per region (NV ~$4.25, CA ~$4.95, AZ ~$3.95, UT ~$3.89/gal), with per-POI
  overrides (Death Valley charges $6.49). You can buy by dollars, gallons, liters, or `fill` — and
  you can only put 40 L in a 40 L tank.

### Nothing goes to plan — the drama engine

`engine/drama.py` throws complications during drives, deterministically (seeded) but scaled by heat,
mileage, days out, and how close you are to home: she **overheats on a grade**, a cruiser **runs the
plate**, a town **recognizes the car** (a gift, or a witness with a phone), a **gremlin** in the inline-six
makes her limp and thirsty, a **pass closes** and the detour costs you fuel. The engine hands the LLM a
dramatic *cue*; Nemotron (or the offline stub) plays it. That's the compute-heavy part — real narrative
drama on a Blackwell.

**Trust is earned, not dumped.** Ask "who owned you before" early and she's **coy** — "you'll have to earn
it." It surfaces a guarded mile at a time, and the truth only comes out where it's kept: arriving certain
towns triggers set-piece reveals — **Monterey** (the aquarium + memories of 2025 Car Week), **Long Beach**
(the tale of **Mayumi**, a Hagerty Cherished Salvage Story), and finally the **storage unit in Livermore**,
where what's left of her — and the truth — has been waiting. Each told once. Tell her **"drive me home"**
and she heads for the Oakland garage, slowing the closer she gets.

### The pressure axes

- **Fuel** — run dry between stations and you're stranded. A `tow` is the only escape, and it's
  expensive and very hot.
- **Money** — a credit card (limit $2,000) and a little cash ($40). The card is unlimited-ish but
  every swipe leaves a paper trail; cash is clean but scarce.
- **Nightfall** — push past ~20 hours awake and she refuses to drive on until you sleep. Lodging
  costs money and lies you low; a rough night in the seats is free but draws an eye.
- **Heat** (0–100) — the stolen-car meter. Card swipes, pushing hard, and lingering raise it;
  distance, crossing state lines, and lying low lower it. Past 45, patrols take interest; past 90,
  roadblocks — and they run the plate.

### Retro scenes

Every location draws an animated monochrome scene in the panel beside the terminal — Apple II / C64
class: a 320×200 logical screen, one hue in a few tints, Bayer-dithered shading, a hand-built 5×7
bitmap font, chunky pixels. The hue is **SOUL Interface cyan** (`#38d6ec` on `#0e0c0a`, lifted
byte-exact from the brand site) — the game is meant to read as an Ace / SOUL Interface artifact, the
koi-CRT posterization in motion. Type is IBM Plex Mono (body) and Space Grotesk (display), the wordmark
carries 心 and the ace of spades, and the scene bezel uses the site's exact `恋の矢` CRT recipe (cyan
bloom + inset vignette). It opens on a **power-on splash** — a glowing cyan koi over 心 連繋 and FAIRLADY
in Space Grotesk, with the site's `crtOn` warp — that settles into the terminal.

The hero is **Ace** herself, **digitized from Ben's real photo** of the car — rendered as **1-bit cyan
ink** ("there or not there," no gradient dither, the koiNOya look; a denoise pass for the clean "we only
had 16 MB" feel). `tools/make_car.py` hard-thresholds the photo and bakes a ~4 KB `car_sprite.js`. The
same sprite rides the lower foreground of every scene — rear-3/4, with a **driver's-side fender bullet
mirror that glints as she drives**, wearing her real Nevada **CARTALK** plate. Generic travel uses three
**scrolling pseudo-3D highway loops** — **desert / city / mountain** — where the road rushes to the
horizon and the world (mesas, skyline, peaks, poles, pines) sweeps past while the one car stays put. To
re-bake from a new photo: drop it at `/tmp/z_src.png` and run `./.venv/bin/python tools/make_car.py 188 --bake`.

**Life of a Show Car.** Ask her "where were you born?" or "where did you grow up?" and she'll tell you
— and reveal the places: **koiNOya**, the Edo-relic shop in Richmond where she was switched on, and the
**AiSha garage** in 1926 downtown Oakland where she was built. Born in Richmond, raised in Oakland,
debuted at SEMA, stolen on a romantic whim. The whole game is a two-hander between the show car and the
schmuck who took her.

40+ bespoke scenes: the gas station (nixie clock reads **5:37**), Grand Canyon, Zion, Bryce, Arches,
Death Valley (heat-shimmer + the world's tallest thermometer), Great Basin under the stars, Monument
Valley, Yosemite, Joshua Tree, the **Hollywood** sign with sweeping searchlights, the **Bay Bridge**
and Golden Gate in fog, the Vegas Strip (Luxor beam + turning High Roller), the **Sphere** (a giant
blinking eye that watches you), **Fallon** (F-18s tearing across — TOPGUN country), Area 51 / the ET
Highway (a UFO and the black mailbox), Bonneville salt flats (Ace flat-out with a ticking MPH),
Laguna Seca's Corkscrew, SF Japantown (pagoda + swaying lanterns), a stranded-on-the-shoulder screen,
and more. Anything without a bespoke scene falls back by kind (park/track/amusement/city/gas/encounter)
so coverage is total. Easter eggs are sprinkled throughout: the recurring 5:37, a license plate that
reads 537, and a camera flash in the dark — Larry Chen, still looking for her.

### Voices

FAIRLADY speaks English (`af_heart`). Drive to a place where the language isn't English and `talk`:
the local answers in **their** language, in their own Kokoro voice. **San Francisco Japantown and
Little Tokyo are fully voiced today** via Ace's `/translate_speak` (real Japanese text + audio).
Spanish, Mandarin, Hindi, Italian, French, and Portuguese encounters show real native text from
Nemotron; set `FAIRLADY_KOKORO_URL` to any OpenAI-compatible multi-voice Kokoro server to voice
those too.

---

## Test

```bash
cd backend && FAIRLADY_ROUTING=offline FAIRLADY_ADAPTER=stub ../.venv/bin/python -m pytest -q
```

28 tests cover the Zion trap, the 211-mile full-tank range, fuel/tank/credit math, the cash-vs-card
heat economy, state-line cooling, the nightly-sleep gate, the tow rescue, the parser, and an
end-to-end turn — all network-free.

---

## License & copyright

Copyright © 2026 **Benjamin J. Adler**. All rights reserved. Published as a portfolio
showcase (a buried easter egg of [badler.ai](https://badler.ai)) — **source-visible, viewing only**.
See [`LICENSE`](LICENSE). The car ("FAIRLADY" / "Ace"), the writing (the *Mayumi* storyline and all
in-game prose), the digitized sprite, and the SOUL Interface marks are the author's; please don't reuse
them without permission. Built with [Claude Code](https://claude.com/claude-code).
