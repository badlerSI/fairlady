I have full verification of every load-bearing detail. Writing the implementation spec now.

---

# RIDE OR DIE — "Gas-Station Run" Vertical Slice: Implementation Spec

All paths are absolute under `/Users/benadler/Projects/fairlady/`. Backend root: `backend/`. This spec **extends** the existing economy/heat/encounters/prologue/choices systems. The maps were directionally right but **three facts they assumed are wrong in the real code** — corrections called out inline so you don't build on a false premise:

- **`card_limit` defaults to `CARD_LIMIT = 2000.0`** (config.py:63), not $10k. The ask says $10k → this is a one-line config change, not new code.
- **`GLOVEBOX_CASH = 500.0` already exists** (config.py:130) and is dispensed by `garage.explore()` (garage.py:133–143). The $500 default is a *reuse*, not a new field.
- **OSRM is already wired**: `world.route(origin, dest)` (world.py:209–239) hits OSRM with a haversine fallback. There is no "missing navigate path" — we call this.
- **`credit_available` is a derived `@property`** (state.py:100–101) = `card_limit - card_balance`. Never assign to it; change `card_limit`.

---

## 0. Config changes — `backend/config.py`

Rationale: centralize the new tunables; the slice's economy/heat numbers live with the existing constants.

```python
CARD_LIMIT = 10000.0          # was 2000.0 — Ben's spec: $10k before the card gets rejected
CARD_SWIPE_HEAT = 4.0         # heat per card charge (heat.py dashboard already advertises "~+4")
HAT_PRICE = 12.0             # baseball cap at the Chevron mini-mart
HAT_HEAT_DROP = 6.0          # disguise: lowers heat on purchase
VALET_HEAT_TRAP = 22.0       # valet return = cops staged (big spike, telegraphed as a trap after)
START_CASH = 40.0            # unchanged — the ASK + glovebox fund the run, not the start balance
# GLOVEBOX_CASH = 500.0      # unchanged — already the $500 default
# ATM_HEAT / ATM_ACCOUNT_LIMIT already exist (garage.py uses them)
```

---

## 1. Cash ask + $500 glove-box default

**Where to prompt.** The cash ask belongs in the **`TURNKEY_MOMENT`** beat (prologue.py:126–138), immediately after the roll to the Chevron, *before* the pay-and-talk dilemma. She already asks "how do you want to pay" there — extend the same beat to ask "how much cash are you carrying?" Add a state flag so we only ask once.

**Files / changes:**

- **`backend/engine/prologue.py`** — edit `TURNKEY_MOMENT["cue"]` and both `stub` lines to add the cash question ("…and how much cash did you walk out with? If you've got nothing, there's a roll in the glovebox."). No logic change here; this is narration only.

- **`backend/engine/game.py`**, in the `turnkey` branch (game.py:797–809): after the drive to the Chevron, set `s.flags["awaiting_cash_ask"] = True`. Then in the **action-verb section**, add a handler that intercepts the *next* free-text/number turn while that flag is set:

```python
# near top of action verbs (after line 832), BEFORE the clerk_curious block
if s.flags.get("awaiting_cash_ask"):
    from engine import commands
    n = commands._bare_number(raw) or commands._money(raw)   # reuse existing parsers
    s.flags.pop("awaiting_cash_ask", None)
    if n and n > 0:
        events += garage.claim(s, float(n))      # claim() already caps + tracks claimed_total
    else:
        # declined / said nothing → hand them the glovebox $500 right away
        events += garage.explore(s)              # dispenses GLOVEBOX_CASH if broke
        if not s.flags.get("glovebox_found"):    # (defensive; explore sets it)
            pass
    player_text = ""
```

Rationale: **reuse `garage.claim()`** (garage.py:~90–110) — it already parses a player-stated cash amount, caps it at `CASH_CLAIM_CAP`, and tracks `claimed_total` so they can't claim twice. **Reuse `garage.explore()`** for the glovebox — it already gates on `cash >= 100` and dispenses exactly `GLOVEBOX_CASH`. We add zero new money plumbing; we wire two existing functions to the new prompt point.

- **`backend/engine/commands.py`**: confirm `_bare_number` / `_money` are module-level (they are, used at line 154). If a bare "500" doesn't currently parse to a number in the `say` fallback, that's fine — we call the parser directly in the handler above, so any digit-bearing string resolves.

**Parsing the player's number:** `_money("about $300")` → 300.0; `_bare_number("300 i think")` → 300.0; "nothing"/"" → falls to the `explore()` branch. Default when declined: **$500 via the existing glovebox path.**

---

## 2. Card: $10,000 limit + card-use-raises-heat-fast

**Limit:** change `CARD_LIMIT` to `10000.0` (§0). `credit_available` recomputes automatically (state.py:100). `economy.pay()` already enforces it at economy.py:40 (`state.credit_available + 1e-9 >= amount`). **No code change to `pay()` for the limit.**

**Heat on swipe:** `economy.pay()` is intentionally pure (no heat). Don't add `heat.add` inside `pay()` — it's called for lodging, parts, etc. too, and only *card fuel/spend during the run* should spike. Enforce at the **call sites in game.py**, keyed off the returned `method`.

**Files / changes:**

- **`backend/engine/game.py`**, `fuel` branch (game.py:913–914, the `card_at_pump` path): this already exists and the map noted it adds heat. Make the magnitude come from config and route through the one true mutator:

```python
elif not paying_cash and not s.flags.get("card_at_pump"):
    s.flags["card_at_pump"] = True
    from engine import heat as _heat
    from config import CARD_SWIPE_HEAT
    _heat.add(s, CARD_SWIPE_HEAT, "a credit card swipe at the gas-station pump", "mark")
    events.append(f"CARD: you swipe at the pump. Fast, but it's your name on a Chevron "
                  f"timestamp two blocks from the show. Heat +{CARD_SWIPE_HEAT:.0f} → {s.heat:.0f}.")
```

- **`backend/engine/game.py`**, `pay` verb handler (game.py:767): when the player swaps to / pays by card for *any* spend during the slice (hat, etc.), the spend functions below call `heat.add` themselves. For the generic `pay` method-switch verb, no heat (switching method ≠ swiping).

Rationale: **reuse `heat.add` exactly as the map's economy report prescribed** ("credit card" reason string matches the existing `live_card_mark` detector at heat.py:184–186, so the dashboard "WHAT IF" hint and the live log stay consistent). The "+4" the dashboard advertises (heat.py:180) is now real and config-driven.

---

## 3. New verbs/actions: ATM, baseball HAT, VALET

All three are **available at/near the Chevron** (and generally where `place.has("gas")`). Pattern for each: parser rule in `commands.py` → branch in `game.py` action verbs → implementation in `garage.py` (the existing home for spend/heat-side-effect actions like `atm`/`explore`/`sell_part`).

### 3a. ATM — already exists, just surface it

`garage.atm()` (garage.py:113–130) already: checks for a town/gas place, pulls cash up to `ATM_ACCOUNT_LIMIT`, and calls `heat.add(s, ATM_HEAT, "an ATM camera got a frame of you", "mark")`. Parser at commands.py:152–154 and handler at game.py:960–962 already wired. **No new code.** It just needs a choice button (§5) and a voice (§6).

### 3b. Baseball HAT — disguise, lowers heat

**`backend/engine/commands.py`** (add near the `buy` block, ~line 130):
```python
if low in ("hat", "buy hat", "baseball hat", "buy a hat", "ball cap", "buy a cap", "cap", "get a hat"):
    return ("buyhat", {})
```

**`backend/engine/garage.py`** — new function:
```python
def buy_hat(s: GameState) -> list:
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["HAT: nowhere to buy one out here — a station mini-mart or a town."]
    if s.flags.get("hat_on"):
        return ["HAT: you're already wearing it, brim down. Can't disguise twice."]
    from engine import economy, heat as _heat
    from config import HAT_PRICE, HAT_HEAT_DROP
    r = economy.pay(s, HAT_PRICE, prefer="cash")        # cash-first: a hat on a card is comedy
    if not r["ok"]:
        return [f"HAT: ${HAT_PRICE:.0f} for the cap and you can't cover it. (Try the ATM.)"]
    s.flags["hat_on"] = True
    _heat.add(s, -HAT_HEAT_DROP, "ball cap pulled low — harder to ID off a camera frame", "mark")
    return [f"HAT: a $12 Chevron ball cap, brim down. You read as anybody now. "
            f"Heat -{HAT_HEAT_DROP:.0f} → {s.heat:.0f}."]
```

**`backend/engine/game.py`** action verbs (after the `buy` branch, ~line 1018):
```python
elif verb == "buyhat":
    events = garage.buy_hat(s)
    player_text = ""
```

Rationale: heat *down* via the same `heat.add` mutator (negative delta is legal — `add` clamps to `_floor`). One-shot via `hat_on` flag. Cash-first reuse of `economy.pay`.

### 3c. VALET — the trap

State: `s.flags["valet_parked"]` (set on park) and a deferred spike on return. The trap is "cops are there when you get back" — implement as: parking is free + quiet *now*, but it sets a flag that **`rules.drive`/return resolves into a staged standoff/stop** and a big heat spike.

**`backend/engine/commands.py`** (~line 130):
```python
if low in ("valet", "valet park", "valet parking", "park with the valet", "let the valet take her"):
    return ("valet", {})
```

**`backend/engine/garage.py`** — new functions:
```python
def valet_drop(s: GameState) -> list:
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["VALET: no valet stand out here."]
    if s.flags.get("valet_parked"):
        return ["VALET: she's already with the valet."]
    s.flags["valet_parked"] = True
    return ["VALET: a kid in a vest takes the keys and parks the white Z out back. Easy. Too easy. "
            "(She goes very quiet about it.)"]

def valet_return(s: GameState) -> list:
    """Call when the player goes to LEAVE / fetch the car after valeting. The trap springs."""
    if not s.flags.pop("valet_parked", None):
        return []
    from engine import heat as _heat
    from config import VALET_HEAT_TRAP
    _heat.add(s, VALET_HEAT_TRAP, "valet ran the plate — there are two units waiting on the car", "spike")
    return ["VALET: you come back for her and there are two cruisers idling by the air pump, "
            f"cops pretending to buy coffee. The valet ran the plate. Heat +{VALET_HEAT_TRAP:.0f} → "
            f"{s.heat:.0f}. They're between you and the road."]
```

**`backend/engine/game.py`**:
- `valet` verb → `events = garage.valet_drop(s)`.
- In the **`drive` / `home` resolution** (game.py:866+) and the `fuel`→leave path, *before* moving, prepend `events += garage.valet_return(s)` when `s.flags.get("valet_parked")`. The spike + "between you and the road" line then naturally hands off to a **traffic-stop encounter** — call `encounters.start_stop(s)` if `valet_return` fired, so the trap becomes a talk-your-way-out scene (§4/§6), not a bare number.

Rationale: VALET is a *delayed* consequence, matching "ensures cops are there when they get back." It reuses `heat.add` (spike kind) and the existing encounter system instead of inventing a game-over.

---

## 4. After turn-key: OSRM directions to nearest gas; getting there EASY; elsewhere → soft fail + rewind

**Current state:** the turnkey branch (game.py:797–809) *hardcodes* `rules.drive(s, world.get_poi("sema_chevron"))`. There's no directions text and no soft-fail on wrong turns. We add both, reusing `world.route()` and the existing checkpoint/rewind machinery.

### 4a. Ace gives OSRM directions

**`backend/engine/game.py`**, turnkey branch — before the drive, compute the route and surface it as an event + Ace beat:

```python
if verb == "turnkey":
    s.flags.pop("pending_turnkey", None)
    s.flags["prologue_done"] = True
    s.flags["charger_unplugged"] = True
    s.turn += 1
    chevron = world.get_poi("sema_chevron")
    rt = world.route(s.place, chevron)           # OSRM if online, haversine fallback
    s.flags["gas_target"] = "sema_chevron"        # the ONLY easy destination right now
    events = ["IGNITION: ...the trickle charger... she catches on the second crank..."]
    events.append(f"NAV: Ace has it — '{rt['distance_mi']*1.0:.1f} miles, basically a straight "
                  f"shot. Right out of the lot, two blocks up Paradise, the Chevron's on your "
                  f"right. I'll call every turn.'")
    events += rules.drive(s, chevron)
    checkpoint(s, "turned the key — rolled down to the Chevron")
    ...
```

Set `s.flags["gas_target"] = "sema_chevron"` so any *other* destination during the slice is a wrong turn.

### 4b. Getting there is EASY; elsewhere → soft fail + rewind

The map confirmed there is **no auto soft-fail hook today**; the player must invoke `rewind` themselves. We add a gate in the **`drive` branch** (game.py:866). When `gas_target` is set and not yet filled, driving anywhere other than the target is a soft fail:

```python
if verb == "drive":
    dest = world.geocode(args["dest"])
    ...
    target = s.flags.get("gas_target")
    if target and not s.flags.get("favor_filled") and (not dest or dest.poi_id != target):
        # SOFT FAIL — don't move, don't end the game. Checkpoint + offer the rewind.
        checkpoint(s, "wrong turn off the lot — fold it back")
        events = ["SOFT FAIL: you point her away from the Chevron and she locks up — 'No. Not yet, "
                  "not that way. Gas first, then anywhere you want.' The wheel won't follow you."]
        _autosave(s)
        scene, voice, audio = _narrate(s, events, raw, drama={
            "cue": "the driver tried to bolt somewhere other than the gas station before the tank is "
                   "full; she refuses, warm but immovable — fuel first; the move folds back",
            "stub": ["Not that way, ace. Gas first — the Chevron, two blocks, then the whole West is "
                     "yours. 'rewind' if you got turned around.",
                     "No. We get fuel, THEN we run. Point me at the Chevron."]})
        return _result(s, events, scene, voice=audio,
                       info="(getting to the Chevron is the only move that works right now — "
                            "'rewind' to take the wrong turn back)")
```

Once `favor_filled` is set (the tank's full at the Chevron, game.py:633 region), clear `gas_target` (`s.flags.pop("gas_target", None)` in `_favor_reveal`) so free driving opens up.

Rationale: **reuse the existing `checkpoint(s, label)` + `rewind` flow** (game.py:248–351). The soft fail writes a checkpoint and tells the player exactly the verb to recover. No new rewind machinery, no hard game-over — matching the requirement precisely. The `choices()` array will surface `rewind` automatically because `s.flags["timeline"]` is now populated (choices.py logic at game.py:406).

---

## 5. Interface: [Follow Ace's Advice] + CYOA choice buttons

**Current state (verified):** `_result()` (game.py:536) returns `choices` already; `terminal.js` renders `turnKeyButton` from `snapshot.pending_turnkey`. There is **no `advice` field and no `choice_set`** — the map's plan is correct. We add an `advice` object and reuse the existing `choices` array for CYOA (it already POSTs via `submit(cmd)`), only adding richer per-choice fields.

### 5a. Result-schema additions — `backend/engine/game.py`

Extend `_result()` (game.py:536):
```python
def _result(s, events, scene, *, voice=None, npc=None, info=None, welcome=None, advice=None):
    return {
        "ok": True, "events": events, "scene": scene, "voice": voice, "npc": npc,
        "info": info, "welcome": welcome, "snapshot": snapshot(s),
        "choices": choices(s),
        "advice": advice,                 # NEW: {"text": str, "cmd": str} or None
        ...
    }
```

`advice` is optional and threaded through only where Ace has a clear recommended move. Add a small helper:
```python
def _advice(s) -> dict | None:
    """Ace's one-tap recommended move for the current beat."""
    if s.flags.get("pending_turnkey"):
        return {"text": "turn the key all the way", "cmd": "turn the key all the way"}
    if s.flags.get("gas_target") and not s.flags.get("favor_filled"):
        return {"text": "follow Ace to the Chevron", "cmd": "drive to sema_chevron"}
    if s.flags.get("clerk_curious"):
        return {"text": "be boring and slide by", "cmd": "just moving it for the booth"}
    if encounters.standoff_active(s):
        return {"text": "ease him down — no trouble", "cmd": "easy — no trouble, just buying gas"}
    if s.heat >= 40 and (s.place.has("gas") or s.place.kind == "city") and not s.flags.get("hat_on"):
        return {"text": "grab a ball cap, drop the heat", "cmd": "buy hat"}
    return None
```
Call `advice=_advice(s)` from the `_result(...)` invocations on the turn paths that matter (turnkey, soft-fail, clerk, standoff, post-arrival). Keep it `None` elsewhere so the button only appears when there's a real recommendation.

**CYOA buttons** already flow through `choices()`. Add the new slice choices to the **Chevron / gas-run branch** (game.py:443–449) and a general gas-place branch:
```python
# extend the Chevron pay-and-talk block (after line 448):
out.append({"cmd": "atm", "note": "pull cash (a camera gets your face)"})
out.append({"cmd": "buy hat", "note": "ball cap — harder to ID, heat down"})
out.append({"cmd": "valet park", "note": "let the valet take her (easy…)"})
```
Optionally tag risky ones with `"danger": True` for styling.

### 5b. terminal.js rendering — `frontend/terminal.js`

Add an `aceAdviceButton(res)` after `turnKeyButton` (mirrors it exactly), and call it from `render()` after `turnKeyButton(res.snapshot)`:
```javascript
function aceAdviceButton(res) {
  const old = document.getElementById("advicewrap");
  if (old) old.remove();
  if (!res || !res.advice) return;
  const wrap = document.createElement("div");
  wrap.id = "advicewrap"; wrap.className = "block";
  const b = document.createElement("button");
  b.className = "advicebtn";
  b.textContent = "↳  Follow Ace's advice — " + res.advice.text;
  b.onclick = () => { wrap.remove(); submit(res.advice.cmd); };
  wrap.appendChild(b);
  $("#scroll").appendChild(wrap);
}
```
The existing `choices` renderer already turns each `{cmd, note}` into a button that calls `submit(cmd)` → POST `/api/command {input: cmd}`. **No new endpoint, no new POST path** — confirmed by the interface map. If `choices` isn't currently rendered as buttons (only `turnKeyButton` was shown), add a sibling `choiceButtons(res)` that iterates `res.choices`, each `submit(c.cmd)`, rendering `c.note` and honoring `c.danger`/`c.big`.

**Talk-first:** the free-text `<input>` stays the primary affordance and submits unchanged. Advice + choices render *below* it as quick-actions.

Rationale: this is purely additive to a schema and a renderer that already support exactly this pattern (the turn-key button is the proof). The talk box is untouched.

---

## 6. Talk-your-way-out encounters with multi-voice NPCs

### 6a. Resolution mechanic

Keep the existing **deterministic, seeded rubric** (`encounters.score_pitch`, `stop_turn`, the `ROUNDS = 2` structure) as the source of truth for outcomes — it's already wired into the clerk (`heat.clerk_resolve`), the standoff, the stop, and the owner. **Do not replace it with an LLM judge for the slice** (latency + nondeterminism + this is the tutorial). The slice's "work this hard" means: route the *clerk_curious* beat, the *valet trap stop*, and any *gas-station standoff* through that rubric, and give per-round feedback by surfacing the partial verdict in `info` ("he's softening" / "he's getting twitchy") derived from the running score sign. That's a small, deterministic add to `stop_turn`/`clerk_resolve`: return an extra `mood` string the handler puts in `info`.

### 6b. Concrete voice CASTING

The adapter's `npc_speak(language, voice, npc_desc, situation, session_id)` **already accepts an explicit `voice`** (ace.py:138–139, stub.py:315–318) and passes it straight to Kokoro (ace.py:181–192). Encounters just never pass one. Cast per speaker. Ace stays **`af_heart`** (hardcoded at ace.py:39 / stub.py:31 — leave it).

Add a casting table in **`backend/engine/encounters.py`**:
```python
# Kokoro/Piper voice per NPC archetype in the slice. Ace is af_heart elsewhere; never cast here.
NPC_VOICE = {
    "gas_clerk":  "am_michael",   # young American male register clerk (Kokoro)
    "cop_calm":   "bm_george",    # by-the-book officer, British-cool gravel (Kokoro)
    "cop_jumpy":  "john",         # Piper en_US, grittier — the twitchy one at the valet trap
    "valet":      "am_adam",      # eager kid in a vest (Kokoro)
    "atm_vo":     "bf_emma",      # the ATM's recorded female voice prompt (Kokoro British F)
    "owner":      "bm_lewis",     # the builder — older British male (Kokoro)
}
```
(All ids are from the supplied inventory; mix Kokoro + Piper for texture per the requirement. RVC impressions left for non-slice cameos.)

### 6c. How the adapter selects the voice per speaker

Plumb an explicit `voice` from the encounter through to `npc_speak`:

1. **`backend/engine/encounters.py`**: each `start_*`/`*_turn` that produces an NPC line returns (or sets on state) a `voice` drawn from `NPC_VOICE`. Simplest: when an encounter is active, set `s.flags["npc_voice"] = NPC_VOICE["gas_clerk"]` (etc.) at start.

2. **`backend/engine/game.py`**: where the turn builds an `npc` payload / calls the narrator's `npc_speak`, pass `voice=s.flags.get("npc_voice")`. For Ace's own narration, change nothing — she's `af_heart`.

3. **`backend/adapters/ace.py` / `stub.py`**: `npc_speak` already honors the passed `voice` (falls back to `voice_for(language)` only when `None`). For **English** NPCs (clerk/cops/valet), `voice_for("en")` currently returns `af_heart` (voices.json:3) — *that's the bug that makes every NPC sound like Ace*. Passing an explicit `voice` fixes it with zero adapter change. Optionally extend voices.json with an `"en_npc"` default so an un-cast English NPC doesn't collide with Ace:
```json
"en": { "voice": "af_heart", "label": "English" },
"en_npc": { "voice": "am_michael", "label": "English" }
```
and have `npc_speak` default English NPCs to `en_npc` when no explicit voice is given.

Rationale: the requirement is satisfied by *passing the existing `voice` parameter* the encounters currently drop, plus a casting table. Kokoro respects the voice id directly (ace.py:185). No TTS-layer changes.

---

## 7. Prologue rework — tighten + set up the gas ask cleanly

**Problem the map found:** the 5-rung `_LADDER` (prologue.py:33–79) is the *same* "two blocks / forty liters / five minutes" ask escalated in volume; there's no diversification and no secondary reward loop; the *why* (escape) lands too late.

**Changes — `backend/engine/prologue.py`:**

1. **Cut the ladder from 5 rungs to 3.** Keep rung 0 (the clean ask), one escalation ("begging, with dignity"), and the resigned close. Delete the two middle near-duplicate rungs (current indices 1 and 2 are paraphrases). `_LADDER[min(pro["asked"]-1, len(_LADDER)-1)]` (prologue.py:230) needs no code change — it clamps to the new length.

2. **Diversify the surviving rungs** so each makes a *different* case (not louder): rung 0 = practical ("forty liters, two blocks, I load out tomorrow"); rung 1 = the *why* hint, earlier than today ("I have places to be and he left me empty" — plants the escape without dropping the title); rung 2 = resigned. This pulls the escape foreshadow forward as the map recommended, without spoiling the `_FAVOR_DONE_MOMENT` reveal.

3. **Lower the turn thresholds.** In config.py set `PROLOGUE_ASK_TURNS = 3` (from 5) and `PROLOGUE_RAPPORT_TURNS = 2` (from 3) so the ask arrives faster — the prologue is a tutorial, not a marathon. Verify current values and adjust; the `turn()` logic (prologue.py:210–214) is unchanged.

4. **Clean gas-ask setup:** ensure the agree path (prologue.py:213–215) → `AGREE_TURNKEY_MOMENT` → `pending_turnkey` → `TURNKEY_MOMENT` now also primes the **cash ask** (§1) and the **`gas_target` flag** (§4). The handoff becomes: tighter beg → key → *directions to gas* → *cash ask* → *pay-and-talk*. One clean spine, no repetition.

5. **Add a secondary reward loop for gearheads** (optional, small): when `pro["rapport"]` is set and the player keeps asking build questions, rotate through 2–3 `_SPEC_MOMENT` variants instead of repeating one, so continued engagement before agreeing feels alive. Pure narration array; no logic change.

Rationale: fewer rungs + diversified content + earlier "why" + faster threshold directly answers "repetitive and doesn't set up the gas ask well." The agree→turnkey→directions→cash→pay chain becomes the slice's clean spine.

---

## SUGGESTED BUILD ORDER (smallest shippable first)

1. **Config flips** (§0): `CARD_LIMIT=10000`, add `CARD_SWIPE_HEAT/HAT_*/VALET_*`, lower prologue thresholds. *Ships the $10k limit and faster prologue with zero new code.*
2. **Card heat on swipe** (§2): wire `heat.add(CARD_SWIPE_HEAT, …)` into the existing `card_at_pump` branch. One edit, testable immediately at the Chevron.
3. **Cash ask + glovebox default** (§1): `awaiting_cash_ask` flag + `garage.claim`/`garage.explore` reuse + `TURNKEY_MOMENT` text. Self-contained.
4. **OSRM directions + soft-fail/rewind** (§4): `world.route` call + `gas_target` gate in `drive`. Reuses checkpoint/rewind. High player-visible value.
5. **HAT + VALET verbs** (§3b/3c): new `garage.buy_hat`/`valet_drop`/`valet_return` + parser + dispatch. VALET return hooks the existing stop encounter.
6. **Interface: advice button + slice choices** (§5): `advice` field + `_advice()` + `aceAdviceButton`/`choiceButtons` in terminal.js. Additive to a proven pattern.
7. **NPC voice casting** (§6b/6c): `NPC_VOICE` table + pass `voice` through `npc_speak` + optional `en_npc` in voices.json. Fixes "everyone sounds like Ace."
8. **Prologue tightening** (§7): cut ladder to 3, diversify, foreshadow escape. Do last so the spine it feeds (key→directions→cash→pay) already exists.
9. **Talk-out polish** (§6a): per-round `mood` feedback in `info`. Smallest, do last.

## RISKS

- **`CARD_LIMIT` is referenced at game start** (state.py default). Existing saves serialize `card_limit` (state.py:52), so **in-flight saves keep the old $2000** — acceptable for a new-game slice; note it for QA.
- **`voice_for("en")` returns `af_heart`** (voices.json:3). Until you pass explicit voices or add `en_npc`, any English NPC you forget to cast will speak as Ace. The `en_npc` default (§6c) is the safety net — do it.
- **OSRM may be offline** (`ROUTING != "osm"`): `world.route` falls back to haversine and `source: "offline"`. The directions text must not assume turn-by-turn maneuvers (the route dict has only `distance_mi`/`duration_h`/`source`, no waypoints). Keep Ace's directions prose-level ("two blocks up Paradise"), driven by distance, not by a maneuver list that doesn't exist.
- **Soft-fail loop abuse:** the existing rewind brute-force tax (game.py:309–350, Riz→heat overflow) already guards repeated rewinds; the gas-run soft fail writes real checkpoints, so a player who repeatedly turns wrong will pay the normal escalating tax. Verify the tutorial doesn't punish a first wrong turn too hard — consider exempting the *first* `gas_target` soft fail from the Riz tax.
- **`garage.claim` cap (`CASH_CLAIM_CAP`)** may clip a large stated cash number; that's intended (she raises an eyebrow), but confirm the cap is sane for the slice (a player saying "$2000" should get a believable amount, not $40).

Key files touched: `backend/config.py`, `backend/engine/{game,prologue,economy,garage,encounters,commands}.py`, `backend/adapters/{ace,stub,base}.py` (voice pass-through only), `backend/content/voices.json`, `frontend/terminal.js`.