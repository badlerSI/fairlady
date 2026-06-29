"""Weather — a deterministic 55-day climatology for NV/CA/AZ/UT, Nov 7 – Dec 31 2025, with the season's
real storms overlaid.

There is no live data and no historical file to fetch: every (day, place) resolves from the game seed +
the calendar + the town's latitude and its `terrain` value (the elevation proxy already used for fuel and
the snow line). A small table of the season's actual fronts (content/weather_events.json) nudges the
baseline on the right days in the right places — the first Sierra snow, the Thanksgiving warm window, the
big pre-Christmas storm — so you can read a front coming, outrace it, or get caught and stuck.

What it powers:
  - atmosphere (a line on arrival, a HUD readout),
  - the COLD-START ritual (a cold morning won't catch without the pump-pump-hold — see game/rules),
  - chain-control escalation (an active storm chains a mountain grade even before the seasonal line does),
  - a small cold/altitude fuel penalty.

Everything is pure + seeded, so a session is reproducible and a rewind re-derives the same sky. Prose is a
working DRAFT for Ben.
"""
from __future__ import annotations
import json
from datetime import date

from config import (CONTENT_DIR, START_ISO, COLD_START_TEMP, WEATHER_ELEV_LAPSE_F)
from engine.state import GameState

try:
    _EVENTS = json.loads((CONTENT_DIR / "weather_events.json").read_text()).get("events", [])
except Exception:
    _EVENTS = []
for _e in _EVENTS:                                  # parse the date windows once
    _e["_d0"] = date.fromisoformat(_e["date_range"][0])
    _e["_d1"] = date.fromisoformat(_e["date_range"][1])

_START = date.fromisoformat(START_ISO[:10])         # 2025-11-07
_LAT_REF = 36.0                                     # ~Las Vegas; north of this runs colder

# `terrain` is a grade/fuel proxy, not true elevation, so a few rugged-but-LOW or coastal towns come out
# absurdly cold (Death Valley snowing, SF in the 20s). Floor their lows so they never read as snow country.
_WARM = {
    # the low/hot desert
    "death_valley", "stovepipe", "badwater", "furnace_creek", "amboy", "amboy_ca", "baker_ca", "needles",
    "lake_havasu", "laughlin", "blythe", "yuma", "parker", "ehrenberg", "salton_sea", "bombay_beach",
    "salvation_mountain", "calexico", "el_centro", "indio", "palm_springs", "twentynine_palms",
    # the coast — maritime, doesn't snow
    "san_francisco", "oakland_aisha", "richmond_koinoya", "sf_japantown", "berkeley", "monterey", "carmel",
    "big_sur", "santa_cruz_boardwalk", "santa_cruz", "san_jose", "los_angeles", "santa_monica",
    "long_beach", "venice_beach", "santa_barbara", "san_diego", "seaworld_sd", "malibu", "ventura",
    "half_moon_bay", "pacifica", "hayward", "richmond",
}
_WARM_LOW_FLOOR = 38.0                               # these towns' overnight low never drops below this

# regional sea-level baseline highs/lows (deg F), interpolated Nov 7 -> Dec 31 (~mild autumn -> cold winter).
# Calibrated so the desert valleys (Vegas/Phoenix) land near real Nov-Dec normals; altitude + latitude pull
# the mountains down from here.
_HIGH_NOV, _HIGH_DEC = 67.0, 55.0
_LOW_NOV, _LOW_DEC = 46.0, 35.0
_SEASON_DAYS = 54.0                                 # Nov 7 (day 1) .. Dec 31 (day 55)


def _hashf(*parts) -> float:
    """A stable 0..1 from ints/strings — our seeded 'noise' without Math.random (which is banned)."""
    h = 2166136261
    for p in parts:
        for ch in str(p):
            h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
        h = (h * 16777619) & 0xFFFFFFFF
    return (h & 0xFFFFFF) / float(0xFFFFFF)


def _progress(d: date) -> float:
    return max(0.0, min(1.0, (d - _START).days / _SEASON_DAYS))


def _active_events(d: date, place):
    """Every weather event whose window covers `d` and whose region/zone matches `place`."""
    region = getattr(place, "region", "") or ""
    pid = getattr(place, "poi_id", None)
    out = []
    for e in _EVENTS:
        if not (e["_d0"] <= d <= e["_d1"]):
            continue
        zone = e.get("zone") or []
        if zone:
            if pid in zone:
                out.append(e)
        elif region in (e.get("regions") or []):
            out.append(e)
    return out


def daily(s: GameState, place=None) -> dict:
    """The day's weather where `place` is (defaults to s.place). Deterministic, cached per (date, poi)."""
    place = place or s.place
    d = s.clock.date()
    pid = getattr(place, "poi_id", None) or f"{getattr(place,'lat',0):.2f},{getattr(place,'lon',0):.2f}"
    cache = s.flags.setdefault("weather_cache", {})
    key = f"{d.isoformat()}:{pid}"
    if key in cache:
        return cache[key]

    prog = _progress(d)
    lat = float(getattr(place, "lat", _LAT_REF))
    terrain = float(getattr(place, "terrain", 1.0))

    base_high = _HIGH_NOV + (_HIGH_DEC - _HIGH_NOV) * prog
    base_low = _LOW_NOV + (_LOW_DEC - _LOW_NOV) * prog
    lat_adj = (_LAT_REF - lat) * 2.2                       # north = colder
    elev_adj = -(max(0.0, terrain - 1.0)) * WEATHER_ELEV_LAPSE_F
    # a multi-day 'system' wobble + a per-day jitter, both seeded (no RNG)
    wobble = (_hashf(s.seed, d.year, d.month, (d.day // 3)) - 0.5) * 12.0
    jitter = (_hashf(s.seed, pid, d.toordinal()) - 0.5) * 7.0

    high = base_high + lat_adj + elev_adj + wobble + jitter
    low = base_low + lat_adj + elev_adj + wobble * 0.7 + jitter * 0.6

    # precip: rare in the desert, likelier high & cold & later in the season
    precip = 0.0
    wet_roll = _hashf(s.seed, "wet", pid, d.toordinal())
    wet_chance = 0.06 + 0.20 * prog + 0.35 * max(0.0, terrain - 1.05)
    if wet_roll < wet_chance:
        precip = round(0.1 + wet_roll * 1.5, 2)
    wind = round(6.0 + _hashf(s.seed, "wind", pid, d.toordinal()) * 16.0 + (terrain - 1.0) * 20.0, 0)

    # overlay the real fronts
    for e in _active_events(d, place):
        if "low_f" in e:
            low = min(low, float(e["low_f"]))
            high = min(high, float(e["low_f"]) + 14.0)
        low += float(e.get("low_bump", 0))
        high += float(e.get("high_bump", 0)) + float(e.get("low_bump", 0)) * 0.5
        if e.get("snow_in"):
            precip = max(precip, float(e["snow_in"]) / 10.0)
        if e.get("rain_in"):
            precip = max(precip, float(e["rain_in"]))
        if e.get("wind_mph"):
            wind = max(wind, float(e["wind_mph"]))

    if pid in _WARM:                                      # a low-desert or coastal town never snows
        low = max(low, _WARM_LOW_FLOOR)
        high = max(high, low + 12.0)
    high = round(high, 0)
    low = round(low, 0)
    snowing = bool(precip >= 0.1 and low <= 34.0)         # cold + wet = it's falling as snow
    if snowing:
        code, cond = "snow", "snow"
    elif precip >= 1.2:
        code, cond = "storm", "heavy rain"
    elif precip >= 0.1:
        code, cond = "rain", "rain"
    elif wind >= 35:
        code, cond = "wind", "windy"
    elif _hashf(s.seed, "sky", pid, d.toordinal()) < 0.7:  # most dry days in the Southwest are simply clear
        code, cond = "clear", "clear"
    else:
        code, cond = "cloudy", "overcast"

    w = {"high_f": high, "low_f": low, "precip_in": round(precip, 2), "snow": snowing,
         "wind_mph": wind, "code": code, "condition": cond, "date": d.isoformat(),
         "storm": bool(precip >= 1.0 or (snowing and precip >= 0.6))}
    cache[key] = w
    if len(cache) > 400:                                   # keep the save from ballooning
        for k in list(cache)[:200]:
            del cache[k]
    return w


# ------------------------------------------------------------------ cold-start
def cold_start_needed(s: GameState) -> bool:
    """A cold morning (or a cold night after she's sat) needs the pump-pump-hold ritual. True when the
    low where she's parked is at/below COLD_START_TEMP and the engine is cold (early/late hours), and she
    hasn't been started yet today."""
    # the white Z's carbs are the whole point — a car that's legally yours (maintained), the brown Bob
    # loaner (a modern automatic), or one driving herself doesn't put you through the ritual.
    if s.flags.get("no_heat") or s.flags.get("bob_mode") or s.flags.get("self_driving"):
        return False
    if s.flags.get(f"cold_started_{s.clock.date().isoformat()}"):
        return False
    hour = s.clock.hour
    if not (hour < 11 or hour >= 20):                     # engine's only stone-cold morning/late-night
        return False
    return daily(s)["low_f"] <= COLD_START_TEMP


def mark_started(s: GameState) -> None:
    s.flags[f"cold_started_{s.clock.date().isoformat()}"] = True
    s.flags["crank_count"] = 0                             # a clean start clears the cranking strain


# ------------------------------------------------------------------ the battery (over-cranking kills it)
CRANK_LIMIT = 4                                            # this many fruitless cold cranks flattens her


def crank(s: GameState) -> bool:
    """Count one fruitless cold crank. Returns True if THIS one flattened the battery."""
    n = s.flags.get("crank_count", 0) + 1
    s.flags["crank_count"] = n
    if n >= CRANK_LIMIT and not s.flags.get("battery_dead"):
        s.flags["battery_dead"] = True
        return True
    return False


def battery_dead(s: GameState) -> bool:
    return bool(s.flags.get("battery_dead"))


def cranks_left(s: GameState) -> int:
    return max(0, CRANK_LIMIT - s.flags.get("crank_count", 0))


# ------------------------------------------------------------------ storms vs chain controls
def storm_chains(s: GameState, dest) -> bool:
    """An ACTIVE snow storm chains a mountain grade even before the seasonal snow line reaches it — it's
    snowing on the road right now. Only on real snow-country destinations."""
    from engine import season
    pid = getattr(dest, "poi_id", None)
    if pid not in season.CHAIN_ZONES and pid not in season.SNOW_PASSES:
        return False
    w = daily(s, dest)
    return bool(w["snow"] and w["precip_in"] >= 0.4)


def storm_closes(s: GameState, dest) -> bool:
    """A severe storm (feet of snow, gale wind) on a genuine PASS shuts it outright, even if the seasonal
    line hasn't reached it yet."""
    from engine import season
    if getattr(dest, "poi_id", None) not in season.SNOW_PASSES:
        return False
    w = daily(s, dest)
    return bool(w["snow"] and w["precip_in"] >= 3.0 and w["wind_mph"] >= 45)


# ------------------------------------------------------------------ fuel + atmosphere
def fuel_factor(s: GameState, dest) -> float:
    """A small extra fuel burn for a cold engine and thin high-altitude air."""
    w = daily(s, dest)
    f = 1.0
    if w["low_f"] <= 20:
        f += 0.05
    if float(getattr(dest, "terrain", 1.0)) >= 1.15:
        f += 0.05
    return round(min(1.12, f), 3)


_FEEL = {
    "snow": "Snow's coming down — fat, quiet flakes catching in the wipers.",
    "storm": "It's coming down in sheets; the wipers can't keep up and the gutters are rivers.",
    "rain": "A cold rain ticks on the roof, the road shining black under the lights.",
    "wind": "The wind shoves at her flank in gusts, grit hissing against the paint.",
    "clear": "High, hard desert blue — not a cloud, the light going gold and long.",
    "cloudy": "Flat gray overcast, the cold sitting in the bones of the day.",
}


def line(s: GameState, place=None) -> str:
    """A short atmosphere line for an arrival / a 'weather' check."""
    w = daily(s, place)
    feel = _FEEL.get(w["code"], "")
    return (f"WEATHER: {w['condition']}, {w['high_f']:.0f}°/{w['low_f']:.0f}°F"
            + (f", wind {w['wind_mph']:.0f}" if w["wind_mph"] >= 25 else "")
            + (f". {feel}" if feel else "."))


def report(s: GameState) -> list:
    """The 'weather'/'forecast' command — here-and-now plus any front the radio's tracking."""
    out = [line(s)]
    d = s.clock.date()
    # any storm event live or imminent in this region telegraphs (read the front coming)
    region = getattr(s.place, "region", "")
    soon = []
    for e in _EVENTS:
        if e.get("hook") not in ("outrace", "first_closure", "cold_snap"):
            continue
        days_out = (e["_d0"] - d).days
        in_region = region in (e.get("regions") or []) or getattr(s.place, "poi_id", None) in (e.get("zone") or [])
        if in_region and -1 <= days_out <= 4:
            when = "now" if days_out <= 0 else (f"in {days_out} day" + ("s" if days_out != 1 else ""))
            soon.append(f"  → {when}: {e['what']}")
    if soon:
        out.append("FORECAST — the radio's tracking:")
        out += soon
    return out


def snapshot(s: GameState) -> dict:
    """The weather block for the HUD."""
    w = daily(s)
    return {
        "temp_high_f": w["high_f"], "temp_low_f": w["low_f"], "condition": w["condition"],
        "weather_code": w["code"], "snowing": w["snow"], "wind_mph": w["wind_mph"],
        "storm": w["storm"], "cold_start_needed": cold_start_needed(s),
        "battery_dead": battery_dead(s),
    }
