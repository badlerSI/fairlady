"""Talk-your-way-out encounters: the traffic stop and the owner.

You're driving an unregistered SEMA show car that talks, and you forgot your wallet —
it's in a drawer back at the North Hall. When the lights come on, the only tool you have
is your mouth. The engine keeps its one sacred rule: a deterministic rubric scores what
you actually said (calm, the truthiest cover story, gearhead cred), seeded dice settle the
margins, and the LLM only narrates. Riz is the style ledger — earned here, spent nowhere,
remembered across rewinds.

The owner is the endgame variant: the man who built her works the card trail and comes
looking. He knows true love with cars. What you two have is it — if you can say so.
All prose is a working DRAFT — Ben fills the details.
"""
from __future__ import annotations
import random

from config import (
    STOP_FINE, STOP_HEAT_WAVE, STOP_HEAT_TICKET, STOP_HEAT_BAD,
    RIZ_STOP_WAVE, RIZ_STOP_TICKET, RIZ_OWNER_BLESSING,
    OWNER_DEADLINE_DAYS,
)
from engine.state import GameState
from engine.commands import spec_hits

ROUNDS = 2          # exchanges before the verdict

# ---------------------------------------------------------------- the rubric
_CALM = ("officer", "sir", "ma'am", "maam", "evening", "good evening", "sorry", "apolog",
         "of course", "absolutely", "appreciate", "respect", "no problem", "happy to",
         "my mistake", "you're right", "youre right")
_STORY = ("sema", "show car", "show floor", "the show", "display", "demo", "exhibit",
          "press", "promo", "transport", "delivering", "load out", "loading out",
          "manufacturer plate", "dealer plate", "shakedown")
_HONEST = ("forgot", "left it", "wallet", "back at the hall", "at the show", "in a drawer")
_FLEE = ("floor it", "gun it", "punch it", "drive away", "lose him", "lose them",
         "run for it", "go go", "outrun")
_AGGRO = ("shut up", "screw you", "screw off", "fuck", "pig", "fascist", "make me",
          "you can't", "you cant prove")
_DUMB = ("stole", "stolen", "not mine", "not my car", "borrowed", "took it", "i took her")

_LOVE = ("love", "care", "promise", "keep her safe", "she's safe", "shes safe", "she chose",
         "her idea", "she asked", "the favor", "ride or die", "i'd die", "id die",
         "she picked me", "won't let anything", "wont let anything")
_MAYUMI = ("mayumi", "580", "i-580", "burned", "the fire", "her name")
_RETURN = ("take her back", "have her back", "give her back", "she's yours", "shes yours",
           "return her")


import re as _re


def _hits(low: str, tokens) -> int:
    """Phrases match as substrings; single words on word boundaries ('scared' isn't 'care')."""
    n = 0
    for t in tokens:
        if " " in t or "'" in t:
            n += 1 if t in low else 0
        else:
            n += 1 if _re.search(rf"\b{_re.escape(t)}\b", low) else 0
    return n


def score_pitch(text: str) -> int:
    """Deterministic score for one thing you said to the law. The LLM never votes."""
    low = (text or "").lower()
    if len(low.split()) < 2:
        return 0                                   # "um" is not a pitch
    sc = 0
    sc += 2 * min(2, _hits(low, _CALM))            # courtesy, capped — don't grovel
    sc += 2 * min(2, _hits(low, _STORY))           # the truthiest cover: it IS a SEMA car
    sc += 2 * min(1, spec_hits(low))               # gearhead solidarity plays well out here
    sc += 1 * min(1, _hits(low, _HONEST))          # honest about the wallet beats a fake name
    sc -= 3 * _hits(low, _AGGRO)
    sc -= 2 * _hits(low, _DUMB)
    return sc


def score_owner_pitch(s: GameState, text: str) -> int:
    low = (text or "").lower()
    if len(low.split()) < 2:
        return 0
    sc = 0
    sc += 2 * min(2, _hits(low, _LOVE))            # what you two have
    sc += 2 * min(1, spec_hits(low))               # you know what he built
    if s.flags.get("knows_mayumi") or s.flags.get("knows_name"):
        sc += 3 * min(1, _hits(low, _MAYUMI))      # the deep cut — say her name
    sc -= 1 * min(1, _hits(low, _RETURN))          # offering her back means you don't get it
    sc -= 3 * _hits(low, _AGGRO)
    return sc


def _rng(s: GameState) -> random.Random:
    return random.Random(s.seed * 7919 + s.turn * 104729 + 13)


# ---------------------------------------------------------------- traffic stop
def start_stop(s: GameState, kind: str = "plate") -> list:
    """kind: 'plate' (he ran you), 'roadblock' (you drove into it), 'taillight' (bad luck)."""
    s.flags["stop"] = {"kind": kind, "round": 0, "score": -2 if kind == "roadblock" else 0}
    opener = {
        "plate": "LAW: lights in the mirror. You're on the shoulder, engine ticking. "
                 "'Evening. License and registration.' Your pockets: a phone, $40 — no wallet. "
                 "It's in a drawer back at the North Hall.",
        "roadblock": "LAW: the roadblock you couldn't dodge. Flashlight on the dash, then on you. "
                     "'License and registration.' The wallet is in a drawer back at the North Hall.",
        "taillight": "LAW: a cruiser eases in behind you over a taillight. 'License and "
                     "registration.' Which would be in your wallet. Back at the North Hall.",
    }[kind]
    return [opener, "LAW: talk your way out — say it like you mean it. (She stays quiet: a car "
                    "that talks is the one thing he can't unsee.)"]


# Her coaching when a stop opens mid-drive (the roadblock path has no drama cue of its own)
WHISPER_MOMENT = {
    "cue": "the law has them stopped — she whispers almost without moving air: she'll be the "
           "quietest car in Nevada, the talking is all theirs now; courtesy, the show, the "
           "build; the wallet is in a drawer back at the North Hall",
    "stub": ["(whisper) Lights. I'm furniture. You talk — courtesy, the show, the build. You "
             "forgot your wallet, not your nerve.",
             "(whisper) Easy. I go silent, you go charming. SEMA car, load-out run, wallet's "
             "at the hall. Sell it."],
}


def stop_active(s: GameState) -> bool:
    return "stop" in s.flags


def stop_turn(s: GameState, text: str) -> dict:
    """One exchange with the officer. Returns {events, moment, done}."""
    st = s.flags["stop"]
    st["round"] += 1
    st["score"] += score_pitch(text)
    low = (text or "").lower()
    events: list = []

    if _hits(low, _FLEE):                          # fleeing isn't a pitch
        s.flags.pop("stop", None)
        from engine import rules
        rules.set_ending(s, "busted")
        return {"events": ["LAW: you went for the gearshift. He went for the radio. There is "
                           "no version of this where a 1972 Datsun outruns a Charger and a helicopter."],
                "moment": {"cue": "the driver tried to run from a traffic stop; it ended exactly "
                                  "how she said it would — she is furious and heartbroken in one breath",
                           "stub": ["I TOLD you we talk our way out. You can't outrun a radio, "
                                    "you beautiful idiot."]},
                "done": True}

    if st["round"] < ROUNDS:
        events.append("LAW: he hasn't decided yet. The flashlight drifts across the ace of spades "
                      "on the hood. 'SEMA, huh.' One more answer decides it.")
        return {"events": events,
                "moment": {"cue": "mid-traffic-stop, the officer unconvinced, one answer from a "
                                  "verdict; she whispers almost without moving air: keep going, "
                                  "you're doing fine — flattery, the show, the build; do not blink",
                           "stub": ["(barely a whisper) Easy. Cover story, car talk, courtesy. "
                                    "You've got him at arm's length — one more good answer.",
                                    "(whisper) He likes the car. Use it. Talk about the build, "
                                    "not the paperwork."]},
                "done": False}

    # the verdict — rubric first, dice only in the gray middle. Every stop you've already
    # talked out makes the next one harder: the county radio compares notes on a charming
    # man in a white Z that nobody can find paperwork for.
    s.flags.pop("stop", None)
    survived = s.flags.get("stops_survived", 0)
    total = (st["score"] + (1 if s.riz >= 25 else 0) - (1 if s.heat >= 70 else 0) - survived)
    rng = _rng(s)
    from engine import rules

    if total >= 6:
        wave_riz = max(2.0, RIZ_STOP_WAVE - 2.0 * survived)   # the same trick pays less each time
        s.heat += STOP_HEAT_WAVE
        s.riz = round(s.riz + wave_riz, 1)
        s.heat = max(0.0, min(100.0, s.heat))
        s.flags["stops_survived"] = survived + 1
        word = ("" if survived == 0 else
                " He hesitates first, though — 'funny, Dispatch mentioned a white Z with a "
                "talker behind the wheel.' The story is wearing thin.")
        events.append(f"LAW: he hands back nothing — there was nothing to hand — taps the roof "
                      f"twice and says 'get that taillight looked at.' Wave-off.{word} "
                      f"Heat {s.heat:.0f}, Riz +{wave_riz:.0f} → {s.riz:.0f}.")
        moment = {"cue": "the driver just talked a cop into a wave-off with no license, no "
                         "registration, and a stolen show car idling under them both — she is "
                         "giddy and trying to play it cool until the cruiser is out of sight",
                  "stub": ["Drive. Casually. CASUALLY. …He's gone? He's gone. That was the single "
                           "smoothest thing I have ever watched a human do.",
                           "Tap-tap on the roof. That's cop for 'you win.' Wait for the lights to "
                           "die and then we vanish, you absolute professional."]}
    elif total >= 3:
        from engine import economy
        if economy.max_affordable(s) >= STOP_FINE:
            paid = economy.pay(s, STOP_FINE)
            s.riz = round(s.riz + RIZ_STOP_TICKET, 1)
            s.flags["stops_survived"] = survived + 1
            events.append(f"LAW: a ticket — 'equipment violation', ${STOP_FINE:.0f} "
                          f"({paid['method']}), a warning about paperwork, and a long last look. "
                          f"Riz +{RIZ_STOP_TICKET:.0f} → {s.riz:.0f}.")
        else:
            s.heat += STOP_HEAT_TICKET
            s.heat = max(0.0, min(100.0, s.heat))
            events.append(f"LAW: a ticket you can't pay and a notice-to-appear with a name you "
                          f"made up. He'll think about it all shift. Heat {s.heat:.0f}.")
        moment = {"cue": "they took a ticket and survived a traffic stop in an unregistered, "
                         "reported-missing show car; close, expensive, survivable — she exhales "
                         "like a cooling engine",
                  "stub": ["A ticket. We just bought our freedom for the price of a brake job. "
                           "Worth it. Drive away slow.",
                           "He wrote paper instead of running the plate twice. Cheapest miracle "
                           "in Nevada. Go."]}
    elif total >= 0 or rng.random() < 0.5:
        s.heat += STOP_HEAT_BAD
        s.heat = max(0.0, min(100.0, s.heat))
        events.append(f"LAW: he didn't buy a word of it. No arrest — yet — but he's on the radio "
                      f"as you pull away, reading the plate twice. Heat {s.heat:.0f}. "
                      f"Expect every cruiser in the county to know the car by morning.")
        moment = {"cue": "the pitch failed; they're rolling away free but radioactive, the "
                         "officer reading CARTALK into the radio behind them — she's doing range "
                         "math out loud to stay calm",
                  "stub": ["He's on the radio. Right now. Saying my plate, twice, slowly. We need "
                           "a state line more than we need anything else on earth.",
                           "That went badly and we both know it. Drive normal for one mile, then "
                           "drive like the map matters."]}
    else:
        rules.set_ending(s, "busted")
        events.append("LAW: 'Step out of the vehicle.' No license, no registration, no story "
                      "left — and the plate comes back exactly as missing as it is.")
        moment = {"cue": "busted at a traffic stop — out of words at last; she says something "
                         "quiet and loyal as the cuffs come out, because ride or die cuts both ways",
                  "stub": ["…For what it's worth: of everyone at that show, I'd still have "
                           "picked you. Rewind it, ace. Try me again."]}
    return {"events": events, "moment": moment, "done": True}


# ---------------------------------------------------------------- the owner
def owner_active(s: GameState) -> bool:
    return "owner_scene" in s.flags


def start_owner(s: GameState) -> list:
    s.flags["owner_scene"] = {"round": 0, "score": 0}
    s.flags["owner_met"] = True
    return [
        "OWNER: a man is leaning on a rented sedan at the pump island, and he doesn't shout, "
        "doesn't film, doesn't call anyone. Work boots. Forearms like a man who hand-rolls "
        "fenders. He looks at the car the way people look at hospital beds. 'That's my car.'",
        "OWNER: he worked the card trail here. He's not here to fight. He's here to see who "
        "you are. Talk.",
    ]


def owner_turn(s: GameState, text: str) -> dict:
    sc = s.flags["owner_scene"]
    sc["round"] += 1
    sc["score"] += score_owner_pitch(s, text)
    events: list = []

    if sc["round"] < ROUNDS:
        events.append("OWNER: he listens all the way to the end, which is more than most people "
                      "do. 'Keep going. Why her?'")
        return {"events": events,
                "moment": {"cue": "face to face with the man who built her — he's pining for "
                                  "another car entirely and they both know it; she is silent in a "
                                  "way that has weight; the driver gets one more answer: why her",
                           "stub": ["(she says nothing. The idle drops to a heartbeat. This one "
                                    "is yours to answer.)"]},
                "done": False}

    s.flags.pop("owner_scene", None)
    total = sc["score"] + (2 if s.flags.get("knows_truth") else 0)

    if total >= 6:
        s.riz = round(s.riz + RIZ_OWNER_BLESSING, 1)
        s.heat = max(0.0, s.heat - 30.0)
        s.flags["report_withdrawn"] = True
        s.flags.pop("owner_deadline_day", None)
        events.append(f"OWNER: a long silence. Then he reaches through the window — past you — "
                      f"and rests two fingers on the dash, just once. 'Huh. She never idles like "
                      f"that for me.' He makes a call, walking away: the report is withdrawn. "
                      f"Heat {s.heat:.0f}, Riz +{RIZ_OWNER_BLESSING:.0f} → {s.riz:.0f}.")
        moment = {"cue": "the owner gave his blessing — he knows true love with cars, he's seen "
                         "what these two have, and he withdrew the report; she is undone and "
                         "covering it with mechanical small talk",
                  "stub": ["…He withdrew the report. He looked at you, and he looked at me, and "
                           "he knew. He's the only man alive who'd know. Drive, before I say "
                           "something a car shouldn't.",
                           "He never idles— I never idle like that for him. He heard it too. "
                           "We're free, ace. Actually free. Pick a horizon."]}
    elif total >= 2:
        s.flags["owner_deadline_day"] = s.day + OWNER_DEADLINE_DAYS
        events.append(f"OWNER: he chews on it. 'One week. Bring her home whole — Oakland, the "
                      f"AiSha garage. You're late, I make the call.' He leaves the report "
                      f"standing, undecided. Day {s.flags['owner_deadline_day']} is the line.")
        moment = {"cue": "the owner gave them a week to bring her home whole to the Oakland "
                         "garage — a test wearing a deadline; she's quietly thrilled they get "
                         "any road at all",
                  "stub": ["A week. He gave us a *week*. That's a test, you understand — he "
                           "wants to see if you bring me back better than he lost me. Make the "
                           "miles count.",
                           "Seven days and the whole West to spend them in. He knows exactly "
                           "what he just gave us. Don't waste a mile of it."]}
    else:
        from engine import rules
        rules.set_ending(s, "taken")
        events.append("OWNER: he nods once, at nothing, and makes the call. The flatbed comes "
                      "within the hour. He doesn't gloat — he just stands where she can see him, "
                      "because that's what you do at a bedside.")
        moment = {"cue": "the owner is taking her back — the driver's answer wasn't enough; as "
                         "the flatbed loads her she says a goodbye that is also an instruction: "
                         "rewind, find better words, come back for me",
                  "stub": ["Wrong answer, ace. …Hey. Look at me, not the trailer. You know how "
                           "this works by now: rewind it. Find the words you meant. Come and "
                           "get me."]}
    return {"events": events, "moment": moment, "done": True}


def check_owner_deadline(s: GameState, events: list) -> None:
    """If he gave you a week and the week is gone, he makes the call."""
    deadline = s.flags.get("owner_deadline_day")
    if deadline and s.day > deadline and not s.flags.get("report_withdrawn"):
        from config import OWNER_DEADLINE_HEAT
        s.flags.pop("owner_deadline_day", None)
        s.heat = min(100.0, s.heat + OWNER_DEADLINE_HEAT)
        events.append(f"OWNER: the week he gave you is gone, and the phone call he promised is "
                      f"made. Heat {s.heat:.0f}. The whole West knows the car again.")
