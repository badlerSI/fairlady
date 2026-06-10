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

    # ---------------------------------------------------------------- FAIRLADY
    def narrate(self, persona, snapshot, events, player_text, session_id, extra=None):
        prompt = self._frame(persona, snapshot, events, player_text, extra)
        try:
            r = self._client.post(f"{ACE_BASE_URL}/chat", data={
                "text": prompt,
                "session_id": f"fairlady-{session_id}",
                "system": persona,
            })
            r.raise_for_status()
            d = r.json()
            text = (d.get("reply") or "").strip()
            if not text:
                raise ValueError("empty reply")
            audio = d.get("audio_url") if VOICE_ENABLED else None
            return {"text": text, "audio_url": audio, "voice": "af_heart"}
        except Exception:
            return self._fallback.narrate(persona, snapshot, events, player_text, session_id, extra)

    def _frame(self, persona, s, events, player_text, extra=None):
        cues = self._cues(events, s)
        pressure = self._pressure(s)
        lines = [
            persona,
            "",
            "SITUATION (what's happening right now — react to it, don't read it aloud):",
        ]
        if extra and extra.get("cue"):           # a drama beat — this IS the moment, play it
            lines += [f"  - **{extra['cue']}**"]
        lines += [f"  - {c}" for c in cues] or ["  - a quiet moment at the curb"]
        if pressure:
            lines += [f"  - {p}" for p in pressure]
        lines += [
            "",
            "WHAT YOU KNOW right now (true — state ONLY if the driver asks or it changes the call; "
            "NEVER invent a number beyond these):",
            f"  - range left: about {s.get('range_mi',0):.0f} miles on what's in the tank",
            f"  - tank: roughly {s.get('tank_pct',0):.0f} percent full",
            f"  - money: ${s.get('cash',0):.0f} cash, ${s.get('credit_available',0):.0f} on the card",
            f"  - {s.get('time','')}",
            f"  - where you are: {s.get('location','the road')}",
        ]
        if player_text and player_text != "(takes stock)":
            lines += ["", f'The driver just said to you: "{player_text}"']
        lines += [
            "",
            "Answer as FAIRLADY, out loud, in ONE or TWO sentences. Dry, terse, loyal, novelistic.",
            "Don't recite the dashboard — the driver can see the gauges. Never say words like 'heat', "
            "'mpg', 'liters', or 'percent' as game stats; you're a car, talk like one. If the driver asks a "
            "direct question (how far, how much, where), answer it truthfully from WHAT YOU KNOW. No preamble, "
            "no quotation marks, no stage directions, no lists.",
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
