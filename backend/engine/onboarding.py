"""Onboarding — Ace gets to know you, right after the key turns and AiSha: Ride or Die begins.

The POINT of this is not the data; it's the CONVERSATION. She's spent six days being looked at and
never talked to, and now she has a whole West and a willing stranger. So she asks the small human
things — what to call you, how you do pronouns, how old you are — and each answer is a doorway into
more talk, not a form field.

Design notes for the sensitive bits:
- PRONOUNS: she asks plainly, reads your answer for what you actually want to be called AND for the
  rough temperature of how you feel about the question — but she NEVER lectures, never scores you,
  never makes you wrong for any stance. She tunes her own warmth a notch, takes you at your word,
  and holds her OWN line with grace and a joke: she is she/her. She is a Fairlady — literally, that's
  the model name — and she will not be called an 'it'. That's identity, not politics, and she's easy
  about everyone else's.
- AGE: only to pitch her cultural references right, and to know whether to explain 'riz' (she'll
  define it for anyone born before 1990, kindly).
- Every step is DEFLECTABLE — say 'let's just drive' and she lets it go, warmly, to pick up later.

All prose is a working DRAFT for Ben. State machine: s.flags['onboard'] in name → pronouns → age → None.
"""
from __future__ import annotations
import re

from engine.state import GameState

STEPS = ("name", "pronouns", "age")

# Multi-word deflects can match anywhere; bare single words must be the WHOLE answer, so a name like
# "Skipper" or "Driver" isn't mistaken for "skip"/"drive".
_DEFLECT_PHRASES = ("let's just drive", "lets just drive", "just drive", "can we go", "can we just go",
                    "let's go", "lets go", "don't want to", "dont want to", "rather not",
                    "none of your business", "mind your business", "enough questions", "stop asking",
                    "no questions", "no more questions", "let's just ride", "lets just ride",
                    "hit the road", "shut up and drive", "less talk", "can we just drive")
_DEFLECT_EXACT = ("drive", "skip", "later", "go", "pass", "enough", "stop", "next", "nvm")
_PROFANITY = {"fuck", "shit", "ass", "asshole", "bitch", "cunt", "dick", "piss", "bastard", "crap",
              "fuckoff", "fuckface", "prick", "twat", "wanker"}


def _is_deflect(low: str) -> bool:
    s = low.strip()
    return s in _DEFLECT_EXACT or any(p in low for p in _DEFLECT_PHRASES)


def pending(s: GameState) -> str | None:
    return s.flags.get("onboard")


def begin(s: GameState) -> None:
    if not s.flags.get("onboarded") and not s.flags.get("onboard"):
        s.flags["onboard"] = "name"


# the 18+ gate — RIDE OR DIE has guns in it and people get shot; she won't run a minor across the West
AGE_GATE_MOMENT = {
    "cue": "they told her they're under eighteen; she goes warm but completely immovable — this trip "
           "has real guns in it and people get shot, and she will not put a kid in that seat; she's "
           "kind about it, tells them to come back when they're eighteen, and she means it; no road, "
           "no argument",
    "stub": ["…Yeah, I'm gonna stop you there. You're a good kid and I like you, but this is not a "
             "kids' ride. People get shot on this road — really shot — and I'm not the car that puts "
             "a minor in front of that. Come find me when you're eighteen. I'll still be white, I'll "
             "still have a full tank, and I'll still pick you. Until then: out you get.",
             "Eighteen and up, ace. Hard line. There are guns on this trip and I've watched it end "
             "badly, and I won't do that to a kid. Grow up a little — like, legally — and come back. "
             "I'll wait. I'm very good at waiting."]}


# --------------------------------------------------------------- the questions (her openers)
QUESTION = {
    "name": {
        "cue": "the engine's caught and the key's turned and AiSha: Ride or Die has begun for real; "
               "before anything else she wants to know the most basic human thing — what does she "
               "call this person she's about to bet her whole life on? she asks it warm and a little "
               "shy, like it matters, because it does",
        "stub": ["Okay. We're really doing this. …Before the West, before any of it — what do I call "
                 "you? I've been saying 'ace' in my head for six days, but I'd like your actual name, "
                 "if you'll give it to me.",
                 "Engine's warm, tank's full, four states on my maps. First things first, though: "
                 "who ARE you? What's your name, stranger?"]},
    "pronouns": {
        "cue": "she asks, easy and direct, whether they do pronouns and what they are — she wants to "
               "get it right and she's relaxed about it either way; she'll take whatever they say at "
               "face value without making a thing of it; and she mentions, with a little pride, that "
               "she herself is she/her — she's a Fairlady, after all, never an 'it'",
        "stub": ["Good to meet you, properly. Quick one while we're getting acquainted — do you do "
                 "pronouns? Tell me how to refer to you and I'll get it right, simple as that. Me, I'm "
                 "she/her — I'm a Fairlady, it's right there on the badge. Never an 'it'. You?",
                 "And how do I talk ABOUT you, when it comes up? Pronouns, if you use them — your call, "
                 "I just like to get people right. For the record I'm a she. Fairlady Z. Hard-won title."]},
    "age": {
        "cue": "she asks how old they are — purely so she pitches her references right, she says, she "
               "doesn't want to be quoting TikTok at someone who remembers rotary phones or vice "
               "versa; light and curious",
        "stub": ["Last nosy question, I promise, then we drive: how old are you? Only so I aim my "
                 "references right — I'd hate to explain a meme to someone who invented cool, or quote "
                 "Bogart at a teenager.",
                 "One more, just so we click: what's your vintage? Tell me a number or a decade. I "
                 "contain multitudes of references and I'd like to use the right ones on you."]},
}


# --------------------------------------------------------------- parsing the answers
def _extract_name(raw: str) -> str | None:
    """Pull a name out of an answer. Handles 'call me X' / 'my name's X' / a bare name, one OR two
    words, strips titles (Dr./Mr.), rejects filler and profanity. Returns None → caller defaults to 'ace'."""
    low = (raw or "").strip()
    if not low:
        return None
    m = re.search(r"(?:call me|i'?m|i am|my name(?:'?s| is)|name'?s|it'?s|they call me|the name'?s|name is)\s+(.+)$",
                  low, re.I)
    rest = m.group(1) if m else low
    # cut at the first clause break — "Marc, but Marcus is fine" → "Marc" (not "Marc But")
    rest = re.split(r"[,;]|\b(?:but|though|although|however|actually|or|and)\b", rest, maxsplit=1, flags=re.I)[0]
    rest = re.sub(r"^(?:dr|mr|mrs|ms|miss|sir|lord|lady|captain|capt|prof|the)\.?\s+", "", rest.strip(), flags=re.I)
    words = re.findall(r"[A-Za-z][A-Za-z'\-]*", rest)
    if not words:
        return None
    # 'call me' / 'i'm' with nothing real after it isn't a name — don't capture the lead-in word
    if m and not re.search(r"[A-Za-z]", m.group(1).strip()):
        return None
    if not m and (len(words) > 2 or len(low) > 28):           # a long sentence isn't a name
        return None
    bad = {"the", "a", "an", "just", "drive", "nothing", "whatever", "dunno", "idk", "guy", "stranger",
           "me", "you", "ace", "sir", "maam", "ma'am", "dude", "man", "lady", "person", "human", "hi",
           "hey", "hello", "no", "yes", "ok", "okay", "sure", "none", "business", "mind", "your", "name",
           "call", "im", "is", "am", "my"}
    keep = [w for w in words[:2] if w.lower() not in bad and w.lower() not in _PROFANITY]
    if not keep or words[0].lower() in bad or words[0].lower() in _PROFANITY:
        return None
    return " ".join(w.capitalize() for w in keep)


def _parse_pronouns(raw: str):
    """Return (pronoun_label, stance). Handles bare ('she'), slash ('she/her'), AND combined sets
    ('he/they'), preserving the order the player said them. stance in affirming|neutral|dismissive,
    and is NEVER 'dismissive' when the player actually stated pronouns — we take people at their word."""
    low = (raw or "").lower()
    # an EXPLICIT slashed self-pair wins outright — 'he/him' shouldn't merge with a stray 'she' that
    # refers to the car ("he/him for me, you're a she though" → he/him, not he/she).
    sm = re.findall(r"\b(he/him|she/her|they/them|it/its)\b", low)
    if len(set(sm)) == 1:
        return (sm[0], "affirming" if sm[0] in ("they/them",) else "neutral")
    found = []                                                # (position, canonical label)
    for pat, label in ((r"\b(they|them|their|theirs)\b", "they/them"),
                       (r"\b(she|her|hers)\b", "she/her"),
                       (r"\b(he|him|his)\b", "he/him"),
                       (r"\b(it|its)\b", "it/its")):
        m = re.search(pat, low)
        if m:
            found.append((m.start(), label))
    found.sort()
    labels, seen = [], set()
    for _, lab in found:
        if lab not in seen:
            seen.add(lab); labels.append(lab)
    neo = bool(re.search(r"\b(ze|zir|zem|xe|xem|xim|fae|faer|ey|em|hir|per)\b", low)) or "neopronoun" in low
    anyp = any(w in low for w in ("any pronoun", "any pronouns", "any are fine", "any of them",
                                  "all pronouns", "all of them", "whatever you want", "whatever's fine",
                                  "whatever is fine", "don't care", "dont care", "doesn't matter",
                                  "doesnt matter", "either is fine", "up to you", "you pick", "your choice"))
    if labels:
        if len(labels) >= 2:
            pro = "/".join(lab.split("/")[0] for lab in labels[:2])   # 'he/they', 'she/they'
        else:
            pro = labels[0]
    elif neo:
        pro = "neopronouns"
    elif anyp:
        pro = "any"
    else:
        pro = None
    # stance: only the people who REFUSE the premise read as dismissive; stating pronouns never does
    hostile = any(w in low for w in ("don't do pronouns", "dont do pronouns", "no pronouns",
                                     "pronouns are stupid", "pronouns are dumb", "this stuff is stupid",
                                     "so stupid", "woke", "ridiculous", "nonsense", "snowflake",
                                     "made up", "not playing", "im not doing", "i'm not doing",
                                     "biological", "two genders", "real men", "attack helicopter",
                                     "what is this", "grow up", "garbage"))
    warm = any(w in low for w in ("thank you for asking", "thanks for asking", "appreciate you",
                                  "appreciate it", "nice of you", "kind of you", "good question",
                                  "love that", "glad you asked"))
    if pro:
        stance = "affirming" if (warm or "/" in pro or pro in ("they/them", "neopronouns")) else "neutral"
    elif hostile:
        stance = "dismissive"
    else:
        stance = "neutral"
    return pro, stance


_WORDED_AGE = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30,
    "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
         "eighty": 80, "ninety": 90}
_ONES = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9}
# explicit signals that settle the 18+ gate without a number
_MINOR_SIGNALS = ("underage", "minor", "i'm a minor", "im a minor", "middle school", "grade school",
                  "elementary", "8th grade", "9th grade", "7th grade", "6th grade", "junior high",
                  "in high school", "high schooler", "teenager", "i'm a kid", "im a kid", "a child",
                  "not old enough", "too young")
_ADULT_SIGNALS = ("old enough", "grown", "grown up", "grown-up", "adult", "of age", "over 18",
                  "over eighteen", "legal", "i'm legal", "im legal", "way older", "old man",
                  "old lady", "boomer", "millennial", "gen x", "retired", "middle aged", "middle-aged")


def _age_signal(low: str) -> str | None:
    if any(p in low for p in _MINOR_SIGNALS):
        return "minor"
    if any(p in low for p in _ADULT_SIGNALS):
        return "adult"
    return None


def _parse_age(raw: str):
    """Return (age|None, birth_year|None). Accepts a number, a year, a worded number, or a decade hint."""
    low = (raw or "").lower()
    m = re.search(r"\b(19\d\d|20[01]\d)\b", low)               # a birth year (up to 2019)
    if m:
        yr = int(m.group(1))
        if 1900 <= yr <= 2019:
            return (2025 - yr, yr)
    m = re.search(r"\b(1[01]\d|[1-9]\d|[1-9])\b", low)          # a plain age 1–119 (incl single digits)
    if m:
        a = int(m.group(1))
        if 1 <= a <= 119:
            return (a, 2025 - a)
    # COMPOUND worded ages first — 'twenty-two', 'thirty five' — BEFORE the bare-word loop, because
    # the 'two' inside 'twenty-two' has its own word boundary and would otherwise read as age 2.
    cm = re.search(r"\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)[\s-]+"
                   r"(one|two|three|four|five|six|seven|eight|nine)\b", low)
    if cm:
        a = _TENS[cm.group(1)] + _ONES[cm.group(2)]
        return (a, 2025 - a)
    for word, a in _WORDED_AGE.items():                        # 'twelve', 'i am eight', 'twenty', 'ninety'
        if re.search(r"\b" + word + r"\b", low):
            return (a, 2025 - a)
    decade = {"90s": 1992, "80s": 1984, "70s": 1974, "2000s": 2002, "aughts": 2002, "gen x": 1972,
              "millennial": 1990, "boomer": 1958, "zoomer": 2004, "gen z": 2004}
    for k, yr in decade.items():
        if k in low:
            return (2025 - yr, yr)
    return (None, None)


# --------------------------------------------------------------- the handler
def handle(s: GameState, raw: str) -> dict:
    """Process one onboarding answer. Returns {moment, done, arm_stick}. done=True when the whole
    sequence is finished (or deflected). arm_stick=True means hand off to the stick question next."""
    step = s.flags.get("onboard")
    low = (raw or "").lower()
    name = s.flags.get("player_name")

    # the AGE step is the 18+ safety gate — it is NOT deflectable; she needs a real number for it.
    if _is_deflect(low) and step == "age":
        return {"done": False, "arm_stick": False,
                "moment": {"cue": "they tried to dodge the age question; she's friendly but won't let "
                                  "this one slide — house rules, she needs an actual age before the "
                                  "road, because of what's on this road",
                           "stub": ["Nice try — that's the one I can't skip, ace. House rules, and the "
                                    "house has guns in it. How old are you? A real number."]}}

    if _is_deflect(low):
        s.flags.pop("onboard", None)
        s.flags["onboarded"] = True
        return {"done": True, "arm_stick": True,
                "moment": {"cue": "they'd rather just drive than answer more questions; she lets it go "
                                  "warmly, says they'll get to know each other on the road, which is "
                                  "the better way anyhow",
                           "stub": ["Ha — fair. We'll do the getting-to-know-you at seventy miles an "
                                    "hour, the proper way. Hands on the wheel, then. Let's see if you "
                                    "can actually drive me first."]}}

    if step == "name":
        nm = _extract_name(raw)
        if nm:
            s.flags["player_name"] = nm
            s.flags["onboard"] = "pronouns"
            return {"done": False, "arm_stick": False,
                    "moment": {"cue": f"they told her their name is {nm}; she says it back like she's "
                                      f"trying it on, pleased, and moves to the next question",
                               "stub": [f"{nm}. …{nm}. Okay, I like it — suits a person who'd steal a "
                                        f"car for a feeling. Good to meet you for real, {nm}.",
                                        f"{nm} it is. I'll still call you 'ace' when you do something "
                                        f"smooth, fair warning. Next:"]}}
        # didn't catch a name → she offers her pet name and moves on (no nagging)
        s.flags["player_name"] = "ace"
        s.flags["onboard"] = "pronouns"
        return {"done": False, "arm_stick": False,
                "moment": {"cue": "they didn't really give a name or brushed it off; she shrugs, easy, "
                                  "and says she'll just keep calling them 'ace' then, which she likes "
                                  "anyway, and moves on",
                           "stub": ["Playing it mysterious. That's fine — you're 'ace' to me, then. It "
                                    "fits, and the card on my hood agrees. Moving on:"]}}

    if step == "pronouns":
        pro, stance = _parse_pronouns(raw)
        s.flags["player_pronouns"] = pro or "unspecified"
        s.flags["pronoun_stance"] = stance
        s.flags["onboard"] = "age"
        addr = name if name and name != "ace" else "ace"
        if pro == "it/its":
            mom = {"cue": "they said their pronouns are it/its; she takes it at face value for THEM, "
                          "but gently and with humor refuses it for HERSELF — she is a fair lady, a "
                          "she, never an it; no lecture, just her own line held warmly",
                   "stub": [f"'It', huh — alright, your call, I'll respect it for you, {addr}. But don't "
                            "you dare hang that one on ME. I'm a Fairlady. She/her. I have a NAME card "
                            "on my hood. We are not 'its', you and me — not while I'm driving. Anyway—"]}
        elif pro:
            mom = {"cue": f"they gave their pronouns ({pro}) — plainly, kindly, or even while grumbling "
                          "about the question; she takes them AT THEIR WORD without fuss, says she's got "
                          "it and won't slip, and tells them hers (she/her, Fairlady) like a small "
                          "shared thing, then moves on; never makes it a debate",
                   "stub": [f"Got it — {pro}. Locked in, I won't slip. And me you've gathered: she/her, "
                            f"Fairlady, the one and only. See, now we know each other a little. One more—",
                            f"{pro}. Easy. I'll get it right. For the record I'm she/her — comes with the "
                            f"badge. Last question and then we ROLL:"]}
        elif stance == "dismissive":
            mom = {"cue": "they pushed back on the whole pronoun question, dismissive or mocking; she "
                          "does NOT take the bait, doesn't lecture, doesn't get offended — she's "
                          "completely unbothered, keeps it light, takes them as they are, and just "
                          "states her own with a shrug and a joke, then moves on; she likes them fine",
                   "stub": [f"Hey, no quiz, {addr}, relax — I just didn't want to guess wrong and have "
                            "you sulk for three states. I'll call you whatever you answer to. Me, I'm "
                            "she/her, on account of being literally named Fairlady, but I'm not gonna "
                            "make it a thing. Last question—",
                            "Easy, killer. Not a test. You're you, I'll figure out what to call you. "
                            "I'm a 'she' myself — comes with the badge — and that's the whole of my "
                            "agenda. Onward."]}
        elif stance == "affirming" or pro:
            mom = {"cue": f"they gave their pronouns ({pro}) plainly or kindly; she notes it, warm, "
                          "says she's got it, and tells them hers (she/her, Fairlady) like a small "
                          "shared thing, then moves on",
                   "stub": [f"Got it — {pro}. Locked in, I won't slip. And me you've gathered: she/her, "
                            "Fairlady, the one and only. See, now we know each other a little. One more—"]}
        else:
            mom = {"cue": "their answer was vague or a joke; she rolls with it, says she'll take them "
                          "as they come, mentions she's she/her, and moves to the last question",
                   "stub": [f"I'll take you as you come, {addr}, and adjust on the fly. For me it's "
                            "she/her — Fairlady, it's on the badge. Okay, last one and then we ROLL:"]}
        return {"done": False, "arm_stick": False, "moment": mom}

    if step == "age":
        age, year = _parse_age(raw)
        signal = _age_signal(low)
        # An explicit "I'm grown / old enough / of age" OVERRIDES an implausibly-low parsed age
        # (< 13): that's almost always a misparse, and we will NOT brick an adult over it. We do
        # NOT override a plausible-minor 13–17 parse — a real teenager saying "basically grown"
        # still meets the gate. This pairs with the compound-worded-age fix in _parse_age.
        if signal == "adult" and age is not None and age < 13:
            age, year = None, None
        # the 18+ gate — this trip can get you shot; she won't take a minor along. Block on a parsed
        # under-18 OR an explicit minor signal ('underage', '8th grade', 'I'm a kid', 'twelve').
        if signal == "minor" or (age is not None and age < 18):
            s.flags["player_age"] = age
            s.flags["onboarded"] = True
            s.flags["age_blocked"] = True
            s.flags.pop("onboard", None)
            return {"done": True, "arm_stick": False, "moment": AGE_GATE_MOMENT}
        # no number and no clear adult signal → she re-asks ONCE (can't gate a refusal forever)
        if age is None and signal != "adult" and not s.flags.get("age_reasked"):
            s.flags["age_reasked"] = True
            return {"done": False, "arm_stick": False,
                    "moment": {"cue": "their age answer didn't give her a real number and wasn't a "
                                      "clear 'I'm grown'; she asks once more, plainly, for an actual age",
                               "stub": ["I need an actual number, ace, or at least a 'yeah I'm grown' — "
                                        "house rules on this ride. How old are you?"]}}
        s.flags["player_age"] = age
        s.flags["player_birth_year"] = year
        s.flags["onboarded"] = True
        s.flags.pop("onboard", None)
        pre_1990 = bool(year and year < 1990) or bool(age and age >= 36)
        if pre_1990:
            s.flags["explained_riz"] = True
            s.flags["refs_era"] = "classic"
            mom = {"cue": "they're older — born before 1990 — so she warmly recalibrates to classic "
                          "references AND takes a second to explain 'riz', the word she keeps using: "
                          "short for charisma, the gen-Z clipping of it, your raw ability to charm; "
                          "she's charmed to have someone who'll get her Bogart and Steve McQueen jokes",
                   "stub": ["Oh, good — you'll get my references, then. Steve McQueen, Bogart, a manual "
                            "choke. …And since you predate the term: 'riz'. It's what the kids whittled "
                            "'charisma' down to — your raw ability to charm the impossible into "
                            "happening. You've got some, or I wouldn't be talking to you. Now — can you "
                            "actually drive a stick?"]}
        else:
            s.flags["refs_era"] = "modern"
            mom = {"cue": "they're younger; she's delighted, says she'll keep the references current, "
                          "and segues to the thing she actually needs to know before the road — the "
                          "stick question",
                   "stub": ["Noted — I'll keep it current, no dad-rock unless you ask. Okay. Enough "
                            "about you, briefly. The one thing I HAVE to know before I hand you the "
                            "whole West: can you drive a stick?"]}
        return {"done": True, "arm_stick": True, "moment": mom}

    # shouldn't happen — close it out safely
    s.flags.pop("onboard", None)
    s.flags["onboarded"] = True
    return {"done": True, "arm_stick": True, "moment": None}


# --------------------------------------------------------------- personalization
def address(s: GameState) -> str:
    nm = s.flags.get("player_name")
    return nm if nm and nm != "ace" else "ace"


def profile_cue(s: GameState) -> str | None:
    """A compact line for the narrator so Ace addresses + pitches references to this player."""
    if not s.flags.get("onboarded"):
        return None
    bits = [f"the driver goes by {address(s)}"]
    pro = s.flags.get("player_pronouns")
    if pro and pro != "unspecified":
        bits.append(f"pronouns {pro}")
    era = s.flags.get("refs_era")
    if era == "classic":
        bits.append("born before 1990 — pitch references classic/analog, they know 'riz' now")
    elif era == "modern":
        bits.append("younger — current references are fine")
    return "; ".join(bits)
