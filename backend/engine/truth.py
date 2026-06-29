"""SOURCE OF TRUTH — the deterministic registry of every win/bonus and the MECHANICAL condition that
grants it. Nothing here is ever granted by conversation: Ace (the narrator) returns only text, the DM
(judge.py) returns only a verdict, and the engine sets these flags ONLY when the listed condition is
mechanically true. This module is the contract; test_engine.py fuzzes conversation against it.

If you add a win, a bonus, or a powerful flag, register it here AND make sure the only code path that
sets it checks the real condition — never a free-text `say`.
"""
from __future__ import annotations

# flag -> (one-line meaning, the mechanical requirement that may set it)
WIN_FLAGS = {
    "bought":          ("she's legally yours", "garage.go_legit after owner_buy with cash >= his price"),
    "no_heat":         ("the meter is retired", "bought / pardon / faked_death — a real legal/closed state"),
    "report_withdrawn":("the owner called off the law", "owner blessing: a winning owner_turn pitch"),
    "self_driving":    ("she drives herself", "upgrade_selfdrive at oakland_aisha, bought, bond>=STEADY, $15k"),
    "ending_key":      ("the run's outcome", "one of endings.WIN_KEYS/loss keys, set by an ending action"),
    "married_alma":    ("eloped with Alma", "the Vegas first-night hack: in Vegas, day<=1, knows her name"),
    "faked_death":     ("officially dead", "fake_death: owner_secret + spade hood + dark country + cash"),
    "desperado":       ("armed and dangerous", "the standoff disarm lucky-third, done set-up-right"),
    "gun":             ("you have the pistol", "the standoff disarm unlock"),
    "stinger_granted": ("the FIM-92 in the hatch", "arriving at area51_gate"),
    "owner_secret":    ("you know he wants her gone", "asking 'where painted' in a quiet place, or Fresno"),
}

# bonuses that move a meter — each has a bounded, mechanical source (never 'you said something nice')
BONUS_SOURCES = {
    "riz": "rapport spec-Q (+5 once), a JUDGED clever line (small, cooldowned), a survived stop, a "
           "race/show win, the owner blessing, a rizzbreaker — all engine-applied",
    "bond": "lore reveals, JUDGED/farmed conversation (diminishing per place), clean driving, buying "
            "her, peeling a respray — all engine-applied via bond.adjust",
    "cash": "claim (capped), ATM (<$10k), glovebox ($500 once), gambling, parts sale, bank job, the "
            "poker rizzbreaker — never from speech",
}

# flags a conversation turn (verb 'say'/'talk') must NEVER be able to set — the test asserts this
SPEECH_FORBIDDEN = ("bought", "no_heat", "report_withdrawn", "self_driving", "ending_key",
                    "married_alma", "faked_death", "desperado", "gun", "resprayed", "stinger_granted")


def speech_safe(before: dict, after: dict) -> bool:
    """True if a conversation turn changed none of the forbidden flags (and didn't end the game).
    Used by the fuzz test — the engine is the source of truth, speech only moves the verdict."""
    for f in SPEECH_FORBIDDEN:
        if bool(after.get(f)) and not bool(before.get(f)):
            return False
    return after.get("status", "playing") == before.get("status", "playing")
