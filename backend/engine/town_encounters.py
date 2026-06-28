"""Town encounters — the West-of-Loathing/Kingdom-of-Loathing layer.

Every visitable town gets one odd little arrival vignette (a barely-disguised trope or archetype),
shown ONCE the first time you roll in, after the location's factual beat and only when nothing bigger
(a story reveal, a stop, the owner) is already owning the moment. Some hand you a roadside-find item.
Content lives in content/town_encounters.json (162 towns, one each). Prose is the writers' draft for Ben.
"""
from __future__ import annotations
import json

from config import CONTENT_DIR
from engine.state import GameState

try:
    _ENC = {e["poi_id"]: e for e in json.loads((CONTENT_DIR / "town_encounters.json").read_text()).get("encounters", [])}
except Exception:
    _ENC = {}


def has(poi_id) -> bool:
    return poi_id in _ENC


def surface(s: GameState) -> list:
    """If the current town has an unseen encounter, fire it once and return its event lines (arming a
    findable item if it carries one). Returns [] otherwise."""
    pid = getattr(s.place, "poi_id", None)
    enc = _ENC.get(pid)
    if not enc:
        return []
    seen = s.flags.setdefault("town_enc_seen", [])
    if pid in seen:
        return []
    seen.append(pid)
    out = [f"· {enc['vignette']}"]
    if enc.get("ace"):
        out.append(f"ACE: {enc['ace']}")
    # a town encounter can offer a roadside-find item to pick up here
    fid = enc.get("find")
    if fid and not s.flags.get("pending_find"):
        from engine import finds
        if fid in finds._BY_ID and not (enc.get("find") in s.flags.get("found_items", [])):
            s.flags["pending_find"] = fid
            out.append("  (something here's worth grabbing — 'take it')")
    return out
