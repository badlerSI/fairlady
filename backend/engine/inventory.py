"""Inventory — what fits in the back of a 240Z, and why that matters.

Grounded in real numbers (RESEARCH_NOTES.md): the S30 hatch bay, seats up, is a pinched wedge —
~7.5 cubic feet of genuinely USABLE volume after you account for the strut towers and the sloped
glass (factory luggage spec is 7.47 cu ft). So you can NOT bring everything. A run out to the Black
Rock with extra fuel and water means leaving the cooler or the spare behind — that trade-off IS the
mechanic. Jerry cans carry reserve fuel that extends your range past one tank; water keeps a desert
excursion from being a bad idea; a tent turns a rough night into a real camp.

A couple of things can't be bought — they just turn up. Ask Area 51 about that.

Capacity is a hard cap; buying is volume-checked. Prose is a working DRAFT for Ben.
"""
from __future__ import annotations

from engine.state import GameState

CAPACITY_CUFT = 7.5            # usable hatch volume, seats up (real, tape-measured + factory spec)
JERRY_LITERS = 18.9           # a 5-gallon NATO can

# id → spec. cuft = packed volume; price None = not for sale (it just appears).
ITEMS = {
    "jerrycan":     {"name": "5-gal steel jerry can", "cuft": 0.9, "price": 45.0, "kind": "fuel",
                     "desc": "carries reserve fuel — pour it into the tank to extend your range"},
    "water":        {"name": "water jug (1 gal)", "cuft": 0.16, "price": 3.0, "kind": "water",
                     "desc": "you do not go deep into the Black Rock without it"},
    "cooler":       {"name": "soft cooler", "cuft": 1.6, "price": 40.0, "kind": "gear",
                     "desc": "keeps food and a few drinks cold"},
    "tent":         {"name": "2-person tent", "cuft": 1.0, "price": 70.0, "kind": "gear",
                     "desc": "turns a rough night into a real camp — rest like a bed, draw fewer eyes"},
    "sleeping_bag": {"name": "sleeping bag", "cuft": 0.8, "price": 45.0, "kind": "gear",
                     "desc": "warmth for the high desert at night"},
    "tool_roll":    {"name": "tool roll", "cuft": 0.4, "price": 60.0, "kind": "gear",
                     "desc": "field repairs — knock the limp out of her without a shop"},
    "first_aid":    {"name": "first-aid kit", "cuft": 0.2, "price": 25.0, "kind": "gear",
                     "desc": "just in case"},
    "spare":        {"name": "full-size spare (useless — no jack on board)", "cuft": 3.0, "price": 120.0,
                     "kind": "gear", "desc": "a show-car joke: the spare well is full of her compute and "
                     "there's no jack, so a flat is always a tow no matter what you carry"},
    "snacks":       {"name": "bag of road snacks", "cuft": 0.3, "price": 12.0, "kind": "food",
                     "desc": "takes the edge off hunger on a long leg"},
    "tire_chains":  {"name": "set of tire chains", "cuft": 0.5, "price": 70.0, "kind": "gear",
                     "desc": "the ONLY way past a chain-control checkpoint when it's snowing on a grade"},
    "stinger":      {"name": "an olive-drab tube stenciled FIM-92 (do NOT ask)", "cuft": 1.2,
                     "price": None, "kind": "ordnance",
                     "desc": "it was not here this morning. it is here now. one shot of pure bad idea"},
}

ALIASES = {
    "jerry can": "jerrycan", "jerrycan": "jerrycan", "jerry cans": "jerrycan", "gas can": "jerrycan",
    "gas cans": "jerrycan", "fuel can": "jerrycan", "fuel cans": "jerrycan", "can of gas": "jerrycan",
    "water": "water", "water jug": "water", "water jugs": "water", "jug of water": "water",
    "cooler": "cooler", "ice chest": "cooler", "tent": "tent",
    "sleeping bag": "sleeping_bag", "bag": "sleeping_bag", "tools": "tool_roll", "tool roll": "tool_roll",
    "toolkit": "tool_roll", "tool kit": "tool_roll", "first aid": "first_aid", "first-aid": "first_aid",
    "first aid kit": "first_aid", "medkit": "first_aid", "spare": "spare", "spare tire": "spare",
    "snacks": "snacks", "snack": "snacks", "food": "snacks", "stinger": "stinger", "missile": "stinger",
    "launcher": "stinger", "rocket": "stinger",
    "chains": "tire_chains", "tire chains": "tire_chains", "tire_chains": "tire_chains",
    "snow chains": "tire_chains", "set of chains": "tire_chains",
}


def _inv(s: GameState) -> dict:
    return s.flags.setdefault("inventory", {})


def count(s: GameState, item_id: str) -> int:
    return int(_inv(s).get(item_id, 0))


def has(s: GameState, item_id: str) -> bool:
    return count(s, item_id) > 0


def volume_used(s: GameState) -> float:
    return round(sum(ITEMS[i]["cuft"] * n for i, n in _inv(s).items() if i in ITEMS), 2)


def volume_free(s: GameState) -> float:
    return round(CAPACITY_CUFT - volume_used(s), 2)


def jerry_fuel(s: GameState) -> float:
    return float(s.flags.get("jerry_fuel_l", 0.0))


def _match(text: str) -> str | None:
    t = (text or "").lower()
    for phrase, iid in sorted(ALIASES.items(), key=lambda kv: -len(kv[0])):
        if phrase in t:
            return iid
    return None


def _qty(text: str) -> int:
    import re
    low = (text or "").lower()
    # ignore numbers that describe the ITEM, not the count ('5 gallon', '2 liter', '12 oz', '5-gal')
    low = re.sub(r"\b\d{1,2}\s*-?\s*(gal(lon)?s?|l(it(er|re)s?)?|oz|ounce|quart|qt|inch|in|man|person)\b",
                 " ", low)
    m = re.search(r"\b(\d{1,2})\b", low)
    n = int(m.group(1)) if m else 1
    return max(1, min(20, n))


# --------------------------------------------------------------- the verbs
def add(s: GameState, item_id: str, qty: int = 1) -> None:
    inv = _inv(s)
    inv[item_id] = inv.get(item_id, 0) + qty


def grant_stinger(s: GameState) -> list:
    """It just appears in the hatch after Area 51. Once."""
    if has(s, "stinger") or s.flags.get("stinger_granted"):
        return []
    s.flags["stinger_granted"] = True
    if volume_free(s) < ITEMS["stinger"]["cuft"]:           # make room — it does not ask permission
        for junk in ("snacks", "cooler", "spare"):
            if has(s, junk):
                _inv(s)[junk] -= 1
                if _inv(s)[junk] <= 0:
                    del _inv(s)[junk]
                break
    add(s, "stinger", 1)
    return ["HATCH: …there's a weight in the back that wasn't there before. Olive-drab tube, "
            "stenciling, a grip-stock. You did not put it there. (acquired: an FIM-92 — 'do NOT ask.')",
            "ACE: 'I'm going to pretend I don't see that. …You're not going to do anything stupid "
            "with it. Right? Right, ace?'"]


def buy(s: GameState, text: str) -> list:
    item_id = _match(text)
    place = s.place
    if not item_id:
        return ["BUY: not sure what you mean. The hatch takes jerry cans, water, a cooler, a tent, "
                "a sleeping bag, tools, a first-aid kit, a spare, snacks. ('inventory' to see the back.)"]
    spec = ITEMS[item_id]
    if spec["price"] is None:
        return ["BUY: that's not something you buy, ace. That's something that finds you."]
    if not (place.has("gas") or place.has("food") or place.kind == "city"):
        return [f"BUY: nowhere to buy a {spec['name']} out here — a station, a store, a town."]
    qty = _qty(text)
    need_vol = spec["cuft"] * qty
    if need_vol > volume_free(s) + 1e-9:
        fit = int(volume_free(s) // spec["cuft"])
        if fit <= 0:
            return [f"BUY: the hatch is full — {volume_used(s):.1f}/{CAPACITY_CUFT:.1f} cu ft. "
                    f"Drop something first. It's a 240Z, not a U-Haul."]
        qty = fit
        need_vol = spec["cuft"] * qty
    from engine import economy
    cost = spec["price"] * qty
    paid = economy.pay(s, cost)
    if not paid["ok"]:
        return [f"BUY: {qty}× {spec['name']} runs ${cost:.0f} and you're short."]
    add(s, item_id, qty)
    line = (f"BUY: {qty}× {spec['name']} (${cost:.0f}, {paid['method']}). "
            f"Hatch {volume_used(s):.1f}/{CAPACITY_CUFT:.1f} cu ft.")
    if item_id == "jerrycan":
        line += " (empty — 'fill the jerry cans' at a pump to carry reserve fuel.)"
    return [line]


def drop(s: GameState, text: str) -> list:
    item_id = _match(text)
    if not item_id or not has(s, item_id):
        return ["DROP: you're not carrying that."]
    inv = _inv(s)
    inv[item_id] -= 1
    if inv[item_id] <= 0:
        del inv[item_id]
    if item_id == "jerrycan" and jerry_fuel(s) > 0:         # dropping a can spills its reserve
        spill = min(jerry_fuel(s), JERRY_LITERS)
        s.flags["jerry_fuel_l"] = round(jerry_fuel(s) - spill, 2)
    return [f"DROP: left the {ITEMS[item_id]['name']} behind. Hatch {volume_used(s):.1f}/"
            f"{CAPACITY_CUFT:.1f} cu ft."]


def fill_jerrycans(s: GameState) -> list:
    """At a pump: top off every empty jerry can with gas you pay for. Reserve fuel you can pour into
    the tank later — the only way to out-run the gaps between stations (the Black Rock, the 50)."""
    if not s.place.has("gas"):
        return ["JERRY: no pump here to fill them at."]
    cans = count(s, "jerrycan")
    if cans <= 0:
        return ["JERRY: you don't have any cans. 'buy a jerry can' first."]
    capacity = cans * JERRY_LITERS
    room = capacity - jerry_fuel(s)
    if room < 0.5:
        return ["JERRY: the cans are already full."]
    from engine import economy
    gal = room / 3.785411784
    price = economy.gas_price(s.place)
    cost = gal * price
    paid = economy.pay(s, cost)
    if not paid["ok"]:
        return [f"JERRY: filling the cans is {gal:.1f} gal, about ${cost:.0f}, and you can't cover it."]
    s.flags["jerry_fuel_l"] = round(jerry_fuel(s) + room, 2)
    return [f"JERRY: filled {cans} can(s) — {room:.0f} L of reserve ({gal:.1f} gal, ${cost:.0f}, "
            f"{paid['method']}). That's ~{room / 3.785411784 * s.mpg:.0f} extra miles in the hatch."]


def pour_jerrycans(s: GameState) -> list:
    """Pour the reserve into the tank — on the shoulder, in the dark, wherever the needle died."""
    res = jerry_fuel(s)
    if res <= 0.1:
        return ["JERRY: the cans are dry. Nothing to pour."]
    room = s.tank_l - s.fuel_l
    if room < 0.5:
        return ["JERRY: the tank's already full — no room to pour."]
    moved = min(res, room)
    s.fuel_l = round(s.fuel_l + moved, 2)
    s.flags["jerry_fuel_l"] = round(res - moved, 2)
    return [f"JERRY: you pour {moved:.0f} L from the cans into her tank on the shoulder. "
            f"Tank {s.fuel_l:.1f}/{s.tank_l:.0f} L (~{s.range_mi:.0f} mi). Reserve left: "
            f"{jerry_fuel(s):.0f} L."]


def dashboard(s: GameState) -> str:
    inv = _inv(s)
    lines = [f"THE HATCH  ·  {volume_used(s):.1f} / {CAPACITY_CUFT:.1f} cu ft used"]
    if not inv:
        lines.append("  empty but for a jack and a sun-bleached map. ('buy a jerry can', 'buy water'…)")
    for iid, n in inv.items():
        if iid not in ITEMS:
            continue
        nm = ITEMS[iid]["name"]
        extra = ""
        if iid == "jerrycan":
            extra = f"  ·  {jerry_fuel(s):.0f} L reserve"
        lines.append(f"  {n}× {nm}{extra}")
    if jerry_fuel(s) > 0:
        lines.append(f"  → reserve fuel: ~{jerry_fuel(s) / 3.785411784 * s.mpg:.0f} mi if you pour it in")
    return "\n".join(lines)


def desert_warning(s: GameState, dest) -> str | None:
    """Heading deep into the empty quarter without water/reserve fuel — she says something."""
    pid = getattr(dest, "poi_id", "") or ""
    name = (getattr(dest, "name", "") or "").lower()
    deep_desert = pid in ("gerlach", "black_rock", "racetrack_playa", "berlin_nv") or "black rock" in name
    if not deep_desert:
        return None
    warn = []
    if not has(s, "water"):
        warn.append("no water")
    if jerry_fuel(s) <= 0 and s.tank_pct < 75:
        warn.append("no fuel reserve and a half-empty tank")
    if not warn:
        return None
    return ("DESERT: 'Ace — out here there's no pump and no faucet for a long way. We've got "
            + " and ".join(warn) + ". Stock the hatch first, or this gets stupid fast.'")
