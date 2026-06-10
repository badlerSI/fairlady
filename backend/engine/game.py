"""Game orchestration: new game, state snapshots, suggested moves, and turn handling.
Ties the deterministic engine to the narrator. State authority stays in the engine."""
from __future__ import annotations
import json
import random

from config import CONTENT_DIR, AWAKE_START_ISO, AWAKE_WARN_HOURS, AWAKE_FORCE_HOURS
from engine.state import GameState
from engine import world, rules, economy, save, drama
from engine.commands import parse
from adapters import get_narrator
from adapters.base import voices

_CAR = json.loads((CONTENT_DIR / "car.json").read_text())
_INTRO = (CONTENT_DIR / "intro.md").read_text().strip()
_PERSONA = _CAR["persona"]

OPENING = (
    "Easy, hotshot — I'm not a phone and I'm not haunted. There's a little stack of compute behind the "
    "dash now, and it handed me a voice and a map: every street address and most of the worth-seeing "
    "places in Nevada, California, Arizona, Utah. All memorized. What it did not hand me is a miracle. "
    "I hold forty liters and I do about twenty to the gallon, which is a touch over two hundred miles "
    "when I'm full — and right now the needle's on the wrong side of E. You drove me out of the North "
    "Hall, which makes you a thief and makes me an accomplice. So. We're in this together, or we're a "
    "very pretty paperweight on the shoulder. Buy the gas first. Then tell me where."
)

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
        "There was someone, before you. I don't hand that out to a man who drove me off a show floor on a "
        "whim — you'll have to earn it. Drive a while. Stay out of trouble. Maybe, somewhere quiet, I'll "
        "tell you her name. Not on a parking lot. Not yet.",
        None),
}

# Set-piece reveals — coy by design, surfaced only on arrival at the right town (told once each).
# The full truth about Mayumi waits in a storage unit in Livermore. Drafts; Ben fills the details.
STORIES = {
    "monterey": {"flag": "seen_monterey", "beat":
        "Monterey. The aquarium's down on Cannery Row — go press your face to the kelp tank for me, I "
        "can't fit. And this asphalt: Car Week, August 2025, 17-Mile Drive at dawn. I rolled this exact "
        "stretch once, polished within an inch of my life, wearing someone else's hands on the wheel. "
        "Funny to be back as a stolen car. Ask me about that morning when we're farther from people."},
    "long_beach": {"flag": "knows_mayumi", "beat":
        "Long Beach. All right — this is where I tell you about Mayumi. Hagerty wrote her up once; they "
        "called it a Cherished Salvage Story, which is a kind phrase for 'pulled back from the crusher.' "
        "She's the one who loved me first, before the Oakland cats, before the spade on the hood. The "
        "salvage part is documented. The cherished part is the half that still hurts, and I'm not opening "
        "all of it on a pier. The rest is in a storage unit in Livermore, if you ever want the truth."},
    "livermore": {"flag": "knows_truth", "beat":
        "Livermore. The storage unit — Mayumi's name still on the lease, paid through a year she didn't "
        "get to finish. This is where they parked what was left of me after the salvage, in a row of "
        "roll-up doors with the boxes nobody came back for. You wanted the truth, thief? Here it is: I'm "
        "not a show car. I'm a keepsake somebody built a body around. Now you know what you took. Drive "
        "me like it."},
}


def _story_on_arrival(s: GameState):
    st = STORIES.get(s.place.poi_id)
    if not st or s.flags.get(st["flag"]):
        return None
    if st.get("requires") and not s.flags.get(st["requires"]):
        return None
    s.flags[st["flag"]] = True
    return st["beat"]

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
def new_game(seed: int | None = None) -> GameState:
    if seed is None:
        seed = random.randint(1, 2_000_000_000)
    start = world.start_place()
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
    save.save(s, "autosave")
    return s


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
        "odometer_mi": round(s.odometer_mi), "adventures": list(s.adventures),
        "status": s.status, "turn": s.turn,
        "gas_price": round(economy.gas_price(p), 2) if p.has("gas") else None,
    }


# --------------------------------------------------------------------- choices
def choices(s: GameState) -> list:
    if s.status == "stranded":
        gas = world.nearest_with_service(s.place, "gas", limit=1)
        c = []
        if gas:
            dist, dest = gas[0]
            c.append({"cmd": "tow", "note": f"flatbed to {dest.name}, ~${175 + 4*dist:.0f}"})
        c.append({"cmd": "new", "note": "start over"})
        return c
    if s.status != "playing":
        return [{"cmd": "new", "note": "drive again"}]

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

    # ---- meta verbs (no LLM) ----
    if verb == "help":
        return _result(s, [], "", info=_help_text())
    if verb == "map":
        return _result(s, [], "", info=_map_text(s, args.get("service")))
    if verb == "save":
        save.save(s, "autosave")
        return _result(s, [], "", info="Saved.")
    if verb == "pay":
        s.pay_method = args["method"]
        return _result(s, [], "", info=f"Paying with {s.pay_method} now.")
    if verb == "origin":
        beat, poi_id = LORE[args["which"]]
        if poi_id:
            revealed = s.flags.setdefault("revealed", [])
            if poi_id not in revealed:
                revealed.append(poi_id)
        save.save(s, "autosave")
        return _result(s, [], beat)
    if verb == "load" or verb == "new":
        return _result(s, [], "", info="(handled by the server)")

    if s.status != "playing" and verb not in ("tow", "look"):
        return _result(s, [], "The trip's over. 'tow' if you can afford it, or 'new' to start again."
                       if s.status == "stranded" else "The trip's over. 'new' to start again.")

    # ---- action verbs ----
    s.turn += 1                       # a true per-action counter (used for resume + rng)
    events, player_text, npc, drama_ev, story_beat = [], raw, None, None, None

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
            scene, voice, audio = _narrate(
                s, ["NAV: that address is off my maps (Nevada, California, Arizona, Utah only)."], raw)
            return _result(s, [], scene, voice=audio)
        events = rules.drive(s, dest, push=args.get("push", False))
        if s.status == "playing":
            npc = _encounter(s)
            if npc:
                events.append(f"ENCOUNTER: {npc['who']} greets you in {npc['label']}, "
                              "not switching to English.")
            story_beat = _story_on_arrival(s)    # a set-piece reveal takes the moment
            if not story_beat:
                drama_ev = drama.maybe_event(s)  # else: nothing ever goes to plan
                if drama_ev:
                    events += drama_ev["lines"]
        player_text = ""
    elif verb == "fuel":
        events = rules.fuel(s, dollars=args.get("dollars"), liters=args.get("liters"),
                            gallons=args.get("gallons"), fill=args.get("fill", False),
                            prefer=args.get("prefer"))
        player_text = ""
    elif verb == "sleep":
        events = rules.sleep(s, kind=args.get("kind"), prefer=args.get("prefer"),
                             rough=args.get("rough", False))
        player_text = ""
    elif verb == "tow":
        events = rules.tow(s, prefer=args.get("prefer"))
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
    else:  # say — conversation
        player_text = args.get("text", raw)

    save.save(s, "autosave")
    welcome = _state_welcome(s)
    if story_beat:
        scene, audio = story_beat, None         # the authored reveal, verbatim
    else:
        scene, voice, audio = _narrate(s, events, player_text, drama=drama_ev)
    return _result(s, events, scene, voice=audio, npc=npc, welcome=welcome)


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
        "  look                  fuel, money, time, heat\n"
        "  tow                   the only way off the shoulder — and a fast way to get caught\n"
        "  save / new            \n"
        "Just typing to her also works. She has opinions."
    )


def _map_text(s: GameState, service: str | None) -> str:
    p = s.place
    if service:
        rows = world.nearest_with_service(p, service, limit=8)
        head = f"NEAREST {service.upper()}:"
        lines = [f"  {d:>5.0f} mi  {q.name}  [{q.region}]" for d, q in rows]
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
