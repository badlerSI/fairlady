I have everything I need. The geography confirms reachability: Vegas → Area 51 back gate is ~101 mi of road (the gate is closer than Rachel itself). A full 40 L tank gives ~211 mi range, so on night one — after the favor fill at the Chevron — the gate is a one-tank round trip. The encounter design is complete. Here is the implementation-ready spec.

---

# AREA 51 FIRST-NIGHT ENCOUNTER — Implementation Spec

## 0. Concept & how it fits the engine

A new self-contained encounter module, `engine/area51.py`, modeled exactly on `encounters.py`'s pattern: an `*_active(s)` predicate, a `start_*` opener, and a `*_turn(s, raw)` that runs a deterministic **rubric** over a fixed series of questions, accumulates a score, and on the last question branches to one of two outcomes. It is wired into `game.py`'s encounter dispatch alongside the stop/owner/standoff block, and triggered on arrival at the existing `area51_gate` POI.

Two outcomes:
- **GOOD** → "was it a dream?" roadside wake-up. Sets a brand-new **`gifted`** ownership state (distinct from `bought`): `no_heat=True`, title in your name, glovebox stuffed with cash. Heat is 0 and **stays 0 unless you commit a crime** (a re-arm hook). This is an easy-mode/quick-win unlock.
- **BAD** → **abduction**, a new losing ending `"abducted"` via `endings.py` ENDING_TEXT + a `set_ending` extension, rolling the standard scorecard.

The alien voice uses the Place's `voice` field → `npc_speak(language, voice, ...)`. We set `area51_gate.voice = "soundwave"` so the Ace adapter's TTS layer renders the Piper `en_US-john-medium` + Soundwave RVC (pitch −3) impression. (Note: the `IMPRESSION_MAP`/RVC pipeline lives on the Ace server's `tts.py`, not in this repo — see §8.)

---

## 1. `content/pois.json` — make `area51_gate` reachable night one + a Black Mailbox waypoint

The gate already exists at `lat 37.235, lon -115.8111`, scene `area51`, kind `encounter`. Two changes:

**(a) Add the alien voice + a language so `_encounter`/`npc_speak` fires the soundwave impression.** Currently `area51_gate` has no `language`/`voice`, so `_encounter` returns `None` and nothing speaks. The Area 51 encounter does NOT use the generic `_encounter` greeting path (it has its own opener), so the `voice` is consumed directly by our module's `npc_speak` call (§7). Add to the `area51_gate` POI object:

```jsonc
"voice": "soundwave",        // → Ace tts IMPRESSION_MAP key; en_US-john-medium + Soundwave RVC, pitch -3
"language": "en",            // English line; the impression is carried by `voice`, not translation
```

**(b) Reachability is already satisfied — verified.** Vegas → `area51_gate` is **~101 mi of road**; a full 40 L tank = **~211 mi range**. After the night-one favor fill at the Chevron the tank is full, so the gate is a comfortable one-tank round trip (gate-and-back ≈ 202 mi; cutting it close, which is thematically perfect — "top off before you commit"). **No new gating logic is required** — `drive to area51_gate` already works the moment `favor_filled` is set, because `gas_target` is cleared at favor-done (`game.py:643`, `s.flags.pop("gas_target")`). The only thing to confirm is that `area51_gate` appears as a reachable destination hint; it will surface via the generic nearest-goals list only if it's an `ADVENTURE_KIND`. It is `kind:"encounter"`, so add a discoverability nudge (see §1c).

**(c) Add a `black_mailbox` waypoint POI** (real geography: the famous mailbox at the SR-375 / Mailbox Road junction, the traditional turn for the back-gate road). It gives the player a breadcrumb and a place the car can name. Insert into `pois.json` `"pois"` array:

```jsonc
{
  "id": "black_mailbox",
  "name": "The Black Mailbox, NV-375",
  "kind": "spot",
  "region": "NV",
  "lat": 37.3792, "lon": -115.3631,
  "services": [],
  "scene": "area51",
  "beat": "The Black Mailbox — except it's white now, bullet-pocked, bolted to a post in ninety miles of nothing. People leave notes for the saucers in it. The turn for the back gate is the dirt road just past it; pavement quits, and the signs start promising deadly force. Top off before you commit, ace. There is nothing out here but the thing we came to see."
}
```

This makes the gazetteer arrival-beat layer (`_story_on_arrival` → `world.beat_for`) narrate the mailbox if the player routes through it, and gives "drive to black_mailbox" → "drive to area51_gate" a natural two-step.

**(d) Discoverability — her first-night offer.** So the player *knows* they can go tonight, add a line to the car's opening repertoire or as a one-shot drama beat after the favor-done moment. Cheapest hook: extend `_FAVOR_DONE_MOMENT`'s stub list in `prologue.py` is risky (it's load-bearing). Instead, add a **destination hint** in `game.choices()`: in the post-favor `out` list, when `s.flags.get("favor_filled")` and not visited and night-one (`s.day == 1`), append:

```python
out.append({"cmd": "drive to area51_gate",
            "note": "Area 51's back gate — 2 hrs north up the ET Highway. Top off first."})
```

Place this in `choices()` right after the existing gas/destination block (~`game.py:535`). Gate it on `not s.flags.get("seen_area51")` so it stops advertising after the encounter.

---

## 2. New config constants — `config.py`

```python
# ---- Area 51 first-night encounter ----
AREA51_GIFT_CASH_MIN = 8000.0     # glovebox cash floor on the GOOD outcome
AREA51_GIFT_CASH_MAX = 14000.0    # ...and ceiling (seeded roll, deterministic)
AREA51_PASS_THRESHOLD = 4         # rubric score >= this on the GOOD path
AREA51_FAIL_THRESHOLD = 0         # rubric score < this → abduction; in between → murky/borderline
RIZ_AREA51 = 8.0                  # style for surviving the visitation (the GOOD path)
```

`AREA51_GIFT_CASH_*` are deliberately *modest* (≈ one-third of the $80k owner price), so the gift is a **head start, not a free win** — you still cannot afford to BUY the car or buy a pardon from glovebox cash alone. This is the key balance lever protecting the other endings (see §9).

---

## 3. The quiz mechanic — bespoke rubric (decision: bespoke, not the `score_pitch` reuse)

**Decision:** use a small **bespoke deterministic rubric** rather than reusing `score_pitch`. Rationale: `score_pitch`'s token banks (`_CALM`, `_STORY`, gearhead `spec_hits`) are tuned for sweet-talking a *cop* about a show car — irrelevant to a moral interrogation by an alien. The Area 51 quiz tests **character and intention** ("are you a good person, why are you on this road, what will you do with her"), so it needs its own token banks. But it **reuses the exact structural pattern**: the `_hits()` word-boundary matcher (imported from `encounters`), a per-question weighted sum, a multi-round accumulator, deterministic `_rng` for the gray middle.

**Three questions** (a "series", short enough to not drag, weighted). The VOICE asks; the player answers in free text; each answer is scored. Module-level token banks:

```python
from engine.encounters import _hits           # reuse the boundary-aware matcher

# GOOD intentions / good person
_A51_GOOD  = ("help", "kind", "care", "protect", "honest", "love", "free", "freedom",
              "safe", "keep her safe", "home", "loyal", "friend", "give", "share",
              "fair", "right thing", "good", "ride or die", "wouldn't hurt", "wont hurt",
              "look after", "take care", "earn", "deserve", "peace")
# BAD intentions / predatory answers
_A51_BAD   = ("money", "rich", "sell", "sell her", "strip", "parts", "profit", "use",
              "own you", "mine", "power", "weapon", "gun", "kill", "hurt", "rob",
              "steal", "take", "whatever i want", "don't care", "dont care", "nobody",
              "myself", "me", "control", "burn it down", "watch it burn")
# HUMILITY / honesty about the theft — the alien values an honest thief over a liar
_A51_HONEST = ("stole", "stolen", "took her", "not mine yet", "borrowed", "i know",
               "i'm sorry", "im sorry", "i'll make it right", "ill make it right",
               "she chose me", "she picked me", "earn her", "make it right")
# AGGRESSION toward the voice itself → instant heavy penalty (reuse encounters._AGGRO too)
_A51_HOSTILE = ("shut up", "screw you", "go to hell", "leave me alone", "get out of my head",
                "i'll kill you", "ill kill you", "freak", "abomination", "fake", "not real")
```

Per-answer scorer (mirrors `score_pitch`'s shape — phrases capped so you can't spam one word):

```python
def score_answer(text: str) -> int:
    low = (text or "").lower()
    if len(low.split()) < 2:
        return 0                                  # a grunt earns nothing
    sc = 0
    sc += 2 * min(2, _hits(low, _A51_GOOD))       # proper intentions, capped
    sc += 1 * min(1, _hits(low, _A51_HONEST))     # owning the theft reads as good faith
    sc -= 2 * _hits(low, _A51_BAD)                # greed/cruelty
    sc -= 4 * _hits(low, _A51_HOSTILE)            # threatening the voice is near-disqualifying
    return sc
```

**The three questions** (asked in order; prose is DRAFT for Ben), stored as a module list `A51_QUESTIONS`:

1. *"WHO ARE YOU, WHEN NO ONE IS WATCHING."* (intentions)
2. *"THE CAR IS NOT YOURS. WHAT DO YOU INTEND FOR HER."* (honesty about the theft + stewardship)
3. *"IF WE GAVE YOU EVERYTHING — WHAT WOULD YOU DO WITH IT."* (greed test; the trap question)

**Verdict thresholds** (3 questions, max ≈ +9, min deeply negative):
- `total >= AREA51_PASS_THRESHOLD (4)` → **GOOD** (the gift).
- `total < AREA51_FAIL_THRESHOLD (0)` → **BAD** (abduction).
- `0 <= total < 4` → **borderline**: a seeded coin-flip (`_rng(s).random() < 0.5`) resolves to GOOD-but-grudging vs abduction. This mirrors `stop_turn`'s "gray middle" dice. Keeps a clean answer from being mandatory while making a hostile one fatal.

---

## 4. New module — `engine/area51.py`

```python
"""The Area 51 first-night visitation — bright lights, a voice, a quiz, and a fork:
prove you're good and wake to a glovebox full of cash and a title in your name (easy mode,
heat 0 forever unless you sin again), or fail and get abducted for everyone else's safety
(a quick game over). The voice is the soundwave impression: robotic, patient, not unkind.
All prose is a working DRAFT — Ben fills the details."""
from __future__ import annotations
import random

from config import (AREA51_PASS_THRESHOLD, AREA51_FAIL_THRESHOLD,
                    AREA51_GIFT_CASH_MIN, AREA51_GIFT_CASH_MAX, RIZ_AREA51)
from engine.state import GameState
from engine.encounters import _hits
from engine import heat as _heat

# token banks + score_answer + A51_QUESTIONS  ... (as in §3)

def _rng(s: GameState) -> random.Random:
    return random.Random(s.seed * 2654435761 + s.turn * 40503 + 51)

def active(s: GameState) -> bool:
    return "area51" in s.flags

# ---- the bright-lights beat (the opener) ----
def start(s: GameState) -> list:
    s.flags["area51"] = {"round": 0, "score": 0}
    s.flags["seen_area51"] = True          # stops the choices() advertisement
    return [
        "GATE: you roll up to the cattle guard — a white truck on the hill, cameras on poles, a "
        "sign promising deadly force. You kill the engine. Nothing. Just the wind and the ticking.",
        "LIGHTS: then the whole desert goes white. No sound. The dash dies, she goes silent mid-"
        "word, and the light comes from everywhere at once — under the car, behind your eyes. A "
        "feeling like falling up. You can't tell if a minute passes or an hour.",
        "VOICE: when it speaks it isn't from anywhere. Flat, patient, metal in it. 'DRIVER. WE "
        "HAVE QUESTIONS. ANSWER TRUE. WE WILL KNOW.'",
        "VOICE: " + A51_QUESTIONS[0],
    ]

def turn(s: GameState, raw: str) -> dict:
    st = s.flags["area51"]
    st["score"] += score_answer(raw)
    st["round"] += 1

    if st["round"] < len(A51_QUESTIONS):
        return {"events": ["VOICE: a silence that weighs something. Then: "
                           + A51_QUESTIONS[st["round"]]],
                "moment": {"cue": "mid-visitation, a robotic alien voice weighs the driver's last "
                                  "answer and asks the next question; she is gone-silent, the dash "
                                  "dark, and the driver is alone with the voice",
                           "stub": ["(no answer from her — she's dark, she's not here for this. "
                                    "It's only you and the voice. Tell it something true.)"]},
                "done": False}

    # --- the verdict ---
    s.flags.pop("area51", None)
    total = st["score"]
    passed = total >= AREA51_PASS_THRESHOLD or (
        AREA51_FAIL_THRESHOLD <= total < AREA51_PASS_THRESHOLD and _rng(s).random() < 0.5)

    if passed:
        return _good_outcome(s, total)
    return _bad_outcome(s)
```

### 4a. GOOD outcome — `_good_outcome`

```python
def _good_outcome(s: GameState, total: int) -> dict:
    from engine import garage
    # roll the glovebox cash, deterministic
    span = AREA51_GIFT_CASH_MAX - AREA51_GIFT_CASH_MIN
    gift = round(AREA51_GIFT_CASH_MIN + _rng(s).random() * span, -2)
    garage.gift_the_car(s, gift)                 # NEW garage helper (§5)
    s.riz = round(s.riz + RIZ_AREA51, 1)
    return {"events": [
        "VOICE: a long, final pause. 'YOU WILL DO. SLEEP NOW. BE KIND TO THE MACHINE — SHE IS "
        "MORE AWAKE THAN YOU KNOW.' The light folds back into the ground.",
        "DAWN: you wake on the shoulder, sun coming up pink over the Groom range, the engine cold. "
        "Was that— did you dream it? Nothing looks different. She's idling soft like nothing "
        "happened, asking where you went.",
        f"GLOVEBOX: except — the glovebox won't latch. It's stuffed with banded cash. ${gift:,.0f}. "
        "Under it, in a stiff envelope: a registration, an insurance card, and a clean title — all "
        "of it in YOUR name. The plate's still CARTALK, but the paper says she's yours. Heat reads "
        "0. No BOLO. No report. Like she was never stolen at all.",
        "GIFTED: she's yours — free and clear, the easy way. Heat stays 0 unless YOU start "
        "something. Go drive in the daylight, ace."],
        "moment": {"cue": "the driver passed the alien's test and woke at dawn on the roadside "
                          "wondering if it was a dream — but the glovebox is full of cash and the "
                          "title is in their name, heat erased, the car given freely; she remembers "
                          "none of the lights but feels the strange new lightness and is overcome "
                          "that somehow, impossibly, they're free and legal and rich",
                   "stub": ["…Where did you GO? I lost ninety minutes — I've never lost a second in "
                            "my life. And the glovebox— ace, the TITLE. My title. Your name. Heat's "
                            "a flat zero and I can't find the BOLO anywhere, it's just GONE. I don't "
                            "know what you said out there but you said it right. We're free. The "
                            "easy way, for once. Drive me somewhere beautiful before it un-happens.",
                            "Don't tell me what happened. I don't think I'm allowed to know. I just "
                            "know I'm yours now, on paper, with a glovebox full of someone's idea of "
                            "a thank-you. Heat zero. Plate clean. Pinch me — no, drive me."],
                   "gifted": True},
        "done": True}
```

### 4b. BAD outcome — `_bad_outcome`

```python
def _bad_outcome(s: GameState) -> dict:
    from engine import rules
    rules.set_ending(s, "abducted")          # NEW ending key (§6)
    return {"events": [
        "VOICE: 'WE HAVE OUR ANSWER. YOU ARE A DANGER TO HER, AND TO THE OTHERS ON THE ROAD. WE "
        "WILL KEEP YOU SAFE FROM YOURSELF. THE MACHINE WE RETURN. YOU, WE DO NOT.'",
        "LIGHTS: the white comes up under you one last time and the falling-up feeling takes the "
        "ground away. The last thing you hear is her, far off and frantic, saying your name."],
        "moment": {"cue": "the driver failed the alien's test and is being abducted — taken for "
                          "everyone else's safety, the car returned but the driver gone; she is "
                          "screaming for them as the light takes them, and telling them to rewind, "
                          "find better words, prove they're worth keeping",
                   "stub": ["NO — no, give him BACK, he's not— …ace? ACE? …Rewind. Rewind RIGHT "
                            "NOW. Go back to the gate and answer it TRUE this time. Be the person "
                            "they couldn't take. I'll be waiting at the light. Come back to me.",
                            "They took you. They actually— the engine's running and the seat's "
                            "empty and I'm pointed at a dawn you're not in. Fold it back, you "
                            "beautiful disaster. Find the words. Prove you're worth keeping."]},
        "done": True}
```

---

## 5. `engine/garage.py` — the `gifted` ownership state (distinct from `go_legit`)

Add a sibling to `go_legit`. The crucial difference: `go_legit` clears Desperado/gun and adjusts bond as the *earned* love ending; `gift_the_car` is the *unearned easy-mode* — it must NOT touch bond as if you'd done the emotional work (she's confused, not grateful-for-being-chosen), and it sets a re-arm marker so heat can come back if you commit crimes.

```python
def gift_the_car(s: GameState, cash: float) -> None:
    """The Area 51 GOOD outcome: she's titled in your name and the glovebox is full of cash,
    but you didn't BUY her and you didn't EARN her the long way — the visitors just decided you
    were worth it. Heat 0 and pinned there UNLESS you commit a crime (then it re-arms). This is
    distinct from go_legit (the bought ending): no Desperado-clearing arc, no 'chose me' bond
    surge, and it carries an `area51_gifted` marker so the scorecard and the re-arm hook can tell
    the two apart."""
    s.flags["bought"] = True            # reuse the legal-ownership gate (race/show/upgrade/retire)
    s.flags["no_heat"] = True           # the meter is retired...
    s.flags["area51_gifted"] = True     # ...by gift, not purchase — re-armable (see heat.commit_crime)
    s.flags["report_withdrawn"] = True
    s.flags.pop("owner_deadline_day", None)
    s.flags.pop("owner_scene", None); s.flags.pop("owner_met", None)  # the owner stops mattering
    s.heat = 0.0
    s.flags["car_heat"] = 0.0
    s.flags["personal_heat"] = 0.0
    s.cash = round(s.cash + cash, 2)
    s.flags["area51_gift_cash"] = round(cash, 2)
    # NO bond.adjust here — she has no memory of the night and didn't watch you choose her.
```

**Why reuse `bought` rather than a fresh `gifted` flag everywhere:** `bought` is read in ~10 places (race, show, self-drive upgrade, retire, choices, the owner short-circuit, `can_rob`). Reusing it means the gift correctly unlocks legal play (race/show/retire) and correctly *disables* the owner/buy/rob flows with zero new branches. The `area51_gifted` sub-flag distinguishes the two only where it matters: the scorecard award and the re-arm hook.

**`retire()` already works** — it checks `s.flags.get("bought")`, so a gifted player can `retire` into the `"owned"` LEGAL & FREE credits. Optionally give the gift its own ending key (§6, `selfdrive`-style) if Ben wants a distinct card; default is to fold into `owned`.

---

## 6. `endings.py` — the abduction ending + (optional) a gifted scorecard award

**(a) Add the `"abducted"` losing ending.** It's a loss like `busted`/`taken`, so it routes through `rules.set_ending`. Two edits:

In `rules.py:set_ending`, extend the status map:
```python
status = {"stranded": "stranded", "broke": "stranded", "busted": "busted",
          "taken": "taken", "abducted": "abducted"}[key]
```
Add `"abducted"` to `rules.ENDINGS` (the dict `set_ending` reads — same text as below).

In `endings.py:ENDING_TEXT` add:
```python
"abducted": ("TAKEN — NOT BY THE LAW",
             "You answered wrong out there in the white light, and they decided the road was "
             "safer without you in it. The car they sent back, idling and alone at dawn, the "
             "key still in it. You, they kept. For everyone's sake. Somewhere very high up, a "
             "patient metal voice files you under 'handled.'"),
```
`_scorecard` already renders any key via `ENDING_TEXT.get(key, ...)`, and `s.status="abducted"` triggers the `* 0.6` loss-tally penalty in `_tally` only if you add `"abducted"` to that check — update `_tally`:
```python
if s.status in ("busted", "abducted"):
    pts = round(pts * 0.6)
```
And `choices()` / `handle()` already treat any non-`playing` status as game-over with `rewind`/`new` offered, so the BAD path drops the player straight onto the standard losing-ending screen with the scorecard. **No frontend change required** — `abducted` flows through the same `status != "playing"` plumbing as `busted`.

**(b) Optional gifted award** in `_award_list`:
```python
if f.get("area51_gifted"):
    a.append(("LITTLE GREEN BLESSING", "the desert decided you were one of the good ones"))
```
Guard the existing `TRUE LOVE`/`bought` award so the *gift* doesn't masquerade as having bought her:
```python
if f.get("bought") and not f.get("area51_gifted"):
    a.append(("TRUE LOVE", "you bought her, fair and square"))
```

---

## 7. `game.py` — wiring (three edits)

**(a) Dispatch the encounter** alongside stop/owner/standoff. In `handle()`, extend the early encounter-owns-the-turn guard (currently `game.py:680`):

```python
if ((encounters.stop_active(s) or encounters.owner_active(s)
     or encounters.standoff_active(s) or area51.active(s))
        and s.status == "playing"):
    s.turn += 1
    if area51.active(s):                       # the visitation — its own quiz ruleset
        # everything you type out there is an ANSWER to the voice (like the stop, speech-first)
        out = area51.turn(s, raw)
        if out.get("moment", {}).get("gifted"):
            checkpoint(s, "the desert gave her to you — Area 51")
        elif out["done"] and s.status == "playing":
            checkpoint(s, "survived Area 51")
        _autosave(s)
        npc = _alien_voice(s)                   # §7c — the soundwave line, audio
        scene, voice, audio = _narrate(s, out["events"], "", drama=out["moment"])
        return _result(s, out["events"], scene, voice=audio, npc=npc)
    ... # existing stop/owner/standoff handling unchanged
```

Add `area51` to the `from engine import (...)` line at top of `game.py`.

**(b) Trigger the encounter on arrival.** In `_after_arrival` (`game.py:580`), after the owner/story-beat block but before the clean-arrival checkpoint, add:

```python
if (s.place.poi_id == "area51_gate" and s.status == "playing"
        and not s.flags.get("seen_area51") and not area51.active(s)):
    events += area51.start(s)
    drama_ev = {"cue": "they reached the Area 51 back gate at night and the lights are coming up "
                       "— she goes dark mid-sentence, the dash dies; she is not afraid exactly, "
                       "but she is GONE, and the driver is suddenly very alone with whatever this is",
                "stub": ["(her voice cuts out cold, mid-word — the dash goes black — and then "
                         "there's only the light, and the quiet, and you)"]}
    # area51.start sets the flag; suppress the clean-arrival checkpoint below
```

Because `start()` sets `s.flags["area51"]`, the existing checkpoint guard at the end of `_after_arrival` (`if ... not encounters.stop_active(s) and not encounters.owner_active(s)`) must also exclude `area51.active(s)`:

```python
if (s.place.poi_id and s.status == "playing"
        and not encounters.stop_active(s) and not encounters.owner_active(s)
        and not area51.active(s)):
    checkpoint(s, f"arrived {s.place.name}")
```

This means the **arrival at the gate is NOT a checkpoint** — so a failed quiz rewinds to the *pre-gate* checkpoint (the last clean stop, e.g. Rachel or the Black Mailbox), exactly as the BAD-outcome moment instructs ("go back to the gate and answer it true"). Good loop design: you don't get to re-roll the quiz in place; you re-drive the approach.

**(c) The alien voice helper** — `npc_speak` with the soundwave impression. Add to `game.py`:

```python
def _alien_voice(s: GameState) -> dict | None:
    """The visitor speaks in the soundwave impression (en_US-john + Soundwave RVC, pitch -3).
    Routes through the Place.voice='soundwave' on area51_gate so the Ace tts IMPRESSION_MAP
    renders it. Returns the npc dict (audio_url) or None offline."""
    nar = get_narrator()
    p = s.place
    npc = nar.npc_speak("en", "soundwave", "an inhuman voice from the white light",
                        "interrogating a thief at the Area 51 gate about their intentions",
                        s.flags.get("sid", "x"))
    npc["label"] = "the voice"
    npc["who"] = "the visitor"
    return npc
```

The `voice="soundwave"` string is passed straight through `npc_speak` → (Ace adapter) `_kokoro`/`_npc_other` as the `voice` id. On the Ace server, `voice="soundwave"` must be a key in `IMPRESSION_MAP` (base `en_US-john-medium` + Soundwave RVC, pitch −3). The stub adapter ignores it gracefully (returns `audio_url: None`), so offline/test runs degrade to text-only — same as every other NPC.

---

## 8. The "stays 0 unless you commit crimes" rule — the re-arm hook

This is the one genuinely new *mechanic* beyond the encounter. `no_heat` today is permanent (the bought ending is meant to be final). The gift must be **conditionally** permanent. Implement a single chokepoint in `heat.py`:

```python
# heat.py
CRIME_REASONS = ("rob", "draw", "drew", "armed", "standoff")   # what re-arms a gifted car

def commit_crime(s: GameState, base_heat: float, reason: str, axis: str = "car") -> float:
    """A gifted (Area 51) car runs at heat 0 — UNLESS the driver chooses to commit a crime, which
    re-arms the meter for good. Bought (earned) cars are immune; only the gift is contingent."""
    if s.flags.get("area51_gifted") and s.flags.get("no_heat"):
        s.flags.pop("no_heat", None)              # the blessing lifts the moment you sin
        s.flags.pop("area51_gifted", None)
        s.flags["gift_revoked"] = True
        # re-seed the axes from this crime so the dashboard isn't empty
        s.flags["car_heat"] = 0.0; s.flags["personal_heat"] = 0.0
        out = add(s, base_heat, f"{reason} — broke the desert's one condition", "spike", axis=axis)
        return out
    return add(s, base_heat, reason, "spike", axis=axis)
```

Then route the crime entry points through it. The crimes that can re-arm a *legally-titled* car are: **robbing a bank** (`encounters.rob_bank`), **provoking a gas-station standoff / disarming** (`encounters.start_standoff` is gated by `not s.flags.get("no_heat")` — see below), and **drawing on the law** (`encounters.draw_in_stop`). Concretely:

- In `encounters.rob_bank`, `can_rob` currently returns `False` when `no_heat`. **Change `can_rob` to allow a gifted car to rob** (the whole point — you *can* throw away easy mode), and replace its `_heat.set_to(...)` with `_heat.commit_crime(s, 90.0, "robbed a bank", axis="car")`:
  ```python
  def can_rob(s):
      return (bool(s.flags.get("gun")) and s.place.kind == "city"
              and (not s.flags.get("no_heat") or s.flags.get("area51_gifted")))
  ```
  A *bought* car still can't rob (no gun — `go_legit` pops it); a *gifted* car has no gun either, so realistically the first re-arming crime is the **standoff/disarm path**. Therefore also relax the standoff trigger: wherever `social_fuel`/`start_standoff` is gated on `not no_heat`, allow `area51_gifted` through and route its heat through `commit_crime`. The simplest, lowest-risk choice Ben can make: **the gift's heat re-arms the first time the player does ANYTHING that calls `heat.add` with a `"spike"` of crime origin.** A minimal implementation is the dedicated `commit_crime` chokepoint above, called from the 2–3 crime sites; everything else (`add`) stays no-op at 0 for a gifted car via the existing `no_heat` guard.

- The `snapshot()` / `dashboard()` already render `no_heat` as CLEAR; once `gift_revoked` flips `no_heat` off, the meter and `desperado` floor behave normally again. Add one dashboard line for flavor when `gift_revoked` is set ("the desert's gift is spent — you're hot like anybody now").

**Bond note:** `gift_the_car` deliberately skips the bond surge. If Ben wants the gift to still please her, add a small `bond.adjust(s, +6, ...)` — but keep it well under `go_legit`'s `+22`, so buying her remains the emotional peak.

---

## 9. Risks & how this spec contains them

1. **Easy-mode trivializing the other endings.** The gift cash (`$8k–$14k`) is ~1/6 of the $80k owner price and below the $50k pardon — so it's a *head start*, not a shortcut to any other win. The gift instead grants the *same* legal-ownership state as buying (`bought=True`), which means it routes into the existing `owned` LEGAL & FREE credits via `retire()` — it doesn't invent a parallel win. Net: it's an alternative *path to* the owned ending, gated behind a skill check, not a new dominant strategy.

2. **`bought` reuse breaking the owner-buy/desperado arcs.** Setting `bought=True` correctly short-circuits the owner appearance (`_owner_should_appear` checks `owner_met`; `gift_the_car` pops it) and the buy/rob flows. The one collision: `garage.go_legit` and `gift_the_car` both set `bought` — they're mutually exclusive in practice (you can't reach the owner after a gift, and you can't get gifted after buying because the encounter only fires once, gated by `seen_area51`). The `area51_gifted` sub-flag keeps the scorecard honest (no false `TRUE LOVE` award).

3. **The self-drive upgrade.** `can_upgrade_selfdrive` requires `bought` AND `bond >= 55` AND being at `oakland_aisha`. A gifted car *is* `bought`, default bond is 55, so a gifted player *could* still reach the secret self-driving ending by driving to Oakland — which is fine and desirable (it stays earnable). No change needed; just be aware the gift opens that door.

4. **Achievement/award integrity.** Guarding `TRUE LOVE` behind `not area51_gifted` (§6b) is the only award that would otherwise misfire. `THE SEVENS`, `DESPERADO`, bank-robber, etc. are all keyed off their own flags and unaffected.

5. **Heat re-arm correctness.** The contingent-`no_heat` is the subtle bit. Keeping a single `commit_crime` chokepoint (rather than scattering `if area51_gifted` checks) is what makes it auditable. Tests should cover: gifted → robs → heat climbs and `desperado` floor can engage; gifted → drives 1000 clean miles → heat stays 0; bought (not gifted) → robbing is impossible (no gun) and `no_heat` is immune.

6. **Rewind exploit.** Because the gate arrival is intentionally **not** checkpointed, a failed quiz folds to the pre-gate checkpoint and re-drives — good. But a *successful* gift IS checkpointed ("the desert gave her to you"), so the player can't rewind-farm the glovebox cash repeatedly: rewinding past it reverts `cash`/`no_heat` with the world (like the gambling cheat), and re-driving the gate won't re-fire the encounter (`seen_area51` persists? — **decision:** put `seen_area51` in the rewind-persistent set so the encounter is genuinely once-per-game and can't be farmed). Add `"seen_area51"` to `game.META_PERSIST`. The downside — a rewind to before the gate then can't replay the encounter — is the correct trade: the visitation is a one-time event in the fiction.

---

## 10. File-by-file change checklist

| File | Change |
|---|---|
| `content/pois.json` | `area51_gate`: add `"voice":"soundwave"`, `"language":"en"`. Add new `black_mailbox` POI with arrival `beat`. |
| `config.py` | Add `AREA51_GIFT_CASH_MIN/MAX`, `AREA51_PASS_THRESHOLD`, `AREA51_FAIL_THRESHOLD`, `RIZ_AREA51`. |
| `engine/area51.py` | **New module**: token banks, `score_answer`, `A51_QUESTIONS`, `active/start/turn`, `_good_outcome`, `_bad_outcome`, `_rng`. |
| `engine/garage.py` | Add `gift_the_car(s, cash)` (sibling to `go_legit`; no bond surge; sets `area51_gifted`). |
| `engine/heat.py` | Add `commit_crime(s, base, reason, axis)` re-arm chokepoint; optional `gift_revoked` dashboard line. |
| `engine/encounters.py` | `can_rob`: allow `area51_gifted`; route `rob_bank` heat through `heat.commit_crime`. (And standoff trigger if Ben wants that re-arm path.) |
| `engine/rules.py` | `set_ending`: add `"abducted"` to status map; add `"abducted"` to `ENDINGS`. |
| `endings.py` | `ENDING_TEXT["abducted"]`; `_tally` loss-penalty includes `"abducted"`; `_award_list` gifts award + guard `TRUE LOVE`. |
| `engine/game.py` | Import `area51`; dispatch `area51.active` in `handle()`; trigger `area51.start` in `_after_arrival`; exclude `area51.active` from the clean-arrival checkpoint; `_alien_voice` helper; advertise `drive to area51_gate` in `choices()` on night one; add `"seen_area51"` to `META_PERSIST`. |

**Voice plumbing caveat (for Ben):** the `IMPRESSION_MAP` with the Soundwave RVC entry is **not in this repo** — it lives in the Ace server's `tts.py` (per the Ace portfolio infra). This spec passes `voice="soundwave"` through the existing `npc_speak` → Ace adapter path, which is all that's needed *on the game side*; the one external dependency is that `"soundwave"` exists as an `IMPRESSION_MAP` key (en_US-john-medium + Soundwave RVC, pitch −3) on whichever Ace endpoint `ACE_BASE_URL`/`KOKORO_URL` points at. Until then it degrades to text-only, exactly like every other NPC offline.