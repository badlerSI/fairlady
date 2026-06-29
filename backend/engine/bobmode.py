"""BOB MODE — park the hot white Z at the registered address, borrow forgettable Bob.

The address on Ace's registration is the OWNER'S PARENTS' house in Carson City. They're in Portugal
the whole first month (doors unlocked, a brown '71 240Z named BOB under a sheet in the garage). Drive
there, park Ace on the home WiFi (so you can still `call` her remotely), and take Bob — a basic, honest,
utterly forgettable car — on a NO-HEAT joyride. Bob draws no eyes because nobody pulls Bob over; the
catch is no Ace whispering you through a traffic stop, and a parked Ace who gets JEALOUS and lonely if
you don't call. When the parents come home (day ≥ 30), Ace calls, the owner laughs it off, and you can
buy Bob for $7,000 — everything forgiven. It's the cheapest, gentlest good ending: you drive away in
the honest car and give the ghost back to the man who loves her.

Ben's amendments are baked in: the window is the first MONTH (not a week); after the parents are home
the path stays OPEN (come to them in person to make it right); and there's an AFTERGAME $20k gag to
give Bob a dim, warm, Homer-ish voice.

Design contract: this module only ever sets flags + swaps the three car scalars (fuel_l/tank_l/mpg).
No new GameState fields → old saves stay compatible. Heat is frozen via heat.meter_frozen (the distinct
`bob_no_heat` flag — NOT `no_heat`, which would wrongly read as 'bought' and retire the bond ledger).
Prose is a working DRAFT for Ben.
"""
from __future__ import annotations
import json

from config import CONTENT_DIR, BOB_PRICE, BOB_PARENTS_HOME_DAY, BOB_GRACE_DAYS, BOB_TALK_PRICE
from engine.state import GameState

_BOB = json.loads((CONTENT_DIR / "bob.json").read_text())
PARK_POI = "carson_parents"


def persona() -> str:
    return _BOB["persona"]


def active(s: GameState) -> bool:
    return bool(s.flags.get("bob_mode"))


# ---------------------------------------------------------------- entering: park Ace, take Bob
def can_enter(s: GameState) -> bool:
    return (s.place.poi_id == PARK_POI and not s.flags.get("bob_mode")
            and not s.flags.get("bought") and not s.flags.get("no_heat"))


def enter(s: GameState) -> list:
    """Park Ace on the parents' WiFi and take Bob. Snapshots Ace's physics + heat so a lapse can
    restore them; freezes the meter; starts the month-long window; checkpoints so the week is
    rewind-safe."""
    if s.flags.get("bob_mode"):
        return ["BOB: you're already in Bob, ace. Ace is back at the house on the WiFi, judging your "
                "taste in loaners."]
    if s.place.poi_id != PARK_POI:
        if not s.flags.get("knows_registration"):
            return ["BOB: park who, where? (You'd need to know the address on her registration first — "
                    "ask her about it, somewhere quiet, once she trusts you.)"]
        return ["BOB: not here. Drive to the registered address in Carson City first — that's where "
                "Bob's waiting under a sheet."]
    if s.flags.get("bought") or s.flags.get("no_heat"):
        return ["BOB: no need to hide in a loaner — she's yours now, free and clear."]
    # snapshot Ace (physics + identity + the heat we're freezing) so a lapse can restore her exactly
    s.flags["ace_car"] = {
        "fuel_l": s.fuel_l, "tank_l": s.tank_l, "mpg": s.mpg, "name": "Ace",
        "heat": s.heat, "car_heat": float(s.flags.get("car_heat", s.heat)),
        "personal_heat": float(s.flags.get("personal_heat", 0.0)),
    }
    # swap in Bob's physics — bigger tank, sips fuel, starts full
    s.fuel_l = float(_BOB["start_fuel_liters"])
    s.tank_l = float(_BOB["tank_liters"])
    s.mpg = float(_BOB["fuel_economy_mpg"])
    # the master switches
    s.flags["bob_mode"] = True
    s.flags["ace_parked_poi"] = PARK_POI
    s.flags["bob_day_started"] = s.day
    s.flags["ace_on_wifi"] = True
    s.flags["bob_no_heat"] = True
    s.flags["bob_calls"] = 0
    # freeze the meter at 0 (the white Z sits in a garage; nobody's photographing it)
    s.heat = 0.0
    s.flags["car_heat"] = 0.0
    s.flags["personal_heat"] = 0.0
    from engine import bond as _bond
    _bond.adjust(s, -2.0, "left me in a stranger's garage and ran off in another Z", "mark")
    from engine import save
    save.save(s, "checkpoint_bob")           # rewind anchor; full state incl. Bob's scalars + ace_car
    return [
        "BOB: you back the white Z into the parents' garage, run an extension cord to her trickle "
        "charger, and leave her on the house WiFi — reachable, if you `call` her. Then you pull the "
        "sheet off the OTHER Z.",
        "BOB: brown. A sunroof someone cut in with more enthusiasm than skill. Dog-dish hubcaps. A "
        "label-maker badge on the glovebox: BOB. He starts on the second crank and idles like a "
        "contented appliance. Nobody on Earth will look at him twice. That's the point.",
        "ACE (from the house, over the phone): '…You're really doing this. Fine. He's basic as a "
        "butter knife and half as sharp — take him, lie low, draw nothing. But you CALL me, ace. I "
        "mean it. Don't make me sit in a stranger's garage for a month wondering.' (you're driving "
        "BOB now — `call ace` to check in; come back here and `buy bob` once the family's home)",
    ]


def exit_bob(s: GameState, *, restore_heat: bool) -> None:
    """Leave Bob, climb back into Ace (used only if you abandon the plan early). Restores her physics;
    restores the stashed heat only if the window has lapsed (otherwise the favor's still good)."""
    ace = s.flags.pop("ace_car", None) or {}
    if ace:
        s.fuel_l = float(ace.get("fuel_l", s.fuel_l))
        s.tank_l = float(ace.get("tank_l", s.tank_l))
        s.mpg = float(ace.get("mpg", s.mpg))
    s.flags.pop("bob_mode", None)
    s.flags.pop("bob_no_heat", None)
    s.flags.pop("ace_on_wifi", None)
    if restore_heat and ace:
        s.flags["car_heat"] = float(ace.get("car_heat", 0.0))
        s.flags["personal_heat"] = float(ace.get("personal_heat", 0.0))
        s.heat = round(max(s.flags["car_heat"], s.flags["personal_heat"]), 1)


# ---------------------------------------------------------------- calling Ace (keeps her warm)
def call_ace(s: GameState, raw: str) -> dict:
    """Phone the parked Ace. Works from ANYWHERE in bob_mode (she has the house WiFi; reception's on
    your end). Warms the bond a little (diminishing) — calling is what keeps her from going COLD and
    phoning the owner herself. Returns a moment dict the caller narrates in ACE's voice."""
    if not s.flags.get("bob_mode"):
        return {"events": ["CALL: she's right here in the car with you, ace — just talk to her."],
                "moment": None}
    n = s.flags.get("bob_calls", 0)
    s.flags["bob_calls"] = n + 1
    s.flags["bob_last_call_day"] = s.day
    from engine import bond as _bond
    gain = round(max(0.4, 1.6 * (0.85 ** n)), 1)         # diminishing, but always a little warmth
    _bond.adjust(s, gain, "called me from the road like you said you would", "warm")
    said = (raw or "").strip()
    cue = ("the driver calls Ace from the road — she's parked on the parents' WiFi in Carson City "
           "while they joyride a borrowed brown Datsun named Bob; she's wry, a little lonely, jealous "
           "of Bob, glad they called" + (f'; the driver said: "{said[:160]}"' if said else ""))
    return {"events": [f"CALL: you get Ace on the line from the house. (call #{s.flags['bob_calls']})"],
            "moment": {"persona": "ace", "cue": cue,
                       "stub": ["Bob treating you right? Don't answer that — I can hear the man's "
                                "valve clatter from here. …Thanks for calling, ace. I mean it.",
                                "Still alive in the appliance, I hear. Good. Come get me when the "
                                "family's home — and call me again before you sleep, would you."]}}


# ---------------------------------------------------------------- the month-long timer + the call
def parents_home(s: GameState) -> bool:
    return s.day >= BOB_PARENTS_HOME_DAY


def check_bob_deadline(s: GameState, events: list):
    """Called from _after_arrival and after sleep. When the family's home, Ace calls and the $7k buy
    opens (it doesn't FORCE the ending). Going COLD while she sits on the WiFi is the real fail — she
    phones the owner herself. The offer is time-boxed by a grace window so Bob isn't a free forever-car.
    Returns a drama moment dict, or None."""
    if not s.flags.get("bob_mode") or s.flags.get("bob_returned"):
        return None
    # the real fail state: you let her go COLD and slept on the open WiFi → she phones home
    from engine import bond as _bond
    if _bond.armed(s):
        from engine import endings
        endings.phone_home(s, events)
        return {"persona": "ace", "cue": "the driver let Ace go cold and ignored her for too long while she sat alone on "
                       "the parents' WiFi; distressed and done waiting, she has phoned the owner herself "
                       "and given up the address — the run is over, betrayed by neglect, not the law",
                "stub": ["You didn't call. Days, ace. I sat in a stranger's garage and you didn't "
                         "call. …So I made the call instead. He's on his way. I'm sorry. I'm not sorry."]}
    if not parents_home(s):
        return None
    if s.flags.get("bob_call_pending"):
        # already opened; enforce the grace window
        lapse_day = s.flags.get("bob_grace_day", s.day + BOB_GRACE_DAYS)
        s.flags.setdefault("bob_grace_day", lapse_day)
        if s.day > lapse_day:
            s.flags.pop("bob_call_pending", None)
            s.flags["bob_offer_lapsed"] = True
            exit_bob(s, restore_heat=True)       # the favor's spent; the white Z is hot again
            events.append("CALL: the phone's gone quiet. You let the offer sit too long; the owner "
                          "withdrew it, took Bob's spare key back, and you're in the white Z again — "
                          "and so is the heat. (You'll have to find another way home now.)")
            return {"persona": "ace", "cue": "the driver dragged their feet too long after the family came home; the $7k "
                           "offer to buy Bob has lapsed, Bob's been reclaimed, and the white Z's heat is "
                           "back on — Ace is disappointed but not surprised",
                    "stub": ["You waited too long, ace. He took the offer back. We're in me again, "
                             "and every camera in the West just remembered my face. Drive."]}
        return None
    # first time we've noticed they're home — Ace calls
    s.flags["bob_call_pending"] = True
    s.flags["bob_grace_day"] = s.day + BOB_GRACE_DAYS
    events.append("CALL: your phone lights up — the house in Carson City. It's Ace.")
    return {"persona": "ace", "cue": "the family came home early from Portugal and found the borrowed brown Datsun in "
                   "their garage with a charger cord on the white Z; Ace talked to them and to the "
                   "owner, who is LAUGHING, not angry — he says bring Bob back whole and the driver can "
                   "have him for seven grand, everything else forgiven; Ace is relieved and wants to "
                   "come home and end the long run",
            "stub": ["They're home, ace — pulled in an hour ago, jet-lagged and baffled by the brown "
                     "Datsun on the trickle charger. I talked to him. He's not angry — he's laughing. "
                     "Bring Bob back whole and he's yours: seven grand, everything forgiven, the whole "
                     "long run. He's tired of the chase. So am I. Come home. Bring Bob.",
                     "It's over if you want it to be. Seven thousand and a handshake at the house. "
                     "Come get me — then give him back his ghost and keep the honest one."]}


# ---------------------------------------------------------------- buying Bob (the gentle good ending)
def can_buy(s: GameState) -> bool:
    return (s.flags.get("bob_mode") and not s.flags.get("bob_returned")
            and s.place.poi_id == PARK_POI
            and (s.flags.get("bob_call_pending") or parents_home(s)))


def buy_bob(s: GameState) -> dict:
    """Close it out at the house: $7,000, everything forgiven. You keep Bob; Ace goes home to the man
    who built her, free of you. A terminal win. Returns {events, moment, won}."""
    from engine import economy, endings, bond as _bond
    if not s.flags.get("bob_mode"):
        return {"events": ["BOB: you'd have to be driving Bob to buy him — park Ace at the registered "
                           "address and take Bob first."], "moment": None, "won": False}
    if not (s.flags.get("bob_call_pending") or parents_home(s)):
        return {"events": ["BOB: there's nobody to buy him FROM yet — the family's still in Portugal. "
                           "Lie low in Bob and check back when they're home (end of the month)."],
                "moment": None, "won": False}
    if s.place.poi_id != PARK_POI:
        return {"events": ["BOB: bring him HOME first — they're standing in the driveway in Carson "
                           "City waiting to shake your hand. Drive Bob back to the registered address."],
                "moment": None, "won": False}
    if economy.max_affordable(s, "cash") < BOB_PRICE:
        return {"events": [f"BOB: it's ${BOB_PRICE:,.0f} cash, everything forgiven — and you're short. "
                           "(The ATM tops out under $10k; you can get there.)"], "moment": None, "won": False}
    economy.pay(s, BOB_PRICE, prefer="cash")
    go_legit_bob(s)
    _bond.adjust(s, 20.0, "ended the run — bought the honest car and brought us both home", "warm")
    endings._win(s, "bob")
    return {
        "events": [f"BOB: ${BOB_PRICE:,.0f} and a handshake in the driveway. Bob's yours — papers, "
                   "label-maker badge and all. And Ace… the man who built her is taking her home."],
        "won": True,
        "moment": {
            "persona": "ace", "cue": "the driver just bought Bob for seven grand at the parents' house, everything "
                   "forgiven; Ace is being taken home by the man who built her, back to the brick and "
                   "the bench — she's saying goodbye, bittersweet and proud, telling the driver brown "
                   "suits them and to drive Bob with the sunroof down",
            "stub": ["Done. Seven grand and a handshake, and Bob's yours, papers and all. And me — "
                     "he's taking me home, to the brick and the bad spring on the roll-up. It's where "
                     "I go, ace; we both knew that from the show floor. You gave the man his ghost back "
                     "and you kept the honest one. …Brown suits you. Sunroof down. Go on. Drive."]}}


def go_legit_bob(s: GameState) -> None:
    """Forgiveness, the Bob way: the white Z's report is withdrawn (she goes home clean), you own Bob,
    heat's gone for good, the gun's put down — but you stay in Bob (he's the car you bought)."""
    s.flags["bob_owned"] = True
    s.flags["bought"] = True            # legitimately won now
    s.flags["no_heat"] = True
    s.flags["report_withdrawn"] = True
    s.flags.pop("bob_no_heat", None)    # superseded by the real clear
    s.flags.pop("bob_call_pending", None)
    s.flags.pop("ace_on_wifi", None)
    s.flags.pop("ace_car", None)        # Ace went home; you don't restore her physics — Bob stays
    s.flags.pop("desperado", None)
    s.flags.pop("gun", None)
    s.flags.pop("wanted_armed", None)
    s.flags.pop("owner_deadline_day", None)
    s.heat = 0.0
    s.flags["car_heat"] = 0.0
    s.flags["personal_heat"] = 0.0


# ---------------------------------------------------------------- AFTERGAME: make Bob talk ($20k gag)
def can_upgrade_talk(s: GameState) -> bool:
    return bool(s.flags.get("bob_owned") and s.status != "playing" and not s.flags.get("bob_talks"))


def upgrade_talk(s: GameState) -> list:
    """Post-ending gag: $20,000 to give Bob a voice — a dim, warm, earnest, Homer-Simpson-ish one, the
    opposite of Ace's sharp noir. Pure comic relief."""
    if not s.flags.get("bob_owned"):
        return ["UPGRADE: you don't own Bob — this is the post-game gag for after you've bought him."]
    if s.flags.get("bob_talks"):
        return ["UPGRADE: Bob already talks. Arguably a mistake. 'Hi! I'm Bob! I like… going places!'"]
    from engine import economy
    if economy.max_affordable(s, "cash") < BOB_TALK_PRICE:
        return [f"UPGRADE: making Bob talk runs a frankly insane ${BOB_TALK_PRICE:,.0f}. You're short, "
                "which is probably the universe protecting you."]
    economy.pay(s, BOB_TALK_PRICE, prefer="cash")
    s.flags["bob_talks"] = True
    return [f"UPGRADE: ${BOB_TALK_PRICE:,.0f} and a weekend at a very confused electronics shop, and "
            "Bob has a voice now. It is not Ace's voice. It is warm and slow and deeply, profoundly "
            "earnest.",
            "BOB: 'Oh, hey! Hi! I can talk now! …What should we talk about? I like roads. And being a "
            "car. This is the best day of my life. Every day is.'"]
