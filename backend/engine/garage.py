"""The garage: the trust-the-player economy and what ownership unlocks.

- CLAIM cash you're carrying (within reason) — you narrate your wallet, the engine holds you to it.
- ATM withdrawals (anything under $10k, total) at a town with services.
- The GLOVEBOX: claim you're broke and explore the car, there's $500 in there (once).
- SELL the build off her — the carbon hood, the triple Mikunis, the deep-dish wheels — for cash,
  swapped for cheap stock parts. It strips her value and her show-worthiness; some parts even change
  how she drives.
- Once you BUY her from the owner (the good ending), heat is gone for good and you can do it all the
  legal way: RACE her on a real track, or SHOW her on the lawn.

All prose is a working DRAFT — Ben fills the details.
"""
from __future__ import annotations
import re

from config import (
    CASH_CLAIM_CAP, ATM_ACCOUNT_LIMIT, ATM_HEAT, GLOVEBOX_CASH,
    CAR_VALUE_BASE, PART_VALUE_MULT, RIZ_RACE_WIN, RIZ_SHOW_WIN,
)
from engine.state import GameState
from engine import economy

# ---------------------------------------------------------------- the build sheet
# id: name, the cheap stock part it's swapped for, resale $, and effects.
# show = beauty-show points it's worth · mpg = change to economy when removed ·
# torque = change to the headline torque number when removed.
PARTS = {
    "hood":      {"name": "carbon-fiber hood", "stock": "a stock 280Z vented steel hood",
                  "value": 1800, "show": 8, "mpg": -0.4},
    "wheels":    {"name": "deep-dish forged wheels", "stock": "stock steelies and hubcaps",
                  "value": 2400, "show": 10, "mpg": 0.0},
    "carbs":     {"name": "triple Mikuni carbs", "stock": "a single stock Hitachi",
                  "value": 1600, "show": 9, "mpg": 1.6, "torque": -70},
    "exhaust":   {"name": "stainless header and exhaust", "stock": "a dented stock muffler",
                  "value": 900, "show": 5, "mpg": -0.3},
    "coilovers": {"name": "coilover suspension", "stock": "saggy stock springs",
                  "value": 1300, "show": 7},
    "seats":     {"name": "checkered bucket seats", "stock": "cracked stock vinyl",
                  "value": 700, "show": 6},
}
_ALIASES = {
    "hood": "hood", "carbon hood": "hood", "carbon fiber hood": "hood", "carbon-fiber hood": "hood",
    "wheels": "wheels", "rims": "wheels", "deep dish": "wheels", "deep-dish": "wheels",
    "carbs": "carbs", "mikunis": "carbs", "carburetors": "carbs", "triple mikunis": "carbs",
    "exhaust": "exhaust", "header": "exhaust", "headers": "exhaust",
    "coilovers": "coilovers", "suspension": "coilovers", "coils": "coilovers",
    "seats": "seats", "buckets": "seats", "bucket seats": "seats",
}
SHOW_BASE = 50            # the rest of her (paint, the spade, the lines) is worth this on a lawn
SHOW_WIN_THRESHOLD = 90   # full build clears it; strip much and you can't


def part_id(text: str):
    low = (text or "").lower()
    for k in sorted(_ALIASES, key=len, reverse=True):
        if k in low:
            return _ALIASES[k]
    return None


def sold(s: GameState) -> list:
    return s.flags.setdefault("parts_sold", [])


def car_value(s: GameState) -> float:
    lost = sum(PARTS[p]["value"] * PART_VALUE_MULT for p in sold(s))
    return round(CAR_VALUE_BASE + sum(PARTS[p]["value"] * PART_VALUE_MULT for p in PARTS) - lost)


def show_score(s: GameState) -> int:
    return SHOW_BASE + sum(PARTS[p]["show"] for p in PARTS if p not in sold(s))


def is_stripped(s: GameState) -> bool:
    return len(sold(s)) >= 3


def parts_text(s: GameState) -> str:
    lines = ["ON THE CAR (sell at a town with a shop — 'sell the carbon hood'):"]
    done = sold(s)
    for pid, p in PARTS.items():
        if pid in done:
            lines.append(f"  — {p['name']}  SOLD → {p['stock']}")
        else:
            lines.append(f"  ${p['value']:>4.0f}  {p['name']}")
    lines.append(f"  value ~${car_value(s):,.0f} · show score {show_score(s)}"
                 + ("  (stripped — won't win a lawn)" if not _show_ok(s) else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------- claims / ATM / glovebox
def claim_cash(s: GameState, amount: float) -> list:
    """You declare the cash you brought — ONCE, up to the cap, total across the whole trip.
    Re-claiming after you've spent it doesn't refill (it's what you walked out with, not a faucet)."""
    amt = round(max(0.0, amount), 2)
    if amt <= 0:                                   # claiming you're broke
        if s.cash >= 100.0:                        # ...but you're demonstrably not
            return [f"CASH: you're not broke, ace — there's ${s.cash:.0f} in your hand already."]
        s.cash = 0.0
        return ["CASH: you say you're carrying nothing. (Try 'explore' — check the car.)"]
    claimed = s.flags.get("claimed_total", 0.0)
    grant = round(min(amt, CASH_CLAIM_CAP) - claimed, 2)   # only the part above what you've already claimed
    if grant <= 0:
        return [f"CASH: you already told me what you walked out with — ${claimed:.0f}. "
                "That's the wallet; the ATM's for the rest."]
    s.cash = round(s.cash + grant, 2)
    s.flags["claimed_total"] = round(claimed + grant, 2)
    note = "" if min(amt, CASH_CLAIM_CAP) >= amt else " (she raises an eyebrow — that's the ceiling)"
    return [f"CASH: ${grant:.0f} more from your pocket{note}. ${s.cash:.0f} on you."]


def atm(s: GameState, amount: float | None) -> list:
    if not s.place.has("gas") and s.place.kind not in ("city",):
        return ["ATM: no cash machine out here. Try a town."]
    pulled = s.flags.get("atm_pulled", 0.0)
    room = ATM_ACCOUNT_LIMIT - pulled
    if room <= 0.5:
        return ["ATM: your account's tapped — you've pulled all it'll give (under $10k)."]
    want = room if amount is None else min(amount, room)
    want = round(max(0.0, want), 2)
    if want <= 0:
        return ["ATM: nothing to withdraw."]
    s.cash = round(s.cash + want, 2)
    s.flags["atm_pulled"] = round(pulled + want, 2)
    s.heat = min(100.0, s.heat + ATM_HEAT)
    return [f"ATM: withdrew ${want:.0f} (the camera gets a frame of you — heat +{ATM_HEAT:.0f} → "
            f"{s.heat:.0f}). Cash ${s.cash:.0f}. ${ATM_ACCOUNT_LIMIT - s.flags['atm_pulled']:.0f} "
            "left in the account."]


def explore(s: GameState) -> list:
    if s.flags.get("glovebox_found"):
        return ["EXPLORE: you've already been through the glovebox. Maps, a parking stub, lint."]
    if s.cash >= 100.0:                            # the stash only matters when you're truly broke
        s.flags["glovebox_found"] = True
        return ["EXPLORE: glovebox, console, under the seats — maps, a parking stub, a cassette. "
                "Nothing you need; you've already got cash in hand."]
    s.flags["glovebox_found"] = True
    s.cash = round(s.cash + GLOVEBOX_CASH, 2)
    return [f"EXPLORE: under the registration and a dead flashlight — a roll of bills. "
            f"${GLOVEBOX_CASH:.0f}. Somebody's emergency stash, yours now. Cash ${s.cash:.0f}."]


def sell_part(s: GameState, pid: str) -> list:
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["SELL: no one out here to buy parts. A town with a shop."]
    if pid in sold(s):
        return [f"SELL: the {PARTS[pid]['name']} is already gone — that's the stock piece on her now."]
    p = PARTS[pid]
    sold(s).append(pid)
    s.cash = round(s.cash + p["value"], 2)
    out = [f"SELL: the {p['name']} comes off, ${p['value']:.0f} in your hand, and they bolt on "
           f"{p['stock']}. Cash ${s.cash:.0f}."]
    if p.get("mpg"):
        s.mpg = round(max(8.0, s.mpg + p["mpg"]), 1)
        out.append(f"SELL: she does about {s.mpg:.0f} mpg now.")
    if p.get("torque"):
        out.append(f"SELL: down on power — the build sheet's a lie now.")
    return out


# ---------------------------------------------------------------- ownership: race & show
def _rng(s: GameState, salt: int):
    import random
    return random.Random(s.seed * 6151 + s.turn * 277 + salt)


def race(s: GameState) -> list:
    if s.place.kind != "track":
        return ["RACE: this isn't a track. Find a real circuit — Laguna Seca, Willow Springs, Sonoma."]
    if not s.flags.get("bought"):
        return ["RACE: they tech-inspect and check the title at the gate. You can't run a car that's "
                "still reported missing. (Come to terms with the owner first.)"]
    if s.fuel_l < 4.0:
        return ["RACE: you can't run a race day on fumes — fuel up first."]
    from engine import rules
    rules.advance_clock(s, 1.0)                      # a session burns an hour and a few liters
    s.fuel_l = round(max(0.0, s.fuel_l - 3.0), 2)
    won_here = s.flags.setdefault("raced_tracks", [])
    repeat = s.place.poi_id in won_here
    perf = 70 + (12 if "carbs" not in sold(s) else 0) + (8 if "coilovers" not in sold(s) else 0)
    perf -= len(sold(s)) * 4
    score = perf + _rng(s, 1).randint(-15, 18)
    if repeat:                                       # you've run this circuit — still a thrill, no new purse
        return [f"RACE: another run at {s.place.name} — quicker, cleaner, but the purse and the "
                "trophy were a one-time thing. You burn an hour for the love of it. Worth it."]
    if s.place.poi_id:
        won_here.append(s.place.poi_id)
    if score >= 92:
        prize = 600 + _rng(s, 2).randint(0, 400)
        s.cash = round(s.cash + prize, 2)
        s.riz = round(s.riz + RIZ_RACE_WIN, 1)
        return [f"RACE: you win it outright at {s.place.name} — flag, photo, ${prize} envelope. "
                f"Riz +{RIZ_RACE_WIN:.0f} → {s.riz:.0f}. She has never sounded happier."]
    if score >= 78:
        s.riz = round(s.riz + RIZ_RACE_WIN / 2, 1)
        return [f"RACE: a podium at {s.place.name} — third, but clean. Riz +{RIZ_RACE_WIN/2:.0f} → "
                f"{s.riz:.0f}. 'Did you feel that corner? I felt that corner.'"]
    return [f"RACE: mid-pack at {s.place.name}. The stripped bits show on the clock — but you ran "
            "her legal, in the daylight, with your real name on the entry. That's the whole prize."]


def _show_ok(s: GameState) -> bool:
    return show_score(s) >= SHOW_WIN_THRESHOLD


SHOW_POIS = ("petersen", "getty", "heard", "nhmu", "monterey", "sema_north_hall")


def can_show(s: GameState) -> bool:
    return s.place.kind == "museum" or s.place.poi_id in SHOW_POIS


def show(s: GameState) -> list:
    if not can_show(s):
        return ["SHOW: no show field here — a museum lawn, Monterey, the hall she debuted in."]
    if not s.flags.get("bought"):
        return ["SHOW: every entry form wants a title and a name. Not while she's stolen. "
                "(Buy her from the owner and you can show her anywhere.)"]
    if not _show_ok(s):
        return [f"SHOW: they walk the car and shake their heads — too much of the build is gone "
                f"(show score {show_score(s)}/{SHOW_WIN_THRESHOLD}). Stock steel where the carbon was. "
                "You can race her all day, but you can't win a lawn stripped."]
    shown = s.flags.setdefault("shown_venues", [])
    if s.place.poi_id in shown:
        return [f"SHOW: she's already taken best in class at {s.place.name} — the plaque's on the "
                "shelf. They wave you onto the field to enjoy it, not to judge it again."]
    if s.place.poi_id:
        shown.append(s.place.poi_id)
    prize = 800 + _rng(s, 3).randint(0, 700)
    s.cash = round(s.cash + prize, 2)
    s.riz = round(s.riz + RIZ_SHOW_WIN, 1)
    return [f"SHOW: best in class at {s.place.name} — the spade on the hood, the lines, the story. "
            f"${prize} and a little brass plaque. Riz +{RIZ_SHOW_WIN:.0f} → {s.riz:.0f}. "
            "She idles like she's purring."]


# ---------------------------------------------------------------- the good ending
def go_legit(s: GameState) -> None:
    """She's yours, on paper. Heat's gone for good; the law and the owner stop hunting — and you
    don't need the gun anymore. A clean slate is the whole point of the good ending."""
    s.flags["bought"] = True
    s.flags["no_heat"] = True
    s.flags["report_withdrawn"] = True
    s.flags.pop("owner_deadline_day", None)
    s.flags.pop("desperado", None)       # the title clears the car; the heat floor lifts
    s.flags.pop("gun", None)             # you put it down — there's nothing left to point it at
    s.flags.pop("wanted_armed", None)
    s.heat = 0.0
