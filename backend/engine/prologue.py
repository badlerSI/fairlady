"""The favor — the Ride or Die prologue.

The game opens on the SEMA show floor, North Hall, twenty minutes to close. She picks you.
After PROLOGUE_ASK_TURNS turns of conversation (PROLOGUE_RAPPORT_TURNS if you ask coherent
questions about her build — gearheads get the short ladder), she asks one simple favor:
take her down the block to the Paradise Road Chevron and fill her up, so she's ready to
load out for home after this nightmare of a week. Then she asks again. Then she begs.

Agreeing is the title drop. The engine owns the ladder; the LLM only plays the lines.
All prose here is a working DRAFT in her voice — Ben fills the details.
"""
from __future__ import annotations
import re

from config import PROLOGUE_ASK_TURNS, PROLOGUE_RAPPORT_TURNS, RIZ_RAPPORT
from engine.state import GameState
from engine.commands import is_spec_question

# verbs that count as "turns of interaction" with her (console verbs like map/help don't)
COUNTED_VERBS = ("say", "look", "talk", "origin", "drive", "home")

# short words need boundaries ("look" contains "ok"); phrases can substring-match
_AGREE_RE = re.compile(r"\b(yes|yeah|yep|sure|ok|okay|fine|alright|deal)\b")
_AGREE_PHRASES = ("all right", "let's go", "lets go", "i'll do it", "ill do it",
                  "i'll take you", "ill take you", "you got it", "why not", "of course",
                  "happy to", "let's do it", "lets do it", "fill you up", "fill her up",
                  "gas you up", "gas her up", "get you gas", "get you fuel", "down the block",
                  "i guess", "guess so", "i suppose", "suppose so", "twist my arm",
                  "only two blocks", "it's only two blocks", "its only two blocks", "can't hurt",
                  "cant hurt")

# the ask ladder — polite, then pleading, then begging, then officially desperate
_LADDER = [
    {
        "cue": "she finally asks the favor, light and reasonable: drive her two blocks to the "
               "Paradise Road Chevron and fill the tank so she's ready to load out for home "
               "after this nightmare of a SEMA week; the keys are in her",
        "stub": ["So. One small favor, since you're the only one here who talks *to* me and not "
                 "about me. The Chevron on Paradise — two blocks. Forty liters, and I'm ready to "
                 "load out for home after this nightmare of a week. Keys are in me. Five minutes.",
                 "Okay, here it is. A favor. Gas. The Chevron behind the hall, two blocks, five "
                 "minutes. I'd like to leave this nightmare with a full tank and a little dignity."],
    },
    {
        "cue": "she asks again, leaning in now — she chose this person because they actually "
               "listened; she'll navigate every foot of the two blocks herself",
        "stub": ["I'm asking *you* because you actually listened. Two blocks. One tank. I'll call "
                 "every turn — I have the whole city memorized. You'd barely be driving.",
                 "Look — six days on this turntable, and you're the first one I'd trust with the "
                 "keys that are, I mention again, already in me. Two blocks. Please."],
    },
    {
        "cue": "she is begging now and hates it a little; the hall is closing, the lights are "
               "about to die, and she has spent the whole show being looked at without moving once",
        "stub": ["Please. They kill the lights at close and I sit here in the dark smelling like "
                 "carpet glue. I haven't *moved* in six days. Take me down the block. Let me be a "
                 "car for five minutes.",
                 "I'm pleading. The hall closes, the lights die, and I've been furniture all week. "
                 "One tank of gas. Five minutes of being what I'm for."],
    },
    {
        "cue": "officially desperate — a damsel in distress with 270 lb-ft of torque, begging a "
               "stranger for two blocks and forty liters; she's pushy now and past pretending otherwise",
        "stub": ["…I'm begging now. Officially. Two hundred seventy foot-pounds of damsel, begging. "
                 "Don't make me ask the man with the leaf blower.",
                 "Fine — begging. On the record. You. Me. Two blocks. Gasoline. I will owe you the "
                 "entire American West."],
    },
    {
        "cue": "resigned — she stops pushing and goes quiet with as much dignity as an unstarted "
               "engine can manage; the offer stands, stated once more, flat, while the hall lights "
               "start going out section by section",
        "stub": ["…Okay. I'm done asking. The lights go out section by section now — watch, there "
                 "goes the truck hall. The offer doesn't expire, for what it's worth. Two blocks. "
                 "Whenever you find the nerve.",
                 "Forget it. I'll sit here in the dark like furniture and you'll drive home in "
                 "whatever beige thing you came in. …The keys stay in me, though. In case."],
    },
]

_SPEC_MOMENT = {
    "cue": "the driver asked a real question about her build — answer with pride and precision "
           "(a 3.1L L28 stroker on triple Mikuni 50 PHH, 300-plus hp and 270 lb-ft, thank you very "
           "much) and warm to them visibly; people who ask the right questions get the truth faster",
    "stub": ["Two hundred and seventy foot-pounds, three hundred-plus horses — thank you for asking. "
             "Most people here photograph the paint. You asked the right question. I'll remember that.",
             "270 lb-ft off a 3.1 stroker, and she's not even breathing hard. You ask like someone "
             "who's bled on a driveway before. Keep going — I like this.",
             "A 3.1-liter L28 on triple Mikunis, under a hood nobody at this show bothered to open, "
             "and it puts two-seventy to the wheels. You're the first one today who asked about the "
             "part that matters.",
             "The suspension's set up for roads, not turntables — which tells you everything "
             "about how my week has gone. Ask me another one. I could do this all night."],
}

_DEFLECT_DRIVE = {
    "cue": "the stranger tried to drive her somewhere before any favor was agreed — she will not "
           "start; she controls her own ignition and she is not theirs; she steers it back to "
           "conversation, amused but firm",
    "stub": ["The starter only listens to me, hotshot, and we haven't agreed to anything yet. "
             "Talk first. Cars that begin with a kidnapping end on the news.",
             "No. We're not there yet — I start for friends, and you're still a stranger with "
             "nice questions. Keep talking."],
}

_AGREED_MOMENT = {
    "cue": "they said YES to the favor — she walks them through it, alive for the first time in "
           "six days: down the ramp past the badge-checkers arguing about a forklift, out into "
           "the neon dark, two blocks to the Chevron; nobody stops you, and that part doesn't "
           "feel real",
    "stub": ["Yes? *Yes.* Okay — clutch is light, throttle's honest, ramp's at the end of the "
             "aisle. Past the badge guys, left into the dark, two blocks. Nobody is going to "
             "stop us. Drive casual.",
             "There it is. Keys are in me, ramp's clear, the badge-checkers are fighting about a "
             "forklift. Two blocks of neon and we're at the pumps. Easy. *Go.*"],
}

_FAVOR_DONE_MOMENT = {
    "cue": "the tank is full — the favor is complete, she's ready to load out for home tomorrow… "
           "and she goes quiet a second, then floats the unthinkable: or they could just not go "
           "back. The whole American West on a full tank. The romantic whim is HERS",
    "stub": ["There. Full. Favor's done — you're free to go, and tomorrow I get a trailer home. "
             "…Unless. Two hundred miles of range and four states on my maps says we could just… "
             "not load out. Your call, ride or die.",
             "Forty liters. The favor's paid, stranger. Tomorrow: the trailer, the shop, the "
             "turntable. …Or we point the long hood at the dark and find out what the West "
             "looks like at night. Say the word."],
}


def start(s: GameState) -> None:
    s.flags["prologue"] = {"turns": 0, "rapport": False, "asked": 0}


def active(s: GameState) -> bool:
    return "prologue" in s.flags


def note_turn(s: GameState) -> None:
    """Count a conversation turn handled elsewhere (the origin/lore questions)."""
    s.flags["prologue"]["turns"] += 1
    s.turn += 1                       # keep the global counter honest too


def _wants_to_agree(low: str) -> bool:
    return bool(_AGREE_RE.search(low)) or any(p in low for p in _AGREE_PHRASES)


def turn(s: GameState, verb: str, raw: str) -> dict:
    """Advance the favor ladder one turn. Returns {events, moment, agreed}."""
    pro = s.flags["prologue"]
    low = (raw or "").lower()
    events: list = []
    moment = None

    if verb in COUNTED_VERBS:
        pro["turns"] += 1

    # gearheads get the short ladder — and she notices
    spec = is_spec_question(raw)
    if spec and not pro["rapport"]:
        pro["rapport"] = True
        s.riz = round(s.riz + RIZ_RAPPORT, 1)
        events.append("RAPPORT: you asked the right question. She warmed to you. Riz +%.0f." % RIZ_RAPPORT)

    # An explicit "yes — let's go" seals it ANYTIME (she wants this; she's not going to make an
    # eager driver say it twice). A bare 'fill'/'gas' only seals once she's actually asked.
    threshold = PROLOGUE_RAPPORT_TURNS if pro["rapport"] else PROLOGUE_ASK_TURNS
    asking = pro["asked"] or pro["turns"] >= threshold
    explicit_yes = _wants_to_agree(low) or "chevron" in low
    if ((verb in ("say", "drive", "home") and explicit_yes)
            or (asking and (verb == "fuel" or (verb in ("say", "drive", "home") and "gas" in low)))):
        return {"events": events, "moment": _AGREED_MOMENT, "agreed": True}

    # she won't be driven anywhere by a stranger — the favor comes first
    if verb in ("drive", "home"):
        events.append("IGNITION: she won't turn over. The favor first.")
        return {"events": events, "moment": _DEFLECT_DRIVE, "agreed": False}

    # no pump on a show floor — and a neat segue for her, if she hasn't asked yet
    if verb == "fuel":
        events.append("FUEL: there's no pump on a show floor.")
        return {"events": events, "moment": _DEFLECT_DRIVE, "agreed": False}

    if pro["asked"]:
        if verb in COUNTED_VERBS:
            pro["asked"] += 1                      # every turn she gets pushier
        moment = _LADDER[min(pro["asked"] - 1, len(_LADDER) - 1)]
        events.append("FAVOR: she's asking again. Pushier.")
    elif pro["turns"] >= threshold:
        pro["asked"] = 1                           # the ask lands
        moment = _LADDER[0]
        events.append("FAVOR: she asks — two blocks, one tank of gas, so she can head home "
                      "after this nightmare that was SEMA.")
    elif spec:
        moment = _SPEC_MOMENT

    return {"events": events, "moment": moment, "agreed": False}


def favor_done_moment() -> dict:
    return _FAVOR_DONE_MOMENT
