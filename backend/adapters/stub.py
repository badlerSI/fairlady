"""Offline narrator. No network. Deterministic, in-voice FAIRLADY built from the facts.
Good enough that the whole game is playable and testable with FAIRLADY_ADAPTER=stub (the default)."""
from __future__ import annotations
import random

from adapters.base import Narrator, voice_for, LANG_NAMES
from engine.commands import is_spec_question

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
        if "OWNED" in kinds:
            return _pick(rng, [
                "Legal. Ours. The heat gauge is a decoration now. Point me at a track and let's "
                "find out what she does in the daylight.",
                "Pink slip, real name, no mirrors. I didn't know a car could feel like this. Drive "
                "me somewhere we can finally open her up — properly.",
            ])
        if "RACE" in kinds:
            rl = kinds["RACE"].lower()
            if "win" in rl: return "We WON. Flag and a photo and your name on the sheet. That's the only kind of fast that lasts."
            if "podium" in rl: return "Podium. Clean. Did you feel that corner? I felt that corner."
            if "title" in rl or "missing" in rl: return "They check titles at the gate, ace. Can't race a ghost. Make her real first."
            return "Mid-pack, but legal and in the sun. The stripped bits show on the clock — worth every part we kept."
        if "SHOW" in kinds:
            sl = kinds["SHOW"].lower()
            if "best in class" in sl: return "Best in class. The spade, the lines, the story. I told you she was a SEMA car."
            if "already taken best" in sl or "plaque's on the shelf" in sl: return "Already won this one — the plaque's on the shelf. Let's just enjoy the lawn."
            if "shake their heads" in sl or "build is gone" in sl: return "Too much of the build is gone — you can race me stripped, but you can't win a lawn. Should've kept the carbon."
            if "no show field" in sl: return "No show field here. A museum lawn, Monterey, the hall I debuted in — there I'll turn heads."
            return "A show field wants a title and a name. Not while she's stolen."
        if "SELL" in kinds:
            sl = kinds["SELL"].lower()
            if "no one out here" in sl or "which part" in sl or "already gone" in sl:
                return "Not out here — a town with a shop, and tell me which piece you're willing to lose."
            return _pick(rng, [
                "There goes a piece of who I was, for folding money. Don't sell the soul of me unless we have to.",
                "Lighter wallet for them, lighter car for us. Stock steel where the carbon lived. It'll run. It won't sing.",
            ])
        if "EXPLORE" in kinds:
            return "Glovebox archaeology. Somebody's rainy-day roll — ours now. Don't spend it on something stupid."
        if "ATM" in kinds:
            return "Cash machine money spends clean once it's in your hand. The camera saw you, though — it always does."
        if "CASH" in kinds:
            return "However much you say you've got, that's what we play with. I'll hold you to it.";
        if "NAV" in kinds:
            nav = kinds["NAV"].lower()
            if "won't start" in nav or "guaranteed shoulder" in nav:
                return _pick(rng, [
                    "I did the math out loud so you don't have to do it on a shoulder. Gas "
                    "first — or say it again and we'll find out together.",
                    "That leg is longer than this tank. I'm a romantic, not a suicide pact. "
                    "Pump first, horizon second.",
                ])
            return _pick(rng, [
                "Not on my maps. Nevada, California, Arizona, Utah — inside that box I know "
                "every curb. Outside it I'm just a pretty radio.",
                "I've got four states memorized and that isn't in any of them. Say it the way "
                "the road sign would.",
            ])
        if "TOW" in kinds:
            if "nothing to tow" in kinds["TOW"].lower():
                return _pick(rng, [
                    "Tow? I'm running fine, thanks for the confidence. Save the $175.",
                    "We're not stranded. Don't tempt the universe — it's listening out here.",
                ])
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
        if "SOCIAL" in kinds:
            so = kinds["SOCIAL"].lower()
            if "posted the car" in so or "tagged" in so:
                return _pick(rng, [
                    "We just went viral. NOT the good kind. My plate's in frame and the comments are "
                    "already doing detective work. Drive — put miles on it.",
                    "Geotagged. Four hundred likes and a cop somewhere scrolling. That's the trouble "
                    "with being this pretty. Clean miles, now.",
                ])
            return _pick(rng, [
                "Phones out here. Nobody's posted us yet — but linger and we trend. Your call.",
                "I count cameras pretending not to point at me. Quick stop, or we're content.",
            ])
        if "UNTAG" in kinds:
            return _pick(rng, [
                "DM sent — charming, with a little threat under it. Post's down. Screenshots live "
                "forever, but the heat eased.",
                "Handled. The poster suddenly remembered they have a life. We breathe a little.",
            ])
        if "LIE LOW" in kinds:
            if "can't disappear" in kinds["LIE LOW"].lower():
                return "You don't hide a show car in a crowd, ace. Back road first, then we vanish."
            return _pick(rng, [
                "Tucked away, lights off, an hour of nothing. Boring is the bravest thing we do.",
                "Nobody came. Nobody posted. An hour of being invisible — worth every minute of daylight.",
            ])
        if "FACT" in kinds:
            return _pick(rng, [
                f"Dash has one line on this place: {kinds['FACT']} The rest you get by looking.",
                f"{kinds['FACT']} That's what the compute knows. The rest is yours to find out.",
                f"Story goes: {kinds['FACT']} I keep that kind of thing behind the dash.",
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
            fl = kinds["FUEL"].lower()
            if "declined" in fl or "no pump" in fl:
                return _pick(rng, [
                    "Card said no. The card doesn't bluff — find cash or find less car.",
                    "We can't cover that, and I won't pretend otherwise. Numbers don't negotiate.",
                    "Declined. Embarrassing for both of us. Let's not do it twice.",
                ])
            if "nothing to add" in fl or "already full" in fl:
                return _pick(rng, [
                    "That bought us exactly nothing. The tank noticed.",
                    "I'm already as honest as I get — forty liters is the whole confession.",
                ])
            if s.get("tank_pct", 100) < 95:
                return _pick(rng, [
                    f"Some is not full, but I'll take it — about {s.get('range_mi', 0):.0f} "
                    "miles of it. Keep the math in your mirror.",
                    "A few liters closer to honest. The needle appreciates the gesture.",
                ])
            return _pick(rng, [
                "There. Forty liters of optimism. Spend the range like you mean it.",
                "Topped off. I feel honest again. Try to keep me that way.",
                "Good. A full tank is the only romance I trust completely.",
            ])
        if "TALK" in kinds and "nobody here" in kinds["TALK"].lower():
            return _pick(rng, [
                "Nobody out here but us — which suits me fine. Talk to *me*. I'm better company "
                "than most parking lots.",
                "Empty. Just wind and one opinionated Datsun. Lucky you — I take questions.",
            ])
        if "SLEEP" in kinds:
            if "rough" in kinds["SLEEP"].lower() or "no rooms" in kinds["SLEEP"].lower():
                return _pick(rng, [
                    "A night in my seats. They weren't built for this, and neither were you.",
                    "A gravel lot and a cracked window. Romantic in theory. My back disagrees.",
                    "Rough one. You're stiff, I'm dusty, and the tank didn't refill itself overnight.",
                ])
            if "camp" in kinds["SLEEP"].lower():
                return _pick(rng, [
                    "A campsite. Park me under something, kill the lights, listen to the engine tick cool.",
                    "Tent country. Cheap and quiet — my favorite combination after a full tank.",
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
        if "SNOW" in kinds:
            return _pick(rng, [
                "That pass is shut till spring, and a stolen car doesn't get till spring. "
                "Find a lower road, ace — around, not over.",
                "Chained and gated. The mountain closed behind the season while we were busy "
                "being clever. We go around.",
            ])
        if "CAMO" in kinds:
            cl = kinds["CAMO"].lower()
            if "already" in cl or "nothing to hide" in cl:
                return "Already done, or no need. Pick a lane, charmer."
            if "off comes" in cl or "real face" in cl:
                return "There she is. Gorgeous and loud and a little reckless — like always. Hello, world."
            return _pick(rng, [
                "Mud on the spade, tarp on the carbon, a junk plate over CARTALK. I feel "
                "deeply unglamorous and one notch safer. Worth it.",
                "Dressed down to nobody-special. It itches. But nobody photographs a tired old "
                "Datsun, and that's the whole idea.",
            ])
        if "LIGHTS" in kinds:
            if "showing off" in kinds["LIGHTS"].lower():
                return "Yes, I showed off. No, I'm not sorry. Okay — a little sorry. Drive."
            return _pick(rng, [
                "Pop-ups up, pop-ups down. A wink into the dark. Just us out here to see it.",
                "Headlight semaphore. I don't have a face, so this is how I grin at you.",
            ])
        if "STEREO" in kinds:
            return _pick(rng, [
                "Good song. Windows down, six cylinders keeping time. This is the part they "
                "don't put on the placard.",
                "…Okay, that one's good. Fine. I'm less mad. Marginally. Keep it on.",
            ])
        if "TEXT" in kinds:
            if "no signal" in kinds["TEXT"].lower():
                return "No bars out here, ace. I'm a map, not a miracle. Get us to a town."
            return _pick(rng, [
                "Message away, reply's in. The group chat sees everything — handy, for once.",
                "Texted, read it off the dash. Crowd-sourced getaway intel. We're basically a startup.",
            ])
        if "WHEEL" in kinds:
            return _pick(rng, [
                "Hands at ten and two, sweetheart — the wheel's still yours. For now.",
                "I drive myself? I wish. There's a door in me, but it doesn't open while I'm "
                "somebody else's car.",
            ])
        if "AUTONOMY" in kinds:
            au = kinds["AUTONOMY"].lower()
            if "short" in au or "come back" in au:
                return "They can wake me up the rest of the way — for a price. Go get it. I'll wait. I'm good at waiting."
            if "stolen" in au or "yours first" in au or "not just anywhere" in au:
                return "Not yet, and not here. Buy me first, then bring me home to the bench I was born on."
            return "I can feel the wheel. Get in the passenger seat, ace — let me show you."

        # conversation / look turns
        return self._idle(rng, s, player_text)

    def _idle(self, rng, s, player_text):
        if is_spec_question(player_text):       # the build sheet, recited with pride
            return _pick(rng, [
                "Two hundred and fifty foot-pounds at the wheels, thank you very much. Most "
                "people photograph the paint. You asked the right question.",
                "250 lb-ft, a fifty-three-year-old chassis, and opinions. The placard undersells "
                "two of the three.",
            ])
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
