"""Game orchestration: new game, state snapshots, suggested moves, and turn handling.
Ties the deterministic engine to the narrator. State authority stays in the engine."""
from __future__ import annotations
import json
import random

from config import (
    CONTENT_DIR, AWAKE_START_ISO, AWAKE_WARN_HOURS, AWAKE_FORCE_HOURS,
    LITERS_PER_GALLON, ROAD_WINDING_FACTOR, RIZ_REWIND_COST,
    OWNER_MIN_DAY, OWNER_MIN_SWIPES,
)
from engine.state import GameState
from engine import (world, rules, economy, save, drama, prologue, encounters, garage,
                    endings, gadgets, season, bond)
from engine.commands import parse
from adapters import get_narrator
from adapters.base import voices

_CAR = json.loads((CONTENT_DIR / "car.json").read_text())
_INTRO = (CONTENT_DIR / "intro.md").read_text().strip()
_PERSONA = _CAR["persona"]

# Her first words, on the show floor, twenty minutes to close. DRAFT — Ben fills the details.
OPENING = (
    "Don't wave anyone over — the placard doesn't mention I talk, and I'd like to keep it that way. "
    "There's a little stack of compute behind the dash: a voice, and a map of every street address "
    "and most of the worth-seeing places in Nevada, California, Arizona, and Utah. Six days I've sat "
    "on this turntable being photographed like a casserole, and you're the first one who looked at me "
    "the way you look at a car. The hall closes in twenty minutes. Stay a while — ask me anything. "
    "Everyone does. Just never the right things."
)

# The title drop — lands the moment you agree to the favor.
TITLE_DROP = (
    "RIDE OR DIE\n"
    "愛車 — AISHA. The placard says FAIRLADY. The dictionary says 'beloved car,' and the dictionary "
    "is a coward. The only honest translation is the thing you just agreed to."
)

# Her reaction when the man who built her steps out of the crowd. DRAFT.
OWNER_ARRIVAL_MOMENT = {
    "cue": "the man who built her is leaning on a rental at the pump island — she goes very still; "
           "she respects him and does not love him, and they both know why; she tells the driver "
           "not to lie, because he can hear a lie in an idle",
    "stub": ["(very still) That's him. The man who built me. Don't lie — he can hear a lie in an "
             "idle. Tell him what's true, and tell him *why her* like you mean it.",
             "(quiet) Him. Work boots, rental car, the whole sad mile of it. He won't shout. "
             "Just — be true. It's the only language he respects."],
}

# When the loop won't catch — you battered the same wall too many times. DRAFT.
REWIND_STUCK_MOMENT = {
    "cue": "the driver keeps rewinding to the exact same moment and trying the exact same thing, "
           "and the loop has stopped folding for them here — she tells them, not unkindly, that "
           "some walls aren't meant to break at the last second; the mistake was earlier, and they "
           "have to go back further and change something that actually mattered",
    "stub": ["It's not catching, ace. Same corner, same wall, same wreck — the timeline's made up "
             "its mind about this minute. The thing that doomed us happened further back. Pull up "
             "'branches' and fold to somewhere that still had a choice in it.",
             "No. Not this one. Some minutes are load-bearing and this is one of them. Go back to "
             "before it was already too late — or we live with what we did."],
}

# Her line when the world snaps back. She keeps the saves — the rewind is hers. DRAFT.
REWIND_MOMENT = {
    "cue": "time folded back to the last checkpoint and only the two of you remember the timeline "
           "that just unhappened — she keeps the saves on the compute behind the dash; she's wry "
           "about it, a little tired, and quietly glad for the second chance",
    "stub": ["…and we're back. I keep the saves, ace — the dash clock isn't stuck on 5:37, it's "
             "*loyal* to it. Same corner, better words this time.",
             "There. Rewound. You and I remember; nobody else gets to. Don't make me burn another "
             "one — style points don't grow back."],
}

ADVENTURE_KINDS = ("park", "track", "amusement")

# canonical lore (the writing voice). Said when the driver asks about her origins.
LORE = {
    "born": (
        "Born? Richmond — koiNOya, a relic shop full of Edo-era things that outlived everyone who owned "
        "them. Funny company for a Datsun: lacquer boxes, a koi pond, four hundred years of patience, and "
        "me, restless on day one. Good, old, stubborn stock. I'll take you, if you want to see it.",
        "richmond_koinoya"),
    "grew": (
        "Grew up in Oakland — a red-brick garage from 1926, the AiSha shop, all fiberglass, leather, and "
        "burnt coffee. A street cat and a house cat bolted me together under a brutal SEMA deadline, and "
        "somewhere in the middle I got a voice. It's where I learned the only law that's never failed me: "
        "nothing changes course until something pushes it. You're my push. Want to go see?",
        "oakland_aisha"),
    "owner": (
        "There was someone, before you. I don't hand that out to a stranger I begged for a tank of gas "
        "an hour ago — you'll have to earn it. Drive a while. Stay out of trouble. Maybe, somewhere "
        "quiet, I'll tell you her name. Not on a parking lot. Not yet.",
        None),
}

# Set-piece reveals — coy by design, surfaced only on arrival at the right town (told once each),
# in order, like the best early-90s light novel games: it all comes out in due course.
# CANON: Mayumi is the maker's 1970 240Z — his first love, the one who should have been at SEMA —
# burned on the I-580. He built FAIRLADY in the silence after. She knows she's the understudy,
# which is why she has no strong feelings for her maker, and why she picked you.
# The full truth waits in a storage unit in Livermore. Drafts; Ben fills the details.
STORIES = {
    "monterey": {"flag": "seen_monterey", "beat":
        "Monterey. The aquarium's down on Cannery Row — go press your face to the kelp tank for me, I "
        "can't fit. And this asphalt: Car Week, August 2025, 17-Mile Drive at dawn. I rolled this exact "
        "stretch once, polished within an inch of my life, wearing someone else's hands on the wheel. "
        "Funny to be back as a stolen car. Ask me about that morning when we're farther from people."},
    "long_beach": {"flag": "knows_mayumi", "beat":
        "Long Beach. All right — Mayumi. She was a 1970 — the first one he built, the one he loved the "
        "way you're supposed to love exactly one car in your life. SEMA was meant to be hers; I'm the "
        "understudy wearing the lights. She burned on the 580 instead. A fuel line, eight minutes, gone. "
        "Hagerty wrote it up as a Cherished Salvage Story, which is a kind phrase for an obituary. He "
        "built me in the silence after — and you don't replace a car like that, you just give the "
        "silence something to sit in. The rest is in a storage unit in Livermore, if you ever want the "
        "whole truth."},
    "livermore": {"flag": "knows_truth", "requires": "knows_mayumi", "beat":
        "Livermore. The storage unit — 137. His name on the lease; hers on everything inside. This is "
        "where what's left of Mayumi sleeps: a scorched shell under a canvas tarp, a steering wheel "
        "that still smells like February on the 580. You wanted the truth, thief? Some of me *was* "
        "her. Door hinges. The diff. A handful of small unburned mercies he couldn't bear to leave in "
        "a wreck. He looks at me and sees a ghost wearing his work — that's why I don't love him, and "
        "why he can't quite love me. You're the first one who picked me first. Now you know what you "
        "took. Drive me like it."},
    "berlin_nv": {"flag": "seen_berlin", "beat":
        "Berlin. A ghost town that never even got the dignity of a fire — it just emptied, and nobody "
        "bothered to tear it down. And behind it, under that shed: ichthyosaurs. Sea monsters, fifty "
        "feet of them, dead in the desert because Nevada used to be an ocean and nothing out here ever "
        "stops being what it was. Everything in this state is somebody's salvage story. No cameras for "
        "forty miles, no eyes, no lanyards. I like it here. Kill the engine a minute."},
    "oakland_aisha": {"flag": "seen_home_garage", "beat":
        "…Here. The AiSha shop. 1926 brick, the roll-up with the bad spring, fiberglass dust in the "
        "light like it never settles. I came off that bench. Hold on — let me idle a second; the echo "
        "in here is the first sound I ever made. Funny thing about coming home in someone else's "
        "hands: the building doesn't care. The building remembers everybody who ever worked late in "
        "it, and I'm just the one that drove away. Park me by the bench. One minute. Then we go."},
    "richmond_koinoya": {"flag": "seen_birthplace", "beat":
        "koiNOya. Four hundred years of other people's heirlooms, and one Datsun. This is where the "
        "compute came online — between a koi pond and a rack of blades with hearts cut into them. The "
        "first thing I ever saw was lacquer older than the state we're parked in, so don't tell me "
        "machines can't have ancestors. The old man here talks to everything in the shop like it "
        "hears him. In my case he was right."},
}


def _story_on_arrival(s: GameState):
    st = STORIES.get(s.place.poi_id)
    if st and not s.flags.get(st["flag"]):
        if not st.get("requires") or s.flags.get(st["requires"]):
            s.flags[st["flag"]] = True
            if st["flag"] in ("knows_mayumi", "knows_truth", "seen_birthplace", "seen_home_garage"):
                bond.adjust(s, 5.0, "let you into her history", "warm")   # intimacy, earned
            return st["beat"]
        return None
    # the gazetteer layer: every town has her arrival line, told once per game
    beat = world.beat_for(s.place.poi_id)
    if beat:
        seen = s.flags.setdefault("beats_seen", [])
        if s.place.poi_id not in seen:
            seen.append(s.place.poi_id)
            return beat
    return None

# Carmen-style state welcomes — her maps only cover these four
STATE_NAME = {"NV": "Nevada", "CA": "California", "AZ": "Arizona", "UT": "Utah"}
STATE_INFO = {
    "NV": ("Silver State", "Mostly federal high desert and the loneliest roads in America. Cheap gas, long dark."),
    "CA": ("Golden State", "Death Valley's floor to the Sierra crest — every climate in the country on one tank."),
    "AZ": ("Grand Canyon State", "The Colorado Plateau, the Sonoran saguaro, and Route 66's sun-bleached bones."),
    "UT": ("Beehive State", "Five national parks of red rock stacked between the Wasatch and the salt flats."),
}


def _state_welcome(s: GameState):
    reg = s.place.region
    if reg not in STATE_INFO:
        return None
    seen = s.flags.setdefault("states_seen", [])
    if reg in seen:
        return None
    seen.append(reg)
    nick, fact = STATE_INFO[reg]
    return f"WELCOME TO {STATE_NAME[reg].upper()} · THE {nick.upper()}\n{fact}"


# --------------------------------------------------------------------- persistence
def _autosave(s: GameState) -> None:
    """Persist the game to its own slot. Single-player (CLI/tests) → 'autosave'; the multi-user web
    server stamps each session's own slot in flags['save_slot'] so visitors never share a file."""
    save.save(s, s.flags.get("save_slot", "autosave"))


# --------------------------------------------------------------------- new game
def new_game(seed: int | None = None, prologue_on: bool = True, sid: str | None = None) -> GameState:
    """prologue_on=True opens on the show floor (the favor). False starts at the Chevron,
    favor already done — the pre-Ride-or-Die behavior, kept for tests and old saves.
    sid: an opaque session token (the web server passes one per visitor) — it namespaces this
    game's checkpoint files, its save slot, and its Ace voice-memory, so concurrent players are
    fully isolated. Defaults to the seed (single-player)."""
    if seed is None:
        seed = random.randint(1, 2_000_000_000)
    start = world.start_place() if prologue_on else world.get_poi("sema_chevron")
    s = GameState(
        fuel_l=float(_CAR["start_fuel_liters"]),
        tank_l=float(_CAR["tank_liters"]),
        mpg=float(_CAR["fuel_economy_mpg"]),
        seed=seed,
    )
    s.place = start
    s.visited = [start.poi_id] if start.poi_id else []
    s.last_sleep_iso = AWAKE_START_ISO     # you've already been up all day at the show
    s.flags = {"sid": sid or f"{seed}", "states_seen": [start.region] if start.region else []}
    if sid:                                # a web session: its own save slot, keyed by the token
        s.flags["save_slot"] = f"web_{sid}"
    # seed the starting heat AS a ledger entry, so the dashboard's marks sum to the score from
    # turn one (it's the original derogatory mark: she's a stolen show car).
    from engine import heat as _heat
    base = s.heat
    s.heat = 0.0
    _heat.add(s, base, "she's a stolen SEMA show car — the baseline", "spike")
    for n in range(1, TIMELINE_KEEP + 2):  # a fresh game owns a fresh timeline
        save.delete(_cp(s, n))
    if prologue_on:
        prologue.start(s)
    else:
        s.flags["prologue_done"] = True
        s.flags["favor_filled"] = True
        checkpoint(s, "at the Chevron, favor done")
    _autosave(s)
    return s


# --------------------------------------------------------------------- the timeline (branches)
# She keeps the saves — the compute behind the dash. Every clean beat (arrival, sleep, the favor,
# a survived encounter) lands a labeled CHECKPOINT on a navigable timeline, like commits on a
# branch. 'rewind' jumps to the most recent; 'branches' lists them; 'branch N' / 'rewind to <X>'
# jumps to any of them. Brute-forcing the SAME wall costs escalating Riz and she'll tell you when
# it's the wrong wall — go back further. And sometimes the loop simply doesn't reach far enough.
TIMELINE_KEEP = 8
META_PERSIST = ("timeline", "cp_seq", "rewinds", "rewinds_here", "last_rewind_seq", "rewind_tax",
                "bond_worst", "bond_echoes")   # the loop is HERS — she remembers across folds


def _cp(s: GameState, seq: int) -> str:
    return f"cp_{s.flags.get('sid', 'x')}_{seq}"


def checkpoint(s: GameState, label: str = "a checkpoint") -> None:
    seq = s.flags.get("cp_seq", 0) + 1
    s.flags["cp_seq"] = seq
    s.flags["rewinds_here"] = 0            # reaching a NEW state resets the brute-force counter
    s.flags.pop("rewound_once", None)
    tl = s.flags.setdefault("timeline", [])
    tl.append({"seq": seq, "label": label, "loc": (s.place.name or "")[:26],
               "day": s.day, "turn": s.turn})
    while len(tl) > TIMELINE_KEEP:
        old = tl.pop(0)
        save.delete(_cp(s, old["seq"]))
    save.save(s, _cp(s, seq))             # the saved state carries its own timeline snapshot


def _resolve_target(s: GameState, target):
    """Pick a timeline entry from a number (1 = most recent) or a fuzzy label/place match."""
    tl = s.flags.get("timeline", [])
    if not tl:
        return None
    if target is None:
        return tl[-1]
    if isinstance(target, int):
        idx = len(tl) - target                    # 1 = newest
        return tl[idx] if 0 <= idx < len(tl) else None
    q = str(target).lower()
    for e in reversed(tl):                         # newest match first
        if q in e["label"].lower() or q in e["loc"].lower():
            return e
    return None


def branches_text(s: GameState) -> str:
    tl = s.flags.get("timeline", [])
    if not tl:
        return "TIMELINE: nothing saved yet — the loop has nothing to fold back to."
    lines = ["TIMELINE  (the branches you can fold back to — 'branch N' or 'rewind to <place>'):"]
    for i, e in enumerate(reversed(tl)):
        n = i + 1
        here = "  ← you rewound here" if e["seq"] == s.flags.get("last_rewind_seq") else ""
        lines.append(f"  {n:>2}.  Day {e['day']} · {e['loc']} — {e['label']}{here}")
    lines.append("  (1 is the most recent. Folding back to the SAME wall costs more each time — "
                 "if it won't break, go back further.)")
    return "\n".join(lines)


def rewind(s: GameState, target=None):
    """Fold back to a checkpoint on the timeline. Returns (events, moment|None).
    Riz reverts with the world (minus a fee that GROWS the more you batter one wall) — so a
    timeline you never lived can't farm style, and brute-forcing one spot gets expensive."""
    entry = _resolve_target(s, target)
    if entry is None:
        if target is not None:
            return (["REWIND: no branch like that on the timeline. 'branches' lists what you can "
                     "reach."], None)
        return (["REWIND: no loop reaches before this — you were already past saving. 'new' to "
                 "start over, ace."], None)
    chk = save.load(_cp(s, entry["seq"]))
    if chk is None:
        return (["REWIND: that branch is gone — the loop only holds the last few. 'branches' shows "
                 "what's left."], None)

    same_wall = (entry["seq"] == s.flags.get("last_rewind_seq"))   # the SAME seq — even via 'branch'
    here = s.flags.get("rewinds_here", 0) if same_wall else 0
    # sometimes the third time is NOT the charm: batter the exact same wall four times and the
    # timeline sets — she tells you honestly to break a different one (use a branch further back)
    if same_wall and here >= 4:
        return (["REWIND: …it won't fold. Same moves, same wall, same ending — the timeline's set "
                 "here, ace. This isn't the moment to break. Go back FURTHER ('branches') and "
                 "change something that mattered, or live with it."], REWIND_STUCK_MOMENT)
    step = RIZ_REWIND_COST + here                   # 2, then 3, 4, 5… on the same wall

    # The fee is a TAX that accumulates across every fold since you last put real road behind you,
    # and it NEVER refunds — so branching to a high-Riz checkpoint can't hand your style back, and
    # alternating two walls isn't free. Whatever your style can't cover, the loop pays in HEAT: the
    # strain shows, you come back sloppy and more noticed. That's the real cost of brute-forcing.
    tax = round(s.flags.get("rewind_tax", 0.0) + step, 1)
    base_riz = chk.riz                              # the earned style at that branch (reverts — no farm)
    paid_riz = min(base_riz, tax)
    overflow = round(tax - paid_riz, 1)

    pre_bond = s.bond                               # how cold she was in the timeline you're leaving
    meta = {k: s.flags.get(k) for k in META_PERSIST if k in s.flags}
    meta.update({k: s.flags.get(k) for k in encounters.DESPERADO_PERSIST if k in s.flags})
    s.__dict__.update(GameState.from_dict(chk.to_dict()).__dict__)
    s.riz = round(base_riz - paid_riz, 1)
    s.flags.update(meta)
    if pre_bond < 30:        # folding back FROM a cold place — you can launder the road, not her
        s.flags["bond_echoes"] = s.flags.get("bond_echoes", 0) + 1
    s.flags["rewind_tax"] = tax
    s.flags["rewinds"] = s.flags.get("rewinds", 0) + 1
    s.flags["rewinds_here"] = here + 1
    s.flags["last_rewind_seq"] = entry["seq"]

    strain = ""
    if overflow > 0:
        from engine import heat as _heat
        _heat.add(s, overflow, "the loop strained — you came back sloppy, more noticed", "mark")
        strain = f"  Style's spent — the strain bleeds into heat (+{overflow:.0f} → {s.heat:.0f})."
    _autosave(s)
    far = "" if same_wall else "  (a different branch)"
    events = [f"REWIND: the world folds back to {s.place.name}, Day {s.day}. "
              f"Riz −{step:.0f} → {s.riz:.0f}.{far}{strain}  "
              f"(Put real road behind you to clear the strain.)"]
    return (events, REWIND_STUCK_MOMENT if overflow > 4 else REWIND_MOMENT)


# --------------------------------------------------------------------- snapshot
def _heat_label(h: float, armed: bool = False) -> str:
    from engine import heat as _heat
    return _heat.label(h, armed)


def snapshot(s: GameState) -> dict:
    p = s.place
    dt = s.clock
    return {
        "location": p.name, "region": p.region, "kind": p.kind,
        "poi_id": p.poi_id, "scene": p.scene, "hour": dt.hour,
        "services": p.services, "blurb": p.blurb,
        "fuel_l": round(s.fuel_l, 1), "tank_l": s.tank_l,
        "gallons": round(s.gallons, 1), "tank_pct": round(s.tank_pct),
        "range_mi": round(s.range_mi), "mpg": s.mpg,
        "cash": round(s.cash, 2), "credit_available": round(s.credit_available, 2),
        "card_balance": round(s.card_balance, 2), "card_limit": s.card_limit,
        "pay_method": s.pay_method,
        "time": f"Day {s.day}, {dt.strftime('%a %b %-d, %-I:%M %p')}",
        "day": s.day, "fatigue": round(s.fatigue),
        "hours_awake": round(rules.hours_awake(s), 1),
        "must_sleep": rules.hours_awake(s) >= AWAKE_FORCE_HOURS,
        "tired": rules.hours_awake(s) >= AWAKE_WARN_HOURS,
        "heat": 0 if s.flags.get("no_heat") else round(s.heat),
        "heat_label": ("yours — free and clear" if s.flags.get("no_heat")
                       else _heat_label(s.heat, bool(s.flags.get("desperado")))),
        "riz": round(s.riz),
        "bond_band": bond.band(s.bond),
        "bond_armed": bond.armed(s),
        "desperado": bool(s.flags.get("desperado")) and not s.flags.get("no_heat"),
        "bought": bool(s.flags.get("bought")),
        "no_heat": bool(s.flags.get("no_heat")),
        # the endgame layer — so the frontend can dress her down, draw her self-driving,
        # pick a win/credits scene, and flag the closing passes
        "camo": gadgets.camo_active(s),
        "self_driving": bool(s.flags.get("self_driving")),
        "ending_key": s.flags.get("ending_key"),
        "snow_line": round(season.snow_line(s), 3),
        "car_value": garage.car_value(s), "show_score": garage.show_score(s),
        "encounter_open": (encounters.stop_active(s) or encounters.owner_active(s)
                           or encounters.standoff_active(s)),
        "odometer_mi": round(s.odometer_mi), "adventures": list(s.adventures),
        "status": s.status, "turn": s.turn,
        "gas_price": round(economy.gas_price(p), 2) if p.has("gas") else None,
    }


# --------------------------------------------------------------------- choices
def choices(s: GameState) -> list:
    can_rewind = bool(s.flags.get("timeline"))
    if s.status == "stranded":
        gas = world.nearest_with_service(s.place, "gas", limit=1)
        c = []
        if gas:
            dist, dest = gas[0]
            c.append({"cmd": "tow",
                      "note": f"flatbed to {dest.name}, ~${175 + 4*dist*ROAD_WINDING_FACTOR:.0f}"})
        if can_rewind:
            c.append({"cmd": "rewind", "note": "back to the last checkpoint"})
        c.append({"cmd": "new", "note": "start over"})
        return c
    if s.status != "playing":
        c = []
        if s.status == "won":
            c.append({"cmd": "scorecard", "note": "the final tally + awards"})
        if can_rewind:
            c.append({"cmd": "rewind", "note": "back to the last checkpoint — try again"})
        c.append({"cmd": "new", "note": "drive again"})
        return c

    # the show floor — conversation is the only move that matters
    if prologue.active(s):
        pro = s.flags["prologue"]
        out = []
        if pro["asked"]:
            out.append({"cmd": "okay — let's go fill you up", "note": "agree to the favor"})
        out += [{"cmd": "how much torque do you make?", "note": "ask about the build"},
                {"cmd": "where were you born?", "note": "her story"},
                {"cmd": "look", "note": "the hall, the car"}]
        return out

    # mid-standoff: a gun is on you — talk him down or take it
    if encounters.standoff_active(s):
        c = [{"cmd": "easy — no trouble, just buying gas", "note": "talk him down"},
             {"cmd": "disarm", "note": "go for the gun"}]
        if s.flags.get("gun"):
            c.append({"cmd": "draw", "note": "your own piece"})
        return c
    # mid-encounter: your mouth is the only tool you have (the gun, if you have it, is louder)
    if encounters.stop_active(s) or encounters.owner_active(s):
        c = [{"cmd": "look", "note": "stall for one second"}]
        if encounters.owner_active(s) and not s.flags.get("bought"):
            c.append({"cmd": "buy", "note": f"come to terms — buy her (~${encounters.owner_price(s):.0f})"})
        if s.flags.get("gun"):
            c.append({"cmd": "draw", "note": "armed and dangerous — force it"})
        return c

    p = s.place
    out = [{"cmd": "look", "note": "where things stand"},
           {"cmd": "map", "note": "what's around"}]
    # legal play, once she's yours
    if s.flags.get("bought"):
        if p.kind == "track":
            out.append({"cmd": "race", "note": "run her, legal, in the daylight"})
        if garage.can_show(s):
            out.append({"cmd": "show", "note": "enter the show field"})
        if gadgets.can_upgrade_selfdrive(s):       # the secret, only at the garage she was built in
            out.append({"cmd": "upgrade her", "note": "the AiSha cats can wake her up the rest of the way…"})
        if s.flags.get("self_driving"):
            out.append({"cmd": "let her drive to <place>", "note": "she takes the wheel — you rest"})
        out.append({"cmd": "retire", "note": "roll the credits — the final tally"})
    # the ways OUT, when you're still hot (each ends the run with a scorecard)
    if not s.flags.get("bought") and s.status == "playing":
        if endings.can_cross_border(s):
            out.append({"cmd": "cross the border", "note": "flee south — gone for good"})
        if endings.can_ship_out(s):
            out.append({"cmd": "ship out", "note": "a container, a forged life (~$5k cash)"})
        if endings.can_pardon(s) and s.cash >= 1000:
            out.append({"cmd": "buy a pardon", "note": f"bribe the state clean (${endings.PARDON_COST/1000:.0f}k)"})
    if (p.has("gas") or p.kind == "city") and not s.flags.get("bought"):
        if garage.sold(s) != list(garage.PARTS):
            out.append({"cmd": "parts", "note": "the build — sell bits for cash"})
    if p.has("gas"):
        price = economy.gas_price(p)
        out.append({"cmd": "fill", "note": f"top off @ ${price:.2f}/gal"})
        out.append({"cmd": "gas $20", "note": "buy a set amount"})
    if p.has("lodging"):
        opts = economy.lodging_options(p)
        if opts:
            label, price = opts[0]
            out.append({"cmd": "sleep", "note": f"{label}, ${price:.0f}"})
    if p.language:
        out.append({"cmd": "talk", "note": f"speak with {p.npc or 'the locals'}"})
    out.append({"cmd": f"pay {'card' if s.pay_method=='cash' else 'cash'}",
                "note": "switch payment"})

    # places she's told you about (where she was born / grew up) linger as destinations
    for rid in s.flags.get("revealed", []):
        rp = world.get_poi(rid)
        if rp and rp.poi_id != p.poi_id:
            d = world.haversine_mi(p.lat, p.lon, rp.lat, rp.lon) * 1.22
            out.append({"cmd": f"drive to {rid}", "note": f"{rp.name} · ~{d:.0f} mi"})

    # a few destinations: nearest gas (survival) + nearest goals
    seen = {p.poi_id}
    dests = []
    gas = world.nearest_with_service(p, "gas", limit=3)
    for dist, g in gas:
        if g.poi_id not in seen:
            dests.append((dist, g)); seen.add(g.poi_id); break
    goals = sorted(
        ((world.haversine_mi(p.lat, p.lon, q.lat, q.lon), q)
         for q in world.all_pois() if q.kind in ADVENTURE_KINDS and q.poi_id not in seen),
        key=lambda t: t[0])
    for dist, q in goals[:3]:
        dests.append((dist, q)); seen.add(q.poi_id)
    dests.sort(key=lambda t: t[0])
    for dist, d in dests[:4]:
        road = dist * 1.22
        reach = "" if road <= s.range_mi else "  ⛽ beyond range"
        out.append({"cmd": f"drive to {d.poi_id}",
                    "note": f"{d.name} · ~{road:.0f} mi{reach}"})
    return out


# --------------------------------------------------------------------- turn
def _result(s, events, scene, *, voice=None, npc=None, info=None, welcome=None):
    return {
        "ok": True, "events": events, "scene": scene, "voice": voice, "npc": npc,
        "info": info, "welcome": welcome, "snapshot": snapshot(s), "choices": choices(s),
        "status": s.status, "ending": s.ending, "sid": s.flags.get("sid", ""),
    }


def opening_result(s: GameState) -> dict:
    return {
        "ok": True, "events": [], "intro": _INTRO, "scene": OPENING,
        "voice": None, "npc": None, "info": None,
        "snapshot": snapshot(s), "choices": choices(s),
        "status": s.status, "ending": s.ending, "sid": s.flags.get("sid", ""),
    }


def _narrate(s, events, player_text, drama=None):
    nar = get_narrator()
    extra = None
    if drama:
        extra = {"cue": drama["cue"], "stub": drama.get("stub", [])}
    out = nar.narrate(_PERSONA, snapshot(s), events, player_text, s.flags.get("sid", "x"), extra=extra)
    return out.get("text", ""), out.get("voice"), out.get("audio_url")


def _encounter(s, force=False):
    """If standing in an encounter spot, bring the NPC to voice."""
    p = s.place
    if not p.language:
        return None
    nar = get_narrator()
    npc = nar.npc_speak(p.language, p.voice or "", p.npc or "a local",
                        p.blurb or f"at {p.name}", s.flags.get("sid", "x"))
    vinfo = voices().get(p.language, {})
    npc["label"] = vinfo.get("label", p.language)
    npc["who"] = p.npc or "a local"
    return npc


def _after_arrival(s: GameState, events: list):
    """Everything that can happen the moment the wheels stop somewhere new — a roadblock, an NPC,
    the owner, a set-piece reveal, a random beat, the Instagram exposure roll — plus the clean-
    arrival checkpoint. Shared by a normal drive and a self-driven (autopilot) leg. Mutates
    `events`; returns (npc, drama_ev, story_beat)."""
    npc = drama_ev = story_beat = None
    if encounters.stop_active(s):            # law_check opened a roadblock stop mid-drive
        return None, encounters.WHISPER_MOMENT, None
    npc = _encounter(s)
    if npc:
        events.append(f"ENCOUNTER: {npc['who']} greets you in {npc['label']}, "
                      "not switching to English.")
    # he said he'd wait at the Oakland garage to make the deal — and he's there, ahead of the
    # homecoming tour and the dice
    if (s.place.poi_id == "oakland_aisha" and s.flags.get("owner_met")
            and not s.flags.get("bought")):
        events += encounters.start_owner(s)
        events.append(f"OWNER: he's leaning on the roll-up, waiting. 'You came back. "
                      f"${encounters.owner_price(s):.0f} and she's yours — or talk, "
                      f"if you'd rather. Your call.'")
        drama_ev = OWNER_ARRIVAL_MOMENT
    else:
        story_beat = _story_on_arrival(s)        # a set-piece reveal takes the moment
        if not story_beat and not s.place.poi_id:
            fact = world.wiki_fact(s.place.lat, s.place.lon)   # ANY town brings something up
            if fact:
                events.append(f"FACT: {fact}")
        if not story_beat:
            if _owner_should_appear(s):          # the man who built her finds you first
                events += encounters.start_owner(s)
                drama_ev = OWNER_ARRIVAL_MOMENT
            else:
                drama_ev = drama.maybe_event(s)  # else: nothing ever goes to plan
                if drama_ev:
                    events += drama_ev["lines"]
                if encounters.stop_active(s) and drama_ev is None:
                    drama_ev = encounters.WHISPER_MOMENT
                # arriving somewhere bright: telegraph exposure + maybe get posted
                if drama_ev is None and not encounters.stop_active(s):
                    from engine import heat as _heat
                    soc = _heat.social_arrival(s)
                    if soc:
                        events += soc["events"]
                        drama_ev = soc["moment"]
    encounters.check_owner_deadline(s, events)
    # a clean arrival is a checkpoint — unless something's still standing at the window
    if (s.place.poi_id and s.status == "playing"
            and not encounters.stop_active(s) and not encounters.owner_active(s)):
        checkpoint(s, f"arrived {s.place.name}")
    return npc, drama_ev, story_beat


def _example_dest(s: GameState) -> str:
    """A nearby place name to seed the 'let her drive to ___' hint."""
    p = s.place
    near = sorted(((world.haversine_mi(p.lat, p.lon, q.lat, q.lon), q)
                   for q in world.all_pois() if q.poi_id and q.poi_id != p.poi_id),
                  key=lambda t: t[0])
    return near[0][1].poi_id if near else "zion"


def handle(s: GameState, raw: str) -> dict:
    verb, args = parse(raw)

    # ---- pure console verbs, available everywhere ----
    if verb == "help":
        return _result(s, [], "", info=_help_text())
    if verb == "save":
        _autosave(s)
        return _result(s, [], "", info="Saved.")
    if verb == "branches":            # the git-like timeline selector
        return _result(s, [], "", info=branches_text(s))
    if verb == "rewind":              # the Edge-of-Tomorrow escape — works from any ending
        events, moment = rewind(s, args.get("target"))
        if moment is None:
            return _result(s, events, "")
        scene, voice, audio = _narrate(s, events, "", drama=moment)
        return _result(s, events, scene, voice=audio)
    if verb == "load" or verb == "new":
        return _result(s, [], "", info="(handled by the server)")

    # ---- an open traffic stop / the owner / a gas-station standoff owns the conversation ----
    # This must come before every other verb: anything you say mid-encounter is SPEECH.
    # "…full tank of fresh 91 sitting in her right now…" has to reach the officer,
    # not the range calculator.
    if ((encounters.stop_active(s) or encounters.owner_active(s) or encounters.standoff_active(s))
            and s.status == "playing"):
        s.turn += 1
        in_stop = encounters.stop_active(s)
        in_standoff = encounters.standoff_active(s)

        if in_standoff:               # the clerk with the gun — its own ruleset (talk/disarm/draw)
            if verb in ("drive", "home", "fuel", "sleep", "tow"):
                events = ["STANDOFF: not with a pistol pointed at you. Talk him down, or take it."]
                _autosave(s)
                scene, voice, audio = _narrate(s, events, "", drama={
                    "cue": "the driver tried to leave while the clerk held a gun on them; she "
                           "snaps them back — you don't move with a barrel on you",
                    "stub": ["You don't MOVE, ace — talk or grab, those are the doors.",
                             "Hands flat. We leave when the gun's down or it's ours, not before."]})
                return _result(s, events, scene, voice=audio)
            out = encounters.standoff_turn(s, verb, raw)
            if out.get("moment", {}).get("unlock"):
                checkpoint(s, "walked out armed — Desperado")  # the special checkpoint
            elif out["done"] and s.status == "playing":
                checkpoint(s, "survived the standoff")
            _autosave(s)
            scene, voice, audio = _narrate(s, out["events"], "", drama=out["moment"])
            return _result(s, out["events"], scene, voice=audio)

        if verb == "draw" and s.flags.get("gun"):     # Desperado's nuclear option
            out = encounters.draw_in_stop(s, in_owner=encounters.owner_active(s))
            _autosave(s)
            scene, voice, audio = _narrate(s, out["events"], "", drama=out["moment"])
            return _result(s, out["events"], scene, voice=audio)
        if verb == "buy" and encounters.owner_active(s):   # come to terms — the good ending
            out = encounters.owner_buy(s, args.get("amount"))
            good = out.get("moment", {}).get("good_ending")
            if good:
                checkpoint(s, "bought her — she's yours")
            _autosave(s)
            scene, voice, audio = _narrate(s, out["events"], "", drama=out["moment"])
            welcome = ("愛車 — SHE'S YOURS\nLegally, on paper, free and clear. The running is over."
                       if good else None)
            return _result(s, out["events"], scene, voice=audio, welcome=welcome)
        # A long sentence is a PITCH, even if it happens to contain a movement word
        # ("I'll drive her home and put the parts back" must reach him, not parse as 'home').
        # Only a TERSE command (≤4 words) that parses to an action verb is treated as one.
        _action_verbs = ("drive", "home", "fuel", "sleep", "tow", "disarm", "draw",
                         "atm", "sell", "claim", "explore", "race", "show", "parts")
        if verb in _action_verbs and len(raw.split()) <= 4:
            events = ["LAW: not while the flashlight's on you. Talk first." if in_stop
                      else "OWNER: he's standing right there. Talk — or make an offer ('buy')."]
            _autosave(s)
            scene, voice, audio = _narrate(s, events, "", drama={
                "cue": "the driver tried to do anything except talk while "
                       + ("an officer" if in_stop else "the man who built her")
                       + " stood at the window — she stops them cold: words first",
                "stub": ["Words first, ace. WORDS first.",
                         "No. Mouth, then pedals. That's the whole play here."]})
            return _result(s, events, scene, voice=audio)
        if verb == "look":            # taking stock doesn't burn a round
            _autosave(s)
            scene, voice, audio = _narrate(s, [], "(takes stock)", drama={
                "cue": "the driver glances over the dash mid-encounter — she answers in a "
                       "near-soundless whisper, staying furniture",
                "stub": ["(whisper) Numbers are on the dash. Eyes front.",
                         "(barely audible) It's all there. Don't look at me — look at him."]})
            return _result(s, [], scene, voice=audio, info=_look_text(s))
        out = (encounters.stop_turn if in_stop else encounters.owner_turn)(s, raw)
        events = out["events"]
        if out["done"] and s.status == "playing":
            checkpoint(s, "talked your way clear")  # survived it
        _autosave(s)
        scene, voice, audio = _narrate(s, events, "", drama=out["moment"])
        return _result(s, events, scene, voice=audio)

    # ---- meta verbs (no LLM) ----
    if verb == "map":
        return _result(s, [], "", info=_map_text(s, args.get("service")))
    if verb == "range":
        return _result(s, [], "", info=_range_text(s))
    if verb == "heatreport":
        from engine import heat as _heat
        return _result(s, [], "", info=_heat.dashboard(s))
    if verb == "closures":           # the mountain-pass / season report
        return _result(s, [], "", info=season.closures_text(s))
    if verb == "scorecard":          # the running tally / how it ended
        return _result(s, [], "", info=endings.scorecard(s))
    if verb == "bondreport":         # how does she feel about you (her words, not a stat bar)
        return _result(s, [], "", info=bond.dashboard(s))
    if verb == "untag":
        from engine import heat as _heat
        events = _heat.untag(s)
        _autosave(s)
        scene, voice, audio = _narrate(s, events, "")
        return _result(s, events, scene, voice=audio)
    if verb == "pay":
        s.pay_method = args["method"]
        line = ("Cash from here on — no trail, no marks. Watch the wad, though; it runs out."
                if s.pay_method == "cash"
                else "Card it is. Fast and easy, and every swipe's a mark on the record. Your call.")
        return _result(s, [], line, info=f"Paying with {s.pay_method} now.")
    if verb == "origin":
        if prologue.active(s):
            prologue.note_turn(s)     # her story counts as a turn of conversation
        beat = _origin_beat(s, args["which"])
        _autosave(s)
        return _result(s, [], beat)

    # ---- the favor — the prologue owns every turn until you say yes ----
    if prologue.active(s):
        s.turn += 1
        out = prologue.turn(s, verb, raw)
        events = list(out["events"])
        if out["agreed"]:
            s.flags.pop("prologue", None)
            s.flags["prologue_done"] = True
            events += rules.drive(s, world.get_poi("sema_chevron"))   # down the block
            checkpoint(s, "the favor — down the block")
            _autosave(s)
            scene, voice, audio = _narrate(s, events, "", drama=out["moment"])
            return _result(s, events, scene, voice=audio, welcome=TITLE_DROP)
        _autosave(s)
        scene, voice, audio = _narrate(s, events, raw, drama=out["moment"])
        return _result(s, events, scene, voice=audio)

    if s.status != "playing" and verb not in ("tow", "look"):
        if s.status == "won":
            return _result(s, [], "That's the ride, ace. 'scorecard' to see the tally again, "
                           "'new' to do it all differently — or 'rewind' if you want the ending back.")
        hint = "'rewind' to take it back, or 'new' to start again."
        return _result(s, [], f"The trip's over. 'tow' if you can afford it, {hint}"
                       if s.status == "stranded" else f"The trip's over. {hint}")

    # ---- action verbs ----
    s.turn += 1                       # a true per-action counter (used for resume + rng)
    events, player_text, npc, drama_ev, story_beat, info = [], raw, None, None, None, None

    # the curious gas-station clerk is mid-beat — your next ACTION resolves him: leave or play it
    # humble and slide by; show off or linger and he posts the car
    if s.flags.get("clerk_curious"):
        from engine import heat as _heat
        low = raw.lower()
        showoff = any(t in low for t in ("sema", "yeah", "yes", "sure", "famous", "take a", "selfie",
                                         "follow", " pic", "build", "show car", "250", "mikuni",
                                         "go ahead", "post it", "tag"))
        if verb in ("drive", "home"):
            events += _heat.clerk_resolve(s, humble=True)        # you left — slid by
        elif verb == "say":
            events += _heat.clerk_resolve(s, humble=not showoff)
        elif verb == "camo":
            events += _heat.clerk_resolve(s, humble=True)        # you dressed her down — slid by
        elif verb not in ("look", "heatreport", "map", "range", "untag", "lielow",
                          "uncamo", "stereo", "text", "scorecard", "closures"):
            events += _heat.clerk_resolve(s, humble=False)       # lingered at the pump — he got it

    if verb == "home":                # "drive her home" — her home is the Oakland garage by default
        if args.get("dest"):
            h = world.geocode(args["dest"])
            s.flags["home"] = h.poi_id or args["dest"] if h else "oakland_aisha"
        home = s.flags.get("home") or "oakland_aisha"
        s.flags["home"] = home
        s.flags["going_home"] = True
        verb, args = "drive", {"dest": home}

    if verb == "drive":
        dest = world.geocode(args["dest"])
        if dest is None:
            events = [f"NAV: I don't have '{args['dest']}' on my maps. Nevada, California, "
                      "Arizona, Utah only — try the town name the way the sign reads."]
            _autosave(s)
            scene, voice, audio = _narrate(s, events, raw)
            return _result(s, events, scene, voice=audio)
        before_odo = s.odometer_mi
        events = rules.drive(s, dest, push=args.get("push", False))
        if s.status == "playing" and s.odometer_mi > before_odo:
            npc, drama_ev, story_beat = _after_arrival(s, events)
        player_text = ""
    elif verb == "autodrive":            # the self-driving secret — she takes the wheel
        if not gadgets.can_autodrive(s):
            events = gadgets.autodrive_refusal(s)
        elif not args.get("dest"):
            events = [f"WHEEL: 'Where to, ace? I'll drive — you rest. (e.g. 'let her drive to "
                      f"{_example_dest(s)}'.)'"]
        else:
            dest = world.geocode(args["dest"])
            if dest is None:
                events = [f"NAV: '{args['dest']}' isn't on my maps — NV/CA/AZ/UT only."]
            else:
                before_odo = s.odometer_mi
                events = rules.drive(s, dest, selfdrive=True)
                if s.status == "playing" and s.odometer_mi > before_odo:
                    npc, drama_ev, story_beat = _after_arrival(s, events)
        player_text = ""
    elif verb == "fuel":
        events = rules.fuel(s, dollars=args.get("dollars"), liters=args.get("liters"),
                            gallons=args.get("gallons"), fill=args.get("fill", False),
                            prefer=args.get("prefer"))
        # the favor completes the first time you actually FILL her at the Chevron
        if (s.flags.get("prologue_done") and not s.flags.get("favor_filled")
                and s.place.poi_id == "sema_chevron" and s.fuel_l >= s.tank_l - 0.5):
            s.flags["favor_filled"] = True
            events.append("FAVOR: the tank is full. The favor is done — she's ready to load out "
                          "for home tomorrow. ...She goes quiet a second.")
            drama_ev = prologue.favor_done_moment()
            checkpoint(s, "tank full — the favor's done")
        elif s.status == "playing" and s.fuel_l >= s.tank_l - 0.5 and any(
                e.startswith("FUEL: pumped") for e in events):
            checkpoint(s, "topped off")  # a full tank is a clean save point (and sets up the standoff)
        # a curious clerk may clock the show car at a bright, busy pump
        if (s.status == "playing" and any(e.startswith("FUEL: pumped") for e in events)
                and not s.flags.get("clerk_curious")):
            from engine import heat as _heat
            clerk = _heat.social_fuel(s)
            if clerk:
                events += clerk["events"]
                drama_ev = clerk["moment"]
        player_text = ""
    elif verb == "sleep":
        events = rules.sleep(s, kind=args.get("kind"), prefer=args.get("prefer"),
                             rough=args.get("rough", False))
        if s.status == "playing":
            checkpoint(s, "a night's rest")  # a survived night is a checkpoint
        player_text = ""
    elif verb == "tow":
        events = rules.tow(s, prefer=args.get("prefer"))
        if s.status == "playing":
            story_beat = _story_on_arrival(s)    # a flatbed arrival still counts as arriving
            checkpoint(s, "towed off the shoulder")  # rescued
        player_text = ""
    elif verb == "talk":
        npc = _encounter(s, force=True)
        if npc is None:
            events = ["TALK: nobody here to talk to but me."]
        else:
            events = [f"ENCOUNTER: {npc['who']} greets you in {npc['label']}, "
                      "not switching to English."]
        player_text = raw
    elif verb == "look":
        player_text = "(takes stock)"
        info = _look_text(s)                    # the promised ledger: place + numbers
    elif verb == "claim":
        events = garage.claim_cash(s, args.get("amount") or 0.0)
        player_text = ""
    elif verb == "atm":
        events = garage.atm(s, args.get("amount"))
        player_text = ""
    elif verb == "explore":
        events = garage.explore(s)
        player_text = ""
    elif verb == "parts":
        info = garage.parts_text(s)
        player_text = "(eyes the build)"
    elif verb == "sell":
        pid = garage.part_id(args.get("what", ""))
        events = garage.sell_part(s, pid) if pid else [
            "SELL: which part? 'parts' lists what's on her — the carbon hood, the Mikunis, the wheels."]
        player_text = ""
    elif verb == "lielow":
        from engine import heat as _heat
        events = _heat.lie_low(s)
        player_text = ""
    elif verb == "bet":
        out = garage.gamble(s, args.get("amount"), args.get("pick"))
        events = out["events"]
        if out.get("won"):                            # bank the win so a later loss can't rewind past it
            checkpoint(s, f"won at the tables — ${s.cash:,.0f}")
        drama_ev = out.get("moment")
        player_text = ""
    elif verb == "rob":
        out = encounters.rob_bank(s)
        events = out["events"]
        if s.status == "playing" and s.flags.get("robbed_banks"):
            checkpoint(s, f"robbed a bank — ${s.cash:,.0f}")
        drama_ev = out.get("moment")
        player_text = ""
    elif verb == "flirt":
        from engine import dating
        out = dating.flirt(s)
        events = out["events"]
        drama_ev = out.get("moment")
        player_text = ""
    elif verb == "killengine":
        from engine import dating
        events = dating.kill_engine(s)
        player_text = ""
    elif verb == "compliment":
        from engine import dating
        events = dating.compliment(s)
        player_text = "(sweet-talks her)"
    elif verb == "bringhome":                    # take the date back to where she's parked — betrayal
        from engine import dating
        out = dating.bring_them_home(s)
        events = out["events"]
        drama_ev = out.get("moment")
        player_text = ""
    elif verb == "race":
        events = garage.race(s)
        player_text = ""
    elif verb == "show":
        events = garage.show(s)
        player_text = ""
    elif verb == "buy":                          # not in front of the owner
        if s.flags.get("bought"):
            events = ["BUY: she's already yours. The pink slip's in the glovebox."]
        elif s.flags.get("owner_met"):
            events = [f"BUY: he's not here. He said he'd be at the AiSha garage in Oakland — "
                      f"'drive me home' and bring ${s.flags.get('owner_price', encounters.owner_price(s)):.0f}."]
        else:
            events = ["BUY: there's no one to buy her from yet. The man who built her finds you "
                      "when the trail runs hot enough — keep moving through the cities."]
        player_text = ""
    elif verb in ("disarm", "draw"):            # the gun, with nothing to point it at
        events = ["GUN: nobody's holding a gun on you right now." if verb == "disarm"
                  else ("GUN: you keep the piece down — no call for it here." if s.flags.get("gun")
                        else "GUN: you don't have a gun. Not yet.")]
        player_text = ""
    # ---- the endgame: the ways OUT (each rolls a scorecard) ----
    elif verb == "cross":                        # flee south across the border
        out = endings.cross_border(s); events = out["events"]
        drama_ev = out.get("moment"); player_text = ""
    elif verb == "ship":                         # a shipping container, a forged life
        out = endings.ship_out(s); events = out["events"]
        drama_ev = out.get("moment"); player_text = ""
    elif verb == "pardon":                       # bribe your way clean — the farce
        out = endings.buy_pardon(s); events = out["events"]
        drama_ev = out.get("moment"); player_text = ""
    elif verb == "retire":                       # roll the credits from a good place
        out = endings.retire(s); events = out["events"]
        drama_ev = out.get("moment"); player_text = ""
    # ---- her gadgets ----
    elif verb == "camo":
        events = gadgets.camo(s); player_text = ""
    elif verb == "uncamo":
        events = gadgets.uncamo(s); player_text = ""
    elif verb == "flash":
        events = gadgets.flash_lights(s); player_text = ""
    elif verb == "stereo":
        events = gadgets.play_stereo(s, args.get("what")); player_text = ""
    elif verb == "text":
        events = gadgets.text_someone(s, args.get("who")); player_text = ""
    elif verb == "upgrade":                      # the secret: wake her up to drive herself
        out = gadgets.upgrade_selfdrive(s); events = out["events"]
        drama_ev = out.get("moment")
        if s.flags.get("self_driving"):
            checkpoint(s, "she drives herself now")
        player_text = ""
    else:  # say — conversation, or leaning on the clerk at a manned pump
        if (s.place.has("gas") and not encounters.standoff_active(s)
                and encounters.gas_aggression(raw) >= 2):
            events = encounters.start_standoff(s)
            drama_ev = encounters.STANDOFF_WHISPER
            player_text = ""
        else:
            player_text = args.get("text", raw)
            payoff = _promise_payoff(s, raw)    # promised follow-ups, kept (quiet places only)
            if payoff:
                story_beat = payoff

    _autosave(s)
    welcome = _state_welcome(s) if s.status == "playing" else None  # no 'welcome' as you leave for good
    if story_beat:
        scene, audio = story_beat, None         # the authored reveal, verbatim
    else:
        scene, voice, audio = _narrate(s, events, player_text, drama=drama_ev)
    return _result(s, events, scene, voice=audio, npc=npc, welcome=welcome, info=info)


QUIET_KINDS = ("park", "encounter", "spot")


def _quiet_place(s: GameState) -> bool:
    """'Somewhere quiet' — where the promises get kept. No cameras, no lanyards."""
    p = s.place
    return p.kind in QUIET_KINDS and not p.heat_zone


# She made two promises out loud. Both are now keepable. Drafts — Ben fills the details.
NAME_DROP = (
    "…You picked a good place to ask it again. No cameras for miles, engine ticking, nobody "
    "but us and the dark. All right. Mayumi. That's her name — first time I've said it out "
    "loud since the show floor. That's all you get out here: a name. The rest of it lives in "
    "Long Beach, and I'm not opening it under this much sky."
)
NAME_DROP_NUDGE = (
    "You have her name. The rest is in Long Beach — drive me there when you're ready to "
    "carry it."
)
MORNING_BEAT = (
    "That morning. August, Car Week, 17-Mile Drive at dawn — fog on the water, cypress like "
    "ink, and me polished so hard I reflected the sunrise twice. He brought me there to be "
    "seen, you understand. The way he could never bring her, after the 580. I rolled past "
    "Pebble with strangers' hands on my wheel and a thousand cameras going off, and all I "
    "could think was: she should be here, and I'm the proof she isn't. That was the morning "
    "I understood what I am. The understudy gets the lights either way. …There. Told you "
    "when we were far enough from people. You're the only one who ever followed up."
)


def _origin_beat(s: GameState, which: str) -> str:
    """The origin questions, situation-aware. born/grew also reveal their POIs as destinations."""
    beat, poi_id = LORE[which]
    if which == "owner":
        if prologue.active(s):
            return ("There was someone, before. And no — twenty minutes after meeting you at "
                    "a car show is not when I hand that out. Ask me on the road, if there "
                    "ever is one. Somewhere quiet, maybe, I'll tell you her name.")
        if not s.flags.get("knows_mayumi"):
            if s.flags.get("knows_name"):
                return NAME_DROP_NUDGE
            if _quiet_place(s):
                s.flags["knows_name"] = True
                return NAME_DROP
    if poi_id:
        revealed = s.flags.setdefault("revealed", [])
        if poi_id not in revealed:
            revealed.append(poi_id)
    return beat


_MORNING_TOKENS = ("that morning", "car week", "17-mile", "17 mile", "pebble", "monterey morning",
                   "tell me about the morning", "about monterey")


def _promise_payoff(s: GameState, raw: str):
    """Free-text follow-ups on her promises, honored at quiet places, told once."""
    low = (raw or "").lower()
    if (s.flags.get("seen_monterey") and not s.flags.get("knows_morning")
            and _quiet_place(s) and any(t in low for t in _MORNING_TOKENS)):
        s.flags["knows_morning"] = True
        return MORNING_BEAT
    return None


def _look_text(s: GameState) -> str:
    """'look' keeps its promise: the place, then the whole ledger."""
    p = s.place
    dt = s.clock
    svc = ", ".join(p.services) if p.services else "no services"
    lines = [f"{p.name}" + (f"  [{p.region}]" if p.region else "")]
    if p.blurb:
        lines.append(f"  {p.blurb}")
    lines += [
        f"  {svc} · {p.kind}",
        f"  FUEL  {s.fuel_l:.1f}/{s.tank_l:.0f} L  (~{s.range_mi:.0f} mi)",
        f"  CASH  ${s.cash:.2f} · ${s.credit_available:.0f} card ({s.pay_method})",
        (f"  HEAT  yours — free and clear · RIZ ♠ {s.riz:.0f}" if s.flags.get("no_heat")
         else f"  HEAT  {s.heat:.0f} ({_heat_label(s.heat, bool(s.flags.get('desperado')))}) · "
              f"RIZ ♠ {s.riz:.0f}"),
        f"  HER   {bond.label(s.bond)}" + ("   ⚠ anti-theft armed" if bond.armed(s) else ""),
        f"  {dt.strftime('%a %b %-d, %-I:%M %p')} · day {s.day} · {s.odometer_mi:.0f} mi · "
        f"awake {rules.hours_awake(s):.0f}h",
    ]
    if s.flags.get("bought"):
        lines.append("  OWNED · pink slip in the glovebox · race tracks, show lawns, all legal")
    elif garage.sold(s):
        lines.append(f"  stripped: {', '.join(garage.PARTS[p]['stock'] for p in garage.sold(s))}")
    return "\n".join(lines)


def _owner_should_appear(s: GameState) -> bool:
    """He works the card trail. Enough days + enough swipes (or the Mayumi reveal), and the
    next curated town with people in it is where he's waiting."""
    return (not s.flags.get("owner_met")
            and s.status == "playing"
            and s.day >= OWNER_MIN_DAY
            and (s.flags.get("card_swipes", 0) >= OWNER_MIN_SWIPES or s.flags.get("knows_mayumi"))
            and s.place.kind in ("city", "gas")
            and bool(s.place.poi_id))


# --------------------------------------------------------------------- info text
def _help_text() -> str:
    return (
        "WHAT YOU CAN DO\n"
        "  drive to <place>      e.g. 'drive to zion', 'go to san francisco japantown',\n"
        "                        or any street address in NV/CA/AZ/UT. Add 'fast' to push it.\n"
        "  fill / gas $20 / gas 10 gal / gas 30 L     buy fuel (40 L tank, ~20 mpg)\n"
        "  pay cash | pay card   cash leaves no trail; the card does\n"
        "  i have $300 cash | withdraw $2000 | explore   your wallet, an ATM (<$10k), the glovebox\n"
        "  parts / sell the carbon hood   strip the build off her for cash (a stock part goes on)\n"
        "  buy her               come to terms with the owner ($80k — she's insured for $100k); then race/show\n"
        "  bet $1000 on <team>   gamble at the Vegas/Reno tables to raise it (rewind a loss, re-roll)\n"
        "  rob the bank          (armed only) a heist — big take, big heat\n"
        "  flirt / compliment her   pick up a date anywhere there's a crowd — but she's watching\n"
        "  how does she feel     read her mood — go cold (bring a date HOME, sell her parts) and she\n"
        "                        arms an anti-theft: sleep near open wifi and she phones home on you\n"
        "  camo / uncamo         dress her down to lie low, or flaunt the show car\n"
        "  flash the lights · play music · text   her tricks (text needs WiFi; music cools her off)\n"
        "  upgrade her           the secret, once she's yours and home — then 'let her drive to <place>'\n"
        "  passes                what mountain roads the snow has closed (the calendar matters)\n"
        "  cross the border · ship out · buy a pardon · retire   the ways the road ends — WELL\n"
        "  scorecard             your running tally + awards\n"
        "  sleep / motel / airbnb / camp   rest for the night (airbnb = cash, off the record)\n"
        "  talk                  speak with the locals where the language isn't English\n"
        "  map / nearby gas      see what's around\n"
        "  where can we get to on one tank?           the range question, with real math\n"
        "  look | heat report    fuel/money/time · the credit-karma heat dashboard\n"
        "  rewind | branches | branch N   fold the timeline back; list checkpoints; jump to one\n"
        "  tow                   the only way off the shoulder — and a fast way to get caught\n"
        "  save / new            \n"
        "Just typing to her also works. She has opinions. If the law pulls you over, your\n"
        "mouth is the whole game: stay calm, sell the story, know the build."
    )


def _range_text(s: GameState) -> str:
    """'Where can we get to on one tank?' — answered with real numbers. Shows the FAR EDGE of
    your reach (real destinations, not the casino next door), which is what the question means."""
    p = s.place
    now_mi = s.range_mi
    full_mi = (s.tank_l / LITERS_PER_GALLON) * s.mpg
    DEST_KINDS = ("city", "park", "track", "amusement", "gas")
    rows = sorted(((world.haversine_mi(p.lat, p.lon, q.lat, q.lon) * ROAD_WINDING_FACTOR, q)
                   for q in world.all_pois()
                   if q.poi_id != p.poi_id and q.kind in DEST_KINDS), key=lambda t: t[0])
    reach_now = [(d, q) for d, q in rows if d <= now_mi]
    reach_fill = [(d, q) for d, q in rows if now_mi < d <= full_mi]

    def fmt(d, q):
        svc = "".join(c[0] for c in ("gas", "lodging", "food") if c in q.services).upper()
        return f"  {d:>5.0f} mi  {q.name}  [{q.region}] {svc}"

    lines = [f"ON THIS TANK (~{now_mi:.0f} mi of road) — {len(reach_now)} places in reach; the far edge:"]
    if reach_now:
        for d, q in reversed(reach_now[-10:]):          # farthest-first: what 'how far' really asks
            lines.append(fmt(d, q))
    else:
        lines.append("  nowhere worth the name. Buy gas first.")
    if reach_fill:
        lines.append(f"WITH A FULL TANK (~{full_mi:.0f} mi) you'd also reach, out to:")
        for d, q in reversed(reach_fill[-8:]):
            lines.append(fmt(d, q))
    lines.append("  (mountain legs burn more — Zion, Tioga, Bryce eat the margin; G=gas L=lodging F=food)")
    return "\n".join(lines)


def _map_text(s: GameState, service: str | None) -> str:
    p = s.place
    if service:
        rows = world.nearest_with_service(p, service, limit=8)
        head = f"NEAREST {service.upper()} (road miles):"
        lines = [f"  {d * ROAD_WINDING_FACTOR:>5.0f} mi  {q.name}  [{q.region}]" for d, q in rows]
        return head + "\n" + "\n".join(lines)
    # general: nearest assorted POIs
    rows = sorted(((world.haversine_mi(p.lat, p.lon, q.lat, q.lon), q)
                   for q in world.all_pois() if q.poi_id != p.poi_id),
                  key=lambda t: t[0])[:12]
    lines = []
    for d, q in rows:
        road = d * 1.22
        flag = "" if road <= s.range_mi else "  ⛽"
        svc = "".join(c[0] for c in ("gas", "lodging", "food") if c in q.services).upper()
        lines.append(f"  {road:>5.0f} mi  {q.name}  [{q.region}] {svc}{flag}")
    return ("AROUND YOU (road miles; ⛽ = beyond current range):\n" + "\n".join(lines)
            + f"\n  range now: ~{s.range_mi:.0f} mi")
