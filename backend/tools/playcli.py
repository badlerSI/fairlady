"""Stateful one-turn CLI for alpha playtesting against the LIVE Ace narrator.

Each call loads the named save, runs ONE player line through engine.handle(), saves, and prints a
compact JSON line: Ace's actual reply (the live LLM), the engine event log, and the state that matters
for judging (heat, bond, riz, Ai, cash, fuel, day, place, damage, status/ending). A playtest agent
improvises in a persona by reading the reply and choosing the next line — drive the same --session and
state carries across processes.

    # start a fresh run (seed fixes luck/rolls so a session is reproducible)
    python3 -m tools.playcli --session carnut --new --seed 4111
    # then feed lines, reusing the session:
    python3 -m tools.playcli --session carnut --say "they/them, and call me Riz"
    python3 -m tools.playcli --session carnut --say "yeah I can drive stick, my dad taught me on a truck"

Routing: set FAIRLADY_ADAPTER=ace for the real LLM (default here), FAIRLADY_VOICE=0 to skip TTS.
Use FAIRLADY_ADAPTER=stub for a fast offline dry-run of the harness itself.
"""
from __future__ import annotations
import argparse
import json
import os
import sys

# default to the LIVE narrator, text-only, unless the caller overrides
os.environ.setdefault("FAIRLADY_ADAPTER", "ace")
os.environ.setdefault("FAIRLADY_VOICE", "0")
os.environ.setdefault("FAIRLADY_DRIVE_CHAT", "1")    # let Ace talk on the move

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import game, save


def _snap(s) -> dict:
    snp = game.snapshot(s)
    keep = ("day", "time", "location", "heat", "heat_label", "cash", "credit_available",
            "fuel_l", "tank_pct", "range_mi", "bond", "bond_label", "riz", "ai", "affection",
            "status", "ending", "limp", "damage", "damage_pct", "must_sleep", "tired",
            "active_car", "car_name", "alma_aboard", "married", "no_heat", "bob_days_left")
    return {k: snp.get(k) for k in keep if k in snp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True)
    ap.add_argument("--say", default=None)
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--persona", default="")          # free-text label for the agent's own notes
    ap.add_argument("--full", action="store_true")    # dump the whole snapshot, not the compact view
    args = ap.parse_args()

    name = f"pt_{args.session}"
    if args.new or not save.exists(name):
        seed = args.seed if args.seed is not None else abs(hash(args.session)) % 90000 + 10000
        s = game.new_game(seed=seed, prologue_on=True, sid=args.session)
        save.save(s, name)
        if args.say is None:
            out = game.opening_result(s)
            print(json.dumps({"turn": s.turn, "opening": True,
                              "intro": out.get("intro", ""), "scene": out.get("scene", ""),
                              "snap": _snap(s)}, ensure_ascii=False))
            return

    s = save.load(name)
    if s is None:
        print(json.dumps({"error": "could not load session"})); sys.exit(1)
    if args.say is None:
        print(json.dumps({"turn": s.turn, "snap": _snap(s),
                          "snapshot": game.snapshot(s) if args.full else None}, ensure_ascii=False))
        return

    res = game.handle(s, args.say)
    save.save(s, name)
    rec = {
        "turn": s.turn,
        "said": args.say,
        "reply": res.get("scene") or "",            # Ace's live narrated line
        "events": res.get("events") or [],
        "info": res.get("info"),
        "npc": res.get("npc"),
        "status": res.get("status"),
        "ending": res.get("ending"),
        "snap": _snap(s),
    }
    if args.full:
        rec["snapshot"] = game.snapshot(s)
    print(json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()
