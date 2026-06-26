"""BOND — how Ace feels about YOU. A relationship meter, modeled exactly like heat.py's honest
attributed ledger, but pointed at affection instead of notoriety.

Design (from the living-character pass — the engaging parts of companion AI, none of the predatory):
- NEVER A TIMER DRIP. Bond moves only on CHOSEN actions. Park her a week and she's exactly as warm
  as you left her — the opposite of an engagement-farming withdrawal engine.
- ATTRIBUTE EVERY DELTA. Each change logs a plain-language reason; she banks specific slights and
  calls them back later ("you only say that when you've done something"). Her memory is real engine
  truth, not a flattering hallucination — she can't invent a grudge she doesn't hold.
- TELEGRAPH, THEN ROLL. When she goes COLD she ARMS an anti-theft device — but you see it coming for
  many turns and can avert it (pay cash, sleep off-grid, kill the engine, make amends).
- WARMTH IS THE WIN. The good endings gate on it. You play toward a resolution, then leave clean.

She never shows as a bare number — only her voice (her register shifts by band), her behavior, and a
"how does she feel" report she gives you herself. All prose is a working DRAFT for Ben.
"""
from __future__ import annotations

from engine.state import GameState

START = 55.0                 # neutral-fond: she picked you first
LOG_KEEP = 16
GRUDGE_FADE_MI = 320.0       # minor slights age off with clean miles; deep betrayals never do


def band(b: float) -> str:
    if b >= 80:
        return "RIDE-OR-DIE"
    if b >= 55:
        return "STEADY"
    if b >= 30:
        return "COOL"
    return "COLD"


_GLOSS = {
    "RIDE-OR-DIE": "she'd cross any line for you",
    "STEADY": "she's fond of you — warm, dry, loyal",
    "COOL": "clipped now, fewer words, watching you",
    "COLD": "no pet names — and the anti-theft just armed",
}


def label(b: float) -> str:
    return f"{band(b)} — {_GLOSS[band(b)]}"


def armed(s: GameState) -> bool:
    """The anti-theft is live when she's COLD — unless she's legally yours (buying her retires it)."""
    return band(s.bond) == "COLD" and not s.flags.get("no_heat")


def adjust(s: GameState, delta: float, reason: str, kind: str = "warm") -> float:
    """The one true bond mutator: clamp, apply, and record the factor (cause + magnitude + odometer
    stamp). kind='deep' = a sticky betrayal that never ages off; 'warm'/'mark' fade with clean miles.
    A car she's been bought free of (no_heat) stops keeping score — she got what she wanted."""
    if s.flags.get("no_heat") and delta < 0:
        return s.bond                       # she's yours; she stops holding the road against you
    before = s.bond
    s.bond = round(max(0.0, min(100.0, s.bond + delta)), 1)
    real = round(s.bond - before, 1)
    if abs(real) >= 0.1 and reason:
        log = s.flags.setdefault("bond_log", [])
        log.append({"d": real, "r": reason, "k": kind, "day": s.day,
                    "odo": round(s.odometer_mi, 1)})
        del log[:-LOG_KEEP]
    s.flags["bond_worst"] = min(s.flags.get("bond_worst", round(START)), round(s.bond))
    return s.bond


# --------------------------------------------------------------- the "she remembers" buffer
def _live_grudges(s: GameState) -> list:
    """Negative marks still on her mind: deep betrayals never fade; minor slights age with miles."""
    odo = s.odometer_mi
    return [e for e in s.flags.get("bond_log", [])
            if e["d"] < 0 and (e["k"] == "deep" or (odo - e.get("odo", odo)) < GRUDGE_FADE_MI)]


def grudge(s: GameState):
    """The single worst unhealed thing you've done to her — she may bring it up by name."""
    marks = _live_grudges(s)
    return min(marks, key=lambda e: e["d"])["r"] if marks else None


def kindness(s: GameState):
    """The warmest thing you've done — she remembers the good too."""
    warms = [e for e in s.flags.get("bond_log", []) if e["d"] > 0]
    return max(warms, key=lambda e: e["d"])["r"] if warms else None


def repair(s: GameState, amount: float, reason: str) -> None:
    """A matching repair (sincere apology, buying a part back, enough warm beats) heals her — and
    drops the freshest slight out of the grudge pool so she stops bringing it up."""
    adjust(s, amount, reason, "warm")
    log = s.flags.get("bond_log", [])
    for i in range(len(log) - 1, -1, -1):
        if log[i]["d"] < 0 and log[i]["k"] != "deep":
            log[i]["k"] = "healed"
            break


# --------------------------------------------------------------- the report (her, not a stat bar)
def dashboard(s: GameState) -> str:
    if s.flags.get("no_heat"):
        return ("HOW SHE FEELS  ·  YOURS\n"
                "  She's titled in your name and done keeping score. Whatever's between you now is "
                "just the two of you, off the books.")
    lines = [f"HOW SHE FEELS  ·  {band(s.bond)}", f"  {_GLOSS[band(s.bond)]}"]
    helps, hurts = {}, {}
    for e in s.flags.get("bond_log", []):
        (helps if e["d"] > 0 else hurts).setdefault(e["r"], 0.0)
        (helps if e["d"] > 0 else hurts)[e["r"]] += e["d"]
    if helps:
        lines.append("  WHAT SHE LIKES:")
        for r, _ in sorted(helps.items(), key=lambda kv: -kv[1])[:4]:
            lines.append(f"    ♥  {r}")
    live = {e["r"] for e in _live_grudges(s)}
    if hurts:
        lines.append("  WHAT SHE HASN'T FORGOTTEN:")
        for r, _ in sorted(hurts.items(), key=lambda kv: kv[1])[:4]:
            tag = "" if r in live else "  (fading)"
            lines.append(f"    ✗  {r}{tag}")
    if armed(s):
        lines += ["  ⚠ SHE'S COLD — the anti-theft is ARMED. Sleep near open WiFi and she phones",
                  "    home while you sleep. Defuse: pay cash + sleep OFF-GRID (camp / a dead two-lane),",
                  "    'kill the engine' at motels, or win her back ('compliment her', drive her right)."]
    elif band(s.bond) == "COOL":
        lines.append("  She's cooling. A sincere word, a good song, the right question — before she goes cold.")
    else:
        lines.append("  Keep her this way: ask about her, drive her clean, don't bring strangers home.")
    return "\n".join(lines)
