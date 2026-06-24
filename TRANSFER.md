# RIDE OR DIE ◇ 愛車 (FAIRLADY ♠ 240Z) — Transfer / Handoff Document

> A complete brief for a fresh session to **improve** this game without re-discovering anything.
> Repo: <https://github.com/badlerSI/fairlady> (public, © Benjamin J. Adler, all rights reserved).
> Local: `~/Projects/fairlady`. Last updated by the build session on 2026‑06‑10.

---

## 0. What it is (the north star)

A **voice-first, compute-heavy, retrofuturistic terminal road-trip** across the American West. It opens on
the SEMA show floor at twenty minutes to close, where a talking 1972 Datsun 240Z — **FAIRLADY** ("Ace") —
asks you one simple favor: two blocks and a tank of gas. Saying yes is the title drop (see §0.5). Then it's
the two of you on a 40 L tank (~20 mpg, ~211 mi full), a credit card that leaves a trail, and a car
somebody is about to report missing.

Design pillars (do not break these):

1. **The deterministic engine owns ALL state** (fuel/money/time/heat/routing). The LLM **only narrates** a
   snapshot + situational cues. She can recite the true range when asked but can **never** invent a full
   tank or move the car somewhere it didn't go. *The dashboard is always real.*
2. **Voice-first.** The interface is *Where in the USA is Carmen Sandiego?* — a location chip, a day/time
   chip, a framed dithered graphic, a compact dash, a text panel, and a mic. **No button grid.** You talk
   to her; typing is the backup.
3. **Retro graphics + futuristic LLM.** Apple II / C64-class 1-bit cyan art (the "we only had 16 MB" look),
   the SOUL Interface brand cyan, the car **digitized from Ben's real photo**. Drama and voice come from
   Nemotron + Kokoro on an RTX 6000 Blackwell (rop1's "Ace" stack).
4. **Trust is earned.** Her tragic backstory (the previous owner, **Mayumi**) is **coy** and only fully
   revealed at the **storage unit in Livermore**. Never let her volunteer it.
5. **Her map is NV / CA / AZ / UT only.** Everything outside those four states is off her maps by design.

**Status:** fully playable end-to-end, 55 passing tests, 129 POIs, 55 scenes. The narrative prose for
Mayumi/Livermore/Monterey/prologue/owner is a strong *draft* — Ben fills the details.

---

## 0.5 The RIDE OR DIE re-frame (2026-06-10, second session)

The app is now **RIDE OR DIE** — Ben's translation of 愛車 *aisha* ("certainly not 'Love Car'").
The theft is re-framed as **the favor**: the game opens ON the show floor (`sema_north_hall`, new
start POI; the Chevron moved into `pois[]`), where she makes conversation and then asks one simple
favor — two blocks, one tank, so she can head home after the nightmare that was SEMA. New systems,
all engine-owned (the LLM still only narrates):

- **`engine/prologue.py`** — the favor ladder. Counts conversation turns; asks at
  `PROLOGUE_ASK_TURNS` (5), or `PROLOGUE_RAPPORT_TURNS` (3) if the player asks coherent build/spec
  questions (`commands.is_spec_question`; she has **250 lb-ft** — it's in `car.json` and she'll say
  so). Escalates ask→plead→beg→desperate. Agreement = auto-drive to the Chevron + **TITLE_DROP**
  banner. The first full tank there completes the favor and SHE floats the whim ("…or we could just
  not load out"). She won't start for a joyride pre-pact.
- **`engine/encounters.py`** — talk-your-way-out. Traffic stops (`pulled_over` drama event at
  heat≥25; roadblock `law_check` now opens a stop instead of insta-busting): 2 exchanges, a
  deterministic keyword rubric (`score_pitch`) — calm/cover-story(SEMA!)/spec-cred/honest-about-the-
  wallet vs aggro/confession — seeded dice only in the gray middle; outcomes wave-off (+Riz) /
  ticket ($80 or heat) / BOLO (heat+15) / busted. Flee tokens = instant bust. **The owner**: tracked
  via `flags.card_swipes` (counted at every card payment); appears at the next city/gas POI once
  `day≥3` and `swipes≥3` (or `knows_mayumi`). 2 exchanges via `score_owner_pitch` (love/spec/
  saying-Mayumi's-name; offering her back scores negative): blessing (report withdrawn → law_check
  and plate dramas off, heat−30, +15 Riz) / one-week deadline (`owner_deadline_day`) / **taken**
  (new ending, status `taken`).
- **Riz** (`GameState.riz`, in snapshot + dash) — the style ledger. Earned: rapport (+5), wave-off
  (+8 diminishing −2 per prior survived stop, floor 2), ticket (+3), blessing (+15). On rewind it
  **reverts to the checkpoint's value** minus `RIZ_REWIND_COST` (2) — undone timelines can't pay
  (closes the owner-blessing rewind farm found in playtesting).
- **Checkpoints + rewind** (Edge of Tomorrow) — `game.checkpoint()` saves a 2-deep ring
  (`chk1_<sid>`/`chk2_<sid>` save files) on every clean POI arrival, sleep, tow, resolved encounter,
  and the favor. `rewind` (also "go back"/"run it back") restores **in-place** (`__dict__.update`),
  works from ANY status (it's the escape from BUSTED/STRANDED/TAKEN — choices offer it), and a
  second consecutive rewind reaches chk2 (the ring then collapses — chk2 becomes the floor).
  Diegetically SHE keeps the saves ("I keep the saves, ace").
- **`range` verb** — "where can we get to on one tank?" → `game._range_text`: POIs reachable on
  current fuel + after a fill, real winding-road math.
- **Canon revision (Ben, 2026-06-10): Mayumi is a CAR** — the maker's 1970 240Z, his first love,
  the one that should have been at SEMA; she **burned on the I-580**. FAIRLADY was built in the
  grief after and carries some of Mayumi's unburned parts (the Livermore unit-137 reveal — now
  `requires: knows_mayumi`). The maker = the owner who comes looking. She has *no strong feelings
  for her maker* — he sees a ghost when he looks at her; the player is the first to pick her first.
- **New POI + story**: `berlin_nv` (Berlin–Ichthyosaur SP — ghost town + sea monsters, bespoke
  scene). New scene `sema_hall`. §7 P0s all fixed (encounter SPR.city, FONT ♣ + CJK-blank,
  livermore gate, README counts, make_car guard).
- **Old saves**: missing fields default cleanly (`riz=0`, no prologue flags). `new_game(seed,
  prologue_on=False)` gives the classic Chevron start (tests use it).

All new prose (ladder, stop/owner lines, story beats, intro.md, OPENING, TITLE_DROP) is **draft
for Ben's pass** — same status as the Mayumi beats before.

### 0.6 The 8-persona playtest wave (2026-06-10, same session)

Eight parallel LLM agents played full runs through `tools/play_cli.py` (seeds 101–108: gearhead
speedrun, cautious cash tourist, reckless joyrider, chatty wanderer, homebound romantic, QA
edge-breaker, riz-farmer exploit hunt, owner trailer-loop). 25+ consensus findings, all fixed and
regression-tested (68 tests now):

- `drive me home` / `drive me to X` parser holes; unknown/off-map destinations now answer via NAV.
- **Over-range legs warn once and refuse** (`confirm_run` flag) — repeat the command to strand
  yourself on purpose. The Zion trap survives for the stubborn.
- **Encounter-first routing in `handle()`**: anything said during a stop/owner scene is SPEECH —
  meta verbs can no longer hijack a confession ("…full tank…where she was born" used to print the
  range table mid-climax). Only help/save/rewind/load stay console.
- Rubric word boundaries: "she's **spec**ial", "re**spec**t", "**cam**era" no longer score; owner
  middle tier (one-week deadline) is reachable; `knows_name` also unlocks the Mayumi deep-cut.
- Stop escalation: each survived stop −1 to future verdicts + diminishing wave-off riz (the county
  radio compares notes) — bounds the riz farm; riz reverts across rewinds (see above).
- One crisis at a time: drama can't fire over an open stop/owner; same drama can't repeat
  back-to-back; roadblock-opened stops get her whisper cue (WHISPER_MOMENT).
- `look` prints a real ledger; map/tow distances use ROAD_WINDING_FACTOR consistently; cash→card
  fallback announces itself; camp kiosks aren't "front desks"; gremlin card fixes count as swipes.
- Homestretch works without the home flag (defaults to oakland_aisha); story beats fire on tow
  arrivals; homecoming beats added for oakland_aisha + richmond_koinoya.
- **Promises are now keepable**: "who owned you before" at a QUIET place (park/encounter/spot,
  no heat_zone) name-drops Mayumi once (`knows_name`); asking about "that morning"/Car Week at a
  quiet place after Monterey pays off the hook (`knows_morning`, MORNING_BEAT). Long Beach still
  gates the full story.
- Favor completes only on a genuine FILL (tank−0.5 L); prologue ladder gained a 5th "resigned"
  rung; soft consent ("i guess", "twist my arm") counts as yes.

Tuning: `pulled_over` threshold heat ≥20 (was 25 — low-heat players never met the law).
Known-and-accepted: DRIVE event lines show pre-drama fuel/time when a drama mutates state after
(cosmetic); stub NPC phrasebook is static by design (Ace gives real dialogue in prod).

---

## 0.7 The gazetteer + sketch pipeline (2026-06-10, same session)

"Any town or POI in those 4 states should bring something up, and each one should get a sketch."
- **122 new town POIs** (NV 24 / CA 50 / AZ 26 / UT 22) in pois.json, each with: real coords +
  blurb from its Wikipedia extract, a judged arrival **beat** in her voice, services/terrain
  overrides, and a `wm_<id>` scene. Beats fire ONCE per game via `_story_on_arrival` →
  `world.beat_for` (flags `beats_seen`); STORIES still take precedence.
- **Beat evolution loop** (`gazetteer-beat-evolution` workflow): 8 writers grounded in
  data/gazetteer/source.json extracts → 3 judge lenses (voice/truth/play) → style memo distilled
  from winners → rewrite failures → re-judge. Converged: 122/122 mean ≥7.5, 88 ≥8.5. The learned
  house rules are in the workflow output; the big ones: one fact per beat, never let a fact sit
  raw (cash it into present-tense meaning), history pivots to now, the narrator reacts through
  hardware, closers land (image / small decision / two-part aphorism).
- **Sketch pipeline**: `tools/gazetteer_fetch.py` (Wikipedia REST summary → facts + coords + lead
  image, polite + resumable; thumbs use the 500px bucket — arbitrary widths 400) →
  `tools/make_scene.py` (adaptive-percentile 4-tone posterize to the INK ramp, 320×200, Bayer
  seam) → frontend/scenes_wm/*.png (~180 sketches, ~2.4 MB) → `wmScene()` in scenes.js (drawImage
  backdrop + ground band + parked Ace at y196/w138). `sceneIdFor` passes `wm_*` ids through;
  missing file → kind/drive fallback. ATTRIBUTION.md lists author+license per source (CC/PD).
- **Runtime fallback**: arrivals at NON-curated geocoded spots call `world.wiki_fact(lat,lon)`
  (geosearch + summary, disk-cached, `ROUTING=osm` only → offline tests unaffected) → `FACT:`
  event → narrator voices it (stub has a FACT branch).
- `tools/gazetteer_merge.py` is idempotent: rerun after editing beats.json or rebaking scenes.
- Eureka exists twice (NV + CA) — CA displays as "Eureka, CA" so name matching stays unambiguous.

## 0.8 Desperado Mode (2026-06-10, Ben's request)

Heat → the gas-station standoff → armed and dangerous. All in `engine/encounters.py` (the DESPERADO
section) + wiring:
- **Trigger**: `gas_aggression(text) >= 2` while the player `say`s something hostile/robbery-flavored
  at a place with gas (game.py say-tail) → `start_standoff` (flag `standoff`). Clerk pulls a pistol,
  dialing the cops. Routed encounter-first in `handle()` alongside stop/owner; movement verbs blocked
  (no bust — just "not with a gun on you"); `STANDOFF_COPS_ROUNDS` (3) stall limit.
- **Two exits**: de-escalate (≥2 `_DEESCALATE` tokens, no robbery tokens → clean walk-out, no gun) OR
  `disarm`.
- **The disarm** = `_set_up_right(s)`: full tank AND `flags.last_fuel_cash` (set in rules.fuel). If
  not set up → instant busted (she yells DO IT RIGHT). If set up → the Edge-of-Tomorrow ladder:
  `flags.desperado_tries` (1,2 = busted; `DESPERADO_DISARM_LUCKY`=3 = WIN). The counter is in
  `encounters.DESPERADO_PERSIST` which `game.rewind` re-applies AFTER restoring the checkpoint — so it
  survives the fold (like riz). The loop: fail→rewind→fail→rewind→win.
- **CRITICAL fix that makes the loop work**: `handle()` now clears `rewound_once` on any non-rewind
  verb, so a busted disarm between two rewinds breaks the "consecutive → go deeper" chain (otherwise
  the 2nd rewind jumped to chk2 = empty-tank Chevron and the setup was lost). Also: a fill-to-full now
  checkpoints, so the rewind lands on the set-up state.
- **Unlock** (win): `flags.desperado`+`gun`+`wanted_armed`, +`RIZ_DESPERADO` (20), +`DESPERADO_HEAT_ON_UNLOCK`
  (30), and a checkpoint (the "special checkpoint" — moment carries `unlock:True`).
- **Desperado persistent**: `DESPERADO_HEAT_FLOOR` (35) enforced in `rules._clamp_heat`; dash badge
  (`snapshot.desperado` → terminal.js red `.d-row.desperado`); `_heat_label` armed variant; `draw`
  verb (`draw_in_stop`) usable in stops (escape, heat→`DRAW_HEAT` 100, law comes ready) and as a dark
  beat in the owner scene. All meta flags survive rewind; the gun is forever.
- Knobs in config.py under "Desperado Mode". Prose is DRAFT for Ben. 8 tests (`test_*desperado*`,
  `test_*standoff*`, `test_*disarm*`, `test_draw_*`, `test_talking_the_clerk_down*`).

## 0.9 The garage economy + the GOOD ending (2026-06-10, Ben's request)

`engine/garage.py` + wiring. A trust-the-player economy and what BUYING the car unlocks.
- **Claims/ATM/glovebox**: `claim` ("i have $X cash", capped `CASH_CLAIM_CAP` 3000, tops up not
  overwrite; "i'm broke" only zeros if you're already <$100). `atm`/`withdraw` (running total under
  `ATM_ACCOUNT_LIMIT` 9999, +`ATM_HEAT` camera ping; needs gas/city POI). `explore` → glovebox $500
  once (`glovebox_found`). Parser `_money()` handles $/k/grand; `_is_claim` searches anywhere.
- **Parts** (`garage.PARTS`): hood/wheels/carbs/exhaust/coilovers/seats. `parts` lists, `sell <part>`
  (alias-matched) pays resale, appends to `flags.parts_sold`, swaps in the cheap stock part, applies
  mpg/torque effects (carbs sold → +1.6 mpg −70 tq; hood → −0.4 mpg). `car_value` and `show_score`
  drop; `is_stripped` ≥3 sold. Only at gas/city POIs.
- **The GOOD ending — buy her**: `buy`/`offer $X` in the owner encounter → `encounters.owner_buy`.
  `owner_price` = `OWNER_BUY_FLOOR` 6000 − Mayumi 2500 − riz(≥20) 1500, floor 2000, paid CASH. Afford
  it → `garage.go_legit`: `bought`+`no_heat`+`report_withdrawn`, pops `desperado`, heat 0, +25 riz,
  checkpoint, "SHE'S YOURS" welcome. Can't afford → he names the price and waits; **drive to
  oakland_aisha after `owner_met` re-summons him** (takes precedence over the homecoming story beat).
- **no_heat**: `rules._clamp_heat` forces heat 0 when set; snapshot heat/label reflect it; law/owner/
  plate dramas already gated on `report_withdrawn`.
- **Legal `race`/`show`** (require `bought`): `race` at kind==track (perf from remaining build − seeded
  roll → win/podium/midpack + prize + riz); `show` at museums/`SHOW_POIS` (needs show_score ≥90 =
  mostly-whole build → best-in-class + prize + riz; stripped → refused). Pre-ownership both refuse
  ("they check titles at the gate").
- Dash badges: red DESPERADO + cyan OWNED (`snapshot.bought` → `.d-row.owned`).

### 0.95 Economy playtest wave (2026-06-10) — 4 agents, fixes:
- **bare `buy` now parses** (was the listed choice but looped on 'Why her?' — only 'offer $N' worked).
  'deal' deliberately NOT mapped to buy (it's the prologue agreement word).
- **Encounter pitch-vs-command**: a >4-word sentence during a stop/owner scene is SPEECH even if it
  contains a movement word ("I'll drive her home and put the parts back" used to parse as 'home' and
  get blocked). Only terse (≤4-word) action verbs are intercepted now.
- **Claim ratchet closed**: claim is a one-time wallet (`claimed_total`, lifetime ≤ cap); re-claiming
  after spending no longer refills (was an infinite slow-cash faucet).
- **Glovebox broke-gated** (per Ben's spec "if they claim none"): `explore` only yields $500 if
  cash < $100; otherwise flavor.
- **Race/show one-prize-per-venue** + race now costs ~1h + 3L and needs fuel (was a zero-cost
  cash/riz faucet — flagged by 3 of 4 agents). `flags.raced_tracks`/`shown_venues`.
- **Strip-to-fund loophole closed**: `owner_price` adds 2× the resale of every sold part, so chopping
  her to afford the buy is a net loss (he won't title a shell, and it costs to undo).
- **go_legit clears gun + wanted_armed** (was leaving 'draw' usable after redemption).
- Stub: fixed stale "she's stolen" line after ownership. 105 tests. Prose draft.

## 0.96 Heat as Credit Karma (2026-06-10, Ben's request, research-grounded)

`engine/heat.py` is the heat model. Built from a research pass (workflow) on fun-vs-tiresome
notoriety mechanics — the load-bearing rules: attribute every delta, never drip on a timer,
telegraph before commit, gate the Instagram spike behind visible exposure with a dodge window,
always an active way down, marks age off (grace), car as deadpan straight-man.
- `heat.add(s, delta, reason, kind)` is the ONE mutator: clamps (respects no_heat/desperado floor)
  + logs a factor {d, r, k, day, odo} to flags.heat_log (kept 16). All the heat sites in rules.py
  (card swipe via `_card_mark`, push, rough sleep, state-line, decay, lodging, linger, tow) route
  through it now. `kind`: mark / spike / lower.
- `dashboard(s)` = the 'heat report'/'score' command (game.heatreport verb): band + bar, DEROGATORY
  MARKS vs IN YOUR FAVOR (marks show 'fades in ~N mi' via MARK_FADE_MI=260 clean miles; fully-aged
  marks are pruned from the view), a WHAT-IF simulator line, and contextual DO-THIS levers.
- `band()`/`label()` = 5 readable bands (GHOST<25 / NOTICED / TRENDING≥45 / FLAGGED≥70 / MOST
  WANTED≥90), replacing the old warm/hot labels everywhere (game._heat_label delegates to it).
- `visibility(place)` 0-3 from _FLASHY/_BUSY/_REMOTE sets + kind. Drives exposure.
- INSTAGRAM: `social_arrival(s)` on a clean flashy arrival (vis≥2) → telegraph + a gated tag roll
  (0.11*vis, ×0.35 cooldown within 3 turns) → +12-24 spike 'tagged by @handle', a 'hard inquiry';
  `untag(s)` claws back 6 if fresh. `social_fuel(s)` = the curious clerk at flashy pumps (sets
  flags.clerk_curious; game.handle resolves on the next action: drive/humble-say = slide by,
  showoff/linger = `clerk_resolve` posts you). `lie_low(s)` = active cooldown (−4/−7, costs 1.5h,
  refuses at vis≥2).
- Airbnb: economy.lodging_options adds 'airbnb' ($110); rules.sleep special-cases it (cash-preferred
  alias booking, AIRBNB_HEAT −8, no card mark). commands parses airbnb/private/rental.
- New verbs: heatreport, lielow, untag (commands.py). Stub has SOCIAL/CLERK/LIE LOW/UNTAG lines.
- 116 tests. Full research spec + findings in the workflow output. Prose draft.

## 1. Run it

```bash
cd ~/Projects/fairlady
./run.sh                       # offline stub narrator + real OSM routing (default)
FAIRLADY_ADAPTER=ace ./run.sh  # her real voice via rop1 Ace (Nemotron + Kokoro)
```

Open **<http://127.0.0.1:8739/>**. Tests: `cd backend && FAIRLADY_ROUTING=offline FAIRLADY_ADAPTER=stub ../.venv/bin/python 

**Env knobs** (read by `config.py`; `run.sh` exports only the first two):

| Var | Default | Meaning |
|---|---|---|
| `FAIRLADY_ADAPTER` | `stub` | `stub` (offline deterministic) or `ace` (rop1 LLM voice) |
| `FAIRLADY_ROUTING` | `osm` | `osm` (Nominatim+OSRM, cached) or `offline` (haversine×1.22) |
| `FAIRLADY_ACE_URL` | `https://ace-api.badler.ai` | Ace base url (read directly by `adapters/ace.py`) |
| `FAIRLADY_KOKORO_URL` | (unset) | optional OpenAI-compatible TTS for non-Japanese NPC voices |
| `HOST` / `PORT` | `127.0.0.1` / `8739` | bind |

**⚠ Gotcha that will waste an hour:** live OSM routing needs **OpenSSL 3.x**. macOS system/Xcode Python 3.9
ships **LibreSSL 2.8.3** → `SSLV3_ALERT_HANDSHAKE_FAILURE` against the OSRM/Nominatim demo servers (Ace's
TLS happens to accept it). The venv is built on **Homebrew `python@3.12`**. On Linux (rop1) the default
Python is fine. Preview launcher: `/Applications/.claude/launch.json` (name `fairlady`).

---

## 2. Architecture map

```
backend/                         FastAPI + the deterministic engine (Python 3.12)
  app.py                 5 routes; one in-memory CURRENT GameState; autosaves each turn
  config.py              flat registry of EVERY tunable (physics/economy/heat/fatigue/env)
  engine/
    state.py             GameState + Place dataclasses — THE save; derived read-only props
    rules.py             drive/fuel/sleep/tow/law — mutates state, returns factual `events`
    economy.py           gas_price, pay(), max_affordable(), quote_fuel() (pure)
    world.py             POI registry + OSM geocode/route (disk-cached) + offline fallback
    commands.py          intent parser — the LLM NEVER decides what happens
    game.py              orchestration: new_game, snapshot, choices, handle(), LORE/STORIES/STATE_INFO
    drama.py             "nothing goes to plan" — complications on drives, seeded
    save.py              JSON save/load by name
  adapters/
    base.py              Narrator interface + voices()/voice_for()
    stub.py              offline deterministic FAIRLADY (powers tests; canned drama lines)
    ace.py               rop1 Ace: /chat (Nemotron+Kokoro), /translate_speak (JA NPCs), /v1/audio/speech
  content/
    pois.json            128 POIs (NV/CA/AZ/UT), real coords, scene/story/language/lore tags
    car.json             40L/20mpg spec + FAIRLADY persona (the LLM system prompt)
    voices.json          language → Kokoro female voice id
    intro.md             the SEMA cold-open
  tests/test_engine.py   34 network-free tests
frontend/                vanilla JS, no build step (served by FastAPI StaticFiles at /ui)
  index.html             Carmen two-panel DOM + boot splash + Google Fonts
  crt.css                cyan tokens, two-panel layout, chips, dash, 恋の矢 CRT bezel, boot/crtOn
  retro.js               RetroScene: 320×200 logical canvas (SS=3 supersample), 5×7 FONT, INK palette, dither
  car_sprite.js          baked 1-bit OPAQUE car PNG (data URL) + CAR_META anchors  [GENERATED]
  scenes.js              SPR sprite lib + drawAce + drawHighway + 53 SCENES + sceneIdFor resolver
  terminal.js            render pipeline, dash/chips, welcome/placeCard, voice mic, boot dismiss
tools/make_car.py        build tool: /tmp/z_src.png → 1-bit cyan sprite → bakes car_sprite.js
run.sh  requirements.txt  README.md  LICENSE  .gitignore
```

---

## 3. Data contracts (the API between engine, narrator, and frontend)

**`snapshot(s)`** (game.py) — the read-only state the narrator and UI consume. Keys:
`location, region, kind, poi_id, scene, hour, services, blurb, fuel_l, tank_l, gallons, tank_pct,
range_mi, mpg, cash, credit_available, card_balance, card_limit, pay_method, time, day, fatigue,
hours_awake, must_sleep, tired, heat, heat_label, odometer_mi, adventures, status, turn, gas_price`.

**`_result(...)`** dict returned to the frontend per turn:
`ok, events[], scene, voice, npc, info, welcome, snapshot, choices[], status, ending, sid`.
**⚠ Naming trap:** the `voice` field actually holds the **audio URL** (Ace's `audio_url`), *not* the voice
name. The voice-name string the adapter returns is discarded. Frontend reads `res.voice` as a URL. The
opening turn also carries `intro`.

**`GameState`** (state.py) fields: `fuel_l, tank_l, mpg, cash, card_limit, card_balance, pay_method, pos
(serialized Place), odometer_mi, visited[], adventures[], clock_iso, day, last_sleep_iso, fatigue, heat,
last_sleep_poi, status, ending, seed, turn, log[], flags{}`. Derived props: `gallons, range_mi, tank_pct,
credit_available, clock, place`.

**`Place`** fields: `name, lat, lon, region, poi_id, kind, services[], blurb, gas_price, terrain,
heat_zone, language, voice, npc, scene`. (**Note:** the POI `story`/`origin` JSON fields are **dropped** by
`world._place_from_poi` — they live only in pois.json and are re-matched by `poi_id` string in game.py.)

**`s.flags` catalog** (string keys, set across engine):
`sid` (per-game id), `states_seen[]` (welcome dedupe), `revealed[]` (origin POIs offered as chips),
`home` (poi id for "drive home"), `going_home` (**dead — set, never read**), `owner_revealed` (int, drama
escalation), `limp` (gremlin → 1.25× fuel until next fuel-up), `homestretch` (set once near home),
`drama_drives` (**dead counter**), `seen_monterey` / `knows_mayumi` / `knows_truth` (STORIES gates).

**Narrator interface** (base.py): `narrate(persona, snapshot, events, player_text, session_id, extra=None)
→ {text, audio_url, voice}`; `npc_speak(language, voice, npc_desc, situation, session_id) → {native,
english, audio_url, language, voice}`. `extra` carries a drama moment: `{cue: <LLM hint>, stub: [<canned
lines>]}` — stub plays a canned line, Ace folds the cue into the prompt as the dominant beat.

**Ace API contract** (adapters/ace.py → `ace-api.badler.ai`):
- `POST /chat` form `{text, session_id, system}` → `{reply, language, audio_url}` (Nemotron reply + one
  Kokoro `af_heart` wav, session memory by `session_id`). **Sent form-encoded (`data=`), not JSON.**
- `POST /translate_speak` form `{text}` → `{japanese, audio_url}`. **Japanese-ONLY** (it's the "日本語 Voice
  Translator"; ignores any target-lang param). So JA NPCs (Japantown, Little Tokyo, koiNOya) are fully
  voiced; other languages get native text from Nemotron, silent unless `FAIRLADY_KOKORO_URL` is set.
- `POST /v1/audio/speech` (Kokoro, optional) for non-JA voices; `/asr` exists for voice input (**not yet
  wired in the frontend**); `GET /audio/{name}` serves the wavs.

---

## 4. The numbers (exact current tunables)

**Fuel/range** — tank 40 L, 20 mpg, start fuel 5 L. `L_per_mile = 3.785411784/20 = 0.18927` base, ×terrain
(≥1.0, per-POI), ×1.15 push, ×1.25 limp. Full range ≈ **211.3 mi**; from 5 L ≈ **26.4 mi**. A drive either
completes or runs dry mid-route → **stranded** (no partial-arrival; only `tow()` recovers, refuels a fixed
2.0 L, costs $175 + $4/mi, +~9–14 heat).

**Economy** — gas $/gal NV 4.25 / CA 4.95 / AZ 3.95 / UT 3.89 (per-POI overrides up to Death Valley 6.49);
lodging motel 92 / lodge 165 / camp 28; START_CASH 40; CARD_LIMIT 2000. (FOOD_PRICE 16 is **unused**.)

**Heat** (0–100) — start 8; patrol ≥45; card-nervous ≥70; roadblock ≥90. Card swipe +2 (base) / +4 (hot
zone), +2 if <24 h since start. Decay 0.8/h while moving outside hot zones; ×0.82 crossing a state line;
push +6; lodging −4; linger (2nd night same town) +5. `law_check()` rolls after each completed drive.

**Fatigue / awake gate** — hard gate: can't drive past **20 h awake** (warn at 16); awake clock starts
**07:30** and resets on sleep. The soft 0–140 `fatigue` points meter only warns (literals 70/100) and is
**inert above 100**.

**Drama chance** (drama.py `_chance`): `0.20 + heat/100·0.18 + min(0.18, odometer/2500) + (day−1)·0.015`,
`+0.35` if within 120 mi of home, capped **0.72**. Fires **only on `drive`**.

**Graphics** — canvas 320×200 logical, **SS=3** supersample (960×600 backing). INK cyan: `bg #0e0c0a,
d1 #13262a, d2 #1f6f7d, d3 #2ba8bf, f #38d6ec, hot #b8f4ff, red #e23b2e`. Car sprite 188×135, anchors
`mirror [0.10,0.15]`, `rearGlass [0.18,0.06,0.30,0.27]`, `ground 0.97` (**unused**). `make_car.py`
threshold `INK_T 0.47 / HOT_T 0.80`. `drawHighway` diagonal VP `0.36·W`, near-centre `0.60·W`; `drawAce`
`baseY 184, w 150`.

---

## 5. Catalogs

**Intents** (commands.py `parse()` → verbs): `drive` (+`fast`/push), `home` ("drive me home" / "home is X"),
`origin` (which ∈ born/grew/owner — "where were you born / grew up / who built you / who owned you before"),
`fuel` ("fill / gas $20 / 10 gal / 30 L" + cash/card), `pay` (cash|card), `sleep` (motel/camp/rough),
`talk`, `map` (+ "nearby gas"), `tow`, `look`, `help`, `save`/`new`/`load`, `say` (free conversation →
narrator). **Order matters:** origin/home detection must precede the generic `where…`/`map` check.

**Drama events** (drama.py `EVENTS`): `overheat` (mountain grade → time lost), `plate` (heat≥30 → +6 heat,
near-miss), `owner` (coy melancholy hint, `owner_revealed`++, −3 heat), `recognized` (city/track/amusement/
encounter/museum/park → gift $ **or** witness +heat), `gremlin` (odo>120 → pay to fix **or** `limp`),
`detour` (closed pass → −fuel −time), `homestretch` (within 70 mi of home, weight 6 → she stalls).

**Story set-pieces** (game.py `STORIES`, fired once on arrival, verbatim, pre-empts drama): `monterey`
(aquarium + 2025 Car Week → `seen_monterey`), `long_beach` (the **Mayumi** Cherished-Salvage tale →
`knows_mayumi`), `livermore` (the **storage unit 137** = the truth → `knows_truth`). `_story_on_arrival`
supports a `requires` gate but **none is set** (so order isn't enforced — see quick wins).

**Scenes** (53; scenes.js `SCENES`): bespoke — gas, stranded, motel, grand_canyon, zion, bryce, arches,
canyonlands, death_valley, joshua_tree, yosemite, sequoia, great_basin, monument_valley, saguaro,
petrified_forest, sedona, meteor_crater, goblin_valley, capitol_reef, hollywood, bay_bridge, golden_gate,
vegas_strip, sphere, fallon, hoover_dam, bonneville, laguna_seca, disneyland, santa_monica, lake_havasu,
sf_japantown, koinoya, oakland_aisha, museum, aquarium, storage, mojave, lone_pine, reno, salt_lake;
driving loops — drive_desert, drive_city, drive_mountain (+ night_drive/roadside aliases); kind-fallbacks —
park, track, amusement, city→drive_city, encounter, gas, museum. Resolver: `sceneIdFor(snap)` → stranded?
→ explicit `snap.scene` → `KIND_SCENE[kind]` → `_driveEnv` (UT=mountain, else desert).

**POIs** — 128 total (NV 26, CA 69, AZ 17, UT 16). Kinds: city 49, encounter 31, park 19, track 10,
amusement 9, museum 6, gas 4. NPC languages present: ja, zh, es, it, hi (voices.json also declares fr/pt
but **no POI uses them**, and there's no `ko` at all). Story POIs: monterey, long_beach, livermore.

**FastAPI routes** (app.py): `GET /api/health`, `POST /api/new`, `GET /api/state`, `POST /api/command`,
`GET /` (→ `/ui/`). Static: `/ui` (frontend), `/tts-audio` (Kokoro wavs).

---

## 6. How to extend (recipes)

- **Add a POI:** append to `backend/content/pois.json` with `id, name, kind, region (NV/CA/AZ/UT), lat, lon,
  services[], blurb`, optional `scene, gas_price, terrain, heat_zone, language+voice+npc, story, origin`.
  Real coords. Restart server (it reloads pois at import).
- **Add a scene:** add a `myscene(s, t) { … drawAce(s, t, {moving:false|true}) }` to `SCENES` in
  `scenes.js`, reference it from a POI's `scene` field (or add to `KIND_SCENE`). Use `s.rect/line/poly/disc/
  dither/text` + `SPR.*` helpers; colors from `I.*`. Frontend is static — just reload.
- **Add a drama event:** add `{id, pred(s), weight(s), fire(s,rng)}` to `EVENTS` in `drama.py`; `fire`
  mutates state and returns `{tag, id, lines:[…], cue:"…", stub:[…]}`.
- **Add a story town/beat:** add the POI (with `story:true`), then a `STORIES["poi_id"] = {flag, beat,
  requires?}` in `game.py`. Optionally a bespoke scene. Use `requires` to enforce order.
- **Re-bake the car** from a new photo: convert HEIC→PNG to `/tmp/z_src.png` first (e.g.
  `sips -s format png IMG_xxxx.heic --out /tmp/z_src.png`), then `./.venv/bin/python tools/make_car.py 188
  --bake`. Tune `INK_T/HOT_T` in the file; re-check `anchors` (mirror/rearGlass) against the new crop.
- **Point at rop1 Ace:** `FAIRLADY_ADAPTER=ace ./run.sh`. For non-JA NPC voices, also set
  `FAIRLADY_KOKORO_URL` to a Kokoro `/v1/audio/speech` endpoint.
- **Add a language/voice:** add a row to `voices.json`, give a POI `language` + matching `voice` + `npc`.
  JA is fully voiced via `/translate_speak`; others need `FAIRLADY_KOKORO_URL`.

---

## 7. Known bugs & quick wins (from a full subsystem audit)

**Bugs to fix (P0):** — ✅ ALL FIVE FIXED in the Ride or Die session (2026-06-10). Kept for history:
1. **`encounter` scene throws** — `scenes.js` (~line 905) calls `SPR.city(s,t)`, which doesn't exist (only
   `SCENES.city` and `ENV_OBJ.city` do). The RAF loop swallows it, so the generic non-JP encounter renders
   only its bg + text. Replace with the `SCENES.city` body or a skyline helper.
2. **Missing FONT glyphs** — `retro.js` `FONT` lacks `♣` and CJK, so koiNOya's club blade shows `?` and the
   encounter banner `你好` shows `??`. Add glyphs or strip unsupported chars in `s.text`.
3. **STORIES order not enforced** — `livermore` (the truth) can fire before `long_beach` (Mayumi). Add
   `requires: "knows_mayumi"` to the livermore entry (the gate already exists in `_story_on_arrival`).
4. **README test-count drift** — says "33" and "28"; the real number is **34**. Fix both.
5. **`make_car.py` runs `main()` at import** with no `if __name__` guard and crashes if `/tmp/z_src.png` is
   absent — add the guard + a friendly error.

**Quick wins / cleanups (P1):**
- Rename the `_result['voice']` field to `audio_url` (it's the most confusing thing for a frontend dev).
- Wire `FATIGUE_WARN/FATIGUE_FORCE` into `rules.py` (currently bare literals 70/100); delete dead constants
  `NIGHT_START_HOUR`, `FOOD_PRICE`, the inert 140 fatigue cap, the unused `impounded` status, dead flags
  `going_home`/`drama_drives`, dead `SPR.car`/`SPR.poles` (~80 lines) and the unused path math in
  `laguna_seca`/`track`.
- Promote magic numbers to `config.py` (push 1.15/0.85, limp 1.25, tow constants, law_check 0.45/12/etc.,
  the `1.22` road-winding repeated in 3 files → use `config.ROAD_WINDING_FACTOR`).
- Rename `crt.css --orange` (it's actually hot-cyan `#b8f4ff`) to `--hot`/`--accent`.
- Fix the stale "amber phosphor" comments in `retro.js`/`scenes.js` (it's cyan now).
- Honor `CAR_META.anchors.ground` in `drawAce` instead of the magic `baseY=184` (robust to re-crops).
- Surface swallowed scene errors (throttled `console.error` in the RAF catch and the Ace fallback).
- Add a content-validation test: every POI `scene` ∈ SCENES, every `language` ∈ voices.json, every voice
  matches, lat/lon ∈ REGION_BBOX. (These invariants are currently clean but unenforced.)
- `last_sleep_iso` default should be `AWAKE_START_ISO` (currently `START_ISO`, so a directly-constructed
  GameState has a ~10 h-off awake clock unless created via `game.new_game`).

---

## 8. Gotchas / non-obvious things

- **LibreSSL** (see §1) — the OSM-routing TLS trap on macOS system Python.
- **`/translate_speak` is Japanese-only.** Don't expect target-language switching.
- **Type-on race in UI test scripts:** `typing`/`busy` are module-scoped closures, *not* on `window`. A
  `submit()` called while the opening line is still typing just fast-forwards the animation and returns
  (swallowing the command). When scripting the UI via `preview_eval`, wait real time for the open to finish
  before the first `submit`. The game logic is fine; this only bites test harnesses.
- **The fender mirror is placed procedurally, not photo-aligned.** Ben's clear front-3/4 mirror photo was a
  clipboard paste that never hit disk; the sprite is the rear-3/4 IMG_7714, so the two angles can't be
  pixel-aligned. The mirror lives in `drawAce` at `anchors.mirror`.
- **Voice input is browser-only today.** `webkitSpeechRecognition` (Chrome) is wired; **Ace `/asr` is not
  yet called from the frontend** — that's the production path (and it can't be exercised in a preview
  sandbox without a mic).
- **Single global game state.** `app.py` keeps one `CURRENT` GameState + one autosave — single-player only.
- **`get_narrator()` caches** the adapter at first call; changing `FAIRLADY_ADAPTER` needs a process restart.
- **Drama only fires on `drive`** (so `homestretch` only triggers on a drive within 70 mi of home).

---

## 9. Open creative items (Ben's, pending)

- **Finalize the Mayumi / Livermore / Monterey prose** — the current beats in `game.py STORIES` are evocative
  *placeholders*. Canon to keep: **Mayumi = the cherished-salvage previous owner** (a Hagerty "Cherished
  Salvage Story"); the **Oakland AiSha cats = the builders** (separate from the owner); the **truth lives in
  the Livermore storage unit (137)**; she stays **coy** until then.
- **Per-town metro events** — Bay Area / SoCal towns should trigger set-pieces like Monterey/Long Beach do.
  The system (`STORIES` + `_story_on_arrival`) is built; it just needs more entries + scenes.
- **Fill out towns** — coverage is uneven (CA 69 but whole metros are single pins; AZ/UT thin on long legs).
  Add neighborhood encounters (LA: Hollywood/Venice/Koreatown; SF pattern already good), and intermediate
  gas/town pins where terrain multipliers bite (I-15 Mojave, the Loneliest Road, Page↔Monument Valley).
- **Missing-language encounters** that `voices.json` already promises: `fr` (a Québécoise at a Bryce
  overlook), `pt` (a rally crew out of Vegas), and a new `ko` (LA Koreatown / Garden Grove).
- **The mirror graft** — if Ben provides the front-3/4 photo *as a file*, digitize the real fender mirror.
- **Wire Ace `/asr`** for real voice input (the headline interaction).

---

## 10. Reference assets & memory

These live **outside the repo** (intentionally — they're personal/source material), under `~/Downloads`:

- **`IMG_7714.heic`** (in `~/Library/Messages/Attachments/bc/12/…`) — the rear-3/4 photo the car sprite is
  baked from. Convert to `/tmp/z_src.png` to re-bake.
- **`Portfolio-15.zip`** — the live **badler.ai** website bundle = the design source of truth. `deploy/
  index.html` has the exact cyan tokens (`#38d6ec`/`#0e0c0a`/`#f6f4eb`), fonts, and the `恋の矢` CRT recipe.
  `media/koi-crt.webp` is the posterization reference — **now shipped in-repo as `frontend/koinoya-crt.webp`** (the boot-splash hero art; Ben rejected the hand-drawn SVG koi fish — there is no koi-fish brand asset, the 'koi' is the shop); the SEMA "Soul 心 連繋 Interface" koi wordmark is the
  brand mark.
- **`koiNOya.png`** (Edo relic shop, suit-bladed naginata — the Richmond "born" look) and **`AiShaPaint.jpg`**
  (1926 red-brick Oakland garage — the "grew up" look).
- **`Cartesia_Application_Packet_Benjamin_Adler.pdf`** — the source for FAIRLADY's **writing voice** (terse,
  dry, literate, romantic-not-sentimental; the "bury-the-lede pivot" + constraint-as-romance).
- The **Ace stack** lives on **rop1** (`ace-api.badler.ai`); see the project memory note `project_ace_portfolio`
  for its services and lore (always 5:37, Larry Chen, AiSha LLC).

**Project memory:** `~/.claude/projects/-Applications/memory/project_fairlady_game.md` holds the full
decision history (why cyan, why 1-bit, why coy, etc.). Read it for the *why* behind any choice.

---

## 11. Suggested first moves in the new session

1. `git` is already initialized and pushed — work on a branch, PR to `main`.
2. Knock out the §7 P0 bugs (encounter scene, FONT glyphs, STORIES `requires`, README count, make_car guard).
3. Then pick a thread: **content** (fill towns + the missing-language encounters), **narrative** (finalize
   Mayumi with Ben), or **voice** (wire Ace `/asr` so the mic talks to the Blackwell).
4. Keep the **engine-owns-state / LLM-only-narrates** invariant and the **voice-first / no-buttons** rule
   sacred. The dashboard must always be real; she must stay coy about Mayumi until Livermore.
```
