# RIDE OR DIE — design notes & build plan (2026-06)

Research-grounded plan for the next wave. Two parts: (1) what makes a good game good, applied to
*this* game; (2) the concrete build plan for the outlined features, with exact engine hooks.

---

## Part 1 — "sprinkle good game on top" (the research, applied)

The honest read from the design research: **RIDE OR DIE already has more *systems* than most shipped
indies.** The risk isn't a thin game — it's a dense one whose ~8 genuinely interesting decisions get
buried under bookkeeping, in the one place text games are weakest: **moment-to-moment feedback
(juice)**. So the highest-leverage work is *reinforcing and subtractive*, not additive.

**Top 3 (do these as we build everything else):**

1. **The dashboard IS the particle effects.** A text game's juice is the numbers *moving*. The engine
   already computes exact deltas every turn (fuel, miles, money, time, heat, Riz) — that's unexploited
   juice. Make every consequential turn fire a tiny, legible animated delta on the persistent chips/dash:
   `RANGE 211→164 mi`, `HEAT +6` with the band flashing `NOTICED→TRENDING`, `RIZ −2` in red, a derogatory
   mark appearing with its "ages off in ~180 mi" counter. Use the mood-tint (spooky/sketchy/awe) as a
   **one-turn full-panel flash** on big beats. A single CRT "chunk" on a heat spike and a warm chime on
   the title-drop / owner's-blessing do enormous work. Sell the **Instagram-tag spike** like pinball
   multiball — it's the most dramatic feedback moment in the game.
2. **Sid Meier's test on every verb: interesting decision or busywork?** Tag the ~40 commands DECISION
   vs BOOKKEEPING. The forks (steal-or-buy, cash-vs-card, gamble-all-in, buy-her-vs-run, draw the gun,
   ditch-the-phone) get full weight + a visible consequence delta. The bookkeeping (cold-start ritual
   after it's taught, refuel math, sleep) should **auto-resolve / one-tap** — never make the player
   re-type the 3-pump crank once they've learned it ("crank her (you know the trick) [y]").
3. **Match narration cost to dramatic weight.** The LLM narrator is slow; a multi-second Nemotron turn on
   "fill up" is the worst boredom-side flow break, and an instant stub for the owner's confession is the
   worst anxiety-side one. Reserve heavy narration for drama (the owner, set-pieces, complications); let
   the deterministic stub instantly resolve bookkeeping turns. Guard **Riz's meaning** — make payouts
   legible ("RIZ +4 — talked your way out clean") and keep the gamble→rewind "sanctioned cheat" a *real*
   sacrifice so it never becomes the dominant strategy that makes the honest buyout pointless.

These thread through everything below: every new beat ships its legible delta, every new verb gets the
decision-vs-busywork check, and the heavy moments (the owner, Alma, the 3-way) get the real voice budget.

---

## Part 2 — the build plan (exact hooks)

### A. The 3-way (Ace + Alma + player) — the foundation  ·  task #104
**Confirmed broken:** with Alma aboard, free conversation only ever routes to Ace; Alma is mute outside
her scripted beats (`romance.py` test reproduces it). Build a real 3-way:
- When `alma.aboard(s)`, a free-text `say` turn can produce **Ace's line AND/OR an Alma interjection**.
  Route by address + content: a line addressed to Alma ("Alma, …") → Alma answers (persona="alma");
  a charged/romantic line → Alma answers + Ace reacts (jealousy); a car/road line → Ace, Alma may chime.
- Implement as: in the `say` handler, when Alma's aboard, run a light **director** — decide speaker(s)
  from (who's addressed, romance vs practical, Ace's bond band, `alma_is_friend`). Surface up to two
  voiced lines (Ace `_PERSONA`/af_heart, Alma `PERSONA`/af_nova) in one turn. Keep each ≤2 sentences.
- Jealousy coloring: high Ace bond + romantic-to-Alma line → an Ace dig (uses the dating jealousy ladder,
  not the one-shot triangle hit). Friend-mode → Ace ribs instead of seethes.

### B. Owner persona + voice — DONE (groundwork)  ·  task #105
`encounters.OWNER_PERSONA` + `OWNER_VOICE="am_onyx"` (a loaded male voice), routed in `game._narrate`
via `persona:"owner"`. The new SEMA moments below use it. (Alma moved to `af_nova` — a loaded distinct
female — because **ef_dora is NOT loaded** on the ace-api Kokoro; swap back when it is.)

### C. SEMA owner-at-6 set-piece  ·  task #106  (depends on the opening clock, task #100)
The clock + 6pm only matters **after turn-the-key** — it's the "lingered too long" branch. Reuse the
buyout spine; **do not reinvent `go_legit`**.
- **6pm spawn:** in the SEMA handler, when you've turned the key but haven't left by `clock.hour>=18`,
  the builder returns → `encounters.start_owner(s)` (a SEMA-flavored arrival) speaking in his voice.
- **Branches off the conversation score** (`owner_turn` already scores the pitch):
  - **Great talk + you buy →** `encounters.owner_buy_sema(s, amount)` (clone `owner_buy`'s success):
    BTC as a **label over a USD price** (`SEMA_BTC_PRICE_USD` ≈ 2 BTC instant-accept; bargainable to
    1 BTC if you say it's all you have and pitch it well) → set `bill_of_sale` flag → `garage.go_legit(s)`
    (bought + no_heat + report_withdrawn + gun dropped + +22 bond) → **inventory + range tutorial**
    (illustrated by the near-empty tank) → the CAR-TALK-plate warning → fade to `sema_chevron`. Game
    **continues** legit (heat is different but you can still get arrested for bad acts). Ace's plea
    ("Please buy me! …third favorite after a Station Wagon") + the builder's confession (Larry Chen, zero
    media, doomed business) are the beats — exact lines from Ben.
  - **Great talk, no buy →** he trailers her → terminal **`sema_timeout` short loss** (the "fallen in
    love but let go of the wheel" version).
  - **Mediocre talk →** he trailers her → `sema_timeout` (the Oakland / "enjoy your conversation" /
    "7000 RPM in 6th across the Mojave, not too high with that 3.9 rear, definitely not legal" version).
- **Ending wiring** (per the endings map): SEMA-buy is a WIN — `WIN_KEYS += "owned"` path or a new
  `sema_buy` key; the wait-too-long is a LOSS (`status='busted'`, `ending_key='sema_timeout'`). New text
  in `endings.py`, scorecard award + tally, trigger in the SEMA handler.

### D. Endings + their screens  ·  task #108  (one engine patch unlocks all loss art)
- **The single unlock:** `sceneIdFor` (scenes.js ~1144) hard-returns `'stranded'` for every loss before
  reading `ending_key`. Patch it to `lose_<ending_key>` lookup → today's `towed_sema`/`phoned_home`/`ces`
  + every new loss can have a bespoke plate. Win scenes auto-pick `won_<key>` already.
- **Codex brief (separate file):** SEMA fade-out, cop-car silhouette (the only sanctioned `red` use — a
  blinking lightbar), Ace on fire (the fake-death decoy), Ace crashed, ambulance (punched out),
  sunset-with-Alma-on-the-hood, + more. Several can be procedural (retro.js prims) per the endings map;
  the photographic ones go to Codex.

### E. Alma affection bar + companion CYOA  ·  task #107
New scalar `s.flags['alma_affection']` (mirror `bond`, its own attributed ledger + an `alma_gauge`
snapshot key + a second 愛-style bar in the dash). Then:
- **"Where you going?" → "Nowhere…Anywhere…How about you?"** (a club/hitchhiker beat).
- **Beds:** `alma.book_room` sets `alma_room_beds = 'king' if alma_affection high and not friend else
  'two'`; `rules.sleep` (l.629) consumes it and varies the line. Bedroom stuff **implied**.
- **Friend-vs-lover:** `s.flags['alma_is_friend']` (declared in-convo — "I'm only into men" / "I'm
  happily married" → friend). Scales the **three** triangle jealousy hits (`alma.py` elope/club/hitch)
  by 0.2, and softens Ace's stubs (ribbing, not seething). Alma swings both ways by default.
- **Park Ace, ride with Alma:** new verb `parkwithalma` (must be guarded against `park ace`→Bob at
  commands.py:160 — require an explicit "with alma"), set `ace_off` + `ace_parked_with_alma`, a real
  `bond.adjust(−N, "left me behind to ride off with HER", "deep")` jealousy beat, reuse `dating.py`'s
  `ace_off` so closeness with Alma doesn't trip Ace's live jealousy while she can't watch. CYOA to the max.
- **Gotchas:** two separate jealousy systems (one-shot triangle hit vs the dating ladder) — friend-mode
  scales both; **never mutate `s.bond` directly** (always `bond.adjust`); `book_room` is bed-agnostic
  today (greenfield).

### F. SEMA opening mechanics  ·  task #100 (already designed, Ben's calls locked)
Clock ticks 5:37→6:00; after interest she tacks the qualifier onto her answer ("…stick? …age?"); pass
(18+ and yes) → turn-the-key; fail → "that's too bad" + the WAY-too-young / vanishing-third-pedal lines,
keep talking to 6 → the owner set-piece (C). Name/pronouns stay post-qualify. `sema_back_hall` plate
(no stock turntable car) is in the Codex character brief.

---

## Build order (foundations first)
1. **3-way (A)** — Alma must be able to speak; unblocks all Alma content.
2. **Alma affection bar + friend-flag (E core)** — the meter the CYOA reads.
3. **SEMA opening mechanics (F) + owner set-piece (C)** — one coherent set-piece (the most-specified beat).
4. **Endings unlock + Codex ending-screen brief (D)** — one engine patch + art.
5. **Companion CYOA polish (E rest)** — beds, park-with-Alma.
6. **Juice pass (Part 1)** — animated deltas + sound, woven across all of the above.

Every step ships its legible delta and gets the decision-vs-busywork check. Prose stays a DRAFT for Ben.
