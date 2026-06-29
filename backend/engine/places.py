"""Places — the real world the trip drives through: actual restaurants, bars, motels, and the real
NV/CA/AZ/UT events of November–December 2025. Ace suggests real spots to eat and sleep, and if you're
in the right town on the right day, you drive into something that's actually happening.

Data is auto-gathered (see RESEARCH_NOTES.md): content/eateries.json + content/world_events.json.
The eight cities Ben reserved for himself (Reno, Carson City, Oakland, Richmond, Long Beach, Fresno,
Fallon, Folsom) are deliberately SKIPPED here — their local color is his to write. Prose DRAFT.
"""
from __future__ import annotations
import json
from datetime import date

from config import CONTENT_DIR
from engine.state import GameState

RESERVED_CITIES = {"reno", "carson city", "oakland", "richmond", "long beach", "fresno",
                   "fallon", "folsom"}

_EVENTS = None
_FOOD = None


def _load() -> None:
    global _EVENTS, _FOOD
    if _EVENTS is None:
        try:
            _EVENTS = json.loads((CONTENT_DIR / "world_events.json").read_text())
        except Exception:
            _EVENTS = []
        try:
            _FOOD = json.loads((CONTENT_DIR / "eateries.json").read_text())
        except Exception:
            _FOOD = []


def _reserved(name: str) -> bool:
    n = (name or "").lower()
    return any(rc in n for rc in RESERVED_CITIES)


def _match_town(place_name: str, town: str) -> bool:
    pn, tn = (place_name or "").lower(), (town or "").lower()
    return bool(tn) and (tn in pn or pn.startswith(tn) or tn.startswith(pn.split(",")[0].strip()))


def _within(datestr: str, today: date) -> bool:
    try:
        if "/" in datestr:
            a, b = datestr.split("/", 1)
            return date.fromisoformat(a.strip()) <= today <= date.fromisoformat(b.strip())
        return date.fromisoformat(datestr.strip()) == today
    except Exception:
        return False


def active_event(s: GameState) -> dict | None:
    """A real event happening in this city, today. Reserved cities are skipped (Ben's to write)."""
    _load()
    name = s.place.name or ""
    if _reserved(name):
        return None
    today = s.clock.date()
    for e in _EVENTS:
        if e.get("reserved"):
            continue
        if _match_town(name, e.get("city", "")) and _within(e.get("date", ""), today):
            return e
    return None


def event_beat(s: GameState) -> str | None:
    """Surface a live event on arrival, once per event per game."""
    e = active_event(s)
    if not e:
        return None
    seen = s.flags.setdefault("events_seen", [])
    key = e.get("name", "")
    if key in seen:
        return None
    seen.append(key)
    return f"EVENT: {e['name']} — {e.get('venue','')}. {e.get('blurb','')} You drove right into it."


def suggest(s: GameState, kind: str = "food") -> dict | None:
    """A real local spot of the given kind (food / drink / lodging) for the current town."""
    _load()
    name = s.place.name or ""
    if _reserved(name):
        return None
    cands = [f for f in _FOOD if f.get("type") == kind and _match_town(name, f.get("town", ""))]
    return cands[0] if cands else None


def suggest_line(s: GameState, kind: str = "food") -> str | None:
    f = suggest(s, kind)
    if not f:
        return None
    verb = {"food": "There's", "drink": "Drinks?", "lodging": "Sleep?"}.get(kind, "There's")
    return f"ACE: '{verb} {f['name']} here — {f.get('note','a local spot')}.'"
