I now have full verification of every constant, signature, and call site. Here is the implementation-ready spec.

---

# RIDE OR DIE — Implementation Spec: Two-Axis Heat, PPF Car Disguise, Real Lodging + Clown Motel, Z Events

Verified against the live code (heat.py, gadgets.py, garage.py, economy.py, rules.py, drama.py, game.py, commands.py, state.py, world.py, config.py, pois.json) at `/Users/benadler/Projects/fairlady/backend`. 163 tests currently green; tests assert directly on `s.heat`, so **`s.heat` must remain the authoritative combined meter**.

---

## FEATURE 1 — TWO-AXIS HEAT (car_heat vs personal/driver_heat)

### Design decision (least-disruptive refactor)
Keep `s.heat` as the **derived combined meter** = `max(car_heat, personal_heat)`. Store the two axes in `s.flags` (no dataclass schema change → old saves load unchanged; new fields default to 0). `add()` gains an optional `axis` param; the default path keeps writing the combined meter directly (back-compat), but every real call site passes an axis. Bands/thresholds/law all keep reading `s.heat`.

**Why `max`, not `sum`:** thresholds (45/70/90) are tuned against a single 0–100 meter and the tests assert specific magnitudes (`test_card_swipe_raises_heat_cash_does_not`, `test_atm_under_10k_and_camera_heat`, `test_state_line_cools_heat`). `max` keeps a single-axis hit producing the same `s.heat` it does today, so existing assertions hold. `sum` would double everything and break them.

### 1a. `engine/heat.py` — rewrite `add()` + add accessors

Add module constant and helpers near the top (after `MARK_FADE_MI`):

```python
AXES = ("car", "personal")

def car_heat(s) -> float:
    return float(s.flags.get("car_heat", 0.0))

def personal_heat(s) -> float:
    return float(s.flags.get("personal_heat", 0.0))

def _combined(s) -> float:
    """s.heat is always the max of the two axes (clamped to the live floor)."""
    return round(max(car_heat(s), personal_heat(s)), 1)
```

Rewrite `add()` (lines 76–92). Keep the exact signature plus a new keyword so every existing caller still works:

```python
def add(s, delta, reason, kind="mark", axis=None):
    """One true mutator. axis in {'car','personal'} routes the delta to that axis and
    re-derives s.heat = max(car, personal). axis=None (legacy) writes the combined meter
    directly AND mirrors the change onto BOTH axes proportionally, so the split never goes stale."""
    if s.flags.get("no_heat"):
        s.heat = 0.0
        s.flags["car_heat"] = 0.0
        s.flags["personal_heat"] = 0.0
        return 0.0
    lo = _floor(s)
    before = s.heat

    if axis in AXES:
        key = f"{axis}_heat"
        s.flags[key] = round(max(lo, min(100.0, s.flags.get(key, 0.0) + delta)), 1)
        s.heat = max(lo, min(100.0, _combined(s)))
    else:
        # legacy / untyped: move the combined meter, and apply the same delta to both axes
        # (clamped) so max(car,personal) stays consistent with s.heat.
        s.heat = round(max(lo, min(100.0, s.heat + delta)), 1)
        for a in AXES:
            k = f"{a}_heat"
            s.flags[k] = round(max(lo, min(100.0, s.flags.get(k, before) + delta)), 1)

    s.heat = round(s.heat, 1)
    s.flags["peak_heat"] = max(s.flags.get("peak_heat", 0), round(s.heat))
    real = round(s.heat - before, 1)
    if abs(real) >= 0.1 and reason:
        log = s.flags.setdefault("heat_log", [])
        log.append({"d": real, "r": reason, "k": kind, "day": s.day,
                    "odo": round(s.odometer_mi, 1), "x": axis or "both"})
        del log[:-LOG_KEEP]
    return s.heat
```

Note the log entry gains `"x"` (axis) — `_aggregate()` reads via `e.get(...)`, so old log entries without `"x"` are fine.

**Cooling subtlety:** when a cooling delta is routed to one axis only (e.g. car-disguise drops `car`), `s.heat` (= max) only falls if that axis was the dominant one. That's the intended mechanic — "you fixed the car but your face is still on three cameras." The dashboard must explain this (below), or players will think disguise "did nothing."

For lowers that should cool **both** axes (clean miles, lie-low, state line), call `add(..., axis=None)` — the legacy path already cools both. Keep those as untyped.

### 1b. Route existing deltas to axes

Per Ben: **CARD/ATM/face = PERSONAL; car seen/flashy/tagged/BOLO = CAR.**

| Call site | File:line | Current | New |
|---|---|---|---|
| card swipe (`_card_mark`) | rules.py:77 | `_heat.add(state, dh, "credit card swipe", "mark")` | add `axis="personal"` |
| tow card swipe | rules.py:466 | `"credit card swipe"` | `axis="personal"` |
| ATM camera | garage.py:128 | `ATM_HEAT, "an ATM camera got a frame of you"` | `axis="personal"` |
| hat (face disguise) | garage.py:158 | `-HAT_HEAT_DROP, "ball cap pulled low…"` | `axis="personal"` |
| roadside mechanic on card | drama.py:115 | `2, "paid a roadside mechanic on the card"` | `axis="personal"` |
| Instagram tag (arrival) | heat.py:245 | `spike, "tagged by {handle}"` | `axis="car"` (they photographed the car/plate) |
| clerk posts the car | heat.py:296 | `"the gas-station clerk posted you…"` | `axis="car"` |
| flashy lights | gadgets.py:65 | `3.0, "flashed the lights…"` | `axis="car"` |
| push hard drive | rules.py:202 | `HEAT_PUSH_DRIVE, "drove flashy…"` | `axis="car"` |
| rough sleep, flashy car | rules.py:384 | `rough_h, "slept rough in a flashy car"` | `axis="car"` |
| cruiser ran plate | drama.py:52 | `6, "a cruiser ran the plate"` | `axis="car"` (BOLO on plate) |
| witness filmed car | drama.py:99 | `5, "a witness recognized the car…"` | `axis="car"` |
| valet ran plate | garage.py:181 | `VALET_HEAT_TRAP, "the valet ran the plate…"` | `axis="car"` |
| tow driver long look | rules.py:467 | `8.0, "a tow driver got a long look…"` | `axis="car"` |
| patrol tail (raw `+= 3`) | rules.py:115 | `state.heat += 3` | **convert** to `_heat.add(state, 3, "a county cruiser clocked the car", "spike", axis="car")` |
| baseline (stolen show car) | game.py:220 | `base, "she's a stolen SEMA show car — the baseline"` | `axis="car"` (the BOLO is on the car) |
| untag damage control | heat.py:311 | `-back, "damage control…"` | `axis="car"` (it was a car tag) |
| lie low | heat.py:335 | `-cool, "laid low, out of sight"` | **untyped** (cools both) |
| state line | rules.py:197 | `…"crossed a state line"` | **untyped** (cools both) |
| clean miles decay | rules.py:200 | `…"miles and time, lying low"` | **untyped** (cools both) |
| overheat pull-over | drama.py:38 | `-1.5, "pulled over…"` | **untyped** |
| self-drive bonus (if present) | rules.py | n/a | untyped |

**rules.py:109 (`state.heat -= 12`) and rules.py:116 raw mutations:** line 115 (`+= 3`) becomes an `add(..., axis="car")` call as above. Line 109's `-= 12` (slipped a roadblock) → leave as a raw combined nudge but follow with a re-sync: after `_clamp_heat(state)` add `state.flags["car_heat"] = min(state.flags.get("car_heat", state.heat), state.heat)` so the dominant axis can't exceed combined. Simpler: replace `state.heat -= 12; _clamp_heat(state)` with `_heat.add(state, -12, "slipped the roadblock onto a frontage road", "lower")` (untyped → cools both). Do the same audit for any other bare `state.heat +=/-=` (grep: `state.heat [-+]=`, `s.heat [-+]=`). Convert each to `_heat.add(... axis=...)` or untyped lower. **This is the single most important correctness step** — any bare write leaves the axes stale.

`new_game` (game.py:218-220) zeroes `s.heat` then re-adds the baseline. After the rewrite, also explicitly seed `s.flags["car_heat"]=0.0; s.flags["personal_heat"]=0.0` before the baseline `add(..., axis="car")`, so a fresh game starts clean.

`go_legit` (garage.py:362) and `_clamp_heat` (rules.py:81-86) set `s.heat = 0.0` on `no_heat`; also clear both axis flags there.

### 1c. Dashboard — show both axes

In `heat.py dashboard()` (after the bar, ~line 156), insert a two-axis readout and re-key the levers:

```python
ch, ph = car_heat(s), personal_heat(s)
lines.append(f"  CAR HEAT      {ch:>3.0f}  (the white Z — BOLO, the spade, people clocking her)")
lines.append(f"  DRIVER HEAT   {ph:>3.0f}  (YOU — your face on a camera, your card, the ATM)")
hotter = "CAR" if ch >= ph else "DRIVER"
lines.append(f"  → {hotter} heat is what's setting the meter. "
             + ("Change her looks — plates, hood, a respray." if hotter == "CAR"
                else "Hide your face — ball cap, pay CASH, no ATM, lie low."))
```

Update the WHAT-IF line (heat.py:180) to: `pay cash +0 · swipe/ATM ~+4 DRIVER · push hard / get tagged +CAR · swap plates −CAR · ball cap −DRIVER · clean miles − both`.

Update the live levers (heat.py:188-200): the `live_card_mark` lever already keys off card/ATM reasons → label it "pay CASH — that's DRIVER heat." Add: `if exposure(s) >= 2 and ch >= 45: levers.append("swap the plate / hood — drop the car's heat")`.

### 1d. Call sites to touch (summary)
- **heat.py**: `add()` rewrite, `car_heat`/`personal_heat`/`_combined` accessors, `dashboard()` two-axis block + levers, `social_arrival` (`axis="car"`), `clerk_resolve` (`axis="car"`), `untag` (`axis="car"`).
- **rules.py**: `_card_mark` (×2 paths it feeds), tow swipe + tow look, push-drive, rough-sleep, patrol-tail conversion, roadblock-slip conversion, `_clamp_heat` axis clear, plus state-line/decay stay untyped.
- **garage.py**: `atm`, `buy_hat`, `valet_return`, `go_legit` axis clear.
- **drama.py**: `_e_plate`, `_e_recognized`, `_e_gremlin` card path.
- **game.py**: `new_game` baseline seed + axis init.
- **`snapshot()`** (game.py ~391): add `"car_heat": round(heat.car_heat(s)), "driver_heat": round(heat.personal_heat(s))` next to existing `heat` key so the frontend/HUD can show both. The test at line 749 (`snapshot(s)["heat"] == 0`) is unaffected.

### 1e. Tests to add (extend, don't replace)
- `test_card_swipe_is_driver_heat_not_car`: fuel on card → `personal_heat` up, `car_heat` flat, `s.heat == personal_heat`.
- `test_tag_is_car_heat`: force a tag → `car_heat` up, `personal_heat` flat.
- `test_combined_is_max_and_backcompat`: set car=60 personal=20 → `s.heat == 60`.
- `test_hat_only_cools_driver`: hat drops `personal_heat`; if car was dominant, `s.heat` unchanged (documents the mechanic).

---

## FEATURE 2 — PPF-AWARE CAR DISGUISE (plate → hood → respray ladder)

This drops **CAR heat only** (Feature 1's `axis="car"`). It's distinct from `camo` (the tarp/mud, a temporary one-notch *visibility* drop that a hard push blows) — these are durable physical changes stored in `s.flags["car_disguise_level"]`.

### 2a. `config.py` — new constants
```python
PLATE_SWAP_COST   = 60.0;   PLATE_SWAP_HEAT  = -10.0   # cheap starter; cold plate
HOOD_SWAP_COST    = 900.0;  HOOD_SWAP_HEAT   = -22.0   # hides the spade, changes silhouette
RESPRAY_COST      = 3800.0; RESPRAY_HEAT     = -40.0   # nuclear, ugly over PPF, Ace resists
RESPRAY_BOND_HIT  = -14.0                              # a bad job hurts her vanity (sticky)
DISGUISE_RANK = {"none": 0, "plate": 1, "hood": 2, "respray": 3}
```

### 2b. `engine/gadgets.py` — add the ladder

A car-disguise level is monotonic (plate < hood < respray); applying a higher tier supersedes. Each tier sets `car_disguise_level` and is one-shot per tier. Respray requires a **confirm** (two-step, like the over-range drive) because Ace resists.

```python
from config import (PLATE_SWAP_COST, PLATE_SWAP_HEAT, HOOD_SWAP_COST, HOOD_SWAP_HEAT,
                    RESPRAY_COST, RESPRAY_HEAT, RESPRAY_BOND_HIT, DISGUISE_RANK)

def disguise_level(s) -> str:
    return s.flags.get("car_disguise_level", "none")

def _shop_here(s) -> bool:
    return bool(s.place.has("gas") or s.place.kind == "city")

def swap_plate(s) -> list:
    from engine import heat as _heat, economy
    if s.flags.get("no_heat"):
        return ["PLATES: she's yours — the tag's legit now. Nothing to hide."]
    if DISGUISE_RANK[disguise_level(s)] >= 1:
        return ["PLATES: already running a swapped tag. One set of cold plates is enough."]
    if not _shop_here(s):
        return ["PLATES: nowhere to grab a plate out here — a town or a busy stop."]
    r = economy.pay(s, PLATE_SWAP_COST, prefer="cash")
    if not r["ok"]:
        return [f"PLATES: a cold plate runs ${PLATE_SWAP_COST:.0f} and you can't cover it."]
    s.flags["car_disguise_level"] = "plate"
    _heat.add(s, PLATE_SWAP_HEAT, "swapped to a cold plate — the BOLO's looking for CARTALK", "lower", axis="car")
    return [f"PLATES: you pull CARTALK and screw on a junkyard tag. The BOLO's hunting a plate that's "
            f"in your trunk now. Car heat {PLATE_SWAP_HEAT:.0f} → {s.heat:.0f}. "
            "(She doesn't love losing the vanity plate, but she gets it.)"]

def swap_hood(s) -> list:
    from engine import heat as _heat, economy, bond as _bond
    if s.flags.get("no_heat"):
        return ["HOOD: no need — she's clean now. Keep the carbon, keep the spade."]
    if DISGUISE_RANK[disguise_level(s)] >= 2:
        return ["HOOD: already wearing the plain hood. The spade's in the trunk."]
    if not _shop_here(s):
        return ["HOOD: you need a shop or a town to swap a hood."]
    r = economy.pay(s, HOOD_SWAP_COST, prefer="cash")
    if not r["ok"]:
        return [f"HOOD: a swap hood + labor is ${HOOD_SWAP_COST:.0f}. You're short."]
    s.flags["car_disguise_level"] = "hood"
    s.flags["spade_hidden"] = True
    _heat.add(s, HOOD_SWAP_HEAT, "swapped the spade hood for a plain one — different silhouette", "lower", axis="car")
    _bond.adjust(s, -2.0, "boxed up my ace of spades", "warm")   # small, she understands
    return [f"HOOD: off comes the carbon ace-of-spades hood, on goes a flat steel one — the whole "
            f"face of the car reads different now, and the one thing every witness remembers is in a "
            f"box. Car heat {HOOD_SWAP_HEAT:.0f} → {s.heat:.0f}. "
            "'…I look like a parts car. Effective. I hate it a little. Good call though.'"]

def respray(s) -> list:
    from engine import heat as _heat, economy, bond as _bond, rules as _rules
    if s.flags.get("no_heat"):
        return ["RESPRAY: she's legal — repaint her for fun someday, not to hide."]
    if DISGUISE_RANK[disguise_level(s)] >= 3:
        return ["RESPRAY: she's already been shot over. Once is more than she can forgive twice."]
    if not _shop_here(s):
        return ["RESPRAY: you need a real shop — a town, and a shady one."]
    # two-step: she RESISTS, you must say it again
    if s.flags.get("confirm_respray") != (s.place.poi_id or s.place.name):
        s.flags["confirm_respray"] = s.place.poi_id or s.place.name
        return ["RESPRAY: 'Absolutely not. Ace — I'm wrapped in paint-protection film. You shoot color "
                "over PPF in a back-alley booth and it fish-eyes, it orange-peels, it PEELS. I will look "
                "like a bad insurance job for the rest of my life. …If you mean it, say it again. But you'll "
                "have done it to my FACE.' (Repeat the command to go through with it.)"]
    s.flags.pop("confirm_respray", None)
    if economy.max_affordable(s, "cash") < RESPRAY_COST:
        return [f"RESPRAY: a no-questions booth wants ${RESPRAY_COST:.0f} cash. You can't cover it."]
    economy.pay(s, RESPRAY_COST, prefer="cash")
    _rules.advance_clock(s, 8.0)                 # overnight in the booth
    s.flags["car_disguise_level"] = "respray"
    s.flags["resprayed_ugly"] = True             # narration + show-score hook
    _heat.add(s, RESPRAY_HEAT, "resprayed in a back-alley booth — she's a different-colored car now", "lower", axis="car")
    _bond.adjust(s, RESPRAY_BOND_HIT, "painted over me in an alley — it bubbled on the PPF and I'll never look right", "deep")
    return [f"RESPRAY: eight hours in a plastic booth that smells like a crime. She comes out a dull, "
            f"wrong gunmetal — and where the film was, the paint already micro-blisters in the light. "
            f"Unrecognizable, which is the point. Car heat {RESPRAY_HEAT:.0f} → {s.heat:.0f}. "
            "'…There. Nobody knows me now. Including me. Don't tell me I'm pretty, ace. I'll know you're lying.'"]
```

**Interactions:**
- `respray` should set the floor on car heat low (the spade is buried + new color), but **personal heat is untouched** — reinforces the two-axis lesson.
- Hook `resprayed_ugly` into `garage.show_score()` (garage.py:72): `-25` if `s.flags.get("resprayed_ugly")` — a bad respray makes her **unwinnable on a lawn** until she's bought (a paint correction could be a future buy-back beat). This is the "a bad job makes her look bad" consequence.
- A hard push (rules.py:203) blows only `camo` (the tarp), **never** the durable disguise level — correct as written; no change needed.

### 2c. `engine/commands.py` — parser rules (insert in the gadgets block, near line 268, before generic `camo`)
```python
if (low in ("swap plate", "swap the plate", "swap plates", "change the plate", "change plates",
            "new plate", "new plates", "cold plate", "stolen plate", "fake plate", "swap the tag")
        or ("plate" in low and any(w in low for w in ("swap", "change", "new", "cold", "fake", "different")))):
    return ("swapplate", {})
if (low in ("swap hood", "swap the hood", "change the hood", "new hood", "plain hood",
            "hide the spade", "lose the spade", "different hood", "swap the bonnet")
        or ("hood" in low and any(w in low for w in ("swap", "change", "new", "plain", "different")))
        or ("spade" in low and any(w in low for w in ("hide", "lose", "cover", "ditch")))):
    return ("swaphood", {})
if (low in ("respray", "respray her", "repaint", "repaint her", "paint her", "paint the car",
            "new paint", "new color", "change her color", "spray her", "get her painted",
            "different color", "paint job")
        or "respray" in low or ("paint" in low and any(w in low for w in ("her","car","job","new","change")))):
    return ("respray", {})
```
Keep these **above** the existing `camo`/`sell` rules so "hide the spade" doesn't fall into `camo` and "paint" doesn't reach `say`. Note `sell` parses "swap hood"? No — `sell` only triggers on `low.startswith("sell"|"strip")`, so no collision; but confirm "swap the hood" doesn't hit `_is_sleep` (it doesn't).

### 2d. `engine/game.py` — dispatch (in the gadgets elif chain, ~line 1129)
```python
elif verb == "swapplate":
    events = gadgets.swap_plate(s); player_text = ""
elif verb == "swaphood":
    events = gadgets.swap_hood(s); player_text = ""
elif verb == "respray":
    events = gadgets.respray(s); player_text = ""
```
Add `"swapplate","swaphood","respray"` to the mid-encounter no-go check is **not** needed (they're not in `_action_verbs`), but they should be blocked during a stop/standoff. The existing `else`/`say` fallthrough for unknown verbs during an encounter already routes long text as speech; a terse "respray" mid-stop would dispatch the verb. To be safe, treat these like other non-talk verbs: they fall through the encounter guard normally (the guard only special-cases `_action_verbs`), so a "respray" during a stop would currently run. **Add a guard:** in the mid-encounter block, extend the "do anything except talk" set to include disguise verbs, or simply let them no-op via a `_shop_here`/place check (a respray booth isn't open at a traffic stop — the existing `_shop_here` returns False on a `shoulder`/roadblock spot, so it self-blocks). The clean fix: rely on `_shop_here`; no encounter-guard change required.

### 2e. Help + tests
- `_help_text()` (game.py:~1290): add `  swap plate / hood / respray   drop the CAR's heat (the BOLO) — plate cheap, respray ugly`.
- Tests: `test_plate_swap_drops_car_heat_only`, `test_respray_needs_confirm_and_hurts_bond_and_show`, `test_disguise_ladder_monotonic`.

---

## FEATURE 3 — REAL LODGING + THE CLOWN MOTEL (Tonopah)

### 3a. `engine/state.py` — extend `Place` (optional, default-safe)
Add one field to the `Place` dataclass (after `scene`, line 29):
```python
lodging_names: dict = field(default_factory=dict)  # {"motel": ["Mizpah Hotel","Clown Motel"], "airbnb": "..."}
```
`Place.from_dict` already filters to known fields, so old saved `pos` dicts without this key load fine (default `{}`). `to_dict` (asdict) round-trips it.

### 3b. `engine/economy.py` — surface real names
Change `lodging_options` (lines 15–24) to read names from the place and return a third tuple element, **defaulting to None** so callers that do `dict(lodging_options(place))` still work (a 3-tuple unpacks `(label, price, name)`; but `dict()` over 3-tuples fails). To keep `rules.py:390`'s `dict(economy.lodging_options(place))` intact, **do not change the tuple arity.** Instead add a separate helper:

```python
def lodging_label(place, kind: str) -> str:
    """The real-place name for a lodging type here, if pois.json provides one; else the generic."""
    names = getattr(place, "lodging_names", None) or {}
    v = names.get(kind)
    if isinstance(v, list):
        return v[0] if v else kind
    return v or kind
```
Keep `lodging_options` returning `(label, price)` 2-tuples (unchanged — zero break to rules.py).

### 3c. `engine/rules.py` — use the real name in the sleep event
In `sleep()` (line 417), replace the generic `place_word`:
```python
real = economy.lodging_label(place, kind)
place_word = (f"a private place off a quiet street in" if airbnb
              else (f"{real}" if real != kind else f"a {kind} at"))
```
And the event line (line 418-421) becomes e.g. `SLEEP: the Clown Motel in Tonopah, $92 (cash)…`. For airbnb keep the alias phrasing. This is pure flavor; no heat/test impact (test at line 431/598 sets `s.heat` and checks decay, not the string).

### 3d. `content/pois.json` — real lodging names for the Vegas→Reno corridor + others
Add `lodging_names` and `beat` to existing entries. Examples (research-grounded):

- **tonopah**: `"lodging_names": {"motel": ["The Clown Motel", "Mizpah Hotel", "Tonopah Station"], "airbnb": "a miner's cottage north of Main"}`
- **hawthorne** (add the POI if absent, on US-95 between Tonopah and Fallon, lat 38.5246 lon -118.6256, services gas/lodging/food): `"lodging_names": {"motel": ["El Capitan Lodge & Casino", "Walker Lake Motel"]}`
- **beatty**: `"lodging_names": {"motel": ["Stagecoach Hotel & Casino", "Death Valley Inn"]}`
- **fallon**: `"lodging_names": {"motel": ["The Holiday Inn Express by the base", "Bonanza Inn"]}`
- **carson_city**: `"lodging_names": {"motel": ["Hotel Nevada-style downtown motor inn", "Carson Station"]}`
- **reno**: `"lodging_names": {"motel": ["a weekly motel on 4th", "the Sands"]}`

### 3e. The CLOWN MOTEL as its own creepy beat
Two options; **recommended: a Tonopah `beat`** (one-time arrival voice) plus the Clown Motel surfacing as the named motel there — no new POI needed, no routing change, and it ties to "where you end up heading toward Reno." Add to **tonopah** in pois.json:

```json
"beat": "(the town's one stoplight blinks yellow over Main and she idles low) Tonopah. Halfway to nowhere, the darkest sky in the lower 48 — and that, ace, lit up on the right: the Clown Motel. Hundreds of them. Porcelain faces stacked floor to ceiling in the lobby, every room hung with two or three more, all of them looking at the door. The old miners' cemetery is RIGHT behind it — they share a fence. Eighteen-aught-eight, the Belmont fire took a hundred men into that ground, and somebody decided the right neighbor for the dead was a wall of clowns. We could sleep here. The BOLO won't think to look in the one town nobody can stand to stop in. …I'll keep the lights on. You won't."
```

And a **lodging-specific creepy line** when the player actually checks into the Clown Motel: in `rules.py sleep()`, after a successful motel stay, add:
```python
if (place.poi_id == "tonopah" and not airbnb
        and "clown" in economy.lodging_label(place, kind).lower()):
    events.append("SLEEP: room 6 of the Clown Motel. Three painted faces over the bed, one over the "
                  "sink, the AC ticking like a dripping faucet. Through the wall, the cemetery's "
                  "dead-quiet. She watches the parking lot all night so you don't have to. "
                  "'I don't sleep, ace. Lucky us. Go ahead.'")
```
(Trigger only when `lodging_label` resolves to a Clown-Motel name; if you want the player to *choose* it, accept a `kind`-style hint — out of scope, the default `motel` here is the Clown Motel since it's first in the list.)

### 3f. Reno routing through Tonopah
The router (`world.route`) is point-to-point (OSRM or haversine), so **no router change is needed** — OSRM naturally takes US-95 through Tonopah for a Vegas→Reno leg, and offline mode uses straight-line distance. The "you end up at the Clown Motel heading toward Reno" is delivered narratively: when the player drives a long northbound leg toward `reno` and stops to sleep, Tonopah is the realistic mid-point town. Optionally add a **soft nudge** in `_after_arrival` or the drive's range warning: if `dest.poi_id == "reno"` and the leg exceeds tank range from south of Tonopah, the over-range warning (rules.py:170-178) already forces a fuel/lodging stop — and Tonopah is the nearest serviced POI (`world.nearest_with_service`). No code required; document it.

### 3g. Tests
- `test_lodging_label_returns_real_name`: tonopah → "The Clown Motel".
- `test_clown_motel_creepy_beat_fires_once`: arrive tonopah → beat present, second arrival absent (uses existing `beats_seen` machinery).
- `test_lodging_options_arity_unchanged`: `dict(economy.lodging_options(...))` still works (guards the back-compat).

---

## FEATURE 4 — Z EVENTS at FALLON & CARSON CITY (+ reusable pattern)

Two layers, both already supported: (A) one-time **gazetteer beats** (`pois.json "beat"`, fires once on arrival via `_story_on_arrival` → `world.beat_for`), and (B) **rewardable arrival events** via `drama.EVENTS` with a POI-keyed predicate. Use **(B)** for Fallon/Carson because Ben wants heat/cash/riz/bond effects; (A) is the reusable lightweight pattern for "others."

### 4a. Reusable pattern — a POI-arrival event factory in `drama.py`
Add a helper so new town events are one-liners:

```python
def _poi_event(poi_id, flag, cue, stub, line, *, riz=0.0, cash=0.0,
               heat=0.0, heat_axis="car", bond=0.0, bond_reason=""):
    def fire(s, rng):
        s.flags[flag] = True
        if riz:  s.riz = round(s.riz + riz, 1)
        if cash: s.cash = round(s.cash + cash, 2)
        if heat: _heat.add(s, heat, line["heat_reason"], "spike" if heat > 0 else "lower", axis=heat_axis)
        if bond:
            from engine import bond as _bond
            _bond.adjust(s, bond, bond_reason or "a moment on the road", "warm")
        return {"tag": "DRAMA", "id": flag, "lines": [line["text"]], "cue": cue, "stub": stub}
    return fire
```

Register in `EVENTS` (list at line 174) with a high weight and a `not seen` predicate so it reliably fires once on arrival at that town:

```python
{"id": "fallon_topgun",
 "pred": lambda s: s.place.poi_id == "fallon" and not s.flags.get("saw_topgun"),
 "weight": lambda s: 9.0,
 "fire": _poi_event(
     "fallon", "saw_topgun",
     cue="an F/A-18 from NAS Fallon — the real TOPGUN — tore low across the alfalfa as the driver "
         "fueled; the pilot, clocking the SEMA Z, rocked his wings in salute. She is floored that "
         "military iron knows her, proud and a little undone",
     stub=["Hornet. Low and loud — that's TOPGUN's house, ace. …Did you SEE that? He wagged his "
           "wings at ME. A '72 Datsun. The fastest men in America know my face. I could cry. I won't.",
           "F/A-18, afterburner over the cornfields. He saw the spade and he SALUTED. We're famous in "
           "the one place that goes faster than us."],
     line={"text": "DRAMA: a TOPGUN Hornet thundered the salt flats and wagged its wings at the Z. "
                   "Riz +6 → {riz}.", "heat_reason": "a Navy pilot recognized the legend"},
     riz=6.0, bond=2.0, bond_reason="a fighter pilot saluted me and you were there")},
```

Note: the `{riz}` in the line text needs formatting at fire time — simplest is to build the line string inside `fire` after mutating, e.g. `line_text = f"DRAMA: …Riz +{riz:.0f} → {s.riz:.0f}."`. Adjust `_poi_event` to compose the line post-mutation rather than pre-format.

### 4b. Fallon (grounded: NAS Fallon / TOPGUN, "Nevada's salad bowl")
- **Effect**: Riz +6, bond +2, no heat (a salute isn't a witness). A second visit: no event (flag set).
- Alternative branch (low chance via `rng`): a base-town gawker films the car → small CAR heat +4 ("a base-town kid filmed the Z by the alfalfa scales"). Keeps it from being pure upside.

### 4c. Carson City (grounded: state capital, US-50 "Loneliest Road," Sierra escape)
```python
{"id": "carson_escape",
 "pred": lambda s: s.place.poi_id == "carson_city" and not s.flags.get("saw_carson"),
 "weight": lambda s: 9.0,
 "fire": _poi_event(
     "carson_city", "saw_carson",
     cue="rolling into the quiet capital under the Sierra, she eyes the high passes west — the start "
         "of US-50, the Loneliest Road — and talks, low and conspiratorial, about how easy it would be "
         "to vanish up the 8% grades where there are no cameras and no traffic; a getaway-car's daydream",
     stub=["Carson City. Capital of the whole state and it sleeps by nine. See that road climbing west? "
           "US-50 — they call it the Loneliest Road in America like it's an insult. To us it's a door. "
           "Eight percent grades, hairpins over seven thousand feet, not one camera. We could disappear "
           "up there for a week, ace.",
           "The high country starts right here. No traffic, no eyes, just switchbacks and pine. I was "
           "BUILT for that road. Say the word and we're a rumor by morning."],
     line={"text": "DRAMA: Carson City, and the Loneliest Road climbs west — she reads it as an escape "
                   "hatch. Quiet miles cooled her. Heat → {heat}.",
           "heat_reason": "the quiet capital, off the cameras"},
     heat=-4.0, heat_axis="car", riz=2.0)},
```
- **Effect**: cools CAR heat −4 (off the cameras, in the sleepy capital) + Riz +2. Optional light **choice**: if `s.heat >= 60`, append a stub line offering to detour up US-50 ("lie low up the passes") — the player can follow with `lielow`/a westbound drive; no new verb needed.

### 4d. Beats for the lighter "others" (reusable, no rewards)
Add `"beat"` strings to **goldfield** (eerie half-ruin), **hawthorne** (the 2,427 ammo igloos + Walker Lake), **beatty** (Death Valley gateway, Rhyolite ghost town) directly in pois.json — they fire once via the existing gazetteer layer, zero engine code. Example hawthorne beat: "Hawthorne. Those green mounds running to the horizon? Bunkers. Twenty-four hundred of them — the biggest ammo dump on earth, sleeping under the sand. And that blue slash is Walker Lake. Prettiest place in Nevada to not be noticed."

### 4e. Tests
- `test_fallon_topgun_event_awards_riz_once`: arrive fallon → riz up, `saw_topgun` set; re-arrive → no second award.
- `test_carson_city_cools_car_heat`: set car heat 60, arrive carson_city → `car_heat` down ~4, `s.heat` follows.
- `test_town_beats_fire_once` (extend existing `test_story_beats_fire_on_tow_arrivals`) for goldfield/hawthorne/beatty.

---

## SUGGESTED BUILD ORDER (smallest shippable first)

1. **Feature 3 — lodging names + Clown Motel** (lowest risk, mostly data). `Place.lodging_names` field, `economy.lodging_label`, the `rules.sleep` flavor line, pois.json `lodging_names`/`beat` for the US-95 corridor + Tonopah/Clown Motel. No heat-system changes; ship and run tests.
2. **Feature 4 — Z events** (data + a small `drama.py` helper). `_poi_event` factory, Fallon/Carson entries, the lighter town beats. Depends on nothing in 1; can interleave. (If you build it before Feature 1, use untyped/`axis=None` heat in the events, then switch to `axis="car"` after Feature 1 lands.)
3. **Feature 1 — two-axis heat** (the structural change; do it as one focused PR). Rewrite `add()`, add accessors, **convert every bare `state.heat ±=`**, route the deltas, dashboard + snapshot. Run the full 163 + new axis tests. This is the keystone — land it before Feature 2 so disguise can target `axis="car"`.
4. **Feature 2 — PPF disguise ladder** (depends on Feature 1's `axis="car"`). Config constants, `gadgets` ladder, parser rules, dispatch, show-score penalty, help, tests.

Ship 1 and 2 first to get visible new content live with no risk to the heat meter, then do the heat split (3 in this order) carefully, then layer disguise on top.

---

## RISKS

- **Stale axes from bare heat writes (highest risk).** Any `state.heat += N` / `s.heat = ...` that bypasses `add()` leaves `car_heat`/`personal_heat` out of sync with the combined meter, so the dashboard lies and disguise/hat appear to do nothing. **Mitigation:** grep `\.heat\s*[-+]?=` across `engine/` and convert every hit to `add(... axis=...)` or untyped lower; the only legitimate raw writes are the `no_heat → 0.0` resets (which must also zero both axis flags). Add a debug assertion in tests: after any `handle()`, `abs(s.heat - max(car_heat,personal_heat)) < 0.2`.
- **Save back-compat.** Old saves have no `car_heat`/`personal_heat` flags and no `lodging_names` in `pos`. Both default safely (flags `.get(...,0.0)`; dataclass default `{}`). But an in-progress old save will show `car=personal=0` while `s.heat` is high until the next `add()` re-syncs both. **Mitigation:** add a one-time backfill in `GameState.from_dict` / game load: if `heat > 0` and both axis flags absent, seed `car_heat = personal_heat = heat` (the conservative "both could be hot" assumption), so the dashboard is coherent immediately.
- **`max` vs `sum` band feel.** With `max`, stacking car+driver heat doesn't push past the dominant axis, so a player hot on both axes isn't *more* wanted than one hot on a single axis. This is a deliberate tuning choice that preserves the 163 tests; if Ben wants compounding danger later, switch to a capped blend (`max + 0.3*min`) — but that breaks current magnitude assertions and needs a test rebaseline. Flagged, not done.
- **Respray as a trap.** The bad-respray show-score penalty (`-25`, unwinnable lawn) is intentionally punishing. Verify it doesn't soft-lock a player who resprayed *then* bought the car and wants to show her — consider a future "paint correction at AiSha" buy-back beat (out of scope; note it).
- **Parser collisions.** "hide the spade"/"paint her"/"new plates" must be ordered **above** `camo`, `sell`, and the `say` fallthrough in `commands.py`. Add parser unit tests for each new phrase to lock ordering.
- **Clown Motel auto-selection.** Because it's first in tonopah's `lodging_names["motel"]` list, a plain `sleep`/`motel` at Tonopah lands there by default — desired, but confirm players who type `sleep camp`/`airbnb` still get those (they do; `lodging_label` only renames the chosen `kind`).

Files touched: `engine/heat.py`, `engine/gadgets.py`, `engine/garage.py`, `engine/economy.py`, `engine/rules.py`, `engine/drama.py`, `engine/game.py`, `engine/commands.py`, `engine/state.py`, `config.py`, `content/pois.json`, `tests/test_engine.py`.