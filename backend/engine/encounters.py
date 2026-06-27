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
    STANDOFF_COPS_ROUNDS, DESPERADO_DISARM_LUCKY, DESPERADO_HEAT_ON_UNLOCK,
    DESPERADO_HEAT_FLOOR, RIZ_DESPERADO, DRAW_HEAT,
)
from engine.state import GameState
from engine.commands import spec_hits
from engine import heat as _heat

# flags that are META-progress: they survive rewinds (game.rewind re-applies them), because
# the curse — the gun you win, the heat the county's seen — belong to you, not to any one timeline.
DESPERADO_PERSIST = ("desperado", "gun", "desperado_tries", "wanted_armed", "rob_attempts")

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
    lines = [opener]
    if s.flags.get("wanted_armed"):
        lines.append("LAW: he's already out of the cruiser with a hand on his holster — this stretch "
                     "of road knows the white Z pulls guns. Charm's a longer shot now.")
    lines.append("LAW: talk your way out — say it like you mean it. (She stays quiet: a car "
                 "that talks is the one thing he can't unsee.)")
    return lines


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
    # once you've pulled iron on the law, they come ready — a charming story doesn't cut it anymore
    armed_pen = 3 if s.flags.get("wanted_armed") else 0
    total = (st["score"] + (1 if s.riz >= 25 else 0) - (1 if s.heat >= 70 else 0)
             - survived - armed_pen)
    rng = _rng(s)
    from engine import rules

    if total >= 6:
        wave_riz = max(2.0, RIZ_STOP_WAVE - 2.0 * survived)   # the same trick pays less each time
        _heat.add(s, STOP_HEAT_WAVE, "a wave-off, but the plate got eyeballed", "spike", axis="car")
        s.riz = round(s.riz + wave_riz, 1)
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
            _heat.add(s, STOP_HEAT_TICKET, "a notice-to-appear under a made-up name", "mark", axis="car")
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
        _heat.add(s, STOP_HEAT_BAD, "he read the plate twice on the radio", "spike", axis="car")
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
        _heat.add(s, -30.0, "the owner withdrew the report", "lower")
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


def owner_price(s: GameState) -> float:
    """What he needs to let her go. She's insured for $100k, so he opens near there and won't go
    under the $80k FLOOR — discounts (knowing Mayumi, real style) bring his number toward it, and
    stripping the build pushes it back up (he won't title a shell). It's a heist-scale goal: you
    have to plausibly RAISE it — gambling, the ATM, your assets — which is the whole point."""
    from config import OWNER_BUY_BASE, OWNER_BUY_FLOOR, OWNER_BUY_MAYUMI_DISC, OWNER_BUY_RIZ_DISC
    from engine import garage
    price = OWNER_BUY_BASE
    if s.flags.get("knows_mayumi") or s.flags.get("knows_truth"):
        price -= OWNER_BUY_MAYUMI_DISC
    if s.riz >= 20:
        price -= OWNER_BUY_RIZ_DISC
    price = max(OWNER_BUY_FLOOR, price)                      # the floor holds against discounts
    price += sum(garage.PARTS[p]["value"] * 2 for p in garage.sold(s))   # stripping pushes it back up
    return round(price)


def owner_buy(s: GameState, amount):
    """Come to terms and buy her — the good resolution. She's insured for $100k and he won't go
    under $80k... unless you offer the exact magic number, $77,777.77 — the sevens are a hack he
    can't refuse. Otherwise you have to actually cover his price (gamble it up, sell, withdraw)."""
    from engine import garage, economy
    from config import RIZ_BOUGHT, LUCKY_SEVENS, INSURED_VALUE
    price = owner_price(s)
    s.flags["owner_price"] = price

    # THE HACK: offer exactly seven sevens and the $80k floor evaporates — but you still PAY the
    # number (it's a secret price below the floor, not a free car). You have to raise ~$78k either way.
    if amount is not None and abs(amount - LUCKY_SEVENS) < 0.01:
        if economy.max_affordable(s, "cash") < LUCKY_SEVENS:
            return {"events": [f"OWNER: you say the number — 'seventy-seven thousand, seven hundred "
                               f"seventy-seven seventy-seven.' His eyes flicker, something almost "
                               f"superstitious — then he counts the air where the cash should be. "
                               f"'...Cute. Come back when you can actually lay it down, kid.'"],
                    "moment": {"cue": "the driver found the magic number $77,777.77 but doesn't have "
                                      "it to pay — the owner is rattled that they KNOW it but won't "
                                      "be hustled; she's thrilled they cracked the code and gutted "
                                      "they can't cover it yet", "stub": ["You KNOW it. You actually "
                               "know the number — I felt him flinch. We just don't have it. Go get "
                               "$77,777.77, ace, and that exact number walks her out the door."]},
                    "done": False}
        s.flags.pop("owner_scene", None)
        s.flags["used_sevens"] = True
        economy.pay(s, LUCKY_SEVENS, prefer="cash")
        s.riz = round(s.riz + RIZ_BOUGHT, 1)
        garage.go_legit(s)
        return {"events": [f"OWNER: you say it slow — 'seventy-seven thousand, seven hundred and "
                           f"seventy-seven dollars. And seventy-seven cents.' He goes very still. "
                           f"'...How did you—' Then he just laughs, takes the seven sevens, and signs "
                           f"the slip for two grand under his own floor. Heat 0. Riz "
                           f"+{RIZ_BOUGHT:.0f} → {s.riz:.0f}.",
                           "OWNED: she's yours — for a number that broke his $80k like a password."],
                "moment": {"cue": "the driver offered the exact magic number $77,777.77 — seven "
                                  "sevens — and it broke the owner's $80k floor like a cheat code; "
                                  "he's spooked and delighted and signs; she is gleeful that they "
                                  "found the hack",
                           "stub": ["THE SEVENS. You found the sevens. I didn't think anyone — never "
                                    "mind. Pink slip's signed, the number that broke him, and we're "
                                    "legal and free and ridiculous. Drive, you beautiful cheat.",
                                    "Seven sevens and he folded like a lawn chair. That's not a "
                                    "price, that's a password. We're OURS now. Floor it."],
                           "good_ending": True},
                "done": True}

    have = economy.max_affordable(s, "cash")     # cash on hand (his deal is cash)
    offered = amount if amount is not None else price

    if offered >= price and have >= price:
        s.flags.pop("owner_scene", None)
        economy.pay(s, price, prefer="cash")
        s.riz = round(s.riz + RIZ_BOUGHT, 1)
        garage.go_legit(s)
        return {"events": [f"OWNER: he counts it once, slow, and hands you a pink slip out of his "
                           f"jacket — already signed, like he knew. '${price:.0f}. She's yours. "
                           f"Take better care of her than I could.' He means it. Heat 0. Riz "
                           f"+{RIZ_BOUGHT:.0f} → {s.riz:.0f}.",
                           "OWNED: she's legally yours. No more running. Race her, show her — in "
                           "the daylight, with your name on the entry."],
                "moment": {"cue": "the driver just BOUGHT the car from the man who built her — the "
                                  "good ending; the title is signed, the heat is gone forever, and "
                                  "she is theirs free and clear; she is overcome — after all the "
                                  "running, somebody chose to make it real and legal and hers",
                           "stub": ["…It's done. There's a pink slip with your name on it and the "
                                    "needle on the heat gauge is never moving again. We're legal, "
                                    "ace. We're *real*. Find me a racetrack and let's do this the "
                                    "way it was always supposed to go.",
                                    "He signed it. He actually signed it. No more mirrors, no more "
                                    "cash-only, no more ducking the plate. Just us and the open "
                                    "legal road. Drive me somewhere we can finally open her up."],
                           "good_ending": True},
                "done": True}

    if have < price:
        s.flags.pop("owner_scene", None)
        return {"events": [f"OWNER: 'She's insured for a hundred grand. I'm not handing you six "
                           f"figures of car for pocket change — ${price:,.0f}, cash, and she's "
                           f"yours, papers and all. Not a dollar under.' You don't have it on you. "
                           f"'Find it. I'll be at the AiSha garage in Oakland.' He "
                           f"leaves the report standing until you do."],
                "moment": {"cue": "the owner offered to SELL the car to the driver for a fair price "
                                  "but they can't cover it yet; he'll wait at the Oakland garage; "
                                  "she is breathless at the possibility — there's a way to make this "
                                  "real, they just need the money",
                           "stub": [f"…He'll *sell* her to us. ${price:,.0f} — eighty grand of car "
                                    "we can't fake. But the tables in Vegas don't care how you got "
                                    "rich, the ATM coughs up ten, the build's worth something off "
                                    "her bones... and there's a number, if you ever find it, that he "
                                    "can't say no to. Go raise it, ace. Come back for me."]},
                "done": True}

    # has the money but lowballed him
    return {"events": [f"OWNER: he shakes his head at your number. '${price:,.0f}. Not a dollar "
                       f"under — she's insured for a hundred. Unless you know the number.' He waits."],
            "moment": {"cue": "the driver lowballed the owner on buying the car; he holds firm at his "
                              "floor and hints, almost playfully, that there's a magic number that "
                              "would change his mind", "stub": [f"He won't take a dollar under "
                       f"${price:,.0f} — said it twice. ...Though the way he said 'unless you know "
                       "the number' — there's a hack in there somewhere. Seven of something."]},
            "done": False}


def can_rob(s: GameState) -> bool:
    """Desperados don't BUY cars — but they sure rob banks. Need the gun and a town with a bank."""
    return bool(s.flags.get("gun")) and s.place.kind == "city" and not s.flags.get("no_heat")


def rob_bank(s: GameState) -> dict:
    """A heist beat — armed only. Big take, big heat, and the law comes for you. Botch it and you
    rewind (the loop is a getaway driver). Each bank you hit makes the next one readier for you."""
    from engine import heat as _heat, rules
    if not s.flags.get("gun"):
        return {"events": ["ROB: with what — your winning personality? You'd need to be holding "
                           "more than the wheel. (Desperados rob banks. You're not one. Yet.)"],
                "moment": None, "done": True}
    if s.place.kind != "city":
        return {"events": ["ROB: no bank out here worth the trouble. A real town — a city with a "
                           "vault and a Tuesday-slow teller."], "moment": None, "done": True}
    import random
    # ATTEMPTS (not just successes) drive the danger, and the counter SURVIVES rewinds — so
    # rewind-retrying a botched job makes the next try riskier, not free. The take self-caps.
    s.flags["rob_attempts"] = s.flags.get("rob_attempts", 0) + 1
    attempts = s.flags["rob_attempts"]
    hits = s.flags.get("robbed_banks", 0)
    rng = random.Random(s.seed * 50331653 + s.turn * 7919 + attempts * 104729 + s.flags.get("rewinds", 0))
    botch = rng.random() < (0.18 + attempts * 0.10)   # every attempt makes the whole county warier
    if botch:
        rules.set_ending(s, "busted")
        return {"events": ["ROB: the teller's hand drifts under the counter and the silent alarm's "
                           "already tripped — they were ready for you. Black-and-whites box the lot "
                           "before you reach the door. Busted, hands on the glass."],
                "moment": {"cue": "the driver's bank robbery went wrong — a silent alarm, a fast "
                                  "response, boxed in before the getaway; she's already telling them "
                                  "to rewind and hit a different bank, or the same one before it got "
                                  "wise",
                           "stub": ["Alarm. ALARM — go, go— …and we're boxed. Rewind, ace. Different "
                                    "bank, or this one before it learned our face. The loop's the "
                                    "only wheelman who never flinches."]},
                "done": True}
    take = round(8000 + rng.random() * 17000, -2)
    s.cash = round(s.cash + take, 2)
    s.flags["robbed_banks"] = hits + 1
    _heat.set_to(s, max(s.heat, 90.0), f"robbed a bank in {s.place.name}", "spike")
    return {"events": [f"ROB: you walk in like you own it, walk out with ${take:,.0f} in a duffel, "
                       f"and the long hood's running at the curb. Clean — for now. Heat → {s.heat:.0f}. "
                       f"Every cruiser in {s.place.region} just got the call.",
                       "ROB: that's bank #%d. They'll be readier next time." % (hits + 1)],
            "moment": {"cue": f"the driver just robbed a bank for ${take:,.0f} and made the getaway in "
                              "the show car; heat is maxed and the whole region is hunting them now; "
                              "she is terrified and thrilled and pure adrenaline — this is the most "
                              "alive and the most doomed they've ever been",
                       "stub": [f"${take:,.0f} in the back and the whole county lit up behind us. THAT'S "
                                "a getaway. Drive like you stole me — because you did, and now this "
                                "too. Cross a line, lose the heat, count it later.",
                                f"We just robbed a BANK. ${take:,.0f}. I can't believe— don't slow "
                                "down, do NOT slow down. We are the most wanted thing in Nevada and "
                                "I have never felt more like a getaway car."]},
            "done": True}


def check_owner_deadline(s: GameState, events: list) -> None:
    """If he gave you a week and the week is gone, he makes the call."""
    deadline = s.flags.get("owner_deadline_day")
    if deadline and s.day > deadline and not s.flags.get("report_withdrawn"):
        from config import OWNER_DEADLINE_HEAT
        s.flags.pop("owner_deadline_day", None)
        _heat.add(s, OWNER_DEADLINE_HEAT, "the owner made the call — the West knows the car again", "spike", axis="car")
        events.append(f"OWNER: the week he gave you is gone, and the phone call he promised is "
                      f"made. Heat {s.heat:.0f}. The whole West knows the car again.")


# ============================================================ DESPERADO MODE
# Act suspicious or aggressive at a manned pump and the jumpy clerk pulls a pistol over the
# counter: keep still, he's calling the cops. You can talk him down (clean exit, no gun) OR
# go for the gun. The disarm only lands if you set it up RIGHT — full tank, paid cash, before
# you spooked him — and even then you fail the first two grabs and get lucky on the third.
# Because the try-counter survives rewinds, you are cursed to relive the standoff until you
# win it. Winning takes his gun: a special checkpoint and Desperado Mode — armed and dangerous.
# All prose is a working DRAFT — Ben fills the details.

# robbery / threat language (strong, worth 2) and merely hinky behavior (worth 1)
_ROB = ("give me", "hand it over", "hand over", "empty the", "the register", "the cash",
        "all the money", "all the cash", "the money", "rob", "stick up", "stick 'em",
        "stick em", "this is a holdup", "freeze", "don't move", "dont move",
        "don't you move", "or i'll", "or else", "i'll shoot", "do as i say", "on the floor",
        "open the register", "no cops", "don't call", "dont call", "shut up", "gimme")
_HINKY = ("back off", "what're you looking at", "what are you looking at", "you got a problem",
          "mind your business", "keep your mouth", "you didn't see", "you saw nothing",
          "casing", "nervous", "twitchy", "don't try", "you're not calling")


def gas_aggression(text: str) -> int:
    """Score how hard the player just leaned on the clerk. >=2 makes him reach under the counter."""
    low = (text or "").lower()
    return 2 * _hits(low, _ROB) + _hits(low, _HINKY)


def standoff_active(s: GameState) -> bool:
    return "standoff" in s.flags


STANDOFF_WHISPER = {
    "cue": "the gas-station clerk has a pistol up over the counter, pointed at the driver, phone "
           "in the other hand dialing the police; she whispers, electric and a little thrilled and "
           "very scared: hands where he can see them — talk him down, or go for the gun, but the "
           "gun only works if the tank's full and you paid him cash before this started",
    "stub": ["(low, fast) Gun. He's got a gun and he's dialing. Hands flat. Talk him off it — "
             "or go for it, but only if we're full and we paid cash, or we don't make the door.",
             "(barely moving) Easy. Easy. Either you sweet-talk that pistol back under the counter, "
             "or you take it off him. Half a tank and a card receipt and we're dead either way."],
}


def start_standoff(s: GameState) -> list:
    s.flags["standoff"] = {"round": 0}
    return [
        "STANDOFF: the clerk's hand comes up from under the counter with a pistol in it, and the "
        "other hand has the phone. 'Keep still. Hands where I can see 'em. I'm calling the cops — "
        "I know what you are.' The barrel doesn't waver as much as you'd hope.",
        "STANDOFF: talk him down, or go for the gun ('disarm'). He's already dialing.",
    ]


def _set_up_right(s: GameState) -> bool:
    """The 'do it right' clause: a full tank and your last fill paid in clean cash."""
    full = s.fuel_l >= s.tank_l - 0.5
    return full and bool(s.flags.get("last_fuel_cash"))


_DEESCALATE = ("sorry", "easy", "whoa", "no trouble", "didn't mean", "didnt mean", "my mistake",
               "just buying gas", "just getting gas", "just fuel", "put it down", "lower the",
               "we're cool", "were cool", "no need", "calm", "relax", "i'll go", "ill go",
               "leaving now", "no harm", "friend", "please")


def standoff_turn(s: GameState, verb: str, raw: str) -> dict:
    """One beat of the standoff. verb ∈ {disarm, draw, say/talk (de-escalate), look}."""
    st = s.flags["standoff"]
    st["round"] += 1
    from engine import rules

    # --- go for the gun ---
    if verb == "disarm":
        s.flags.pop("standoff", None)
        if not _set_up_right(s):
            # not set up: the grab can't land, and now the cops have a reason and a corpse-to-be
            rules.set_ending(s, "busted")
            return {"events": ["STANDOFF: you lunge before you're ready — half a tank, a card "
                               "receipt still on the counter — and he's faster than your odds. "
                               "It ends at the pump."],
                    "moment": {"cue": "the driver went for the gun without setting it up — no full "
                                      "tank, no clean cash — and it went exactly as badly as she "
                                      "warned; she is furious and grieving and already telling them "
                                      "to rewind and DO IT RIGHT this time",
                               "stub": ["I SAID full tank and cash, you beautiful idiot. Rewind. "
                                        "Fill up. Pay the man cash. THEN go for it. We do this "
                                        "until we get it right — that's the whole curse."]},
                    "done": True}
        tries = s.flags.get("desperado_tries", 0) + 1
        s.flags["desperado_tries"] = tries          # survives rewind — the curse remembers
        if tries < DESPERADO_DISARM_LUCKY:
            rules.set_ending(s, "busted")
            left = DESPERADO_DISARM_LUCKY - tries
            return {"events": [f"STANDOFF: you go for it — full tank, clean hands — and you almost "
                               f"have it. Almost. The grip slips and the cops are in the lot. "
                               f"Busted. (Something tells you the next grab goes different.)"],
                    "moment": {"cue": "the driver set it up right and went for the gun and it ALMOST "
                                      "worked — closer than last time; she has the strange certainty "
                                      "of someone who's lived this before that the next attempt is "
                                      "the one; she tells them to rewind and try again, " + str(left)
                                      + " more and it lands",
                               "stub": ["So close I felt it. Rewind, ace. Again. I've got a feeling "
                                        "about the next one — like we've done this before and the "
                                        "third time's the charm. Go for it again.",
                                        "Almost. ALMOST. Don't talk — rewind and do the exact same "
                                        "thing. I can feel the timeline bending our way."]},
                    "done": True}
        # the lucky third — you take the gun
        s.flags["desperado"] = True
        s.flags["gun"] = True
        s.flags["wanted_armed"] = True
        _heat.add(s, DESPERADO_HEAT_ON_UNLOCK, "walked out of a standoff armed — wanted statewide", "spike")
        s.riz = round(s.riz + RIZ_DESPERADO, 1)
        return {"events": [f"STANDOFF: this time your hand finds the barrel first. One twist and "
                           f"the pistol is yours, the clerk's backing into the cigarette rack with "
                           f"his hands open. Full tank, clean cash, open road. You walk out armed. "
                           f"Heat {s.heat:.0f}, Riz +{RIZ_DESPERADO:.0f} → {s.riz:.0f}.",
                           "DESPERADO: armed and dangerous. The law plays for keeps now — and so "
                           "can you ('draw' in a tight spot)."],
                "moment": {"cue": "the driver finally disarmed the clerk on the third try and walked "
                                  "out with the gun — full tank, paid cash, untouchable for one shining "
                                  "second; she is exhilarated and changed and a little frightened of "
                                  "what they've both become — they are armed and dangerous now and "
                                  "there is no rewinding past who they are",
                           "stub": ["…You did it. You actually did it. Gun's ours, tank's full, and "
                                    "I have never felt so alive or so doomed. We're something else "
                                    "now, ace. Armed and dangerous and out of second chances at being "
                                    "anything softer. Drive.",
                                    "Got it. GOT it. Third time, just like I knew. We walked out of "
                                    "there armed, and the West is going to feel it. No going back to "
                                    "before this — not even I can rewind that far."],
                           "unlock": True},
                "done": True}

    # --- pull a gun you don't have ---
    if verb == "draw" and not s.flags.get("gun"):
        return {"events": ["STANDOFF: you reach for a gun you don't own yet. He sees the move and "
                           "the barrel jerks up. Don't."],
                "moment": {"cue": "the driver reached for a weapon they don't have during the "
                                  "standoff; she hisses at them to stop", "stub": ["You don't HAVE "
                           "one yet — that's the whole point. Hands flat. Talk, or take HIS."]},
                "done": False}

    # --- flee ---
    if verb in ("drive", "home", "tow"):
        s.flags.pop("standoff", None)
        rules.set_ending(s, "busted")
        return {"events": ["STANDOFF: you go for the door. He goes for the trigger. Nobody "
                           "outdrives a pistol from ten feet."],
                "moment": {"cue": "the driver tried to flee a man pointing a gun at them; it ended "
                                  "at once", "stub": ["You can't DRIVE away from a gun, ace. Rewind."]},
                "done": True}

    # --- de-escalate (talk him down) ---
    if verb in ("say", "talk"):
        calm = _hits((raw or "").lower(), _DEESCALATE)
        if calm >= 2 and not _hits((raw or "").lower(), _ROB):
            s.flags.pop("standoff", None)
            return {"events": ["STANDOFF: you keep your hands flat and your voice flatter, and the "
                               "barrel drops an inch, then a foot. 'Just get your gas and go. And "
                               "don't come back.' He doesn't lower the phone until you're at the door."],
                    "moment": {"cue": "the driver talked the clerk down off the gun — no shot, no "
                                      "hero, just a slow exit; she exhales like a cut brake line and "
                                      "is quietly relieved they didn't become the other thing tonight",
                               "stub": ["Good. GOOD. Out the door, don't run, don't look back. That's "
                                        "how you walk away from a gun — boring. We stayed boring. "
                                        "Tonight that's the bravest thing we did.",
                                        "He's putting it down. Slow. Slower. …Drive normal. We were "
                                        "never here. Nice work staying soft — it's harder than the "
                                        "other thing."]},
                    "done": True}
        # didn't land — and he's still dialing
        if st["round"] >= STANDOFF_COPS_ROUNDS:
            s.flags.pop("standoff", None)
            rules.set_ending(s, "busted")
            return {"events": ["STANDOFF: you talk in circles and the dispatcher picks up. Two "
                               "minutes later there are lights in the lot. Busted at the pump."],
                    "moment": {"cue": "the driver dithered too long and the cops arrived at the "
                                      "standoff", "stub": ["Too slow — they're here. Rewind and "
                               "mean it this time, words or the gun, but pick one."]},
                    "done": True}
        return {"events": [f"STANDOFF: he's not buying it and the phone's still to his ear. "
                           f"'I said keep still.' ({STANDOFF_COPS_ROUNDS - st['round']} before the "
                           f"cops are here.)"],
                "moment": {"cue": "the de-escalation isn't landing and the clerk is still on the "
                                  "phone with police; she urges calm, fast", "stub": ["Not working. "
                           "Drop the act, go simpler — sorry, easy, just buying gas, putting it down. "
                           "Or go for the gun. Clock's running."]},
                "done": False}

    # look / anything else — stall (counts toward the cops arriving)
    if st["round"] >= STANDOFF_COPS_ROUNDS:
        s.flags.pop("standoff", None)
        rules.set_ending(s, "busted")
        return {"events": ["STANDOFF: you freeze a beat too long and the lot fills with red and "
                           "blue. Busted at the pump."],
                "moment": {"cue": "the driver stalled out the standoff clock", "stub": ["That's "
                           "the cops. Rewind, ace."]}, "done": True}
    return {"events": ["STANDOFF: the pistol stays level. He's still on the phone. Do something."],
            "moment": {"cue": "mid-standoff, nothing resolved, the clerk still aiming and dialing",
                       "stub": ["Talk or grab, ace — staring at him isn't a plan."]}, "done": False}


def draw_in_stop(s: GameState, in_owner: bool) -> dict:
    """Desperado's nuclear option: pull the gun on the law (or the owner). Forces an exit at a
    ruinous cost. Only reachable once you're armed."""
    from engine import rules
    if in_owner:
        s.flags.pop("owner_scene", None)
        s.flags["owner_refused_forever"] = True
        _heat.add(s, 20.0, "drew the gun on the man who built her", "spike")
        return {"events": ["OWNER: you put the gun on the man who built her. He goes still, then "
                           "raises both hands and steps back, slow. 'Okay. Okay. She's yours.' He "
                           "walks to his rental without turning his back on you. He will not ask "
                           "again — and he will not call it off, either."],
                "moment": {"cue": "the driver drew the gun on the man who built her to make him back "
                                  "off; she is sick about it — this is the coldest thing they've done "
                                  "and it bought freedom at the price of the one person who understood "
                                  "them both", "stub": ["…You pulled it on HIM. He built me. He's "
                           "walking away with his hands up and something just died in the car that "
                           "isn't coming back with a rewind. We're free. God help us, we're free."]},
                "done": True}
    s.flags.pop("stop", None)
    s.flags["wanted_armed"] = True
    _heat.set_to(s, DRAW_HEAT, "drew first on a cop — armed and flagged statewide", "spike")
    return {"events": [f"LAW: you draw first. The officer's eyes go wide and he dives behind his "
                       f"door as you drop it into gear — clean away, this time, but every radio in "
                       f"the state just learned this car shoots back. Heat {s.heat:.0f}.",
                       "LAW: armed-and-dangerous now. The next ones won't wave you off — they'll "
                       "come ready."],
            "moment": {"cue": "the driver pulled a gun on a cop to escape a stop; they got away but "
                              "crossed a line — the law will now treat this car as a lethal threat; "
                              "she is breathless, half-feral, aware they just traded every soft "
                              "ending for this one",
                       "stub": ["GO — go go go, before he's up. …We're clear. We're clear. And we "
                                "are never going to be waved off again, you understand that? We pulled "
                                "iron on the law. That door's shut now. Just drive.",
                                "Holstered, hammer down, hands at ten and two like a Sunday drive. "
                                "Nobody behind us. But they know now — this Z bites. No more talking "
                                "our way out. Only this."]},
            "done": True}
