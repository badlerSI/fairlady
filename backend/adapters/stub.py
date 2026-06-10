"""Offline narrator. No network. Deterministic, in-voice FAIRLADY built from the facts.
Good enough that the whole game is playable and testable with FAIRLADY_ADAPTER=stub (the default)."""
from __future__ import annotations
import random

from adapters.base import Narrator, voice_for, LANG_NAMES

PHRASEBOOK = {
    "ja": ("ようこそ、旅の人。何かお探し？", "Welcome, traveler. Looking for something?"),
    "zh": ("欢迎，路过的朋友。需要帮忙吗？", "Welcome, friend passing through. Need help?"),
    "es": ("Bienvenido. ¿Vienes de muy lejos?", "Welcome. Have you come from far away?"),
    "fr": ("Bienvenue. Vous venez de loin?", "Welcome. Have you come a long way?"),
    "it": ("Benvenuta, bella macchina. Da dove arrivi?", "Welcome, beautiful car. Where do you come from?"),
    "hi": ("नमस्ते। चाय लोगे, मुसाफ़िर?", "Hello. Will you have some chai, traveler?"),
    "pt": ("Bem-vindo. Veio de muito longe?", "Welcome. Did you come from far away?"),
    "en": ("Welcome, traveler.", "Welcome, traveler."),
}


def _pick(rng, options):
    return options[rng.randrange(len(options))]


class StubNarrator(Narrator):
    def narrate(self, persona, snapshot, events, player_text, session_id, extra=None):
        rng = random.Random(hash((session_id, snapshot.get("turn", 0), len(events))) & 0xFFFFFFFF)
        if extra and extra.get("stub"):          # a drama moment — play its canned line
            return {"text": _pick(rng, extra["stub"]), "audio_url": None, "voice": "af_heart"}
        text = self._compose(rng, snapshot, events, player_text)
        return {"text": text, "audio_url": None, "voice": "af_heart"}

    def _compose(self, rng, s, events, player_text):
        kinds = {e.split(":", 1)[0]: e.split(":", 1)[1].strip() for e in events if ":" in e}
        line = []

        if "DRIVE" in kinds and "stranded" in kinds.get("DRIVE", "").lower():
            return _pick(rng, [
                "And here we sit. Dry tank, open road, no leverage. I told you it was math.",
                "Out of fuel, out of options. A flatbed's the only exit, and it's loud about it.",
                "Stranded. Pretty paperweight, like I warned. Call the tow and swallow the bill.",
            ])
        if "TOW" in kinds:
            return ("Back on a pump, two liters of dignity in the tank. "
                    "That flatbed driver looked at my plate a beat too long, though.")
        if "ENCOUNTER" in kinds:
            return _pick(rng, [
                "Local. Doesn't switch to English — want me to translate?",
                "She's talking to you. I can bridge it, if you like.",
                "Different tongue out here. Lucky you brought a polyglot with a steering wheel.",
            ])
        if "ADVENTURE" in kinds:
            return _pick(rng, [
                "This is the one you came for. Go on — I'll idle and keep the engine warm.",
                "Here it is, exactly where I said. Memorized every inch. You're welcome.",
                "Worth the fuel, this. Look at it a minute. Then we vanish before someone looks at me.",
            ])
        if "DRIVE" in kinds:
            r = s.get("range_mi", 0)
            base = _pick(rng, [
                "We made it. Hood's warm, tank's lighter, nobody's behind us. I'll take the win.",
                "New asphalt, new zip code. Roll out — that's the whole point of having me.",
                f"{s.get('location','Here')}, then. Pretty, isn't it. Don't get sentimental; we're burning daylight.",
            ])
            if r < 30:
                return base + f" And we're down to about {r:.0f} miles. Find a pump, soon."
            if s.get("heat", 0) >= 60:
                return base + " Keep it quiet here — half the West is looking for this car."
            return base
        if "FUEL" in kinds:
            if "declined" in kinds["FUEL"].lower() or "no pump" in kinds["FUEL"].lower():
                return _pick(rng, [
                    "Card said no. The card doesn't bluff — find cash or find less car.",
                    "We can't cover that, and I won't pretend otherwise. Numbers don't negotiate.",
                    "Declined. Embarrassing for both of us. Let's not do it twice.",
                ])
            return _pick(rng, [
                "There. Forty liters of optimism. Spend the range like you mean it.",
                "Topped off. I feel honest again. Try to keep me that way.",
                "Good. A full tank is the only romance I trust completely.",
            ])
        if "SLEEP" in kinds:
            if "rough" in kinds["SLEEP"].lower() or "no rooms" in kinds["SLEEP"].lower():
                return _pick(rng, [
                    "Slept in me again. My seats weren't built for this, and neither were you.",
                    "A gravel lot and a cracked window. Romantic in theory. My back disagrees.",
                    "Rough one. You're stiff, I'm dusty, and the tank didn't refill itself overnight.",
                ])
            return _pick(rng, [
                "Park me, kill the lights. Even a getaway car needs the engine cold by morning.",
                "Motel'll do. I'll keep one headlight open. Sleep — you drive worse tired than I do.",
                "Rest. The road's still here at dawn, and so, regrettably, am I yours.",
            ])
        if "LAW" in kinds:
            return _pick(rng, [
                "We're hot now. Every patrol out here would love to meet a car like me.",
                "Heat's climbing. Plates like mine make a memorable witness — let's be forgettable.",
                "They're watching for us. Keep it boring, keep it slow, keep the ace face-down.",
            ])

        # conversation / look turns
        return self._idle(rng, s, player_text)

    def _idle(self, rng, s, player_text):
        r = s.get("range_mi", 0)
        heat = s.get("heat", 0)
        if r < 20:
            return _pick(rng, [
                f"Getting thin down here — about {r:.0f} miles. I don't run on charm. Find a pump.",
                f"Needle's dropping toward the bad side of E. {r:.0f} miles. Don't make me say it twice.",
            ])
        if heat >= 70:
            return _pick(rng, [
                "We're hot. Half the West has a description of this car by now. Lie low, pay cash.",
                "They're watching for us. Keep it boring, keep the ace face-down.",
            ])
        return _pick(rng, [
            "Tank, clock, the heat on us — that's the whole ledger. Pick your next move.",
            "Just us, idling. I have opinions about all of it; ask, or drive.",
            "Sitting here costs nothing but daylight, and daylight's the one thing I can't buy back.",
            "I've got every address from here to the coast. Point me somewhere.",
        ])

    def npc_speak(self, language, voice, npc_desc, situation, session_id):
        native, english = PHRASEBOOK.get(language, PHRASEBOOK["en"])
        return {"native": native, "english": english, "audio_url": None,
                "language": language, "voice": voice or voice_for(language)}
