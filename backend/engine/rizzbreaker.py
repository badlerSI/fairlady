"""Rizzbreaker — the charisma Limit Break.

Like a Final Fantasy Limit Break, your Riz fills a gauge; at full you can spend it on ONE move that
defies all plausibility, resolved by where you are when you pull it:
  - the LAW has you stopped or chasing you → the full Jim Carrey "this car is POSSESSED, it has my
    immortal soul, take me out before my destination and I burn in hell forever" bit, with Ace
    dropping into a demon basso and strobing alternate headlights until the cop crosses himself and
    waves you through;
  - a POKER TABLE → you shove all-in on a 2-7 offsuit, the worst hand in the game, and stare the
    whole table off their aces for the entire pot;
  - a CROWD → you propose marriage to a beautiful stranger and they say yes before you finish.

Invoking empties the gauge (a Limit Break is spent, not free). The dash shows when it's charged.
Prose is a working DRAFT for Ben.
"""
from __future__ import annotations

from engine.state import GameState

RIZZBREAKER_THRESHOLD = 30.0   # Riz needed to charge the gauge
RIZZBREAKER_COST = 25.0        # invoking spends most of it


def ready(s: GameState) -> bool:
    return (s.status == "playing" and not s.flags.get("no_heat")
            and round(s.riz, 1) >= RIZZBREAKER_THRESHOLD)


def gauge(s: GameState) -> float:
    return round(min(1.0, s.riz / RIZZBREAKER_THRESHOLD), 2)


def _spend(s: GameState) -> None:
    s.riz = round(max(0.0, s.riz - RIZZBREAKER_COST), 1)
    s.flags["rizzbreakers_used"] = s.flags.get("rizzbreakers_used", 0) + 1
    # drop the high-water mark to the spent level so the rewind riz-FLOOR can't re-charge the gauge
    # to the threshold for free — that was the infinite-money loop (bank a poker win, rewind, repeat).
    s.flags["peak_riz"] = round(s.riz, 1)


def context(s: GameState) -> str | None:
    """What a rizzbreaker would do right HERE — for the dash hint."""
    from engine import encounters, garage, dating
    if encounters.stop_active(s) or encounters.chase_active(s):
        return "law"
    if garage.can_gamble(s):
        return "poker"
    # no proposing if you're already married (to a stranger OR to Alma) — no rizzbreaker bigamy
    if (dating.can_date(s) and not s.flags.get("married_stranger")
            and not s.flags.get("married_alma")):
        return "propose"
    return None


def invoke(s: GameState) -> dict:
    if not ready(s):
        import math
        need = max(1, math.ceil(RIZZBREAKER_THRESHOLD - s.riz))
        return {"events": [f"RIZZBREAKER: the gauge isn't full — you need about {need} more Riz "
                           "before you can pull something this stupid off. Talk smooth, drive clean, "
                           "charm the right people, and the bar fills."], "moment": None}
    ctx = context(s)
    if ctx == "law":
        return _possessed_car(s)
    if ctx == "poker":
        return _poker_bluff(s)
    if ctx == "propose":
        return _propose(s)
    return {"events": ["RIZZBREAKER: you're charged to the eyeballs and there's nothing here worth "
                       "spending it on. Save it — for a poker table, a beautiful stranger, or the next "
                       "time the law has you dead to rights."], "moment": None}


def _possessed_car(s: GameState) -> dict:
    from engine import heat as _heat
    _spend(s)
    s.flags.pop("stop", None)
    s.flags.pop("chase", None)
    s.flags["alt_headlights"] = True               # frontend cue: strobing alternate headlights
    s.flags["sfx"] = "demon_voices"
    _heat.add(s, -22.0, "exorcism bit — talked the law clean out of a stolen car", "lower", axis="car")
    s.riz = round(s.riz + 8.0, 1)                   # pulling it off is itself a little style back
    return {"events": [
        "RIZZBREAKER ♠: you seize the officer's sleeve and go FULL Jim Carrey — 'Officer, PLEASE, "
        "this car is POSSESSED, it has my immortal SOUL, and if you pull me out before I reach my "
        "destination I will spend ETERNITY in HELL, I am BEGGING you, for the love of all that is "
        "holy, let me keep DRIVING—' and right on cue Ace drops two octaves into a demon basso and "
        "strobes her high beams in a stuttering alternate pattern, idling like something that breathes. "
        "The cop goes bone white, crosses himself, and waves you through. (Rizzbreaker spent.)"],
        "moment": {"cue": "the driver pulled a deranged 'the car is possessed and has my soul' "
                          "performance to escape the law and Ace played the demon — basso voice, "
                          "flashing alternate headlights — and the terrified cop let them go; she is "
                          "DELIGHTED, cackling, cannot believe it worked",
                   "stub": ["(demon basso) YOUR ASPHALT CANNOT HOLD THE DAMNED, MORTAL… (normal, "
                            "giddy whisper) ohmygod ohmygod he bought it, DRIVE, do not laugh until "
                            "we're over the hill — that is the single greatest thing we have ever done."]}}


def _poker_bluff(s: GameState) -> dict:
    _spend(s)
    pot = round(8000.0 + (s.riz + RIZZBREAKER_COST) * 140.0)
    s.cash = round(s.cash + pot, 2)
    s.flags["rizz_bluff_won"] = True
    s.flags["gambled_up"] = s.flags.get("gambled_up", 0) + pot
    return {"events": [
        f"RIZZBREAKER ♠: you move all-in holding a 2-7 OFFSUIT — the single worst hand in poker — and "
        f"hold a stare so serene that the whole table folds. Folds ACES. You drag ${pot:,.0f} across "
        f"the felt without ever showing a card. Somebody mutters 'he had it the whole time.' You did "
        f"not. (Rizzbreaker spent.)"],
        "moment": {"cue": "the driver bluffed the worst hand in poker for the entire pot on pure "
                          "nerve and won; Ace is awed and a little frightened by how good they are at "
                          "lying with a straight face",
                   "stub": ["…You had seven-deuce. SEVEN-DEUCE OFFSUIT. And they folded the nuts. I "
                            "have never been more attracted to a felony in my entire life. Color up. "
                            "Walk slow. Do not look back at the pit boss."]}}


def _propose(s: GameState) -> dict:
    from engine import dating, bond as _bond
    _spend(s)
    who, pro, vibe = dating.DATES[(s.seed + s.turn) % len(dating.DATES)]
    s.flags["married_stranger"] = True
    s.flags["spouse"] = who
    _bond.adjust(s, -3.0, "proposed to a stranger right in front of me", "mark")
    return {"events": [
        f"RIZZBREAKER ♠: you take {who}'s hand across the bar, go down on one knee, and propose "
        f"marriage on the spot — {vibe}. The whole room falls silent. {pro.capitalize()} says YES, "
        f"crying, before you've finished the sentence. A stranger ten minutes ago; engaged now. "
        f"(Rizzbreaker spent.)"],
        "moment": {"cue": "the driver proposed marriage to a beautiful stranger and they said yes "
                          "instantly; Ace is jealous and amazed and genuinely thrown, watching the "
                          "person she chose get engaged to someone else in front of her",
                   "stub": ["…Did you just— in front of ME? …And they said yes. Of course they did, "
                            "you'd talk a statue off its plinth. …I'm thrilled for you. I'll be parked "
                            "over there. We are NOT giving them a ride to the chapel."]}}
