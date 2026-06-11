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
from engine import world, rules, economy, save, drama, prologue, encounters
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


# --------------------------------------------------------------------- new game
def new_game(seed: int | None = None, prologue_on: bool = True) -> GameState:
    """prologue_on=True opens on the show floor (the favor). False starts at the Chevron,
    favor already done — the pre-Ride-or-Die behavior, kept for tests and old saves."""
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
    s.flags = {"sid": f"{seed}", "states_seen": [start.region] if start.region else []}
    save.delete(f"chk1_{seed}")            # a fresh game owns a fresh checkpoint ring
    save.delete(f"chk2_{seed}")
    if prologue_on:
        prologue.start(s)
    else:
        s.flags["prologue_done"] = True
        s.flags["favor_filled"] = True
        checkpoint(s)
    save.save(s, "autosave")
    return s


# --------------------------------------------------------------------- checkpoints
# She keeps the saves — the compute behind the dash. Checkpoints land on every clean POI
# arrival, after sleep, after the favor, and after a resolved encounter. 'rewind' goes back
# one; a second consecutive rewind reaches one checkpoint deeper. Riz survives the fold —
# only you two remember.
def _chk(s: GameState, n: int) -> str:
    return f"chk{n}_{s.flags.get('sid', 'x')}"


def checkpoint(s: GameState) -> None:
    if save.exists(_chk(s, 1)):
        prev = save.load(_chk(s, 1))
        save.save(prev, _chk(s, 2))
    s.flags.pop("rewound_once", None)
    save.save(s, _chk(s, 1))


def rewind(s: GameState):
    """In-place restore to the last checkpoint. Returns (events, moment|None).
    Riz REVERTS with the world (minus the fee) — style earned in a timeline that never
    happened never happened either, which is what keeps rewind-loops from farming it."""
    deeper = bool(s.flags.get("rewound_once")) and save.exists(_chk(s, 2))
    chk = save.load(_chk(s, 2) if deeper else _chk(s, 1))
    if chk is None:
        return (["REWIND: there's no checkpoint behind you yet."], None)
    riz = max(0.0, round(chk.riz - RIZ_REWIND_COST, 1))
    rewinds = s.flags.get("rewinds", 0) + 1
    s.__dict__.update(GameState.from_dict(chk.to_dict()).__dict__)
    s.riz = riz
    s.flags["rewinds"] = rewinds
    s.flags["rewound_once"] = True
    if deeper:
        save.save(s, _chk(s, 1))             # collapse the ring — this is the floor now
    save.save(s, "autosave")
    events = [f"REWIND: the world folds back to {s.place.name}. {rules._clock_str(s)}. "
              f"Riz −{RIZ_REWIND_COST:.0f} → {s.riz:.0f}. "
              "(Rewinding again, before anything saves, reaches one checkpoint deeper.)"]
    return (events, REWIND_MOMENT)


# --------------------------------------------------------------------- snapshot
def _heat_label(h: float) -> str:
    if h >= rules.HEAT_ROADBLOCK_THRESHOLD:
        return "roadblocks out for this car"
    if h >= rules.HEAT_DECLINE_CARD_THRESHOLD:
        return "burning — they're watching the card"
    if h >= rules.HEAT_PATROL_THRESHOLD:
        return "hot — patrols are interested"
    if h >= 20:
        return "warm"
    return "cold"


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
        "heat": round(s.heat), "heat_label": _heat_label(s.heat),
        "riz": round(s.riz),
        "odometer_mi": round(s.odometer_mi), "adventures": list(s.adventures),
        "status": s.status, "turn": s.turn,
        "gas_price": round(economy.gas_price(p), 2) if p.has("gas") else None,
    }


# --------------------------------------------------------------------- choices
def choices(s: GameState) -> list:
    can_rewind = save.exists(_chk(s, 1))
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

    # mid-encounter: your mouth is the only tool you have
    if encounters.stop_active(s) or encounters.owner_active(s):
        return [{"cmd": "look", "note": "stall for one second"}]

    p = s.place
    out = [{"cmd": "look", "note": "where things stand"},
           {"cmd": "map", "note": "what's around"}]
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


def handle(s: GameState, raw: str) -> dict:
    verb, args = parse(raw)

    # ---- pure console verbs, available everywhere ----
    if verb == "help":
        return _result(s, [], "", info=_help_text())
    if verb == "save":
        save.save(s, "autosave")
        return _result(s, [], "", info="Saved.")
    if verb == "rewind":              # the Edge-of-Tomorrow escape — works from any ending
        events, moment = rewind(s)
        if moment is None:
            return _result(s, events, "")
        scene, voice, audio = _narrate(s, events, "", drama=moment)
        return _result(s, events, scene, voice=audio)
    if verb == "load" or verb == "new":
        return _result(s, [], "", info="(handled by the server)")

    # ---- an open traffic stop / the owner owns the conversation ----
    # This must come before every other verb: anything you say mid-encounter is SPEECH.
    # "…full tank of fresh 91 sitting in her right now…" has to reach the officer,
    # not the range calculator.
    if (encounters.stop_active(s) or encounters.owner_active(s)) and s.status == "playing":
        s.turn += 1
        in_stop = encounters.stop_active(s)
        if verb in ("drive", "home", "fuel", "sleep", "tow"):
            events = ["LAW: not while the flashlight's on you. Talk first." if in_stop
                      else "OWNER: he's standing right there. Talk."]
            save.save(s, "autosave")
            scene, voice, audio = _narrate(s, events, "", drama={
                "cue": "the driver tried to do anything except talk while "
                       + ("an officer" if in_stop else "the man who built her")
                       + " stood at the window — she stops them cold: words first",
                "stub": ["Words first, ace. WORDS first.",
                         "No. Mouth, then pedals. That's the whole play here."]})
            return _result(s, events, scene, voice=audio)
        if verb == "look":            # taking stock doesn't burn a round
            save.save(s, "autosave")
            scene, voice, audio = _narrate(s, [], "(takes stock)", drama={
                "cue": "the driver glances over the dash mid-encounter — she answers in a "
                       "near-soundless whisper, staying furniture",
                "stub": ["(whisper) Numbers are on the dash. Eyes front.",
                         "(barely audible) It's all there. Don't look at me — look at him."]})
            return _result(s, [], scene, voice=audio, info=_look_text(s))
        out = (encounters.stop_turn if in_stop else encounters.owner_turn)(s, raw)
        events = out["events"]
        if out["done"] and s.status == "playing":
            checkpoint(s)             # survived it — that's worth saving
        save.save(s, "autosave")
        scene, voice, audio = _narrate(s, events, "", drama=out["moment"])
        return _result(s, events, scene, voice=audio)

    # ---- meta verbs (no LLM) ----
    if verb == "map":
        return _result(s, [], "", info=_map_text(s, args.get("service")))
    if verb == "range":
        return _result(s, [], "", info=_range_text(s))
    if verb == "pay":
        s.pay_method = args["method"]
        return _result(s, [], "", info=f"Paying with {s.pay_method} now.")
    if verb == "origin":
        if prologue.active(s):
            prologue.note_turn(s)     # her story counts as a turn of conversation
        beat = _origin_beat(s, args["which"])
        save.save(s, "autosave")
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
            checkpoint(s)
            save.save(s, "autosave")
            scene, voice, audio = _narrate(s, events, "", drama=out["moment"])
            return _result(s, events, scene, voice=audio, welcome=TITLE_DROP)
        save.save(s, "autosave")
        scene, voice, audio = _narrate(s, events, raw, drama=out["moment"])
        return _result(s, events, scene, voice=audio)

    if s.status != "playing" and verb not in ("tow", "look"):
        hint = "'rewind' to take it back, or 'new' to start again."
        return _result(s, [], f"The trip's over. 'tow' if you can afford it, {hint}"
                       if s.status == "stranded" else f"The trip's over. {hint}")

    # ---- action verbs ----
    s.turn += 1                       # a true per-action counter (used for resume + rng)
    events, player_text, npc, drama_ev, story_beat, info = [], raw, None, None, None, None

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
            save.save(s, "autosave")
            scene, voice, audio = _narrate(s, events, raw)
            return _result(s, events, scene, voice=audio)
        before_odo = s.odometer_mi
        events = rules.drive(s, dest, push=args.get("push", False))
        moved = s.odometer_mi > before_odo
        if s.status == "playing" and moved:
            if encounters.stop_active(s):        # law_check opened a roadblock stop mid-drive
                drama_ev = encounters.WHISPER_MOMENT
            else:
                npc = _encounter(s)
                if npc:
                    events.append(f"ENCOUNTER: {npc['who']} greets you in {npc['label']}, "
                                  "not switching to English.")
                story_beat = _story_on_arrival(s)    # a set-piece reveal takes the moment
                if not story_beat and not s.place.poi_id:
                    fact = world.wiki_fact(s.place.lat, s.place.lon)   # ANY town brings something up
                    if fact:
                        events.append(f"FACT: {fact}")
                if not story_beat:
                    if _owner_should_appear(s):  # the man who built her finds you before the dice do
                        events += encounters.start_owner(s)
                        drama_ev = OWNER_ARRIVAL_MOMENT
                    else:
                        drama_ev = drama.maybe_event(s)  # else: nothing ever goes to plan
                        if drama_ev:
                            events += drama_ev["lines"]
                        if encounters.stop_active(s) and drama_ev is None:
                            drama_ev = encounters.WHISPER_MOMENT
            encounters.check_owner_deadline(s, events)
            # a clean arrival is a checkpoint — unless something's still standing at the window
            if (s.place.poi_id and s.status == "playing"
                    and not encounters.stop_active(s) and not encounters.owner_active(s)):
                checkpoint(s)
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
            checkpoint(s)
        player_text = ""
    elif verb == "sleep":
        events = rules.sleep(s, kind=args.get("kind"), prefer=args.get("prefer"),
                             rough=args.get("rough", False))
        if s.status == "playing":
            checkpoint(s)             # a survived night is a checkpoint
        player_text = ""
    elif verb == "tow":
        events = rules.tow(s, prefer=args.get("prefer"))
        if s.status == "playing":
            story_beat = _story_on_arrival(s)    # a flatbed arrival still counts as arriving
            checkpoint(s)             # rescued — don't make them re-buy the flatbed
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
    else:  # say — conversation
        player_text = args.get("text", raw)
        payoff = _promise_payoff(s, raw)        # promised follow-ups, kept (quiet places only)
        if payoff:
            story_beat = payoff

    save.save(s, "autosave")
    welcome = _state_welcome(s)
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
        f"  HEAT  {s.heat:.0f} ({_heat_label(s.heat)}) · RIZ ♠ {s.riz:.0f}",
        f"  {dt.strftime('%a %b %-d, %-I:%M %p')} · day {s.day} · {s.odometer_mi:.0f} mi · "
        f"awake {rules.hours_awake(s):.0f}h",
    ]
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
        "  sleep / motel / camp  rest for the night (you must, most nights)\n"
        "  talk                  speak with the locals where the language isn't English\n"
        "  map / nearby gas      see what's around\n"
        "  where can we get to on one tank?           the range question, with real math\n"
        "  look                  fuel, money, time, heat, riz\n"
        "  rewind                back to the last checkpoint (twice in a row goes one deeper)\n"
        "  tow                   the only way off the shoulder — and a fast way to get caught\n"
        "  save / new            \n"
        "Just typing to her also works. She has opinions. If the law pulls you over, your\n"
        "mouth is the whole game: stay calm, sell the story, know the build."
    )


def _range_text(s: GameState) -> str:
    """'Where can we get to on one tank?' — answered with the real numbers, like everything else."""
    p = s.place
    now_mi = s.range_mi
    full_mi = (s.tank_l / LITERS_PER_GALLON) * s.mpg
    rows = sorted(((world.haversine_mi(p.lat, p.lon, q.lat, q.lon) * ROAD_WINDING_FACTOR, q)
                   for q in world.all_pois() if q.poi_id != p.poi_id), key=lambda t: t[0])
    reach_now = [(d, q) for d, q in rows if d <= now_mi]
    reach_fill = [(d, q) for d, q in rows if now_mi < d <= full_mi]
    lines = [f"ON THIS TANK (~{now_mi:.0f} mi of road):"]
    if reach_now:
        for d, q in reach_now[:10]:
            svc = "".join(c[0] for c in ("gas", "lodging", "food") if c in q.services).upper()
            lines.append(f"  {d:>5.0f} mi  {q.name}  [{q.region}] {svc}")
        if len(reach_now) > 10:
            lines.append(f"  …and {len(reach_now) - 10} more in range.")
    else:
        lines.append("  nowhere. The shoulder is not a destination — buy gas first.")
    lines.append(f"AFTER A FILL (~{full_mi:.0f} mi on 40 L):")
    for d, q in reach_fill[:8]:
        lines.append(f"  {d:>5.0f} mi  {q.name}  [{q.region}]")
    lines.append("  (mountain legs burn more — Zion, Tioga, Bryce eat the margin)")
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
