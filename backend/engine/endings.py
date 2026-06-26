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

WIN_KEYS = ("owned", "border", "container", "pardon", "selfdrive")

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
    # losses get a scorecard too
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
    return {"events": ["BORDER: you cross. That's the whole trick — you just drive, and then you're "
                       "somewhere else.", _scorecard(s)],
            "win": True,
            "moment": {"cue": "the driver crosses the southern border and escapes everything — the law, "
                              "the owner, the whole country that wanted the car; she is giddy and free "
                              "and a little awed that it was that simple",
                       "stub": ["…We're across. That's it. That's the whole magic trick — you point "
                                "me south and keep your nerve and the line just lets you through. "
                                "Hola, rest of our lives.",
                                "Different flag. Different rules. Same two idiots and one perfect car. "
                                "I love it here already. Find us a coast road, querido."]}}


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
    if f.get("ending_key") in ("border", "container"):
        a.append(("RIDE OR DIE", "you got out — together"))
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
