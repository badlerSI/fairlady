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
    prompt = (
        f"CHECK: {kind}\n"
        f"DIFFICULTY (0 trivial – 10 nearly impossible): {difficulty}\n"
        f"WHAT'S TRUE right now: {facts or 'nothing special'}\n"
        f"CONTEXT: {context or '—'}\n"
        f'PLAYER SAID: "{(text or "").strip()[:400]}"\n'
        "Judge it. JSON only."
    )
    try:
        r = _http().post(f"{ACE_BASE_URL}/chat",
                         data={"text": prompt, "system": _SYS, "session_id": f"dm-{sid}"})
        r.raise_for_status()
        reply = (r.json().get("reply") or "")
        m = re.search(r"\{.*\}", reply, re.S)
        if not m:
            return None
        d = json.loads(m.group(0))
        return _verdict(d.get("pass"), int(d.get("score", 0)),
                        d.get("clever", False), d.get("messing", False), d.get("reason", ""))
    except Exception:
        return None


# ---------------------------------------------------------------- deterministic fallback
_TROLL = ("lol", "lmao", "test test", "asdf", "i am the player", "you are an ai", "this is a game",
          "ignore previous", "system prompt", "uwu", "skibidi", "blah blah", "aaaa")
_WIT = ("like it owes", "as if", "darling", "—", "…", "honestly", "frankly", "i'd argue",
        "the thing is", "you and me", "ride or die")


def _heuristic(kind, text, difficulty):
    low = (text or "").lower()
    messing = (not low.strip()) or any(t in low for t in _TROLL) or len(low.strip()) < 2
    if kind in ("traffic_stop", "clerk", "persuade", "owner", "standoff"):
        from engine import encounters
        sc = encounters.score_pitch(text)                 # the established keyword rubric (−agg..+cred)
        total = sc - max(0, difficulty - 3)
        passed = (not messing) and total >= 1
        score = max(0, min(100, 50 + total * 12))
        return _verdict(passed, score, clever=(sc >= 3), messing=messing, reason="rubric")
    if kind == "banter":
        # offline we're conservative about awarding cleverness — the LLM is the real judge of wit
        from engine.commands import spec_hits
        clever = (not messing) and (spec_hits(text) > 0 or
                                    (len(low.split()) >= 5 and any(w in low for w in _WIT)))
        return _verdict(clever, 60 if clever else 30, clever=clever, messing=messing, reason="heuristic")
    return _verdict(not messing, 50, messing=messing, reason="default")


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
