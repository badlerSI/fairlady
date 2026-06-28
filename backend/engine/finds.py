"""Roadside finds — the reward for actually TALKING to her on the long stretches.

Ben's design: Ace has sharp eyes and a soft spot for junk with a story. While you're in a real drive
conversation (NOT fast-forwarded), she spots things on the shoulder — practical stuff, clearable trash,
and the occasional miracle (a real Rolex on a certain mountain stretch that only turns up after a long
talk). You can `take` what she points out; a `use` DM judges what each thing is good for. The catch:
NONE of it appears if you 'put on music' and skip the conversation. Slow down, talk to her, and the
road gives you things.

The item catalog lives in content/finds.json (designed to be expanded into a HUGE list). The engine
here owns the mechanic: when/whether a find surfaces, taking it, and the deterministic uses. Creative
uses route to the DM (judge) for a verdict but never grant arbitrary state — the engine stays the
source of truth. Prose is a working DRAFT for Ben.
"""
from __future__ import annotations
import json

from config import CONTENT_DIR
from engine.state import GameState

try:
    _FINDS = json.loads((CONTENT_DIR / "finds.json").read_text()).get("items", [])
except Exception:
    _FINDS = []
_BY_ID = {it["id"]: it for it in _FINDS}

# per-chat-turn surfacing odds by rarity (only after min_talk exchanges + a location match)
_ODDS = {"legendary": 0.05, "rare": 0.11, "uncommon": 0.19, "common": 0.30}


def _eligible(s: GameState, item: dict, dest, talked: int) -> bool:
    if talked < item.get("min_talk", 3):
        return False
    if item.get("one_shot") and item["id"] in s.flags.get("found_items", []):
        return False
    where = item.get("where", "anywhere")
    if where == "anywhere":
        return True
    region = getattr(dest, "region", None)
    pid = getattr(dest, "poi_id", None)
    if isinstance(where, str):
        return where == "anywhere" or region == where
    if isinstance(where, list):
        # a list may hold poi_ids AND/OR region codes (NV/CA/AZ/UT) — match either
        return (pid in where or getattr(s.place, "poi_id", None) in where or region in where)
    return False


def maybe_spot(s: GameState, dest, talked: int):
    """Called on a drive-CHAT turn (you're talking, not skipping). Maybe surface ONE find on the
    shoulder. Returns the item dict (and arms `pending_find`), or None. Deterministic per turn/seed."""
    from engine import luck, inventory
    if s.flags.get("pending_find"):                      # one offer at a time
        return None
    pool = [it for it in _FINDS if _eligible(s, it, dest, talked)]
    if not pool:
        return None
    # one weighted roll: walk the pool (rarest first so a Rolex isn't drowned out by jerry cans)
    pool.sort(key=lambda it: _ODDS.get(it.get("rarity"), 0.2))
    r = luck.roll(s, 88)
    acc = 0.0
    for it in pool:
        p = _ODDS.get(it.get("rarity"), 0.2)
        # don't even offer something that won't fit the hatch (except the trophy-tiny ones)
        if it.get("cuft", 0) > inventory.volume_free(s) + 0.01 and it.get("cuft", 0) > 0.05:
            continue
        acc += p
        if r < acc:
            s.flags["pending_find"] = it["id"]
            return it
    return None


def spot_event(item: dict) -> str:
    return f"FIND: {item.get('spot', 'something on the shoulder')}.  ('take it' / 'grab it' — or keep rolling.)"


def take(s: GameState) -> list:
    """Take the find Ace just pointed out. Adds it to inventory (or keeps a companion), scores find
    points, and — because she only ever finds these when you're TALKING — warms her a little."""
    fid = s.flags.pop("pending_find", None)
    if not fid or fid not in _BY_ID:
        return ["FIND: nothing to grab right now — she only spots things when you're actually talking "
                "to her on the road, not skipping ahead."]
    item = _BY_ID[fid]
    from engine import inventory, bond as _bond
    s.flags.setdefault("found_items", []).append(fid)
    s.flags["find_score"] = s.flags.get("find_score", 0) + item.get("points", 20)
    _bond.adjust(s, 0.8, "stopped for something on the road because she asked", "warm")
    if fid == "stray_puppy":
        s.flags["has_dog"] = True
        return ["FIND: you scoop up the puppy and he immediately falls asleep on the transmission tunnel "
                "like he owns it. 'His name is Lucky and I will hear no arguments.' (+a companion; she is "
                "RADIANT.)"]
    # everything else goes in the hatch (the stinger-style make-room isn't needed; we checked fit)
    inv_id = {"empty_jerrycan": "jerrycan", "cooler_beer": "cooler"}.get(fid)
    if inv_id:
        inventory.add(s, inv_id, 1)
    else:
        inventory.add(s, fid, 1)
        if fid not in inventory.ITEMS:                   # register the find so inventory can show it
            inventory.ITEMS[fid] = {"name": item["name"], "cuft": item.get("cuft", 0.2),
                                    "price": item.get("value", 0), "kind": "find",
                                    "desc": item.get("use", "a roadside find")}
    return [f"FIND: you pull onto the shoulder and grab it — {item['name']}. (+{item.get('points',20)} "
            f"find points · in the hatch now)  Use it later with 'use {fid.replace('_',' ')}'."]


def use(s: GameState, raw: str):
    """The use-DM. A few finds have a hard mechanical effect; everything else gets a judged, in-character
    verdict on whether the attempt is plausible — but speech alone never grants arbitrary state."""
    from engine import inventory
    low = (raw or "").lower()
    # which find are they trying to use?
    fid = None
    for k in _BY_ID:
        if k.replace("_", " ") in low or k in low or _BY_ID[k]["name"].split()[-1].lower() in low:
            fid = k
            break
    if fid is None or not (inventory.has(s, fid) or (fid == "stray_puppy" and s.flags.get("has_dog"))):
        return None                                      # let the normal parser handle it
    item = _BY_ID[fid]
    # hard mechanical uses (engine-owned, never speech-granted)
    if fid == "gas_card":
        return [f"USE: you run the found gas card at the pump — a few free gallons that never touch YOUR "
                "card. (Heat-free splash. The card's tapped now.)"]
    if fid == "cowboy_hat":
        from engine import heat as _heat
        if not s.flags.get("no_heat"):
            _heat.add(s, -4.0, "a felt Stetson, brim down — you read as a local", "lower", axis="personal")
        return [f"USE: brim down, collar up — you read as one more cowboy passing through. Driver heat "
                f"shed a little → {s.heat:.0f}."]
    # creative use → DM verdict (flavor only; no arbitrary state change)
    from engine import judge
    v = judge.assess(s, "persuade", raw, difficulty=4,
                     context=f"the driver wants to use {item['name']} — {item.get('use','')}")
    ok = v.get("pass") or v.get("clever")
    verdict = "she figures it just might work — go on, then." if ok else \
              "she's dubious it does anything useful right here — maybe somewhere it fits better."
    return [f"USE: {item['name']} — {verdict} "
            "(the right place + the right moment makes a thing like this matter)"]
