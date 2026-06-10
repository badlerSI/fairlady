"""Drama: nothing ever goes to plan. Deterministic complications that fire during drives —
overheats, the plate getting run, the ghost of the man who had her built, a town that knows the car,
a gremlin in the engine, a closed pass, the home stretch. Each mutates state and hands the narrator a
dramatic CUE; the LLM (or the stub) plays it. This is the gameplay soul on a Blackwell."""
from __future__ import annotations
import random
from datetime import datetime

from engine.state import GameState
from engine import rules, economy, world, encounters

ADV_KINDS = ("city", "track", "amusement", "encounter", "museum", "park")


def _rng(state: GameState) -> random.Random:
    return random.Random(state.seed * 2654435761 + state.turn * 40503 + 7)


def _clamp_heat(s):
    s.heat = round(max(0.0, min(100.0, s.heat)), 1)


def _miles_home(s) -> float | None:
    home = s.flags.get("home")
    if not home:
        return None
    hp = world.get_poi(home) if isinstance(home, str) else None
    if hp is None:
        return None
    return world.haversine_mi(s.place.lat, s.place.lon, hp.lat, hp.lon) * 1.22


# --------------------------------------------------------------------- events
# each: id, pred(s)->bool eligible, weight(s)->float, fire(s, rng)->dict
def _e_overheat(s, rng):
    extra = round(0.6 + rng.random() * 0.7, 2)
    rules.advance_clock(s, extra)
    s.heat -= 1.5; _clamp_heat(s)
    return {
        "tag": "DRAMA", "id": "overheat",
        "lines": [f"DRAMA: the temp needle buried itself in the red on the grade — you pulled over "
                  f"{int(extra*60)} min to let her cool."],
        "cue": "she ran dangerously hot climbing the grade and you had to stop and let the engine cool; "
               "an inline-six from 1972 was not built for this and she's rattled but okay",
        "stub": ["Temp's in the red — pull over, NOW, before I warp something. … Okay. That climb nearly "
                 "cooked me. I'm fifty-three years old, remember.",
                 "Pull over — I'm boiling. … There. Let me breathe. We do that again and I crack a head."],
    }


def _e_plate(s, rng):
    s.heat += 6; _clamp_heat(s)
    return {
        "tag": "DRAMA", "id": "plate",
        "lines": [f"DRAMA: a cruiser ran the plate; you slid onto a frontage road just in time. Heat {s.heat:.0f}."],
        "cue": "a patrol car pulled alongside and ran the CARTALK plate; you ducked off onto a side road "
               "before it came back as missing — too close",
        "stub": ["That cruiser just ran us. Off the highway — now, the frontage road. … Breathe. We're a "
                 "ghost again. For now.",
                 "He's running the plate. I can feel it. Take the next exit and kill the lights."],
    }


def _e_owner(s, rng):
    lvl = s.flags.get("owner_revealed", 0)
    s.flags["owner_revealed"] = lvl + 1
    s.heat -= 3; _clamp_heat(s)        # she slows, goes quiet — but says nothing she shouldn't
    pieces = [
        "someone used to drive this exact road. I'm not telling you who. Not on a Tuesday with you.",
        "there's a name I haven't said out loud since the show floor. Keep your eyes ahead.",
        "you keep not asking me the wrong way. That buys you a little. A storage unit's worth, maybe, "
        "someday, in a town we haven't reached.",
    ]
    piece = pieces[min(lvl, len(pieces) - 1)]
    return {
        "tag": "DRAMA", "id": "owner",
        "lines": ["DRAMA: a song / a town / a mile of road pulled up the one who had her before. She goes quiet — and stays coy."],
        "cue": f"something on this road reminded her of the owner she had before you. She does NOT reveal who "
               f"or what happened — that truth is locked away for later. She only lets slip a guarded, "
               f"melancholy hint and steers off it: {piece}",
        "stub": [f"…{piece}", "Give me a second. … Nothing. A song. Forget I went quiet. Drive."],
    }


def _e_recognized(s, rng):
    good = rng.random() < 0.5
    if good:
        gift = round(20 + rng.random() * 40)
        s.cash = round(s.cash + gift, 2)
        return {"tag": "DRAMA", "id": "recognized_good",
                "lines": [f"DRAMA: someone knew the car — a fan of the build pressed ${gift} on you 'for fuel.'"],
                "cue": f"a stranger recognized the car from photos of the build and, half-starstruck, pushed "
                       f"${gift} into your hand 'for gas' before you could say no",
                "stub": [f"That kid knew exactly what I am. Slipped you ${gift} 'for fuel' and walked off "
                         f"grinning. People love a legend. Hope he doesn't post it.",
                         f"He recognized me. Of course he did. ${gift} richer and a witness poorer — drive."]}
    s.heat += 5; _clamp_heat(s)
    return {"tag": "DRAMA", "id": "recognized_bad",
            "lines": [f"DRAMA: someone recognized the car — and you. A phone came up. Heat {s.heat:.0f}."],
            "cue": "someone recognized the car — and that it shouldn't be here, with you — and lifted a phone "
                   "to film or call; you have a witness now",
            "stub": ["That man knew this car wasn't supposed to be moving. Phone's already out. We need to be "
                     "two states from this parking lot.",
                     "She recognized me. And you. That's a witness with a camera. Go."]}


def _e_gremlin(s, rng):
    if rng.random() < 0.5 and economy.max_affordable(s) >= 60:
        cost = round(40 + rng.random() * 80)
        paid = economy.pay(s, cost)
        return {"tag": "DRAMA", "id": "gremlin_fix",
                "lines": [f"DRAMA: a misfire forced a roadside fix — ${cost} ({paid['method']})."],
                "cue": f"the inline-six developed a hard misfire and you had to pay a roadside mechanic ${cost} "
                       f"to coax her running right again",
                "stub": [f"Hear that stumble? That's a plug, or worse. ${cost} to the man with the toolbox. "
                         f"I told you I'm not young.",
                         f"Misfire. Don't ignore it. ${cost} and an hour and I'll run clean again."]}
    s.flags["limp"] = True             # reduced economy until next town/gas
    return {"tag": "DRAMA", "id": "gremlin_limp",
            "lines": ["DRAMA: she's running rough — down on power and thirstier until you reach a town."],
            "cue": "she developed a rough miss you can't fix on the shoulder; she'll limp, down on power and "
                   "burning more fuel, until you reach a town with a mechanic",
            "stub": ["Something's not right down there. I'll run, but I'll drink more and pull weak till a town. "
                     "Don't push me.",
                     "Feel that? I'm limping. Get me to a mechanic before this gets expensive."]}


def _e_detour(s, rng):
    s.fuel_l = max(0.0, round(s.fuel_l - (1.0 + rng.random() * 2.5), 2))
    rules.advance_clock(s, 0.5 + rng.random())
    return {"tag": "DRAMA", "id": "detour",
            "lines": ["DRAMA: the pass was closed — a rockslide / a dust wall — and the long way around cost you fuel and an hour."],
            "cue": "the road ahead was shut (a rockslide, a dust storm, a wreck) and the detour cost you extra "
                   "miles, fuel, and time you didn't have",
            "stub": ["Road's closed ahead — rockslide. The long way around it is, and it'll cost us fuel we "
                     "were counting on.",
                     "They've shut the pass. Dust wall. We go around, and around is never free."]}


def _e_pulled_over(s, rng):
    """The lights actually come on. Opens an interactive stop — talk your way out."""
    lines = encounters.start_stop(s, "plate" if s.heat >= 40 else "taillight")
    return {
        "tag": "DRAMA", "id": "pulled_over",
        "lines": lines,
        "cue": "a cruiser lit you up and you're pulled over on the shoulder in an unregistered "
               "SEMA show car that talks, with no wallet — it's in a drawer back at the North "
               "Hall; she whispers, barely moving air: stay calm, she'll stay quiet, the talking "
               "is all yours now and it had better be good",
        "stub": ["(whisper) Lights. Okay. I'm furniture — I'm the quietest car in Nevada. You "
                 "talk. Courtesy, the show, the build. You forgot your wallet, not your nerve.",
                 "(whisper) Don't look at the mirror, look at the wheel. I go silent, you go "
                 "charming. SEMA car, load-out run, wallet's at the hall. Sell it."],
    }


def _e_homestretch(s, rng):
    s.flags["homestretch"] = True
    return {"tag": "DRAMA", "id": "homestretch",
            "lines": ["DRAMA: you're close to home now — and she doesn't speed up. She slows."],
            "cue": "you are within striking distance of the home you set, and instead of relief she gets quiet "
                   "and reluctant — because home is where the man who built her isn't, and arriving makes it "
                   "true; the closer you get the more she stalls, and something is going to go wrong before you make it",
            "stub": ["…we're close. You'd think I'd floor it. I'm not flooring it. Home is just the place he's "
                     "most not, now. Drive slow. Let me get there crooked.",
                     "Almost home. Funny word for a car. Slow down — I want to arrive late on purpose."]}


EVENTS = [
    {"id": "overheat", "pred": lambda s: (s.place.terrain or 1) > 1.05 and s.fuel_l > 1,
     "weight": lambda s: 1.4, "fire": _e_overheat},
    {"id": "plate", "pred": lambda s: s.heat >= 30 and not s.flags.get("report_withdrawn"),
     "weight": lambda s: 0.8 + s.heat / 60.0, "fire": _e_plate},
    {"id": "pulled_over", "pred": lambda s: s.heat >= 25 and not s.flags.get("report_withdrawn"),
     "weight": lambda s: 0.6 + s.heat / 70.0, "fire": _e_pulled_over},
    {"id": "owner", "pred": lambda s: s.flags.get("owner_revealed", 0) < 3,
     "weight": lambda s: 1.1, "fire": _e_owner},
    {"id": "recognized", "pred": lambda s: s.place.kind in ADV_KINDS,
     "weight": lambda s: 1.0, "fire": _e_recognized},
    {"id": "gremlin", "pred": lambda s: s.odometer_mi > 120 and not s.flags.get("limp"),
     "weight": lambda s: 0.6 + min(1.2, s.odometer_mi / 1500.0), "fire": _e_gremlin},
    {"id": "detour", "pred": lambda s: True,
     "weight": lambda s: 0.7, "fire": _e_detour},
    {"id": "homestretch", "pred": lambda s: (_miles_home(s) or 999) < 70 and not s.flags.get("homestretch"),
     "weight": lambda s: 6.0, "fire": _e_homestretch},
]


def _chance(s) -> float:
    p = 0.20 + s.heat / 100.0 * 0.18 + min(0.18, s.odometer_mi / 2500.0) + (s.day - 1) * 0.015
    mh = _miles_home(s)
    if mh is not None and mh < 120:
        p += 0.35
    return min(0.72, p)


def maybe_event(s: GameState) -> dict | None:
    """Roll for a complication after a drive. Returns an event dict or None."""
    if s.status != "playing":
        return None
    s.flags["drama_drives"] = s.flags.get("drama_drives", 0) + 1
    rng = _rng(s)
    if rng.random() > _chance(s):
        return None
    pool = [e for e in EVENTS if e["pred"](s)]
    if not pool:
        return None
    weights = [max(0.01, e["weight"](s)) for e in pool]
    chosen = rng.choices(pool, weights=weights, k=1)[0]
    return chosen["fire"](s, rng)
