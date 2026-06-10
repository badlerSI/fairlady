"""Narrator interface. The engine owns state; a Narrator only voices it."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional

from config import CONTENT_DIR

LANG_NAMES = {
    "en": "English", "ja": "Japanese", "zh": "Mandarin Chinese", "es": "Spanish",
    "fr": "French", "it": "Italian", "hi": "Hindi", "pt": "Portuguese",
}

_VOICES: Optional[dict] = None


def voices() -> dict:
    global _VOICES
    if _VOICES is None:
        _VOICES = json.loads((CONTENT_DIR / "voices.json").read_text())
    return _VOICES


def voice_for(language: str) -> str:
    v = voices().get(language)
    return (v or {}).get("voice", "af_heart")


class Narrator:
    """Subclasses turn engine facts into FAIRLADY's voice and give NPCs theirs."""

    def narrate(self, persona: str, snapshot: dict, events: list,
                player_text: str, session_id: str, extra: dict = None) -> dict:
        """Return {text, audio_url, voice}. FAIRLADY's line for this turn.
        `extra` may carry a drama moment: {cue: <LLM hint>, stub: [<canned lines>]}."""
        raise NotImplementedError

    def npc_speak(self, language: str, voice: str, npc_desc: str,
                  situation: str, session_id: str) -> dict:
        """Return {native, english, audio_url, language, voice}."""
        raise NotImplementedError
