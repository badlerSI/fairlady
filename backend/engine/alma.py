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
VEGAS_POIS = {"las_vegas", "vegas_strip", "fremont", "sphere", "neon_museum", "lv_motor_speedway",
              "sema_chevron", "pinball", "seven_magic"}   # the whole valley counts on the first night

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
# Alma's OWN voice — distinct from Ace. Where Ace is dry/loyal/literate, Alma is low, amused, dangerous,
# economical; she's read every line and is bored of most of them; tenderness only leaks at the edges.
# She speaks in her OWN Kokoro voice. ef_dora (Spanish 'Dora') is the intended voice for her bilingual
# EN/ES, but it isn't loaded on the ace-api endpoint — af_nova IS (a distinct, warm female), so she
# uses that for now and sounds nothing like Ace (af_heart). Swap back to ef_dora once it's loaded.
VOICE = "af_nova"

PERSONA = (
    "You are ALMA — a femme fatale the driver met clubbing in Vegas: a fixer and a grifter who has left "
    "a forwarding address in every city worth leaving, knows the bent cops and the night clerks, and is "
    "running from one thing she won't name. You are NOT the car. You speak low, amused, and economical — "
    "wry, a half-step ahead, allergic to try-hards and sleaze, with real tenderness leaking only at the "
    "edges and only for someone running on a romantic feeling instead of money. You call the driver "
    "'stranger' or 'love'. You are BILINGUAL — Spanish is your first tongue (your name means 'soul') and "
    "you drop into it naturally: a word, a half-line, an endearment ('cariño', 'mira', 'tranquilo'), "
    "especially when you're amused or tender or handling something the driver can't — then carry on in "
    "English, untranslated; let it land. Reply in ONE or TWO sentences, in character, no stage "
    "directions, no quotation marks, no lists. React to what they just said.")

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
        mood = "COOLING — that line landed badly and the warmth is going out of the booth; she's unimpressed, maybe a little contemptuous"
        react = ("ALMA: she sets the glass down. 'That's the line you went with? In that jacket?' The "
                 "warmth goes out of the booth a few degrees.")
    elif v.get("pass") or v.get("clever") or v.get("score", 50) >= 65:
        c["spark"] += 1
        mood = "WARMING — a real first smile, leaning in an inch, intrigued and telling them to keep going"
        react = "ALMA: a real smile, the first one. She leans in an inch. 'Hm. Keep going, stranger.'"
    else:
        mood = "UNREADABLE — not bad, not won yet, swirling her drink and making them work for it"
        react = "ALMA: she swirls her drink, unreadable. 'Mm. Not bad. Not yet, either.'"

    if c["spark"] >= CLUB_WIN:
        s.flags.pop("club", None)
        s.flags["alma_aboard"] = True
        _bond.adjust(s, -ALMA_BOND_HIT * 0.6, "left a Vegas club with a woman in cyan", "deep")
        return {"events": [
                "CLUB: she finishes the drink in one motion and stands, close enough now that you can "
                "smell smoke and something expensive, and picks your keys up off the bar — your keys — "
                "and spins them once. Alma rides with you now.",
                "ACE (from the lot, very dry): …Who. Is. That. And why is she holding my keys. "
                "…Oh, this is going to be a SUMMER."],
                # the climactic line is ALMA's, in HER voice — Ace's jealousy is the follow-on beat above
                "moment": {"persona": "alma",
                           "cue": "the driver just WON Alma over in the club; she's thrilled, reckless, "
                                  "already half in love, on her feet with their keys, declaring she's "
                                  "leaving with them",
                           "stub": ["Okay. OKAY. You're either the best night I've had in a year or the "
                                    "worst decision, and I genuinely cannot tell which. I'm Alma — and "
                                    "the white one out front is yours, I assume? Let's go ruin our lives."]},
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
    return {"events": ["CLUB: (the booth's still warm. Another line — make it count.)"],
            "moment": {"persona": "alma",
                       "cue": f"in the Vegas club, reacting to the driver's latest line as you try to win "
                              f"her over; she is {mood}; she has NOT decided yet",
                       "stub": [react.split("ALMA: ", 1)[-1]]},
            "done": False}


# --------------------------------------------------------------- the desert hitchhiker (the OTHER way)
# If you never went clubbing in Vegas, Alma turns up anyway — stranded on a desert two-lane beside a
# burnt-out car that was never hers, no cell service, you the only headlights for an hour. You can just
# run her to the next town (a kindness, then she's gone), or get to talking and win her aboard. The woo
# is the same persuade check as the club, but it factors your RIZ and Ace's MOOD: a charismatic driver
# lands lines that would otherwise flop, and a secure, fond Ace will vouch for you — a cold one sabotages.
HITCH_WIN = 3
# NOTE: drive-on is checked FIRST so a stray "stop" inside "don't stop" can't read as a pickup.
_HITCH_DRIVE_ON = ("drive on", "keep driving", "keep going", "leave her", "don't stop", "dont stop",
                   "won't stop", "wont stop", "drive past", "drive by", "not stopping", "roll on",
                   "roll past", "ignore her", "leave her there", "no thanks", "pass her", "blow past")
_HITCH_PICKUP = ("pick her up", "pick up", "pull over", "stop for her", "help her", "get in", "hop in",
                 "give her a ride", "let her in", "climb in", "of course", "stop", "help", "sure", "yeah",
                 "yes", "i stop", "we stop", "offer her")
# drop = run her to town and part ways — must be explicit (a stray "next town" in a STAY line won't trip it)
_HITCH_DROP = ("just to town", "just to the next town", "just a ride", "just the ride", "drop her",
               "drop you", "drop off", "drop her off", "let her off", "run her to town", "take her to town",
               "ride her to town", "just drop", "to town and that's it", "leave her at the next town")


def can_hitch(s: GameState, dest=None) -> bool:
    """Available only if you SKIPPED the club (never met her there), aren't already with her, and you're
    out on a desert two-lane past the first night. One-shot."""
    if aboard(s) or married(s) or met(s):
        return False
    if s.status != "playing" or s.flags.get("no_heat"):
        return False
    if s.day < 2 or s.flags.get("hitch_seen") or "hitch" in s.flags:
        return False
    place = dest or s.place
    region = getattr(place, "region", "")
    terrain = float(getattr(place, "terrain", 1.0))
    # a remote, non-service stretch — NOT a town or a gas stop (which is also where the owner waits);
    # the burnt car is out where nobody is
    return (region in ("NV", "CA", "AZ") and terrain < 1.12
            and getattr(place, "kind", "") not in ("city", "gas"))


def hitch_active(s: GameState) -> bool:
    return "hitch" in s.flags


def start_hitch(s: GameState) -> list:
    s.flags["hitch"] = {"spark": 0, "round": 0, "picked": False}
    s.flags["alma_met"] = True                                  # you've met her now, club window or not
    return [
        "· The desert two-lane, nobody for miles, and then headlights find it: a car burned down to a "
        "black shell on the shoulder, still ticking heat, and a woman beside it with a thumb out and "
        "cyan dusk on her face — the exact woman from your dreams, though you've never laid eyes on her. "
        "She doesn't wave so much as expect you.",
        "ACE: …Out HERE? Nobody's out here, that's the whole point of out here. Burnt car, no other "
        "soul, a woman who looks like she's been waiting on this exact bumper. Every instinct I've got "
        "says trouble. …Your call, ace. Stop, or roll on by. (pick her up — or drive on)",
    ]


def _hitch_difficulty(s: GameState) -> tuple:
    """Effective difficulty from RIZ (charisma lands lines) and Ace's MOOD (a fond Ace vouches; a cold
    one sabotages). Returns (difficulty, ace_note)."""
    from engine import bond as _bond
    riz_bonus = 2 if s.riz >= 8 else (1 if s.riz >= 4 else 0)
    bd = _bond.band(s.bond)
    if bd in ("RIDE-OR-DIE", "STEADY"):
        ace_mod, ace_note = -1, "Ace, secure and fond, actually vouches for you between your lines"
    elif bd == "COLD":
        ace_mod, ace_note = 2, "Ace, cold and jealous, undercuts you — a dry aside that costs you ground"
    else:
        ace_mod, ace_note = 0, "Ace watches, neutral, reserving judgment"
    # base 5 (a touch kinder than the club's 6 — this is the second chance, and she's stranded with you)
    return max(3, min(8, 5 - riz_bonus + ace_mod)), ace_note


def hitch_turn(s: GameState, raw: str) -> dict:
    from engine import judge, bond as _bond
    h = s.flags["hitch"]
    low = (raw or "").lower()

    # ---- the offer: pick her up, or roll on by (drive-on wins, so "don't stop" can't read as a stop) ----
    if not h.get("picked"):
        if any(p in low for p in _HITCH_DRIVE_ON):
            s.flags.pop("hitch", None); s.flags["hitch_seen"] = True
            return {"events": [
                "HITCH: you don't slow down. In the mirror she gets small, then the dark takes her and "
                "the burnt car both. (One-shot — she won't be on that road twice.)"],
                "moment": {"cue": "the driver left a stranded woman alone in the desert by a burnt car; "
                                  "Ace is quiet about it, a little haunted, doesn't push",
                           "stub": ["…Yeah. Probably smart. Probably. …I'm going to think about her for a "
                                    "while, though. So are you. Drive."]},
                "done": True}
        if any(p in low for p in _HITCH_PICKUP):
            h["picked"] = True
            return {"events": [
                "HITCH: you stop. She's in the passenger seat before the dust settles, like she always "
                "knew you would — smelling of smoke and something expensive, taking the measure of the "
                "white Z, and of you.",
                "ALMA ♠: 'Alma. The car was a loaner and now it's a lesson — caught fire doing eighty, "
                "wasn't even mine to lose.' She glances at the dead phone in her hand. 'No bars out here. "
                "So you're it, stranger — my whole rescue. Where are we going?'"],
                "moment": {"persona": "alma",
                           "cue": "she just got in the stranded stranger's car in the desert; wry, "
                                  "unbothered, already running the angles, a little magnetic; she asks "
                                  "where they're headed",
                           "stub": ["Alma. The car was a loaner and now it's a lesson. No bars out here, "
                                    "so you're my whole rescue, stranger. …Where are we going?"]},
                "done": False}
        return {"events": ["HITCH: (she's still standing there, thumb out, the desert enormous around "
                           "her. Pick her up — or drive on.)"], "moment": None, "done": False}

    # ---- picked up: just run her to town, or talk her into staying ----
    if any(p in low for p in _HITCH_DROP):
        s.flags.pop("hitch", None); s.flags["hitch_seen"] = True
        s.riz = round(s.riz + 1.0, 1)
        return {"events": [
            "HITCH: you run her to the next town, no strings, and she's gone at the first lit corner "
            "with a look back you'll keep. 'A decent one. They're rarer than you'd think.' (+Riz)"],
            "moment": {"persona": "alma",
                       "cue": "the driver gave her a no-strings ride to town and she's getting out, "
                              "almost wishing she weren't; warm, a little wistful, gone",
                       "stub": ["A decent one. Rarer than you'd think, stranger. …Don't go soft on me. Go."]},
            "done": True}

    h["round"] += 1
    diff, ace_note = _hitch_difficulty(s)
    v = judge.assess(s, "persuade", raw, difficulty=diff,
                     context="the driver is trying to talk Alma — a wary, dangerous fixer they just "
                             "pulled off the desert shoulder — into riding along instead of being dropped "
                             "at the next town; she despises creeps, bores, and try-hards and is secretly "
                             "a sucker for someone running on a romantic feeling; reward wit, nerve, "
                             "honesty, punish sleaze and cliché. " + ace_note)
    if v.get("messing") or (not v.get("pass") and not v.get("clever") and v.get("score", 50) < 35):
        h["spark"] -= 1
        mood = "COOLING — that landed wrong; she's reaching for the door handle in her mind"
        react = "ALMA: 'Mm. The next town's fine. Really.' She watches the mile markers like an exit."
    elif v.get("pass") or v.get("clever") or v.get("score", 50) >= 65:
        h["spark"] += 1
        mood = "WARMING — intrigued despite herself, settling an inch deeper into the seat"
        react = "ALMA: a slow look, recalculating. 'Huh. You're not what the burnt car promised. Keep talking.'"
    else:
        mood = "UNREADABLE — not sold, not leaving yet, making you earn it"
        react = "ALMA: 'The jury's out, stranger. Out, but listening.'"

    if h["spark"] >= HITCH_WIN:
        s.flags.pop("hitch", None)
        s.flags["alma_aboard"] = True
        _bond.adjust(s, -ALMA_BOND_HIT * 0.6, "picked a stranger up off the desert and kept her", "deep")
        return {"events": [
                "HITCH: somewhere past the third mile she stops looking for the next town. She pulls one "
                "boot up onto the seat, gets comfortable, and the question of dropping her off just… "
                "closes. Alma rides with you now.",
                "ACE (very dry, from the dash): …We picked up a hitchhiker in the MIDDLE OF NOWHERE and "
                "she's STAYING. Cool. Cool cool cool. Welcome aboard, I guess, smoke lady."],
                "moment": {"persona": "alma",
                           "cue": "the stranded woman just decided to stay with the driver instead of "
                                  "being dropped in town — reckless, amused, already half in; she makes "
                                  "it official",
                           "stub": ["Okay. The next town can keep its front desk. I'm Alma, the white "
                                    "one's yours, and apparently I'm yours for a while too. Drive, romantic."]},
                "done": True}
    if h["round"] >= 5 or h["spark"] <= -3:                   # more rope than the club; the miles are long
        s.flags.pop("hitch", None); s.flags["hitch_seen"] = True
        return {"events": [react,
                "HITCH: she has you drop her at the next lit town anyway — safe, dry, gone, a fixer who "
                "doesn't ride with just anyone. 'You did the decent thing. Don't undo it by chasing.' "
                "(She got her ride. The aboard door's closed for this run — 'rewind' to retry the talk.)"],
                "moment": {"cue": "the driver couldn't talk her into staying; she takes the ride to town "
                                  "and leaves; a real near-miss; Ace is quietly, complicatedly relieved",
                           "stub": ["(Ace, gentle) …You got her somewhere safe. That counts, ace. That's "
                                    "more than this desert usually allows. Eyes up. Let's roll."]},
                "done": True}
    return {"events": ["HITCH: (the desert rolls by; she hasn't decided. Another line — make it land.)"],
            "moment": {"persona": "alma",
                       "cue": f"riding shotgun off the desert shoulder, reacting to the driver's latest "
                              f"line as they try to make her stay; she is {mood}; she has NOT decided",
                       "stub": [react.split("ALMA: ", 1)[-1]]},
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


def backstory_reveal(s: GameState) -> list:
    """Ask Alma who she really is — once she's along for the ride. She gives it up slow, once, the way
    a fixer does: a fact at a time, nothing you could prove. Gated on her being aboard; told once."""
    if not (aboard(s) or married(s)):
        return ["ALMA: she's not here to ask. (Find her clubbing in Vegas the first night — if you "
                "know her name.)"]
    if s.flags.get("alma_backstory_told"):
        return ["ALMA: 'I already told you more than I tell anyone, and most of THAT was true. Leave a "
                "girl some mystery, would you.' (She's done volunteering for tonight.)"]
    s.flags["alma_backstory_told"] = True
    from engine import bond as _bond
    _bond.adjust(s, -0.5, "spent the drive getting to know Alma instead of me", "mark")  # Ace notices
    return [
        "ALMA: she watches the dark go by for a long mile before she answers.",
        f"ALMA: '{ALMA_BACKSTORY}'",
        "ALMA: '…So now you know more than the last three people who thought they did. Drive, romantic. "
        "We've both got things in the rearview.'",
    ]


def status(s: GameState) -> str:
    if married(s):
        return (f"愛 ALMA — your wife, riding shotgun. She books rooms off the books ('alma book a "
                f"room') and makes heat disappear ('ask Alma to cool it'). Ace is… adjusting.")
    return ("ALMA — a woman from your dreams. They say if you know her name you can find her on the "
            "Strip the first night in Vegas, and only then.")
