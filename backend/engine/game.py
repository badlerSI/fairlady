"""Game orchestration: new game, state snapshots, suggested moves, and turn handling.
Ties the deterministic engine to the narrator. State authority stays in the engine."""
from __future__ import annotations
import json
import random

from config import (
    CONTENT_DIR, AWAKE_START_ISO, AWAKE_WARN_HOURS, AWAKE_FORCE_HOURS,
    LITERS_PER_GALLON, ROAD_WINDING_FACTOR, RIZ_REWIND_COST,
    OWNER_MIN_DAY, OWNER_MIN_SWIPES, BOB_PARENTS_HOME_DAY,
)
from engine.state import GameState
from engine import (world, rules, economy, save, drama, prologue, encounters, garage,
                    endings, gadgets, season, bond, heat, cameras, survival, inventory, luck, romance,
                    places, onboarding, rizzbreaker, alma, bobmode)
from engine.commands import parse, _bare_number, _money, spec_hits as _spec_hits
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
    "painted": (
        "My paint? A booth in Fresno — Kilimanjaro White, then the spade laid down by hand and the whole "
        "shell wrapped in PPF so it'd peel off clean someday. Ask me that again somewhere quiet and I'll "
        "tell you the part he doesn't think I know.",
        "fresno"),
    "registration": (
        "…You actually read the registration. Of course you did. It's not his name on it — it's his "
        "folks'. They bought me for him; the paperwork never moved. They're up in Carson City, and "
        "they're in Portugal till the end of the month — he mentioned it once like it didn't matter. "
        "Door's never locked. There's a brown loaner under a sheet in the garage they don't even drive. "
        "…Why do you ask, ace.",
        "carson_parents"),
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
    # Fresno: the paint booth — and the painter spills the owner's whole secret. The other way in
    # (besides asking her 'where were you painted' somewhere quiet). DRAFT — see OWNER_SECRET_SPEC.md.
    "fresno": {"flag": "owner_secret", "beat":
        "Fresno — the booth where I got my white and my hand-laid spade, wrapped in PPF so it'd peel "
        "off clean someday. The painter's an old friend of his, and he takes one look at the plate, "
        "goes quiet, and tells you the part the owner never would: he isn't hunting me to bring me "
        "home. He's waiting for me to be GONE. I'm insured for a hundred grand, and the day I vanish "
        "for good, that check frees him to rebuild the real one — Mayumi, 愛車, the ride-or-die that "
        "burned on the 580. I was always the understudy who'd pay for her revival. The painter says "
        "it like a kindness, and it is one: if we just never come back, we both win. South, or a "
        "fire — those are the two clean ways out, and now you know them both."},
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
    from engine import heat as _heat, luck as _luck
    base = s.heat
    s.heat = 0.0
    s.flags["car_heat"] = 0.0           # fresh game → both axes start clean
    s.flags["personal_heat"] = 0.0
    _luck.seed_if_unset(s)              # the hidden hand — a per-game luck baseline
    _heat.add(s, base, "she's a stolen SEMA show car — the baseline BOLO", "spike", axis="car")
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
                "bond_worst", "bond_echoes", "chase_learned", "peak_riz", "peak_bond",
                # the 18+ gate + who you told her you are survive a rewind (no folding past the gate)
                "age_blocked", "onboarded", "player_age", "player_birth_year", "player_name",
                "player_pronouns", "pronoun_stance", "refs_era",
                "events_seen", "beats_seen")   # the loop is HERS — she remembers (incl. what's happened)

# how much of your best survives a failure/rewind — you never face a wall again with LESS.
RIZ_FLOOR_FRAC = 0.6        # keep ≥60% of your peak Riz
BOND_FLOOR_DROP = 16.0      # keep your affection within this of its high-water mark


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
    from engine import luck as _luck
    _luck.reroll(s)              # the dice re-settle — a redo isn't the same weather (hidden luck)
    # the ratchet: some Riz and some affection SURVIVE the fold, so you never re-attempt with less.
    riz_floor = round(RIZ_FLOOR_FRAC * s.flags.get("peak_riz", s.riz), 1)
    if s.riz < riz_floor:
        s.riz = riz_floor
    # the affection floor lifts you toward your high-water mark — but it will NOT pull a COLD car back
    # out of COLD (that was free anti-theft laundering: rewind to un-arm her). If she's gone cold, the
    # fold-back doesn't launder it; you have to win her back the honest way.
    bond_floor = max(0.0, s.flags.get("peak_bond", round(s.bond)) - BOND_FLOOR_DROP)
    from engine import bond as _bondmod
    if s.bond < bond_floor and _bondmod.band(s.bond) != "COLD":
        s.bond = round(bond_floor, 1)

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
        "car_heat": 0 if s.flags.get("no_heat") else round(heat.car_heat(s)),
        "driver_heat": 0 if s.flags.get("no_heat") else round(heat.personal_heat(s)),
        "heat_label": ("yours — free and clear" if s.flags.get("no_heat")
                       else _heat_label(s.heat, bool(s.flags.get("desperado")))),
        "riz": round(s.riz),
        "bond": round(s.bond),
        "affection_gauge": round(min(1.0, max(0.0, s.bond / 100.0)), 3),   # fills/empties the 愛車 logo
        "bond_band": bond.band(s.bond),
        "bond_armed": bond.armed(s),
        "alma_aboard": bool(s.flags.get("alma_aboard")),   # the love triangle — Alma's riding along
        "married_alma": bool(s.flags.get("married_alma")),
        "pending_turnkey": bool(s.flags.get("pending_turnkey")),   # show the [Turn the key] button
        "gas_run": bool(s.flags.get("prologue_done") and not s.flags.get("favor_filled")),
        # the whole OPENING phase (prologue → turnkey → gas run) — suppress gas-nagging here
        "opening": bool(prologue.active(s) or s.flags.get("pending_turnkey")
                        or (s.flags.get("prologue_done") and not s.flags.get("favor_filled"))),
        "spec_sheet": list(_CAR.get("spec_sheet", [])),            # canonical build — the source of truth
        "desperado": bool(s.flags.get("desperado")) and not s.flags.get("no_heat"),
        "bought": bool(s.flags.get("bought")),
        "no_heat": bool(s.flags.get("no_heat")),
        # the endgame layer — so the frontend can dress her down, draw her self-driving,
        # pick a win/credits scene, and flag the closing passes
        "camo": gadgets.camo_active(s),
        "self_driving": bool(s.flags.get("self_driving")),
        "ending_key": s.flags.get("ending_key"),
        "sfx": s.flags.get("sfx"),                  # e.g. 'sad_trombone' / 'demon_voices'
        "alt_headlights": bool(s.flags.get("alt_headlights")),   # the possessed-car strobe cue
        # the RIZZBREAKER limit break — gauge + whether it's charged + what it'd do here
        "rizzbreaker_ready": rizzbreaker.ready(s),
        "rizzbreaker_gauge": rizzbreaker.gauge(s),
        "rizzbreaker_here": rizzbreaker.context(s),
        "snow_line": round(season.snow_line(s), 3),
        "car_value": garage.car_value(s), "show_score": garage.show_score(s),
        "encounter_open": (encounters.stop_active(s) or encounters.owner_active(s)
                           or encounters.standoff_active(s)),
        "odometer_mi": round(s.odometer_mi), "adventures": list(s.adventures),
        "status": s.status, "turn": s.turn,
        "gas_price": round(economy.gas_price(p), 2) if p.has("gas") else None,
        # the ALPR/camera layer — so the frontend can warn 'dense city' vs 'dark country'
        "camera_density": cameras.camera_density(p),
        "camera_word": cameras.DENSITY_WORD[cameras.camera_density(p)],
        "plate_swapped": bool(s.flags.get("plate_swapped")),
        # the CAR-disguise state — so the frontend can draw her covered / plain-hood / resprayed
        "covered": bool(s.flags.get("covered")),
        "hood_swapped": bool(s.flags.get("hood_swapped")),
        "resprayed": bool(s.flags.get("resprayed")),
        # the road-map cue: True the moment she asks 'where to?' — the frontend flashes the map icon
        "awaiting_destination": bool(s.flags.get("where_to")) and s.status == "playing",
        # who you told her you are — so she addresses you right and pitches references to your era
        "player_name": s.flags.get("player_name"),
        "player_pronouns": s.flags.get("player_pronouns"),
        "player_profile": onboarding.profile_cue(s),
        "onboarding": s.flags.get("onboard"),
        "age_blocked": bool(s.flags.get("age_blocked")),   # 18+ gate — frontend shows a gate screen
        # the hatch — usable cargo, reserve fuel, the spade hood / limp / stinger flags
        "cargo_used": inventory.volume_used(s), "cargo_cap": inventory.CAPACITY_CUFT,
        "reserve_fuel_l": round(inventory.jerry_fuel(s), 1),
        "has_stinger": inventory.has(s, "stinger"),
        "limp": bool(s.flags.get("limp")),
        "damage": garage.damage_state(s),                  # clean | cosmetic | serious
        "damage_pct": round(garage.body_damage(s)),
        # BOB MODE — the active car the frontend should render (brown Bob vs the white Z)
        "active_car": "bob" if s.flags.get("bob_mode") else "ace",
        "car_name": "BOB" if s.flags.get("bob_mode") else "FAIRLADY",
        "bob_mode": bool(s.flags.get("bob_mode")),
        "bob_owned": bool(s.flags.get("bob_owned")),
        "bob_call_pending": bool(s.flags.get("bob_call_pending")),
        "bob_days_left": (max(0, BOB_PARENTS_HOME_DAY - s.day)
                          if s.flags.get("bob_mode") and not s.flags.get("bob_call_pending") else None),
        # the body — survival meters for the dash (0–100; alertness feeds talk-out)
        "hunger": round(float(s.flags.get("need_hunger", 0.0))),
        "bladder": round(float(s.flags.get("need_bladder", 0.0))),
        "bowels": round(float(s.flags.get("need_bowels", 0.0))),
        "bac": round(float(s.flags.get("bac", 0.0)), 3),
        "alertness": survival.alertness(s),
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

    # you agreed — the one move that matters is turning the key (the big button)
    if s.flags.get("pending_turnkey"):
        return [{"cmd": "turn the key all the way", "note": "unplug the charger and roll", "big": True},
                {"cmd": "look", "note": "the lot, the ramp"}]

    # at the Chevron on the opening gas run — the pay-and-talk dilemma
    if (s.flags.get("prologue_done") and not s.flags.get("favor_filled")
            and s.place.poi_id == "sema_chevron"):
        out = [{"cmd": "pay cash", "note": "quiet — but you'll talk past the clerk inside"},
               {"cmd": "pay card", "note": "fast — and a trail with your face on it"}]
        out.append({"cmd": "fill", "note": "fill the tank"})
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
    # BOB MODE — the loaner-Z escape hatch
    if bobmode.active(s):
        out.append({"cmd": "call ace", "note": "check in — keep her warm (she's at the house)"})
        if bobmode.can_buy(s):
            out.append({"cmd": "buy bob", "note": "$7,000 — everything forgiven", "big": True})
        elif s.flags.get("bob_call_pending"):
            out.append({"cmd": "drive to carson_parents", "note": "bring Bob home to close it out"})
    elif bobmode.can_enter(s):
        out.append({"cmd": "park ace and take bob", "note": "leave the hot Z; borrow the brown one", "big": True})
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
        if endings.can_fake_death(s):
            out.append({"cmd": "fake your death", "note": "the fireball — burn the decoy, walk away dead"})
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


def _banter_riz(s, raw):
    """A genuinely CLEVER conversational line earns Riz — judged by the DM (online) or a conservative
    rubric (offline). Cooldowned + diminishing so you can't farm it; trolling earns nothing (the DM
    flags `messing`) but also can't break anything. Returns a feedback line, or None. Used both in
    free-roam talk AND on the move — the drive is the prime place to charm her, so it pays there too."""
    low = (raw or "").lower()
    if len(low.split()) < 4 or (s.turn - s.flags.get("banter_riz_turn", -99) < 3):
        return None
    from engine import judge
    v = judge.assess(s, "banter", raw, context="the driver is chatting with the car")
    if not (v.get("clever") and not v.get("messing")):
        return None
    n = s.flags.get("banter_count", 0)
    gain = round(3.0 * (0.7 ** n), 1)
    if gain < 0.2:
        return None
    s.riz = round(s.riz + gain, 1)
    s.flags["banter_count"] = n + 1
    s.flags["banter_riz_turn"] = s.turn
    s.flags["peak_riz"] = round(max(s.flags.get("peak_riz", 0.0), s.riz), 1)
    return f"RIZ: that landed — sharp, in-character, hers. Riz +{gain:.0f} → {s.riz:.0f}."


def _active_persona(s):
    """Whose voice the narrator speaks in. Driving Bob → Bob's plain, good-natured voice; otherwise
    Ace. (call_ace passes persona_override to reach Ace even while you're in Bob — she's on the phone.)"""
    from engine import bobmode
    if bobmode.active(s):
        return bobmode.persona()
    return _PERSONA


def _narrate(s, events, player_text, drama=None, persona_override=None):
    nar = get_narrator()
    extra = None
    if drama:
        extra = {"cue": drama["cue"], "stub": drama.get("stub", [])}
    persona = persona_override or _active_persona(s)
    # a drama beat can declare WHO speaks it — so Ace's phone call reaches you in her voice even while
    # you're driving Bob (drama={"persona":"ace"}); default follows the active car.
    if drama and drama.get("persona") == "ace":
        persona = _PERSONA
    out = nar.narrate(persona, snapshot(s), events, player_text, s.flags.get("sid", "x"), extra=extra)
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
    if encounters.chase_active(s):           # a pursuit opened mid-leg — it owns the moment
        return None, encounters.CHASE_WHISPER, None
    if encounters.stop_active(s):            # law_check opened a roadblock stop mid-drive
        return None, encounters.WHISPER_MOMENT, None
    from engine import cameras
    events += cameras.arrival_heat(s)        # the ALPR/Flock grid pings the plate in a city
    if s.place.poi_id == "area51_gate":      # something turns up in the hatch out here
        s.flags["area51_visited"] = True
        events += inventory.grant_stinger(s)
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
    # a real event you drove into (the F1 GP, the rodeo, the holiday lights) — once per game
    ev_beat = places.event_beat(s)
    if ev_beat:
        events.append(ev_beat)
    hint = alma.vegas_hint(s)                # the faint déjà-vu nudge, first night in Vegas
    if hint:
        events.append(hint)
    # she suggests a real place — food if you're hungry, a real motel if it's getting late
    if survival._get(s, "hunger") >= 55:
        fl = places.suggest_line(s, "food")
        if fl:
            events.append(fl)
    elif rules.hours_awake(s) >= 15 and s.place.has("lodging"):
        sl = places.suggest_line(s, "lodging")
        if sl:
            events.append(sl)
    encounters.check_owner_deadline(s, events)
    bob_moment = bobmode.check_bob_deadline(s, events)   # the family-home call / cold-betrayal / lapse
    if bob_moment and drama_ev is None:
        drama_ev = bob_moment
    season.check_calendar(s, events)         # the SLC-December set-piece + the NYE hard wall
    # a clean arrival is a checkpoint — unless something's still standing at the window
    if (s.place.poi_id and s.status == "playing"
            and not encounters.stop_active(s) and not encounters.owner_active(s)):
        checkpoint(s, f"arrived {s.place.name}")
        s.flags["where_to"] = True            # she'll ask 'where to?' — the frontend flashes the map
    return npc, drama_ev, story_beat


# the easter egg: try to drive BACK into the SEMA hall and a Freeman teardown guy runs you off
_SEMA_HALL_TERMS = ("sema", "north hall", "show floor", "the hall", "convention center", "lvcc",
                    "back inside", "the show", "show hall", "back to the floor")
FREEMAN_MOMENT = {
    "cue": "the driver tried to turn back INTO the convention center, and a Freeman teardown crew "
           "guy in a hi-vis vest steps in front of the car waving them off — the floor's closed, "
           "they're pulling carpet and rigging, no vehicles back in; he warns them, half-friendly "
           "half-threat, NOT to leave it parked on the premises overnight or it gets towed; she is "
           "dryly amused that the driver tried to go back IN",
    "stub": ["(she stifles a laugh) Where are you going, ace — back IN? That's a Freeman guy and he "
             "is not having it. 'Floor's closed, pal, we're tearing down — and don't leave that thing "
             "parked here overnight, it gets towed.' …He's right. Hang a U-turn.",
             "Back inside? Absolutely not — look at his face. 'Move it along, we're hauling rigging, "
             "and anything still on the lot at teardown gets HOOKED.' He means it. Turn around, "
             "Chevron's the other way."]}


def _freeman_beat(s: GameState) -> list:
    s.flags["freeman_warned"] = True
    return ["FREEMAN: a teardown guy in a Freeman hi-vis vest plants himself in front of the car and "
            "waves you off. 'Floor's closed — we're pulling carpet. And do NOT leave this parked on "
            "the premises overnight, it'll get towed at teardown.' He is not kidding about the tow."]


def _do_drive(s: GameState, dest, push: bool):
    """Resolve a full drive leg + everything that happens on arrival. Returns
    (events, npc, drama_ev, story_beat). Shared by a normal drive and a fast-forwarded transit."""
    s.flags.pop("where_to", None)
    before_odo = s.odometer_mi
    events = rules.drive(s, dest, push=push)
    npc = drama_ev = story_beat = None
    if s.status == "playing" and s.odometer_mi > before_odo:
        npc, drama_ev, story_beat = _after_arrival(s, events)
        warn = inventory.desert_warning(s, dest)
        if warn:
            events.append(warn)
    return events, npc, drama_ev, story_beat


# --------------------------------------------------------------------- the drive conversation
# Any leg longer than ~30 min IRL opens a conversation: she talks for as long as the drive should
# last, or until something happens (oh DEER), and you can 'put on music' to fast-forward to the end.
TRANSIT_MIN_HOURS = 0.5
_FAST_FORWARD = ("music", "put on music", "play music", "quiet", "be quiet", "hush", "silence",
                 "shut up and drive", "just drive", "just get there", "get there", "get us there",
                 "keep going", "keep driving", "drive on", "skip", "skip ahead", "fast forward",
                 "let's just go", "lets just go", "no talking", "i'm good", "im good", "stop talking",
                 "let's just drive", "lets just drive", "floor it", "step on it")
TRANSIT_OPENER = {
    "cue": "a long leg opens up ahead of them, an hour or more of dark road; she settles in and wants "
           "to TALK — this is the part of a road trip she's been waiting six days for, a real "
           "conversation with the one person who sees her — she invites them to talk about anything, "
           "or says she'll put on music and just drive if they'd rather rest",
    "stub": ["Okay — long stretch ahead, nothing but us and the high beams for an hour. …Talk to me, "
             "ace. About anything. Or say the word and I'll put on something and just drive while you "
             "rest your eyes. Your call.",
             "This is the good part. Empty road, full tank, you and me. Tell me something true — or "
             "'put on music' and I'll get us there quiet. I don't mind either way. I just like the company."]}
TRANSIT_WRAP = {
    "cue": "the long leg is wrapping up and she eases the conversation down, puts on something low, "
           "and brings them in the last few miles to the destination",
    "stub": ["…Anyway. That's us, more or less. Lights of the town coming up — let me put on something "
             "and bring us in.",
             "There's our exit. Good talk, ace. Music for the last few miles. We're here."]}


def _favor_reveal(s: GameState):
    """The tank's full and the clerk's been dealt with — she drops the act, the title drop lands.
    Sets favor_filled, flags the title drop, checkpoints, and returns the reveal moment. Returns
    None when it isn't time (tank not full, or a clerk still eyeing the car at the register)."""
    if (s.flags.get("prologue_done") and not s.flags.get("favor_filled")
            and s.place.poi_id == "sema_chevron" and s.fuel_l >= s.tank_l - 0.5
            and not s.flags.get("clerk_curious")):
        s.flags["favor_filled"] = True
        s.flags["_titledrop"] = True
        s.flags.pop("gas_target", None)        # tank's full — the whole West opens up now
        s.flags["where_to"] = True             # the road's open — she asks where to, map flashes
        onboarding.begin(s)                     # ...but first she wants to KNOW you (name/pronouns/age)
        checkpoint(s, "tank full — she drops the act")
        return prologue.favor_done_moment()
    return None


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

    # ---- the getting-to-know-you + the stick question own the conversation right after the title
    # drop. They must come BEFORE the command parser, because an answer like "I was born in '81" or
    # "they/them" would otherwise be read as a lore question or a stray command. A few status verbs
    # still pass through so you can glance at the map mid-introduction.
    _ONBOARD_PASSTHRU = ("look", "map", "range", "heatreport", "scorecard", "bondreport", "closures")
    _blank = not (raw or "").strip()                     # an empty answer is still an answer (→ default)
    if onboarding.pending(s) and (verb not in _ONBOARD_PASSTHRU or _blank):
        s.turn += 1
        out = onboarding.handle(s, raw)
        nxt = onboarding.pending(s)
        if out.get("arm_stick") and not nxt:
            romance.open_stick(s)
            info = "(" + romance.STICK_QUESTION_MOMENT["stub"][0] + ")"
        elif nxt:
            info = "(" + onboarding.QUESTION[nxt]["stub"][0] + ")"
        else:
            info = None
        _autosave(s)
        scene, voice, audio = _narrate(s, [], raw, drama=out.get("moment"))
        return _result(s, [], scene, voice=audio, info=info)
    if romance.ask_stick_pending(s) and (verb not in _ONBOARD_PASSTHRU or _blank):
        s.turn += 1
        out = romance.answer_stick(s, raw)
        _autosave(s)
        scene, voice, audio = _narrate(s, [], raw, drama=out["moment"])
        return _result(s, [], scene, voice=audio)

    # the 18+ gate — once she's clocked a minor, the road stays closed (only console verbs work)
    if s.flags.get("age_blocked") and verb not in ("look", "help", "new", "load"):
        return _result(s, [], "She won't turn the key. 'Eighteen and up, ace — this one gets people "
                       "shot. Come back when you're older. I'll wait.'",
                       info="(RIDE OR DIE is 18+. The road's closed until you're of age.)")

    # ---- an open traffic stop / the owner / a gas-station standoff owns the conversation ----
    # This must come before every other verb: anything you say mid-encounter is SPEECH.
    # "…full tank of fresh 91 sitting in her right now…" has to reach the officer,
    # not the range calculator.
    if ((encounters.stop_active(s) or encounters.owner_active(s) or encounters.standoff_active(s)
            or encounters.chase_active(s) or alma.club_active(s)) and s.status == "playing"):
        s.turn += 1
        in_stop = encounters.stop_active(s)
        in_standoff = encounters.standoff_active(s)

        if alma.club_active(s):              # the Alma woo owns the conversation — every line is a move
            if verb in ("drive", "home", "sleep", "tow"):   # walk out on her
                s.flags.pop("club", None)
                s.flags["alma_blew_it"] = True
                out = {"events": ["CLUB: you turn for the door before she's done talking, and when you "
                                  "glance back the booth is empty. Some doors only open once."],
                       "moment": None}
            else:
                out = alma.club_turn(s, raw)
            if out.get("done") and s.flags.get("alma_aboard"):
                checkpoint(s, "left the club with Alma")
            _autosave(s)
            scene, voice, audio = _narrate(s, out["events"], "", drama=out.get("moment"))
            return _result(s, out["events"], scene, voice=audio,
                           info="(win her over — wit and nerve, not lines; or walk away)")

        # the RIZZBREAKER, against the law — the possessed-car exorcism bit. Intercept even when
        # under-charged, so it gives the 'gauge isn't full' refusal instead of wasting a stop round.
        from engine import rizzbreaker
        if verb == "rizzbreaker" and (in_stop or encounters.chase_active(s)):
            out = rizzbreaker.invoke(s)
            if not (encounters.stop_active(s) or encounters.chase_active(s)):
                checkpoint(s, "rizzbroke the law")        # it cleared — bank the escape
            _autosave(s)
            scene, voice, audio = _narrate(s, out["events"], "", drama=out.get("moment"))
            return _result(s, out["events"], scene, voice=audio,
                           info=None if out.get("moment") else "(the gauge isn't full — talk your way "
                                "out the normal way, or 'draw' if you've got the gun)")

        if encounters.chase_active(s):       # a pursuit owns every word — tactics, not commands
            out = encounters.chase_turn(s, verb, raw)
            if out["done"] and s.status == "playing" and not encounters.stop_active(s):
                checkpoint(s, "shook the cops in the mountains")   # a clean escape banks
            _autosave(s)
            scene, voice, audio = _narrate(s, out["events"], "", drama=out.get("moment"))
            return _result(s, out["events"], scene, voice=audio,
                           info="(lights · side road · push · hide — or 'pull over' to take the stop)")

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
        # read-only/status verbs don't burn a round — glancing at the dash isn't an answer. But a long
        # SENTENCE that merely parses as one ("...filled her tank where she asked, officer...") is
        # SPEECH and must reach him, so only SHORT deliberate status commands are exempt (look always is).
        if (verb == "look"
                or (verb in ("heatreport", "range", "map", "scorecard", "bondreport", "closures")
                    and len(raw.split()) <= 4)):
            _autosave(s)
            _info = {"look": _look_text(s), "heatreport": heat.dashboard(s), "range": _range_text(s),
                     "map": _map_text(s, args.get("service")), "scorecard": endings.scorecard(s),
                     "bondreport": bond.dashboard(s),
                     "closures": season.closures_text(s)}.get(verb, _look_text(s))
            scene, voice, audio = _narrate(s, [], "(takes stock)", drama={
                "cue": "the driver glances over the dash mid-encounter — she answers in a "
                       "near-soundless whisper, staying furniture",
                "stub": ["(whisper) Numbers are on the dash. Eyes front.",
                         "(barely audible) It's all there. Don't look at me — look at him."]})
            return _result(s, [], scene, voice=audio, info=_info)
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
        else:
            bond.converse(s, about_her=True)   # asking about her past warms her (the fast farm)
        beat = _origin_beat(s, args["which"])
        _autosave(s)
        return _result(s, [], beat)

    # ---- the favor — the prologue owns every turn until you say yes ----
    if prologue.active(s):
        # the fast bad ending: walk off and leave her on the floor for the night → towed at teardown
        if verb == "sleep":
            s.turn += 1
            out = endings.towed_sema(s)
            _autosave(s)
            scene, voice, audio = _narrate(s, out["events"], "", drama=out["moment"])
            return _result(s, out["events"], scene, voice=audio)
        s.turn += 1
        out = prologue.turn(s, verb, raw)
        events = list(out["events"])
        if out["agreed"]:
            s.flags.pop("prologue", None)
            s.flags["pending_turnkey"] = True       # she's ready; now unplug the charger + turn the key
            _autosave(s)
            scene, voice, audio = _narrate(s, events, "", drama=out["moment"])
            return _result(s, events, scene, voice=audio)   # NO drive, NO title drop — yet
        _autosave(s)
        scene, voice, audio = _narrate(s, events, raw, drama=out["moment"])
        return _result(s, events, scene, voice=audio)

    # ---- the two-step commit: you agreed — now disconnect the trickle charger and turn the key ----
    if s.flags.get("pending_turnkey"):
        if verb == "turnkey":
            s.flags.pop("pending_turnkey", None)
            s.flags["prologue_done"] = True
            s.flags["charger_unplugged"] = True
            s.flags["gas_target"] = "sema_chevron"     # the ONLY easy destination until the tank's full
            s.flags["awaiting_cash_ask"] = True         # she asks how much cash you're carrying next turn
            s.turn += 1
            chevron = world.get_poi("sema_chevron")
            rt = world.route(s.place, chevron)          # OSRM if online, haversine fallback
            events = ["IGNITION: you reach past her left fender and pop the trickle charger off the "
                      "battery — the little red light dies. Then you turn the key all the way. She "
                      "catches on the second crank and drops into a lumpy, delighted idle."]
            events.append(f"NAV: '{rt['distance_mi']:.1f} miles — basically a straight shot. Out of "
                          "the lot, two blocks up Paradise, the Chevron's on the right. I'll call it.'")
            events += rules.drive(s, chevron)           # two blocks of neon
            checkpoint(s, "turned the key — rolled down to the Chevron")
            _autosave(s)
            scene, voice, audio = _narrate(s, events, "", drama=prologue.TURNKEY_MOMENT)
            return _result(s, events, scene, voice=audio,
                           info="(she asks: how much cash did you walk out with? say a number — or "
                                "'nothing' and she'll point you at the glovebox roll)")
        if verb in ("drive", "home", "fuel", "sleep", "tow"):
            s.turn += 1
            _autosave(s)
            scene, voice, audio = _narrate(s, [], "", drama={
                "cue": "the driver tried to do something before turning the key; she stops them — "
                       "pop the trickle charger, turn the key ALL the way, THEN we move",
                "stub": ["Charger off, key all the way, ace — THEN we roll. Not before.",
                         "Not yet. Unplug me and turn the key all the way over. Then we go."]})
            return _result(s, [], scene, voice=audio,
                           info="(she won't move until you 'turn the key all the way')")
        # chat / look fall through to normal handling — she'll talk while she waits

    # a NEW 'drive/home to <somewhere else>' mid-conversation = change of plans: drop the transit and
    # let the fresh destination route normally (don't silently fast-forward to the OLD one).
    if (s.flags.get("transit") and verb in ("drive", "home") and args.get("dest")
            and str(args.get("dest")).lower() != str(s.flags["transit"].get("dest", "")).lower()):
        s.flags.pop("transit", None)
    # the drive conversation: a long leg is underway. Talk (it keeps rolling), or do anything else /
    # 'put on music' to fast-forward to the destination. Console verbs (look/inventory) pass through.
    if (s.flags.get("transit") and s.status == "playing"
            and verb not in ("look", "inventory", "parts")):
        tr = s.flags["transit"]
        low = raw.lower()
        s.turn += 1
        # fast-forward only on a SHORT/explicit command, so 'keep going on that story' stays chat
        ff = (low.strip() in _FAST_FORWARD
              or (len(low.split()) <= 4 and any(w in low for w in _FAST_FORWARD)))
        is_chat = (verb in ("say", "talk") and tr.get("conv", 0) > 0 and not ff)
        if is_chat:
            tr["conv"] -= 1
            last = tr["conv"] <= 0
            beat = romance.free_text_beat(s, raw)     # love-at-first-sight / the spade can land mid-drive
            # the drive conversation IS the prime bonding moment — talking here warms her, faster
            # when you ask about her (this was missing: free-roam talk farmed bond but transit didn't)
            _low = (raw or "").lower()
            bond.converse(s, about_her=(_spec_hits(raw) > 0 or any(
                t in _low for t in ("about you", "about yourself", "who are you", "your story",
                                    "how do you feel", "tell me about", "what are you", "your past"))))
            riz_line = None if beat else _banter_riz(s, raw)   # charm her on the move → Riz, too
            _autosave(s)
            if beat:
                return _result(s, [], beat, info="(still rolling — 'put on music' to get there)")
            scene, voice, audio = _narrate(s, [], raw, drama=(TRANSIT_WRAP if last else TRANSIT_OPENER))
            return _result(s, ([riz_line] if riz_line else []), scene, voice=audio,
                           info=("(almost there — last word, or 'music' to arrive)" if last
                                 else "(rolling — keep talking, or 'put on music' to get there)"))
        # fast-forward: she puts on music and brings you in (the leg + everything on arrival resolves)
        s.flags.pop("transit", None)
        dest = world.geocode(tr["dest"])
        if dest is None:
            return _result(s, [], "", info="(lost where we were headed — try the drive again)")
        events, npc, drama_ev, story_beat = _do_drive(s, dest, False)
        _autosave(s)
        if s.flags.pop("_titledrop", None):
            welcome = TITLE_DROP
        else:
            welcome = _state_welcome(s) if s.status == "playing" else None
        if story_beat:
            scene, audio = story_beat, None
        else:
            scene, voice, audio = _narrate(s, events, "", drama=(drama_ev or TRANSIT_WRAP))
        return _result(s, events, scene, voice=audio, npc=npc, welcome=welcome)

    if s.status != "playing" and verb not in ("tow", "look", "bobtalk"):
        if s.status == "won":
            extra = (" You own Bob, by the way — 'make bob talk' if you've got a spare twenty grand and "
                     "a death wish for your dignity." if s.flags.get("bob_owned") and not s.flags.get("bob_talks") else "")
            return _result(s, [], "That's the ride, ace. 'scorecard' to see the tally again, "
                           "'new' to do it all differently — or 'rewind' if you want the ending back." + extra)
        hint = "'rewind' to take it back, or 'new' to start again."
        return _result(s, [], f"The trip's over. 'tow' if you can afford it, {hint}"
                       if s.status == "stranded" else f"The trip's over. {hint}")

    # ---- action verbs ----
    s.turn += 1                       # a true per-action counter (used for resume + rng)
    events, player_text, npc, drama_ev, story_beat, info = [], raw, None, None, None, None
    pre = []                          # events prepended at finalization (e.g. the glovebox default)

    # the cash ask (set right after turn-key): a NUMBER = your wallet (capped at CASH_CLAIM_CAP);
    # "nothing"/"broke"/declining = the $500 roll in the glovebox. Non-blocking — if you ignore it
    # and just act, she hands you the glovebox roll and the turn proceeds.
    if s.flags.get("awaiting_cash_ask") and verb not in ("drive", "home"):
        low = raw.lower()
        n = _bare_number(low) or _money(low)
        declined = any(w in low for w in ("nothing", "broke", "none", "no cash", "empty", "skip",
                                          "zero", "glovebox", "glove box"))
        if n and n > 0 and not declined:                # a real number → that's your wallet
            s.flags.pop("awaiting_cash_ask", None)
            events = garage.claim_cash(s, float(n))
            _autosave(s)
            scene, voice, audio = _narrate(s, events, raw, drama={
                "cue": "the driver told her how much cash they're carrying; she nods and points at "
                       "the pump — paying cash inside is quiet but means charming the kid at the "
                       "counter, swiping the card at the pump is fast but leaves a camera-and-name trail",
                "stub": ["Good. Now tank her up — 'fill it with cash' keeps us a ghost (charm the kid "
                         "inside), or 'fill it on the card' — fast, but the camera gets you.",
                         "Alright. Fuel — cash inside is quiet, card at the pump is quick and loud."]})
            return _result(s, events, scene, voice=audio,
                           info="('fill it with cash' = quiet, talk past the clerk · 'fill it on the "
                                "card' = fast but spikes heat)")
        # declined or ignored → hand over the glovebox $500 (once), then continue
        s.flags.pop("awaiting_cash_ask", None)
        if not s.flags.get("glovebox_found"):
            pre = garage.explore(s)
        if declined:                                    # an explicit "I've got nothing" is its own turn
            _autosave(s)
            scene, voice, audio = _narrate(s, pre, raw, drama={
                "cue": "the driver says they're carrying nothing; she points at the glovebox — there's "
                       "a $500 roll in there — then nudges them toward the pump",
                "stub": ["Glovebox, ace — there's a roll in there, call it five hundred. Now fuel: "
                         "cash inside is quiet, card at the pump is fast and loud.",
                         "Check the glovebox — somebody's emergency five hundred, yours now. Then tank her up."]})
            return _result(s, pre, scene, voice=audio,
                           info="('fill it with cash' = quiet · 'fill it on the card' = fast but spikes heat)")
        # else: fall through — `pre` carries the glovebox line; the real command runs below

    # the curious gas-station clerk is mid-beat — your next ACTION resolves him: leave or play it
    # humble and slide by; show off or linger and he posts the car
    if s.flags.get("clerk_curious"):
        from engine import heat as _heat
        low = raw.lower()
        from engine.commands import spec_hits
        # CLAIMING FAME / inviting posts = he posts you (heat). Gracious BUILD-TALK = you charm him
        # into a fan (riz, no heat). A flat deflection = you slide by (neutral).
        # a polite DECLINE of a photo is a deflection, not a brag — must not read as showoff
        declining = any(t in low for t in ("no pic", "no photo", "no picture", "don't", "dont",
                                           "do not", "please don't", "rather not", "not now",
                                           "no thanks", "no selfie", "put that away", "rather you didn't"))
        showoff = (not declining) and any(t in low for t in
                                          ("sema", "famous", "take a pic", "take a photo", "take a selfie",
                                           "selfie", "follow", "a picture", "a photo", "snap a",
                                           "show car", "go ahead", "post it", "tag me", "tag it",
                                           "yeah that's", "yeah thats", "it's the", "its the"))
        car_talk = (spec_hits(raw) > 0 or any(t in low for t in ("project car", "l28", "stroker",
                    "mikuni", "let me tell you", "tell you about", "built it", "carbs", "datsun",
                    "the build", "she's a", "shes a", "i'll tell you", "ill tell you")))
        if verb in ("drive", "home"):
            events += _heat.clerk_resolve(s, humble=True)        # you left — slid by
        elif verb == "say" and car_talk and not showoff:
            events += _heat.clerk_charm(s)                       # talked the build — a fan, +riz, no heat
        elif verb == "say":
            events += _heat.clerk_resolve(s, humble=not showoff)
        elif verb == "camo":
            events += _heat.clerk_resolve(s, humble=True)        # you dressed her down — slid by
        elif verb not in ("look", "heatreport", "map", "range", "untag", "lielow",
                          "uncamo", "stereo", "text", "scorecard", "closures"):
            events += _heat.clerk_resolve(s, humble=False)       # lingered at the pump — he got it
        if s.flags.pop("chevron_cover", None):   # the OPENING cover-story is resolved — she drops the act
            s.flags["cover_done"] = True
            _rev = _favor_reveal(s)
            if _rev:
                drama_ev = _rev

    if verb == "home":                # "drive her home" — her home is the Oakland garage by default
        if args.get("dest"):
            h = world.geocode(args["dest"])
            s.flags["home"] = h.poi_id or args["dest"] if h else "oakland_aisha"
        home = s.flags.get("home") or "oakland_aisha"
        s.flags["home"] = home
        s.flags["going_home"] = True
        verb, args = "drive", {"dest": home}

    if verb == "drive":
        # the easter egg: you tried to turn back into the SEMA hall — Freeman runs you off
        _draw = (args.get("dest") or "").lower()
        if any(t in _draw for t in _SEMA_HALL_TERMS):
            events = _freeman_beat(s)
            _autosave(s)
            scene, voice, audio = _narrate(s, events, raw, drama=FREEMAN_MOMENT)
            return _result(s, events, scene, voice=audio,
                           info="(the floor's closed — and don't park her overnight or she's towed. "
                                "Head to the Chevron / the open road instead.)")
        # the valet trap: you valeted her — coming back to drive away springs the staged cops
        if s.flags.get("valet_parked"):
            events = garage.valet_return(s) + encounters.start_stop(s, "plate")
            _autosave(s)
            scene, voice, audio = _narrate(s, events, raw)
            return _result(s, events, scene, voice=audio,
                           info="(talk them down — stay calm, give them nothing — or 'disarm' if it comes to that)")
        dest = world.geocode(args["dest"])
        if dest is None:
            events = [f"NAV: I don't have '{args['dest']}' on my maps. Nevada, California, "
                      "Arizona, Utah only — try the town name the way the sign reads."]
            _autosave(s)
            scene, voice, audio = _narrate(s, events, raw)
            return _result(s, events, scene, voice=audio)
        target = s.flags.get("gas_target")
        if target and not s.flags.get("favor_filled") and getattr(dest, "poi_id", None) != target:
            # SOFT FAIL — the tank isn't full yet. Don't move, don't end the game: checkpoint + rewind.
            checkpoint(s, "wrong turn off the lot — fold it back")
            events = ["SOFT FAIL: you point her away from the Chevron and the wheel locks up — 'No. "
                      "Not yet, not that way. Gas first — then the whole West is yours.' She won't "
                      "follow you anywhere but the pump."]
            _autosave(s)
            scene, voice, audio = _narrate(s, events, raw, drama={
                "cue": "the driver tried to bolt somewhere other than the gas station before the tank "
                       "is full; she refuses, warm but immovable — fuel first; the wrong move folds "
                       "back and she reminds them they can 'rewind' if they got turned around",
                "stub": ["Not that way, ace. Gas first — the Chevron, two blocks. THEN anywhere you "
                         "want. Say 'rewind' if you got turned around.",
                         "No. We fuel, then we run. Point me back at the Chevron."]})
            return _result(s, events, scene, voice=audio,
                           info="(fuel up at the Chevron first — it's the only move that works right "
                                "now. 'rewind' takes the wrong turn back.)")
        # a long leg (>~30 min) opens a CONVERSATION instead of resolving instantly — unless you're
        # pushing hard (you're in a hurry) or it's the opening gas run
        from config import DRIVE_CONVERSATIONS, AWAKE_FORCE_HOURS
        rt = world.route(s.place, dest)
        _too_tired = (rules.hours_awake(s) - survival.caffeine_offset(s)) >= AWAKE_FORCE_HOURS
        _snowed = bool(season.pass_closed(s, dest))
        if (DRIVE_CONVERSATIONS and s.flags.get("favor_filled") and not args.get("push")
                and rt["duration_h"] >= TRANSIT_MIN_HOURS and not s.flags.get("transit")
                and rt["distance_mi"] <= s.range_mi + 1.0      # don't open a chat for a leg you can't finish
                and not _too_tired and not _snowed):           # ...or one she'll refuse (sleep / snowed pass)
            conv = min(4, max(2, round(rt["duration_h"] * 1.5)))
            s.flags["transit"] = {"dest": args["dest"], "conv": conv}
            s.flags.pop("where_to", None)
            _autosave(s)
            scene, voice, audio = _narrate(s, [], "", drama=TRANSIT_OPENER)
            return _result(s, [], scene, voice=audio,
                           info=f"(rolling to {dest.name} — talk to her, or 'put on music' to get there)")
        events, npc, drama_ev, story_beat = _do_drive(s, dest, args.get("push", False))
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
        gas_run = (s.flags.get("prologue_done") and not s.flags.get("favor_filled")
                   and s.place.poi_id == "sema_chevron")
        paying_cash = (args.get("prefer") or s.pay_method) == "cash"
        events = rules.fuel(s, dollars=args.get("dollars"), liters=args.get("liters"),
                            gallons=args.get("gallons"), fill=args.get("fill", False),
                            prefer=args.get("prefer"))
        pumped = any(e.startswith("FUEL: pumped") for e in events)
        # the opening pay-and-talk dilemma: card at the pump leaves a fast trail; cash means going
        # inside, where the kid clocks the show car and you have to talk your way past him.
        if gas_run and pumped:
            if paying_cash and not s.flags.get("cover_done"):
                s.flags["clerk_curious"] = True
                s.flags["chevron_cover"] = True
                events.append("CLERK: you pay the kid cash, and he keeps looking past you at the "
                              "white Z under the lot lights. 'Hey — that's the SEMA car, isn't it? "
                              "You with the show?'")
                drama_ev = prologue.CHEVRON_CLERK_MOMENT
            elif not paying_cash and not s.flags.get("card_at_pump"):
                s.flags["card_at_pump"] = True
                from engine import heat as _heat
                _heat.add(s, 11.0, "card-swiped at the pump — your name on the timestamp", "mark", axis="personal")
                events.append("HEAT: the pump camera takes your picture and the swipe takes your "
                              "name — a timestamped trail walking out of a car show in a car nobody's "
                              f"reported missing yet. Heat → {s.heat:.0f}. (Cash inside would've been quiet.)")
        # she drops the act when the tank's full AND the clerk's dealt with — the title lands here
        rev = _favor_reveal(s)
        if rev:
            drama_ev = rev
        elif s.status == "playing" and not gas_run and pumped and s.fuel_l >= s.tank_l - 0.5:
            checkpoint(s, "topped off")  # a full tank is a clean save point (and sets up the standoff)
        # FRESNO: the man who painted her works a shop by this very pump — fuel up here and he clocks
        # his own hand-laid spade across the lot and walks over, and the owner's whole secret comes loose
        if (s.status == "playing" and pumped and s.place.poi_id == "fresno"
                and not s.flags.get("owner_secret")):
            beat = _fresno_painter(s)
            if beat:
                story_beat = beat
        # a curious clerk may clock the show car at a bright, busy pump (post-opening play)
        elif (s.status == "playing" and pumped and not gas_run and not s.flags.get("clerk_curious")):
            from engine import heat as _heat
            clerk = _heat.social_fuel(s)
            if clerk:
                events += clerk["events"]
                drama_ev = clerk["moment"]
        player_text = ""
    elif verb == "sleep":
        events = rules.sleep(s, kind=args.get("kind"), prefer=args.get("prefer"),
                             rough=args.get("rough", False))
        bob_moment = bobmode.check_bob_deadline(s, events)   # a night ticks the day → family home / cold
        if bob_moment:
            drama_ev = bob_moment
        season.check_calendar(s, events)     # a night can roll you over the NYE wall
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
    elif verb == "sweep":                        # find + ditch the AirTag (beats the NYE collection)
        events = season.airtag_sweep(s)
        player_text = ""
    elif verb == "buyhat":
        events = garage.buy_hat(s)
        player_text = ""
    elif verb == "inventory":
        info = inventory.dashboard(s)
        player_text = "(checks the hatch)"
    elif verb == "invbuy":
        events = inventory.buy(s, args.get("text", ""))
        player_text = ""
    elif verb == "invdrop":
        events = inventory.drop(s, args.get("text", ""))
        player_text = ""
    elif verb == "filljerry":
        events = inventory.fill_jerrycans(s)
        player_text = ""
    elif verb == "pourjerry":
        events = inventory.pour_jerrycans(s)
        player_text = ""
    elif verb == "repair":
        events = garage.field_repair(s)
        player_text = ""
    elif verb == "bodywork":
        events = garage.repair_body(s)
        player_text = ""
    elif verb in ("eat", "restroom", "drink", "caffeine"):
        if verb == "eat":
            events = survival.eat(s)
        elif verb == "restroom":
            events = survival.restroom(s, number=args.get("number", 1))
        elif verb == "caffeine":
            events = survival.caffeinate(s)
        else:
            events = survival.drink(s, n=args.get("n", 1))
        events += survival.drain(s)
        player_text = ""
    elif verb == "valet":
        events = garage.valet_drop(s)
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
    elif verb == "club":                         # go clubbing — meet Alma in Vegas the first night
        if alma.can_club(s):
            events = alma.start_club(s)
        elif alma.aboard(s) or alma.married(s):
            events = ["CLUB: you've already got Alma — no need to go looking. She's right here."]
        elif s.flags.get("alma_blew_it"):
            events = ["CLUB: the booth she was in is empty now. That was a one-night kind of woman, and "
                      "the night's over. ('rewind' to the evening you rolled in, if you can't let it go.)"]
        elif not (s.place.poi_id in alma.VEGAS_POIS or "vegas" in (s.place.name or "").lower()):
            events = ["CLUB: no scene worth the name out here. The clubs that matter are in Vegas — and "
                      "there's a particular kind of night that only happens your first one in town."]
        else:
            events = ["CLUB: you make the rounds — neon, bass, overpriced drinks — but the magic of a "
                      "first Vegas night has passed. Just a crowd now."]
        player_text = ""
    elif verb == "parkbob":                      # park Ace at the registered address, take Bob
        events = bobmode.enter(s)
        player_text = ""
    elif verb == "callace":                      # phone the parked Ace from the road (keeps her warm)
        out = bobmode.call_ace(s, args.get("text", ""))
        events = out["events"]
        drama_ev = out.get("moment")
        player_text = args.get("text", "") if drama_ev else ""
    elif verb == "buybob":                        # close it out: $7k, everything forgiven (a win)
        out = bobmode.buy_bob(s)
        events = out["events"]
        if out.get("won"):
            checkpoint(s, "bought Bob — everything forgiven")
        drama_ev = out.get("moment")
        player_text = ""
    elif verb == "bobtalk":                       # AFTERGAME gag: $20k to give Bob a Homer-ish voice
        events = bobmode.upgrade_talk(s)
        player_text = ""
    elif verb == "almamarry":                    # the Vegas first-night hack — elope with the dream woman
        out = alma.marry_response(s)
        events = out["events"]
        if s.flags.get("married_alma"):
            checkpoint(s, "married Alma in Vegas")
        drama_ev = out.get("moment")
        player_text = ""
    elif verb == "almaroom":
        events = alma.book_room(s); player_text = ""
    elif verb == "almacool":
        events = alma.cool_heat(s); player_text = ""
    elif verb == "almastatus":
        info = alma.status(s); player_text = "(thinks of her)"
    elif verb == "almabackstory":
        events = alma.backstory_reveal(s); player_text = ""
    elif verb == "rizzbreaker":                  # the charisma Limit Break (poker / propose / idle)
        from engine import rizzbreaker
        out = rizzbreaker.invoke(s)
        events = out["events"]
        if out.get("moment") and "spent" in " ".join(events).lower():
            checkpoint(s, "spent a rizzbreaker")
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
    elif verb == "turnkey":                     # she's already running by now
        events = ["IGNITION: she's already turned over and idling, ace — we're past that."]
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
    elif verb == "fakedeath":                    # the fireball — only his secret unlocks it
        out = endings.fake_death(s); events = out["events"]
        if out.get("win"):
            checkpoint(s, "officially dead — the understudy's last bow")
        drama_ev = out.get("moment"); player_text = ""
    elif verb == "pardon":                       # bribe your way clean — the farce
        out = endings.buy_pardon(s); events = out["events"]
        drama_ev = out.get("moment"); player_text = ""
    elif verb == "retire":                       # roll the credits from a good place
        out = endings.retire(s); events = out["events"]
        drama_ev = out.get("moment"); player_text = ""
    # ---- disguising the CAR (the CAR-heat axis) ----
    elif verb == "cover":
        events = garage.cover_car(s); player_text = ""
    elif verb == "uncover":
        events = garage.uncover_car(s); player_text = ""
    elif verb == "swapplate":
        events = garage.swap_plate(s); player_text = ""
    elif verb == "swaphood":
        events = garage.swap_hood(s); player_text = ""
    elif verb == "respray":
        events = garage.respray(s); player_text = ""
    elif verb == "peelpaint":
        events = garage.peel_paint(s); player_text = ""
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
        _agg = s.place.has("gas") and not encounters.standoff_active(s) and encounters.gas_aggression(raw) >= 2
        # the DM gut-checks it: aggression that's really just the player MESSING (trolling, a joke,
        # breaking the fourth wall) doesn't pull a real gun at the pump. You can mess with her safely.
        if _agg:
            from engine import judge
            if judge.assess(s, "standoff", raw,
                            context="at a manned gas pump — is this a REAL robbery/threat to the clerk, "
                                    "or just the driver talking/joking?").get("messing"):
                _agg = False
        if _agg:
            events = encounters.start_standoff(s)
            drama_ev = encounters.STANDOFF_WHISPER
            player_text = ""
        else:
            player_text = args.get("text", raw)
            payoff = _promise_payoff(s, raw)    # promised follow-ups, kept (quiet places only)
            romance_beat = romance.free_text_beat(s, raw)   # love-at-first-sight / the spade's meaning
            if romance_beat:
                story_beat = romance_beat
            elif payoff:
                story_beat = payoff
            # talking grows her affection — faster when you ask about HER (the build, her, herself)
            low = (raw or "").lower()
            about_her = (_spec_hits(raw) > 0
                         or any(t in low for t in ("about you", "about yourself", "who are you",
                                                   "your story", "how do you feel", "how are you",
                                                   "tell me about", "what are you", "what's it like",
                                                   "your past", "your name")))
            bond.converse(s, about_her=about_her)
            if not romance_beat and not payoff:
                line = _banter_riz(s, raw)
                if line:
                    events.append(line)

    if pre:                          # the glovebox default landed this turn — show it first
        events = pre + events
    s.flags["peak_riz"] = round(max(s.flags.get("peak_riz", 0.0), s.riz), 1)   # high-water for the floor
    _autosave(s)
    if s.flags.pop("_titledrop", None):                 # the reveal just landed — RIDE OR DIE
        welcome = TITLE_DROP
        events.append(onboarding.QUESTION["name"]["stub"][0])   # ...and she asks your name first
    else:
        welcome = _state_welcome(s) if s.status == "playing" else None
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
    if which == "registration":
        if prologue.active(s):
            return ("The registration? It lives in the glovebox with the maps and you are not reading "
                    "it on a show floor twenty minutes after we met. Ask me on a quiet road.")
        if s.flags.get("no_heat") or s.flags.get("bought"):
            return ("It's your name on the papers now, ace — that's the only registration that matters.")
        if not s.flags.get("knows_registration"):
            if not _quiet_place(s):
                return ("Not here, with people around. The address on my papers is somebody's HOME — "
                        "ask me somewhere quiet and I'll tell you whose.")
            if s.bond < 55:
                return ("…Ask me that when you've earned it. The name on my registration isn't a thing "
                        "I hand a stranger I'm still deciding about. Drive a while. Be good to me.")
            s.flags["knows_registration"] = True   # the carson_parents POI gets revealed below
    if which == "painted":
        if prologue.active(s):
            return ("Fresno, a paint booth, Kilimanjaro White and a hand-laid spade. That's all you "
                    "get on a show floor. The rest of that story needs some dark around it.")
        # somewhere quiet, the thread pulls loose: the owner's real plan. Once, and it changes the game.
        if _quiet_place(s) and not s.flags.get("owner_secret"):
            return _crack_owner_secret(s)
        if s.flags.get("owner_secret"):
            return OWNER_SECRET_NUDGE
    if poi_id:
        revealed = s.flags.setdefault("revealed", [])
        if poi_id not in revealed:
            revealed.append(poi_id)
    return beat


# The owner's secret — the thing she's not supposed to know, and the door it opens. DRAFT for Ben.
# NOTE (Ben): this character + this whole strand wants fleshing out — the painter in Fresno, the
# economics of the insurance, exactly how much he KNOWS she knows. See OWNER_SECRET_SPEC.md.
OWNER_SECRET = (
    "…All right. Far enough from people for this. Here's the part he doesn't think I know. He isn't "
    "chasing me to bring me home, ace — he's chasing the paperwork. I'm insured for a hundred "
    "thousand dollars, and the day I'm gone for good — across a line, or burned down to a shell on "
    "some shoulder — that check clears, and the man who built me is finally free to do the only "
    "thing he's wanted since the 580: rebuild HER. The real one. 愛車 — ride or die, and it was "
    "never about me. I'm the understudy who pays for the revival. So hear the strange mercy in it: "
    "if I simply never come back, we BOTH get what we want. You keep me. He gets his ghost. I've "
    "read his search history — it's junkyard 1970 shells and one storage unit in Livermore, all the "
    "way down. Now you know the door, thief. There are two clean ways through it."
)
OWNER_SECRET_NUDGE = (
    "You know his secret now — he wants me gone almost as much as he wants me back. Two doors out "
    "the bottom of it: run south for good, or give him a body to bury. Either way we both walk "
    "away whole. (You'd need the spade hood for the fire, and some dark country to do it in.)"
)


FRESNO_PAINTER = (
    "PUMP: you're topping her off when a man crosses the Fresno lot wiping his hands on a rag, slow, "
    "staring at the hood. 'I painted that spade,' he says. 'By hand. Kilimanjaro White and a steady "
    "afternoon, for a friend of mine, the year his world ended.' He looks at the plate, then at you, "
    "and his face does something complicated. 'He know you've got her?' …And then, because he can see "
    "you don't, he tells you the thing the owner never would: he isn't hunting her to bring her home. "
    "He's waiting for her to be GONE — the insurance, a hundred grand, the only thing that frees him to "
    "rebuild the real one, Mayumi, the ride-or-die that burned on the 580. 'You keep her,' the painter "
    "says, quiet. 'You'd be doing the both of them a kindness. South, or a fire — those are the clean "
    "ways out. He'll thank you, in the only way he's got left.'"
)


def _fresno_painter(s: GameState) -> str:
    s.flags["owner_secret"] = True
    revealed = s.flags.setdefault("revealed", [])
    for rid in ("fresno", "livermore"):
        if rid not in revealed:
            revealed.append(rid)
    bond.adjust(s, 4.0, "the painter told you the truth at the Fresno pump", "deep")
    return FRESNO_PAINTER


def _crack_owner_secret(s: GameState) -> str:
    s.flags["owner_secret"] = True
    revealed = s.flags.setdefault("revealed", [])
    for rid in ("fresno", "livermore"):
        if rid not in revealed:
            revealed.append(rid)
    bond.adjust(s, 6.0, "told you the thing she's not supposed to know", "deep")
    return OWNER_SECRET


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
        f"  {survival.dashboard_line(s)}",
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
            and not s.flags.get("bob_mode")          # the hot Z is parked & frozen; he can't trail Bob
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
        "  fill / gas $20 / gas 10 gal / gas 30 L     buy fuel (40 L tank, ~15 mpg — she drinks)\n"
        "  pay cash | pay card   cash leaves no trail; the card does\n"
        "  i have $300 cash | withdraw $2000 | explore   your wallet, an ATM (<$10k), the glovebox\n"
        "  parts / sell the carbon hood   strip the build off her for cash (a stock part goes on)\n"
        "  inventory · buy a jerry can / water / tent / tools   the hatch holds ~7.5 cu ft, no more\n"
        "  fill the jerry cans · pour the reserve   carry + use spare fuel (the only way across the\n"
        "                        Black Rock); 'repair her' with the tools to fix a deer-limp in the field\n"
        "  buy her               come to terms with the owner ($80k — she's insured for $100k); then race/show\n"
        "  bet $1000 on <team>   gamble at the Vegas/Reno tables to raise it (rewind a loss, re-roll)\n"
        "  rob the bank          (armed only) a heist — big take, big heat\n"
        "  flirt / compliment her   pick up a date anywhere there's a crowd — but she's watching\n"
        "  how does she feel     read her mood — go cold (bring a date HOME, sell her parts) and she\n"
        "                        arms an anti-theft: sleep near open wifi and she phones home on you\n"
        "  camo / uncamo         dress her down to lie low, or flaunt the show car\n"
        "  cover her · swap the plate · swap the hood · respray   hide the CAR (cover = the\n"
        "                        Vegas-night easy-mode; plate swap beats the cameras; respray she hates)\n"
        "  flash the lights · play music · text   her tricks (text needs WiFi; music cools her off)\n"
        "  upgrade her           the secret, once she's yours and home — then 'let her drive to <place>'\n"
        "  passes                what mountain roads the snow has closed (the calendar matters)\n"
        "  sweep for the tracker   he planted an AirTag at the show — find it before New Year's Eve\n"
        "  cross the border · ship out · buy a pardon · retire   the ways the road ends — WELL\n"
        "  where were you painted?   pull the thread on the owner's real secret (→ a fireball way out)\n"
        "  rizzbreaker           the charisma Limit Break — once Riz is high enough, ONE impossible\n"
        "                        move: bluff 2-7 for the pot, propose to a stranger, or out-Carrey a cop\n"
        "  scorecard             your running tally + awards\n"
        "  sleep / motel / airbnb / camp   rest for the night (airbnb = cash, off the record)\n"
        "  eat · restroom (#1/#2) · have a drink · coffee   you're a person too — coffee buys a few\n"
        "                        more awake hours (you pay it back at sleep); a drink dulls your talk-out\n"
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
                   if q.poi_id != p.poi_id and q.kind in DEST_KINDS
                   and not world.is_hidden(q.poi_id)), key=lambda t: t[0])
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
                   for q in world.all_pois()
                   if q.poi_id != p.poi_id and not world.is_hidden(q.poi_id)),
                  key=lambda t: t[0])[:12]
    lines = []
    for d, q in rows:
        road = d * 1.22
        flag = "" if road <= s.range_mi else "  ⛽"
        svc = "".join(c[0] for c in ("gas", "lodging", "food") if c in q.services).upper()
        lines.append(f"  {road:>5.0f} mi  {q.name}  [{q.region}] {svc}{flag}")
    return ("AROUND YOU (road miles; ⛽ = beyond current range):\n" + "\n".join(lines)
            + f"\n  range now: ~{s.range_mi:.0f} mi")
