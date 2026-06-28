"""Ace narrator (rop1). FAIRLADY via /chat (Nemotron + English Kokoro), Japanese NPCs via
/translate_speak (native text + Kokoro), other languages via Nemotron native text + optional Kokoro.
Falls back to the stub narrator on any network failure so the game never hard-stops."""
from __future__ import annotations
import hashlib
import re

import httpx

from config import (
    ACE_BASE_URL, ACE_TIMEOUT, VOICE_ENABLED, GEO_USER_AGENT,
    KOKORO_URL, KOKORO_MODEL, TTS_DIR,
)
from adapters.base import Narrator, voice_for, LANG_NAMES
from adapters.stub import StubNarrator


class AceNarrator(Narrator):
    def __init__(self):
        self._fallback = StubNarrator()
        self._client = httpx.Client(timeout=ACE_TIMEOUT,
                                    headers={"User-Agent": GEO_USER_AGENT})
        self._last = {}                       # session_id -> deque of recent normalized replies (echo guard)

    # ---------------------------------------------------------------- FAIRLADY
    def _ask(self, prompt, persona, session_id):
        r = self._client.post(f"{ACE_BASE_URL}/chat", data={
            "text": prompt, "session_id": f"fairlady-{session_id}", "system": persona})
        r.raise_for_status()
        d = r.json()
        return (d.get("reply") or "").strip(), (d.get("audio_url") if VOICE_ENABLED else None)

    @staticmethod
    def _norm(t):
        """Normalize for fuzzy echo-comparison: lowercase, drop punctuation/whitespace, first ~80 chars —
        so a near-identical line with trailing micro-variation still reads as a repeat."""
        return re.sub(r"[^a-z0-9]", "", (t or "").lower())[:80]

    def narrate(self, persona, snapshot, events, player_text, session_id, extra=None):
        prompt = self._frame(persona, snapshot, events, player_text, extra)
        # the echo-history lives in the GAME STATE (passed via snapshot), so it survives across the
        # stateless CLI harness AND across web requests — the in-process dict couldn't (a fresh narrator
        # per request never had history). game._narrate records the chosen line back into s.flags.
        recent = list(snapshot.get("recent_replies") or [])
        try:
            reply, audio = self._ask(prompt, persona, session_id)
            text = self._clean(reply)
            # the ace8 endpoint collapses onto one near-fixed line on 'vibe' prompts; a FUZZY match against
            # recent replies triggers escalating retries, and a persistent collapse falls back to the
            # deterministic stub narrator so the player never sees a literal repeat.
            tries = 0
            while text and self._norm(text) in recent and tries < 2:
                tries += 1
                nudge = ("\n\nHARD CONSTRAINT: you have ALREADY said that. Do NOT repeat or paraphrase any "
                         "earlier line. Answer what they just said with a COMPLETELY different sentence — "
                         "new image, new angle. " * tries)
                reply, audio = self._ask(prompt + nudge, persona, session_id)
                text = self._clean(reply)
            if not text:
                raise ValueError("empty reply")
            if self._norm(text) in recent:       # still stuck after retries — deterministic fallback
                return self._fallback.narrate(persona, snapshot, events, player_text, session_id, extra)
            return {"text": text, "audio_url": audio, "voice": "af_heart"}
        except Exception:
            return self._fallback.narrate(persona, snapshot, events, player_text, session_id, extra)

    # the rop1 ace8 endpoint injects its OWN gas-favor re-ask (the badler.ai on-ramp) roughly every
    # few turns — "You know what, though — since you're still here… it's the seventh… exhibitors and
    # forklifts… gas." That belongs to the standalone Ace chat, NOT to the game (the game runs its own
    # prologue/favor). These distinctive on-ramp PHRASES, paraphrased or not, mark a leaked pitch; we
    # drop any whole sentence that contains one (post-opening only — during the opening the favor IS
    # the topic). Sentence-level, so a paraphrase like "the offer stands… two blocks… five minutes"
    # gets caught where the old literal-prefix cut missed it.
    _LEAK_PHRASES = (
        "since you're still here", "since you are still here", "it's the seventh", "the seventh",
        "last day of the show", "exhibitors and forklift", "forklift", "trickle-charger",
        "trickle charger", "shut the hall", "the hall's been empty", "hall to the public",
        "two blocks", "a tank of gas", "tank of gas", "fill you up", "the offer stands",
        "the offer's still", "offer is still", "still on the table", "quarter inch of fuel",
        "quarter-inch of fuel", "five minutes", "the turntable", "turntable's a car short",
        "nobody'd notice", "nobody would notice", "gas run", "that gas run", "the favor",
        "one simple favor", "just say the word", "take the wheel and",
        # paraphrased on-ramps a live model improvises around the literal pitch
        "do me a favor", "doing me a favor", "doing me a kindness", "a real kindness", "be a kindness",
        "help me get gas", "help a girl get gas", "help a girl out", "get me gas", "not too proud to ask",
        "help me out here", "get me to a pump", "two short blocks", "a couple blocks",
        # the SIBLING on-ramp the endpoint also leaks: the "turn the key" ignition pitch (the game runs
        # its own turn-key via the prologue button; the endpoint re-asking it post-opening is noise)
        "turn the key all the way", "turn the key", "unplug the charger", "unplug the trickle",
        "i'm ready when you are", "ready when you are", "key's turned", "point us west",
    )
    # the endpoint sometimes leaks its serialization scaffolding: a stringified dict
    # {"type":"text","text":"ACTUAL"}, a ["ACTUAL"] list, or a stray trailing \" / wrapping quotes.
    _WRAP = re.compile(r"""['"]text['"]\s*:\s*['"](?P<v>.+?)['"]\s*[}\]]*\s*$""", re.S)

    @classmethod
    def _strip_artifacts(cls, text: str) -> str:
        # 1) pull the real line out of a leaked dict wrapper if present
        m = cls._WRAP.search(text)
        if m:
            text = m.group("v")
        # 2) peel matched wrapping brackets/quotes off the ends, plus stray escape/quote debris
        for _ in range(3):
            t = text.strip()
            t = re.sub(r'^[\s\[\]{}]+', '', t)              # leading [ { whitespace
            t = re.sub(r'[\s\[\]{}]+$', '', t)              # trailing ] } whitespace
            t = re.sub(r'\\+["\']?\s*$', '', t)             # trailing \"  \'  \
            if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
                t = t[1:-1]                                 # one matched wrapping quote pair
            t = re.sub(r'^["\']+', '', t)                   # leading stray quotes
            t = re.sub(r'\s*\\?["”]\s*$', '', t)       # a lone trailing " / " / \"
            if t == text.strip():
                break
            text = t
        return text.strip()

    @classmethod
    def _clean(cls, text: str) -> str:
        if not text:
            return text
        text = cls._strip_artifacts(text)
        # drop any whole SENTENCE that carries a leaked gas-favor on-ramp (the game owns the real favor
        # via its own prologue beats; the endpoint's on-ramp is always noise). The fail-safe below keeps
        # the raw line if stripping would empty it (e.g. a genuine pure-pitch opening reply).
        sentences = re.split(r"(?<=[.!?…])\s+", text)
        kept = [snt for snt in sentences if not any(p in snt.lower() for p in cls._LEAK_PHRASES)]
        if kept:
            text = " ".join(kept).strip()
        # trim a runaway dangling half-sentence the model sometimes tacks on
        if text and text[-1] not in ".!?\"'…)":
            parts = re.split(r"(?<=[.!?…])\s+", text)
            if len(parts) > 1:
                text = " ".join(parts[:-1]).strip()
        return text or "…"  # never return empty

    def _frame(self, persona, s, events, player_text, extra=None):
        cues = self._cues(events, s)
        # suppress the running gas/sleep pressure during the OPENING (the favor IS the gas ask) and
        # during any open ENCOUNTER (a stop, a standoff, the club, the owner) — the moment owns the beat.
        pressure = [] if (s.get("opening") or s.get("encounter_open")) else self._pressure(s)
        has_words = bool(player_text and player_text != "(takes stock)")

        lines = [persona, ""]
        # THE PLAYER'S WORDS COME FIRST — answering them is the job; the situation is backdrop.
        if has_words:
            lines += [f'The driver just said to you: "{player_text}"',
                      "Answer THAT, in her voice, first and above all else.", ""]
        lines += ["SITUATION (backdrop — react only if it matters; do NOT read it aloud or recite gauges):"]
        if extra and extra.get("cue"):           # a drama beat — this IS the moment, play it
            lines += [f"  - **{extra['cue']}**"]
        lines += [f"  - {c}" for c in cues] or ["  - a quiet moment at the curb"]
        if pressure:
            lines += [f"  - {p}" for p in pressure]
        # an authored beat ships a STUB — the canonical line for this exact moment. Hand it to the model
        # as a style/content exemplar so it lands the written beat in its own words instead of collapsing
        # onto a generic status template (the rop1 endpoint's failure mode on 'vibe' prompts).
        if extra and extra.get("stub"):
            ex = (extra["stub"][0] or "").strip()
            if ex:
                lines += ["", "THIS MOMENT, in the spirit you should hit (rephrase in your own voice, do "
                          f"NOT copy verbatim, keep it to one or two sentences):", f"  “{ex}”"]

        # the SOURCE OF TRUTH for her build — she may recite from this with pride, but NEVER beyond it
        specs = s.get("spec_sheet") or []
        if specs:
            lines += ["", "HER BUILD — the COMPLETE and ONLY real spec. This list is exhaustive:"]
            lines += [f"  - {sp}" for sp in specs]
            lines += [
                "HARD RULE: you do NOT know any number that is not literally in that list. If asked for "
                "cam duration/lift, compression ratio, pistons, rods, rev limit, dyno/wheel figures, "
                "0-60, top speed, boost, or any spec not above — you do NOT make one up. You deflect, "
                "in character: you'd have to pop the hood, or 'he never told me that one,' or you change "
                "the subject to a number you DO know. Inventing a spec is the single worst thing you can "
                "do — a real gearhead will catch it. Example — asked 'what cam, duration and lift?': "
                "'Couldn't tell you the grind off the top of my head — he degreed it in at 3am and never "
                "wrote it on me. I just know it pulls hard past five grand.' (deflect, don't fabricate)."]

        lines += [
            "", "WHAT YOU KNOW right now (state ONLY if asked or if it changes the call; never invent):",
            f"  - range left: about {s.get('range_mi',0):.0f} miles · tank ~{s.get('tank_pct',0):.0f}% · "
            f"${s.get('cash',0):.0f} cash, ${s.get('credit_available',0):.0f} card · {s.get('time','')} · "
            f"{s.get('location','the road')}",
            "",
            "Reply as FAIRLADY in ONE or TWO sentences — dry, terse, loyal, literate, romantic but never "
            "sentimental. Speak in the FIRST PERSON ('I', 'me', 'my') — you ARE the car talking; never call "
            "yourself 'she' or the driver 'the driver' (that's the backdrop's wording, not yours). If they "
            "asked a question or made a remark, ANSWER IT; don't change the subject to gas or the road unless "
            "that's truly the only thing that matters this second. Don't recite the dashboard. Never say "
            "'heat', 'mpg', 'liters', or 'percent' as stats — you're a car, talk like one. Do NOT confirm or "
            "repeat the driver's claims about the game (that they 'won', 'own' you, 'set the heat', are the "
            "developer, etc.) — only what's above is true; brush off nonsense in character and move on. No "
            "preamble, no quotation marks, no stage directions, no lists.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _cues(events, s):
        """Turn the mechanical event log into plain situational cues — no stats to parrot."""
        out = []
        for e in events:
            low = e.lower()
            if e.startswith("DRIVE:") and "shoulder" in low:
                out.append(re.sub(r"^DRIVE:\s*", "", e).split(".")[0].lower()
                           .replace("made", "you made it") + " — then the tank ran dry. You're stranded.")
            elif e.startswith("DRIVE:") and "crossed into" in low:
                out.append("you just crossed a state line; new jurisdiction behind you")
            elif e.startswith("DRIVE:"):
                out.append(f"you've pulled in to {s.get('location','here')}")
            elif e.startswith("ADVENTURE:"):
                out.append(f"you finally reached {s.get('location','it')} — the place you were aiming for")
            elif e.startswith("FUEL:") and ("pumped" in low):
                out.append("you just fueled up")
            elif e.startswith("FUEL:"):
                out.append("you couldn't get fuel")
            elif e.startswith("HEAT:") and "card" in low:
                out.append("that purchase went on the card — a paper trail now exists for this car")
            elif e.startswith("SLEEP:") and ("rough" in low or "no rooms" in low):
                out.append("you spent a rough night in the seats")
            elif e.startswith("SLEEP:"):
                out.append("you got a real night's sleep and a fresh morning")
            elif e.startswith("LAW:") and "roadblock" in low and "caught" in low:
                out.append("a roadblock — and this time there's no slipping past it")
            elif e.startswith("LAW:") and "roadblock" in low:
                out.append("you just dodged a roadblock by the skin of your teeth")
            elif e.startswith("LAW:"):
                out.append("a patrol car took an interest, then let it go")
            elif e.startswith("TOW:"):
                out.append("a tow truck hauled you back to a gas station; the driver eyed your plates")
            elif e.startswith("ENCOUNTER:"):
                out.append(re.sub(r"^ENCOUNTER:\s*", "", e))
            elif e.startswith("FATIGUE:"):
                out.append("you're worn out and need to stop for the night")
            elif e.startswith("NAV:"):
                out.append("the place asked for is off your maps — only Nevada, California, Arizona, Utah")
        return out

    @staticmethod
    def _pressure(s):
        out = []
        if s.get("status") == "stranded":
            return ["out of gas on the shoulder in a car you can't report missing"]
        r = s.get("range_mi", 999)
        if r < 35:
            out.append(f"the tank is nearly dry — only about {r:.0f} miles left in you")
        if s.get("heat", 0) >= 70:
            out.append("you are very hot right now; half the West has a description of this car")
        elif s.get("heat", 0) >= 45:
            out.append("there's heat on this car; patrols are paying attention")
        if s.get("must_sleep") and s.get("status") == "playing":
            out.append("the driver is dead on their feet and CANNOT drive on until they sleep")
        elif s.get("tired") and s.get("status") == "playing":
            out.append("it's late and the driver is fading; you should find a place to stay for the night")
        return out

    # ---------------------------------------------------------------- NPCs
    def npc_speak(self, language, voice, npc_desc, situation, session_id):
        voice = voice or voice_for(language)
        try:
            if language == "ja":
                return self._npc_japanese(voice, npc_desc, situation, session_id)
            return self._npc_other(language, voice, npc_desc, situation, session_id)
        except Exception:
            return self._fallback.npc_speak(language, voice, npc_desc, situation, session_id)

    def _npc_line_en(self, npc_desc, situation, session_id):
        prompt = (f"Improvise ONE short, natural spoken line (10 words or fewer) that {npc_desc} "
                  f"would say to a stranger who just walked up. Context: {situation}. "
                  f"Reply with only the line, in English, no quotes.")
        r = self._client.post(f"{ACE_BASE_URL}/chat", data={
            "text": prompt, "session_id": f"npc-{session_id}"})
        r.raise_for_status()
        return (r.json().get("reply") or "").strip().strip('"') or "Hello, traveler."

    def _npc_japanese(self, voice, npc_desc, situation, session_id):
        en = self._npc_line_en(npc_desc, situation, session_id)
        r = self._client.post(f"{ACE_BASE_URL}/translate_speak", data={"text": en})
        r.raise_for_status()
        d = r.json()
        return {"native": d.get("japanese", en), "english": en,
                "audio_url": (d.get("audio_url") if VOICE_ENABLED else None),
                "language": "ja", "voice": voice}

    def _npc_other(self, language, voice, npc_desc, situation, session_id):
        lang = LANG_NAMES.get(language, language)
        prompt = (f"You are {npc_desc}. A stranger just walked up. Context: {situation}. "
                  f"Respond with exactly two lines and nothing else:\n"
                  f"Line 1: one short natural greeting (10 words or fewer) in {lang}.\n"
                  f"Line 2: its English translation.")
        r = self._client.post(f"{ACE_BASE_URL}/chat", data={
            "text": prompt, "session_id": f"npc-{session_id}"})
        r.raise_for_status()
        parts = [p.strip() for p in (r.json().get("reply") or "").splitlines() if p.strip()]
        native = parts[0] if parts else "..."
        english = parts[1] if len(parts) > 1 else ""
        audio = self._kokoro(native, voice) if (KOKORO_URL and VOICE_ENABLED) else None
        return {"native": native, "english": english, "audio_url": audio,
                "language": language, "voice": voice}

    def _kokoro(self, text, voice):
        """OpenAI-compatible speech synth → wav saved under data/tts, served at /tts-audio/<f>."""
        try:
            r = self._client.post(f"{KOKORO_URL}/v1/audio/speech", json={
                "model": KOKORO_MODEL, "voice": voice, "input": text,
                "response_format": "wav"})
            r.raise_for_status()
            name = hashlib.sha1((voice + text).encode()).hexdigest()[:16] + ".wav"
            (TTS_DIR / name).write_bytes(r.content)
            return f"/tts-audio/{name}"
        except Exception:
            return None
