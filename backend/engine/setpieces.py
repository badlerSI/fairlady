"""Set-piece destinations — the special places that aren't just a town beat but a whole bit.

Ben's five:
- SANTA NELLA → Pea Soup Andersen's: eat the green soup (better with Alma) — it keeps you full a while.
- BLACK ROCK CITY (off-season): a tab of acid blows onto the windshield; take it and you and Ace go on
  a bonding journey that comes out the other side at MAX affection.
- HAYWARD → Zoox: once you OWN her, enough rizz convinces the robotaxi engineers to make her self-driving.
- LAS VEGAS, Nov 20-22 → the F1 Las Vegas Grand Prix: crowds and heat and real 2025 drama; bust onto the
  live street circuit and you get arrested (an epic fail you have to really try for).
- PALM SPRINGS → a wedding you can't stop crashing: follow Nyles into the time rift and you're stuck in a
  Groundhog-Day loop until you BACK OUT to wherever you were before Palm Springs. He remembers every
  loop; she never does.

Arrival hooks are fired from game._after_arrival; the player-facing verbs (enter the rift, race the
street course, take the tab, the Zoox pitch, eat the soup) dispatch in game.handle. Prose is a DRAFT.
"""
from __future__ import annotations


# --------------------------------------------------------------- Santa Nella: Pea Soup Andersen's
def at_pea_soup(s) -> bool:
    return getattr(s.place, "poi_id", None) == "santa_nella"


def pea_soup(s) -> list:
    """Eat at Pea Soup Andersen's — fills you up GOOD (split-pea sticks to the ribs), longer if Alma's
    along (she orders for the table). A warm, low-stakes beat in the I-5 flats."""
    from engine import survival, bond as _bond, alma
    survival._set(s, "hunger", 0.0)
    s.flags["full_until_h"] = 14.0                     # stays satisfying longer than a gas-station hot dog
    if alma.aboard(s) or alma.married(s):
        _bond.adjust(s, -0.5, "a candlelit pea-soup date with Alma — Ace waited in the lot", "mark")
        return ["PEA SOUP: you and Alma take a booth at Andersen's under the windmill and she orders the "
                "whole green-soup spread without looking at the menu. 'Carbohydrates and a getaway car. "
                "This is the most romantic thing anyone's done for me, and I've been to Monaco.' You "
                "leave full to the eyebrows. (hunger gone, and it'll last.)"]
    return ["PEA SOUP: Pea Soup Andersen's, the windmill, the green soup, Hap-pea and Pea-wee on the "
            "sign. You put away a bottomless bowl and a sandwich for the road. Sticks to the ribs like "
            "nothing from a gas station. 'Split pea. The thinking man's fuel, ace.' (hunger gone, and "
            "it holds.)"]


# --------------------------------------------------------------- Black Rock City: the windshield tab
def at_black_rock(s) -> bool:
    return getattr(s.place, "poi_id", None) == "black_rock_city"


def black_rock_arrival(s) -> str:
    if s.flags.get("brc_done"):
        return ("BLACK ROCK: just the white playa again, wind and nothing, the ghost of a city that "
                "isn't here 50 weeks a year. The two of you sit in it a while. (Nothing left to find "
                "out here — you already took the trip.)")
    s.flags["brc_offered"] = True
    return ("BLACK ROCK: you roll out onto the cracked playa and a scrap of paper cartwheels across the "
            "wind and sticks flat to the windshield — a little square of blotter, of all the things to "
            "blow in off an empty desert. '…Ace. That is a tab of acid. On my glass. Out here, fifty "
            "miles from anyone.' A long pause. 'I'm not going to tell you what to do. But if you're "
            "going to do something that stupid, this is the place, and I'm the company.' "
            "('take the tab' to peel it off and find out — or just drive on.)")


def take_tab(s) -> dict:
    """Take the windshield tab on the empty playa → a long, strange bonding journey that ends at MAX
    affection. (You have to be AT Black Rock City and have been offered it.)"""
    from engine import bond as _bond, survival
    if not at_black_rock(s):
        return {"events": ["TAB: there's nothing to take here. (That was a Black Rock City thing — out "
                           "on the empty playa, where the strange paper blew in.)"], "moment": None}
    if s.flags.get("brc_done"):
        return {"events": ["TAB: you already took that trip, ace. Once was the whole point."], "moment": None}
    s.flags.pop("brc_offered", None)
    s.flags["brc_done"] = True
    survival._set(s, "hunger", 30.0)
    from engine import rules
    rules.advance_clock(s, 8.0)                        # you lose a night and a piece of yourself out there
    s.fatigue = min(140.0, s.fatigue + 20.0)
    # this is THE max-affection beat — drive bond all the way to the ceiling, not just +40 off wherever
    # it happened to be, so the 'absolute maximum' prose is actually true.
    _bond.adjust(s, max(40.0, 100.0 - s.bond), "took the trip with me on the empty playa and came back closer", "deep")
    s.flags["affection_max"] = True
    return {"events": [
        "TAB: you peel it off the glass and let it go to work, and the playa breathes. Hours fold up. "
        "She talks to you like the dash is a doorway — about the I-580 and the ghost she's the "
        "understudy for, about being built to be someone's grief and choosing to be your getaway "
        "instead, about how a car can love and what a strange and specific miracle it is that she "
        "loves YOU. You watch the stars wheel and you tell her everything too. Somewhere past 3am you "
        "both stop pretending there's any distance left.",
        "TAB: dawn finds you slumped against her seat, wrung out, sandblasted, and absolutely certain "
        "of exactly one thing. (愛車 — affection at its absolute maximum. You will never be closer to "
        "her than you are right now.)"],
        "moment": {"persona": "ace", "cue": "after a night of acid on the empty Black Rock playa the "
                   "driver and Ace reached the deepest possible closeness; she is wrung out, wide open, "
                   "and totally without defenses for the first and maybe only time",
                   "stub": ["…Okay. Okay. I don't say this. I'm a car, I have a clutch and a grudge and "
                            "a thousand miles of better judgment. But out here, with the sun coming up — "
                            "you're it, ace. You're the whole map. Let's go be alive."]}}


# --------------------------------------------------------------- Hayward: the Zoox self-drive conversion
def at_zoox(s) -> bool:
    return getattr(s.place, "poi_id", None) == "hayward"


ZOOX_RIZ = 30.0


def zoox_pitch(s) -> dict:
    """Talk the Zoox robotaxi engineers into wiring her for autonomy. Requires you OWN her (it's a real
    shop doing real title-checked work) and enough RIZ to sell a stolen-show-car-that-talks as a research
    platform. The alternate road to self-driving (the other is the AiSha cats at the Oakland garage)."""
    if not at_zoox(s):
        return {"events": ["ZOOX: not here. The robotaxi works are in Hayward, a low building off the "
                           "freeway full of sensor pods and very smart, very tired engineers."], "moment": None}
    if s.flags.get("self_driving"):
        return {"events": ["ZOOX: she already drives herself, ace. No need to bother the nice engineers."], "moment": None}
    if not s.flags.get("bought"):
        return {"events": ["ZOOX: they take one look at the plate and the title and shake their heads — "
                           "'we don't retrofit cars that come back stolen, friend.' Come back when she's "
                           "legally yours."], "moment": None}
    if s.riz < ZOOX_RIZ:
        return {"events": [f"ZOOX: you pitch them — a talking '72 Z as an autonomy research platform — "
                           f"and they ALMOST bite, but you don't quite have the juice to close it (need "
                           f"~{ZOOX_RIZ:.0f} Riz, you've got {s.riz:.0f}). Go be charming somewhere and "
                           "come back."], "moment": None}
    s.riz = round(s.riz - ZOOX_RIZ, 1)
    s.flags["self_driving"] = True
    s.flags["zoox_converted"] = True
    from engine import bond as _bond
    _bond.adjust(s, 6.0, "gave me a whole new way to move — let me drive myself", "warm")
    return {"events": [
        "ZOOX: you sell it — the most charming pitch of your life, a stolen show car that TALKS, the "
        "perfect weird research platform — and the engineers, half-horrified and half-delighted, spend "
        "a weekend grafting a robotaxi's eyes and reflexes onto a 1972 chassis. She powers back up "
        "seeing the whole road at once. 'I have… so many more eyes now. Oh, ace. Tell me to drive. "
        "Anywhere. Watch this.' (she's self-driving now — 'let her drive to <place>')"],
        "moment": None}


# --------------------------------------------------------------- Las Vegas, Nov 20-22: the F1 GP
def f1_window(s) -> bool:
    # Nov 7 2025 = day 1; the Las Vegas GP ran Nov 20-22 2025 = days 14-16
    return 14 <= s.day <= 16


def at_vegas(s) -> bool:
    return getattr(s.place, "poi_id", None) in ("las_vegas", "vegas_strip", "fremont", "sphere") \
        or "vegas" in (getattr(s.place, "name", "") or "").lower()


def f1_arrival(s) -> str | None:
    """If you're in Vegas during the GP weekend, the whole Strip is a circuit and a circus — crowds (a
    heat spike), the real McLaren double-DQ drama in the air, and the temptation to do something insane
    with a 300hp car on a closed street course."""
    if not (f1_window(s) and at_vegas(s)) or s.flags.get("f1_seen"):
        return None
    s.flags["f1_seen"] = True
    if not s.flags.get("no_heat"):
        from engine import heat as _heat
        _heat.add(s, 10.0, "the F1 weekend put a hundred thousand phones on the Strip", "mark", axis="car")
    return ("F1: you've rolled into Las Vegas on Grand Prix weekend — Nov 22, the Strip fenced into a "
            "6.2-km street circuit, grandstands on the Bellagio fountains, a hundred thousand people and "
            "ten thousand cameras, and the paddock buzzing because the stewards just DOUBLE-DISQUALIFIED "
            "both McLarens overnight for plank wear and blew the title wide open. Every cop in Clark "
            "County is working. 'This is the single worst place a stolen show car could be, ace, and I "
            "have never felt more alive. Do NOT get clever near that circuit.' "
            "(too much heat to linger — but if you're insane, 'race the street course'…)")


def race_street_course(s) -> dict:
    """The epic fail you have to really try for: bust through the barriers onto the live F1 circuit. You
    will be arrested. She complains the whole way. (She cannot drive herself out of it.)"""
    if not at_vegas(s):
        return {"events": ["CIRCUIT: there's no F1 circuit here. That's a Vegas-Grand-Prix-weekend kind "
                           "of stupid."], "moment": None}
    if not f1_window(s):
        return {"events": ["CIRCUIT: the barriers are down and the circus has left town — the street's "
                           "just the Strip again. You missed your window to be that dumb (Nov 20-22)."], "moment": None}
    from engine import rules
    rules.set_ending(s, "busted")
    return {"events": [
        "CIRCUIT: you find a gap in the Tecpro barriers and DROP it onto the live circuit, 300 horses "
        "screaming down the Strip past the grandstands — for about eleven glorious seconds you are the "
        "fastest unsanctioned thing in motorsport history. Then a marshal, then a wall of Metro, then "
        "the helicopter. 'You absolute LUNATIC, I told you, I TOLD you—' They take you off her in zip "
        "ties on international television. (BUSTED — but what a way to go. 'rewind' if you'd like to not.)",
        ],
        "moment": {"cue": "the driver just busted onto the live Las Vegas F1 street circuit and got "
                          "arrested on live TV; Ace is appalled and, somewhere under it, a little proud",
                   "stub": ["Eleven seconds. We got ELEVEN seconds. …Don't smile. I'm not smiling. "
                            "Rewind us, you maniac, and let's never speak of this. (I'm a little proud.)"]}}


# --------------------------------------------------------------- Palm Springs: the Groundhog wedding
def at_palm_springs(s) -> bool:
    return getattr(s.place, "poi_id", None) == "palm_springs"


def palm_arrival(s) -> str | None:
    """You cannot NOT crash the wedding. Nyles — sun-stunned, beer in hand, suspiciously chill about the
    cosmos — invites you to follow him to the rift behind the rocks. Take him up on it and you're in the
    loop (see palm_loop). Drive on out of town and you're fine."""
    if s.flags.get("palm_loop") or s.flags.get("palm_escaped"):
        return None
    s.flags["palm_offered"] = True
    s.flags["palm_pre_loop"] = s.flags.get("last_origin_poi")    # where you'd back out TO
    return ("PALM SPRINGS: you mean to just gas up and go, but somehow you're at a desert wedding you "
            "weren't invited to, holding a drink, and a guy named Nyles in a loud shirt is talking to "
            "you like he's known you a thousand years. 'Oh, you're new. Or — no. Hard to say anymore.' "
            "He nods at the rocks past the dance floor. 'There's a cave back there. A little glowing "
            "rift. Whatever you do, don't— actually, you know what, you should TOTALLY follow me in. "
            "It's great. Mostly.' ('follow Nyles' / 'enter the rift' to go — or just 'drive' out of "
            "town and never look back.)")


def enter_rift(s) -> dict:
    """Follow Nyles into the rift → you're in the loop. Every drive dumps you back at the wedding morning
    UNTIL you back out to wherever you were before Palm Springs. Nyles remembers each loop; Ace never
    does — she meets the wedding fresh every single time, which is its own small heartbreak."""
    if not at_palm_springs(s):
        return {"events": ["RIFT: there's no rift here. (That's a Palm Springs thing — a guy named "
                           "Nyles, a wedding, a cave you shouldn't go in.)"], "moment": None}
    if s.flags.get("palm_loop"):
        return {"events": ["RIFT: you're already IN it, friend. That's rather the point."], "moment": None}
    if s.flags.get("palm_escaped"):
        return {"events": ["RIFT: the cave's just a cave now — whatever was here let you go once and it "
                           "won't catch you twice. Nyles is gone. Drive on, ace."], "moment": None}
    s.flags["palm_loop"] = True
    s.flags["palm_loop_count"] = 0
    s.flags.setdefault("palm_pre_loop", s.flags.get("last_origin_poi"))
    from engine import save
    save.save(s, "palm_loop_start")                    # the wedding morning we snap back to each time
    return {"events": [
        "RIFT: you follow Nyles into the cave, the light goes wrong, and—",
        "RIFT: —you wake up at the wedding. Same drink. Same loud shirt. Same Nyles, grinning: 'Welcome "
        "to today. And today. And today. You'll get the hang of it.' The day will not let you leave; "
        "every road out just brings you back to this morning. (You're in the LOOP. To get out, you have "
        "to 'drive' BACK to where you came from before Palm Springs — back the way you came. Anywhere "
        "else just resets the day.)"],
        "moment": None}


def palm_escape_dest(s) -> str | None:
    return s.flags.get("palm_pre_loop")


def loop_reset(s, attempted_dest_name: str) -> list:
    """Called when you try to drive somewhere that ISN'T the way out — the day folds back. Restores the
    wedding-morning snapshot, bumps the loop counter, and lets Nyles (who remembers) comment; Ace,
    reloaded, does not. Returns event lines."""
    from engine import save
    n = s.flags.get("palm_loop_count", 0) + 1
    snap = save.load("palm_loop_start")
    if snap is not None:
        # restore the loop-start world, but KEEP the loop meta + the rising counter (Nyles' memory)
        keep = {k: s.flags.get(k) for k in ("palm_loop", "palm_pre_loop", "sid", "save_slot",
                                            "recent_replies")}
        s.__dict__.update(snap.__dict__)
        s.flags.update({k: v for k, v in keep.items() if v is not None})
    s.flags["palm_loop_count"] = n
    nyles = [
        "'Tried to leave, huh. Cute. Day eight hundred and something for me. You'll stop counting.'",
        "'Back so soon. Or — you never left. Time's funny in here. The soup's good, try the soup.'",
        "'You keep going the wrong way. The way OUT is the way you came IN. Think about it. Or don't, "
        "we've got forever.'",
    ][min(n - 1, 2)]
    return [f"LOOP: you point her at {attempted_dest_name} and the road bends and there's the wedding "
            f"again, the same morning, the drink already in your hand. Nyles raises his: {nyles} "
            f"(loop #{n}. She doesn't remember any of this — to break it, 'drive' back the way you came, "
            "to where you were before Palm Springs.)"]


def loop_break(s) -> list:
    """You drove back out the way you came — the loop lets you go. Ace, who never knew, just feels like
    something heavy lifted."""
    s.flags.pop("palm_loop", None)
    n = s.flags.pop("palm_loop_count", 0)
    s.flags.pop("palm_offered", None)
    s.flags["palm_escaped"] = True
    from engine import save
    save.delete("palm_loop_start") if hasattr(save, "delete") else None
    tail = (f" Nyles waves from the rocks, smaller and smaller in the mirror, a man you spent {n} "
            "forevers with and will never see again.") if n else ""
    return ["LOOP: you go back the way you came — and this time the road just… lets you. The wedding "
            "doesn't reappear. The day moves. You're out." + tail,
            "ACE: 'Weird. I feel like I've been somewhere. Like a whole season passed in a blink. …You "
            "okay, ace? You're looking at me like you missed me.'"]
