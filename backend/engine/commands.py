"""Deterministic intent parser. The LLM never decides what happens — this does.
Maps free-ish player text to (verb, args). Anything unrecognized becomes conversation."""
from __future__ import annotations
import re
from typing import Tuple

_NUM = r"(\d+(?:\.\d+)?)"


def parse(raw: str) -> Tuple[str, dict]:
    t = (raw or "").strip()
    low = t.lower()
    if not low:
        return ("look", {})

    if low in ("help", "?", "commands", "h"):
        return ("help", {})
    if low in ("new", "new game", "restart", "reset"):
        return ("new", {})
    if low in ("save",):
        return ("save", {})
    if low.startswith("load"):
        return ("load", {"name": low[4:].strip() or "autosave"})

    if low in ("look", "l", "status", "state", "look around", "hud"):
        return ("look", {})

    # the two-step commit: turn the key all the way (the opening button)
    if (low in ("turn the key all the way", "turn the key", "turnkey", "turn her all the way",
                "turn the key all the way over", "turn it all the way", "start her", "start her up",
                "fire her up", "start the engine", "start the car", "turn her over", "turn the key over",
                "crank her", "crank it", "key it", "send it down the block")
            or ("turn" in low and "key" in low)
            or ("all the way" in low and any(w in low for w in ("key", "turn", "crank")))):
        return ("turnkey", {})

    # the heat report — the credit-karma dashboard for your notoriety
    if low in ("heat", "score", "heat report", "report", "record", "my record", "how hot",
               "how hot are we", "how hot am i", "notoriety", "rap sheet", "the heat",
               "heat score", "credit", "where do we stand with the law"):
        return ("heatreport", {})
    # how does she feel about you — the relationship report (her words, not a stat bar)
    if (low in ("how does she feel", "how does she feel about me", "does she like me",
                "does she love me", "her mood", "how is she feeling", "how's she feeling",
                "hows she feeling", "how are we", "how do we stand", "are we okay", "are we good",
                "is she mad", "is she mad at me", "her feelings", "bond", "bond report", "how she feels",
                "what does she think of me", "how's her mood", "feelings", "how's she feel")
            or ("she" in low and any(w in low for w in ("feel", "mad", "like me", "love me")))):
        return ("bondreport", {})

    # lie low (active cool-down) and untag (post-tag damage control)
    if low in ("lie low", "lay low", "lie low here", "lay low here", "lie low a while", "hide",
               "hide out", "lay up", "go quiet", "keep a low profile", "duck out of sight",
               "wait it out", "cool off", "lay low for a bit", "lie low for a bit"):
        return ("lielow", {})
    if low in ("untag", "untag the post", "take it down", "damage control", "delete the post",
               "dm the poster", "get it taken down", "clean up the post"):
        return ("untag", {})

    # the timeline / branch selector (git-like) — list your checkpoints
    if low in ("branches", "branch", "timeline", "checkpoints", "saves", "history", "the timeline",
               "list branches", "show branches", "where can i rewind to"):
        return ("branches", {})
    # jump to a specific branch: "branch 3", "rewind to mesquite", "fold back to the standoff"
    m = re.match(r"^(?:branch|rewind to|fold back to|go back to|jump to|load branch)\s+(.+)$", low)
    if m:
        tgt = m.group(1).strip(" .")
        return ("rewind", {"target": int(tgt) if tgt.isdigit() else tgt})

    # rewind to the last checkpoint (the Edge-of-Tomorrow escape — must precede the drive check,
    # since "go back" would otherwise parse as a drive)
    if low in ("rewind", "go back", "rewind it", "take it back", "loop", "loop it",
               "try again", "try that again", "run it back"):
        return ("rewind", {})

    # "where can we get to on one tank?" — the range question, answered with real math.
    # "tank" overrides the service words ("one tank of gas" is range, "where can we get gas" is map).
    service_q = any(w in low for w in ("gas", "fuel", "pump", "motel", "lodg", "stay", "sleep"))
    if (("tank" in low and any(w in low for w in ("where", "far", "get to", "reach", "make it", "go on")))
            or (not service_q
                and (low.startswith(("how far", "what can we reach", "where can we get",
                                     "where can we go", "where can you take me"))
                     or low in ("range", "reachable")))):
        return ("range", {"full": "full" in low or "one tank" in low})

    # ask about her origins — Life of a Show Car (must precede the generic "where..." map check)
    if any(p in low for p in ("born", "where are you from", "where you from", "where're you from")):
        return ("origin", {"which": "born"})
    if any(p in low for p in ("grew up", "grow up", "came of age", "come of age", "raised",
                              "where were you built", "where you built", "who built you", "who made you")):
        return ("origin", {"which": "grew"})
    if any(p in low for p in ("previous owner", "last owner", "old owner", "who owned you",
                              "who had you", "your owner", "your past", "before you", "owned you before")):
        return ("origin", {"which": "owner"})
    # where were you PAINTED — the thread that pulls the owner's whole secret loose (→ Fresno)
    if (any(p in low for p in ("where were you painted", "where you painted", "who painted you",
                               "where'd you get painted", "where did you get painted", "your paint job",
                               "the paint job", "where was the paint", "where was your paint",
                               "where'd the paint", "who laid the paint", "where'd you get sprayed",
                               "where were you wrapped", "who wrapped you", "your ppf", "the wrap",
                               "where was the spade", "who painted the spade"))
            or ("paint" in low and any(q in low for q in ("where", "who", "your", "the spade")))):
        return ("origin", {"which": "painted"})
    # ask about the REGISTRATION — whose name is on her papers (→ the Carson City address, Bob mode)
    if (any(p in low for p in ("registration", "registered to", "registered address", "whose name is on",
                               "who's it registered", "who is it registered", "name on the reg",
                               "name on your papers", "the address on", "address on the reg",
                               "whose car are you", "who owns the title", "the title says"))
            or ("papers" in low and any(q in low for q in ("name", "whose", "who", "address")))):
        return ("origin", {"which": "registration"})

    # ---- BOB MODE: park Ace at the registered address, take the loaner, call her, buy Bob ----
    if (low in ("park ace", "park her", "stash ace", "stash her", "leave her here", "leave ace here",
                "take bob", "swap to bob", "borrow bob", "park ace and take bob", "get in bob",
                "drive bob", "park ace take bob")
            or ("take bob" in low)
            # "park/stash" only as a LEADING verb — so "now that we're PARKED, that ACE of spades…" (a
            # past-tense remark mentioning the ace of spades) doesn't fire the BOB handler
            or (re.match(r"^(?:park|stash)\b", low) and ("ace" in low or "her" in low) and "spade" not in low)
            or (("swap" in low or "borrow" in low or "get in" in low) and "bob" in low)):
        return ("parkbob", {})
    if (low in ("call ace", "call her", "phone ace", "phone her", "ring ace", "ring her",
                "facetime ace", "check in with ace", "call ace and check in")
            or (low.startswith(("call ", "phone ", "ring ", "tell ace ", "say to ace ")) and
                any(w in low for w in ("ace", "her")))):
        rest = re.sub(r"^(?:call|phone|ring|tell|say to)\s+(?:ace|her)\b[:,]?\s*", "", low).strip()
        return ("callace", {"text": rest})
    if low in ("buy bob", "purchase bob", "buy bob from him", "buy the loaner", "pay for bob",
               "buy bob for 7000", "buy bob for $7000", "buy bob for seven thousand"):
        return ("buybob", {})
    # ask Alma who she really is (reveals her backstory once she's aboard)
    if ("alma" in low and any(p in low for p in ("your story", "who are you", "who you are",
            "about yourself", "your past", "your deal", "real name", "who you really", "where you from",
            "what's your", "whats your", "tell me about you", "what is your story"))):
        return ("almabackstory", {})
    if (low in ("make bob talk", "give bob a voice", "upgrade bob", "bob talk", "make bob speak",
                "upgrade bob to talk", "give bob a voice box") or ("bob" in low and "talk" in low and
                any(w in low for w in ("make", "give", "upgrade", "want")))):
        return ("bobtalk", {})

    # take her home (her home is the Oakland garage; or name a place in NV/CA/AZ/UT)
    if low.startswith(("home is ", "set home ", "my home is ", "home in ", "home's ")):
        dest = re.sub(r"^(?:home is|set home|my home is|home in|home's)\s+", "", low).strip(" .")
        return ("home", {"dest": dest})
    if any(p in low for p in ("driving you home", "driving her home", "taking you home", "taking her home",
                              "drive you home", "drive her home", "drive me home", "drive us home",
                              "take you home", "take her home",
                              "take me home", "let's go home", "lets go home", "head home", "get you home")):
        m = re.search(r"home (?:to|in) (.+)$", low)
        return ("home", {"dest": m.group(1).strip(" .")} if m else {})
    if low in ("home", "drive home", "go home", "homeward", "take us home"):
        return ("home", {})

    if low.startswith(("map", "nearby", "where")):
        svc = None
        if "gas" in low or "fuel" in low or "pump" in low:
            svc = "gas"
        elif "sleep" in low or "motel" in low or "lodg" in low or "stay" in low:
            svc = "lodging"
        return ("map", {"service": svc})

    if low in ("tow", "call a tow", "call tow", "get towed", "tow truck"):
        return ("tow", {})

    # the gun (Desperado): go for an armed clerk's pistol, or pull your own once you have it
    if low in ("disarm", "disarm him", "grab the gun", "go for the gun", "grab for the gun",
               "go for it", "take the gun", "take his gun", "lunge", "lunge for it",
               "make a grab", "grab it", "jump him", "wrestle the gun"):
        return ("disarm", {})
    if low in ("draw", "pull the gun", "pull my gun", "pull the piece", "point the gun",
               "draw on him", "draw the gun", "pull iron", "pull the trigger", "show the gun"):
        return ("draw", {})

    # go clubbing (the discoverable way to MEET Alma the first night in Vegas)
    if (low in ("club", "clubbing", "go clubbing", "go to a club", "hit a club", "hit the clubs",
                "find a club", "go out", "go dancing", "go to the club", "hit the strip", "go out tonight",
                "go to a bar", "hit a nightclub", "nightclub", "go party", "let's go out", "lets go out",
                "paint the town", "go to a casino bar", "hit the town")
            or ("go" in low and any(w in low for w in ("club", "dancing", "out tonight", "party")))):
        return ("club", {})

    # ---- Alma (the dream woman / companion) — book a room, cool the heat, or marry her in Vegas ----
    if (low in ("alma", "where's alma", "wheres alma", "find alma", "who is alma", "who's alma",
                "about alma", "alma status", "is alma here")
            or low.startswith(("where is alma", "tell me about alma"))):
        # marriage intent on Alma routes to the marry handler; otherwise it's a status/lookup
        if any(w in low for w in ("marry", "elope", "wed", "propose", "chapel", "wife")):
            return ("almamarry", {})
        return ("almastatus", {})
    if ("alma" in low and any(w in low for w in ("marry", "married", "elope", "wed", "chapel",
                                                 "propose", "vegas wedding", "make her my wife"))):
        return ("almamarry", {})
    if (("alma" in low and any(w in low for w in ("book", "room", "hotel", "motel", "get us a",
                                                  "find us a", "a place to stay")))
            or low in ("alma book a room", "have alma book a room", "ask alma for a room",
                       "alma get us a room", "alma a room")):
        return ("almaroom", {})
    if (("alma" in low and any(w in low for w in ("cool", "heat", "handle it", "make a call", "favor",
                                                  "fix it", "clean it", "lower the heat", "calm")))
            or low in ("ask alma to cool it", "have alma cool the heat", "alma cool the heat",
                       "ask alma to handle it", "alma handle the heat")):
        return ("almacool", {})

    # the RIZZBREAKER — the charisma Limit Break (context-aware; must precede gambling/drive parses)
    if (low in ("rizzbreaker", "rizz breaker", "rizz break", "rizzbreak", "limit break", "limitbreak",
                "break the rizz", "unleash the rizz", "unleash", "all the rizz", "full rizz",
                "rizzler", "use the rizzbreaker", "pull a rizzbreaker", "do a rizzbreaker", "go all rizz",
                "maximum rizz", "max rizz", "the rizzbreaker", "spend the rizz", "limit-break")
            or ("rizz" in low and any(w in low for w in ("break", "unleash", "limit", "max", "full",
                                                         "spend", "all the")))
            or ("limit break" in low)):
        return ("rizzbreaker", {})

    # ---- the hatch: inventory, buying gear, jerry cans (reserve fuel) ----
    if low in ("inventory", "hatch", "the hatch", "the back", "what's in the back", "whats in the back",
               "what am i carrying", "my stuff", "my gear", "open the hatch", "check the hatch",
               "look in the back", "the trunk", "what's in the hatch", "show inventory"):
        return ("inventory", {})
    if (low in ("fill the jerry cans", "fill the cans", "fill jerrycans", "fill the jerrycans",
                "fill up the cans", "top off the cans", "fill the gas cans", "fill cans")
            or ("fill" in low and any(w in low for w in ("jerry", "the cans", "gas can")))):
        return ("filljerry", {})
    if (low in ("pour the jerry can", "pour the cans", "pour the jerry cans", "use the reserve",
                "use the spare fuel", "use the reserve fuel", "empty the cans into the tank",
                "top off from the cans", "add the reserve", "pour the gas can", "pour in the reserve",
                "use the jerry can", "use the gas can", "dump the cans in")
            or ("pour" in low and any(w in low for w in ("jerry", "can", "reserve")))
            or ("reserve" in low and any(w in low for w in ("use", "pour", "add", "tank")))):
        return ("pourjerry", {})
    _GEAR = ("jerry", "gas can", "fuel can", "water", "cooler", "ice chest", "tent", "sleeping bag",
             "tool", "first aid", "first-aid", "medkit", "spare tire", "spare", "snack", "chain",
             "chains", "snow chain")
    if (low.startswith(("buy", "get", "grab", "pick up", "purchase", "i need", "i want", "stock up"))
            and any(g in low for g in _GEAR)):
        return ("invbuy", {"text": raw})
    if (low.startswith(("drop", "leave", "ditch", "toss", "dump")) and any(g in low for g in _GEAR)):
        return ("invdrop", {"text": raw})
    # the body shop (a town/city) — pull the dents, fix the scrapes, make her pretty after a wreck
    if (low in ("body shop", "bodywork", "body work", "fix the dents", "fix the dent", "pull the dents",
                "fix the scrapes", "fix the body", "panel beat", "fix her body", "take her to a body shop",
                "fix the damage", "repair the body", "fix the bodywork", "fix the panel")
            or ("body" in low and any(w in low for w in ("shop", "work", "panel")))
            or (("dent" in low or "scrape" in low) and any(w in low for w in ("fix", "pull", "repair", "fix the")))):
        return ("bodywork", {})
    # field repair (needs the tool roll) — knock the deer-limp out without a town
    if (low in ("repair", "repair her", "fix her", "fix the car", "repair the car", "fix the limp",
                "use the tools", "use the tool roll", "patch her up", "field repair", "fix her up",
                "wrench on her", "fix the fender")
            or ("fix" in low and any(w in low for w in ("her", "the car", "limp", "fender")))
            or ("repair" in low and any(w in low for w in ("her", "the car")))):
        return ("repair", {})

    # ---- the garage economy: claims, ATM, glovebox, parts, racing, shows, buying her ----
    # buy the car (the good ending) — must precede the generic 'gas'/drive checks
    if (low in ("buy", "buy her", "buy it", "buy the car", "i'll buy her", "ill buy her",
                "come to terms", "let's come to terms", "lets come to terms")
            or any(p in low for p in ("buy the car", "buy her", "buy you", "buy it", "i'll buy",
                                      "ill buy", "let me buy", "purchase her", "purchase the car",
                                      "make you an offer", "name your price", "i'll take her",
                                      "ill take her", "pay you for her", "buy you off him",
                                      "buy her off"))):
        return ("buy", {"amount": _money(low) or _bare_number(low)})   # '$80k' OR a bare '80000'
    if low == "offer" or low.startswith("offer ") or "i'll offer" in low or "ill offer" in low:
        return ("buy", {"amount": _money(low) or _bare_number(low)})
    # the seven-sevens hack — spelled out, or the bare magic number
    if any(p in low for p in ("seven sevens", "77777.77", "77,777.77", "seven 7s", "all the sevens",
                              "lucky sevens")):
        return ("buy", {"amount": 77777.77})

    # baseball cap (disguise — drops heat) and valet parking (a trap: cops staged on your return)
    if (low in ("hat", "cap", "buy hat", "buy a hat", "buy cap", "buy a cap", "get a hat",
                "grab a hat", "buy the hat", "get a cap")
            or "baseball" in low or "ball cap" in low or "ballcap" in low):
        return ("buyhat", {})
    if "valet" in low and "no valet" not in low:
        return ("valet", {})

    # sweep for the AirTag he planted (before 'search the car' → explore eats it)
    if (low in ("sweep", "sweep the car", "sweep her", "sweep for trackers", "check for a tracker",
                "check for trackers", "find the tracker", "find the airtag", "find the tag",
                "look for a tracker", "look for the airtag", "search for a tracker", "scan for trackers",
                "check for bugs", "check for an airtag", "am i being tracked", "is there a tracker",
                "look for a bug", "debug the car", "check for a tag")
            or "airtag" in low or "air tag" in low
            or ("tracker" in low and any(w in low for w in ("find", "check", "sweep", "search",
                                                            "look", "scan", "for")))):
        return ("sweep", {})

    # explore the car / the glovebox
    if (low in ("explore", "search", "search the car", "search her", "look around the car",
                "glovebox", "glove box", "check the glovebox", "check the glove box", "rummage")
            or low.startswith(("explore", "search the", "check the glove"))):
        return ("explore", {})

    # ATM / withdraw — match the ATM/withdraw signal ANYWHERE ("let me hit the ATM for $5000")
    if ("atm" in low or "cash machine" in low or "bank machine" in low or "withdraw" in low
            or low.startswith("take out") or low in ("find a bank", "hit the bank")):
        return ("atm", {"amount": _money(low) or _bare_number(low)})   # accept 'withdraw 200'

    # claim what you're carrying — accept '$300' AND a bare '300'; only ZERO it on an explicit broke
    if _is_claim(low):
        amt = _money(low) or _bare_number(low)
        if amt is None and any(w in low for w in ("no cash", "no money", "broke", "nothing", "empty",
                               "zero", "don't have", "dont have", "haven't got", "havent got")):
            return ("claim", {"amount": 0.0})
        return ("claim", {"amount": amt})

    # parts list + selling the build off her
    if low in ("parts", "the build", "build sheet", "what can i sell", "what can i sell?",
               "show parts", "list parts", "the parts"):
        return ("parts", {})
    if low.startswith("sell") or low.startswith("strip"):
        return ("sell", {"what": re.sub(r"^(sell|strip)\s+", "", low).strip()})

    # dating + her jealousy
    if (low in ("flirt", "date", "find a date", "pick up a date", "get a date", "hit on someone",
                "find someone", "go on a date", "pull", "rizz someone up", "ask someone out",
                "meet someone", "chat someone up", "flirt with someone")
            or low.startswith(("flirt with", "pick up", "hit on", "ask out"))):
        return ("flirt", {})
    # take the date back to where she's parked — the deep betrayal
    if (low in ("bring them home", "take them home", "bring them back", "take them back",
                "bring my date home", "take my date home", "bring my date back", "take my date back",
                "invite them back", "invite them home", "take them to the motel", "bring them to the motel",
                "take them back to the motel", "back to the motel", "back to my place", "take them to bed",
                "take them to my room", "bring them to my room", "take them upstairs")
            or ("date" in low and any(w in low for w in ("home", " back", "motel", "room", "place", "bed")))
            or ("them" in low and any(w in low for w in ("home", "back to", "motel", "my room", "my place", "to bed")))):
        return ("bringhome", {})
    if low in ("kill the engine", "kill engine", "turn her off", "shut her off", "park her",
               "leave her in the lot", "leave her", "power her down", "engine off"):
        return ("killengine", {})
    if low in ("compliment her", "sweet talk her", "sweet-talk her", "tell her she's pretty",
               "apologize to her", "make it up to her", "reassure her", "she's the best"):
        return ("compliment", {})

    # rob a bank (Desperado only)
    if low in ("rob", "rob bank", "rob the bank", "rob a bank", "hit a bank", "stick up the bank",
               "rob the vault", "heist", "do a bank job", "rob this bank"):
        return ("rob", {})

    # gambling — raise the money (and the rewind cheat). 'put'/'lay' ONLY count as bets when there's
    # an amount, so "put on music" / "lay low" don't get eaten by the tables.
    _has_stake = bool(_money(low) or _bare_number(low)
                      or any(p in low for p in ("all in", "all-in", "let it ride", "everything",
                                                "double or nothing")))
    if (low.startswith(("bet", "gamble", "wager", "place a bet"))
            or (low.startswith(("put ", "lay ")) and _has_stake)
            or low in ("hit the tables", "hit the casino", "play the tables", "sports bet",
                       "double or nothing", "all in", "all-in", "let it ride", "everything")):
        m = re.search(r"on\s+(.+)$", low)            # "bet $1000 on the raiders"
        if any(p in low for p in ("all in", "all-in", "let it ride", "everything", "double or nothing")):
            amt = "all"                              # bet the whole wad
        else:
            _two = re.search(r"\b(\d{2,})\b", low)   # a bet of '50' is valid (unlike a menu '3')
            amt = _money(low) or _bare_number(low) or (float(_two.group(1)) if _two else None)
        return ("bet", {"amount": amt, "pick": (m.group(1).strip() if m else None)})

    # legal racing / showing (only after you own her)
    if low in ("race", "race her", "run it", "run a lap", "track day", "do a track day",
               "race the car", "send it", "hot lap", "lap it"):
        return ("race", {})
    if (low in ("show", "show her", "show the car", "enter the show", "car show", "enter her",
                "enter the car", "concours", "show her off", "enter the show field")
            or low.startswith(("enter the show", "show her in", "enter her in"))):
        return ("show", {})

    # payment method — exact phrases, plus short natural variants anchored to a PAY verb ("I'll pay
    # cash", "let's use the card", "put it on the card") so a narrated choice sets the method before 'fill'.
    _pays = re.match(r"^(?:i'?ll |let'?s |we'?ll |just |okay,? )?(?:pay|use|put it on|charge|swipe)\b", low)
    if (low in ("pay cash", "use cash", "cash", "pay with cash", "cash please", "cash it is")
            or (_pays and "cash" in low and "card" not in low and "credit" not in low)):
        return ("pay", {"method": "cash"})
    if (low in ("pay card", "use card", "card", "pay with card", "credit", "card please")
            or (_pays and ("card" in low or "credit" in low) and "cash" not in low)):
        return ("pay", {"method": "card"})

    # ---- the endgame: ways OUT, and the credits ----
    # flee south across the border (must precede the drive parse — "go south" is a drive otherwise)
    if (low in ("cross", "cross the border", "cross over", "flee", "run for the border",
                "run for it south", "go south", "head south", "south of the border", "to mexico",
                "flee to mexico", "escape to mexico", "make a run for the border", "jump the border",
                "drive into mexico", "cross into mexico")
            or ("border" in low and any(w in low for w in ("cross", "run", "flee", "jump", "over")))
            or ("mexico" in low and any(w in low for w in ("to ", "into", "flee", "escape", "run", "drive")))):
        return ("cross", {})
    # the shipping container — a forged life overseas
    if (low in ("ship out", "ship her out", "the container", "ship overseas", "ship her overseas",
                "load the container", "into the container", "disappear overseas", "vanish overseas",
                "get in the container", "take the container", "container", "ship the car")
            or ("container" in low and any(w in low for w in ("ship", "load", "into", "the")))
            or ("ship" in low and "overseas" in low)):
        return ("ship", {})
    # fake your own death — the fireball (only once you know his secret); must precede pardon/drive
    if (low in ("fake my death", "fake your death", "fake her death", "fake our death", "fake a death",
                "stage my death", "stage a death", "stage an accident", "fake the crash", "fake a crash",
                "burn her", "burn the decoy", "torch the decoy", "the fireball", "fake my own death",
                "stage my own death", "set the fire", "light it up", "die", "play dead", "disappear for good")
            or ("fake" in low and any(w in low for w in ("death", "die", "crash", "accident", "wreck")))
            or (any(w in low for w in ("stage", "fiery", "flaming", "fireball")) and
                any(w in low for w in ("crash", "wreck", "death", "fire", "accident", "disappear")))
            or (any(w in low for w in ("crash", "wreck")) and "disappear" in low)
            or ("burn" in low and any(w in low for w in ("decoy", "shell", "her down", "the z", "it down",
                                                          "the hood", "spade")))):
        return ("fakedeath", {})
    # bribe a pardon (the farce) — must be DELIBERATE: 'buy/get a pardon' or bribing the state, never
    # a stray 'pardon?' / 'pardon me' / 'beg your pardon' in conversation.
    if (low in ("pardon", "buy a pardon", "get a pardon", "bribe", "bribe an official",
                "pay for a pardon", "grease the wheels", "buy my way clean", "buy a pardon",
                "buy our way clean", "bribe the state", "bribe the governor", "buy off the state",
                "pay them off", "make it go away", "buy the pardon", "bribe my way out")
            or re.search(r"\b(buy|get|pay for|purchase|want) (a |the )?pardon\b", low)
            or ("bribe" in low and "clerk" not in low and "pardon" not in low)):
        return ("pardon", {"amount": _money(low)})
    # roll the credits — end the trip on your terms
    if low in ("retire", "end the trip", "end the road trip", "end the game", "roll credits",
               "roll the credits", "call it", "call it here", "the end", "i'm done", "im done",
               "we're done", "were done", "park it for good", "settle down", "hang it up",
               "that's a wrap", "thats a wrap", "finish the trip", "end it"):
        return ("retire", {})
    # the scorecard — how you're doing / how it ended
    if low in ("scorecard", "score card", "final score", "the score", "how did i do",
               "how did we do", "tally", "final tally", "stats", "my stats", "achievements",
               "awards", "the tally"):
        return ("scorecard", {})

    # ---- disguising the CAR (the CAR-heat axis): cover, plate swap, hood swap, respray ----
    # uncover FIRST (so 'uncover her' isn't eaten by the broad 'cover' catch-all just below)
    if (low in ("uncover", "uncover her", "uncover the car", "take the cover off", "pull the cover off",
                "off with the cover", "remove the cover", "take her cover off", "lose the cover")
            or "uncover" in low
            or ("cover" in low and any(w in low for w in ("off", "remove")))):
        return ("uncover", {})
    # the opaque cover (the Vegas-night easy-mode) — must precede camo (which owns 'cover the plate').
    # Word-boundary \bcover\b so it never fires inside 'discover'/'recover'/'undercover'.
    if (low in ("cover", "cover her", "cover the car", "cover the z", "car cover", "the cover",
                "grab the cover", "grab her cover", "put the cover on", "throw the cover on",
                "throw the cover over her", "cover her up", "drape her", "use the cover",
                "put her cover on", "get the cover", "opaque cover", "grab the car cover")
            or (re.search(r"\bcover\b", low) and "plate" not in low and "discover" not in low
                and any(w in low for w in ("her", "the car", "the z", "car cover", "up over")))):
        return ("cover", {})
    # swap the plate (the single best CAR-heat move — reads clean to ALPR, kills the Cedric tell)
    if (low in ("swap the plate", "swap plate", "swap plates", "swap the plates", "change the plate",
                "change plates", "change the plates", "switch the plate", "switch plates", "new plate",
                "different plate", "steal a plate", "grab a plate", "swap her plate", "switch the plates",
                "get a new plate", "put a different plate on")
            or ("plate" in low and any(w in low for w in ("swap", "change", "switch", "different",
                                                          "steal", "new ", "another")))):
        return ("swapplate", {})
    # detach the ace-of-spades hood (the disguise she CONSENTS to — it's a wrap)
    if (low in ("swap the hood", "swap hood", "change the hood", "change hood", "swap her hood",
                "plain hood", "steel hood", "new hood", "different hood", "ditch the hood",
                "lose the hood", "swap the carbon hood", "put a plain hood on", "detach the hood",
                "detach the spade", "detach the spade hood", "take the hood off", "take off the hood",
                "pull the hood", "pull the spade", "remove the hood", "remove the spade hood",
                "take the spade off", "lose the spade")
            or ("hood" in low and any(w in low for w in ("swap", "change", "plain", "steel", "ditch",
                                                         "lose", "different", "detach", "remove",
                                                         "take off", "take the", "pull")))
            or ("spade" in low and any(w in low for w in ("detach", "remove", "take", "lose", "pull off")))):
        return ("swaphood", {})
    # peel the rattle-can back off (undo a respray) — guard 'peel OUT of here' (a drive)
    if (low in ("peel", "peel it", "peel the paint", "peel off the paint", "peel her", "peel it off",
                "peel the paint off", "take the paint off", "remove the paint", "remove the rattle can",
                "undo the paint", "strip the paint", "peel the rattle can off")
            or (re.search(r"\bpeel\b", low) and "out" not in low
                and any(w in low for w in ("paint", "rattle", "the gray", "the grey")))):
        return ("peelpaint", {})
    # respray — rattle-can over the PPF (the betrayal she fears most). The DESTRUCTIVE verb: it must
    # require UNAMBIGUOUS paint intent, never a stray 'different color' / 'spray her with the hose'.
    if (low in ("respray", "repaint", "repaint her", "paint her", "paint the car", "paint job",
                "new paint", "respray her", "spraypaint her", "rattle can her", "rattlecan her",
                "change the color", "change her color", "different color", "spray paint her",
                "paint her a different color", "get her painted", "paint over her", "paint her gray",
                "paint her grey", "rattlecan her", "give her a respray", "spray her down")
            or re.search(r"\b(respray|repaint|rattle ?can|spray ?paint|paint ?job|maaco)\b", low)
            or re.search(r"\bpaint (her|it|the car|the z|over)\b", low)):
        return ("respray", {})

    # ---- her gadgets: camo, connectivity, and the self-driving secret ----
    # Z camouflage — dress her down / flaunt her
    if (low in ("camo", "camouflage", "disguise her", "disguise the car", "dress her down",
                "tarp her", "tarp the car", "hide the plate", "cover the plate", "go incognito",
                "blend in", "disguise", "hide her", "dull her down", "mud her up")
            or low.startswith(("disguise", "camo"))):
        return ("camo", {})
    if low in ("uncamo", "un-camo", "show her real face", "take the tarp off", "lose the disguise",
               "ditch the camo", "ditch the disguise", "clean her up", "drop the disguise",
               "show her off again", "unmask her", "reveal her"):
        return ("uncamo", {})
    # flash the lights
    if (low in ("flash the lights", "flash her lights", "flash the headlights", "flash lights",
                "blink the lights", "headlight flash", "pop the lights", "flash the brights",
                "flash", "hit the lights", "flash the high beams")
            or (low.startswith("flash") and "light" in low)):
        return ("flash", {})
    # play the stereo (not the gambling tables — those parsed above)
    if (low in ("stereo", "music", "play music", "play the stereo", "put on music", "play a song",
                "crank the tunes", "turn up the music", "turn up the stereo", "play something",
                "some music", "put on a song", "play the radio", "turn on the radio", "radio")
            or low.startswith("play ")):     # the gambling 'play the tables' was consumed above
        what = None
        m = re.search(r"play (?:me |us )?(?:some )?(.+)$", low)
        if m and m.group(1) not in ("music", "a song", "something", "the stereo", "the radio"):
            what = m.group(1).strip(" .")
        return ("stereo", {"what": what})
    # text someone (on WiFi)
    if (low in ("text", "send a text", "text someone", "check her messages", "check messages",
                "use the wifi", "use wifi", "get online", "go online", "send a message", "dm someone")
            or low.startswith(("text ", "message ", "dm "))):
        m = re.search(r"^(?:text|message|dm)\s+(.+)$", low)
        return ("text", {"who": (m.group(1).strip(" .") if m else None)})
    # the secret: wake her up to drive herself
    if (low in ("upgrade her", "upgrade the car", "make her drive herself", "make her self driving",
                "make her self-driving", "self driving", "self-driving", "give her autonomy",
                "teach her to drive", "wake her up", "wake her up the rest of the way",
                "make her autonomous", "give her the upgrade", "the upgrade", "upgrade")
            or ("self" in low and "driv" in low and any(w in low for w in ("make", "her", "upgrade")))
            or ("wake her" in low)):
        return ("upgrade", {})
    # let her drive (autopilot) — works only once she's upgraded
    if (low in ("let her drive", "let her take the wheel", "you drive", "you take the wheel",
                "take the wheel", "autopilot", "drive yourself", "she drives", "let ace drive",
                "let her have the wheel", "her turn to drive", "you take it from here")
            or low.startswith(("let her drive", "you drive", "drive yourself", "autopilot"))):
        m = re.search(r"(?:drive|take the wheel|autopilot)(?:\s+(?:to|toward|for|us to|me to|over to))\s+(.+)$", low)
        return ("autodrive", {"dest": (m.group(1).strip(" .") if m else None)})

    # the mountain-pass / season report
    if (low in ("passes", "mountain passes", "the passes", "road conditions", "conditions",
                "what's closed", "whats closed", "what passes are open", "snow", "weather",
                "is tioga open", "are the passes open", "season", "what's the season")
            or ("pass" in low and any(w in low for w in ("open", "closed", "snow", "condition")))):
        return ("closures", {})

    # ---- the body: eat, bathroom (#1 / #2), a drink ----
    if (low in ("eat", "eat something", "get food", "grab food", "grab a bite", "food", "lunch",
                "dinner", "breakfast", "get something to eat", "feed me", "i'm hungry", "im hungry",
                "grab lunch", "grab dinner", "have a meal", "get a meal", "get lunch", "get dinner")
            or low.startswith(("eat ", "grab some food", "get some food"))):
        return ("eat", {})
    # #2 first (more specific) so it never falls through to #1
    if (any(p in low for p in ("number two", "#2", "take a dump", "take a shit", "poop", "go number 2"))
            or low in ("number 2", "do a number two", "drop the kids off at the pool")):
        return ("restroom", {"number": 2})
    # NB: dropped the ambiguous 'i need to go' / 'i have to go' — they ate 'i need to go to vegas'.
    # 'i gotta go' bathroom intent must be unambiguous (pee/bathroom/restroom), not a travel verb.
    if (any(p in low for p in ("restroom", "bathroom", "need to pee", "have to pee", "gotta pee",
                               "take a leak", "#1", "use the toilet", "rest stop", "pit stop",
                               "find a john", "go to the bathroom", "need the bathroom"))
            or low in ("pee", "toilet", "piss", "number one", "number 1", "leak", "wc",
                       "i need to pee", "i gotta go", "i need to go", "nature calls")):
        return ("restroom", {"number": 1})
    # caffeine — counter fatigue. Require drinking INTENT ('coffee' alone could be 'coffee break from
    # this conversation'); guard 'wake HER up' (the upgrade) and 'coffee break' (a rest, not a coffee).
    if ((low in ("coffee", "get coffee", "grab coffee", "drink coffee", "a coffee", "get a coffee",
                 "grab a coffee", "caffeine", "caffeinate", "espresso", "energy drink", "red bull",
                 "monster", "rockstar", "stay awake", "stay up", "wake up", "wake myself up",
                 "get some coffee", "need coffee", "i need coffee", "another coffee", "more coffee",
                 "cup of coffee", "buy a coffee", "buy coffee")
             or (("coffee" in low or "caffeine" in low or "energy drink" in low or "espresso" in low)
                 and any(w in low for w in ("get", "grab", "buy", "need", "want", "have", "drink",
                                            "a coffee", "some coffee", "cup", "more", "another"))
                 and "coffee break" not in low))
            and "wake her" not in low and "wake me her" not in low):
        return ("caffeine", {})
    if ((low in ("drink", "have a drink", "get a drink", "grab a drink", "have a beer", "get a beer",
                 "buy a drink", "go to the bar", "hit the bar", "have a few", "get drunk", "buy a round",
                 "have a couple", "do shots", "shots", "let's drink", "lets drink", "a beer")
             or low.startswith(("drink", "have a drink", "have a beer", "have a few", "have a couple",
                                "do a shot", "do shots")))
            # 'drink the water' / 'have a glass of water' / soda / coffee aren't alcohol
            and not any(w in low for w in ("water", "soda", "juice", "coffee", "milk", "soft drink",
                                           "lemonade", "tea", "coke"))):
        if "few" in low or "couple" in low or "round" in low:
            n = 3
        else:
            m = re.search(r"\b([1-9])\b", low)
            n = int(m.group(1)) if m else 1
        return ("drink", {"n": n})

    # a bare grade request at the pump = a fuel command ("premium", "91", "the good stuff", "give me premium")
    _bare = low.strip().rstrip("!.")
    if (_bare in ("premium", "premium please", "the good stuff", "good stuff", "high octane", "91", "92",
                  "93", "super", "top tier", "the expensive stuff", "the good gas")
            or re.match(r"^(?:give me|i'?ll take|gimme|get me|fill (?:with|it with|her with|me with))\s+"
                        r"(?:the\s+)?(?:premium|high[\s-]?octane|good stuff|good gas|91|92|93|super|top[\s-]?tier)\b", low)):
        return ("fuel", {"fill": True, "grade": "premium"})
    if _bare in ("regular", "regular please", "the cheap stuff", "cheap gas", "87", "unleaded", "the cheap one"):
        return ("fuel", {"fill": True, "grade": "regular"})

    # fuel
    if _is_fuel(low):
        args = {}
        if "fill" in low or "top" in low:
            args["fill"] = True
        m = re.search(r"\$\s*" + _NUM, low) or re.search(_NUM + r"\s*(?:dollars|bucks|usd)", low)
        if m:
            args["dollars"] = float(m.group(1))
        m = re.search(_NUM + r"\s*(?:gal|gallon)", low)
        if m:
            args["gallons"] = float(m.group(1))
        m = re.search(_NUM + r"\s*(?:l\b|liter|litre)", low)
        if m:
            args["liters"] = float(m.group(1))
        if "cash" in low:
            args["prefer"] = "cash"
        elif "card" in low or "credit" in low:
            args["prefer"] = "card"
        # FUEL GRADE — she takes PREMIUM only. Asking for it = premium; saying nothing or asking for the
        # cheap stuff = regular (the trap: she'll knock down the road on 87).
        if any(g in low for g in ("premium", "high octane", "high-octane", "the good stuff", "top tier",
                                  "top-tier", "91", "92", "93", "super", "the good gas", "good gas",
                                  "highest", "best gas", "the expensive")):
            args["grade"] = "premium"
        elif any(g in low for g in ("regular", "the cheap", "cheap stuff", "cheapest", "lowest", "87",
                                    "85", "unleaded plain", "low octane", "save money")):
            args["grade"] = "regular"
        if not any(k in args for k in ("fill", "dollars", "gallons", "liters")):
            args["fill"] = True
        return ("fuel", args)

    # sleep
    if _is_sleep(low):
        args = {}
        if "rough" in low or "pull over" in low or "in the car" in low or "in the seat" in low:
            args["rough"] = True
        for k in ("camp", "motel", "lodge", "airbnb"):
            if k in low:
                args["kind"] = k
        if any(w in low for w in ("airbnb", "air bnb", "private", "rental", "alias", "off the books",
                                  "under a name", "under an alias", "vrbo")):
            args["kind"] = "airbnb"
        if "cash" in low:
            args["prefer"] = "cash"
        elif "card" in low:
            args["prefer"] = "card"
        return ("sleep", args)

    # talk to the locals (an encounter NPC)
    if _is_talk(low):
        return ("talk", {})

    # drive
    dest = _drive_dest(low)
    if dest is not None:
        push = any(w in low for w in ("fast", "floor", "push", "hard", "haul", "book it", "step on"))
        return ("drive", {"dest": dest, "push": push})

    # otherwise: talk to FAIRLADY
    return ("say", {"text": t})


# Her build sheet, as conversation. A "coherent question about her build or specs" warms her
# up fast — gearheads get the 3-turn favor, civilians get the 5. Also used by the narrator stub
# and the traffic-stop rubric (car-cred plays well with a certain kind of cop).
# Single words match on WORD BOUNDARIES — "she's special" is not spec talk, "respect" is not
# spec talk, and a witness with a "camera" earns no cam credit. Phrases match as substrings.
_SPEC_WORD_RE = re.compile(
    r"\b(torque|horsepower|hp|engine|motor|displacement|compression|carbs?|webers?|mikunis?|"
    r"cams?|strokers?|stroked|l24|l26|l28|inline|suspension|coilovers?|brakes?|gearbox|"
    r"transmission|diffs?|lsd|redline|wheelbase|specs?|"
    r"lb[-/ ]?ft|ft[-/ ]?lbs?|foot[- ]?pounds?|0-60|5[- ]?speed)\b")
_SPEC_PHRASES = (
    "straight six", "straight-six", "five speed", "five-speed", "zero to sixty",
    "quarter mile", "curb weight", "your build", "the build", "what's under", "whats under",
    "under the hood",
)
_INTERROGATIVE = ("what", "how", "tell me", "talk me through", "walk me through",
                  "is it", "does", "do you", "you got", "give me", "?")


def spec_hits(text: str) -> int:
    """Count distinct build-sheet references, boundary-safe."""
    low = (text or "").lower()
    return len(set(_SPEC_WORD_RE.findall(low))) + sum(1 for p in _SPEC_PHRASES if p in low)


def is_spec_question(text: str) -> bool:
    low = (text or "").lower()
    return spec_hits(low) > 0 and any(q in low for q in _INTERROGATIVE)


def _bare_number(low: str):
    """A bare integer figure ('withdraw 200', 'bet 1000') with no $ — for the money verbs that
    already know the number is dollars. Skips small ints that are likely menu picks (handled first)."""
    m = re.search(r"\b(\d[\d,]{2,})\b", low)        # ≥3 digits → a dollar amount, not 'branch 3'
    return float(m.group(1).replace(",", "")) if m else None


def _money(low: str):
    """Pull a dollar figure out of free text: '$2000', '2,000', '5k', '5 grand'. None if absent."""
    m = re.search(r"\$\s*([\d,]+(?:\.\d+)?)", low) or re.search(r"\b([\d,]+(?:\.\d+)?)\s*(?:dollars|bucks|usd)\b", low)
    if m:
        return float(m.group(1).replace(",", ""))
    m = re.search(r"\b([\d.]+)\s*(?:k\b|grand)", low)
    if m:
        return float(m.group(1)) * 1000.0
    return None


_CLAIM_PHRASES = ("i have", "i've got", "ive got", "i got", "i'm carrying", "im carrying",
                  "i am carrying", "claim", "i'm holding", "im holding", "carrying", "in my pocket",
                  "on me", "in my wallet", "i'm packing", "im packing")


def _is_claim(low: str) -> bool:
    if low in ("i'm broke", "im broke", "i have no cash", "i have no money", "no cash", "broke",
               "i'm flat broke", "im flat broke", "got nothing", "i've got nothing"):
        return True
    has_money = bool(_money(low)) or any(w in low for w in ("cash", "broke", "wallet", "pocket"))
    return has_money and any(p in low for p in _CLAIM_PHRASES)


def _is_fuel(low: str) -> bool:
    return (low.startswith(("fuel", "gas", "fill", "pump", "buy gas", "buy fuel", "refuel", "top"))
            or low in ("fill up", "fill her up", "fill it up", "gas up", "fuel up"))


def _is_sleep(low: str) -> bool:
    return (low.startswith(("sleep", "rest", "motel", "camp", "lodge", "stay", "check in",
                            "check-in", "bed", "crash", "pull over", "turn in", "good night",
                            "airbnb", "air bnb", "book", "find a place", "get a room", "get some sleep",
                            "find a motel", "find a room", "find a hotel", "get some rest", "call it a night"))
            or "airbnb" in low or "private stay" in low or "private place" in low
            or any(p in low for p in ("find a motel", "find a room", "find a hotel", "get some sleep",
                                      "call it a night", "go to sleep", "bed down")))


def _is_talk(low: str) -> bool:
    if low.startswith(("talk to", "speak to", "speak with", "talk with")):
        return True
    return low in ("talk", "speak", "greet", "say hi", "say hello", "hello", "hi",
                   "talk to them", "talk to her", "talk to the locals", "introduce yourself")


_DRIVE_PREFIX = re.compile(
    r"^(?:let'?s |let me |let us |we'?(?:ll| will) |can (?:you|we) |i'?(?:d| would)?\s*(?:like to |want to |wanna )?|please |okay,? )?"
    r"(?:drive|go|head|take (?:me|us)|navigate|route|set off for|"
    r"set out for|make for|aim for|roll (?:out )?(?:to|for)|point (?:me|us) (?:at|to|toward))\b", re.I)


def _drive_dest(low: str) -> str | None:
    m = _DRIVE_PREFIX.match(low)
    if not m:
        return None
    rest = low[m.end():].strip()
    rest = re.sub(r"^(?:me|us|her)\s+", "", rest)      # "drive me to zion" → "to zion"
    rest = re.sub(r"^(?:to|for|toward|towards|at|over to|out to|up to|down to)\s+", "", rest)
    rest = re.sub(r"\b(fast|hard|quick(?:ly)?|floor it|push it|step on it)\b", "", rest).strip(" .,")
    return rest or None
