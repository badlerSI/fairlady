"""Heat — the stolen-car notoriety meter, modeled like a credit score.

Design (grounded in a research pass on what makes notoriety mechanics fun vs tiresome):
- ATTRIBUTE EVERY DELTA. Heat never moves as a bare number — each change logs a plain-language
  factor with cause, magnitude, and an age-off, so the player reads cause-and-effect and learns
  to game it. The dashboard is a Credit-Karma-style report, pulled on demand, not pushed.
- NEVER A TIMER DRIP. Heat moves only on chosen actions (swipe the card, park somewhere flashy,
  push hard, get tagged) and cools on chosen actions (cash, clean miles, lying low, state lines).
- TELEGRAPH, THEN ROLL. The car warns you before a flashy spot can get you posted; the Instagram
  tag is a rare, high-variance spike gated behind visible exposure with a dodge window — a bet you
  took, never an ambush.
- ALWAYS A WAY DOWN. Marks age off with clean miles; the dashboard shows the path back. Going
  clean is a skill flex, not a tax.

`add()` is the one true mutator. Prose is a working DRAFT for Ben.
"""
from __future__ import annotations

from config import DESPERADO_HEAT_FLOOR
from engine.state import GameState

LOG_KEEP = 16
MARK_FADE_MI = 260.0       # a derogatory mark fully ages off after ~a tank of clean miles


# --------------------------------------------------------------- location visibility
# How exposed a flashy stolen show car is here: 3 = paparazzi-bright (the Strip, Hollywood,
# Rodeo), 0 = nobody for miles. Drives the flashy-area risk and how likely a stranger posts you.
_FLASHY = {"las_vegas", "vegas_strip", "sphere", "fremont", "neon_museum", "lv_motor_speedway",
           "los_angeles", "santa_monica", "venice_beach", "hollywood", "san_francisco",
           "golden_gate", "bay_bridge", "disneyland", "knotts", "universal", "petersen",
           "getty", "rodeo", "beverly_hills", "santa_cruz_boardwalk", "fishermans_wharf",
           "palm_springs", "laguna_seca", "monterey", "long_beach", "san_diego", "pasadena"}
_REMOTE = {"berlin_nv", "bodie", "area51_gate", "rachel", "racetrack_playa", "great_basin",
           "gerlach", "goldfield", "amargosa_valley", "mina_nv", "why_az", "zzyzx", "trona",
           "searchlight", "eureka_nv", "austin_nv", "mexican_hat", "bluff_ut", "hanksville"}
# mid-to-large cities and tourist hubs — busy enough that phones come out, but not paparazzi-bright
_BUSY = {"reno", "carson_city", "sacramento", "fresno", "bakersfield", "stockton", "san_jose",
         "berkeley", "oakland_aisha", "phoenix", "tucson", "salt_lake_city", "santa_barbara",
         "ventura", "riverside", "palm_desert", "napa", "flagstaff", "sedona", "park_city",
         "santa_cruz_boardwalk", "lake_havasu", "laughlin", "primm"}


def visibility(place) -> int:
    pid = place.poi_id or ""
    name = (place.name or "").lower()
    if getattr(place, "heat_zone", False) or pid in _FLASHY:
        return 3
    if pid in _REMOTE or any(k in name for k in ("shoulder", "ghost", "ichthyosaur")):
        return 0
    kind = getattr(place, "kind", "spot")
    if pid in _BUSY or kind in ("amusement", "museum"):
        return 2
    return 1                          # small towns, gas stops, parks, tracks, generic spots


VIS_WORD = {0: "nowhere — no eyes for miles", 1: "low-key", 2: "busy, a few phones up",
            3: "paparazzi-bright — phones everywhere"}


# --------------------------------------------------------------- the meter
def _floor(s: GameState) -> float:
    if s.flags.get("no_heat"):
        return 0.0
    return DESPERADO_HEAT_FLOOR if s.flags.get("desperado") else 0.0


def add(s: GameState, delta: float, reason: str, kind: str = "mark") -> float:
    """The one true heat mutator: clamp, apply, and record the factor (cause + magnitude +
    odometer stamp for age-off). A no_heat (bought) car never moves off 0."""
    if s.flags.get("no_heat"):
        s.heat = 0.0
        return 0.0
    lo = _floor(s)
    before = s.heat
    s.heat = round(max(lo, min(100.0, s.heat + delta)), 1)
    real = round(s.heat - before, 1)
    if abs(real) >= 0.1 and reason:
        log = s.flags.setdefault("heat_log", [])
        log.append({"d": real, "r": reason, "k": kind, "day": s.day,
                    "odo": round(s.odometer_mi, 1)})
        del log[:-LOG_KEEP]
    return s.heat


def set_to(s: GameState, value: float, reason: str, kind: str = "spike") -> float:
    return add(s, value - s.heat, reason, kind)


# 5 readable bands, each changing the world; tension lives in the gradient, low heat stays playable
def band(h: float, armed: bool = False, owned: bool = False) -> str:
    if owned:
        return "CLEAR"
    if h >= 90:
        return "MOST WANTED"
    if h >= 70:
        return "FLAGGED"
    if h >= 45:
        return "TRENDING"
    if h >= 25:
        return "NOTICED"
    return "GHOST"


_BAND_GLOSS = {
    "GHOST": "nobody's looking",
    "NOTICED": "the odd phone, a few marks on the record",
    "TRENDING": "a fan account is tracking the car — patrols interested",
    "FLAGGED": "they're watching the card; lie low",
    "MOST WANTED": "plates flagged — roadblocks out for this car",
    "CLEAR": "she's yours, on paper — the meter's retired",
}


def label(h: float, armed: bool = False, owned: bool = False) -> str:
    b = band(h, armed, owned)
    if armed and b == "MOST WANTED":
        return "ARMED & DANGEROUS — they come ready"
    return f"{b} — {_BAND_GLOSS[b]}"


# --------------------------------------------------------------- the dashboard (credit report)
def _aggregate(s: GameState):
    """Collapse the ledger into hurting/helping factors, freshest first, with rough age-off."""
    hurts, helps = {}, {}
    odo = s.odometer_mi
    for e in s.flags.get("heat_log", []):
        if e["k"] == "mark" and (odo - e.get("odo", odo)) >= MARK_FADE_MI:
            continue                                          # fully aged off — don't show it
        bucket = hurts if e["d"] > 0 else helps
        cur = bucket.setdefault(e["r"], {"pts": 0.0, "n": 0, "odo": e.get("odo", odo), "k": e["k"]})
        cur["pts"] += e["d"]
        cur["n"] += 1
        cur["odo"] = max(cur["odo"], e.get("odo", odo))      # freshest stamp
    return hurts, helps


def dashboard(s: GameState) -> str:
    if s.flags.get("no_heat"):
        return ("HEAT REPORT  ·  CLEAR\n"
                "  She's titled in your name. The meter's retired. Drive in the daylight.")
    h = round(s.heat)
    armed = bool(s.flags.get("desperado"))
    filled = round(h / 5)
    bar = "█" * filled + "·" * (20 - filled)
    lines = [f"HEAT REPORT  ·  {band(s.heat, armed)}   ({h}/100)",
             f"  [{bar}]   {_BAND_GLOSS[band(s.heat, armed)]}"]
    hurts, helps = _aggregate(s)
    odo = s.odometer_mi

    def fade(stamp):
        gone = MARK_FADE_MI - (odo - stamp)
        return f"fades in ~{gone:.0f} mi" if gone > 5 else "fading now"

    if hurts:
        lines.append("  DEROGATORY MARKS:")
        for r, v in sorted(hurts.items(), key=lambda kv: -kv[1]["pts"])[:5]:
            tag = "  ⚡hard inquiry" if v["k"] == "spike" else f"  ({fade(v['odo'])})"
            lines.append(f"    +{v['pts']:>4.0f}  {r}" + (f" x{v['n']}" if v["n"] > 1 else "") + tag)
    if helps:
        lines.append("  IN YOUR FAVOR:")
        for r, v in sorted(helps.items(), key=lambda kv: kv[1]["pts"])[:4]:
            lines.append(f"    {v['pts']:>5.0f}  {r}" + (f" x{v['n']}" if v["n"] > 1 else ""))

    # the what-if simulator — planning IS the fun (Credit Karma's score simulator)
    lines.append("  WHAT IF: pay cash +0 · swipe the card ~+4 · push hard +6 · "
                 "park somewhere flashy +risk · lie low / clean miles −")
    # 1-2 contextual levers — the panel is a control surface, not a report card
    levers = []
    if s.flags.get("card_swipes"):
        levers.append("pay CASH to stop the bleed")
    if h >= 45:
        levers.append("cross a state line and run clean miles — marks age off")
    if visibility(s.place) >= 2:
        levers.append("you're parked somewhere bright — keep moving")
    if levers:
        lines.append("  DO THIS: " + "; ".join(levers) + ".")
    return "\n".join(lines)


# --------------------------------------------------------------- the social layer (Instagram)
# Funny @handles the West tags her with. The car monitors her own feed.
_TAGGERS = [
    "@desert_carspotting", "@vegasvalets", "@brunch.babe.93", "@socal_jdm",
    "@route66ramblers", "@the.gram.reaper", "@coffee_and_cars_no_filter",
    "@influencer.in.recovery", "@dadtographer", "@nokiaflip4lyfe", "@plate_detective",
    "@she_sees_everything", "@gas_station_gourmet", "@yelp_elite_karen",
]


def _social_rng(s: GameState, salt: int):
    import random
    return random.Random(s.seed * 99991 + s.turn * 521 + salt)


def social_arrival(s: GameState) -> dict | None:
    """On arriving somewhere flashy, TELEGRAPH the exposure and ROLL a rare tag (gated by how
    bright the spot is). Returns a moment dict, or None. Never fires anywhere low-key — the
    variance lives inside the band the player's own route set."""
    if s.flags.get("no_heat"):
        return None
    vis = visibility(s.place)
    if vis < 2:
        return None
    events = [f"SOCIAL: {VIS_WORD[vis]}. She watches her own feed and the notifications climb."]
    # cooldown so it can't fire two stops running — it's the spice, not the staple
    since = s.turn - s.flags.get("last_tag_turn", -99)
    chance = 0.11 * vis * (0.35 if since < 3 else 1.0)    # vis2 ~22%, vis3 ~33% per flashy stop
    if _social_rng(s, 1).random() >= chance:
        # near miss — telegraph only, the dodge window stays open
        return {"events": events,
                "moment": {"cue": "she arrives somewhere bright and busy and watches strangers half-"
                                  "notice the show car; phones are out but nobody's posted yet — she "
                                  "warns the driver, dry, that lingering here is how you go viral",
                           "stub": ["Phones out. Nobody's posted us — yet. We linger here, we trend. "
                                    "Your call, ace.",
                                    "I count a few cameras pretending not to point at me. Quick stop, "
                                    "or we're somebody's afternoon content."]}}
    # TAGGED — a hard inquiry
    handle = _TAGGERS[_social_rng(s, 2).randrange(len(_TAGGERS))]
    spike = 12 + _social_rng(s, 3).randint(0, 8) + (4 if vis == 3 else 0)
    add(s, spike, f"tagged by {handle}", "spike")
    s.flags["last_tag_turn"] = s.turn
    s.flags["instagram_tags"] = s.flags.get("instagram_tags", 0) + 1
    events.append(f"SOCIAL: {handle} just posted the car — geotagged, {spike} new eyes on the plate. "
                  f"Heat → {s.heat:.0f}. (Hard inquiry; ages off with clean miles. 'untag' to do damage control.)")
    return {"events": events, "tagged": True,
            "moment": {"cue": f"a stranger ({handle}) just posted the stolen show car to Instagram, "
                              f"geotagged, and it's the one external thing that can blindside her — "
                              f"she's mortified and funny about going viral the wrong way; tell the "
                              f"driver to get out of the frame and put miles between us",
                       "stub": [f"{handle} just posted us. GEOTAGGED. We went viral — NOT the good "
                                "kind. Drive, before the comments find a cop.",
                                f"And there it is: {handle}, four hundred likes and climbing, my plate "
                                "in frame. Miles, ace. We need miles between us and that caption."]}}


def social_fuel(s: GameState) -> dict | None:
    """The curious gas-station clerk. At a bright, busy pump he circles the show car with his
    phone — a TELEGRAPHED beat. Be humble ('say' something low-key) and slide by; linger or show
    off and he posts you. Rare and gated by how flashy the stop is, so it's a moment, not a tax."""
    if s.flags.get("no_heat") or not s.place.has("gas"):
        return None
    vis = visibility(s.place)
    if vis < 2:
        return None
    since = s.turn - s.flags.get("last_clerk_turn", -99)
    if since < 4 or _social_rng(s, 7).random() >= 0.45 * (vis - 1):
        return None
    s.flags["clerk_curious"] = True          # the dodge window: a humble word OR leaving closes it
    s.flags["last_clerk_turn"] = s.turn
    return {"events": ["CLERK: the kid behind the counter clocks the ace of spades on the hood and "
                       "comes around with his phone half-up. 'Yo — is this the SEMA car? Can I get a—'"],
            "moment": {"cue": "a starstruck gas-station clerk is circling the show car with his phone "
                              "out, about to film it for his followers; she warns the driver, fast and "
                              "dry, to keep it humble and unmemorable — a shrug and a 'just a project "
                              "car' and they're gone; show off and they're his next post",
                       "stub": ["(low) Phone's coming up. Be boring. 'Just an old project car, "
                                "man' — shrug, pay, leave. Do NOT let him film the plate.",
                                "(quiet) He thinks I'm famous. Make me forgettable — humble, quick, "
                                "gone. One selfie and we're his story."]}}


def clerk_resolve(s: GameState, humble: bool) -> list:
    """Resolve the curious clerk once it's open: a humble word (or just leaving) slides by; showing
    off / lingering gets the car posted."""
    s.flags.pop("clerk_curious", None)
    if humble:
        return ["CLERK: you give him a shrug and 'just an old project, man,' sign nothing, and pull "
                "out before he frames the plate. He posts a blurry tire. Nobody cares."]
    handle = "@" + _TAGGERS[_social_rng(s, 9).randrange(len(_TAGGERS))].lstrip("@")
    spike = 10 + _social_rng(s, 8).randint(0, 6)
    add(s, spike, f"the gas-station clerk posted you ({handle})", "spike")
    s.flags["instagram_tags"] = s.flags.get("instagram_tags", 0) + 1
    s.flags["last_tag_turn"] = s.turn
    return [f"CLERK: you let him get the shot — and the caption. {handle}: 'CARTALK plate, the "
            f"actual SEMA Z at my station 🤯'. Geotagged. Heat → {s.heat:.0f}. ('untag' to scramble.)"]


def untag(s: GameState) -> list:
    """Post-hoc agency: damage-control a tag. A small clawback, once per tag."""
    if not s.flags.get("instagram_tags") or s.flags.get("untag_used_turn") == s.turn:
        return ["UNTAG: nothing fresh to clean up — her feed's quiet right now."]
    if s.flags.get("last_tag_turn", -99) < s.turn - 4:
        return ["UNTAG: too late — that post's already screenshotted and reposted. Outrun it instead."]
    s.flags["untag_used_turn"] = s.turn
    back = 6.0
    add(s, -back, "damage control — got the post taken down", "lower")
    return [f"UNTAG: she DMs the poster something charming and a little threatening, and the post "
            f"vanishes. −{back:.0f}. The screenshots are out there, but the heat eased to {s.heat:.0f}."]


def lie_low(s: GameState) -> list:
    """An ACTIVE way down — cool off deliberately at a low-key spot. Better than waiting; useless
    where everyone can see you."""
    if s.flags.get("no_heat"):
        return ["LIE LOW: nothing to hide from — she's yours, free and clear."]
    vis = visibility(s.place)
    if vis >= 2:
        return [f"LIE LOW: you can't disappear in plain sight — {VIS_WORD[vis]}. Get to a back road "
                "or a quiet town first."]
    cool = 7.0 if vis == 0 else 4.0
    from engine import rules
    rules.advance_clock(s, 1.5)                  # it costs you an hour and a half of daylight
    add(s, -cool, "laid low, out of sight", "lower")
    return [f"LIE LOW: you tuck her behind {('a derelict barn' if vis == 0 else 'the building')} "
            f"and wait it out an hour. Nobody comes. −{cool:.0f} → {s.heat:.0f}."]
