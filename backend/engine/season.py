"""Seasons: the mountains close as winter rolls in.

The road trip opens Nov 7. IRL, Tioga Pass is usually already shutting; the Sierra high
country, the Wasatch, and the Grand Canyon's North Rim follow through December. We model a SNOW
LINE that descends with the calendar: a terrain threshold that starts above every pass (nothing
closed, you've got a window) and drops through the season until even the 1.15 passes are chained
shut. A genuine snow-pass POI whose terrain is at or above the current snow line is closed for the
season — you can't drive TO it. It's real time pressure, and it bites hardest on a Desperado who
has to burn days lying low while the map freezes around them.

(Coming DOWN from a pass is always fine — only arriving at a snowed-in one is blocked. Desert
'high terrain' like Death Valley and Big Sur isn't in the snow set; heat and rockslides aren't
snow.) Prose is a working DRAFT for Ben.
"""
from __future__ import annotations
from datetime import datetime

from datetime import date

from config import (SEASON_SNOW_START, SNOW_LINE_HIGH, SNOW_LINE_LOW, SNOW_LINE_DESCENT,
                    SLC_EVENT_START, SLC_EVENT_END, NYE_DATE)
from engine.state import GameState

_SNOW_EPOCH = datetime.fromisoformat(SEASON_SNOW_START)
_SLC_START = date.fromisoformat(SLC_EVENT_START)
_SLC_END = date.fromisoformat(SLC_EVENT_END)
_NYE = date.fromisoformat(NYE_DATE)

# The genuine seasonal closures of NV/CA/AZ/UT — high passes that snow shut, roughly in the order
# the real ones do. Their terrain value (in pois.json) sets WHEN each closes as the snow line drops.
SNOW_PASSES = {
    "lee_vining",          # Tioga Pass — the first to go, every year
    "yosemite", "sequoia", "kings_canyon", "mammoth_lakes", "bodie",
    "great_basin",         # Wheeler Peak / Great Basin
    "grand_canyon_north",  # North Rim — gated all winter
    "bryce", "capitol_reef",
    "truckee", "south_lake_tahoe", "park_city", "mount_shasta_city",
}


def snow_line(s: GameState) -> float:
    """The terrain threshold at/above which a snow pass is currently shut. High in early Nov
    (everything open), descending ~0.005/day to a deep-winter floor."""
    days = (s.clock - _SNOW_EPOCH).total_seconds() / 86400.0
    line = SNOW_LINE_HIGH - SNOW_LINE_DESCENT * max(0.0, days)
    return max(SNOW_LINE_LOW, min(SNOW_LINE_HIGH, line))


def pass_closed(s: GameState, dest) -> str | None:
    """If `dest` is a snow pass the season has shut, return a player-facing reason; else None."""
    pid = getattr(dest, "poi_id", None)
    if pid not in SNOW_PASSES:
        return None
    if float(getattr(dest, "terrain", 1.0)) < snow_line(s):
        return None
    when = s.clock.strftime("%b %-d")
    return (f"SNOW: {dest.name} is closed for the season — the pass is chained-and-gated, drifts "
            f"over the road, and it's only {when}; it won't open till spring, and a stolen car "
            f"doesn't have till spring. Pick a lower road, or get there before the snow beat you "
            f"to it next time.")


# CHAIN CONTROLS — the rung BELOW a full closure. As the snow line drops onto a mountain route, Caltrans
# and UDOT post chain controls (R1/R2): you may pass ONLY with chains. No chains = turned back at the
# checkpoint. A high-terrain dest within CHAIN_BAND of the snow line (snowy, but not yet gated shut) is
# chain-controlled. (Ben: "chain controls will get you good.")
CHAIN_BAND = 0.10           # terrain within this much BELOW the snow line = chains required
# real chain-control country in Nov-Dec: the Sierra/Tahoe corridor, the eastern Sierra, the Wasatch,
# the high Colorado Plateau, the northern CA volcanoes — NOT desert/coastal high terrain (Death Valley,
# Big Sur, the wine-country road courses), which the snow set already excludes.
CHAIN_ZONES = {
    "south_lake_tahoe", "truckee", "kingvale", "donner", "tahoe_city", "kirkwood", "heavenly",
    "mammoth_lakes", "lee_vining", "bishop", "june_lake", "mount_shasta_city", "mount_shasta",
    "park_city", "alta", "brighton", "sundance", "deer_valley", "heber", "midway",
    "flagstaff", "snowbowl", "big_bear", "wrightwood", "yosemite", "sequoia", "kings_canyon",
    "great_basin", "bryce", "capitol_reef", "cedar_city", "brian_head", "grand_canyon_north", "bodie",
}


def chain_controlled(s: GameState, dest) -> bool:
    """True if the road to `dest` is under a chain control right now (snowing on a mountain grade, not
    yet fully closed). Restricted to real snow country; independent of whether YOU carry chains."""
    pid = getattr(dest, "poi_id", None)
    if pid not in CHAIN_ZONES and pid not in SNOW_PASSES:
        return False
    terr = float(getattr(dest, "terrain", 1.0))
    line = snow_line(s)
    return (line - CHAIN_BAND) <= terr < line        # snowy band, below the full-closure threshold


def chain_block(s: GameState, dest) -> str | None:
    """A player-facing refusal if the route is chain-controlled and you don't have tire chains; None
    otherwise (open, or you're carrying chains)."""
    from engine import inventory
    if not chain_controlled(s, dest):
        return None
    if inventory.has(s, "tire_chains"):
        return None
    return (f"CHAINS: a Caltrans chain-control checkpoint stops you short of {dest.name} — it's snowing "
            "on the grade and it's R2: chains REQUIRED, no exceptions, and you don't have any. The "
            "trooper waves you back. (Buy TIRE CHAINS at a mountain town first — 'buy chains' — take a "
            "lower road, or 'rewind' and route around the white stuff.)")


# --------------------------------------------------------------------- the dated set-pieces
def check_calendar(s: GameState, events: list) -> None:
    """Two dated events ride on top of the snow line, checked on every arrival/clock advance:
    the Salt Lake City week in early December (the owner + his APC crew catch up), and the hard
    New Year's Eve wall (the AirTag collection, unless you found the tag). Mutates `events`."""
    if s.status != "playing":
        return
    # a car the player legally owns / was set free / is driving herself is PAST all this — the owner
    # never comes for a car that's already hers on paper or that he let go. (Don't repossess a win.)
    if (s.flags.get("no_heat") or s.flags.get("bought") or s.flags.get("report_withdrawn")
            or s.flags.get("self_driving") or s.flags.get("faked_death")):
        return
    _slc_december(s, events)
    _new_years_eve(s, events)


def _slc_december(s: GameState, events: list) -> None:
    """First week of December in Salt Lake City: the man who built her is there, and this time he
    brought help — the APC crew, a flatbed, and no more patience. A guaranteed owner encounter."""
    if s.flags.get("slc_december_done"):
        return
    today = s.clock.date()
    in_slc = s.place.poi_id == "salt_lake_city"
    if in_slc and _SLC_START <= today <= _SLC_END and not s.flags.get("owner_met"):
        from engine import encounters
        s.flags["slc_december_done"] = True
        events += encounters.start_owner(s)
        events.append("OWNER: Salt Lake, first week of December — and he's waiting in the lot with "
                      "three guys in APC-crew jackets and a flatbed already idling. He knew you'd come "
                      "through here. 'You're a hard car to lose, you know that? Let's talk before my "
                      "friends stop being friendly.'")


def _new_years_eve(s: GameState, events: list) -> None:
    """The hard wall, and the reckoning. If you're still running when the year turns, the man who
    built her FINDS you — no matter where you are, no matter what you've done to hide. The AirTag was
    only ever one of his ways; press him on how and all he'll say is 'I have my ways.' Whether that's
    the end or the beginning depends entirely on what you've become to each other and to him.

    - You know his secret (he WANTS her gone) → he signs her over, freed at last. A WIN.
    - She'd cross any line for you (bond RIDE-OR-DIE) → he sees it, and lets the two of you go. A WIN.
    - Otherwise → he collects her for CES. Taken. (Ditching the AirTag earns a tip of the hat, but
      not, by itself, your freedom — you had to give him a reason.)
    """
    if s.clock.date() < _NYE:
        return
    from engine import endings, bond as _bond
    s.flags["made_new_year"] = True                 # reaching NYE alive is itself the achievement
    found = ("There was an AirTag, once — but you found that weeks ago, didn't you. Doesn't matter. "
             "'How did you—' I have my ways, kid."
             if s.flags.get("airtag_ditched")
             else "The dot behind the dash stops moving at the stroke of midnight, and he's just… "
                  "there. 'How did you find us?' …I have my ways.")
    if s.flags.get("owner_secret"):
        endings._win(s, "new_year")
        events.append("CALENDAR: New Year's Eve, and the man who built her steps out of the dark "
                      "wherever you've run to. " + found + " He looks at the two of you a long moment, "
                      "then takes a pink slip out of his coat, already signed. 'I wasn't chasing her to "
                      "take her back, ace. I was chasing the day I could let her go. You gave me that. "
                      "She's yours. Go build something I couldn't.' Happy New Year.")
        events.append(endings._scorecard(s))
    elif _bond.band(s.bond) == "RIDE-OR-DIE":
        endings._win(s, "new_year")
        events.append("CALENDAR: New Year's Eve, and he finds you anyway. " + found + " He watches how "
                      "she leans toward you, how she goes quiet and protective the second he steps "
                      "close, and something in him gives. 'She never did that for me.' He steps back "
                      "into the dark and waves you off. 'Drive, then. Both of you. Happy New Year.'")
        events.append(endings._scorecard(s))
    else:
        s.status = "taken"
        s.flags["ending_key"] = "ces"
        title, text = endings.ENDING_TEXT["ces"]
        s.ending = f"[{title}] {text}"
        events.append("CALENDAR: New Year's Eve, and he finds you — of course he does. " + found
                      + " A flatbed idles behind him. She goes to CES next week, his headline after "
                      "all. You never gave him a reason to do anything else.")
        events.append(endings._scorecard(s))


def airtag_sweep(s: GameState) -> list:
    """Sweep the car for the tracker he slipped in at the show. Findable once you have reason to look
    (he's surfaced, or the heat's real) — ditch it and the New Year's Eve collection can't find you."""
    if s.flags.get("no_heat"):
        return ["SWEEP: nothing to find — nobody's tracking a car that's legally yours."]
    if s.flags.get("airtag_ditched"):
        return ["SWEEP: already done — the tag's riding north on some stranger's bumper."]
    ready = s.flags.get("owner_met") or s.heat >= 30 or s.flags.get("knows_mayumi")
    if not ready:
        return ["SWEEP: you run your hands under the dash and the seats and find nothing yet — and "
                "honestly no reason to think there's anything to find. (Come back when you KNOW "
                "he's hunting you.)"]
    s.flags["airtag_ditched"] = True
    from engine import bond as _bond
    _bond.adjust(s, 2.0, "found the tracker he hid in me and got it off us", "warm")
    return ["SWEEP: behind the dash, zip-tied to a harness that isn't stock — a little white AirTag, "
            "patient as everything he builds. You pry it loose and stick it to the bumper of a "
            "northbound reefer truck at the next stop. Let him chase THAT to Idaho.",
            "ACE: 'He slipped that in on the show floor, didn't he. The whole time. …Thank you for "
            "looking. Most people never look.'"]


def closures_text(s: GameState) -> str:
    """The 'passes'/'closures' command — what the snow has shut and what's about to, given today."""
    from engine import world
    line = snow_line(s)
    shut, soon = [], []
    for pid in SNOW_PASSES:
        p = world.get_poi(pid)
        if not p:
            continue
        t = float(getattr(p, "terrain", 1.0))
        if t >= line:
            shut.append((t, p.name))
        elif t >= line - 0.06:                       # within ~12 days of closing
            soon.append((t, p.name))
    out = [f"MOUNTAIN PASSES  ·  {s.clock.strftime('%b %-d')}  (snow line at terrain {line:.2f})"]
    if shut:
        out.append("  CLOSED for the season:")
        out += [f"    × {n}" for _, n in sorted(shut, reverse=True)]
    else:
        out.append("  Everything's still open — but the high passes won't last.")
    if soon:
        out.append("  Going soon — get there now if you're going:")
        out += [f"    ! {n}" for _, n in sorted(soon, reverse=True)]
    return "\n".join(out)
