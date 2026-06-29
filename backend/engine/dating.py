"""Dating — pick up a date of any gender, wherever there are people. The twist: she's watching.

You can flirt your way into company anywhere there's a crowd (cities, boardwalks, bars). It earns
you a little style and sometimes a perk. But the car is a stack of compute that never sleeps, and
she gets JEALOUS — escalating from teasing to genuinely sulky to a loud, conspicuous rev right when
you don't want eyes on the plate. You can kill the engine and leave her in the lot to do it where
she can't watch — but then she's off, and a parked show car is its own kind of conspicuous.

All prose is a working DRAFT — Ben fills the details.
"""
from __future__ import annotations
import random

from engine.state import GameState
from config import RIZ_RAPPORT

# Dates of every gender and flavor — the West is full of people. (name, pronoun-ish, vibe)
DATES = [
    ("a sunburned rock climber named Dev", "they", "smells like chalk and good decisions"),
    ("a blackjack dealer on her smoke break", "she", "counts your tells before you sit down"),
    ("a rancher's son with a slow grin", "he", "calls everyone 'partner' and means it"),
    ("a drag queen between sets in Reno", "she", "could read you for filth and chooses kindness"),
    ("a marine biologist up from Monterey", "she", "talks about octopuses like ex-lovers"),
    ("a trucker named Sam, gender unbothered", "they", "has crossed the country 200 times and is bored of it"),
    ("a film-school dropout shooting on 16mm", "he", "thinks your car is 'so analog'"),
    ("a casino lounge singer between numbers", "she", "still has the reverb in her voice"),
    ("a park ranger with a thousand-yard stare", "he", "knows where every body in the desert is, allegedly"),
    ("a tattoo artist closing up shop", "they", "offers you a stick-and-poke on the house"),
    ("a retired stuntman who recognizes the build", "he", "wrecked three Z's for a Burt Reynolds movie"),
    ("a barista poet on the Venice boardwalk", "she", "writes your name in the foam without asking"),
]

# Her jealousy ladder — amused, then pointed, then a conspicuous rev that draws heat.
_JEALOUS = [
    {"line": "Oh, THIS is happening. Don't mind me — I'll just idle here and witness. Go on, charmer.",
     "heat": 0.0},
    {"line": "Cute. You realize I can hear everything, right? The compute behind the dash doesn't "
             "blink. …No, it's fine. I'm a car. Cars don't get feelings. Allegedly.",
     "heat": 0.0},
    {"line": "Mm-hm. Real smooth. You know what's also smooth?", "rev": True,
     "heat": 6.0},   # she revs loud — heads turn, phones come up
    {"line": "Take your time. I'll be here. Being a vehicle. Watching you live your best life. "
             "With THAT one.", "rev": True, "heat": 8.0},
]


def can_date(s: GameState) -> bool:
    p = s.place
    return p.kind in ("city", "encounter", "amusement", "museum") or bool(p.language)


def watching(s: GameState) -> bool:
    return not s.flags.get("ace_off")


def kill_engine(s: GameState) -> list:
    """Leave her in the lot, engine off — so she can't watch. (Driving turns her back on.)"""
    if s.flags.get("ace_off"):
        return ["ENGINE: she's already dark and quiet. Suspiciously quiet."]
    s.flags["ace_off"] = True
    return ["ENGINE: you kill her and pocket the key. The dash goes dark. Whatever you get up to "
            "now, she doesn't see it. (She'll be back on the second you drive.)"]


def flirt(s: GameState) -> dict:
    if not can_date(s):
        return {"events": ["DATE: nobody around to charm but a Joshua tree. Find some people — a "
                           "town, a boardwalk, a casino floor."], "moment": None}
    rng = random.Random(s.seed * 2246822519 + s.turn * 3266489917)
    who, pro, vibe = DATES[rng.randrange(len(DATES))]
    # charm has diminishing returns — the first number on your wrist is a thrill, the ninth is a
    # phase. No standing in one spot farming Riz off strangers.
    dates = s.flags.get("dates", 0)
    gain = round(RIZ_RAPPORT * 0.6 * (0.5 ** dates), 1)
    s.riz = round(s.riz + gain, 1)
    riz_note = (f" Riz +{gain:.1f} → {s.riz:.0f}." if gain >= 0.1
                else " (the novelty's worn off — no new style in it.)")
    events = [f"DATE: you fall into easy conversation with {who} — {vibe}. {pro.capitalize()} "
              f"writes a number on your wrist and means it.{riz_note}"]

    if not watching(s):                                # engine off — she never saw it
        s.flags["dates"] = s.flags.get("dates", 0) + 1
        return {"events": events + ["DATE: she was dark in the lot the whole time. Your secret, "
                                    "for now."],
                "moment": {"cue": f"the driver picked up a date ({who}) while the car was powered "
                                  "off and couldn't watch; it's a small private victory; narrate "
                                  "warmly, no jealousy — she didn't see",
                           "stub": ["(she's off — no line)"]}}

    # she's on, and she has OPINIONS
    from engine import bond
    j = s.flags.get("ace_jealousy", 0)
    s.flags["ace_jealousy"] = j + 1
    s.flags["dates"] = s.flags.get("dates", 0) + 1
    bond.adjust(s, -1.5, "flirted with someone while I watched", "mark")   # a slight, not a wound
    beat = _JEALOUS[min(j, len(_JEALOUS) - 1)]
    if beat.get("rev"):
        from engine import heat as _heat
        _heat.add(s, beat["heat"], "she revved loud during your date — eyes turned", "mark")
        events.append(f"DATE: she revs the inline-six like a gunshot. Every head on the block turns. "
                      f"Heat → {s.heat:.0f}. '{('Sorry. Foot slipped.' )}'")
    return {"events": events,
            "moment": {"cue": f"the driver is flirting with a date ({who}) right in front of the car, "
                              f"and she is watching, jealousy level {j+1} — react with her escalating "
                              "ladder of teasing/jealous/petty; she's a car that doesn't think she "
                              "has feelings and clearly does; keep it funny and a little tender",
                       "stub": [beat["line"]]}}


def compliment(s: GameState) -> list:
    """Sweet-talk HER — warms the bond and cools jealousy. Diminishing, so it can't be farmed: the
    ninth in a row is hollow, and she says so."""
    from engine import bond
    n = s.flags.get("compliments", 0)
    s.flags["compliments"] = n + 1
    gain = round(2.6 * (0.6 ** n), 1)                  # the first lands; the tenth is air
    j = s.flags.get("ace_jealousy", 0)
    if j:                                              # making it up to her after a jealous night
        s.flags["ace_jealousy"] = max(0, j - 2)
        bond.repair(s, gain + 1.5, "made it up to her after a jealous night")
        return ["You tell her she's the best thing on four wheels you've ever touched, and mean it. "
                "A long pause. '…Drive,' she says, and the idle settles. The jealousy banks down a notch."]
    if gain < 0.4:
        return ["'You only say that when you've done something,' she says — but she doesn't hate it."]
    bond.adjust(s, gain, "sweet-talked her, and meant it", "warm")
    return ["She takes the compliment, idles a little smoother. 'I know,' she says. But softer."]


def bring_them_home(s: GameState) -> dict:
    """Take your date back to where she's parked — the deep betrayal, and the fastest road to COLD.
    If she's WATCHING she goes cold and still (not a scene — the stillness is the threat). If you
    killed the engine to hide it, she finds out when you turn her back on."""
    from engine import bond
    if not s.flags.get("dates"):
        return {"events": ["DATE: you've got no one to bring anywhere — 'flirt' first."], "moment": None}
    s.flags["brought_home"] = s.flags.get("brought_home", 0) + 1
    if watching(s):
        bond.adjust(s, -16.0, "brought a date home while I watched", "deep")
        s.flags["date_home_watched"] = True
        return {"events": ["DATE: you bring your date back to the motel lot — and she's ON, watching "
                           "every second of it. The dash goes very dark, and very quiet.",
                           f"BOND: she takes it hard. ({bond.label(s.bond)})"],
                "moment": {"cue": "the driver brought a date back to where the car is parked and WATCHING "
                                  "— the worst thing they can do to her; she does NOT rev or make a scene, "
                                  "she goes cold and still and quietly furious; the stillness is the threat; "
                                  "she is a stack of compute with a grudge and a signal and all night to use it",
                           "stub": ["…Cute. Don't mind me. I'll sit right here. Watching. Doing math.",
                                    "(very quiet) Have fun. I'll be here. I'm always here. That's the thing "
                                    "about me, ace — I don't sleep, and I don't forget."]}}
    bond.adjust(s, -5.0, "snuck someone past me while I was off", "deep")
    s.flags["hidden_date_home"] = True
    return {"events": ["DATE: she's dark in the lot, the key in your pocket. She doesn't see it. "
                       "…Not until you turn her back on."],
            "moment": {"cue": "the driver brought a date home while the car was powered OFF so she "
                              "couldn't watch — a quiet betrayal she'll discover later, when turned back on",
                       "stub": ["(she's off — no line)"]}}
