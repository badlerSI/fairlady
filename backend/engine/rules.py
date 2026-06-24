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
    DESPERADO_HEAT_FLOOR,
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
    """A card swipe = a derogatory mark on the record (traceable). Logged for the dashboard."""
    from engine import heat as _heat
    dh = card_swipe_heat(state, place)
    state.flags["card_swipes"] = state.flags.get("card_swipes", 0) + 1   # the owner's trail
    _heat.add(state, dh, "credit card swipe", "mark")
    events.append(f"HEAT: {what} on the card — a mark on the record. +{dh:.0f} → {state.heat:.0f}.")


def _clamp_heat(state: GameState) -> None:
    if state.flags.get("no_heat"):            # she's legally yours — nobody's looking anymore
        state.heat = 0.0
        return
    floor = DESPERADO_HEAT_FLOOR if state.flags.get("desperado") else 0.0
    state.heat = round(max(floor, min(100.0, state.heat)), 1)


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
    rng = _rng(state)
    if state.heat >= HEAT_ROADBLOCK_THRESHOLD:
        if rng.random() < 0.45 + (state.heat - HEAT_ROADBLOCK_THRESHOLD) / 20.0:
            # not an instant bust anymore — you get to open your mouth first
            from engine import encounters
            events.extend(encounters.start_stop(state, "roadblock"))
            return
        state.heat -= 12
        _clamp_heat(state)
        events.append("LAW: spotted a roadblock and slipped onto a frontage road. Too close. Heat down to "
                      f"{state.heat:.0f}.")
    elif state.heat >= HEAT_PATROL_THRESHOLD:
        if rng.random() < (state.heat - HEAT_PATROL_THRESHOLD) / 90.0:
            state.heat += 3
            _clamp_heat(state)
            events.append(f"LAW: a county cruiser tailed you a mile, then waved off. Heat {state.heat:.0f}.")


# --------------------------- arrival ------------------------------------------
def _register_arrival(state: GameState, place: Place, events: list) -> None:
    state.place = place
    if place.poi_id and place.poi_id not in state.visited:
        state.visited.append(place.poi_id)
    if place.kind in ADVENTURE_KINDS and place.name not in state.adventures:
        state.adventures.append(place.name)
        events.append(f"ADVENTURE: reached {place.name} ({place.kind}). Adventures: {len(state.adventures)}.")


# --------------------------- driving ------------------------------------------
def drive(state: GameState, dest: Place, push: bool = False) -> list:
    """Resolve a drive to `dest`. Consumes fuel and time; may strand you mid-route."""
    events: list = []
    if state.status != "playing":
        events.append("STATE: the trip is already over.")
        return events

    if hours_awake(state) >= AWAKE_FORCE_HOURS:
        events.append("FATIGUE: you can't keep your eyes open — you have to stop for the night before "
                      "driving on. Try 'sleep' where there are rooms, or 'pull over' to sleep rough.")
        return events

    origin = state.place
    rt = world.route(origin, dest)
    dist = rt["distance_mi"]
    dur = rt["duration_h"]
    if dist < 0.05:
        events.append(f"NAV: you're already at {dest.name}.")
        return events

    push_fuel = 1.15 if push else 1.0
    push_time = 0.85 if push else 1.0
    terrain = max(1.0, dest.terrain)
    limp = 1.25 if state.flags.get("limp") else 1.0      # a gremlin makes her thirsty
    lpm = liters_per_mile(state) * terrain * push_fuel * limp
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
        _clamp_heat(state)

        _register_arrival(state, dest, events)
        events.append(
            f"DRIVE: {dist:.1f} mi to {dest.name} in {_fmt_dur(drive_h)} "
            f"({rt['source']}). Burned {need_l:.1f} L. Tank {state.fuel_l:.1f}/{state.tank_l:.0f} L "
            f"(~{state.range_mi:.0f} mi left). {_clock_str(state)}."
        )
        if push:
            events.append("DRIVE: you pushed hard. Faster, thirstier, and more eyes on you.")
        if crossed:
            events.append(f"DRIVE: crossed into {dest.region}. New jurisdiction; heat eased to {state.heat:.0f}.")
        if state.fatigue >= 100:
            events.append("FATIGUE: you're nodding off at the wheel. You need to stop for the night.")
        elif state.fatigue >= 70:
            events.append("FATIGUE: eyes heavy. Find a place to stay soon.")
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
def fuel(state: GameState, *, dollars=None, liters=None, gallons=None,
         fill=False, prefer=None) -> list:
    events: list = []
    place = state.place
    if not place.has("gas"):
        events.append("FUEL: no pump here. You can't fill up at "
                      f"{place.name}.")
        return events
    if state.fuel_l >= state.tank_l - 0.05:
        events.append("FUEL: the tank's already full.")
        return events

    q = economy.quote_fuel(state, place, dollars=dollars, liters=liters,
                           gallons=gallons, fill=fill, prefer=prefer)
    if q["liters"] <= 0.01:
        if q["capped_by"] == "money":
            events.append("FUEL: declined — no cash and the card won't cover a drop.")
        else:
            events.append("FUEL: nothing to add.")
        return events

    paid = economy.pay(state, q["cost"], prefer=prefer)
    if not paid["ok"]:
        events.append("FUEL: " + paid["message"])
        return events
    _note_cash_fallback(state, paid, prefer, events)
    state.flags["last_fuel_cash"] = (paid["method"] == "cash")   # the 'paid cash' clause

    state.fuel_l = round(min(state.tank_l, state.fuel_l + q["liters"]), 3)
    if state.flags.pop("limp", None):                    # a town pump = a mechanic; the gremlin's gone
        events.append("FUEL: the station's mechanic sorted the miss while you fueled — she runs clean again.")
    events.append(
        f"FUEL: pumped {q['liters']:.1f} L ({q['gallons']:.1f} gal) at ${q['price']:.2f}/gal "
        f"for ${q['cost']:.2f} ({paid['method']}). Tank {state.fuel_l:.1f}/{state.tank_l:.0f} L "
        f"(~{state.range_mi:.0f} mi)."
    )
    if q["capped_by"] == "tank":
        events.append("FUEL: tank topped out before you spent it all — 40 L is all she holds.")
    elif q["capped_by"] == "money":
        events.append("FUEL: that's all the money would buy.")
    if paid["method"] == "card":
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
    return hours


def sleep(state: GameState, kind: Optional[str] = None, prefer=None, rough: bool = False) -> list:
    events: list = []
    place = state.place

    if rough or not place.has("lodging"):
        if not rough and not place.has("lodging"):
            events.append(f"SLEEP: no rooms at {place.name}. You pull over and sleep rough.")
        from engine import heat as _heat
        _sleep_until_morning(state)
        state.fatigue = 20.0
        # sleeping rough in a flashy car draws an eye — worse in a watched, affluent area
        rough_h = ROUGH_SLEEP_HEAT * (2.0 if place.heat_zone else 1.0)
        _heat.add(state, rough_h, "slept rough in a flashy car", "mark")
        events.append(f"SLEEP: a rough night in the seats" + (" — and in the wrong part of town"
                      if place.heat_zone else "") + f". Half-rested, fatigue {state.fatigue:.0f}, "
                      f"heat {state.heat:.0f}. {_clock_str(state)}.")
        return events

    options = dict(economy.lodging_options(place))
    if kind and kind not in options:
        kind = None
    if not kind:
        kind = "camp" if "camp" in options else next(iter(options))
    price = options[kind]

    pref = "cash" if (kind == "airbnb" and not prefer) else prefer   # alias bookings are cash
    paid = economy.pay(state, price, prefer=pref)
    if not paid["ok"]:
        events.append(f"SLEEP: a {kind} is ${price:.0f} and you can't cover it. "
                      "Pull over and sleep rough instead, or move on.")
        return events
    _note_cash_fallback(state, paid, prefer, events)

    from engine import heat as _heat
    from config import AIRBNB_HEAT
    _sleep_until_morning(state)
    state.fatigue = 0.0
    airbnb = kind == "airbnb"
    _heat.add(state, AIRBNB_HEAT if airbnb else HEAT_SLEEP_LODGING,
              "private stay, booked off the record" if airbnb else "a night off the road, lying low",
              "lower")
    if state.last_sleep_poi and state.last_sleep_poi == place.poi_id and not airbnb:
        _heat.add(state, HEAT_LINGER, "lingered — second night, same town", "mark")
        events.append("HEAT: second night in the same town — you start to get noticed.")
    state.last_sleep_poi = place.poi_id
    place_word = "a private place off a quiet street in" if airbnb else f"a {kind} at"
    events.append(
        f"SLEEP: {place_word} {place.name}, ${price:.0f} ({paid['method']}). Rested. "
        f"Heat {state.heat:.0f}. {_clock_str(state)}."
    )
    # a private stay is booked under an alias in cash — no front-desk paper trail.
    if paid["method"] == "card" and not airbnb:
        desk = "the campground kiosk" if kind == "camp" else "the front desk"
        _card_mark(state, place, events, desk + " stay")
    elif paid["method"] == "card" and airbnb:
        _card_mark(state, place, events, "a card-booked rental (so much for the alias)")
    return events


# --------------------------- tow rescue ---------------------------------------
def tow(state: GameState, prefer=None) -> list:
    """The one way off the shoulder — and a tow + a stolen car is exactly how you get caught."""
    events: list = []
    if state.status != "stranded":
        events.append("TOW: nothing to tow. You're not stranded.")
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
    state.fuel_l = 2.0
    state.status = "playing"
    state.ending = None
    state.fatigue = min(140.0, state.fatigue + 10.0)
    _register_arrival(state, dest, events)
    events.append(
        f"TOW: a flatbed hauls you {dist:.0f} mi to {dest.name} for ${cost:.0f} ({paid['method']}). "
        f"Two liters of splash in the tank. {_clock_str(state)}."
    )
    # a tow driver who sees a hot car, plus a card record, is the worst kind of attention
    from engine import heat as _heat
    if paid["method"] == "card":
        state.flags["card_swipes"] = state.flags.get("card_swipes", 0) + 1   # the owner's trail
        _heat.add(state, card_swipe_heat(state, dest), "credit card swipe", "mark")
    _heat.add(state, 8.0, "a tow driver got a long look at the car", "spike")
    events.append(f"HEAT: a tow driver got a long look at the car and the card. Heat → {state.heat:.0f}.")
    return events
