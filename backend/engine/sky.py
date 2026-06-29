"""Celestial — a deterministic moon phase from the in-game date.

The clock starts 2025-11-07 and the trip runs to NYE. Within that window the real ephemeris has the
moon FULL on the night of Dec 4-5 2025 (the "Cold Moon", game day 28-29), NEW on Nov 19-20 (day
13-14) and Dec 19-20 (day 43-44). This module reproduces that from `s.clock.date()` alone so the
moon in the sky, the full-moon night drive, and the Virginia City werewolf all read one source of
truth. No I/O, no randomness — same date always gives the same moon.
"""
from __future__ import annotations
import math
from datetime import date, datetime

SYNODIC = 29.530588853                       # mean lunar month, days
# a known reference new moon (2000-01-06 18:14 UTC). Day-resolution is plenty for a phased sprite.
_EPOCH = datetime(2000, 1, 6, 18, 14)


def _as_date(d) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    # a GameState — use its clock
    return d.clock.date()


def moon_age(d) -> float:
    """Days since the last new moon, 0..29.53 (0 = new, ~14.77 = full)."""
    dt = _as_date(d)
    days = (datetime(dt.year, dt.month, dt.day, 12) - _EPOCH).total_seconds() / 86400.0
    return days % SYNODIC


def phase01(d) -> float:
    """0 = new, 0.5 = full, 1 = new again — the value the procedural moon sprite carves with."""
    return moon_age(d) / SYNODIC


def illum(d) -> float:
    """Illuminated fraction 0..1 (0 new, 1 full)."""
    return (1.0 - math.cos(2.0 * math.pi * moon_age(d) / SYNODIC)) / 2.0


def is_full_moon(d) -> bool:
    """The night(s) the moon reads genuinely FULL — the trip's headline full moon is the Dec 4-5 2025
    Cold Moon (illum .99/1.0). The Nov 7 start sits at ~.967 (a waning gibbous two nights after the
    Beaver Moon), so the threshold is set above it to keep the full-moon beats a singular event."""
    return illum(d) >= 0.985


def is_new_moon(d) -> bool:
    return illum(d) <= 0.02


def waxing(d) -> bool:
    return moon_age(d) < SYNODIC / 2.0


def phase_name(d) -> str:
    a = moon_age(d)
    if a < 1.0 or a >= SYNODIC - 1.0:
        return "new moon"
    if is_full_moon(d):
        return "full moon"
    q = SYNODIC / 4.0
    if a < q - 1.0:
        return "waxing crescent"
    if a < q + 1.0:
        return "first quarter"
    if a < 2 * q - 1.0:
        return "waxing gibbous"
    if a < 2 * q + 1.0:
        return "full moon"
    if a < 3 * q - 1.0:
        return "waning gibbous"
    if a < 3 * q + 1.0:
        return "last quarter"
    return "waning crescent"


def snapshot(s) -> dict:
    """The moon fields the frontend reads (one source of truth — don't parse the time string)."""
    d = s.clock.date()
    return {
        "moon_phase": round(phase01(d), 4),     # 0..1, 0.5 = full — the sprite carve value
        "moon_illum": round(illum(d), 3),
        "is_full_moon": is_full_moon(d),
        "moon_name": phase_name(d),
    }
