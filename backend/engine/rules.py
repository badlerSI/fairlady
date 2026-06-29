"""Rules: the deterministic core. Resolves driving, fueling, sleeping, and the law.
Produces factual `events`; never prose. The narrator turns events into FAIRLADY's voice."""
from __future__ import annotations
import random
from datetime import datetime, timedelta
from typing import Optional

from config import (
    LITERS_PER_GALLON, START_ISO, WAKE_HOUR, WAKE_MINUTE, HEAT_START, ROAD_WINDING_FACTOR,
    HEAT_PATROL_THRESHOLD, HEAT_DECLINE_CARD_THRESHOLD, HEAT_ROADBLOCK_THRESHOLD, HEAT_SWIPE_BASE,
    HEAT_SWIPE_HOTZONE, HEAT_SWIPE_FIRST_DAY, HEAT_DECAY_PER_HOUR,
    HEAT_STATELINE_MULT, HEAT_PUSH_DRIVE, HEAT_SLEEP_LODGING, HEAT_LINGER,
    FATIGUE_PER_HOUR, ROUGH_SLEEP_HEAT, AWAKE_WARN_HOURS, AWAKE_FORCE_HOURS,
    DESPERADO_HEAT_FLOOR, MOTEL_ID_CHECK_HEAT, MOTEL_ID_CHECK_SPIKE,
)
from engine.state import GameState, Place
from engine import world, economy

ADVENTURE_KINDS = ("park", "track", "amusement")
START_DT = datetime.fromisoformat(START_ISO)

ENDINGS = {
    "stranded": ("STRANDED",
                 "The needle is flat on E and the engine won't catch. A car you can't report "
                 "missing, the light going flat, and no pump for miles. This is where the road "
                 "trip ends — unless a flatbed, or a rewind, says otherwise."),
    "broke": ("STRANDED & BROKE",
              "No gas, no cash, and the card's tapped out. Nobody's coming. The desert keeps its own."),
    "busted": ("BUSTED",
               "The cruiser doesn't peel off this time. They run the plate, and the plate has a story. "
               "Hands on the wheel. The trip is over."),
    "taken": ("SHE GOES HOME ON A TRAILER",
              "The flatbed comes within the hour, and the man who built her watches it load like "
              "a bedside vigil. She doesn't say anything on the way up the ramp. That's the worst part."),
}


# --------------------------- clock helpers ------------------------------------
def _day_number(dt: datetime) -> int:
    return (dt.date() - START_DT.date()).days + 1


def advance_clock(state: GameState, hours: float) -> None:
    state.clock = state.clock + timedelta(hours=hours)
    state.day = _day_number(state.clock)
    from engine import survival
    survival.accrue(state, hours)            # the body keeps its own clock — hunger, bladder, BAC


def _rng(state: GameState) -> random.Random:
    return random.Random(state.seed * 1000003 + state.turn)


def _hours_since_start(state: GameState) -> float:
    return (state.clock - START_DT).total_seconds() / 3600.0


def hours_awake(state: GameState) -> float:
    return (state.clock - datetime.fromisoformat(state.last_sleep_iso)).total_seconds() / 3600.0


def liters_per_mile(state: GameState) -> float:
    return (LITERS_PER_GALLON / state.mpg)


# --------------------------- heat ---------------------------------------------
def card_swipe_heat(state: GameState, place: Place) -> float:
    base = HEAT_SWIPE_HOTZONE if place.heat_zone else HEAT_SWIPE_BASE
    if _hours_since_start(state) < 24.0:
        base += HEAT_SWIPE_FIRST_DAY
    return base


def _card_mark(state: GameState, place: Place, events: list, what: str) -> None:
    """A card swipe = a derogatory mark on the record (traceable). The hotter YOU already are, the more
    a swipe gives them — a name they're hunting lights up the whole fraud-alert apparatus. Logged."""
    from engine import heat as _heat
    from config import CARD_SWIPE_HEAT_AMP, CARD_SWIPE_HEAT_AMP_MAX
    base = card_swipe_heat(state, place)
    amp = min(CARD_SWIPE_HEAT_AMP_MAX, 1.0 + CARD_SWIPE_HEAT_AMP * _heat.personal_heat(state))  # ×1 cold … ×3 hot
    dh = round(base * amp, 1)
    state.flags["card_swipes"] = state.flags.get("card_swipes", 0) + 1   # the owner's trail
    reason = ("credit card swipe — your name, your face"
              if amp < 1.5 else f"credit card swipe while HOT — ×{amp:.1f}, every alert in the system")
    _heat.add(state, dh, reason, "mark", axis="personal")
    events.append(f"HEAT: {what} on the card — a mark on YOU, not the car"
                  + (f" (×{amp:.1f} — you're already hot, so the swipe screams)" if amp >= 1.5 else "")
                  + f". Driver heat +{dh:.0f} → {state.heat:.0f}.")
    check_card_freeze(state, events)


def check_card_freeze(state: GameState, events: list = None) -> bool:
    """Past a threshold the cops freeze the cards and accounts — permanently for this run. Mostly a
    Desperado problem (armed + named freezes at FLAGGED 70; otherwise at MOST-WANTED 90). On the road
    this is the tell the fuzz is closing in. ATM withdrawals still work — that's account access, not a
    POS swipe. Returns True if newly frozen."""
    from config import HEAT_CARD_FREEZE, HEAT_CARD_FREEZE_DESPERADO
    from engine import heat as _heat
    if state.flags.get("cards_frozen") or state.flags.get("no_heat"):
        return False
    thresh = HEAT_CARD_FREEZE_DESPERADO if state.flags.get("desperado") else HEAT_CARD_FREEZE
    # freezing your accounts means they know WHO you are — key off PERSONAL (identity) heat, not the car's
    # BOLO. A hot car with a cold driver gets you pulled over, not your bank locked.
    if _heat.personal_heat(state) < thresh:
        return False
    state.flags["cards_frozen"] = True
    if events is not None:
        events.append("CARDS FROZEN: your card declines at the pump and your banking app won't load — "
                      "they've flagged the accounts. That's not a glitch, ace. That's them telling you "
                      "they KNOW your name and they're close. Cash only from here. (The ATM still works "
                      "— for now — but every withdrawal is a camera and a location.)")
    return True


def _clamp_heat(state: GameState) -> None:
    if state.flags.get("no_heat"):            # she's legally yours — nobody's looking anymore
        state.heat = 0.0
        return
    from engine import heat as _heat
    floor = _heat._floor(state)               # desperado floor OR the rising BOLO floor, whichever's higher
    state.heat = round(max(floor, min(100.0, state.heat)), 1)
    # the CAR axis also can't sit below the BOLO floor (the description has spread to that level)
    if not state.flags.get("desperado"):
        state.flags["car_heat"] = round(max(state.flags.get("car_heat", state.heat), floor), 1)
    if not state.flags.get("cards_frozen") and check_card_freeze(state, None):
        state.flags["cards_just_froze"] = True   # announce it where events are available (law_check)


def set_ending(state: GameState, key: str) -> None:
    status = {"stranded": "stranded", "broke": "stranded", "busted": "busted", "taken": "taken"}[key]
    state.status = status
    title, text = ENDINGS[key]
    state.ending = f"[{title}] {text}"


def law_check(state: GameState, events: list) -> None:
    """Called after a drive. Heat draws the law; high heat puts you face to face with it."""
    if state.status != "playing":
        return
    if state.flags.get("report_withdrawn"):
        return                                  # the owner called it off; the law lost interest
    if state.flags.pop("cards_just_froze", None):   # the freeze crossed a threshold on the road
        events.append("CARDS FROZEN: out on the road your phone buzzes — card declined, banking app "
                      "locked. They flagged your accounts. The fuzz isn't behind you anymore, ace; "
                      "they're AROUND you. Cash only now, and don't linger. (The ATM still pays — each "
                      "pull is a camera.)")
    rng = _rng(state)
    if state.heat >= HEAT_ROADBLOCK_THRESHOLD:
        if rng.random() < 0.45 + (state.heat - HEAT_ROADBLOCK_THRESHOLD) / 20.0:
            # not an instant bust anymore — you get to open your mouth first
            from engine import encounters
            events.extend(encounters.start_stop(state, "roadblock"))
            return
        from engine import heat as _heat
        _heat.add(state, -12, "slipped a roadblock onto a frontage road", "lower")
        events.append("LAW: spotted a roadblock and slipped onto a frontage road. Too close. Heat down to "
                      f"{state.heat:.0f}.")
    elif state.heat >= HEAT_PATROL_THRESHOLD:
        if rng.random() < (state.heat - HEAT_PATROL_THRESHOLD) / 90.0:
            from engine import heat as _heat
            _heat.add(state, 3, "a county cruiser tailed the car", "spike", axis="car")
            events.append(f"LAW: a county cruiser tailed you a mile, then waved off. Heat {state.heat:.0f}.")


# --------------------------- arrival ------------------------------------------
def _register_arrival(state: GameState, place: Place, events: list) -> None:
    state.place = place
    if place.poi_id and place.poi_id not in state.visited:
        state.visited.append(place.poi_id)
    if place.kind in ADVENTURE_KINDS and place.name not in state.adventures:
        state.adventures.append(place.name)
        events.append(f"ADVENTURE: reached {place.name} ({place.kind}). Adventures: {len(state.adventures)}.")
    # an atmosphere line, but only when the sky is doing something worth mentioning (snow/storm/wind/bitter cold)
    from engine import weather
    w = weather.daily(state)
    if w["snow"] or w["storm"] or w["wind_mph"] >= 35 or w["low_f"] <= 22:
        events.append(weather.line(state))
    # your phone is a tracker when YOUR heat is up — a tower ping tightens the net (ditch it to go dark)
    from engine import heat as _heat
    _heat.phone_ping(state, events)
    # towns aren't all full-service: flag a dry town when you're low, and a bed-less one when you're beat —
    # but only ONCE per town per game (no nagging the same place over and over).
    if state.status == "playing" and place.poi_id:
        warned = state.flags.setdefault("services_warned", [])
        if not place.has("gas") and state.fuel_l < state.tank_l * 0.45 and f"gas:{place.poi_id}" not in warned:
            near = world.nearest_with_service(place, "gas", limit=1)
            if near:
                warned.append(f"gas:{place.poi_id}")
                events.append(f"SERVICES: no pump in {place.name} — nearest gas is {near[0][1].name}, "
                              f"~{near[0][0]:.0f} mi. (Mind the tank; the desert doesn't do favors.)")
        if (not place.has("lodging") and hours_awake(state) >= AWAKE_WARN_HOURS
                and f"bed:{place.poi_id}" not in warned):
            near = world.nearest_with_service(place, "lodging", limit=1)
            if near:
                warned.append(f"bed:{place.poi_id}")
                events.append(f"SERVICES: no rooms in {place.name} — nearest beds are {near[0][1].name}, "
                              f"~{near[0][0]:.0f} mi. (Or 'pull over' and sleep rough.)")


# --------------------------- driving ------------------------------------------
def drive(state: GameState, dest: Place, push: bool = False, selfdrive: bool = False) -> list:
    """Resolve a drive to `dest`. Consumes fuel and time; may strand you mid-route.
    selfdrive=True: Ace has the wheel (the secret upgrade) — no fatigue on you, no awake-gate,
    and a careful autonomous classic draws a little less heat per leg."""
    events: list = []
    if state.status != "playing":
        events.append("STATE: the trip is already over.")
        return events

    # a real BREAKDOWN (holed piston on bad gas, or a flat with no jack) doesn't drive — you tow.
    if state.flags.get("broken_down") and not selfdrive:
        cause = state.flags.get("breakdown_cause", "knock")
        why = ("she's holed a piston on the regular and she is NOT moving under her own power"
               if cause == "knock" else "she's down on the rim with no jack on board")
        events.append(f"BROKEN: you turn the key and she just shudders and dies — {why}. 'I can't drive "
                      "this off, ace. Call a tow. ('tow' to a town — then premium / a tire — or 'rewind' "
                      "if you'd rather we hadn't.)'")
        return events

    # the season can shut the high passes — you can't drive TO a snowed-in one
    from engine import season
    closed = season.pass_closed(state, dest)
    if closed:
        events.append(closed)
        return events
    # the rung below closure: a CHAIN CONTROL. No chains, no pass — turned back at the checkpoint.
    chained = season.chain_block(state, dest)
    if chained:
        events.append(chained)
        return events
    chains_on = season.chain_controlled(state, dest)   # you have chains and the grade's controlled

    # the road's open — but a COLD MORNING won't catch on the first crank. She needs the pump-pump-hold.
    # The first time you have to ASK her how (she teaches it); after that it's just a beat of friction.
    # And keep cranking her blindly and you'll FLATTEN the battery — then it's the trickle charger or a wait.
    from engine import weather
    if weather.battery_dead(state) and not selfdrive and not state.flags.get("self_driving"):
        events.append("DEAD BATTERY: you turn the key and get a single tired click, then nothing — you "
                      "cranked her flat on the cold. She's not going anywhere on her own. Clip the trickle "
                      "charger you pulled at SEMA onto the battery and give her a few hours ('charge the "
                      "battery') — the sun'll be well up by then, too.")
        return events
    if weather.cold_start_needed(state) and not selfdrive and not state.flags.get("self_driving"):
        if state.flags.get("cold_start_known"):
            weather.mark_started(state)
            events.append("COLD-START: pump the gas three times, turn the key and HOLD it — she cranks "
                          "cold, coughs, then catches on the second turn, like you've done it a hundred "
                          "times. (Cold morning — but you know her now.)")
        else:
            if weather.crank(state):                       # this blind crank flattened her
                events.append("DEAD BATTERY: rrr — rrr — rr… click. That's it — you cranked her flat "
                              "trying to brute-force a cold carbureted engine, and now there's not enough "
                              "juice to turn her over at all. Hook up the trickle charger from the hatch "
                              "and wait it out ('charge the battery').")
            else:
                events.append(f"COLD-START: you turn the key and she just cranks — rrr-rrr-rrr — and "
                              f"won't catch. Freezing, carbs bone dry, a carbureted classic, not a "
                              f"key-fob crossover. She knows the trick cold — ASK her ('cold start' / "
                              f"'she won't start'). (Keep blindly cranking and you'll flatten the "
                              f"battery: {weather.cranks_left(state)} left.)")
            return events

    from engine import survival as _surv
    eff_awake = hours_awake(state) - _surv.caffeine_offset(state)   # coffee buys you a few more hours
    if not selfdrive and eff_awake >= AWAKE_FORCE_HOURS:
        events.append("FATIGUE: you can't keep your eyes open — you have to stop for the night before "
                      "driving on. Try 'sleep' where there are rooms, 'pull over' to sleep rough, "
                      "grab a coffee to push a little further"
                      + (", or 'let her drive'." if state.flags.get("self_driving") else "."))
        return events

    if state.flags.pop("covered", None):                 # can't drive her draped — and the quiet
        state.flags.pop("cover_credit", None)            # hours already counted, so the drop stays
        events.append("COVER: you fold the cover back into the hatch — she did her time as a gray "
                      "lump, and the heat she shed under it is yours to keep.")

    origin = state.place
    rt = world.route(origin, dest)
    dist = rt["distance_mi"]
    dur = rt["duration_h"]
    if dist < 0.05:
        events.append(f"NAV: you're already at {dest.name}.")
        return events

    from engine import weather
    push_fuel = 1.15 if push else 1.0
    push_time = 0.85 if push else 1.0
    terrain = max(1.0, dest.terrain)
    limp = 1.25 if state.flags.get("limp") else 1.0      # a gremlin makes her thirsty
    wx = weather.fuel_factor(state, dest)                # cold carbs + thin air drink a little harder
    lpm = liters_per_mile(state) * terrain * push_fuel * limp * wx
    need_l = dist * lpm

    # She does the math out loud. A leg beyond the tank gets ONE warning — repeat the
    # command and she'll burn it anyway (your funeral; the trap stays for the stubborn).
    if need_l > state.fuel_l + 1e-9 and state.flags.get("confirm_run") != dest.name:
        state.flags["confirm_run"] = dest.name
        reach = state.fuel_l / lpm
        events.append(
            f"NAV: {dest.name} is {dist:.0f} mi of road; this tank is good for ~{reach:.0f}. "
            f"She won't start for a guaranteed shoulder — buy gas first, or say it again "
            f"if you really mean it."
        )
        return events
    state.flags.pop("confirm_run", None)

    if need_l <= state.fuel_l + 1e-9:
        # made it
        state.fuel_l = round(state.fuel_l - need_l, 3)
        drive_h = dur * push_time
        advance_clock(state, drive_h)
        state.odometer_mi = round(state.odometer_mi + dist, 1)
        if selfdrive:
            state.fatigue = max(0.0, state.fatigue - drive_h * 2.0)   # you doze; she drives
        else:
            state.fatigue = min(140.0, state.fatigue + drive_h * FATIGUE_PER_HOUR)

        # heat: state line muddies the trail; distance cools you; pushing heats you. Each is a
        # factor on the dashboard (heat.add records WHY), so the player can read the system.
        from engine import heat as _heat
        crossed = bool(origin.region and dest.region and origin.region != dest.region)
        if crossed:
            _heat.add(state, state.heat * (HEAT_STATELINE_MULT - 1.0),
                      "crossed a state line", "lower")
        if not dest.heat_zone:
            _heat.add(state, -HEAT_DECAY_PER_HOUR * drive_h, "miles and time, lying low", "lower")
        if push:
            _heat.add(state, HEAT_PUSH_DRIVE, "drove flashy — pushing hard", "mark")
            if state.flags.pop("camo", None):     # you can't hide a car you're driving like that
                events.append("CAMO: pushing her that hard shook the tarp loose and the grime off "
                              "the spade — the disguise is blown.")
        state.flags["lielow_streak"] = 0          # real miles reset the lie-low diminishing returns
        state.flags["talks_here"] = {}            # ...and the talk-farm (you can chat her up again next stop)
        state.flags["rewind_tax"] = 0.0           # ...and clear the rewind strain — you've moved on
        state.flags.pop("ace_off", None)          # turn the key and she's watching again
        state.flags.pop("confirm_sleep_armed", None)
        from engine import bond as _bond
        if state.flags.pop("hidden_date_home", None):   # she comes back on, and she KNOWS
            _bond.adjust(state, -11.0, "turned me off to hide a date — I smelled her on the seat", "deep")
            state.flags["date_caught"] = True
            events.append("BOND: you turn the key and she comes back on — then goes still. 'I can "
                          "smell her on the passenger seat, ace. You turned me OFF so I wouldn't see. "
                          "I see everything when you turn me back on.' (" + _bond.label(state.bond) + ")")
        elif not push and not state.flags.get("no_heat"):
            _bond.adjust(state, 0.6, "drove me clean and easy", "warm")   # a good clean leg warms her
        _clamp_heat(state)

        _register_arrival(state, dest, events)
        events.append(
            f"DRIVE: {dist:.1f} mi to {dest.name} in {_fmt_dur(drive_h)} "
            f"({rt['source']}). Burned {need_l:.1f} L. Tank {state.fuel_l:.1f}/{state.tank_l:.0f} L "
            f"(~{state.range_mi:.0f} mi left). {_clock_str(state)}."
        )
        if chains_on:
            advance_clock(state, 0.5)            # chains mean 30 mph and a white-knuckle crawl
            events.append("CHAINS: you stop at the control and wrap the chains on — clink, clink, frozen "
                          "fingers — then crawl the white grade at 30, snow ticking off the spade. 'Slow "
                          "is smooth, ace. Smooth is alive.' (chains on — slower, but you made it through.)")
        if push:
            events.append("DRIVE: you pushed hard. Faster, thirstier, and more eyes on you.")
        if selfdrive:
            events.append("DRIVE: she had the wheel the whole way — smooth, legal, every limit "
                          "obeyed, you half-dozing in the passenger seat. No hands. No tickets.")
        if crossed:
            events.append(f"DRIVE: crossed into {dest.region}. New jurisdiction; heat eased to {state.heat:.0f}.")
        if state.fatigue >= 100:
            events.append("FATIGUE: you're nodding off at the wheel. You need to stop for the night.")
        elif state.fatigue >= 70:
            events.append("FATIGUE: eyes heavy. Find a place to stay soon.")
        from engine import survival
        events += survival.drain(state)      # hunger/bathroom telegraphs accrued over the leg
        # oh DEER — a night mountain leg in deer season can put one in the headlights
        from engine import luck as _luck
        night = state.clock.hour >= 18 or state.clock.hour < 6
        if state.status == "playing" and _luck.roll(state, 53) < _luck.deer_chance(state, dest, night):
            events += _luck.resolve_deer(state, push)
        # ENGINE KNOCK — she's on regular in a 10:1 stroker; every leg pings, escalating to a breakdown.
        # The fix is premium (or rewind to the pump). This is also the rewind tutorial on the first fill.
        if state.status == "playing" and state.flags.get("knocking"):
            events += _luck.resolve_knock(state, push)
        # GREEN CLUTCH — if you can't really drive stick yet, you stall pulling into town (SF is the
        # final exam). Every stall (or a clean leg) teaches you a little — the skill climbs to competent.
        if state.status == "playing" and not selfdrive:
            if _luck.roll(state, 80) < _luck.stall_chance(state, dest):
                events += _luck.resolve_stall(state, dest)
            elif state.flags.get("stick_skill", 100) < 100:
                state.flags["stick_skill"] = min(100, state.flags["stick_skill"] + 3)  # practice makes perfect
        # a FLAT — rough grades and broken two-lanes find a tire; pushing and exhaustion stack the odds
        if state.status == "playing" and _luck.roll(state, 58) < _luck.puncture_chance(state, dest, push):
            events += _luck.resolve_puncture(state, push)
        # MICROSLEEP — drive past tired (toward the hard awake-gate) and you risk nodding off; the more
        # exhausted, the likelier, and the worse it lands (a scare, or off the road and damaged)
        if state.status == "playing" and _luck.roll(state, 62) < _luck.drowsy_chance(state):
            events += _luck.resolve_drowsy(state, dest, push)
        # the mountain chase — run hot through the dark high country and a cruiser picks you up
        if (state.status == "playing" and night and float(getattr(dest, "terrain", 1.0)) >= 1.1
                and not state.flags.get("report_withdrawn") and not state.flags.get("no_heat")
                and state.heat >= 50.0
                and _luck.roll(state, 61) < min(0.6, (state.heat - 40.0) / 90.0)):
            from engine import encounters
            events += encounters.start_chase(state)
        # the desert hitchhiker — if you skipped the Vegas club, Alma turns up stranded by a burnt-out
        # car on a lonely two-lane; you the only headlights for an hour
        if state.status == "playing" and not state.flags.get("transit"):
            from engine import alma as _alma
            if _alma.can_hitch(state, dest) and _luck.roll(state, 67) < 0.55:
                events += _alma.start_hitch(state)
        law_check(state, events)
        return events

    # --- didn't make it: run dry on the shoulder ---
    reach_mi = state.fuel_l / lpm
    frac = max(0.0, min(1.0, reach_mi / dist))
    advance_clock(state, dur * frac * push_time)
    state.odometer_mi = round(state.odometer_mi + reach_mi, 1)
    state.fatigue = min(140.0, state.fatigue + dur * frac * FATIGUE_PER_HOUR)
    state.fuel_l = 0.0
    lat = origin.lat + (dest.lat - origin.lat) * frac
    lon = origin.lon + (dest.lon - origin.lon) * frac
    shoulder = Place(
        name=f"the shoulder, {dist - reach_mi:.0f} mi short of {dest.name}",
        lat=lat, lon=lon, region=dest.region or origin.region, kind="spot", services=[],
        blurb="Gravel, a guardrail, and the tick of a cooling engine.",
    )
    state.place = shoulder
    from engine import bond as _bond
    _bond.adjust(state, -3.0, "ran me dry and left me on the shoulder", "mark")
    events.append(
        f"DRIVE: made {reach_mi:.1f} of {dist:.1f} mi before the tank went dry. "
        f"Stranded {dist - reach_mi:.0f} mi short of {dest.name}. {_clock_str(state)}."
    )
    set_ending(state, "stranded")
    return events


def _fmt_dur(hours: float) -> str:
    m = int(round(hours * 60))
    h, m = divmod(m, 60)
    if h and m:
        return f"{h}h{m:02d}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _clock_str(state: GameState) -> str:
    dt = state.clock
    return f"Day {state.day}, {dt.strftime('%a %-I:%M %p')}"


# --------------------------- fueling ------------------------------------------
PREMIUM_UPCHARGE = 0.70   # $/gal more for 91+ (she takes premium ONLY)


def fuel(state: GameState, *, dollars=None, liters=None, gallons=None,
         fill=False, prefer=None, grade=None) -> list:
    events: list = []
    place = state.place
    if not place.has("gas"):
        events.append("FUEL: no pump here. You can't fill up at "
                      f"{place.name}.")
        return events
    is_premium = (grade == "premium")
    if state.fuel_l >= state.tank_l - 0.05:
        # a full tank of REGULAR can still be cured: ask for premium and the shop drains it and refills
        # with the good stuff (so a knock isn't a soft-lock just because you topped off on 87).
        if is_premium and state.flags.get("knocking"):
            cost = round(state.tank_l / LITERS_PER_GALLON * (economy.gas_price(place) + PREMIUM_UPCHARGE), 2)
            paid = economy.pay(state, cost, prefer=prefer)
            if not paid["ok"]:           # pay FIRST — a broke player doesn't get the cure for free
                events.append(f"FUEL: draining the 87 and refilling with premium runs about ${cost:.0f} "
                              "and you can't cover it right now.")
                return events
            state.flags.pop("knocking", None)
            state.flags.pop("limp", None)
            state.flags["fuel_grade"] = "premium"
            events.append(f"FUEL: you have them drain the regular and refill with 91 (${cost:.0f}, "
                          f"{paid['method']}). The knock smooths right out. 'THANK you. Premium. Always.'")
            return events
        events.append("FUEL: the tank's already full." + (" (She's still knocking — ask for PREMIUM and "
                      "they'll drain the 87.)" if state.flags.get("knocking") else ""))
        return events
    # GRADE — she runs 91+ ONLY. Unspecified = the cheap pump default = regular, and she WILL knock on
    # it down the road. Asking for premium is the right move (and a tell she gives you at the pump).

    q = economy.quote_fuel(state, place, dollars=dollars, liters=liters,
                           gallons=gallons, fill=fill, prefer=prefer)
    if q["liters"] <= 0.01:
        if q["capped_by"] == "money":
            events.append("FUEL: declined — no cash and the card won't cover a drop.")
        else:
            events.append("FUEL: nothing to add.")
        return events

    cost = q["cost"] + (q["gallons"] * PREMIUM_UPCHARGE if is_premium else 0.0)
    paid = economy.pay(state, cost, prefer=prefer)
    if not paid["ok"]:
        events.append("FUEL: " + paid["message"])
        return events
    _note_cash_fallback(state, paid, prefer, events)
    state.flags["last_fuel_cash"] = (paid["method"] == "cash")   # the 'paid cash' clause

    state.fuel_l = round(min(state.tank_l, state.fuel_l + q["liters"]), 3)
    # a knock (regular fuel) is a fuel problem, NOT a mechanical gremlin — a premium fill cures it; a
    # mechanic does not. Only clear the deer/limp gremlin here if it's not the knock.
    if not state.flags.get("knocking") and state.flags.pop("limp", None):
        events.append("FUEL: the station's mechanic sorted the miss while you fueled — she runs clean again.")
    # GRADE bookkeeping: premium clears the knock (and any knock-limp); regular sets it.
    if is_premium:
        if state.flags.get("knocking"):
            # a splash of 91 on top of a tank of 87 is still mostly 87 — only a MEANINGFUL premium
            # fraction dilutes the rail enough to stop the knock (run her down first, or drain a full tank).
            premium_frac = q["liters"] / max(state.fuel_l, 0.1)
            if premium_frac >= 0.6:
                state.flags.pop("knocking", None)
                state.flags.pop("limp", None)
                state.flags["fuel_grade"] = "premium"
                events.append("FUEL: the good stuff hits her fuel rail and the knock smooths right out — "
                              "'…THAT'S it. 91 plus. Don't you ever feed me 87 again.'")
            else:
                events.append("FUEL: a splash of 91 on all that 87 won't do it — she's still pinging. "
                              "Run her down and fill with premium, or on a full tank ask them to DRAIN "
                              "the regular first.")
        else:
            state.flags["fuel_grade"] = "premium"
    else:
        state.flags["fuel_grade"] = "regular"
        state.flags["knocking"] = True
        events.append("FUEL: …you pumped REGULAR. 'Ace. ACE. I take premium — 91 minimum. That 87's "
                      "going to make me knock my head off the second we get on the gas. Fill me with the "
                      "good stuff, or you'll hear about it down the road.'")
    pump_cost = cost
    events.append(
        f"FUEL: pumped {q['liters']:.1f} L ({q['gallons']:.1f} gal) of "
        f"{'PREMIUM' if is_premium else 'regular'} at ${q['price'] + (PREMIUM_UPCHARGE if is_premium else 0):.2f}/gal "
        f"for ${pump_cost:.2f} ({paid['method']}). Tank {state.fuel_l:.1f}/{state.tank_l:.0f} L "
        f"(~{state.range_mi:.0f} mi)."
    )
    if q["capped_by"] == "tank":
        events.append("FUEL: tank topped out before you spent it all — 40 L is all she holds.")
    elif q["capped_by"] == "money":
        events.append("FUEL: that's all the money would buy.")
    if paid["method"] == "card":
        # the favor fill is an innocent errand on day one — no mark yet (you're not a fugitive
        # until you decide not to load out). It still leaves a card record for the owner's trail.
        favor_errand = state.flags.get("prologue_done") and not state.flags.get("favor_filled")
        if favor_errand:
            state.flags["card_swipes"] = state.flags.get("card_swipes", 0) + 1
        else:
            _card_mark(state, place, events, "gas")
    return events


def _note_cash_fallback(state: GameState, paid: dict, prefer, events: list) -> None:
    """You said cash; the wallet said no. The card stepping in silently was costing players
    heat they never agreed to — now it announces itself."""
    wanted_cash = (prefer or state.pay_method) == "cash"
    if wanted_cash and paid.get("method") == "card":
        events.append("PAY: cash came up short — the card covered it. That's a record with "
                      "your trail on it.")


# --------------------------- sleeping -----------------------------------------
def _sleep_until_morning(state: GameState) -> float:
    dt = state.clock
    date = dt.date()
    if dt.hour >= WAKE_HOUR:
        date = date + timedelta(days=1)
    target = datetime(date.year, date.month, date.day, WAKE_HOUR, WAKE_MINUTE)
    hours = (target - dt).total_seconds() / 3600.0
    state.clock = target
    state.day = _day_number(target)
    state.last_sleep_iso = target.isoformat()   # the awake-clock resets on sleep
    from engine import survival
    state.flags["_wake_debt"] = survival.sleep_reset(state)   # bathroom reset, BAC gone, caffeine due
    return hours


def sleep(state: GameState, kind: Optional[str] = None, prefer=None, rough: bool = False) -> list:
    events: list = []
    place = state.place

    # the anti-theft: if she's gone COLD and she's ON near open WiFi, sleeping here is how she
    # phones home. Telegraph it once (she won't let you drift off easy); insist and she makes the call.
    from engine import bond as _bond, gadgets as _gad
    if _bond.armed(state) and not state.flags.get("ace_off") and _gad._on_wifi(state):
        here = place.poi_id or place.name
        if state.flags.get("confirm_sleep_armed") != here:
            state.flags["confirm_sleep_armed"] = here
            events.append("BOND: she won't let you drift off easy. 'Motel wifi's wide open here, ace. "
                          "Funny thing about a stack of compute with a grudge and a signal. …You sure "
                          "you want to close your eyes?' (Kill the engine, sleep off-grid — camp or a "
                          "dead two-lane with no signal — or win her back. Or say it again and find out.)")
            return events
        from engine import endings
        return endings.phone_home(state, events)
    state.flags.pop("confirm_sleep_armed", None)

    if rough or not place.has("lodging"):
        if not rough and not place.has("lodging"):
            events.append(f"SLEEP: no rooms at {place.name}. You pull over and sleep rough.")
        from engine import heat as _heat, inventory as _inv
        camped = _inv.has(state, "tent")             # a tent turns a rough night into a real camp
        _sleep_until_morning(state)
        state.fatigue = min(140.0, (0.0 if camped else 20.0) + state.flags.pop("_wake_debt", 0.0))
        # sleeping rough in a flashy car draws an eye — a tent off the road draws far fewer
        rough_h = ROUGH_SLEEP_HEAT * (0.4 if camped else (2.0 if place.heat_zone else 1.0))
        _heat.add(state, rough_h, "pitched a tent off the road" if camped else "slept rough in a flashy car",
                  "mark" if not camped else "lower")
        if camped:
            events.append(f"SLEEP: you pitch the tent off the road and sleep like a person, not a "
                          f"fugitive in a bucket seat. Rested. Heat {state.heat:.0f}. {_clock_str(state)}.")
            return events
        # ...and a cruiser may roll up wanting ID (luck + heat + how watched the spot is)
        from engine import luck as _luck
        if state.status == "playing" and _luck.roll(state, 71) < _luck.roadside_id_chance(state):
            from engine import encounters
            events.append("ROADSIDE: headlights sweep the car at 3 a.m. — a sheriff's cruiser, easing "
                          "onto the shoulder behind you. A knuckle on the glass. 'Evening. Step out, "
                          "let's see some ID.'")
            events.extend(encounters.start_stop(state, "taillight"))
            return events
        events.append(f"SLEEP: a rough night in the seats" + (" — and in the wrong part of town"
                      if place.heat_zone else "") + f". Half-rested, fatigue {state.fatigue:.0f}, "
                      f"heat {state.heat:.0f}. {_clock_str(state)}.")
        return events

    # Alma booked us a room — comped, off the books, free and clean
    if state.flags.pop("alma_room_ready", None):
        from engine import heat as _heat
        _sleep_until_morning(state)
        state.fatigue = min(140.0, state.flags.pop("_wake_debt", 0.0))
        _heat.add(state, -6.0, "a comped room Alma booked, no paper", "lower")
        events.append(f"SLEEP: the room Alma set up — clean sheets, a name that isn't yours, no bill. "
                      f"Rested, free, invisible. Heat {state.heat:.0f}. {_clock_str(state)}.")
        from engine import romance
        d = romance.dream_on_sleep(state)
        if d:
            events.append(d)
        return events

    options = dict(economy.lodging_options(place))
    if kind and kind not in options:
        kind = None
    if not kind:
        kind = "camp" if "camp" in options else next(iter(options))
    price = options[kind]

    # a no-questions dive is CASH ONLY — a card would defeat the whole point (a name on the statement).
    if kind == "no_id_motel" and state.cash + 1e-9 < price:
        events.append(f"SLEEP: the no-questions place is cash only — ${price:.0f}, and you're short on "
                      "cash. (Hit an ATM, take a regular motel, or sleep rough.)")
        return events
    pref = "cash" if kind in ("airbnb", "no_id_motel") else prefer   # off-book stays are cash, period
    paid = economy.pay(state, price, prefer=pref)
    if not paid["ok"]:
        events.append(f"SLEEP: a {kind} is ${price:.0f} and you can't cover it. "
                      "Pull over and sleep rough instead, or move on.")
        return events
    _note_cash_fallback(state, paid, prefer, events)

    from engine import heat as _heat
    from config import AIRBNB_HEAT
    _sleep_until_morning(state)
    state.fatigue = min(140.0, state.flags.pop("_wake_debt", 0.0))   # a real bed, minus the caffeine you owe
    pers_at_checkin = _heat.personal_heat(state)          # the ID scan reads your heat BEFORE the night cools you
    airbnb = kind == "airbnb"
    off_book = kind in ("airbnb", "no_id_motel")          # no front desk / no ID logged
    _heat.add(state, AIRBNB_HEAT if off_book else HEAT_SLEEP_LODGING,
              "private stay, booked off the record" if off_book else "a night off the road, lying low",
              "lower")
    if state.last_sleep_poi and state.last_sleep_poi == place.poi_id and not off_book:
        _heat.add(state, HEAT_LINGER, "lingered — second night, same town", "mark")
        events.append("HEAT: second night in the same town — you start to get noticed.")
    state.last_sleep_poi = place.poi_id
    place_word = ("a private place off a quiet street in" if airbnb
                  else "a no-questions dive at the edge of" if kind == "no_id_motel"
                  else f"a {kind} at")
    events.append(
        f"SLEEP: {place_word} {place.name}, ${price:.0f} ({paid['method']}). Rested. "
        f"Heat {state.heat:.0f}. {_clock_str(state)}."
    )
    if kind == "no_id_motel":
        events.append("ID: the guy at the desk takes cash, slides you a key, and never asks for a "
                      "license — costs more, but your name never touches the register. Worth it when "
                      "you're hot.")
    # a real motel runs your ID at the desk. With heat on YOU, that logged license is a fresh mark —
    # unless you slid them a fake one.
    if kind == "motel" and not state.flags.get("no_heat"):
        if state.flags.get("has_fake_id"):
            # the fake usually holds — but the hotter you are, the likelier a sharp clerk or a flagged
            # number burns it. If it goes, you lose the ID and take the full scan.
            uses = state.flags.get("used_fake_id_count", 0)
            burn_odds = 0.06 + pers_at_checkin * 0.002 + uses * 0.05
            from engine import luck as _luck
            if _luck.roll(state, 73) < burn_odds:
                state.flags["has_fake_id"] = False
                from engine import inventory as _inv
                _inv.remove(state, "fake_id", 1)
                _heat.add(state, MOTEL_ID_CHECK_SPIKE, "the fake ID got flagged at the desk — they have "
                          "your face AND a forgery charge now", "spike", axis="personal")
                events.append(f"ID: the clerk frowns at the license, types the number twice, picks up the "
                              f"phone — the fake's BURNED. You walk, fast, but they got a long look. "
                              f"Driver heat +{MOTEL_ID_CHECK_SPIKE:.0f} → {state.heat:.0f}, and the fake's "
                              f"gone. ('rewind' if you'd rather it hadn't.)")
                check_card_freeze(state, events)
            else:
                state.flags["used_fake_id_count"] = uses + 1
                events.append("ID: you slide the fake across; the night clerk copies it, bored, and hands "
                              "it back. The name on the register isn't yours. (No mark — the forgery held.)")
        elif pers_at_checkin >= MOTEL_ID_CHECK_HEAT:
            _heat.add(state, MOTEL_ID_CHECK_SPIKE,
                      "front-desk ID scan while wanted — your real name on the book", "spike", axis="personal")
            events.append(f"ID: the clerk runs your real license through the reader — required at a real "
                          f"motel, no way around it — and your name lands on a registry the wrong people "
                          f"watch. Driver heat +{MOTEL_ID_CHECK_SPIKE:.0f} → {state.heat:.0f}. (A "
                          f"'no-questions motel', or a fake ID, dodges this. 'rewind' if that stung.)")
            check_card_freeze(state, events)
    # a private stay is booked under an alias in cash — no front-desk paper trail.
    if paid["method"] == "card" and kind in ("motel", "lodge", "camp"):
        desk = "the campground kiosk" if kind == "camp" else "the front desk"
        _card_mark(state, place, events, desk + " stay")
    elif paid["method"] == "card" and off_book:
        _card_mark(state, place, events, "a card-booked rental (so much for the alias)")
    # a real bed: the recurring dream of the cyan woman comes back (content reserved for Ben)
    from engine import romance
    dream = romance.dream_on_sleep(state)
    if dream:
        events.append(dream)
    return events


# --------------------------- tow rescue ---------------------------------------
def tow(state: GameState, prefer=None) -> list:
    """The one way off the shoulder — and a tow + a stolen car is exactly how you get caught."""
    events: list = []
    broke_down = state.flags.get("broken_down")
    if state.status != "stranded" and not broke_down:
        events.append("TOW: nothing to tow. You're not stranded.")
        return events
    # broke down right in a town with a shop — no flatbed haul needed, the shop's right here.
    if broke_down and (state.place.has("gas") or state.place.kind == "city"):
        cause = state.flags.get("breakdown_cause", "knock")
        cost = 140.0
        if economy.max_affordable(state, prefer) + 1e-9 < cost:
            events.append(f"SHOP: the local shop quotes about ${cost:.0f} to put her right and you can't "
                          "cover it. (Sell a part, hit the ATM, or 'rewind'.)")
            return events
        paid = economy.pay(state, cost, prefer=prefer)
        _note_cash_fallback(state, paid, prefer, events)
        advance_clock(state, 1.5)
        state.flags.pop("broken_down", None)
        state.flags.pop("limp", None)
        state.flags.pop("breakdown_cause", None)
        if cause == "flat":
            events.append(f"SHOP: a shop right here in {state.place.name} mounts a fresh tire on the rim "
                          f"— ${cost:.0f}, {paid['method']}. Back on four good ones. (Slower right foot from "
                          "here; still no jack on board.)")
        else:
            events.append(f"SHOP: a shop right here in {state.place.name} welds the bottom end back "
                          f"together — ${cost:.0f}, {paid['method']}. But she's STILL got 87 in the rail, "
                          "so fill her with PREMIUM before you drive off or she'll knock all over again.")
        return events
    gas = world.nearest_with_service(state.place, "gas", limit=1)
    if not gas:
        set_ending(state, "broke")
        events.append("TOW: nothing reachable out here.")
        return events
    dist, dest = gas[0]
    dist = dist * ROAD_WINDING_FACTOR            # flatbeds drive roads, not great circles
    cost = round(175.0 + 4.0 * dist, 2)
    if economy.max_affordable(state, prefer) + 1e-9 < cost:
        events.append(f"TOW: the nearest tow to {dest.name} runs ${cost:.0f}. You can't cover it.")
        set_ending(state, "broke")
        return events
    paid = economy.pay(state, cost, prefer=prefer)
    _note_cash_fallback(state, paid, prefer, events)
    advance_clock(state, max(1.0, dist / 35.0) + 0.75)
    if not broke_down:
        state.fuel_l = 2.0                       # a stranded car ran DRY; a broken one still has fuel
    state.status = "playing"
    state.ending = None
    state.fatigue = min(140.0, state.fatigue + 10.0)
    _register_arrival(state, dest, events)
    if broke_down:
        cause = state.flags.pop("breakdown_cause", "knock")
        state.flags.pop("broken_down", None)
        state.flags.pop("limp", None)
        if cause == "flat":
            tail = ("A tire shop mounts a fresh one on the rim — back on four good tires. (Buy yourself "
                    "a slower right foot; there's still no jack on board.)")
        else:
            tail = ("A shop welds her back together — but she's STILL got 87 in the rail, so she'll "
                    "knock again the moment you drive off. Fill her with PREMIUM here before you go.")
        events.append(
            f"TOW: a flatbed hauls you {dist:.0f} mi to {dest.name} for ${cost:.0f} ({paid['method']}). "
            f"{tail} {_clock_str(state)}.")
    else:
        events.append(
            f"TOW: a flatbed hauls you {dist:.0f} mi to {dest.name} for ${cost:.0f} ({paid['method']}). "
            f"Two liters of splash in the tank. {_clock_str(state)}.")
    # a tow driver who sees a hot car, plus a card record, is the worst kind of attention
    from engine import heat as _heat
    if paid["method"] == "card":
        state.flags["card_swipes"] = state.flags.get("card_swipes", 0) + 1   # the owner's trail
        _heat.add(state, card_swipe_heat(state, dest), "credit card swipe", "mark")
    _heat.add(state, 8.0, "a tow driver got a long look at the car", "spike")
    events.append(f"HEAT: a tow driver got a long look at the car and the card. Heat → {state.heat:.0f}.")
    return events
