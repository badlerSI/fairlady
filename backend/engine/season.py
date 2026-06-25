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

from config import SEASON_SNOW_START, SNOW_LINE_HIGH, SNOW_LINE_LOW, SNOW_LINE_DESCENT
from engine.state import GameState

_SNOW_EPOCH = datetime.fromisoformat(SEASON_SNOW_START)

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


def closures_text(s: GameState) -> str:
    """A little seasonal report — what's already shut and what's about to, given today's date."""
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
