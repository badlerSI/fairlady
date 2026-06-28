"""Dated real-world events (Nov–Dec 2025) — the things actually happening in the four states while you
run. On arrival, if you've rolled into a town that's hosting a real event during its date window, it
surfaces once as flavor (and crowds usually mean a little heat). Content in content/events_nov_dec_2025.json
(researched + date-checked). The F1 Las Vegas GP has its own richer set-piece in setpieces.py; this is
the lighter layer for the NFR, the holiday light shows, the rivalry games, the meteor showers, etc.
"""
from __future__ import annotations
import json
import re

from config import CONTENT_DIR
from engine.state import GameState

try:
    _EVENTS = json.loads((CONTENT_DIR / "events_nov_dec_2025.json").read_text()).get("events", [])
except Exception:
    _EVENTS = []

# stop-words: drop the city-noise AND the generic geographic words that over-match across towns
# ("beach" must not let a Bombay-Beach event fire at Venice Beach / Long Beach).
_STOP = {"the", "las", "city", "downtown", "strip", "of", "valley", "national", "park", "area", "county",
         "north", "south", "lake", "mount", "mountain", "state", "and", "st", "santa", "fort", "center",
         "stadium", "arena", "field", "america", "beach", "sea", "springs", "mesa", "dunes", "hills",
         "hill", "river", "creek", "ranch", "rock"}
# marquee venues whose name doesn't contain the city — map them to the host poi so the event fires there
# (and ONLY there). Keys are matched as WHOLE tokens, ALL required, so 'thomas mack' != 'Mackay Stadium'.
_VENUE_HUB = {
    "thomas mack": "las_vegas", "unlv": "las_vegas", "allegiant": "las_vegas",
    "t-mobile arena": "las_vegas", "sphere": "las_vegas", "fremont street": "las_vegas",
    "venetian": "las_vegas", "bellagio": "las_vegas", "convention center": "las_vegas",
    "grand sierra": "reno", "footprint": "phoenix",
    "state farm stadium": "phoenix", "chase field": "phoenix", "phoenix raceway": "phoenix",
    "mountain america": "phoenix",  # ASU's stadium in Tempe (Phoenix metro); no Tempe poi exists
}


def _tokens(text: str):
    return set(re.findall(r"[a-z]+", (text or "").lower()))


def _sig_tokens(text: str):
    """Significant tokens of a venue/town phrase: long-enough, not city-noise/generic-geo."""
    return [t for t in re.findall(r"[a-z]+", (text or "").lower()) if t not in _STOP and len(t) > 3]


def _keys(place_hint: str):
    return _sig_tokens(place_hint)


def _matches_place(ev: dict, place) -> bool:
    name_tokens = _tokens(getattr(place, "name", ""))
    pid = getattr(place, "poi_id", None)
    hint_tokens = _tokens(ev.get("place_hint", ""))
    # a venue → host-poi mapping wins (NFR's "Thomas & Mack" → las_vegas, and nowhere else). EVERY
    # significant word of the venue key must be present as a whole token, so 'mack' can't catch 'Mackay'.
    for venue, host in _VENUE_HUB.items():
        vt = [t for t in re.findall(r"[a-z]+", venue) if len(t) >= 3]
        if vt and all(t in hint_tokens for t in vt):
            return pid == host
    # otherwise a distinctive town-name keyword from the hint must be a WHOLE token of this town's name
    keys = _keys(ev.get("place_hint", ""))
    return bool(keys) and any(k in name_tokens for k in keys)


def on_arrival(s: GameState) -> list:
    """Surface at most one dated event the current town is hosting today. Once per event per game."""
    region = getattr(s.place, "region", None)
    day = s.day
    seen = s.flags.setdefault("dated_events_seen", [])
    for ev in _EVENTS:
        if ev.get("id") in seen or ev.get("id") == "f1_vegas_gp":   # F1 has its own set-piece
            continue
        dr = ev.get("day_range") or [0, 0]
        if not (dr[0] <= day <= dr[1]):
            continue
        if region and ev.get("region") and region != ev["region"]:
            continue
        if not _matches_place(ev, s.place):
            continue
        seen.append(ev["id"])
        # PLAYER-FACING line is the real event (name + what) — NOT the dev-note game_hook.
        out = [f"EVENT: {ev.get('name','')} — {ev.get('what','')}".strip(" —")]
        # a big crowd draws eyes — a little CAR heat unless you're clear
        if not s.flags.get("no_heat") and ev.get("real"):
            from engine import heat as _heat
            _heat.add(s, 4.0, f"the crowds at {ev.get('name','the event')} put eyes on the car", "mark", axis="car")
        return out
    return []
