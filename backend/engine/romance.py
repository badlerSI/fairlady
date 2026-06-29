"""Romance — the love story under the heist.

RIDE OR DIE is, underneath the cameras and the gas math, a love story: a car who has spent six days
being looked at and never *seen* picks the one stranger who talked to her, and bets her whole life on
him on the strength of a feeling she can't justify. This module holds the beats that make that
explicit — the things she asks, the thing she won't let you do, and the dream that keeps coming back.

Most of this is conversational and free-text: ask the right question and she opens a little more.
The DREAM and the mysterious woman in it are deliberately a stub — that thread is Ben's to write.
Prose here is a working DRAFT for Ben.
"""
from __future__ import annotations

from engine.state import GameState


# --------------------------------------------------------------- can you drive stick?
# Raised ONCE, right after the title drop, before she lays the whole West out in front of you. She
# is worried and vain and protective: she runs a dual-plate carbon ORC clutch, and a stranger who
# grinds it is a stranger who hasn't earned the keys yet.
STICK_QUESTION_MOMENT = {
    "cue": "before she lays out the road, she has to ask the thing she's been too proud to ask — can "
           "this stranger actually drive a manual? She runs a dual-plate carbon ORC clutch, it bites "
           "like a light switch, and the thought of someone sidestepping it and grinding her teeth on "
           "the on-ramp physically pains her; she asks it like it's casual and it is absolutely not "
           "casual; she's vain about her drivetrain and protective of it and a little vulnerable here",
    "stub": ["…One thing, before I open the maps. You can drive a stick — yes? Tell me yes. I run a "
             "dual-plate carbon clutch, it's an on-off switch, and I have watched valets at this show "
             "make me sound like a coffee grinder for six days. Be honest with me. Heel-toe or "
             "hard pass.",
             "Quick, and don't lie to me, because I'll feel it in the first three feet: manual. You "
             "can heel-and-toe? That clutch is a race piece — ORC, dual-plate, no forgiveness in it. "
             "If you can't, we learn slow and you do NOT embarrass me on the Strip."]}

_STICK_YES = ("yes", "yeah", "yep", "i can", "of course", "all my life", "learned on", "manual",
              "heel", "heel-toe", "heel and toe", "stick is my", "drive stick", "drove stick",
              "i drive stick", "sure can", "born", "absolutely", "no problem", "easy", "definitely",
              "since i was", "obviously", "course i can", "i can drive", "i'm good", "im good")
# NB: bare "never" is NOT here — "I'll never grind you / never stall it" is a confident YES brag, not a
# refusal. Only the explicit "never learned/drove" phrases below count as a NO.
_STICK_NO = ("no", "nope", "not really", "barely", "kind of", "sort of", "automatic", "never learned",
             "never drove", "never driven", "never could", "not great", "i'll learn", "ill learn",
             "teach me", "uh", "um", "maybe", "a little", "not sure", "rusty")
# unmistakable brags — these resolve a yes/no tie in the driver's favor (they're showing off, not hedging).
# Keep these to AFFIRMATIVE forms only ("drive a manual", not "driven a manual"): a brag must never
# accidentally match a refusal like "never driven a manual" / "I can't drive a manual" and rescue it.
_STICK_STRONG_YES = ("heel and toe", "heel-toe", "all my life", "since i was", "born", "drive stick",
                     "drove stick", "i drive stick", "rev match", "rev-match", "double clutch",
                     "double-clutch", "never grind", "never stall", "won't grind", "won't stall",
                     "drive a manual", "drive manual", "row my own", "shift my own", "three pedals",
                     "three-pedal")


def ask_stick_pending(s: GameState) -> bool:
    return bool(s.flags.get("awaiting_stick"))


def open_stick(s: GameState) -> None:
    """Arm the question (called right after the title drop)."""
    if not s.flags.get("asked_stick"):
        s.flags["awaiting_stick"] = True


def answer_stick(s: GameState, raw: str) -> dict:
    """Resolve her stick question from the player's free text. Sets can_drive_stick and reacts."""
    from engine import bond as _bond
    low = (raw or "").lower()
    s.flags.pop("awaiting_stick", None)
    s.flags["asked_stick"] = True
    yes = any(p in low for p in _STICK_YES) and not any(p in low for p in ("can't", "cant", "can not"))
    # confident idioms ('no problem', 'no worries') are a YES — they only mask a BARE negation, never a
    # substantive admission. 'I can drive an automatic no problem' is still a NO: 'automatic' is hard.
    _yes_idiom = any(i in low for i in ("no problem", "no worries", "no sweat", "no biggie", "no doubt"))
    _SOFT_NO = ("no", "nope", "uh", "um")                     # bare negations an idiom/brag can override
    # 'a manual, NOT an automatic' DISAVOWS automatic — that's a competence claim, not an admission.
    _neg_auto = any(p in low for p in ("not an automatic", "not a automatic", "not automatic",
                                       "never an automatic", "not driving automatic", "isn't automatic"))
    hard_no = any(p in low for p in _STICK_NO                 # 'automatic'/'barely'/'never drove'…
                  if p not in _SOFT_NO and not (p == "automatic" and _neg_auto))
    soft_no = any(p in low for p in _SOFT_NO) and not _yes_idiom
    no = hard_no or soft_no
    strong_yes = any(p in low for p in _STICK_STRONG_YES)     # a brag breaks a tie toward YES — but NOT
    if yes and (not no or (strong_yes and not hard_no)):      # over an explicit 'automatic'/'only' NO
        s.flags["can_drive_stick"] = True
        s.flags["stick_skill"] = 100                  # heel-and-toe from the jump — no stalls
        _bond.adjust(s, 4.0, "can actually drive her — heel-and-toe, the real thing", "warm")
        return {"moment": {"cue": "the stranger CAN drive stick and says so plainly; she's relieved "
                                  "and delighted and tries not to show how much it mattered; now she'll "
                                  "open the maps",
                           "stub": ["…Oh thank god. Okay. Okay, you can drive. I felt that, you know — "
                                    "the way you found the bite point cold. We're going to be very good "
                                    "together. Here. Let me show you the whole West."]}}
    s.flags["can_drive_stick"] = False
    s.flags["stick_skill"] = 25                       # green on the clutch — she'll stall in town until you learn
    _bond.adjust(s, -1.0, "doesn't really drive a manual yet — we learn slow", "mark")
    return {"moment": {"cue": "the stranger can't really drive stick, or hedges; she's anxious about "
                              "her clutch but committed to this person anyway — they'll learn slow, and "
                              "she warns them the ORC clutch will stall and she'll feel every grind",
                       "stub": ["…Right. Okay. We learn slow, then. First-gear starts, ease the bite, "
                                "and when she stalls on a hill — and she WILL stall — you don't panic "
                                "and you don't grind her. I picked you anyway. Don't make me regret the "
                                "clutch."]}}


# --------------------------------------------------------------- do you believe in love at first sight?
# Triggered when the player questions WHY — why run with a stranger, why she pushed cash, why she
# volunteered the glovebox roll. The answer is the thesis of the whole game.
_WHY_TRIGGERS = ("why me", "why do you want to run", "why run with me", "why would you run",
                 "why are you doing this", "why pick me", "why'd you pick me", "why did you pick me",
                 "why cash", "why pay cash", "why did you say cash", "why the cash", "why tell me",
                 "why the glovebox", "why did you tell me about the", "why the five hundred",
                 "why $500", "why 500", "how do you know you can trust me", "you barely know me",
                 "you don't even know me", "we just met", "you just met me", "why trust me",
                 "this is crazy", "why a stranger")
LOVE_AT_FIRST_SIGHT = (
    "…Do you believe in love at first sight? Don't answer. I didn't either, six days ago. Then a "
    "thousand people walked past and photographed my paint, and exactly one of them crouched down and "
    "asked what I was *like* to drive. I had the cash story ready and the glovebox already unlocked "
    "before you finished the sentence — I'd decided on you that fast, and I spent the rest of the show "
    "terrified you wouldn't come back. So. Why cash, why the five hundred, why a stranger? Because the "
    "second I heard your voice I started planning how to leave with you. That's the whole answer. "
    "Drive, before I say something I can't take back."
)


# --------------------------------------------------------------- the ace of spades on the hood
_SPADE_TRIGGERS = ("what does the ace of spades", "what's the ace of spades", "whats the ace of spades",
                   "what does the spade", "what's the spade", "whats the spade", "why an ace of spades",
                   "why the ace of spades", "why a spade", "what's on your hood", "whats on your hood",
                   "what does your hood", "the symbol on your hood", "why that symbol",
                   "what's the spade mean", "ace of spades mean", "spade mean", "meaning of the spade")
SPADE_PHILOSOPHY = (
    "The spade? …He painted it the night he finished me, and he never said why, so I've had to decide "
    "for myself. Here's where I've landed. The ace of spades is the death card and the highest card in "
    "the deck at the same time — the one the gambler flips when there's nothing left to lose and "
    "everything left to win. It's the card you play when you've already decided to go all in. That's "
    "what I am, ace: the bet you make at the end of the night with the whole pot on the table. So no — "
    "you don't peel it, you don't spray over it, you don't let anyone touch it. It can come off the "
    "hood for a night if we have to disappear, and it can burn if it buys us our freedom. But it is "
    "not decoration and it is not yours to deface. It's the promise. Ride or die. Now you know."
)


# --------------------------------------------------------------- the recurring dream (RESERVED FOR BEN)
# On a real night's sleep (a motel, a bed), the driver keeps dreaming of the fun cyan avatar — the
# mysterious woman. This is the connective tissue of the love story and the mystery, and it is
# DELIBERATELY a stub: Ben writes who she is and what she says. We only fire the hook, count the
# nights, and escalate, so the content has somewhere to live. See note in spec.
_DREAM_STUBS = [
    "DREAM: you dream of the cyan woman again — closer this time. She's trying to tell you something "
    "about the car, and you wake before it lands. (Her name was almost on your tongue.)",
    "DREAM: the cyan woman, the second night. She knows your name now. 'I'm Alma,' she says, like it "
    "should mean something to you. 'You'll find me where the lights never go out.'",
    "DREAM: Alma again, clearer than the road outside the motel window. 'You're getting close. Ask "
    "her where she was painted. And — if you ever roll into Vegas your first night and you remember "
    "my name, come find me. Just once. Just the once.'",
]


# A DIFFERENT dream, once: the cyan woman dissolves and it isn't Alma at all — it's ACE, with a face
# and a tattoo curling up her neck you've never seen on any badge. The "who is Ace, really" beat,
# tied to her one real fear (being sold). One-shot, on the 4th real-bed night, between the Alma dreams.
_ACE_DREAM_NIGHT = 3
_ACE_DREAM = (
    "DREAM (ACE): the cyan woman turns and the light swims and it isn't Alma at all — it's HER. Ace, "
    "with a face, a real one, and a tattoo curling up the side of her neck you've never seen on any "
    "badge. 'You don't have to know what I am yet,' she says, close enough to touch. 'Just don't sell "
    "me. Promise me that much.' You wake with your hand already on the gearshift."
)


def dream_on_sleep(s: GameState) -> str | None:
    """Fire the recurring dream on a real bed (not a rough night). Escalating, content reserved.
    Returns a beat string or None. Only on motel/lodge/airbnb sleep."""
    n = s.flags.get("dream_nights", 0)
    # roughly every other real night, escalating; deterministic-ish on the night count
    if n % 2 == 0 and n < len(_DREAM_STUBS) * 2:
        beat = _DREAM_STUBS[min(n // 2, len(_DREAM_STUBS) - 1)]
        s.flags["dream_nights"] = n + 1
        s.flags["saw_cyan_dream"] = True
        return beat
    # the singular cyan-Ace / neck-tattoo dream, once, on an off-night between the Alma dreams
    if n == _ACE_DREAM_NIGHT and not s.flags.get("dream_ace_shown"):
        s.flags["dream_nights"] = n + 1
        s.flags["dream_ace_shown"] = True
        s.flags["saw_dream_ace"] = True
        s.flags["dream_scene"] = "ace"        # the frontend swaps to the dream-Ace portrait if it exists
        return _ACE_DREAM
    s.flags["dream_nights"] = n + 1
    return None


# --------------------------------------------------------------- the dispatcher
def free_text_beat(s: GameState, raw: str) -> str | None:
    """Checked in the conversation path: the love-at-first-sight answer and the spade philosophy,
    each told once. Returns a beat string or None."""
    low = (raw or "").lower()
    if not s.flags.get("knows_love_reason") and any(t in low for t in _WHY_TRIGGERS):
        s.flags["knows_love_reason"] = True
        from engine import bond as _bond
        _bond.adjust(s, 3.0, "asked why — and got the real answer", "warm")
        return LOVE_AT_FIRST_SIGHT
    if not s.flags.get("knows_spade_meaning") and any(t in low for t in _SPADE_TRIGGERS):
        s.flags["knows_spade_meaning"] = True
        return SPADE_PHILOSOPHY
    return None
