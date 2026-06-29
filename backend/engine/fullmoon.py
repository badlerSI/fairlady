"""Full-moon set-pieces. Right now: a charming-spooky close encounter on Main Street in Virginia City
on a full-moon night — once per game. It sets the scene and leaves the next move to the player; the
improv DM handles whatever they try (floor it, roll the window down and talk to it, get out — bad idea).
"""
from __future__ import annotations

from engine import sky
from engine.state import GameState

WEREWOLF_POI = "virginia_city"


def _is_night(s: GameState) -> bool:
    h = s.clock.hour
    return h >= 19 or h < 6


def werewolf_on_arrival(s: GameState) -> list:
    """Fire once: full moon + night + Virginia City. Returns event lines (with Ace's line) and tags the
    arrival 'spooky' so the CRT tints it. Returns [] when the conditions aren't met."""
    if s.flags.get("werewolf_seen"):
        return []
    if getattr(s.place, "poi_id", None) != WEREWOLF_POI:
        return []
    if not _is_night(s) or not sky.is_full_moon(s):
        return []
    s.flags["werewolf_seen"] = True
    s.flags["arrival_tone"] = "spooky"
    s.flags["werewolf_active"] = True            # the improv DM reads this for context on the next line
    return [
        "· Virginia City after midnight, the Comstock moon swollen and full over the leaning "
        "boardwalks. Then something steps out of the dark between the old assay office and the "
        "saloon — too tall, wrong-jointed, hackles up the spine and two coins of yellow where the "
        "eyes should be. It looks at the car. It looks at you. The whole dead town holds its breath.",
        "ACE: …Okay. OKAY. I have seen a lot of weird desert and I have NEVER— it's between us and the "
        "road, ace. I've got a full tank and a redline and zero interest in finding out what it wants. "
        "Say the word and I'm gone — or do something brave and stupid, your call, but make it fast.",
    ]
