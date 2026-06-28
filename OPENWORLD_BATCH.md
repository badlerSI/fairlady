# RIDE OR DIE — open-world batch (engine systems shipped)

This batch turned the game from a heat/gas economy into an **open world where something can happen
anywhere**, grounded in real-world research (`RESEARCH_NOTES.md`, `content/world_events.json`,
`content/eateries.json`). Everything below is **in, wired, and tested** (218 passing). Prose is a
working DRAFT in Ace's voice for Ben to rewrite.

## New engine modules
- **`luck.py`** — the hidden LUCK metric (per-game baseline, re-rolls on rewind so a redo isn't the
  same weather) + `pressure()` (the product of heat, gas, fatigue, hunger, BAC) + the deer roll +
  the roadside-ID roll. Luck is never shown on the dash.
- **`survival.py`** (extended) — caffeine (counters fatigue, hard diminishing returns, a sleep-debt
  you pay back tonight) on top of hunger/#1/#2/alcohol.
- **`inventory.py`** — the 240Z hatch is **~7.5 cu ft** (real, tape-measured + factory spec). Buy
  jerry cans (reserve fuel → range), water, cooler, tent, sleeping bag, tools, first-aid, spare,
  snacks — a hard volume cap (it's a 240Z, not a U-Haul). `fill the jerry cans` / `pour the reserve`.
  The **Stinger** can't be bought — it just turns up in the hatch after Area 51.
- **`romance.py`** — the love story: the stick-shift question at the title drop, "do you believe in
  love at first sight?", the ace-of-spades philosophy, and the recurring cyan-woman dream (stub).
- **`cameras.py`** / **`places.py`** — the ALPR grid (prior batch) and the real-world layer.

## New mechanics (by the user's list)
- **SEMA opening corrected** — checkerboard tiles near the **back of North Hall**, the **SEMA Cruise**
  (the real 1,200-car parade, 4–7:30pm Fri Nov 7) rolling out the exit; you're late + low on gas to
  join it, so you roll out with the crowd to the Chevron. Doors lock ~6.
- **Freeman easter egg** — try to drive back into the hall and a real **Freeman** teardown guy runs
  you off, warns about the overnight tow.
- **Monty Burns ending** — leave her parked overnight (sleep during the prologue) and she's towed
  (real SEMA policy). Sad-trombone sfx + the **Montgomery Burns Award for Outstanding Achievement in
  the Field of Excellence**; reverse reads, italic and quote-less: *The Lesson is: Never Try*
  —Homer Simpson, Inaugural Recipient.
- **Respray = rattle-can over PPF** — peelable, but she BEGS you not to; spray her anyway and she
  crashes into COLD (anti-theft armed) and will **phone home** on the next signal. `peel the paint`
  to undo the look. **Detaching the spade hood** is the disguise she *consents* to (it's a wrap).
- **Universal event engine** — drives/places roll against `pressure × luck`. **Deer** on night
  mountain legs (Nov = peak season, grounded); **roadside ID** sleeping rough in the show car.
  **Caffeine** vs fatigue; **rizz dulls when tired**.
- **Inventory + jerry cans + the Black Rock** — can't carry infinite; water + reserve fuel gate a
  deep-desert run (she warns you).
- **The mountain chase (Edge of Tomorrow)** — high heat + night + mountains → a county cruiser
  pursuit: kill the lights / side road / push / hide, or take the stop. Crash = limp + caught.
  Every run **teaches you the road** (`chase_learned` persists across rewind); déjà vu.
- **Gas-station car-talk** — graciously talk the *build* to a curious onlooker → **riz, no heat** (a
  fan, not a witness). Claiming fame still gets you posted.
- **Drive conversation** — legs >30 min open a conversation with Ace; talk as long as the drive
  lasts, or **'put on music'** to fast-forward. (Config flag `FAIRLADY_DRIVE_CHAT`, ON by default.)
- **NYE reckoning** — the owner finds you **no matter where you are** ("I have my ways"). Know his
  secret OR be RIDE-OR-DIE with her → he signs her over (a win). Otherwise he collects her for CES.
  Making it to NYE alive is its own award.
- **Real world** — Ace suggests **real** restaurants/bars/motels (the Clown Motel, the Mizpah…) and
  you drive into **real** events (F1 GP, the NFR, the holiday lights) if you're there on the day.

## The Rizzbreaker + the getting-to-know-you (added same batch)
- **`onboarding.py`** — right after the key turns, Ace gets to know you (the real goal is *extended
  conversation*): asks your **name**, **"do you do pronouns?"** (reads your answer for what to call
  you AND the rough temperature of how you feel about it, tunes her warmth a notch, but **never
  lectures or judges any stance** — she just holds her own line with grace and a joke: she's she/her,
  a *Fairlady*, never an 'it'), and your **age** (to pitch references right; she explains "riz" to
  anyone born before 1990). Profile flags (`player_name`/`player_pronouns`/`refs_era`) personalize
  her throughout (`onboarding.profile_cue`). Every step is deflectable ("let's just drive").
- **`rizzbreaker.py`** — the charisma **Limit Break**. Riz fills a gauge (`RIZZBREAKER_THRESHOLD=30`);
  at full you spend it on ONE context-aware impossible move: at a **stop/chase** → the full Jim Carrey
  *"this car is POSSESSED, it has my SOUL, take me out before my destination and I burn in hell"* bit
  (Ace in a demon basso + strobing alternate headlights → the cop waves you through); at a **poker
  table** → shove all-in on a **2-7 offsuit** and stare the table off their aces for the whole pot;
  in a **crowd** → propose marriage to a beautiful stranger (they say yes). Invoking empties the gauge.
  Dash shows `rizzbreaker_ready`/`rizzbreaker_gauge`/`rizzbreaker_here`. Scorecard awards: THE RIZZLER,
  ENGAGED TO A STRANGER, SEVEN-DEUCE.

## Age gate, affection gauge, and Alma (added same session)
- **18+ gate** — the game has gunplay and people get shot, so in onboarding, stating an age under 18
  gets a warm-but-firm decline from Ace and closes the road (`age_blocked`, surfaced in snapshot for a
  frontend gate). Best-effort (a refused/vague age passes).
- **愛車 affection gauge** — snapshot ships `affection_gauge` (0–1 = `bond/100`); the 愛車 logo fills
  and empties with it (see [AISHA_GAUGE.md](AISHA_GAUGE.md) — needs Ben's real calligraphy PNG, recipe
  + frontend plan provided; a font placeholder is in `frontend/media/aisha_gauge/`).
- **Conversation farming** — talking to Ace grows affection slowly (diminishing per place, resets on a
  drive); asking about HER (the build, her origins, "tell me about yourself") grows it faster. The
  point: reward the extended conversation.
- **The riz/Ai floor (Ben's ratchet)** — on a rewind/failure you keep ≥60% of your peak Riz and stay
  within `BOND_FLOOR_DROP` of peak affection. You never face a wall again with less than last time;
  the rewind tax still bleeds the *overflow* into heat, so brute-forcing still isn't entirely free.
- **Alma** ([alma.py](backend/engine/alma.py)) — the cyan woman from the dreams. The dreams now name
  her. A HACK: roll into Vegas on the **very first night** and, if you know her name, `marry Alma` —
  you elope before dawn and she rides along. She **books comped off-the-books rooms** (`alma book a
  room` → free, clean `sleep`) and **launders heat** (`ask Alma to cool it`, on an 18h cooldown).
  Marrying her costs you with Ace — the **love triangle** (the deeper arc is hooked for Ben).

## RESERVED FOR BEN (do not auto-generate)
- **Cities:** Reno, Carson City, Oakland, Richmond, Long Beach, Fresno, Fallon, Folsom — the
  auto-suggestion layer (`places.py RESERVED_CITIES`) skips these. Existing core story beats that
  happen to live in them (e.g. the `oakland_aisha` owner-garage arc, the `fresno` painter reveal)
  are load-bearing and left intact — "reserved" means no NEW filler, not deleting the plot.
- **The cyan-woman dream** (`romance.py _DREAM_STUBS`) — the mysterious woman is the heart of the
  mystery; the dream fires and escalates, content is a stub for Ben.
- **Per-place scripts** — each POI has a beat hook; the bespoke scripts are Ben's.

## DEFERRED (earn plausibility first)
- **Alien abduction** at Area 51 — per Ben, "later… we have to earn some plausibility." For now,
  visiting the gate just mysteriously deposits the Stinger in the hatch. No abduction yet.

## Codex art status (as of this batch)
The repo's `frontend/scenes_wm/` has **215 plates = 169 older + 46 cyan placeholders** I generated —
full coverage, zero 404s, but NOT Codex's new marquee art. Codex's 53/252 (38 marquee + 15 tail)
land separately and overwrite by filename. **Use the checkerboard-North-Hall opening, not the generic
240Z.**
