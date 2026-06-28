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
import re

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


_MAX_STACK = 3        # you don't need a dozen of the same roadside trinket rattling around back there


def _award(s: GameState, fid: str, item: dict) -> None:
    """Find-points + a little warmth — but ONCE per unique find id, so re-grabbing a recurring jerrycan
    can't farm score or bond."""
    from engine import bond as _bond
    found = s.flags.setdefault("found_items", [])
    first_time = fid not in found
    found.append(fid)
    if first_time:
        s.flags["find_score"] = s.flags.get("find_score", 0) + item.get("points", 20)
        _bond.adjust(s, 0.8, "stopped for something on the road because she asked", "warm")


def take(s: GameState) -> list:
    """Take the find Ace just pointed out. Adds it to inventory (or keeps a companion), scores find
    points ONCE per id, and — because she only ever finds these when you're TALKING — warms her a
    little. Honors the 7.5 cu ft hatch cap (however the find was armed) and won't stack endlessly."""
    fid = s.flags.get("pending_find")
    if not fid or fid not in _BY_ID:
        s.flags.pop("pending_find", None)
        return ["FIND: nothing to grab right now — she only spots things when you're actually talking "
                "to her on the road, not skipping ahead."]
    item = _BY_ID[fid]
    from engine import inventory
    # the puppy is a passenger, not cargo — no hatch math
    if fid == "stray_puppy":
        s.flags.pop("pending_find", None)
        if s.flags.get("has_dog"):
            return ["FIND: you've already got Lucky asleep on the tunnel — one road dog is plenty."]
        s.flags["has_dog"] = True
        _award(s, fid, item)
        return ["FIND: you scoop up the puppy and he immediately falls asleep on the transmission tunnel "
                "like he owns it. 'His name is Lucky and I will hear no arguments.' (+a companion; she is "
                "RADIANT.)"]
    inv_id = {"empty_jerrycan": "jerrycan", "cooler_beer": "cooler"}.get(fid, fid)
    cuft = inventory.ITEMS.get(inv_id, {}).get("cuft", item.get("cuft", 0.2))
    # already carrying a stack of these? leave this one on the shoulder
    if inventory.count(s, inv_id) >= _MAX_STACK:
        s.flags.pop("pending_find", None)
        return [f"FIND: you've already got {inventory.count(s, inv_id)} of those back there — you leave "
                f"this one for the next desert rat."]
    # will it FIT? a tiny trophy slips in unless the hatch is literally full; anything bigger needs room
    used = inventory.volume_used(s)
    tiny = cuft <= 0.05
    if (not tiny and used + cuft > inventory.CAPACITY_CUFT + 0.01) or (tiny and used >= inventory.CAPACITY_CUFT):
        s.flags.pop("pending_find", None)
        return [f"FIND: no room — the hatch is full ({used:.1f}/{inventory.CAPACITY_CUFT:.1f} cu ft). "
                f"Drop or sell something first if you want {item['name']}."]
    s.flags.pop("pending_find", None)
    if inv_id not in inventory.ITEMS:                     # register the find so inventory can show it
        inventory.ITEMS[inv_id] = {"name": item["name"], "cuft": item.get("cuft", 0.2),
                                   "price": item.get("value", 0), "kind": "find",
                                   "desc": item.get("use", "a roadside find")}
    inventory.add(s, inv_id, 1)
    _award(s, fid, item)
    return [f"FIND: you pull onto the shoulder and grab it — {item['name']}. (+{item.get('points',20)} "
            f"find points · in the hatch now)  Use it later with 'use {fid.replace('_',' ')}'."]


def _match_owned(s: GameState, low: str):
    """Return the id of an OWNED find named in `low`, or None."""
    from engine import inventory
    def _owns(k):
        inv_id = {"empty_jerrycan": "jerrycan", "cooler_beer": "cooler"}.get(k, k)
        return inventory.has(s, inv_id) or (k == "stray_puppy" and s.flags.get("has_dog"))
    matches = [k for k in _BY_ID
               if (k.replace("_", " ") in low or k in low or _BY_ID[k]["name"].split()[-1].lower() in low)]
    return next((k for k in matches if _owns(k)), None)


def sell(s: GameState, raw: str):
    """Pawn an OWNED valuable find for cash — only where there's a counter to fence it (a town). Returns
    event lines, or None if `raw` doesn't name an owned find (so the car-PART seller can handle it)."""
    from engine import inventory
    low = (raw or "").lower().strip()
    if not low:
        return None
    fid = _match_owned(s, low)
    if fid is None:
        return None
    item = _BY_ID[fid]
    if fid == "stray_puppy":
        return ["SELL: …no. You are not selling Lucky. She'd never forgive you and frankly neither would I."]
    value = int(item.get("value", 0))
    if value < 20:
        return [f"SELL: nobody's paying real money for a {item['name']} — it's worth more as a story."]
    if not (getattr(s.place, "kind", "") == "city" or s.place.has("gas") or s.place.has("lodging")):
        return [f"SELL: nowhere to fence a {item['name']} out here — wait for a town with a pawn counter."]
    payout = max(1, int(round(value * 0.6)))             # the pawn haircut
    inv_id = {"empty_jerrycan": "jerrycan", "cooler_beer": "cooler"}.get(fid, fid)
    inventory.remove(s, inv_id, 1)
    s.cash = round(s.cash + payout, 2)
    disp = re.sub(r"^(a |an |the )", "", item["name"], flags=re.I)   # 'a real Rolex' → 'the real Rolex'
    return [f"SELL: a pawn counter in {s.place.name} takes the {disp} for ${payout} "
            f"(~60% of its ${value:,}). Out of the hatch, into your pocket — cash, no questions."]


def use(s: GameState, raw: str):
    """The use-DM. A few finds have a hard mechanical effect; everything else gets a judged, in-character
    verdict on whether the attempt is plausible — but speech alone never grants arbitrary state."""
    low = (raw or "").lower()
    # which find are they trying to use? Only an item you actually OWN can match (so a non-owned item's
    # name doesn't shadow the one in your hatch).
    fid = _match_owned(s, low)
    if fid is None:
        return None                                      # not an owned find → let the normal parser handle it
    item = _BY_ID[fid]
    # hard mechanical uses (engine-owned, never speech-granted)
    if fid == "gas_card":
        if s.flags.get("gas_card_used"):
            return ["USE: that gas card's already tapped, ace — nothing left on it."]
        s.flags["gas_card_used"] = True
        return [f"USE: you run the found gas card at the pump — a few free gallons that never touch YOUR "
                "card. (Heat-free splash. The card's tapped now.)"]
    if fid == "cowboy_hat":
        from engine import heat as _heat
        if s.flags.get("cowboy_hat_worn"):
            return ["USE: you're already wearing it, brim down — you can't get more anonymous than 'a guy "
                    "in a hat', and it only works the once."]
        s.flags["cowboy_hat_worn"] = True
        if not s.flags.get("no_heat"):
            _heat.add(s, -4.0, "a felt Stetson, brim down — you read as a local", "lower", axis="personal")
        return [f"USE: brim down, collar up — you read as one more cowboy passing through. Driver heat "
                f"shed a little → {s.heat:.0f}. (One-time — the hat only fools them once.)"]
    # creative use → DM verdict (flavor only; no arbitrary state change)
    from engine import judge
    v = judge.assess(s, "persuade", raw, difficulty=4,
                     context=f"the driver wants to use {item['name']} — {item.get('use','')}")
    ok = v.get("pass") or v.get("clever")
    verdict = "she figures it just might work — go on, then." if ok else \
              "she's dubious it does anything useful right here — maybe somewhere it fits better."
    tail = ("(the right place + the right moment makes a thing like this matter)"
            if int(item.get("value", 0)) < 100
            else f"(or 'sell the {item['name'].split()[-1].lower()}' at a pawn counter in town — it's "
                 f"worth about ${int(item.get('value',0)):,})")
    return [f"USE: {item['name']} — {verdict} {tail}"]
