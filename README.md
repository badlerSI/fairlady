# RIDE OR DIE ◇ 愛車

*Aisha (愛車) does not translate to "love car." The only honest translation is the thing you're
about to agree to.*

A free-roaming, retrofuturistic text road-trip across the American West, played in a CRT terminal.
It opens on the SEMA show floor, twenty minutes to close, at the white 1972 Datsun 240Z everybody
stops at — **FAIRLADY**, 270 lb-ft of torque, ace of spades on the hood, and a placard that doesn't
mention she talks. Talk to her a while (ask real questions about her build and she warms up fast)
and she'll ask one simple favor: *take her down the block to fill up with gasoline, so she's ready
to head home after this nightmare that was SEMA.* Then she'll ask again. Then she'll beg.

Say yes — that's the title drop — and it's the two of you: a 40-liter tank, ~20 miles to the gallon,
a credit card that leaves a trail, a car somebody is about to report missing, and an owner who will
come looking. She isn't magic: a little stack of compute behind the dash gave her a voice and a map
of every street address and most points of interest in **Nevada, California, Arizona, and Utah** —
your onboard GPU with GPS, and she keeps the saves.

Point her at Zion straight off your opening splash of gas and she'll do the math out loud and
refuse — once. Insist, and you'll end the night stranded on the shoulder in a car you can't
report stolen. The whole game is that tension: **fuel, money, nightfall,
and heat.**

> _"Buy some gas before you point me at the horizon, or we'll be a very pretty paperweight on the shoulder."_

---

## Run it

```bash
./run.sh                       # plays fully offline (deterministic stub narrator), real OSM routing
FAIRLADY_ADAPTER=ace ./run.sh  # FAIRLADY's real voice: Nemotron Nano + Kokoro via rop1's Ace stack
```

Open **http://127.0.0.1:8739/**. Type commands, or just talk to her.

**Putting it on the web** is one step: it's a single FastAPI app that serves both the API and the
UI on one origin, and it's **multi-user** — every browser gets a session cookie keying its own game
(own save slot, rewind checkpoints, and Ace voice-memory), so it's safe behind `uvicorn --workers N`.
See [`deploy/`](deploy/README.md) for the rop1 kit (systemd unit, Caddy/cloudflared + TLS, env).

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
where can we get to on one tank?   the range question — answered with real math, like everything
pay cash | pay card    cash leaves no trail; the card does
sleep / motel          rest for the night — you must, most nights
talk                   speak with the locals where the language isn't English
who owned you before / where were you born / where'd you grow up   — her story, filled in over time
i have $300 cash | withdraw $2000 | explore   claim what you carry · ATM (<$10k) · the glovebox ($500)
parts / sell the carbon hood   strip the build off her for cash (a cheap stock part goes on)
buy her | offer $5000   come to terms with the owner — the GOOD ending; unlocks legal race / show
race | show            once she's yours: run a real track, or enter the show field — legal, by name
heat | heat report     pull the credit-karma dashboard: your band, your marks, what's helping
lie low | untag        cool off at a quiet spot · scrub a fresh Instagram tag
book an airbnb         a private stay, cash, off the record (vs a traceable motel)
disarm / draw          (Desperado) go for an armed clerk's gun; once you're armed, force your way out
bet $1000 on <team>    gamble at the Vegas/Reno tables (rewind a loss and re-roll — the cheat)
rob the bank           (armed only) a Desperado heist — big take, big heat
flirt / compliment her  pick up a date anywhere there's a crowd; she gets jealous
camo / uncamo          dress her down to lie low (one notch quieter), or flaunt the show car
flash the lights · play music · text   her tricks — text needs WiFi; music cools a jealous sulk
upgrade her            the SECRET, once she's yours and home at the AiSha garage → self-driving Ace
let her drive to <place>   after the upgrade, she takes the wheel: no fatigue, never a ticket
passes                 which mountain roads the snow's closed (the calendar matters now)
cross the border · ship out · buy a pardon · retire   the ways the road ENDS — and ends well
scorecard              your running tally + the awards you've earned
rewind | branches | branch N   fold the timeline back; list checkpoints; jump to any one
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
    prologue.py       the favor — the SEMA show-floor opening; she asks, then begs
    encounters.py     talk-your-way-out: stops, the owner, the standoff (Desperado), the buyout
    heat.py           the heat-as-credit-score model: factors dashboard, Instagram tags, visibility
    garage.py         the economy: cash claims, ATM, glovebox, parts, racing, shows, going legit
    dating.py         pick up a date of any gender; the car gets jealous if she's watching
    endings.py        the ways out (border / container / pardon / retire) + the final scorecard
    season.py         the descending snow line that closes the high passes as winter comes
    gadgets.py        Z camo, her WiFi tricks (text/lights/stereo), and the self-driving secret
    game.py           orchestration: new game, snapshots, suggested moves, turns
    save.py           JSON save/load
  adapters/
    base.py           Narrator interface
    stub.py           offline, deterministic FAIRLADY (default; powers the tests)
    ace.py            rop1 Ace stack: /chat (Nemotron+Kokoro), /translate_speak (Japanese NPCs)
  content/
    pois.json         251 places: 130 hand-verified POIs + the 122-town gazetteer (judged beats)
    voices.json       Kokoro female voice per language
    car.json          the 240Z spec + FAIRLADY's persona
    intro.md          the SEMA opening
frontend/
  index.html crt.css terminal.js   the cyan-phosphor CRT terminal (no build step)
  retro.js                         320x200 monochrome scene engine: 5x7 font, Bayer dither, anim loop
  car_sprite.js                    Ace, digitized from Ben's real photo (baked PNG + anchor points)
  scenes.js                        prop sprites + drawAce (the hero) + 40+ location backdrops
tools/make_car.py     build tool: photo → cyan pixel sprite (posterizes, bakes car_sprite.js)
tools/make_scene.py   Wikimedia lead image → 320×200 koiNOya-ink sketch (frontend/scenes_wm/)
tools/gazetteer_*.py  fetch Wikipedia facts/images · merge towns+beats+scenes into pois.json
tools/play_cli.py     parallel-safe playtest driver (the ML-experiment harness)
deploy/               rop1 production kit: systemd unit, Caddy/cloudflared proxy, env, README
backend/tests/        151 tests (engine + web)
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

### Talk your way out — stops, the owner, Riz, and the rewind

Sometimes the lights actually come on, and you're **pulled over in an unregistered SEMA show car
that talks**, with no wallet — it's in a drawer back at the North Hall. The stop is a real
conversation: a deterministic rubric in `engine/encounters.py` scores what you actually said
(courtesy, the truthiest cover story, gearhead cred — knowing her build plays well with a certain
kind of cop), seeded dice settle the gray middle, and the LLM only narrates. Outcomes run from a
wave-off to a ticket to a BOLO to busted — and fleeing is exactly as smart as it sounds.

**The owner comes looking.** Work the card too hard for too many days and the man who built her is
waiting at the next pump island. He's not there to fight; he's there to ask *why her*. He knows true
love with cars — and what you two have is it, if you can say so out loud. (He's pining for someone
else entirely. It all comes out in due course, like the best early-90s light novel games.)

### The timeline — branch like code, but the loop has limits

She keeps the saves, so a dead end is rarely final — but you can't brute-force *everything* anymore.
Checkpoints land on a **navigable timeline** (`branches` lists them; `branch 3` or `rewind to mesquite`
jumps to any). Plain `rewind` folds to the most recent. Batter the **same** wall over and over and the
cost climbs (−2, −3, −4 Riz…) until the loop simply **won't fold there** — *"same wall, same wreck; the
thing that doomed us happened further back."* Sometimes you genuinely are too screwed, and the way out
isn't hammering one minute — it's branching back to a decision that still had a choice in it.

### Raising the $80k — gamble, strip, or rob

She's insured for **$100k**, and the owner won't sell under an **$80k** floor (knowing Mayumi and real
Riz bring his number down toward it; stripping the build pushes it up). So buying her is a heist-scale
goal — you have to *plausibly raise it.* The honest scraps (claim cash, ATM under $10k, sell parts off
her) don't get you there alone. The fun way: **gamble** at the Vegas/Reno tables (`bet $2000 on the
raiders`) — and since a losing bet is the one thing the loop can take back, you `rewind` losses and
re-roll. It's the sanctioned cheat on sports betting: grind $5k → $80k in a handful of all-in bets, at
the cost of all your Riz. *Money for style.* There's also a number, if you ever find it, that the owner
can't refuse. And if you went **Desperado**, you don't buy cars — you `rob the bank` (armed only; big
take, the whole county hunting you, each bank readier than the last).

### Dating — and a jealous car

You can `flirt` and pick up a date of any gender wherever there's a crowd — it's good for your Riz. But
the car is a stack of compute that never sleeps, and she gets **jealous**, escalating from *"don't mind
me, I'll just idle here and witness"* to a loud, conspicuous rev right when you don't want eyes on the
plate. `kill the engine` to do it where she can't watch; `compliment her` to cool it down; driving turns
her right back on.

### Heat is a credit score — learn to read it

HEAT is your notoriety, and it works like Credit Karma. Pull the dashboard any time (`heat report`)
and it reads like a credit report: a band (**GHOST → NOTICED → TRENDING → FLAGGED → MOST WANTED**),
your **derogatory marks** (each one showing how many clean miles until it ages off) against what's
**in your favor**, a what-if line, and a "do this" lever. Every point is attributable to a choice —
nothing drips on a timer.

- **A credit card swipe is a derogatory mark** — traceable, it ages off over about a tank of clean
  miles. Paying **cash** is clean (but cash is finite — that's the squeeze). An **alias `airbnb`**
  (cash, no front desk) lies you low; a **motel on the card** is another mark.
- **It's a visibility problem, not abstract crime.** Park the flashy show car somewhere
  **paparazzi-bright** — the Strip, Hollywood, SF — and exposure climbs. **The car watches her own
  Instagram**, and a stranger geotagging her (`@coffee_and_cars_no_filter` and friends) is a big
  spike — *"we went viral, NOT the good kind."* It's always telegraphed ("phones everywhere") and
  dodgeable (keep moving), with counterplay (`untag` to DM the poster), and it never fires anywhere
  low-key. **The curious gas-station clerk** is the same in miniature: play it humble and slide by,
  show off and he posts you.
- **There's always an active way down** — pay cash, `lie low` at a quiet spot, book under an alias,
  cross a state line and run clean miles. Waiting is the worst option, not the only one.

The design is grounded in a research pass on what makes notoriety mechanics fun vs tiresome (Sid
Meier's interesting-decisions, NFS Heat's risk/reward, GTA's readable bands, Credit Karma's factor
dashboards) — see `TRANSFER.md`.

### Coming to terms — buy her, and go legit

There's a way off the run that isn't a gun. The economy is **trust-the-player**: tell her what you're
carrying (`i have $2000 cash` — any reasonable amount), hit an **ATM** for anything under $10k, and if
you claim you're broke, there's **$500 in the glovebox** when you `explore`. Short on funds, you can
**sell the build off her** — the carbon hood for a stock 280Z steel one, the triple Mikunis for a
single Hitachi, the deep-dish wheels for steelies — each `sell` puts cash in your hand and a cheaper
part on the car (and quietly tanks her value and her show-worthiness).

Scrape together enough and, when the owner comes looking — or when you `drive me home` to the Oakland
garage after meeting him — you can **`buy her`**. He doesn't sell at market; he sells to someone who'll
love her, for a price that drops the more you've shown him (knowing Mayumi, real Riz). Come to terms
and it's **the good ending**: the title's yours, **Heat is gone for good** (`no-heat` mode), and the
running is over. Now you can do it all in the daylight — **`race`** her on a real circuit (Laguna Seca,
Willow Springs, Sonoma…) or **`show`** her on a museum lawn or at Monterey, legal, with your name on
the entry. Keep the build whole and she wins the lawn; strip her for the buy-in and she'll still race,
but she can't win a concours stripped. Your call.

### The ways out — and it ends well

The run has to **end**, and not just on the shoulder with a dry tank. Buying her (above) is one ending
that lets you keep playing — free roam, racing, sightseeing, like post–Elite Four. The others are
escapes you can take while you're still hot, each rolling a **scorecard**:

- **`cross the border`** — drive south to Nogales, Calexico, San Diego, Yuma, and roll into a country
  that's never heard of a plate reading CARTALK. Gone, clean. (Needs a little fuel in the tank.)
- **`ship out`** — at a deepwater port (Long Beach, San Diego, the Bay), a no-questions **shipping
  container** and a forged manifest carry you and her overseas to a new name. **Ends Desperado mode.**
- **`buy a pardon`** — at a state capital, since this is a farce, **$50k cash** in a nice envelope makes
  a stolen car a clerical error with a gold seal on it. Money is the only language the state speaks.
- **`retire`** — once she's legally yours (or self-driving), call it whenever you like and roll credits.

Every ending — win **or** lose (busted, stranded, taken) — prints **THE RIDE**: days, miles, cash, peak
heat, towns, wonders, bank jobs, dates, the **awards** you earned (The Ghost, Most Wanted, Heartbreaker,
Ride or Die, The Sevens, She Told You Everything, The Ghost in the Dash…), a **final score**, and a
**rank**. `scorecard` shows the running tally any time.

### Seasons — the mountains close

The clock starts **Nov 7**, and it matters now. As winter rolls in, a **snow line descends** and the high
passes shut in elevation order — **Tioga first**, then the Sierra high country, the Wasatch, the North
Rim — until by New Year's fourteen of them are chained and gated. You can't `drive to` a snowed-in pass;
`passes` reports what's closed and what's about to. Early November is a window; dawdle, and the map
freezes around you — which bites hardest on a **Desperado who has to burn days lying low**.

### Her gadgets — and the self-driving secret

She's a stack of compute with a voice and a map, not (out of the box) a robot. She can wear **Z camo**
(`camo` / `uncamo`) — a tarp, road grime over the spade, a junk plate over CARTALK — to drop one notch
off how exposed she is everywhere it counts (a flashy full-tilt push shakes it loose). On **WiFi** she
can **`text`** (and read a little road recon back), **`flash the lights`** (a wink in the dark — or the
wrong kind of loud in a crowd), and **`play music`** (which, conveniently, talks her down off a jealous
sulk). What she *can't* do is drive herself — `let her drive` and she'll tell you the wheel's still
yours… **unless** you find the secret: once she's **legally yours** and you bring her **home to the
AiSha garage** where she was built, the cats who made her will **`upgrade her`** the rest of the way.
After that, **`let her drive to <place>`** and she takes the wheel — no fatigue on you, never a ticket,
the strangest and freest ending the road has.

### Desperado Mode — armed and dangerous

Lean on the clerk at a manned pump — threaten him, act hinky — and his hand comes up from under the
counter with a **pistol**: keep still, he's calling the cops. You can talk him down (clean exit) or
go for the gun (`disarm`). But the grab only lands if you **did it right** — full tank, paid **cash**,
*before* you spooked him — and even then, in the spirit of *Edge of Tomorrow*, you **fail the first
two attempts and get lucky on the third**. The catch: the try-counter **survives rewinds**, so you're
cursed to relive the standoff — fail, rewind, fail, rewind, *win* — until the third grab takes his
gun. That unlocks a **special checkpoint** and **Desperado Mode**: armed and dangerous. Your Heat now
has a permanent floor, the law comes ready instead of waving you off, and you carry a new nuclear
option — `draw` — that forces your way out of any traffic stop at a ruinous, no-going-back cost. The
gun, like Riz, is yours across every timeline; not even a rewind takes you back to before it.

**Riz** is the style ledger: earned by suave wave-offs, taken tickets, asking the right questions
before she ever had to beg, and the owner's blessing. And when it all goes wrong: **rewind** — a bit
of the ol' Edge of Tomorrow. She keeps checkpoints at every clean arrival, every survived night, and
the favor itself; `rewind` folds the world back (twice in a row reaches one checkpoint deeper), it
works even from BUSTED and STRANDED endings — and Riz reverts with the world, minus a small fee:
a timeline that never happened can't pay you, so rewind-loops can't farm style.

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
bloom + inset vignette). It opens on a **power-on splash** — the actual **koiNOya relic-shop artwork** (the brand's
koi-crt posterization, byte-exact from the badler.ai bundle — the shop where she was switched
on) in a glowing CRT bezel over 心 連繋 and RIDE OR DIE in Space Grotesk, with the site's
`crtOn` warp — then settles into the terminal on click (or after a beat).

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

### The gazetteer — every town brings something up

251 places now. Beyond the 130 curated POIs, a **gazetteer layer** covers ~120 more towns across
all four states — every one grounded in a real fact from its Wikipedia article and delivered as
her arrival beat, once per game, in her voice ("Zzyzx. The springs are gone; the name kept the
fever."). The beats were written and refined by an evolutionary loop: three judge panels (voice /
grounding / playability) scored every draft, the winners were distilled into house rules, and
everything under the bar was rewritten against them until the whole set converged (122/122 ≥ 7.5,
nothing invented — if the fact isn't in the article, she doesn't say it). Drive somewhere that
isn't even a POI and she still pulls one true sentence from Wikipedia geosearch (online mode,
cached). **Every gazetteer town and every POI without bespoke pixel art gets a sketch**: the
place's Wikimedia lead image posterized into the 1-bit koiNOya cyan ink at 320×200
(`tools/make_scene.py`, adaptive tonal bands), drawn with Ace parked in the foreground. Sources
and licenses in [`ATTRIBUTION.md`](ATTRIBUTION.md).

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

151 tests cover the Zion trap, the 211-mile full-tank range, fuel/tank/credit math, the cash-vs-card
heat economy, state-line cooling, the nightly-sleep gate, the tow rescue, the parser, the favor
ladder (5 turns of small talk, 3 if you ask about her build), the title drop, checkpoint rewinds,
traffic-stop verdicts, the owner's blessing and the trailer ending, the one-tank range question,
Berlin NV, and an end-to-end turn — all network-free.

---

## License & copyright

Copyright © 2026 **Benjamin J. Adler**. All rights reserved. Published as a portfolio
showcase (a buried easter egg of [badler.ai](https://badler.ai)) — **source-visible, viewing only**.
See [`LICENSE`](LICENSE). The car ("FAIRLADY" / "Ace"), the writing (the *Mayumi* storyline and all
in-game prose), the digitized sprite, and the SOUL Interface marks are the author's; please don't reuse
them without permission. Built with [Claude Code](https://claude.com/claude-code).
