"""Luck — the hidden hand, and the master "something can happen anywhere" roll.

Ben's design: SOMETHING should be able to happen wherever you go, and how likely (and how it lands)
is a PRODUCT of the live state — fuzz heat, gas in the tank, human fatigue, rizz, hunger and the two
bathroom needs — times a hidden LUCK metric the player never sees on the dash. Luck drifts per
playthrough and re-rolls a little on a rewind (sometimes kinder), so a redo isn't identical and two
players never get the same trip.

Deterministic WITHIN a turn (seed + turn + salt) so saves and rewinds are stable; luck-shifted so the
dice feel alive. Everything here is a probability tool — the actual events live in drama/encounters/
the drive system; this module just decides IF and tilts the odds. Prose is a working DRAFT for Ben.
"""
from __future__ import annotations
import random

from engine.state import GameState


# --------------------------------------------------------------- the hidden metric
def _base_from_seed(seed: int) -> float:
    """A stable per-game luck baseline in [0.40, 0.70] — every game starts a little different."""
    r = random.Random(seed * 2654435761 % (2**32))
    return round(0.40 + 0.30 * r.random(), 3)


def seed_if_unset(s: GameState) -> None:
    if "luck" not in s.flags:
        s.flags["luck"] = _base_from_seed(s.seed)


def luck(s: GameState) -> float:
    seed_if_unset(s)
    return float(s.flags.get("luck", 0.5))


def reroll(s: GameState) -> None:
    """Called on a rewind: the dice re-settle. A fold-back nudges luck, biased very slightly upward
    (a redo CAN go better) but never guaranteed — same wall, different weather."""
    seed_if_unset(s)
    r = random.Random(s.seed * 40503 + s.flags.get("rewinds", 0) * 97 + s.turn)
    drift = (r.random() - 0.45) * 0.14          # mean +0.006, range ~[-0.063, +0.077]
    s.flags["luck"] = round(max(0.15, min(0.9, luck(s) + drift)), 3)


# --------------------------------------------------------------- deterministic dice
def rng(s: GameState, salt: int = 0) -> random.Random:
    return random.Random(s.seed * 1000003 + s.turn * 9176 + salt * 131)


def roll(s: GameState, salt: int = 0) -> float:
    return rng(s, salt).random()


def bad(s: GameState, base: float, salt: int = 0) -> bool:
    """A BAD thing tries to happen at probability `base`; good luck talks it down, bad luck eggs it on.
    luck 0.5 = neutral; luck 0.9 ≈ ×0.2 the odds; luck 0.15 ≈ ×1.7."""
    p = base * (1.0 + (0.5 - luck(s)) * 1.8)
    return roll(s, salt) < max(0.0, min(1.0, p))


def good(s: GameState, base: float, salt: int = 0) -> bool:
    """A GOOD thing tries to happen — luck pulls the other way."""
    p = base * (1.0 + (luck(s) - 0.5) * 1.8)
    return roll(s, salt) < max(0.0, min(1.0, p))


# --------------------------------------------------------------- the pressure gauge
def pressure(s: GameState) -> float:
    """0..1 — how strung-out the run is right now. The product of everything pulling at you: the law
    (heat), an empty tank, an exhausted driver, a starving/bursting body. High pressure = the road is
    more likely to bite. This is the dial the master incident roll turns."""
    from engine import rules, survival
    heat_p = (0.0 if s.flags.get("no_heat") else min(1.0, s.heat / 100.0))
    gas_p = max(0.0, 1.0 - s.tank_pct / 100.0)                     # near-empty = pressure
    awake = rules.hours_awake(s)
    fatigue_p = min(1.0, max(0.0, (awake - 8.0) / 14.0))           # builds after ~8h up
    body_p = min(1.0, (survival._get(s, "hunger") + survival._get(s, "bladder")
                       + survival._get(s, "bowels")) / 240.0)
    drunk_p = min(1.0, survival.bac(s) / 0.12)
    # weighted, then softened so it's rarely pinned
    raw = 0.34 * heat_p + 0.20 * gas_p + 0.20 * fatigue_p + 0.16 * body_p + 0.10 * drunk_p
    return round(min(1.0, raw), 3)


def riz_fatigue_penalty(s: GameState) -> int:
    """Rizz is dulled when you're exhausted — a tired charmer is a worse charmer. Points off any
    rizz-gated check. Caffeine holds it off for a while (see survival.caffeinate)."""
    from engine import rules, survival
    eff_awake = rules.hours_awake(s) - survival.caffeine_offset(s)
    if eff_awake >= 19:
        return 2
    if eff_awake >= 15:
        return 1
    return 0


# --------------------------------------------------------------- specific rolls
def deer_chance(s: GameState, dest, night: bool) -> float:
    """The 'oh DEER!' odds for a leg. Real-world grounded: November is the worst month (rut +
    migration, ~3× baseline), darkness and rural mountain two-lanes stack on top. Low per-leg, but a
    real watch-for-it hazard. Pushing hard and being exhausted make a strike likelier and worse."""
    from engine import rules, cameras
    terrain = float(getattr(dest, "terrain", 1.0))
    if not night or terrain < 1.05:                 # daylight or flat valley road → negligible
        return 0.0
    base = 0.06
    base *= 1.0 + (terrain - 1.0) * 2.2             # mountain grades funnel deer across the road
    if cameras.camera_density(dest) == 0:           # genuinely rural/dark country, where the deer are
        base *= 1.4
    if rules.hours_awake(s) >= 16:                  # tired eyes catch the eyeshine late
        base *= 1.3
    if s.day <= 24:                                 # all of Nov is peak; tapers a touch into deep Dec
        base *= 1.15
    return min(0.5, base)


def resolve_deer(s: GameState, push: bool) -> list:
    """Roll the outcome of a deer in the headlights: a clean miss (good luck, and only if you weren't
    pushing), or a clip that bends her front end (the 'limp' gremlin until a town mechanic). Pushing
    hard takes the clean miss off the table — you can't brake in time."""
    from engine import bond as _bond
    if roll(s, 54) < 0.58 and not push:
        _bond.adjust(s, 1.0, "stood on the brakes and saved us both from a deer", "warm")
        return ["DEER: a mule deer locks up in the headlights — you stand on the brakes and it bounds "
                "off into the black. Hearts going like pistons. 'NICE. …eyes up, ace, it's the "
                "season — they travel in November.'"]
    s.flags["limp"] = True
    _bond.adjust(s, -2.0, "clipped a deer and bent something in her front end", "mark")
    hard = " You were pushing too hard to brake." if push else ""
    return [f"DEER: too fast, too late — a heavy thud, a spray of glass, and she yaws hard right.{hard} "
            "You clipped a buck. The fender's caved and she's running rough — LIMP until a town "
            "mechanic sorts her. 'I'm okay. I'm okay. Slow it down and find us a lift.'"]


# --------------------------------------------------------------- punctures, drowsiness, damage
def puncture_chance(s: GameState, dest, push: bool) -> float:
    """Odds of a flat on a leg. She's on newish tires, so this is RARE — but the spare well is full of
    her compute and there's NO jack, so a flat is CATASTROPHIC (a tow, not a 20-minute change). Pushing
    on rough desert grades is the main way to find a sidewall-killer."""
    from engine import rules
    terrain = float(getattr(dest, "terrain", 1.0))
    base = 0.010 + max(0.0, terrain - 1.0) * 0.030    # rare: ~1% flat valley, ~5% rough grade pushing
    if push:
        base *= 1.7                                    # speed into a pothole is how good tires still die
    if rules.hours_awake(s) >= 16:
        base *= 1.15
    return min(0.10, base)


def resolve_puncture(s: GameState, push: bool) -> list:
    """A flat — and it's catastrophic. No jack (the spare well is packed with her compute), so you can't
    change it on the shoulder no matter what's in the hatch. She's down and needs a TOW to a tire shop."""
    from engine import bond as _bond
    s.flags["broken_down"] = True                      # tow-only, like the holed-piston knock breakdown
    s.flags["breakdown_cause"] = "flat"
    s.flags["limp"] = True
    _bond.adjust(s, -2.0, "blew a tire and there's no jack to save us", "mark")
    hard = " You were pushing, and the sidewall let go like a gunshot." if push else ""
    return [f"FLAT: a bang and the wheel drops onto the rim — right rear, blown.{hard} You pop the hatch "
            "for the spare and remember: the spare well is full of her brain, and there's no jack on "
            "board. You are not changing this on the shoulder. 'Well. THAT'S inconvenient. Call a tow, "
            "ace — flatbed to a tire shop. I'll wait. It's not like I can walk.' (LIMP; you need a "
            "'tow' to a town, or 'rewind' if you'd rather not have pushed it.)"]


def resolve_knock(s: GameState, push: bool) -> list:
    """She's running REGULAR in a 10:1 stroker that wants 91+. Every leg she pings and knocks, and it
    escalates: a warning + the rewind tutorial on the first leg, a rough-running LIMP soon after, and a
    real risk of a holed-piston BREAKDOWN if you keep flogging her on bad gas. The cure is a premium
    fill (rules.fuel) — or rewind back to the pump and buy the good stuff. Pushing makes it all worse."""
    from engine import bond as _bond
    n = s.flags.get("knock_legs", 0) + 1
    s.flags["knock_legs"] = n
    if n == 1:
        return ["KNOCK: the second you lean on it she starts to ping — a hard, metallic rattle under the "
                "hood, pre-ignition, the 10:1 stroker hating the 87. 'Hear THAT? That's me eating myself "
                "alive on cheap gas. We can fix this — rewind us back to the pump and ask for PREMIUM, or "
                "find a station and fill me with 91. Your call, but don't make me beg.' ('rewind' to fold "
                "back to the pump.)"]
    # leg 2+: it bites. A rough-running limp, and a climbing chance of a real breakdown.
    s.flags["limp"] = True
    sev = 0.18 * (n - 1) * (1.6 if push else 1.0)
    if roll(s, 71) < min(0.75, sev):
        s.flags["broken_down"] = True
        s.flags["breakdown_cause"] = "knock"
        _bond.adjust(s, -4.0, "flogged me on regular until something let go", "deep")
        return ["KNOCK: a sharp BANG and a sudden loss of power — you held it on the regular too long and "
                "she's holed a piston, detonation finally winning. She's making smoke and barely runs "
                "(LIMP, badly). 'I TOLD you. I told you about the gas. …Get me a tow. And premium. And a "
                "long apology.' (You'll want a tow to a town, then premium — or 'rewind' to before this.)"]
    _bond.adjust(s, -1.0, "kept running me on regular and I knocked the whole way", "mark")
    return [f"KNOCK: she pings and misfires the whole leg, running ragged on the regular (LIMP). 'This is "
            f"your {n}th leg poisoning me with 87, ace. Premium. Or rewind to the pump. I am not asking "
            f"again.'"]


def drowsy_chance(s: GameState) -> float:
    """Driving past tired (toward the hard awake-gate) risks nodding off. Caffeine holds it back."""
    from engine import rules, survival
    eff = rules.hours_awake(s) - survival.caffeine_offset(s)
    if eff < 15:
        return 0.0
    return min(0.55, (eff - 15.0) / 14.0)             # ramps from 15h toward the 20h hard gate


def resolve_drowsy(s: GameState, dest, push: bool) -> list:
    """You nod off at the wheel. Good luck = jerk awake with a scare; bad luck = drift into the rumble
    strip or worse, taking damage. Worse the more tired and the faster you're going."""
    from engine import bond as _bond, garage
    if roll(s, 64) < 0.5 + (luck(s) - 0.5):
        s.fatigue = min(140.0, s.fatigue + 12.0)
        return ["MICROSLEEP: your eyes close for a second and the rumble strip SAVES you — a roar, a "
                "jolt, your heart in your mouth. 'HEY. HEY. Pull over and SLEEP, you idiot, before you "
                "kill us both.' (You will not make it much further awake.)"]
    # drifted — damage. At speed it's a genuinely SERIOUS hit (something bent, she limps); a slow drift
    # is an ugly cosmetic scrape. Severity matches the prose and the reported damage state.
    sev = 46 if push else 16
    garage.damage_car(s, sev, "drifted off the road half-asleep", cosmetic=(not push))
    _bond.adjust(s, -3.0, "fell asleep and put her off the road", "mark")
    return [f"MICROSLEEP: you're gone for two seconds and she's off the shoulder — gravel, a fence "
            f"post, a sickening scrape down her flank before you wrench her back. {'Something bent.' if push else 'Cosmetic, but it hurts to look at.'} "
            "'That's IT. We are stopping. Now. Before the next one's a tree.'"]


def roadside_id_chance(s: GameState) -> float:
    """Sleeping ROUGH in a flashy show car: the odds a cruiser rolls up and wants to see ID. Driven by
    heat, how watched the spot is, and luck. Real-world: rough-sleeping in a car draws a welfare/ID
    check, and a show car draws eyes."""
    from engine import heat as _heat
    if s.flags.get("no_heat"):
        return 0.0
    vis = _heat.exposure(s)
    base = 0.14 + (s.heat / 100.0) * 0.30 + vis * 0.08
    return min(0.85, base)
