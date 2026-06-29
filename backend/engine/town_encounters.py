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


def _beats(enc) -> list:
    """Normalize an entry to a list of beats. A modern entry has `beats:[{vignette, ace?, find?, tone?}]`;
    a legacy entry has the single vignette/ace/find at the top — treat it as a one-beat list."""
    if enc.get("beats"):
        return enc["beats"]
    return [{"vignette": enc.get("vignette", ""), "ace": enc.get("ace"),
             "find": enc.get("find"), "tone": enc.get("tone")}]


def surface(s: GameState) -> list:
    """Fire the next UNSEEN beat for the current town (a town with several beats gives you a different
    little thing each time you roll back through). Returns [] once they're all spent. Arms a find if the
    beat carries one."""
    pid = getattr(s.place, "poi_id", None)
    enc = _ENC.get(pid)
    if not enc:
        return []
    beats = _beats(enc)
    done = s.flags.setdefault("town_enc_beats", {}).setdefault(pid, [])
    nxt = next((i for i in range(len(beats)) if i not in done), None)
    if nxt is None:
        return []                                          # every beat for this town has played
    done.append(nxt)
    seen = s.flags.setdefault("town_enc_seen", [])         # legacy 'has this town fired at all' flag
    if pid not in seen:
        seen.append(pid)
    b = beats[nxt]
    out = [f"· {b['vignette']}"]
    if b.get("ace"):
        out.append(f"ACE: {b['ace']}")
    fid = b.get("find")
    if fid and not s.flags.get("pending_find"):
        from engine import finds
        if fid in finds._BY_ID and fid not in s.flags.get("found_items", []):
            s.flags["pending_find"] = fid
            out.append("  (something here's worth grabbing — 'take it')")
    return out
