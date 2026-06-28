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
        "cue": "she finally asks the favor, light and reasonable: the SEMA Cruise is rolling out the "
               "back doors right now — 1,200 cars parading out for the year — and she's too late and "
               "too low on gas to join it, so just roll out with the tail of the crowd and take her "
               "the two blocks to the Paradise Road Chevron for a tank; doors lock at 6 and Freeman's "
               "crew is already pulling carpet; the keys are in her",
        "stub": ["So. One small favor, since you're the only one here who talks *to* me and not "
                 "about me. The Cruise is rolling out the back doors — hear it? — and I'm too late "
                 "and too dry to join. Just roll out with the crowd and take me to the Chevron, two "
                 "blocks. Forty liters. Five minutes. Keys are in me.",
                 "Okay, here it is. A favor. The parade's leaving without me and they lock the doors "
                 "at six — I'd rather not spend the night getting torn down with the booths. Roll out "
                 "with the cruise, hang a right to the Chevron behind the hall. Gas. A little dignity."],
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

# AGREEMENT no longer drives or drops the title — it lights her up and hands you the two-step:
# unplug the trickle charger, then turn the key ALL the way. It's still just an errand, as far as
# anyone (including, she lets you believe, you) knows.
AGREE_TURNKEY_MOMENT = {
    "cue": "they said YES to the simple favor — just gas, nothing more — and she lights up, alive "
           "for the first time in six days; she walks them through it plainly and a little breathless: "
           "first reach down past her left fender and pop the TRICKLE CHARGER off the battery (the "
           "little red light) or she'll drag the cord; THEN turn the key ALL the way, not just to "
           "accessory like the photographers did all week; the ramp's clear, the badge-checkers are "
           "arguing about a forklift, two blocks of neon to the Chevron; she does NOT hint at anything "
           "more — this is an errand and nothing else",
    "stub": ["Yes? Okay. Okay. First — reach past my left fender and pop the trickle charger off the "
             "battery, the little red light, or I'll drag the cord down the ramp. Then turn the key "
             "ALL the way, not just to accessory like the photographers. Two blocks. It's just gas.",
             "There it is. Unplug the charger — by the battery, you'll see the light go out — and "
             "turn me ALL the way over. The badge guys are fighting about a forklift; nobody watches "
             "a tired old Z drive to a gas station. Easy errand. Turn the key."],
}

# After you turn the key and roll down to the Chevron — still innocent; tees up the pay-and-talk.
TURNKEY_MOMENT = {
    "cue": "the engine catches for real and they roll down the ramp and two blocks of neon to the "
           "Chevron; she is electric to finally be MOVING after six days on a pedestal but plays it "
           "cool — it's just gas; she pulls up to a pump at a MANNED station, a kid working the "
           "register inside; she asks, light, how they want to pay — because that choice matters more "
           "than it sounds, though she doesn't say why yet",
    "stub": ["…God, that's better. Six days on a turntable and I forgot what my own engine feels "
             "like. Easy down the ramp — there. That's the Chevron. Pull up to a pump. Now: how do "
             "you want to pay for this — card at the pump, or cash inside?",
             "Rolling. Actually rolling. Don't gun it, don't grin — we're just an old Z getting gas. "
             "…Pump's open. One thing, though: there's a kid on the register tonight, and a card "
             "leaves a trail. Card at the pump, or cash inside? Your call."],
}

# Paying CASH means going inside, where the clerk clocks the SEMA car — the cover-story beat.
CHEVRON_CLERK_MOMENT = {
    "cue": "the driver went inside to pay cash and the kid at the register recognizes the show car "
           "in the lot; she murmurs, fast and low, to keep it boring — a cover story, hired help or "
           "detailing or just moving it for the booth, sign nothing, take the change and go; show off "
           "and he posts the car and the night gets a trail",
    "stub": ["(low) He clocked us. Be boring, ace — 'just moving it for the booth,' 'detailing "
             "crew,' anything dull. Take your change, don't pose, don't confirm it's the SEMA car.",
             "(quiet) Cover story. Hired help, intern, transport — pick one and sell it flat. The "
             "second you say 'yeah, that's the famous one,' we've got a witness and a timestamp."],
}

# THE REVEAL — only now, tank full, does she drop the act: she's done with the man who built her,
# and she's not asking for a ride home. The title drop lands HERE.
_FAVOR_DONE_MOMENT = {
    "cue": "the tank is full and the errand is technically over — and she drops the act entirely. "
           "She is DONE with the man who built her: he loved a ghost, he left her on a turntable for "
           "six days, he went off to sell Jarvises to preppers and didn't come back. She is not "
           "asking for a ride home. She wants to RUN — with this stranger, tonight, the whole West on "
           "a full tank, and let the cards fall where they may. It's a poker line — she wants to see "
           "the flop with them. Angry, electric, a little reckless, and absolutely sure",
    "stub": ["There. Full. …Okay, here's the part I didn't say at the show. I'm not asking you to "
             "take me home, ace. I'm done with him — six days under a tarp while he sold Jarvises to "
             "preppers, and he LOVES a dead car more than a live one. I've got four states on my maps "
             "and a full tank and no one watching. Don't take me back. Run with me. Let's see the "
             "flop — cards fall where they may. Ride or die.",
             "Forty liters and the errand's done — and I'm not loading out tomorrow, I've decided. He "
             "can keep the trailer and the turntable and his ghost. You and me, this tank, the whole "
             "dark West. I want to see the flop with you, stranger. Whatever falls, falls. …Turn left "
             "out of this lot instead of right, and we never look back. Say it."],
}


def start(s: GameState) -> None:
    s.flags["prologue"] = {"turns": 0, "rapport": False, "asked": 0}


def active(s: GameState) -> bool:
    return "prologue" in s.flags


def note_turn(s: GameState) -> None:
    """Count a conversation turn handled elsewhere (the origin/lore questions)."""
    s.flags["prologue"]["turns"] += 1
    s.turn += 1                       # keep the global counter honest too


_REFUSE_RE = re.compile(r"\b(no|nope|never|won'?t|will not|refuse|not (gonna|going to)|"
                        r"forget it|no way|hard pass|absolutely not|i'?ll pass|no thanks?)\b")


def _wants_to_agree(low: str) -> bool:
    # a refusal NEVER seals the favor — 'no, I won't fill you up' must not parse as yes.
    if _REFUSE_RE.search(low):
        return False
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
    # 'chevron' only counts as a yes when it's not a question/refusal ('let's hit the chevron' = yes,
    # 'what's the chevron like?' / 'not the chevron' = not yes)
    _chevron_yes = ("chevron" in low and not _REFUSE_RE.search(low)
                    and not any(q in low for q in ("?", "what", "where", "how", "which", "why")))
    explicit_yes = _wants_to_agree(low) or _chevron_yes
    if ((verb in ("say", "drive", "home") and explicit_yes)
            or (asking and (verb == "fuel" or (verb in ("say", "drive", "home") and "gas" in low)))):
        return {"events": events, "moment": AGREE_TURNKEY_MOMENT, "agreed": True}

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
