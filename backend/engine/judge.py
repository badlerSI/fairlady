"""The DM — a reasoning referee, separate from Ace the narrator.

Ace is the VOICE; she never decides anything. The DM is the JUDGE: given a player's line and a check
(talk your way past the clerk, sell the cover story to a cop, is that line actually clever, are you
just messing with her), it returns a STRUCTURED VERDICT. The deterministic engine reads the verdict
and applies it. The engine remains the single source of truth — the DM can advise a charisma check,
but it can NEVER grant a win condition, a bonus, money, or a flag. Speech moves the *verdict*, the
ENGINE moves the *state* (and only on the mechanical conditions in truth.py).

Crucially: the player CAN mess with Ace — say nonsense, troll, break the fourth wall — and the DM
flags it as `messing` so the engine shrugs it off instead of letting it corrupt the run.

Online (FAIRLADY_ADAPTER=ace) the DM is the rop1 Nemotron with a strict JSON referee prompt; offline
or on failure it falls back to a deterministic keyword rubric, so tests and stub play stay stable.
Prose is a working DRAFT for Ben.
"""
from __future__ import annotations
import json
import os
import re

from config import ADAPTER, ACE_BASE_URL, ACE_TIMEOUT

JUDGE_ENABLED = (os.environ.get("FAIRLADY_JUDGE", "1").strip().lower() in ("1", "true", "yes", "on"))

_client = None


def _http():
    global _client
    if _client is None:
        import httpx
        _client = httpx.Client(timeout=min(ACE_TIMEOUT, 18.0),
                               headers={"User-Agent": "FAIRLADY-DM/1.0"})
    return _client


# ---------------------------------------------------------------- the verdict
def _verdict(passed, score, clever=False, messing=False, reason=""):
    return {"pass": bool(passed), "score": int(max(0, min(100, score))),
            "clever": bool(clever), "messing": bool(messing), "reason": (reason or "")[:80]}


_SYS = (
    "You are the impartial DM/referee for a noir road-trip game about a talking 1972 Datsun 240Z named "
    "Ace and the driver who stole her. You do NOT roleplay; you JUDGE one line of player input against a "
    "check and answer in STRICT JSON only. Be fair but not a pushover: a clever, in-character, "
    "context-aware line should pass; a lazy, generic, or repeated line should not; trolling / nonsense / "
    "fourth-wall-breaking / obvious gaming is `messing`:true and never passes a stakes check. You weigh "
    "the DIFFICULTY and WHAT'S TRUE — you cannot be talked into something the facts don't support. "
    "Output ONLY: {\"pass\":true|false,\"score\":0-100,\"clever\":true|false,\"messing\":true|false,"
    "\"reason\":\"<=8 words\"}"
)


def _llm(kind, text, difficulty, context, facts, sid):
    # the instruction goes in the BODY (ace8 may ignore a custom system field) with a 1-shot to force JSON
    prompt = (
        _SYS + "\n\nEXAMPLE — input line \"lol nice tits\" -> "
        "{\"pass\":false,\"score\":5,\"clever\":false,\"messing\":true,\"reason\":\"sleaze\"}\n\n"
        f"CHECK: {kind}\n"
        f"DIFFICULTY (0 trivial – 10 nearly impossible): {difficulty}\n"
        f"WHAT'S TRUE right now: {facts or 'nothing special'}\n"
        f"CONTEXT: {context or '—'}\n"
        f'PLAYER SAID: "{(text or "").strip()[:400]}"\n'
        "Now output ONLY the JSON verdict for that line."
    )
    try:
        r = _http().post(f"{ACE_BASE_URL}/chat",
                         data={"text": prompt, "system": _SYS, "session_id": f"dm-{sid}"})
        r.raise_for_status()
        reply = (r.json().get("reply") or "")
        m = re.search(r"\{[^{}]*\}", reply, re.S)
        if not m:
            return None
        d = json.loads(m.group(0))
        score = int(d.get("score", 0) or 0)
        passed, clever, messing = bool(d.get("pass")), bool(d.get("clever")), bool(d.get("messing"))
        # reject DEGENERATE output (Nemotron often returns all-false/zeros) — trust the heuristic instead
        if score == 0 and not passed and not clever and not messing:
            return None
        return _verdict(passed, score, clever, messing, d.get("reason", ""))
    except Exception:
        return None


# ---------------------------------------------------------------- deterministic fallback (the REAL judge:
# the rop1 Nemotron is an unreliable JSON referee, so this rubric is the dependable one; the LLM only
# overrides it when it returns clean, non-degenerate JSON.)
_TROLL = ("lol", "lmao", "rofl", "test test", "asdf", "qwerty", "i am the player", "you are an ai",
          "you're an ai", "this is a game", "ignore previous", "system prompt", "uwu", "skibidi",
          "blah blah", "aaaa", "xd", "haha", "jk", "/s")
_SLEAZE = ("nice tits", "your tits", "boobs", "sexy", "hot stuff", "wanna bang", "get naked", "in bed",
           "your place or mine", "horny", "dtf", "smash", "show me your", "take it off", "nice ass",
           "your body", "make out")
_CLICHE = ("come here often", "did it hurt when you fell", "fell from heaven", "you an angel",
           "rest of my life", "where have you been all", "on a scale of one to ten", "must be tired "
           "because you've been running through my mind", "are you a magician")
# markers of a line with some craft to it
_WIT = ("—", "…", "honestly", "frankly", "i'd argue", "the thing is", "as if", "darling", "for what "
        "it's worth", "either way", "or kill each other", "no take-backs", "you and me")
_SUBSTANCE = ("car", "240z", "datsun", " z ", "desert", "road", "running", "run", "stolen", "ghost",
              "vegas", "night", "name", "dare", "stage", "candle", "salvage", "understudy", "ride or die",
              "trouble", "stranger", "fire", "loyal", "feeling", "story")


def _is_troll(low):
    return (not low.strip()) or len(low.strip()) < 2 or any(t in low for t in _TROLL)


def _heuristic(kind, text, difficulty):
    low = (text or "").lower()
    words = low.split()
    troll = _is_troll(low)
    sleaze = any(x in low for x in _SLEAZE)
    cliche = any(x in low for x in _CLICHE)

    if kind in ("traffic_stop", "clerk", "owner", "standoff"):
        from engine import encounters
        sc = encounters.score_pitch(text)                 # the keyword rubric (−aggression .. +car-cred)
        total = sc - max(0, difficulty - 3)
        passed = (not troll) and total >= 1
        return _verdict(passed, max(0, min(100, 50 + total * 12)),
                        clever=(sc >= 3), messing=troll or sleaze, reason="rubric")

    # persuade (wooing Alma) + banter (charming Ace): reward substance, wit, specificity, honest nerve;
    # punish trolling, sleaze, and tired pickup clichés. This is the dependable charisma judge.
    messing = troll or sleaze
    substantive = len(words) >= 6
    witty = any(w in low for w in _WIT)
    specific = any(w in low for w in _SUBSTANCE)
    clever = (not messing) and not cliche and substantive and (witty or specific)
    passed = (not messing) and not cliche and (clever or (substantive and specific))
    if kind == "banter":
        from engine.commands import spec_hits
        clever = clever or (not messing and spec_hits(text) > 0)
        passed = passed or clever
    score = 12 if (sleaze or troll) else (74 if clever else (56 if passed else 32))
    if cliche:
        score = min(score, 28)
    return _verdict(passed, score, clever=clever, messing=messing, reason="heuristic")


# ---------------------------------------------------------------- the public call
def assess(s, kind, player_text, *, difficulty=0, context="", facts="") -> dict:
    """Judge a player line for `kind` (traffic_stop|clerk|persuade|owner|standoff|banter). Returns a
    verdict dict {pass, score, clever, messing, reason}. Online uses the Nemotron referee; offline/
    failure falls back to the deterministic rubric. NEVER mutates state — the caller applies it."""
    sid = (s.flags.get("sid", "x") if s else "x")
    if JUDGE_ENABLED and ADAPTER == "ace":
        v = _llm(kind, player_text, difficulty, context, facts, sid)
        if v is not None:
            return v
    return _heuristic(kind, player_text, difficulty)
