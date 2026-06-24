"""Deterministic intent parser. The LLM never decides what happens — this does.
Maps free-ish player text to (verb, args). Anything unrecognized becomes conversation."""
from __future__ import annotations
import re
from typing import Tuple

_NUM = r"(\d+(?:\.\d+)?)"


def parse(raw: str) -> Tuple[str, dict]:
    t = (raw or "").strip()
    low = t.lower()
    if not low:
        return ("look", {})

    if low in ("help", "?", "commands", "h"):
        return ("help", {})
    if low in ("new", "new game", "restart", "reset"):
        return ("new", {})
    if low in ("save",):
        return ("save", {})
    if low.startswith("load"):
        return ("load", {"name": low[4:].strip() or "autosave"})

    if low in ("look", "l", "status", "state", "look around", "hud"):
        return ("look", {})

    # rewind to the last checkpoint (the Edge-of-Tomorrow escape — must precede the drive check,
    # since "go back" would otherwise parse as a drive)
    if low in ("rewind", "go back", "rewind it", "take it back", "loop", "loop it",
               "try again", "try that again", "run it back"):
        return ("rewind", {})

    # "where can we get to on one tank?" — the range question, answered with real math.
    # "tank" overrides the service words ("one tank of gas" is range, "where can we get gas" is map).
    service_q = any(w in low for w in ("gas", "fuel", "pump", "motel", "lodg", "stay", "sleep"))
    if (("tank" in low and any(w in low for w in ("where", "far", "get to", "reach", "make it", "go on")))
            or (not service_q
                and (low.startswith(("how far", "what can we reach", "where can we get",
                                     "where can we go", "where can you take me"))
                     or low in ("range", "reachable")))):
        return ("range", {"full": "full" in low or "one tank" in low})

    # ask about her origins — Life of a Show Car (must precede the generic "where..." map check)
    if any(p in low for p in ("born", "where are you from", "where you from", "where're you from")):
        return ("origin", {"which": "born"})
    if any(p in low for p in ("grew up", "grow up", "came of age", "come of age", "raised",
                              "where were you built", "where you built", "who built you", "who made you")):
        return ("origin", {"which": "grew"})
    if any(p in low for p in ("previous owner", "last owner", "old owner", "who owned you",
                              "who had you", "your owner", "your past", "before you", "owned you before")):
        return ("origin", {"which": "owner"})

    # take her home (her home is the Oakland garage; or name a place in NV/CA/AZ/UT)
    if low.startswith(("home is ", "set home ", "my home is ", "home in ", "home's ")):
        dest = re.sub(r"^(?:home is|set home|my home is|home in|home's)\s+", "", low).strip(" .")
        return ("home", {"dest": dest})
    if any(p in low for p in ("driving you home", "driving her home", "taking you home", "taking her home",
                              "drive you home", "drive her home", "drive me home", "drive us home",
                              "take you home", "take her home",
                              "take me home", "let's go home", "lets go home", "head home", "get you home")):
        m = re.search(r"home (?:to|in) (.+)$", low)
        return ("home", {"dest": m.group(1).strip(" .")} if m else {})
    if low in ("home", "drive home", "go home", "homeward", "take us home"):
        return ("home", {})

    if low.startswith(("map", "nearby", "where")):
        svc = None
        if "gas" in low or "fuel" in low or "pump" in low:
            svc = "gas"
        elif "sleep" in low or "motel" in low or "lodg" in low or "stay" in low:
            svc = "lodging"
        return ("map", {"service": svc})

    if low in ("tow", "call a tow", "call tow", "get towed", "tow truck"):
        return ("tow", {})

    # the gun (Desperado): go for an armed clerk's pistol, or pull your own once you have it
    if low in ("disarm", "disarm him", "grab the gun", "go for the gun", "grab for the gun",
               "go for it", "take the gun", "take his gun", "lunge", "lunge for it",
               "make a grab", "grab it", "jump him", "wrestle the gun"):
        return ("disarm", {})
    if low in ("draw", "pull the gun", "pull my gun", "pull the piece", "point the gun",
               "draw on him", "draw the gun", "pull iron", "pull the trigger", "show the gun"):
        return ("draw", {})

    # payment method
    if low in ("pay cash", "use cash", "cash", "pay with cash"):
        return ("pay", {"method": "cash"})
    if low in ("pay card", "use card", "card", "pay with card", "credit"):
        return ("pay", {"method": "card"})

    # fuel
    if _is_fuel(low):
        args = {}
        if "fill" in low or "top" in low:
            args["fill"] = True
        m = re.search(r"\$\s*" + _NUM, low) or re.search(_NUM + r"\s*(?:dollars|bucks|usd)", low)
        if m:
            args["dollars"] = float(m.group(1))
        m = re.search(_NUM + r"\s*(?:gal|gallon)", low)
        if m:
            args["gallons"] = float(m.group(1))
        m = re.search(_NUM + r"\s*(?:l\b|liter|litre)", low)
        if m:
            args["liters"] = float(m.group(1))
        if "cash" in low:
            args["prefer"] = "cash"
        elif "card" in low or "credit" in low:
            args["prefer"] = "card"
        if not any(k in args for k in ("fill", "dollars", "gallons", "liters")):
            args["fill"] = True
        return ("fuel", args)

    # sleep
    if _is_sleep(low):
        args = {}
        if "rough" in low or "pull over" in low or "in the car" in low or "in the seat" in low:
            args["rough"] = True
        for k in ("camp", "motel", "lodge"):
            if k in low:
                args["kind"] = k
        if "cash" in low:
            args["prefer"] = "cash"
        elif "card" in low:
            args["prefer"] = "card"
        return ("sleep", args)

    # talk to the locals (an encounter NPC)
    if _is_talk(low):
        return ("talk", {})

    # drive
    dest = _drive_dest(low)
    if dest is not None:
        push = any(w in low for w in ("fast", "floor", "push", "hard", "haul", "book it", "step on"))
        return ("drive", {"dest": dest, "push": push})

    # otherwise: talk to FAIRLADY
    return ("say", {"text": t})


# Her build sheet, as conversation. A "coherent question about her build or specs" warms her
# up fast — gearheads get the 3-turn favor, civilians get the 5. Also used by the narrator stub
# and the traffic-stop rubric (car-cred plays well with a certain kind of cop).
# Single words match on WORD BOUNDARIES — "she's special" is not spec talk, "respect" is not
# spec talk, and a witness with a "camera" earns no cam credit. Phrases match as substrings.
_SPEC_WORD_RE = re.compile(
    r"\b(torque|horsepower|hp|engine|motor|displacement|compression|carbs?|webers?|mikunis?|"
    r"cams?|strokers?|stroked|l24|l26|l28|inline|suspension|coilovers?|brakes?|gearbox|"
    r"transmission|diffs?|lsd|redline|wheelbase|specs?|"
    r"lb[-/ ]?ft|ft[-/ ]?lbs?|foot[- ]?pounds?|0-60|5[- ]?speed)\b")
_SPEC_PHRASES = (
    "straight six", "straight-six", "five speed", "five-speed", "zero to sixty",
    "quarter mile", "curb weight", "your build", "the build", "what's under", "whats under",
    "under the hood",
)
_INTERROGATIVE = ("what", "how", "tell me", "talk me through", "walk me through",
                  "is it", "does", "do you", "you got", "give me", "?")


def spec_hits(text: str) -> int:
    """Count distinct build-sheet references, boundary-safe."""
    low = (text or "").lower()
    return len(set(_SPEC_WORD_RE.findall(low))) + sum(1 for p in _SPEC_PHRASES if p in low)


def is_spec_question(text: str) -> bool:
    low = (text or "").lower()
    return spec_hits(low) > 0 and any(q in low for q in _INTERROGATIVE)


def _is_fuel(low: str) -> bool:
    return (low.startswith(("fuel", "gas", "fill", "pump", "buy gas", "buy fuel", "refuel", "top"))
            or low in ("fill up", "fill her up", "fill it up", "gas up", "fuel up"))


def _is_sleep(low: str) -> bool:
    return low.startswith(("sleep", "rest", "motel", "camp", "lodge", "stay", "check in",
                           "check-in", "bed", "crash", "pull over", "turn in", "good night"))


def _is_talk(low: str) -> bool:
    if low.startswith(("talk to", "speak to", "speak with", "talk with")):
        return True
    return low in ("talk", "speak", "greet", "say hi", "say hello", "hello", "hi",
                   "talk to them", "talk to her", "talk to the locals", "introduce yourself")


_DRIVE_PREFIX = re.compile(
    r"^(?:drive|go|head|take me|navigate|route|let's go|lets go|set off for|"
    r"set out for|make for|aim for|point (?:me|us) (?:at|to|toward))\b", re.I)


def _drive_dest(low: str) -> str | None:
    m = _DRIVE_PREFIX.match(low)
    if not m:
        return None
    rest = low[m.end():].strip()
    rest = re.sub(r"^(?:me|us|her)\s+", "", rest)      # "drive me to zion" → "to zion"
    rest = re.sub(r"^(?:to|for|toward|towards|at|over to|out to|up to|down to)\s+", "", rest)
    rest = re.sub(r"\b(fast|hard|quick(?:ly)?|floor it|push it|step on it)\b", "", rest).strip(" .,")
    return rest or None
