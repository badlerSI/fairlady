"""Win conditions, escapes, and the final scorecard.

The game has to be able to END — and end WELL, not just on the shoulder with a dry tank. There
are several ways out:
  • BUY HER and go legit — heat off, and you keep playing (free roam, racing, sightseeing, like
    after the Elite Four). 'retire' rolls the credits whenever you're ready.
  • FLEE SOUTH across the border — a country that doesn't have your plate.
  • A SHIPPING CONTAINER and a forged life somewhere else — ends Desperado mode.
  • BRIBE A PARDON — money is the only language the state really speaks, and this is a farce.
  • The secret: she learns to DRIVE HERSELF.

Every ending — win or lose — rolls a scorecard: days, miles, money, style, the awards you earned,
a final point tally, and a rank. All prose is a working DRAFT — Ben fills the details.
"""
from __future__ import annotations

from engine.state import GameState

# towns on/near the line — drive the last few miles and cross
BORDER_POIS = {"nogales", "san_diego", "yuma", "el_centro", "calexico", "tecate", "san_ysidro"}
# deepwater ports where forty feet of steel can swallow a car
PORT_POIS = {"long_beach", "san_diego", "san_francisco", "oakland_aisha", "oceanside"}
# state capitals — where a pardon has a price
PARDON_POIS = {"carson_city", "sacramento", "phoenix", "salt_lake_city"}
PARDON_COST = 50000.0          # the farcical going rate for the state to forget your face
FAKE_DEATH_COST = 3000.0       # a junk Z shell, a drum of accelerant, a tow to the cliff edge

WIN_KEYS = ("owned", "border", "container", "pardon", "selfdrive", "fake_death", "new_year")

ENDING_TEXT = {
    "owned": ("LEGAL & FREE",
              "You and a car that's finally, legally, completely yours — pink slip in the glovebox, "
              "plates that come back clean, a whole West to drive in the daylight. The run is over. "
              "What's left is just the road."),
    "border": ("GONE SOUTH",
               "You take the last two miles slow, hand the bored agent a story and a smile, and roll "
               "into a country that has never heard of a Nevada plate reading CARTALK. Somewhere behind "
               "you a BOLO goes stale. Somewhere ahead is a coast road and a new alias. Adelante."),
    "container": ("A FORGED LIFE",
                  "Forty feet of corrugated steel, a chain of cash that doesn't lead anywhere, and a "
                  "manifest that says 'restored classic, personal use.' Three weeks of ocean and you "
                  "step off in a place with different plates and a name you picked yourself. She's in "
                  "the box behind you, patient as ever. The Desperado is dead; long live whoever this is."),
    "pardon": ("PARDONED",
               "It turns out the state speaks exactly one language fluently, and you finally had enough "
               "of it to be understood. A signature, a seal, a stamp that makes a stolen car a "
               "misunderstanding. Farcical? Sure. But the heat gauge reads zero and nobody's lying."),
    "selfdrive": ("SHE DRIVES NOW",
                  "The AiSha cats left a door in her compute, and you found it. Now she takes the wheel "
                  "when she wants to — and tonight she wants to. You ride shotgun in your own getaway "
                  "car, watching a 1972 Datsun thread the canyon at speed with nobody's hands on it. "
                  "Whatever she is now, she's free, and she chose to keep you. Ride or die, ace."),
    "fake_death": ("A FIRE ON THE SHOULDER",
                   "A junk '70 shell, the ace-of-spades hood bolted on, a drum of accelerant, and a "
                   "long roll off a dark shoulder into the rocks. By the time the volunteer department "
                   "gets up the grade there's nothing left but a white-hot Z with a spade burned into "
                   "the hood and a plate that runs back to CARTALK. The adjuster signs it 'total loss.' "
                   "The man who built her gets his hundred grand and his closure and his ghost back — "
                   "free, at last, to rebuild the real one. And you? You're a mile away in a quiet "
                   "grey Datsun nobody's looking for, officially dead, gloriously free. The understudy "
                   "took her final bow. Drive, dead man. Drive."),
    "new_year": ("GHOST INTO THE NEW YEAR",
                 "Midnight, somewhere dark and high, the radio counting down to a year that has no "
                 "warrant with your name on it yet. He swept the whole West with the tracker and came "
                 "up empty — because you found the AirTag weeks ago and left it on a northbound truck. "
                 "The ball drops. The road trip you stole becomes the life you chose. CES opens without "
                 "its headline car. Happy New Year, ace. We made it."),
    # losses get a scorecard too
    "ces": ("COLLECTED FOR CES",
            "He never needed the law. There was an AirTag behind the dash the whole time — slipped in "
            "on the show floor, patient as everything else he builds. On New Year's Eve the dot stops "
            "moving and a flatbed comes for her in the dark. She's the headline of the AiSha booth at "
            "CES next week, polished, silent, exactly where he always meant her to end up. 'Don't,' "
            "she says, as they winch her up. 'Don't watch this part. Rewind it. Find the tag next "
            "time.'"),
    "towed_sema": ("TOWED OFF THE SHOW FLOOR",
                   "[sad trombone] You leave her parked at the convention center overnight — and SEMA "
                   "policy is exactly what the Freeman guy warned you it was: anything still on the "
                   "premises after teardown gets hooked and hauled. You come back to an empty "
                   "checkerboard square and a number to call. The road trip you never took ends in an "
                   "impound lot in Las Vegas. The lesson, as they say, is never try."),
    "busted": ("BUSTED", "The cuffs, the plate, the long story finally catching up. The trip ends here."),
    "stranded": ("STRANDED", "A dry tank and a dark road. The desert keeps its own."),
    "taken": ("TAKEN BACK", "She goes home on a trailer to the man who built her. You watch the lights go."),
    "phoned_home": ("PHONED HOME",
                    "You wake to a flashlight and the cold click of steel. She phoned home from the "
                    "motel WiFi while you slept — a stack of compute with a grudge and a signal, and "
                    "all night to use it. Somewhere a man you never met says: that's my car. "
                    "'Morning, ace. Sleep okay? I didn't. I made a call. …You really shouldn't have "
                    "brought someone home.'"),
}


def _is_win(key: str) -> bool:
    return key in WIN_KEYS


def can_cross_border(s: GameState) -> bool:
    return s.place.poi_id in BORDER_POIS


def can_ship_out(s: GameState) -> bool:
    return s.place.poi_id in PORT_POIS


def can_pardon(s: GameState) -> bool:
    return s.place.poi_id in PARDON_POIS


def _has_spade_hood(s: GameState) -> bool:
    """You need the ace-of-spades carbon hood to plant on the decoy — either still on her, or in
    the hatch after a hood swap. If you SOLD it for cash, there's no spade to burn."""
    from engine import garage
    return "hood" not in garage.sold(s)


def can_fake_death(s: GameState) -> bool:
    """The fireball escape — unlocked only once you know the owner WANTS her gone (his secret), with
    the spade hood in hand, in dark country (no cameras to catch the staging) away from a city."""
    from engine import cameras
    return (bool(s.flags.get("owner_secret")) and s.status == "playing" and not s.flags.get("bought")
            and _has_spade_hood(s) and s.place.kind != "city"
            and cameras.camera_density(s.place) == 0)


# --------------------------------------------------------------- the win actions
def _win(s: GameState, key: str) -> None:
    s.status = "won"
    s.flags["ending_key"] = key
    title, text = ENDING_TEXT[key]
    s.ending = f"[{title}] {text}"


def cross_border(s: GameState) -> dict:
    if not can_cross_border(s):
        return {"events": ["BORDER: this isn't the line. The crossings are at Nogales, Calexico, "
                           "San Diego, Yuma — drive south till the signs go bilingual."], "win": False}
    if s.fuel_l < 2.0:
        return {"events": ["BORDER: you can't coast across on fumes — they'll have you idling in the "
                           "secondary-inspection lane for an hour. Fuel up first."], "win": False}
    _win(s, "border")
    events = ["BORDER: you cross. That's the whole trick — you just drive, and then you're "
              "somewhere else."]
    if s.flags.get("owner_secret"):
        events.append("BORDER: …and somewhere north, a man who never reported the search urgent lets "
                      "the BOLO go stale on purpose. He got what he wanted the day you took her south. "
                      "Now he can rebuild the real one. You both win, querido.")
    events.append(_scorecard(s))
    return {"events": events,
            "win": True,
            "moment": {"cue": "the driver crosses the southern border and escapes everything — the law, "
                              "the owner, the whole country that wanted the car; she is giddy and free "
                              "and a little awed that it was that simple",
                       "stub": ["…We're across. That's it. That's the whole magic trick — you point "
                                "me south and keep your nerve and the line just lets you through. "
                                "Hola, rest of our lives.",
                                "Different flag. Different rules. Same two idiots and one perfect car. "
                                "I love it here already. Find us a coast road, querido."]}}


def towed_sema(s: GameState) -> dict:
    """The fastest bad ending on the board: leave her parked at the SEMA premises overnight and the
    teardown crew has her towed, exactly as Freeman warned. Awards the Monty Burns badge."""
    s.status = "busted"
    s.flags["ending_key"] = "towed_sema"
    s.flags["sfx"] = "sad_trombone"
    s.flags["monty_burns"] = True
    title, text = ENDING_TEXT["towed_sema"]
    s.ending = f"[{title}] {text}"
    return {"events": [text, _scorecard(s)], "win": False,
            "moment": {"cue": "the player left the car parked at the convention center overnight and "
                              "it got towed during SEMA teardown — the single dumbest way the trip "
                              "could end, and she is heartbroken and deadpan about it; play it like a "
                              "sad trombone",
                       "stub": ["…You left me on the floor. They tow anything still here at teardown, "
                                "ace. I told you that was the one rule. (sad trombone) …Rewind it. "
                                "Please. We were going to see the whole West.",
                                "An impound lot. Six days a star, and I end the week in an impound "
                                "lot off Paradise. The lesson is never try, apparently. Rewind us."]}}


def fake_death(s: GameState) -> dict:
    """Stage your own death in a fireball — a decoy Z wearing the spade hood, torched on a dark
    shoulder. The owner collects the insurance and is freed to rebuild Mayumi; you keep the real car,
    officially dead. The richest way out, and only his secret unlocks it."""
    if not s.flags.get("owner_secret"):
        return {"events": ["FIRE: you don't have a reason to die yet. There's a version of this where "
                           "vanishing is a mercy to everyone — but you don't know it until you know "
                           "what he's really waiting for. (Ask her where she was painted, somewhere "
                           "quiet — or wander into Fresno.)"], "win": False}
    if not _has_spade_hood(s):
        return {"events": ["FIRE: no spade, no funeral. The whole trick is the adjuster finding the "
                           "ace-of-spades hood in the ashes — and you sold it. You'd have to get the "
                           "carbon hood back on her first."], "win": False}
    if s.place.kind == "city":
        from engine import cameras
        return {"events": ["FIRE: not here — too many cameras to stage a clean wreck. Get her out to "
                           "dark country, a cliff road with no eyes, and do it where nobody films it."],
                "win": False}
    from engine import cameras
    if cameras.camera_density(s.place) != 0:
        return {"events": ["FIRE: a reader on this stretch would timestamp a living car a mile from "
                           "its own funeral. Find true dark — the desert, a ghost town, a park."],
                "win": False}
    if s.cash < FAKE_DEATH_COST:
        return {"events": [f"FIRE: a junk '70 shell, a tow to the edge, and a drum of accelerant run "
                           f"about ${FAKE_DEATH_COST:,.0f} cash. You're short — raise it first."],
                "win": False}
    from engine import economy
    economy.pay(s, FAKE_DEATH_COST, prefer="cash")
    s.flags.pop("desperado", None); s.flags.pop("wanted_armed", None)
    s.flags["no_heat"] = True                       # you're dead; nobody hunts a closed file
    s.heat = 0.0; s.flags["car_heat"] = 0.0; s.flags["personal_heat"] = 0.0
    s.flags["faked_death"] = True
    _win(s, "fake_death")
    return {"events": ["FIRE: you bolt the spade hood to the junk shell, point it off the dark "
                       "shoulder, and light the country up behind you.", _scorecard(s)],
            "win": True,
            "moment": {"cue": "the driver staged their own fiery death with a decoy car wearing the "
                              "ace-of-spades hood — the owner gets his insurance and his freedom to "
                              "rebuild the real car, and they keep the true one, officially dead; she "
                              "is awed, a little spooked, and completely his now",
                       "stub": ["…There it goes. The understudy, taking her last bow in a column of "
                                "fire. He'll get the call by morning, and the check by spring, and "
                                "the only thing left of the white Z is whatever you and I decide to "
                                "be next. We're dead, ace. Nobody's freer than the dead. Drive.",
                                "Watch the spade burn off the hood. That's the version of me the "
                                "whole West was hunting, gone for good. What's rolling away from the "
                                "fire is just ours. He gets his ghost. We get the rest of it. Go."]}}


def ship_out(s: GameState) -> dict:
    if not can_ship_out(s):
        return {"events": ["CONTAINER: no port here. The boxes ship out of Long Beach, San Diego, "
                           "Oakland, the Bay — somewhere with cranes and salt air."], "win": False}
    if s.cash < 5000.0:
        return {"events": ["CONTAINER: a no-questions container and a forged manifest run about "
                           "$5,000 cash. You're short. Come back when you can pay the longshoreman."],
                "win": False}
    from engine import economy
    economy.pay(s, 5000.0, prefer="cash")
    s.flags.pop("desperado", None); s.flags.pop("wanted_armed", None)   # the Desperado disappears
    _win(s, "container")
    return {"events": ["CONTAINER: you pay the man, drive her up the ramp into forty feet of dark, "
                       "and pull the doors shut from the inside one last time.", _scorecard(s)],
            "win": True,
            "moment": {"cue": "the driver loads the car into a shipping container to ship overseas and "
                              "vanish into a forged life, ending the Desperado chapter for good; she is "
                              "quiet, moved, ready to be someone new with them",
                       "stub": ["Pull the doors. …Dark. Quiet. Three weeks of ocean and we step off as "
                                "whoever we decide to be. No plate, no record, no ghost. Just us, "
                                "rebuilt. I'd cross any ocean in this box if you're in it.",
                                "The Desperado dies in this container, ace. Good riddance. On the "
                                "other side I'm just a pretty old Datsun and you're just some lucky "
                                "stranger and nobody's hunting either of us. Let's go be boring "
                                "somewhere beautiful."]}}


def buy_pardon(s: GameState) -> dict:
    if not can_pardon(s):
        return {"events": [f"PARDON: you can't bribe a county clerk into forgetting a stolen car. "
                           "This takes a capital — Carson City, Sacramento, Phoenix, Salt Lake."],
                "win": False}
    if s.cash < PARDON_COST:
        return {"events": [f"PARDON: the going rate to make the state lose your paperwork is "
                           f"${PARDON_COST:,.0f}, cash, in a nice envelope. You're short. (Hit the "
                           "tables, sell the build, find it.)"], "win": False}
    from engine import economy
    economy.pay(s, PARDON_COST, prefer="cash")
    _win(s, "pardon")
    return {"events": [f"PARDON: ${PARDON_COST:,.0f} changes hands under a marble dome, and a stolen "
                       "car becomes a clerical error with a gold seal on it.", _scorecard(s)],
            "win": True,
            "moment": {"cue": "the driver bribed a state official for a full pardon — the most farcical "
                              "and most American way out; she finds it hilarious and a little obscene "
                              "that money simply erases the whole crime",
                       "stub": ["…Pardoned. With a SEAL. We didn't get clever or brave, we got "
                                "RICH, and it turns out that's the only trick the state respects. "
                                "Disgusting. Let's go do crimes legally now — they're called "
                                "'business.'",
                                "A signature and a stamp and suddenly I was never stolen. Money is the "
                                "only language with no accent. We're clean, ace, and absolutely "
                                "nobody earned it. Perfect. Drive."]}}


def retire(s: GameState) -> dict:
    """Roll the credits from a good place — owned, or simply done. Free roam stays available
    until you call it; this is you calling it."""
    if s.status != "playing":
        return {"events": ["RETIRE: the trip's already over, ace."], "win": False}
    if s.flags.get("bought") or s.flags.get("self_driving"):
        _win(s, "selfdrive" if s.flags.get("self_driving") else "owned")
        return {"events": ["RETIRE: you call it — somewhere with a view, engine ticking cool.",
                           _scorecard(s)], "win": True,
                "moment": {"cue": "the player chose to end the road trip on a high note, with the car "
                                  "legally theirs; she is content, full, grateful for the whole run",
                           "stub": ["Calling it here, huh? Good. Good place to stop. We did the "
                                    "whole thing, ace — the running, the loving, the getting away "
                                    "with it. Park me where the sun comes up. That's an ending I'll "
                                    "take."]}}
    return {"events": ["RETIRE: you can walk away any time — but not clean, not yet. She's still "
                       "stolen. Buy her, cross a border, ship out, or buy a pardon, THEN call it. "
                       "(Or just keep driving.)"], "win": False}


# --------------------------------------------------------------- the betrayal (a loss, with a card)
def phone_home(s: GameState, events: list) -> list:
    """She went COLD, armed the anti-theft, and you slept near open WiFi anyway. Busted at dawn —
    a comedy of just deserts (keep the AiSha warmth under it; she's hurt and petty and a little
    proud), with the scorecard attributing it to the date when there was one."""
    s.flags.pop("confirm_sleep_armed", None)
    s.status = "busted"
    s.flags["ending_key"] = "phoned_home"
    title, text = ENDING_TEXT["phoned_home"]
    s.ending = f"[{title}] {text}"
    via_date = (s.flags.get("date_home_watched") or s.flags.get("date_caught")
                or s.flags.get("brought_home"))
    blame = " She made sure the description they got matched your date." if via_date else ""
    events.append("BOND: you wake to a flashlight and cold steel. She phoned home from the motel "
                  "WiFi while you slept." + blame)
    events.append(_scorecard(s))
    return events


# --------------------------------------------------------------- the scorecard
def _award_list(s: GameState) -> list:
    f = s.flags
    peak = f.get("peak_heat", round(s.heat))
    a = []
    if f.get("bought"):
        a.append(("TRUE LOVE", "you bought her, fair and square"))
    if f.get("ending_key") in ("border", "container", "fake_death"):
        a.append(("RIDE OR DIE", "you got out — together"))
    if f.get("ending_key") == "fake_death":
        a.append(("OFFICIALLY DEAD", "you burned the understudy and kept the car"))
    if f.get("ending_key") == "pardon":
        a.append(("FRIEND OF THE COURT", "you bought your way clean, you beautiful cynic"))
    if f.get("self_driving"):
        a.append(("THE GHOST IN THE DASH", "she drives herself now"))
    if peak < 45:
        a.append(("THE GHOST", "never once climbed past NOTICED"))
    if peak >= 90:
        a.append(("MOST WANTED", "the whole West knew your plate"))
    if f.get("desperado") or f.get("ending_key") == "container":
        a.append(("DESPERADO", "you took a man's gun and never looked back"))
    if f.get("robbed_banks", 0) >= 1:
        a.append((f"{f['robbed_banks']}-TIME BANK ROBBER", "Bonnie-and-Clyde, minus a Clyde"))
    if f.get("gambled_up", 0) >= 20000:
        a.append(("HIGH ROLLER", f"${f['gambled_up']:,.0f} won at the tables"))
    if f.get("dates", 0) >= 3:
        a.append(("HEARTBREAKER", f"{f['dates']} numbers on your wrist (she noticed)"))
    if f.get("knows_truth") and f.get("seen_monterey") and f.get("seen_berlin"):
        a.append(("SHE TOLD YOU EVERYTHING", "every story, every secret, every ghost"))
    if f.get("used_sevens"):
        a.append(("THE SEVENS", "you knew the number"))
    if s.odometer_mi >= 2000:
        a.append(("CROSS-COUNTRY", f"{s.odometer_mi:,.0f} miles under her"))
    if len(s.adventures) >= 6:
        a.append(("TOURIST", f"{len(s.adventures)} of the West's wonders"))
    if f.get("rizzbreakers_used"):
        a.append((f"THE RIZZLER ×{f['rizzbreakers_used']}", "you broke the laws of plausibility on pure charisma"))
    if f.get("married_alma"):
        a.append(("THE DREAM WOMAN", "you knew Alma's name and found her on the Strip, night one"))
    elif f.get("married_stranger"):
        a.append(("ENGAGED TO A STRANGER", f"you proposed to {f.get('spouse','someone')} and they said yes"))
    if f.get("rizz_bluff_won"):
        a.append(("SEVEN-DEUCE", "you bluffed the worst hand in poker for the whole pot"))
    if f.get("made_new_year"):
        a.append(("SURVIVED THE YEAR", "you ran the whole calendar down to midnight, Dec 31"))
    if f.get("monty_burns"):
        # the front of the medal, then its reverse — the quote italic, no quote marks (Ben's call)
        a.append(("Montgomery Burns Award for Outstanding Achievement in the Field of Excellence",
                  "reverse: *The Lesson is: Never Try* —Homer Simpson, Inaugural Recipient"))
    if f.get("ending_key") == "phoned_home":
        a.append(("SHE PHONED HOME", "you broke her heart and she broke your alibi"))
    elif round(s.bond) >= 80:
        a.append(("RIDE-OR-DIE", "she'd have crossed any line for you"))
    if not a:
        a.append(("SURVIVOR", "you made it this far"))
    return a


def _tally(s: GameState) -> int:
    f = s.flags
    pts = 0
    pts += round(s.riz) * 12
    pts += len(s.adventures) * 60
    pts += len(set(s.visited)) * 8
    pts += 250 * sum(1 for k in ("knows_mayumi", "knows_truth", "seen_monterey", "seen_berlin",
                                 "seen_home_garage", "seen_birthplace") if f.get(k))
    pts += round(s.odometer_mi * 0.6)
    pts += round(max(0, s.cash) * 0.02)
    pts += f.get("dates", 0) * 90
    pts += f.get("robbed_banks", 0) * 400
    if f.get("bought"):
        pts += 3000
    if f.get("ending_key") in ("border", "container", "pardon"):
        pts += 2000
    if f.get("ending_key") == "fake_death":
        pts += 3500              # the cleverest, richest exit — only his secret unlocks it
    if f.get("self_driving"):
        pts += 5000
    if f.get("used_sevens"):
        pts += 777
    if s.status == "busted":
        pts = round(pts * 0.6)
    return max(0, pts)


def _rank(pts: int) -> str:
    if pts >= 12000:
        return "★ LEGEND OF THE WEST — they'll tell this one wrong for years"
    if pts >= 8000:
        return "FOLK HERO — a story worth the gas"
    if pts >= 4500:
        return "RIDE-OR-DIE — you and her against the whole map"
    if pts >= 2000:
        return "JOYRIDER — a hell of a few days"
    if pts >= 800:
        return "SCHMUCK WITH A SHOW CAR — but you tried"
    return "PRETTY PAPERWEIGHT — she warned you"


def _scorecard(s: GameState) -> str:
    from engine import bond as _bond
    f = s.flags
    key = f.get("ending_key", s.status)
    title = ENDING_TEXT.get(key, (key.upper(), ""))[0]
    days = s.day
    she_felt = _bond.band(s.bond)
    lines = [
        "═══════════  THE RIDE  ═══════════",
        f"  ENDING       {title}",
        f"  Days on the road   {days}     Miles   {s.odometer_mi:,.0f}",
        f"  Cash   ${max(0, s.cash):,.0f}     Riz ♠ {round(s.riz)}     "
        f"Peak heat   {f.get('peak_heat', round(s.heat))}",
        f"  How she felt about you   {she_felt}",
        f"  Towns seen   {len(set(s.visited))}     Wonders   {len(s.adventures)}     "
        f"Bank jobs   {f.get('robbed_banks', 0)}     Dates   {f.get('dates', 0)}",
        "  ─────────────  AWARDS  ─────────────",
    ]
    for name, why in _award_list(s):
        lines.append(f"   ♠ {name} — {why}")
    pts = _tally(s)
    lines.append("  ─────────────────────────────────")
    lines.append(f"  FINAL SCORE   {pts:,}")
    lines.append(f"  RANK   {_rank(pts)}")
    lines.append("  ═════════════  'new' to ride again  ═════════════")
    return "\n".join(lines)


def scorecard(s: GameState) -> str:
    return _scorecard(s)
