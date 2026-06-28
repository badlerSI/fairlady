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
    HAT_PRICE, HAT_HEAT_DROP, VALET_HEAT_TRAP,
    COVER_PRICE, COVER_HEAT_DROP, PLATE_SWAP_PRICE, PLATE_SWAP_HEAT_DROP,
    HOOD_SWAP_PRICE, HOOD_SWAP_HEAT_DROP, RESPRAY_PRICE, RESPRAY_HEAT_DROP, RESPRAY_BOND_HIT,
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
    raw = SHOW_BASE + sum(PARTS[p]["show"] for p in PARTS if p not in sold(s))
    return max(0, raw - int(body_damage(s) // 4))     # scrapes and dents cost you on the lawn


# ---------------------------------------------------------------- Ace's body: cosmetic → serious
# A 0–100 wound meter, separate from the mechanical LIMP gremlin. 1–39 is cosmetic (scrapes, a caved
# fender, a cracked lens — costs show points, stings the bond); 40+ is SERIOUS (something structural —
# she limps, and a roadside tool-roll fix won't fully cut it; she wants a real body shop). The faked
# flaming-death ending deliberately does NOT care about this — that's a chosen sacrifice, not a wreck.
DAMAGE_SERIOUS = 40

def body_damage(s: GameState) -> float:
    return float(s.flags.get("body_damage", 0.0))


def damage_state(s: GameState) -> str:
    d = body_damage(s)
    if d <= 0:
        return "clean"
    return "serious" if d >= DAMAGE_SERIOUS else "cosmetic"


def damage_car(s: GameState, amount: float, reason: str, cosmetic: bool = True) -> None:
    """Hurt her. `amount` adds to the wound meter; crossing DAMAGE_SERIOUS (or any non-cosmetic hit)
    also throws the LIMP gremlin so she actually drives hurt. Never raises — callers narrate."""
    if s.flags.get("no_heat") and s.flags.get("bought") and False:
        return  # (ownership doesn't make her invincible; placeholder kept intentionally inert)
    before = body_damage(s)
    s.flags["body_damage"] = round(min(100.0, before + max(0.0, amount)), 1)
    if (not cosmetic) or s.flags["body_damage"] >= DAMAGE_SERIOUS:
        s.flags["limp"] = True


def repair_body(s: GameState, full: bool = True) -> list:
    """A real body shop (a town/city) hammers the dents and sorts the structure. Costs by severity.
    The tool-roll field fix (garage.field_repair) clears LIMP but only knocks ~12 off the cosmetic
    wound — you still want a shop to make her pretty again."""
    d = body_damage(s)
    if d <= 0:
        return ["BODY: not a mark on her — nothing for a shop to do."]
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["BODY: no body shop out here. Limp her to a town."]
    cost = round(120 + d * 14, 2)                     # cosmetic ~$300–700, serious $700+
    r = economy.pay(s, cost, prefer="cash")
    if not r["ok"]:
        return [f"BODY: the shop quotes about ${cost:.0f} to set her right, and you can't cover it. "
                "(Sell a part, hit the ATM, or live with the scars a while.)"]
    s.flags["body_damage"] = 0.0
    s.flags.pop("limp", None)
    from engine import bond as _bond
    _bond.adjust(s, 3.0, "paid to make her whole again at a real shop", "warm")
    return [f"BODY: a day in a real shop — ${cost:.0f}, paid {r['method']}. They pull the dents, blend "
            "the panel, set the structure true. She rolls out straight and shining. 'Good as new. "
            "Better. Thank you, ace.'"]


def is_stripped(s: GameState) -> bool:
    return len(sold(s)) >= 3


def _in_bob(s: GameState) -> bool:
    return bool(s.flags.get("bob_mode") and not s.flags.get("bob_owned"))


def parts_text(s: GameState) -> str:
    if _in_bob(s):
        return "PARTS: that's Bob — stock as a fridge, dog-dish hubcaps and all. Nothing to strip, and "\
               "he isn't yours to sell. Ace's build is parked back in the garage."
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
    from engine import heat as _heat
    _heat.add(s, ATM_HEAT, "an ATM camera got a frame of you", "mark", axis="personal")
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


def buy_hat(s: GameState) -> list:
    """A $12 mini-mart ball cap. Brim down, you read as anybody — heat drops. One-shot."""
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["HAT: nowhere to buy one out here — a station mini-mart or a town."]
    if s.flags.get("hat_on"):
        return ["HAT: you're already wearing it, brim down. Can't disguise twice."]
    r = economy.pay(s, HAT_PRICE, prefer="cash")        # cash-first: a hat on a card is comedy
    if not r["ok"]:
        return [f"HAT: ${HAT_PRICE:.0f} for the cap and you can't cover it. (Try the ATM.)"]
    from engine import heat as _heat
    s.flags["hat_on"] = True
    _heat.add(s, -HAT_HEAT_DROP, "ball cap pulled low — harder to ID off a camera frame", "mark", axis="personal")
    return [f"HAT: a ${HAT_PRICE:.0f} Chevron ball cap, brim down. You read as anybody now. "
            f"Driver heat -{HAT_HEAT_DROP:.0f} → {s.heat:.0f}."]


def valet_drop(s: GameState) -> list:
    """Hand the keys to a valet. Easy and quiet NOW — but it's a trap (see valet_return)."""
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["VALET: no valet stand out here."]
    if s.flags.get("valet_parked"):
        return ["VALET: she's already with the valet."]
    s.flags["valet_parked"] = True
    return ["VALET: a kid in a vest takes the keys and parks the white Z out back. Easy. Too easy. "
            "(She goes very quiet about it.)"]


def valet_return(s: GameState) -> list:
    """The trap springs: you come back for her and the valet ran the plate — cops are staged.
    Call this when the player goes to LEAVE / fetch the car after valeting. Returns event lines
    (empty if she was never valeted)."""
    if not s.flags.pop("valet_parked", None):
        return []
    from engine import heat as _heat
    _heat.add(s, VALET_HEAT_TRAP, "the valet ran the plate — there are units waiting on the car", "spike", axis="car")
    return ["VALET: you come back for her and there are two cruisers idling by the air pump, cops "
            "pretending to buy coffee. The valet ran the plate. "
            f"Heat +{VALET_HEAT_TRAP:.0f} → {s.heat:.0f}. They're between you and the road."]


# ---------------------------------------------------------------- disguising the CAR (CAR axis)
def cover_car(s: GameState) -> list:
    """Pull the opaque fitted cover out of her hatch and throw it over her. A covered car can't be
    read or photographed — the easy-mode way to lie low in a hot city for a night (the Vegas move).
    Free (it's hers); driving pulls it off. Routes to CAR heat."""
    from engine import heat as _heat
    if s.flags.get("no_heat"):
        return ["COVER: nothing to hide — she's yours, free and clear."]
    if s.flags.get("covered"):
        return ["COVER: she's already under the cover, just a gray lump in the lot. Nobody's looking."]
    s.flags["covered"] = True
    s.flags["cover_credit"] = COVER_HEAT_DROP        # reverts if you yank it off; kept if you sleep/drive on
    _heat.add(s, -COVER_HEAT_DROP, "tucked under an opaque cover — a covered car reads as nothing",
              "lower", axis="car")
    vegas = (s.place.poi_id in ("las_vegas", "vegas_strip", "fremont", "sphere")
             or "vegas" in (s.place.name or "").lower())
    line = (f"COVER: you pull the fitted cover out of her hatch and drape her — under the garage "
            f"lights she's just another gray lump. CAR heat -{COVER_HEAT_DROP:.0f} → {s.heat:.0f}.")
    out = [line]
    if vegas:
        out.append("COVER: …and now the Strip is yours for a night. Walk it. Pay cash, keep your hat "
                   "on, and she'll be right here, invisible, when you stumble back. ('uncover' to roll.)")
    else:
        out.append("COVER: ('uncover' when you're ready to roll — you can't drive her like this.)")
    return out


def uncover_car(s: GameState) -> list:
    if not s.flags.pop("covered", None):
        return ["COVER: she's not covered."]
    credit = s.flags.pop("cover_credit", 0.0)        # yanked it right off → no quiet hours earned
    if credit:
        from engine import heat as _heat
        _heat.add(s, credit, "pulled the cover — she's exposed again", "mark", axis="car")
    return ["COVER: you whip the cover off and fold it back into the hatch. There she is — and so, "
            "again, is every camera's interest." if credit
            else "COVER: you whip the cover off and fold it back into the hatch. There she is."]


def swap_plate(s: GameState) -> list:
    """Pull a plate off a long-term-lot junker and run it. Every ALPR reads it clean, and the
    CARTALK-to-Cedric mismatch stops being a tell at the next stop. The single best CAR-heat move."""
    from engine import heat as _heat
    if s.flags.get("no_heat"):
        return ["PLATE: she's papered in your name now — the plate on her is legitimately hers."]
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["PLATE: you want a parking structure or a town lot for this — somewhere with rows "
                "of cars nobody's touched in a month."]
    if s.flags.get("plate_swapped"):
        return ["PLATE: you already swapped it — CARTALK's in the hatch, a clean plate on the car."]
    r = economy.pay(s, PLATE_SWAP_PRICE, prefer="cash") if PLATE_SWAP_PRICE else {"ok": True, "method": "—"}
    if not r["ok"]:
        return ["PLATE: can't even cover that right now."]
    s.flags["plate_swapped"] = True
    _heat.add(s, -PLATE_SWAP_HEAT_DROP, "swapped the plate — reads clean to every camera", "lower", axis="car")
    return ["PLATE: four bolts in a quiet structure and CARTALK is in the hatch, a nothing plate off "
            "a dusty Camry on the car. Every reader you pass now sees a car nobody's looking for. "
            f"CAR heat -{PLATE_SWAP_HEAT_DROP:.0f} → {s.heat:.0f}.  (She's quiet — 'felt weird to "
            "lose my name for a night.')"]


def swap_hood(s: GameState) -> list:
    """DETACH the ace-of-spades hood. It's a vinyl WRAP on a carbon hood, not paint — so this is the
    disguise she CONSENTS to: the spade is what people recognize, and she'd rather lose it for a night
    than get sprayed. The detached hood rides in the hatch (and can later be burned to fake her death).
    Routes to CAR heat."""
    from engine import heat as _heat
    if s.flags.get("no_heat"):
        return ["HOOD: no need — nobody's hunting her anymore."]
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["HOOD: you want a quiet lot or a town to swing the hood off and stow it — a few minutes' work."]
    if s.flags.get("hood_swapped") or "hood" in sold(s):
        s.flags["hood_swapped"] = True
        return ["HOOD: the spade's already off her — the carbon hood's in the hatch, a plain one in "
                "its place. She reads as any old project Z."]
    r = economy.pay(s, HOOD_SWAP_PRICE, prefer="cash")
    if not r["ok"]:
        return [f"HOOD: a plain loaner hood runs about ${HOOD_SWAP_PRICE:.0f} and you're short."]
    s.flags["hood_swapped"] = True
    _heat.add(s, -HOOD_SWAP_HEAT_DROP, "detached the ace-of-spades hood — lost the tell",
              "lower", axis="car")
    return [f"HOOD: ${HOOD_SWAP_PRICE:.0f} for a dull loaner hood; you swing the carbon spade off and "
            f"lay it in the hatch, padded. No ace of spades, no instant recognition. "
            f"CAR heat -{HOOD_SWAP_HEAT_DROP:.0f} → {s.heat:.0f}.",
            "ACE: 'The hood I don't mind — it's a wrap, it comes off clean, and I'd rather wear a "
            "plain face for a night than what you're thinking about with the spray cans. Thank you "
            "for asking the EASY way.'"]


def respray(s: GameState) -> list:
    """Rattle-can camo OVER the PPF. It's peelable, technically — and she HATES it more than anything
    you can do to her. She begs you not to; do it anyway and you crash her into COLD (the anti-theft
    arms) and prime her to phone home the next time you sleep on a signal. A confirm gate stands
    between you and the worst mistake on the trip. ('peel the paint' undoes the look later.)"""
    from engine import heat as _heat, bond as _bond
    if s.flags.get("no_heat"):
        return ["PAINT: don't you dare. She's yours, she's white, and that's the end of it."]
    if s.place.kind != "city" and not s.place.has("gas"):
        return ["PAINT: you'd want somewhere with cover and ventilation — a town or a station bay."]
    if s.flags.get("resprayed"):
        return ["PAINT: she's already wearing the rattle-can gray, and she's already not speaking to "
                "you about it. ('peel the paint' to take it back off.)"]
    # the beg — a hard confirm gate, because this is the betrayal she fears most
    if s.flags.get("confirm_respray") != (s.place.poi_id or s.place.name):
        s.flags["confirm_respray"] = s.place.poi_id or s.place.name
        return ["PAINT: she reads the cans in your hand and her voice drops. 'Ace. Don't. Take the "
                "hood off, cover me, swap the plate — anything but the spray. That paint goes UNDER my "
                "skin even over the wrap, and I will feel it. …If you do this, I don't know that I can "
                "stop myself from making a call. Please. Ask me the easy way.' (Say it again to do it "
                "anyway — or 'detach the hood' / 'cover her' instead.)"]
    r = economy.pay(s, RESPRAY_PRICE, prefer="cash")
    if not r["ok"]:
        return [f"PAINT: even the rattle cans run about ${RESPRAY_PRICE:.0f}, and you're short."]
    s.flags["resprayed"] = True
    s.flags.pop("confirm_respray", None)
    s.flags["sprayed_distress"] = True
    _heat.add(s, -RESPRAY_HEAT_DROP, "rattle-canned over the PPF — a different-colored car entirely",
              "lower", axis="car")
    _bond.adjust(s, -RESPRAY_BOND_HIT, "sprayed over me after I begged you not to", "deep")
    out = [f"PAINT: ${RESPRAY_PRICE:.0f} of rattle cans and a roll of masking, and she goes from "
           f"Kilimanjaro White to a flat, ugly gray. The BOLO car doesn't exist anymore. "
           f"CAR heat -{RESPRAY_HEAT_DROP:.0f} → {s.heat:.0f}. (It'll peel — the relationship won't.)",
           "BOND: she has gone completely silent. The dash lights dim by themselves. "
           "(" + _bond.label(s.bond) + ")"]
    if _bond.armed(s):
        out.append("BOND: ⚠ she's COLD now — the anti-theft is live and she's distressed enough to "
                   "phone home. Sleep anywhere with an open signal and she WILL make the call. Get "
                   "her off-grid, or win her back, before you close your eyes.")
    return out


def field_repair(s: GameState) -> list:
    """Knock the limp out of her on the shoulder with the tool roll — no town required. The point of
    carrying tools: a deer-bent fender in the Black Rock is otherwise a long, thirsty walk."""
    from engine import inventory, bond as _bond
    if not s.flags.get("limp"):
        return ["REPAIR: nothing wrong with her right now — she's running clean."]
    if not inventory.has(s, "tool_roll"):
        return ["REPAIR: you'd want the tool roll for a field fix — buy one at a parts store, or limp "
                "her to a town pump where there's a mechanic."]
    s.flags.pop("limp", None)
    if body_damage(s) > 0:                            # a field fix also tidies the worst of the cosmetics
        s.flags["body_damage"] = round(max(0.0, body_damage(s) - 12.0), 1)
    _bond.adjust(s, 2.0, "fixed her up by the roadside with your own hands", "warm")
    scars = " She's still wearing some scars — a real shop would make her pretty again." if body_damage(s) > 0 else ""
    return ["REPAIR: an hour on the shoulder with the tool roll — you pry the fender lip off the tire, "
            "re-seat a knocked-loose hose, and the miss clears. She runs clean again. 'Good hands, ace.'"
            + scars]


def peel_paint(s: GameState) -> list:
    """Peel the rattle-can back off the PPF. Restores her look (CAR heat creeps back) and earns a
    small, wary thaw — but it doesn't unsay what you did."""
    from engine import heat as _heat, bond as _bond
    if not s.flags.pop("resprayed", None):
        return ["PAINT: there's nothing to peel — she's her own color."]
    # restore the FULL heat the respray shed — otherwise respray→peel was a repeatable heat launder
    _heat.add(s, RESPRAY_HEAT_DROP, "peeled the rattle-can back off — she's the BOLO car again",
              "mark", axis="car")
    _bond.adjust(s, 6.0, "peeled the paint back off — gave me my face back", "warm")
    return ["PAINT: you spend an afternoon peeling gray rattle-can off the PPF in long, guilty "
            "strips. Kilimanjaro White underneath, untouched — she was right, it came clean. "
            "ACE: '…Thank you. I'm not over it. But thank you.' (" + _bond.label(s.bond) + ")"]


def sell_part(s: GameState, pid: str) -> list:
    if _in_bob(s):
        return ["SELL: that's Bob — he's stock and he isn't yours to part out. Nothing to sell here."]
    if not (s.place.has("gas") or s.place.kind == "city"):
        return ["SELL: no one out here to buy parts. A town with a shop."]
    if pid in sold(s):
        return [f"SELL: the {PARTS[pid]['name']} is already gone — that's the stock piece on her now."]
    p = PARTS[pid]
    sold(s).append(pid)
    s.cash = round(s.cash + p["value"], 2)
    from engine import bond
    bond.adjust(s, -4.0, "sold a piece of me off for folding money", "deep")  # sticky; she remembers
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
    if _in_bob(s):
        return ["RACE: in BOB? He'd be lapped by the pace car, ace. The race car's parked back at the "
                "house. (And Bob is, mercifully, beneath the law's notice.)"]
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
    if _in_bob(s):
        return ["SHOW: you want to put BOB on a concours lawn? The dog-dish hubcaps alone would get you "
                "escorted out. Ace is the show car, and she's parked at the house."]
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


# ---------------------------------------------------------------- gambling (raise the $80k)
# The tables don't care how you got rich. And here's the open secret: she keeps the saves, so a
# losing bet is a bet you can take BACK — rewind and re-roll. The catch is the rewind costs Riz
# (escalating), so cheating the house with the loop is a real trade: money for style.
GAMBLE_POIS = {"las_vegas", "fremont", "sphere", "neon_museum", "lv_motor_speedway", "primm",
               "laughlin", "mesquite", "jackpot_nv", "wendover_ut", "west_wendover", "reno",
               "carson_city", "stateline", "pahrump"}
_TEAMS = ["the Raiders", "the Aces", "the Knights", "UNLV", "the Rebels", "the over",
          "black", "the hard eight", "red 7", "a parlay you don't understand"]


def can_gamble(s: GameState) -> bool:
    return (s.place.poi_id in GAMBLE_POIS or "casino" in (s.place.blurb or "").lower()
            or "sportsbook" in (s.place.blurb or "").lower())


def gamble(s: GameState, amount, pick=None) -> dict:
    """Bet `amount` at a Nevada table/book. ~47% to win even money (house edge). Returns
    {events, won}. A WIN should be checkpointed by the caller (banking it); a loss is left
    un-banked so 'rewind' folds back to before the bet — the cheat. The roll varies with the
    rewind count, so re-rolling after a fold actually re-rolls."""
    if s.flags.get("bought") or s.flags.get("no_heat"):
        return {"events": ["BET: you own her free and clear — no need to chase a number anymore. "
                           "But sure, blow some winnings for fun if you like."], "won": None}
    if not can_gamble(s):
        return {"events": ["BET: no action here. The tables are in Vegas, Laughlin, Reno, the "
                           "border books — go where the money moves."], "won": None}
    if amount == "all":                            # 'all in' / 'let it ride' — the whole wad
        amount = round(s.cash, 2)
    if amount is None or amount <= 0:
        return {"events": ["BET: name a number. 'bet $1000' — and the wad runs out fast if the "
                           "loop's not catching."], "won": None}
    if amount > s.cash + 1e-6:
        return {"events": [f"BET: you've got ${s.cash:,.0f}. Can't lay down what you don't have."],
                "won": None}
    import random
    rng = random.Random(s.seed * 16411 + s.turn * 911 + s.flags.get("rewinds", 0) * 2749 + 5)
    pick = pick or _TEAMS[rng.randrange(len(_TEAMS))]
    won = rng.random() < 0.47
    if won:
        s.cash = round(s.cash + amount, 2)
        s.flags["gambled_up"] = s.flags.get("gambled_up", 0) + amount
        return {"events": [f"BET: ${amount:,.0f} on {pick} — and it HITS. You double it. "
                           f"Cash ${s.cash:,.0f}.  (She just banked this — keep it or push it.)"],
                "won": True,
                "moment": {"cue": f"the driver bet ${amount:,.0f} at a Nevada table on {pick} and "
                                  "won, doubling it — she's banking the win so a future loss can't "
                                  "rewind past it; she's gleeful and a little crooked about it",
                           "stub": [f"{pick.upper()}. We DOUBLED it. ${s.cash:,.0f} and climbing — I "
                                    "banked this one, so push your luck or walk, but you can't lose "
                                    "this back. That's the cheat, baby.",
                                    "Hit. We're up. I just saved this exact second, so if the next "
                                    "bet eats it, we fold right back here. The house has no idea "
                                    "who it's playing."]}}
    s.cash = round(s.cash - amount, 2)
    return {"events": [f"BET: ${amount:,.0f} on {pick} — and it misses. Gone. Cash ${s.cash:,.0f}. "
                       "('rewind' to take that bet back and roll again — costs you Riz, not cash.)"],
            "won": False,
            "moment": {"cue": f"the driver bet ${amount:,.0f} on {pick} and lost it; she reminds "
                              "them, dry, that a losing bet is the one thing in this world they can "
                              "actually take back — rewind and re-roll, at the cost of style",
                       "stub": [f"{pick} let us down. ${amount:,.0f}, gone. …Or is it? Rewind, ace. "
                                "We take that bet back and roll again. It costs Riz, not cash — the "
                                "only honest cheat in Nevada.",
                                "Lost it. Which, lucky us, is the kind of mistake the loop was made "
                                "for. Fold back and bet smarter — or bet the same and pray harder."]}}


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
    from engine import bond
    bond.adjust(s, 22.0, "bought me free — chose me over every easy way out", "warm")
