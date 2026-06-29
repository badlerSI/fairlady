"""The improv partner — 'yes, and' for anything the player proposes.

RIDE OR DIE is an improv-comedy road movie. When the driver proposes a freeform ACTION the engine has no
verb for ("climb the water tower", "let me hotwire the ATM", "I jump on the hood and sing"), this routes
it to the DM (judge.assess kind='improv' — the rop1 Nemotron online, a rubric offline) which rules whether
it's PLAUSIBLE in the fiction. Then Ace NARRATES the verdict: a charming 'yes, and' if it works (egging you
on, with a small consequence if it's loud/illegal), or a 'no, but' if it can't happen (shot down with
affection and a joke, then a redirect to what you CAN do here).

The DM never grants arbitrary state — no money, no wins, no teleports. The only mechanical effects are
small, bounded, and earned by the FICTION: a loud/illegal stunt nudges heat; a 'search/look in/dig here'
attempt can surface a roadside find if the place has one. Everything else is pure narration — the point is
a generous, rule-bound scene partner who keeps saying yes. Prose is a working DRAFT for Ben.
"""
from __future__ import annotations

from engine.state import GameState

# attempts that are really "poke around for stuff" — let the finds layer answer them
_SEARCH = ("search", "look in", "look inside", "look around", "look under", "dig", "rummage", "rifle",
           "check the", "poke around", "scrounge", "forage", "look for", "rummage through", "go through")


def _facts(s: GameState) -> str:
    p = s.place
    bits = [f"at {p.name} ({getattr(p, 'region', '')}), kind={getattr(p, 'kind', 'spot')}"]
    try:
        from engine import weather
        w = weather.daily(s)
        bits.append(f"{w['condition']}, {w['low_f']:.0f}-{w['high_f']:.0f}F")
    except Exception:
        pass
    bits.append(f"{s.clock.strftime('%-I%p').lower()}, day {s.day}")
    bits.append("driving a stolen white 1972 Datsun 240Z (she talks); heat " + s.heat_label
                if hasattr(s, "heat_label") else "in a stolen 1972 Datsun 240Z")
    return "; ".join(bits)


def adjudicate(s: GameState, raw: str) -> dict:
    """Rule on a freeform action and hand back a narrated moment + any bounded effect. Returns
    {events, moment, possible}."""
    from engine import judge
    low = (raw or "").lower().strip()
    events: list = []

    # 'search/look in X' here → defer to the roadside-find layer if it has something to give
    if any(k in low for k in _SEARCH):
        from engine import finds
        item = finds.maybe_spot(s, s.place, talked=5)         # talked high so min_talk gates don't block a deliberate look
        if item:
            events.append(finds.spot_event(item))
            return {"events": events, "possible": True,
                    "moment": {"cue": f"the driver pokes around ({raw}) and ACE spots something worth "
                                      "grabbing on the shoulder/ground; she points it out, pleased they "
                                      "slowed down to look",
                               "stub": ["Hold up — look. Down there, half in the dirt. People drive right "
                                        "past things like that. Grab it?"]}}

    v = judge.assess(s, "improv", raw, difficulty=3, context="freeform action in an improv road movie",
                     facts=_facts(s))
    possible = bool(v.get("pass"))
    messing = bool(v.get("messing"))
    risky = bool(v.get("risky"))
    reason = v.get("reason", "")

    # the ONLY mechanical effect: a loud/illegal/dangerous stunt that lands draws a small bit of heat
    if possible and risky and not s.flags.get("no_heat") and not s.flags.get("bob_mode"):
        from engine import heat as _heat
        _heat.add(s, 3.0, "pulled a stunt that turned a few heads", "mark")

    if messing:
        moment = {"cue": f"the driver is goofing / proposing nonsense ('{raw[:120]}'); Ace doesn't take "
                         "the bait — she's amused, plays along ONE dry beat, and steers back to the road; "
                         "never breaks character, never lets nonsense move the game",
                  "stub": ["Mm-hm. Sure, ace. And I'm a submarine. …You done? The West isn't getting any "
                           "closer with you doing bits in a parking lot."]}
    elif possible:
        moment = {"cue": f"the driver wants to: '{raw[:160]}'. The DM ruled YES — it WORKS in a "
                         f"stolen-car road-movie way ({reason}). Narrate Ace EGGING THEM ON: the thing "
                         f"actually happens, vivid and quick and fun" + (", and it draws an eye — a little "
                         "heat" if risky else ", harmless and charming") + ". Stay in the rules of a "
                         "fugitive road trip; never grant money, a win, or teleporting.",
                  "stub": (["Oh, we're DOING this. Okay — go, go, I've got the engine running. …Yeah. "
                            "YEAH. Okay that was extremely stupid and I loved it. Now MOVE, somebody saw."]
                           if risky else
                           ["Ha — yeah, go on. Why not. We've got nothing but road and bad ideas. …There "
                            "you go. See? The trip's better when you actually DO the dumb little thing."])}
    else:
        why = reason or "that's not on the menu in this universe"
        moment = {"cue": f"the driver wants to: '{raw[:160]}'. The DM ruled NO — it can't happen in this "
                         f"world ({reason}). Narrate Ace shooting it down with AFFECTION and a joke, then "
                         f"redirecting to something they CAN actually do here. Never mean, never a lecture.",
                  "stub": [f"Ace. Honey. I'm a car — a very good car, but {why}. …Tell you what we CAN do, "
                           "though: pick a road and let's go be a problem somewhere real."]}
    return {"events": events, "moment": moment, "possible": possible}
