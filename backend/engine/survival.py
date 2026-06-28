"""Survival — the body in the driver's seat. You're not just managing a car; you're a person who
has to sleep, eat, use a bathroom (#1 and, yes, #2), and who gets dumber after a few drinks.

Design goals (Ben's tone: characterful, funny, never a grind):
- Meters accrue ONLY on awake time (hooked into rules.advance_clock), so sitting at a menu costs
  nothing — time pressure comes from driving and lying low, same as fuel and the season.
- TELEGRAPH before it bites. Each need warns, then gets urgent, then — if you really ignore it —
  has an embarrassing little consequence. Nothing here ends the game; it costs dignity and ALERTNESS.
- ALERTNESS is the throughline. A full bladder, an empty stomach, a hard night, and especially
  alcohol all dull you — and a dull driver talks his way out of a traffic stop worse (Edge of
  Tomorrow only works if you're sharp). cameras/encounters read alertness via talk_penalty().
- Alcohol decays like a real BAC (~one drink an hour metabolized). Ace is the designated conscience.

Sleep itself stays in rules.py (fatigue + the hours-awake gate); this module owns hunger, the two
bathroom meters, and intoxication, and exposes the single tick() + the alertness math. Prose DRAFT.
"""
from __future__ import annotations

from engine.state import GameState

# per-awake-hour accrual
HUNGER_RATE = 3.0        # full → uncomfortable across a long day; you eat once or twice
BLADDER_RATE = 7.0       # #1 — every several hours on the road
BOWELS_RATE = 3.0        # #2 — about once a day
BAC_DECAY = 0.012        # blood-alcohol metabolized per hour

# thresholds (0 = fine, 100 = crisis)
WARN = {"hunger": 60.0, "bladder": 65.0, "bowels": 70.0}
URGENT = {"hunger": 85.0, "bladder": 88.0, "bowels": 92.0}

DRINK_BAC = 0.025        # one drink ≈ this much BAC on a person who's been up all day
BAC_TIPSY = 0.03
BAC_DRUNK = 0.08         # legally cooked; a stop gets very hard

FOOD_PRICE_DRINK = 11.0  # a roadside beer / well pour

CAFFEINE_PRICE = 4.0     # a gas-station large coffee / energy drink
CAFFEINE_BASE = 5.0      # hours of "awake" the FIRST shot since sleep cancels
CAFFEINE_DECAY = 1.3     # buzz wears off this many cancel-hours per real hour
CAFFEINE_DEBT_FACTOR = 0.55  # the buzz is borrowed — you pay it back as worse rest tonight


def _get(s: GameState, key: str) -> float:
    return float(s.flags.get(f"need_{key}", 0.0))


def _set(s: GameState, key: str, val: float) -> None:
    s.flags[f"need_{key}"] = round(max(0.0, min(100.0, val)), 1)


def bac(s: GameState) -> float:
    return float(s.flags.get("bac", 0.0))


# --------------------------------------------------------------- the tick (awake time)
def tick(s: GameState, hours: float) -> list:
    """Advance the body by `hours` of AWAKE time. Called from rules.advance_clock. Returns any
    threshold-crossing telegraph lines, plus resolves an ignored-too-long accident."""
    if hours <= 0:
        return []
    events: list = []
    for key, rate in (("hunger", HUNGER_RATE), ("bladder", BLADDER_RATE), ("bowels", BOWELS_RATE)):
        before = _get(s, key)
        after = before + rate * hours
        _set(s, key, after)
        # an ignored bathroom need hits the wall — an accident: auto-relief, a little shame, move on
        if key in ("bladder", "bowels") and after >= 100.0 and before < 100.0:
            events += _accident(s, key)
        # a long leg can cross BOTH thresholds in one tick — emit the higher one (urgent), never skip
        elif before < URGENT[key] <= after:
            events.append(_warn_line(key, "urgent"))
        elif before < WARN[key] <= after:
            events.append(_warn_line(key, "warn"))
    # metabolize alcohol
    if bac(s) > 0:
        s.flags["bac"] = round(max(0.0, bac(s) - BAC_DECAY * hours), 4)
        if s.flags["bac"] <= 0:
            s.flags.pop("bac", None)
    # the caffeine buzz wears off
    if s.flags.get("caffeine", 0) > 0:
        s.flags["caffeine"] = round(max(0.0, s.flags["caffeine"] - CAFFEINE_DECAY * hours), 2)
        if s.flags["caffeine"] <= 0:
            s.flags.pop("caffeine", None)
    return events


def accrue(s: GameState, hours: float) -> None:
    """Advance the body silently and stash any telegraph/accident lines for the next drain().
    Called from rules.advance_clock — the one chokepoint for awake time passing."""
    ev = tick(s, hours)
    if ev:
        s.flags.setdefault("_body_pending", []).extend(ev)


def drain(s: GameState) -> list:
    """Pop the body lines accrued since the last drain. Drive/tow/lie-low append these to events."""
    return s.flags.pop("_body_pending", [])


def _warn_line(key: str, level: str) -> str:
    if key == "hunger":
        return ("HUNGER: stomach's growling — you should eat soon." if level == "warn"
                else "HUNGER: you're running on fumes, ace, and so is she. Find food.")
    if key == "bladder":
        return ("BODY: you need to find a bathroom in the next hour or two." if level == "warn"
                else "BODY: you REALLY need a restroom. Next stop, no negotiating.")
    return ("BODY: that gas-station burrito is asking to leave. A real bathroom would be wise."
            if level == "warn" else "BODY: this is now an emergency of the second kind. Find a stall.")


def _accident(s: GameState, key: str) -> list:
    _set(s, key, 0.0)
    from engine import bond as _bond
    _bond.adjust(s, -1.0, "had an accident in her seats", "mark")
    if key == "bladder":
        return ["BODY: …you couldn't hold it. The seat'll need a detail and she is being very, "
                "very quiet about it. (Relieved, at a cost. 'We do not speak of this.')"]
    return ["BODY: you did not make it. There is no dignified way to log this event. Window down, "
            "eyes forward, and she pretends, for your sake, that her sensors aren't that good."]


def sleep_reset(s: GameState) -> float:
    """A night's sleep: you used the bathroom before bed and went in the morning; you wake hungry.
    Returns the caffeine sleep-debt to add back onto fatigue (the buzz was borrowed)."""
    _set(s, "bladder", 0.0)
    _set(s, "bowels", _get(s, "bowels") * 0.35)
    _set(s, "hunger", min(100.0, _get(s, "hunger") + 12.0))   # you wake up hungry
    s.flags.pop("bac", None)                                   # sleep it off
    debt = float(s.flags.pop("caf_debt", 0.0))
    s.flags.pop("caffeine", None); s.flags.pop("caf_shots", None)
    return debt


def caffeine_offset(s: GameState) -> float:
    """Hours of effective 'awake' the current buzz cancels (for the drive gate and the rizz dulling)."""
    return float(s.flags.get("caffeine", 0.0))


def caffeinate(s: GameState) -> list:
    """A coffee or an energy drink. Buys back awake-hours against the drive gate and rizz — but with
    hard diminishing returns (each shot since you slept does less) and a sleep debt: tonight's rest
    pays it back. Caffeine is a loan, not income."""
    from engine import economy
    place = s.place
    if not (place.has("food") or place.has("gas") or place.kind == "city"):
        return ["CAFFEINE: no coffee out here, ace — a station, a diner, or a town."]
    shots = int(s.flags.get("caf_shots", 0))
    boost = round(CAFFEINE_BASE * (0.55 ** shots), 2)
    if boost < 0.6:
        return ["CAFFEINE: you're already so wired your hands are buzzing — another one does nothing "
                "but make it worse. You need actual sleep, not more coffee."]
    paid = economy.pay(s, CAFFEINE_PRICE)
    if not paid["ok"]:
        return [f"CAFFEINE: ${CAFFEINE_PRICE:.0f} for a coffee and you can't cover it."]
    s.flags["caffeine"] = round(caffeine_offset(s) + boost, 2)
    s.flags["caf_shots"] = shots + 1
    s.flags["caf_debt"] = round(float(s.flags.get("caf_debt", 0.0)) + boost * CAFFEINE_DEBT_FACTOR, 2)
    tail = (" — and you can feel it doing less than the last one." if shots >= 1 else ".")
    return [f"CAFFEINE: a {'gas-station coffee' if shots == 0 else 'second-wind energy drink'}, "
            f"${CAFFEINE_PRICE:.0f} ({paid['method']}). The road sharpens up for a few hours{tail} "
            "(You'll pay for it when you finally sleep.)"]


# --------------------------------------------------------------- the verbs
def eat(s: GameState) -> list:
    from engine import economy, rules
    place = s.place
    if not (place.has("food") or place.has("gas") or place.has("lodging") or place.kind == "city"):
        return ["EAT: nothing to eat out here — no town, no pump, no diner. Get somewhere with food."]
    from config import FOOD_PRICE
    paid = economy.pay(s, FOOD_PRICE)
    if not paid["ok"]:
        return [f"EAT: a meal's about ${FOOD_PRICE:.0f} and you can't cover it. Drive hungry, or raise some cash."]
    rules.advance_clock(s, 0.5)
    _set(s, "hunger", 0.0)
    from engine import places
    real = places.suggest(s, "food")             # a real local restaurant, if we have one for this town
    if real:
        where = real["name"]
    else:
        where = ("a diner" if place.has("food") else
                 "a gas-station sandwich" if place.has("gas") else "a quick bite in town")
    return [f"EAT: {where}, ${FOOD_PRICE:.0f} ({paid['method']}). Fed. The road looks better on a full stomach."]


def restroom(s: GameState, number: int = 1) -> list:
    from engine import rules
    place = s.place
    nice = place.has("gas") or place.has("food") or place.has("lodging") or place.kind == "city"
    key = "bladder" if number == 1 else "bowels"
    had = _get(s, key)
    if had < 12:
        return ["BODY: you don't need to go right now." if number == 1
                else "BODY: nothing pressing on that front."]
    rules.advance_clock(s, 0.15 if nice else 0.1)
    _set(s, key, 0.0)
    if nice:
        return [f"BODY: a real restroom. Much better. {'(#1)' if number == 1 else '(#2)'}"]
    return ["BODY: you pull onto the shoulder and find a bush. Not glamorous, but handled. "
            "She keeps her headlights pointed politely the other way."]


def drink(s: GameState, n: int = 1) -> list:
    """A drink (or a few). Raises BAC, dulls you, and Ace does not love it. Driving on it is a
    much worse idea than she'll let you forget."""
    place = s.place
    if not (place.has("food") or place.has("lodging") or place.kind == "city"):
        return ["DRINK: no bar out here, ace. Towns and lodges and diners only."]
    from engine import economy, bond as _bond
    n = max(1, min(4, int(n)))
    cost = FOOD_PRICE_DRINK * n
    paid = economy.pay(s, cost)
    if not paid["ok"]:
        return [f"DRINK: ${cost:.0f} for {n} and the money's not there."]
    s.flags["bac"] = round(bac(s) + DRINK_BAC * n, 4)
    _bond.adjust(s, -0.5 * n, "drinking when I'm the one who has to drive us out of trouble", "mark")
    b = bac(s)
    tail = (" You're cooked. Do NOT let a cop talk to you." if b >= BAC_DRUNK
            else " You feel it." if b >= BAC_TIPSY else "")
    return [f"DRINK: {n} down (${cost:.0f}, {paid['method']}). BAC ~{b:.2f}.{tail}",
            "ACE: (dry) I'm the designated driver and I don't even have hands. Pace yourself."]


# --------------------------------------------------------------- alertness → talk-out
def alertness(s: GameState) -> float:
    """0.0 (wrecked) … 1.0 (sharp). Drunk, busting, starving, or exhausted all pull it down."""
    a = 1.0
    a -= min(0.6, bac(s) / 0.10 * 0.5)                    # 0.10 BAC ≈ −0.5
    if _get(s, "bladder") >= URGENT["bladder"]:
        a -= 0.15
    if _get(s, "bowels") >= URGENT["bowels"]:
        a -= 0.15
    if _get(s, "hunger") >= URGENT["hunger"]:
        a -= 0.1
    from engine import rules
    if rules.hours_awake(s) >= 18:
        a -= 0.15
    return round(max(0.0, min(1.0, a)), 2)


def talk_penalty(s: GameState) -> int:
    """How many points a dulled driver loses on a traffic-stop pitch. 0 when sharp."""
    a = alertness(s)
    if a >= 0.85:
        return 0
    if a >= 0.65:
        return 1
    if a >= 0.45:
        return 2
    return 3


def dashboard_line(s: GameState) -> str:
    """A compact body readout for the 'look' ledger."""
    def bar(v):
        f = int(round(v / 20))
        return "█" * f + "·" * (5 - f)
    parts = [f"HUNGER [{bar(_get(s,'hunger'))}]", f"#1 [{bar(_get(s,'bladder'))}]",
             f"#2 [{bar(_get(s,'bowels'))}]"]
    if bac(s) > 0:
        parts.append(f"BAC {bac(s):.2f}")
    return "BODY  " + "  ".join(parts)
