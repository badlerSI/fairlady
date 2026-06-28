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

# stop-words so "Las Vegas Strip" keys on "vegas", not "the"/"strip"
_STOP = {"the", "las", "city", "downtown", "strip", "of", "valley", "national", "park", "area", "county",
         "north", "south", "lake", "mount", "state", "and", "st", "santa", "fort"}


def _keys(place_hint: str):
    return [w for w in re.findall(r"[a-z]+", (place_hint or "").lower()) if w not in _STOP and len(w) > 3]


def on_arrival(s: GameState) -> list:
    """Surface at most one dated event the current town is hosting today. Once per event per game."""
    name = (getattr(s.place, "name", "") or "").lower()
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
        keys = _keys(ev.get("place_hint", ""))
        if not keys or not any(k in name for k in keys):
            continue
        seen.append(ev["id"])
        out = [f"EVENT: {ev.get('what', ev.get('name',''))} {ev.get('game_hook','')}".strip()]
        # a big crowd draws eyes — a little CAR heat unless you're clear
        if not s.flags.get("no_heat") and ev.get("real"):
            from engine import heat as _heat
            _heat.add(s, 4.0, f"the crowds at {ev.get('name','the event')} put eyes on the car", "mark", axis="car")
        return out
    return []
