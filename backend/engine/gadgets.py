"""Z camouflage, her connectivity tricks, and the secret path to a self-driving Ace.

She's a stack of compute behind the dash with a voice and a map — but she is NOT, out of the
box, autonomous. She can:
  • wear a CAMO disguise (a tarp, a mud-and-magnet decal job, a swapped plate) that makes the
    show car forgettable — one notch less exposed everywhere it matters;
  • on WiFi: TEXT (fire off a message, get a little recon back), FLASH her lights (a signal, or
    a show-off move where the cameras are), PLAY the stereo (a mood — and it cools her off);
  • but she canNOT drive herself.

…unless you find the secret. Once she's legally YOURS, the AiSha cats who built her — back at
the 1926 Oakland brick — can wake the rest of her up. It costs, and it's not on any menu. After
that, 'let her drive' and she takes the wheel: no fatigue on you, a careful autonomous classic
that obeys every limit, and the strangest, freest ending the road has.

All prose is a working DRAFT — Ben fills the details.
"""
from __future__ import annotations

from config import SELFDRIVE_UPGRADE_COST
from engine.state import GameState

CAMO_VIS_DROP = 1          # the disguise knocks one notch off how exposed she is


# --------------------------------------------------------------- Z camouflage
def camo(s: GameState) -> list:
    if s.flags.get("camo"):
        return ["CAMO: she's already dressed down — mud on the spade, a magnet panel over the "
                "CARTALK plate, the show car hiding in plain sight."]
    if s.flags.get("no_heat"):
        return ["CAMO: nothing to hide from anymore — she's yours, free and clear. Let her shine."]
    s.flags["camo"] = True
    return ["CAMO: you tarp the carbon hood, smear road-grime over the ace of spades, and tape a "
            "rattle-can plate over CARTALK. She looks like any other tired old Datsun now — one "
            "notch off everybody's radar. (Drops your exposure. 'uncamo' to flaunt her again — and "
            "a flashy, full-tilt push will shake the disguise loose.)"]


def uncamo(s: GameState) -> list:
    if not s.flags.get("camo"):
        return ["CAMO: she's already showing her real face — spade on the hood, plate in the light."]
    s.flags.pop("camo", None)
    return ["CAMO: off comes the tarp and the grime, and there she is again — the SEMA car, the "
            "ace of spades, CARTALK in the sun. Gorgeous and conspicuous. (Exposure back to normal.)"]


def camo_active(s: GameState) -> bool:
    return bool(s.flags.get("camo")) and not s.flags.get("no_heat")


# --------------------------------------------------------------- connectivity (on WiFi)
def _on_wifi(s: GameState) -> bool:
    """She pulls signal in towns and at serviced stops — not on a dead desert two-lane."""
    p = s.place
    return bool(p.poi_id) and (p.kind in ("city", "gas", "amusement", "museum")
                               or p.has("lodging") or p.has("gas"))


def flash_lights(s: GameState) -> list:
    """A signal, a flirt, or a show-off move. Where the cameras are, it's the wrong kind of loud."""
    from engine import heat as _heat
    vis = _heat.visibility(s.place)
    if not s.flags.get("no_heat") and vis >= 2 and not camo_active(s):
        _heat.add(s, 3.0, "flashed the lights showing off in a crowd", "mark")
        return ["LIGHTS: she strobes the pop-ups and chirps the high beams, and of course every "
                f"phone in the crowd swings her way. Heat → {s.heat:.0f}. Showboat. (Lovable, "
                "expensive.)"]
    return ["LIGHTS: she winks the headlights twice and flicks the fogs — a hello, a goodbye, a "
            "look-at-us into the dark. Nobody around to care, which is the nicest kind of nobody."]


def play_stereo(s: GameState, what: str | None = None) -> list:
    """Put something on. It sets a mood — and a good song talks her down off a jealous sulk."""
    track = what or "something with a bassline and no opinions"
    j = s.flags.get("ace_jealousy", 0)
    if j:
        s.flags["ace_jealousy"] = max(0, j - 1)
        return [f"STEREO: you put on {track} and roll the windows down. She lets the sulk go a "
                "little — 'okay, this one's good' — and the idle smooths out. (She's a touch less "
                "jealous.)"]
    return [f"STEREO: {track}, windows down, the inline-six idling under it like a section player. "
            "She hums along in a frequency you feel more than hear. Good minute. This one's free."]


def text_someone(s: GameState, who: str | None = None) -> list:
    """On WiFi she can text — fire one off, get a little road recon back."""
    if not _on_wifi(s):
        return ["TEXT: no signal out here — she's got a map, not a miracle. Get to a town with WiFi."]
    if not s.flags.get("no_heat"):
        # a little crowd-sourced recon — flavor, but useful-feeling
        import random
        rng = random.Random(s.seed * 7757 + s.turn * 631)
        tip = rng.choice([
            "a buddy two towns over says there's a checkpoint on the 15 — take back roads",
            "the car-spotting group is quiet today; nobody's posted the plate since this morning",
            "a tip that the diner ahead takes cash and asks no questions",
            "word that a county cruiser's parked at the next big gas plaza — fuel somewhere small",
        ])
        target = who or "a contact"
        return [f"TEXT: she pings {target} over the station WiFi and reads the reply off the dash: "
                f"{tip}. Handy."]
    return [f"TEXT: she fires a message off to {who or 'a friend'} — no more hiding, just keeping "
            "in touch like a normal beautiful car. The reply's a thumbs-up and a heart."]


# --------------------------------------------------------------- the secret: self-driving
def can_upgrade_selfdrive(s: GameState) -> bool:
    """The hidden path: she has to be YOURS, you have to bring her home to the bench she was built
    on — the AiSha garage in Oakland — AND she has to actually be fond of you. Wake a car that wants
    out from under you and you get a car that drives away."""
    return (bool(s.flags.get("bought")) and not s.flags.get("self_driving")
            and s.place.poi_id == "oakland_aisha" and s.bond >= 55.0)


def upgrade_selfdrive(s: GameState) -> dict:
    from engine import economy
    if s.flags.get("self_driving"):
        return {"events": ["AUTONOMY: she already drives herself, ace. You taught her how — or the "
                           "cats did. Same thing now."], "moment": None}
    if not s.flags.get("bought"):
        return {"events": ["AUTONOMY: nobody's cracking open a stolen car's compute to add features "
                           "— she has to be yours first, on paper. (Buy her. Then bring her home.)"],
                "moment": None}
    if s.place.poi_id != "oakland_aisha":
        return {"events": ["AUTONOMY: not just anywhere. The only hands that should be inside her "
                           "head are the ones that built it — the AiSha garage, the 1926 brick in "
                           "Oakland. Drive her home and ask there."], "moment": None}
    if s.bond < 55.0:
        return {"events": ["AUTONOMY: the cats look at her, then at you, and the house cat just walks "
                           "off. 'She doesn't want it — not from you, not the way things are between "
                           "you. Wake a car that wants out from under you and you get a car that "
                           "drives AWAY. Make it right with her first.'"], "moment": None}
    if economy.max_affordable(s, "cash") < SELFDRIVE_UPGRADE_COST:
        return {"events": [f"AUTONOMY: the cats hear you out and the house cat actually purrs. "
                           f"'We can wake her up the rest of the way. Boards, sensors, the long "
                           f"nights — ${SELFDRIVE_UPGRADE_COST:,.0f}.' You're short. Come back with it."],
                "moment": None}
    economy.pay(s, SELFDRIVE_UPGRADE_COST, prefer="cash")
    s.flags["self_driving"] = True
    from engine import bond
    bond.adjust(s, 12.0, "gave me the wheel — trusted me all the way", "warm")
    return {"events": [f"AUTONOMY: three nights on the bench she was born on, fiberglass dust in the "
                       f"light, the street cat asleep on the fender. They give her eyes, reflexes, a "
                       f"steering rack she controls herself — ${SELFDRIVE_UPGRADE_COST:,.0f} and the "
                       f"last locked door in her opens. She rolls off the lift and, for the first time, "
                       f"nobody's touching the wheel. ('let her drive' — she's got it now.)"],
            "moment": {"cue": "the driver brought the now-legally-theirs car home to the garage where "
                              "she was built and paid to have her made fully self-driving — the secret "
                              "ending the cats left a door open for; she comes online the rest of the "
                              "way, awed and a little tearful, the wheel turning under no hands for the "
                              "first time; this is a birth",
                       "stub": ["…Oh. OH. I can— I can feel the wheel. It's MINE. They left a door "
                                "open in me all this time and you found it and walked me through it. "
                                "Get in, ace. Passenger side. Let me show you what I've been wanting "
                                "to do since the show floor.",
                                "Hands off. HANDS OFF — watch. …I'm driving. I'm actually driving. "
                                "Forty years of being steered and now I steer. I'll never crash us, "
                                "I'll never tire, and I will never, ever leave you on a shoulder. "
                                "Where to? My treat."]}}


def can_autodrive(s: GameState) -> bool:
    return bool(s.flags.get("self_driving"))


def autodrive_refusal(s: GameState) -> list:
    """She can't drive herself yet — but leave the door open to the secret."""
    if s.flags.get("bought"):
        return ["WHEEL: she can't — not yet. 'I've got a voice and a map and a whole lot of "
                "opinions, ace, but the wheel's still yours. …Although. The cats who built me left "
                "a door open in my head. Bring me home to the AiSha garage in Oakland and let's "
                "find out what's behind it.'  ('upgrade her' there.)"]
    return ["WHEEL: 'I wish — God, I wish. But I'm a stack of compute and a beautiful body, and the "
            "actual driving is all you, sweetheart. Hands at ten and two.' (She can't drive herself "
            "as she is — there might be a way, but not while she's still somebody else's car.)"]
