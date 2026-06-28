"""Cameras — the ALPR / Flock layer. Fixed automated plate-readers that ping CARTALK as you pass.

Grounded in real end-2025 Flock Safety deployment density. The short version of the data dump:
California is the most camera-saturated state in the country; the big metros — the LA basin, the
Bay, Sacramento, San Diego, plus Las Vegas, Phoenix, Tucson, and Salt Lake City — run dense fixed
ALPR grids on intersections and arterials. Mid-size cities have some. Small towns have a couple.
The high desert, the two-lane passes, the ghost towns, and ESPECIALLY the national parks have
essentially none. So the map itself is the lesson: a stolen show car bleeds CAR heat every time it
rolls through a city, and goes quiet the instant you get it out into the empty country. Stay rural,
stay in the parks, and the meter forgets you. The cities are where you get caught.

This routes to the CAR axis (the PLATE is what the camera reads — that's the car's problem, not
yours). It's deterministic and legible — every ping logs a factor on the heat dashboard — unlike
the rare, high-variance Instagram tag in heat.py. The two model different real things and can both
fire in a dense metro (you're hot there for two reasons), which is exactly right.

The plate is the tell. CARTALK is a vanity plate the builder bolted on for the show floor; run it
and it comes back to a 1980 Nissan Cedric wagon, registered to a name that isn't yours — a mismatch
a bored cop WILL clock, and a punchline she is not proud of. See plate_mismatch().

Prose is a working DRAFT for Ben.
"""
from __future__ import annotations

from engine.state import GameState, Place

# --------------------------------------------------------------- the density map
# 3 = SATURATED (dense Flock grid — the plate gets read a dozen times crossing town)
# 2 = MODERATE  (a real camera network, mid-city)
# 1 = SPARSE    (a county sheriff with a couple of readers)
# 0 = NONE      (nobody's watching — rural two-lanes, the desert, the parks)

# The big metros, grounded in the real deployment data. CA dominates; the dense non-CA hubs follow.
_SATURATED = {
    # LA basin
    "los_angeles", "hollywood", "santa_monica", "venice_beach", "beverly_hills", "rodeo",
    "pasadena", "long_beach", "santa_ana", "anaheim", "disneyland", "knotts", "universal",
    "getty", "petersen", "riverside",
    # Bay Area
    "san_francisco", "golden_gate", "bay_bridge", "oakland_aisha", "san_jose", "berkeley",
    "fishermans_wharf",
    # other saturated CA
    "sacramento", "san_diego", "fresno", "stockton", "bakersfield",
    # the dense non-CA metros
    "las_vegas", "vegas_strip", "fremont", "sphere", "neon_museum", "lv_motor_speedway",
    "phoenix", "tucson", "salt_lake_city",
}

# Mid-size cities and tourist hubs — a real network, not a wall of cameras.
_MODERATE = {
    "santa_barbara", "ventura", "napa", "santa_cruz_boardwalk", "monterey", "san_luis_obispo",
    "palm_springs", "palm_desert", "santa_cruz", "santa_rosa", "modesto", "carmel",
    "reno", "carson_city", "laughlin", "primm", "mesquite", "lake_havasu", "henderson",
    "st_george", "flagstaff", "sedona", "park_city", "provo", "moab", "scottsdale", "tempe",
}

# Genuinely dark spots — the desert, the ghost towns, the parks. Heat goes to sleep here.
_DARK = {
    "berlin_nv", "bodie", "area51_gate", "rachel", "racetrack_playa", "great_basin", "gerlach",
    "goldfield", "amargosa_valley", "mina_nv", "why_az", "zzyzx", "trona", "searchlight",
    "eureka_nv", "austin_nv", "mexican_hat", "bluff_ut", "hanksville", "tonopah", "beatty",
    "baker_ca", "shoshone", "lone_pine", "independence_ca", "panamint_springs",
}

DENSITY_WORD = {0: "no cameras — dark country", 1: "a couple of county readers",
                2: "a real ALPR network", 3: "a saturated Flock grid"}

# CAR heat applied on arrival, per density level (before disguise).
_ARRIVAL_HEAT = {0: 0.0, 1: 1.0, 2: 3.0, 3: 6.0}


def camera_density(place: Place) -> int:
    """0–3. An explicit per-POI override in pois.json wins; else a data-grounded heuristic on
    region + kind + the named-city sets. National parks and the deep desert are 0 on purpose."""
    if place is None:
        return 0
    override = getattr(place, "camera_density", None)
    if override is not None:
        try:
            return max(0, min(3, int(override)))
        except (TypeError, ValueError):
            pass                                   # a non-numeric pois.json override → fall back to heuristic
    pid = place.poi_id or ""
    kind = getattr(place, "kind", "spot")
    name = (place.name or "").lower()
    # parks, ghost towns, the open desert, a dead shoulder — nobody's watching
    if pid in _DARK or kind in ("park", "encounter"):
        return 0
    if any(k in name for k in ("shoulder", "ghost", "playa", "national park", "wilderness")):
        return 0
    if pid in _SATURATED:
        return 3
    if pid in _MODERATE:
        return 2
    # unlisted: California is saturated even in its small cities; elsewhere a city has a few readers
    if kind == "city":
        return 2 if place.region == "CA" else 1
    if "gas" in getattr(place, "services", []):
        return 1
    return 0


def effective_density(s: GameState) -> int:
    """The density that actually pings the plate, after disguise. A SWAPPED PLATE reads clean to an
    ALPR (the whole point) and drops it to 0; the Z camo / a dressed-down car shaves one notch off
    the recognition. A car under a cover isn't being driven, so the cover doesn't figure here."""
    if s.flags.get("no_heat") or s.flags.get("covered"):
        return 0
    if s.flags.get("plate_swapped"):
        return 0                                  # the ALPR reads a clean plate — that's the whole point
    d = camera_density(s.place)
    if s.flags.get("camo"):
        d = max(0, d - 1)
    if s.flags.get("hood_swapped") or s.flags.get("resprayed"):
        d = max(0, d - 1)                         # a witness-grade tell, not a plate read — still helps a little
    return d


def arrival_heat(s: GameState) -> list:
    """Called the moment the wheels stop somewhere new. A camera-dense city pings CARTALK and bumps
    CAR heat; the dark country does nothing. Deterministic, legible, and the whole point of the
    rural-vs-city tension. Returns events (possibly empty)."""
    from engine import heat as _heat
    if _heat.meter_frozen(s):        # bought OR driving forgettable Bob — no plate worth pinging
        return []
    raw = camera_density(s.place)
    eff = effective_density(s)
    if eff <= 0:
        # surfaced ONLY when the player actively dodged a grid (swapped plate / camo in a real city)
        if raw >= 2 and (s.flags.get("plate_swapped") or s.flags.get("camo")):
            why = ("the swapped plate reads clean" if s.flags.get("plate_swapped")
                   else "the dressed-down car doesn't trip the recognition")
            return [f"ALPR: {DENSITY_WORD[raw]} here, and {why} — the cameras let you through. "
                    "Nothing on the plate."]
        return []
    dh = _ARRIVAL_HEAT[eff]
    pings = {1: "a reader or two", 2: "the network", 3: "a dozen cameras"}[eff]
    _heat.add(s, dh, f"ALPR cameras read the plate ({s.place.name})", "mark", axis="car")
    tail = ("  (Out in the desert or a park, nobody's watching — that's where she goes quiet.)"
            if raw >= 2 else "")
    return [f"ALPR: {DENSITY_WORD[raw]} in {s.place.name} — {pings} pinged CARTALK on the way in. "
            f"CAR heat +{dh:.0f} → {s.heat:.0f}.{tail}"]


# --------------------------------------------------------------- the plate is the tell
def plate_mismatch() -> str:
    """The punchline when a cop runs CARTALK during a stop: it comes back to a 1980 Cedric wagon."""
    return ("PLATE: he keys CARTALK into the terminal and frowns — it comes back registered to a "
            "1980 Nissan Cedric wagon, beige, two owners ago, and this is very much not that. "
            "A vanity plate the builder never re-papered. Whatever you're selling, sell it fast.")


def plate_risk(s: GameState) -> float:
    """Extra suspicion a plate-run adds in a stop — UNLESS you swapped to a clean plate first.
    The Cedric mismatch is a tell; a swapped plate quietly matches and removes it."""
    if s.flags.get("plate_swapped") or s.flags.get("no_heat"):
        return 0.0
    return 1.0


def nearest_haven(s: GameState):
    """The closest dark, camera-free place to run for — a ghost town, the desert, a national park.
    Berlin, NV is the canonical lie-low spot; parks are the safest country there is. Returns
    (road_miles, Place) or None. This is how she teaches you to get OUT of the cities."""
    from engine import world
    p = s.place
    best = None
    for q in world.all_pois():
        if not q.poi_id or q.poi_id == p.poi_id or world.is_hidden(q.poi_id):
            continue
        if camera_density(q) > 0:
            continue
        d = world.haversine_mi(p.lat, p.lon, q.lat, q.lon) * 1.22
        # prefer Berlin and the parks — the spots she actually likes to disappear into
        pref = 0.0 if q.poi_id == "berlin_nv" else (d if q.kind == "park" else d + 30)
        if best is None or pref < best[0]:
            best = (pref, d, q)
    return (round(best[1], 0), best[2]) if best else None
