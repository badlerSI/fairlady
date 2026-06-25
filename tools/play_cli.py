#!/usr/bin/env python3
"""Playtest driver: one game command per invocation, state persisted via named saves.

    ./.venv/bin/python tools/play_cli.py <session> <seed> [command...]

First call (no existing save) starts a NEW game with <seed> and prints the opening.
Later calls load the session, apply the command, save, and print a compact JSON line.
Sessions are independent — run as many in parallel as you like (use UNIQUE seeds:
the rewind checkpoint ring is keyed by seed). Forces stub narrator + offline routing,
so runs are deterministic and network-free. Saves land in data/saves/pt_<session>.json.
"""
import sys
import os
import json

os.environ["FAIRLADY_ROUTING"] = "offline"
os.environ["FAIRLADY_ADAPTER"] = "stub"

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from engine import game, save  # noqa: E402

FLAGS_OF_INTEREST = (
    "prologue", "prologue_done", "favor_filled", "card_swipes", "knows_mayumi",
    "knows_truth", "seen_monterey", "seen_berlin", "owner_met", "owner_deadline_day",
    "report_withdrawn", "rewinds", "limp", "homestretch", "home",
    # the newer systems — surfaced so QA can see them
    "desperado", "gun", "wanted_armed", "desperado_tries", "robbed_banks", "rob_attempts",
    "bought", "no_heat", "instagram_tags", "ace_jealousy", "ace_off", "dates", "gambled_up",
    "rewind_tax", "rewinds_here", "last_rewind_seq", "cp_seq",
)


def compact(res, s):
    snap = res.get("snapshot", {})
    npc = res.get("npc")
    return {
        "turn": snap.get("turn"), "status": res.get("status"),
        "loc": snap.get("location"), "poi": snap.get("poi_id"),
        "day": snap.get("day"), "time": snap.get("time"),
        "fuel_l": snap.get("fuel_l"), "range_mi": snap.get("range_mi"),
        "cash": snap.get("cash"), "credit": snap.get("credit_available"),
        "heat": snap.get("heat"), "riz": snap.get("riz"),
        "hours_awake": snap.get("hours_awake"), "must_sleep": snap.get("must_sleep"),
        "events": res.get("events") or [],
        "her": res.get("scene") or "",
        "info": res.get("info"),
        "welcome": res.get("welcome"),
        "npc": ({"native": npc.get("native"), "english": npc.get("english")} if npc else None),
        "ending": res.get("ending"),
        "choices": [c["cmd"] for c in (res.get("choices") or [])],
        "flags": {k: s.flags.get(k) for k in FLAGS_OF_INTEREST if k in s.flags},
        "encounter_open": ("stop" in s.flags) or ("owner_scene" in s.flags),
    }


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    name, seed = sys.argv[1], int(sys.argv[2])
    cmd = " ".join(sys.argv[3:]).strip()
    sname = f"pt_{name}"

    s = save.load(sname)
    if s is None:
        s = game.new_game(seed=seed)
        save.save(s, sname)
        res = game.opening_result(s)
        out = compact(res, s)
        out["intro"] = res.get("intro")
        out["her"] = res.get("scene")
        print(json.dumps(out, ensure_ascii=False))
        return

    if not cmd:
        print(json.dumps(compact(game._result(s, [], ""), s), ensure_ascii=False))
        return

    res = game.handle(s, cmd)
    save.save(s, sname)
    print(json.dumps(compact(res, s), ensure_ascii=False))


if __name__ == "__main__":
    main()
