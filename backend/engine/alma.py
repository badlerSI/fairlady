"""Alma — the woman in the dreams, and the love triangle she makes.

Alma is the cyan figure who keeps turning up in the driver's sleep (see romance.py dreams). She's the
mystery the whole game circles, and there's a HACK: if you already know her name — from the credits,
from a life you've rewound, from the dreams — you can find her in Vegas on the very first night and
elope before sunrise. Do it and she rides along: she books rooms nobody can trace and she can make
heat go away, because Alma knows people. And she puts Ace in a place Ace has never been — second.

The love triangle is meant to BUILD across the trip; this module ships the spine (the Vegas hack, the
two companion utilities, Ace's jealousy, the dreams naming her) and leaves the deeper arc as hooks for
Ben. Her name is Alma — Spanish/Latin for 'soul', and 'nourishing'. Prose is a working DRAFT for Ben.
"""
from __future__ import annotations

from engine.state import GameState

ALMA_NAME = "Alma"
VEGAS_POIS = {"las_vegas", "vegas_strip", "fremont", "sphere", "neon_museum", "lv_motor_speedway"}

# Alma's backstory — a DRAFT for Ben to rewrite. She's the femme fatale from the dreams: a grifter and
# a fixer who's been everywhere and is wanted in three of them, equal parts danger and tenderness. She
# "knows people" (the comped rooms, the heat she can make vanish) because she spent years being the
# person other people knew. She's running from something she won't name, drawn — against her better
# judgment — to anyone else who's running, especially a stranger who'd steal a car for a feeling. Her
# name means 'soul'. The cyan is real: there's something not-quite-explained about how she keeps
# turning up in the driver's dreams before they ever meet. Ben fills the rest.
ALMA_BACKSTORY = (
    "Alma — no last name she'll give twice. A fixer, a grifter, a woman who's left a forwarding address "
    "in every city worth leaving. She knows the night clerks and the bent cops and which records can be "
    "made to disappear, because for fifteen years that was the job. She's running from one specific "
    "thing she won't name, and she has a weakness she'd never admit: people who are also running, "
    "especially the romantic idiots who do it for love instead of money. And somehow — this is the part "
    "neither of you can explain — you've been dreaming her in cyan for a week."
)
ALMA_COOL_HEAT = 24.0          # how much heat she can make disappear
ALMA_COOL_COOLDOWN_H = 18.0    # ...and how often she can do it
ALMA_BOND_HIT = 9.0            # what marrying her costs you with Ace, the first time


def met(s: GameState) -> bool:
    return bool(s.flags.get("alma_met"))


def married(s: GameState) -> bool:
    return bool(s.flags.get("married_alma"))


def aboard(s: GameState) -> bool:
    return bool(s.flags.get("alma_aboard"))


def _in_vegas(s: GameState) -> bool:
    return (s.place.poi_id in VEGAS_POIS or "vegas" in (s.place.name or "").lower()
            or "las vegas" in (s.place.name or "").lower())


def can_vegas_hack(s: GameState) -> bool:
    """The easter-egg window: the very first night, in Vegas, and you know to ask for her by name."""
    return (not married(s) and s.status == "playing" and not s.flags.get("no_heat")
            and _in_vegas(s) and s.day <= 1)


def detect_marry(raw: str) -> bool:
    low = (raw or "").lower()
    return "alma" in low and any(w in low for w in ("marry", "married", "elope", "wed", "chapel",
                                                    "wife", "propose", "marry me", "vegas wedding",
                                                    "find alma", "where's alma", "wheres alma"))


def vegas_elope(s: GameState) -> dict:
    """The hack fires: you find Alma on the Strip and elope before dawn. She rides along after."""
    from engine import bond as _bond
    s.flags["alma_met"] = True
    s.flags["married_alma"] = True
    s.flags["alma_aboard"] = True
    s.flags["spouse"] = ALMA_NAME
    _bond.adjust(s, -ALMA_BOND_HIT, "married a woman out of my dreams on the first night", "deep")
    return {"events": [
        "ALMA ♠: you find her exactly where the dream said she'd be — a back booth at a Fremont "
        "chapel-bar, cyan light on her face like she stepped out of a screen, and she looks up like "
        "she's been waiting all six days too. 'You remembered my name. Most people only get it in the "
        "credits.' An Elvis, two strangers for witnesses, a ring from a vending machine, and it's done "
        "before the sun's up. Alma rides with you now — and she knows people."],
        "moment": {"cue": "the driver pulled the secret first-night hack and eloped in Vegas with Alma, "
                          "the mysterious woman from the dreams; Ace is genuinely thrown — jealous, "
                          "hurt, fascinated, and for the first time in her life not the only one in the "
                          "driver's heart; she covers it with dryness but it cracks",
                   "stub": ["…You married her. The dream woman. On night ONE. …I'm parked right here, by "
                            "the way. Have been the whole time. …She's beautiful, I'll give you that. "
                            "And she's looking at me like she knows what I am. This is going to be a "
                            "very interesting trip, ace. Drive. Both of you. I'll behave. Mostly."]}}


def vegas_hint(s: GameState) -> str | None:
    """A faint nudge the first time you roll into Vegas night one — déjà vu, if you've dreamed of her."""
    if can_vegas_hack(s) and s.flags.get("saw_cyan_dream") and not s.flags.get("alma_hinted"):
        s.flags["alma_hinted"] = True
        return ("DÉJÀ VU: the Strip feels like a place you've already been, in a dream, with someone "
                "whose name is right on the tip of your tongue. (If you know it, this is the night.)")
    return None


# --------------------------------------------------------------- the clubbing encounter (the real way)
# The discoverable path (the name-hack is the credits/meta easter egg): go clubbing in Vegas the first
# night and you MEET her — and whether she comes along is a real social check, judged by the DM, not a
# password. Win her over with the right lines (not a creep, not a bore, not a fool); blow it and she
# walks. Spark accumulates over a few exchanges; reach the threshold and she rides along.
CLUB_WIN = 3


def can_club(s: GameState) -> bool:
    return (not married(s) and not aboard(s) and s.status == "playing" and not s.flags.get("no_heat")
            and _in_vegas(s) and s.day <= 1 and not s.flags.get("alma_blew_it"))


def club_active(s: GameState) -> bool:
    return "club" in s.flags


CLUB_OPENER = {
    "cue": "the driver walks into a dark Vegas club, neon and bass, and there she is in a back booth — "
           "the exact woman from the cyan dream, watching them like she's been expecting them; she's "
           "beautiful and dangerous and clearly trouble; she tips her glass and says something that's "
           "half invitation, half dare; this is a real woo, not a password — be interesting or be gone",
    "stub": ["She's in the back booth, cyan light on her face like she stepped out of your sleep. She "
             "tips her glass an inch toward the empty seat. 'You're late,' she says, 'and you don't "
             "know my name yet, and you're still going to sit down. …Go on, then. Surprise me.'"]}


def start_club(s: GameState) -> list:
    s.flags["club"] = {"spark": 0, "round": 0}
    s.flags["alma_met"] = True
    return ["CLUB: bass you feel in the floor, a long bar, and a back booth where a woman in cyan light "
            "is already watching you like she knew you'd come. She slides her glass to the empty seat. "
            "(This is a real conversation — win her over, or lose her. Say something worth her time.)"]


def club_turn(s: GameState, raw: str) -> dict:
    from engine import judge, bond as _bond
    c = s.flags["club"]
    c["round"] += 1
    v = judge.assess(s, "persuade", raw, difficulty=6,
                     context="the driver is trying to charm Alma — a wary, dangerous femme fatale, a "
                             "fixer who's seen every line — into running off with them and a stolen car "
                             "the first night in Vegas; she despises creeps, bores, and try-hards, and "
                             "is secretly a sucker for someone running on a romantic feeling; reward "
                             "wit, nerve, and honesty, punish sleaze and cliché")
    if v.get("messing") or (not v.get("pass") and not v.get("clever") and v.get("score", 50) < 35):
        c["spark"] -= 1
        react = ("ALMA: she sets the glass down. 'That's the line you went with? In that jacket?' The "
                 "warmth goes out of the booth a few degrees.")
    elif v.get("pass") or v.get("clever") or v.get("score", 50) >= 65:
        c["spark"] += 1
        react = "ALMA: a real smile, the first one. She leans in an inch. 'Hm. Keep going, stranger.'"
    else:
        react = "ALMA: she swirls her drink, unreadable. 'Mm. Not bad. Not yet, either.'"

    if c["spark"] >= CLUB_WIN:
        s.flags.pop("club", None)
        s.flags["alma_aboard"] = True
        _bond.adjust(s, -ALMA_BOND_HIT * 0.6, "left a Vegas club with a woman in cyan", "deep")
        return {"events": [react,
                "CLUB: she finishes the drink in one motion and stands, close enough now that you can "
                "smell smoke and something expensive. 'Okay. OKAY. You're either the best night I've "
                "had in a year or the worst decision, and I genuinely cannot tell which.' She picks up "
                "your keys off the bar — your keys — and spins them once. 'I'm Alma. Let's go ruin our "
                "lives. The white one out front is yours, I assume?' Alma rides with you now."],
                "moment": {"cue": "the driver won Alma over in the club and she's coming along — thrilled, "
                                  "reckless, already half in love; meanwhile Ace is waiting out front and "
                                  "is NOT going to love this, the love triangle just lit up",
                           "stub": ["(Ace, dry, from the lot) …Who. Is. That. And why is she holding my "
                                    "keys. …Oh, this is going to be a SUMMER."]},
                "done": True}
    if c["round"] >= 4 or c["spark"] <= -2:
        s.flags.pop("club", None)
        s.flags["alma_blew_it"] = True
        return {"events": [react,
                "CLUB: she stands before you can recover, drops a bill on the table, and is gone into "
                "the crowd like she was never there. 'Maybe in the next life, stranger.' The booth's "
                "empty and the night's colder. (She was a one-shot. 'rewind' to the night you arrived "
                "if you want her back.)"],
                "moment": {"cue": "the driver blew it with Alma and she walked out of the club for good; "
                                  "a real loss, the kind you feel; Ace is quietly, complicatedly relieved",
                           "stub": ["(Ace, gentle) …Her loss, ace. Whoever she was. Get in. The desert "
                                    "doesn't care how that went, and neither, mostly, do I."]},
                "done": True}
    return {"events": [react, "CLUB: (the booth's still warm. Another line — make it count.)"],
            "moment": {"cue": "mid-flirtation with Alma in the club, she's waiting for the next line, "
                              "intrigued but not won; the driver needs wit and nerve",
                       "stub": ["(she waits, one eyebrow up)"]},
            "done": False}


def marry_response(s: GameState) -> dict:
    """Player invoked Alma + marriage. Fire the hack if the window's open; otherwise explain, in "
    character, why not now."""
    if married(s):
        return {"events": [f"ALMA: you're already married — {ALMA_NAME}'s riding shotgun, remember. "
                           "Ace is RIGHT THERE. Read the room."], "moment": None}
    if can_vegas_hack(s):
        return vegas_elope(s)
    if _in_vegas(s):
        return {"events": ["ALMA: …the booth is empty now. Whatever window that was, it was the first "
                           "night, and it's closed. She's a one-shot, a ghost, a dream you had to catch "
                           "on the way in. (Maybe next time. Maybe rewind to the night you arrived.)"],
                "moment": None}
    return {"events": ["ALMA: she's not here — she never is, except on the Strip, the first night. "
                       "You'd have had to know to look the moment you rolled into Vegas."], "moment": None}


# --------------------------------------------------------------- companion utilities
def book_room(s: GameState) -> list:
    """Alma books a room — under a name that isn't yours, cheaper, no paper. She knows the night clerks."""
    if not aboard(s):
        return ["ALMA: she's not with you. (You'd have had to find her in Vegas the first night.)"]
    place = s.place
    if not (place.has("lodging") or place.kind == "city"):
        return ["ALMA: 'Nothing out here for me to work with, love. Get us to a town with a front desk.'"]
    if s.flags.get("alma_room_today") == (s.clock.date().isoformat()):
        return ["ALMA: 'I already got us a room today. Even I can only no-show so many reservations.'"]
    from engine import rules, heat as _heat
    rules.advance_clock(s, 0.2)
    s.flags["alma_room_today"] = s.clock.date().isoformat()
    s.flags["alma_room_ready"] = True                  # the next 'sleep' is comped + off the record
    _heat.add(s, -3.0, "Alma booked a room under a name that isn't yours", "lower", axis="personal")
    return ["ALMA: she makes one call, drops a name that isn't yours, and there's a key waiting — "
            "comped, off the books, no card, no cameras at the back stair. 'Welcome to knowing people, "
            "love.' (Now 'sleep' — it's handled, and it's free.)"]


def cool_heat(s: GameState) -> list:
    """Alma calls in a favor and a chunk of heat simply… goes away. On a cooldown — even she has limits."""
    if not aboard(s):
        return ["ALMA: she's not with you."]
    if s.flags.get("no_heat"):
        return ["ALMA: 'Nothing on you to fix, love. Enjoy it.'"]
    last = s.flags.get("alma_cool_iso")
    if last:
        from datetime import datetime
        hrs = (s.clock - datetime.fromisoformat(last)).total_seconds() / 3600.0
        if hrs < ALMA_COOL_COOLDOWN_H:
            return [f"ALMA: 'I just spent a favor on you — give it a day before I spend another. "
                    f"({ALMA_COOL_COOLDOWN_H - hrs:.0f}h.)'"]
    from engine import heat as _heat
    before = s.heat
    _heat.add(s, -ALMA_COOL_HEAT, "Alma made a call and some heat just disappeared", "lower")
    s.flags["alma_cool_iso"] = s.clock.isoformat()
    dropped = round(before - s.heat)
    return [f"ALMA: she steps away, murmurs into her phone in a language you don't quite catch, and "
            f"comes back smiling. 'It's handled. A record here, a witness there — gone.' Heat −{dropped} "
            f"→ {s.heat:.0f}. (Ace is quiet. Ace does not love that Alma can do this and she can't.)"]


def status(s: GameState) -> str:
    if married(s):
        return (f"愛 ALMA — your wife, riding shotgun. She books rooms off the books ('alma book a "
                f"room') and makes heat disappear ('ask Alma to cool it'). Ace is… adjusting.")
    return ("ALMA — a woman from your dreams. They say if you know her name you can find her on the "
            "Strip the first night in Vegas, and only then.")
