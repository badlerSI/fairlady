I now have everything I need. The car's physics live on three `GameState` scalar fields (`fuel_l`, `tank_l`, `mpg`); the persona is loaded once from `car.json`; heat/bond/desperado all read flags. This gives me a clean design for swapping the active car. Here is the complete, implementation-ready spec.

---

# BOB MODE — AMENDMENTS (Ben's update — these override the base spec below)

1. **The window is the FIRST MONTH, not a week.** You can go to the parents' Carson City house any
   time in the first ~30 days and they are NOT home (doors unlocked). Replace `bob_deadline_day =
   day + 7` with the first-of-the-month boundary: the parents are away until **day 30** (set
   `BOB_PARENTS_HOME_DAY = 30` in config; trigger their return when `s.day >= 30`). The whole "borrow
   Bob, no-heat joyride, call Ace weekly" loop runs across the month.

2. **After the month, the path stays OPEN (no hard fail).** When the parents come home (day ≥ 30 or
   on the return-beat), you can STILL: **return Bob**, **convince them to forgive you** (a short
   talk-your-way-out beat — apologize / explain / lean on Ace having vouched for you), **offer to buy
   Bob ($7,000, everything forgiven)**, and **keep calling Ace** to see how she's doing. So the base
   spec's "grace period then the offer lapses / heat comes back" hard-lapse is SOFTENED: the offer
   doesn't evaporate — instead, once the parents are home you must come to them in person (at
   `carson_parents`) to make it right. Ace's `phone_home` betrayal still triggers only if you let her
   go COLD by not calling — that remains the real fail state, not the calendar.

3. **AFTERGAME: $20k to make Bob talk (the joke).** After any ending (in the post-game free-roam),
   add an upgrade: pay **$20,000** to give Bob talking-car status — purely a gag. It uses a **funny
   male voice, Homer-Simpson-like** (per VOICE_CASTING.md: Piper `en_US-john-medium` + **homer** RVC).
   Spec it as an `upgrade bob` verb available only post-ending when you own Bob: sets
   `s.flags["bob_talks"] = True`, charges $20k, and routes Bob's lines through `npc_speak(voice via the
   homer impression)`. It's comic relief — Bob is dim, warm, and earnest, the opposite of Ace's sharp
   noir. (Ace, if you still talk to her, has OPINIONS about you spending twenty grand to make the
   beige loaner talk.)

Everything else in the base spec (the WiFi calls keeping Ace warm, the economy staying live, the
two-car active-car swap, the $7k buy-Bob ending) stands as written.

---

# BOB MODE — Implementation-Ready Design

## Concept (matches Ben's design exactly)

Drive to the address on Ace's **registration** — the OWNER'S PARENTS' house in **Carson City**, out of town, doors unlocked. You **park Ace** there, leave her **on the home WiFi** (so you can still `call`/`text` her remotely), and take **BOB** — a basic, brown **1971 Series 1 240Z with a sunroof** — on a **7-day NO-HEAT** joyride. On day 7 the parents come home; **Ace calls you**; she can connect you to the owner, and you `buy bob` for **$7,000, everything forgiven** → a new game-end node.

This is a fourth "good ending" alongside owned / border / container / pardon / selfdrive, and it's the *cheapest* one — but it's gated behind finding a secret address and surviving a week in a car you can't hide behind (Bob is forgettable, so no heat; but no Ace whispering you through a traffic stop either).

---

## 1. The trigger — `content/pois.json` + `engine/encounters.py`

The registration address is in Carson City. Two facts already in the codebase make this clean: `garage.explore()` finds the glovebox roll **"under the registration"** (so the registration is canonically a physical object in the car), and `carson_city` is already a POI (`engine/heat.py` lists it `_BUSY`, `endings.py` lists it `PARDON_POIS`).

**Add a new POI** to `pois.json` `pois` array (near the carson_city block, lines 260-274):

```json
{
  "id": "carson_parents",
  "name": "the registered address — a quiet street in Carson City",
  "kind": "encounter",
  "region": "NV",
  "lat": 39.1701,
  "lon": -119.7510,
  "services": ["lodging"],
  "heat_zone": false,
  "blurb": "A '70s ranch house up under the foothills, blinds drawn, two weeks of newspapers on the step. The name on the registration is the mailbox. Nobody home."
}
```

- `kind: "encounter"` keeps it in `QUIET_KINDS`? No — `QUIET_KINDS = ("park","encounter","spot")`, so it counts as quiet (good: low visibility, `heat.visibility` returns 1, and it's not in `_FLASHY`). It carries `lodging` so you can sleep there.
- It must **not** auto-appear in `choices()` drive lists until **revealed**. Reuse the existing `s.flags["revealed"]` destination mechanism (game.py lines 511-515 already render any `revealed` POI as a drive option). The address gets added to `revealed` when Ace tells you about it.

**How the address is revealed (the "registration flag"):** Ben offered three options — POI, the Area 51 unlock flag, or standalone. **Recommended: a hybrid of standalone + a soft tie to intimacy**, because the existing `area51_gate` POI (`kind: "encounter"`, line 1491) has no current unlock payload, and gating BOB MODE behind it would couple two unrelated features. Instead:

Add an `origin`-style reveal. The registration question is a natural extension of the existing "previous owner" lore thread. In `game.py`, the `STORIES`/`LORE` machinery already gates reveals on flags. Add a new free-text intent + reveal:

- **Parser** (`commands.py`, near the origin block lines 86-93): add
  ```python
  if any(p in low for p in ("registration", "the address on", "whose name", "who's it registered",
                            "registered to", "the papers", "the title says", "address on the reg")):
      return ("origin", {"which": "registration"})
  ```
- **Reveal** (`game.py` `_origin_beat`, add a `"registration"` branch + a `LORE["registration"]` entry). It only pays off once she's warmed to you and you're somewhere quiet — reuse `_quiet_place(s)` and a bond gate (`s.bond >= 55`, i.e. STEADY+), mirroring how `NAME_DROP` is gated:

  ```
  LORE["registration"] = (
    "…You actually read the registration. Of course you did. It's not his name on it — it's his
    folks'. They bought me for him; the paperwork never moved. They're up in Carson City, and
    they're in Portugal till the end of the month — he mentioned it once like it didn't matter.
    Door's never locked. …Why do you ask, ace.",
    "carson_parents")
  ```
  Setting `poi_id = "carson_parents"` makes `_origin_beat` append it to `s.flags["revealed"]` (existing code, lines 1220-1224), so "drive to carson_parents" now appears and works. Also set `s.flags["knows_registration"] = True` here.

This keeps it **standalone and discoverable** (ask the right question, somewhere quiet, once she trusts you), with no dependency on Area 51 or the owner appearing. It's the same "ask the right thing at the right place" grammar as Mayumi's name.

---

## 2. Parking Ace + leaving her on WiFi — new module `engine/bobmode.py`

The trigger is **driving to `carson_parents` and choosing to park Ace there.** On arrival at that POI, `_after_arrival` should surface the choice (don't auto-trigger — entering BOB MODE is a deliberate act).

**New state (all in `s.flags`, so saves stay back-compatible — see §7):**

| flag | meaning |
|---|---|
| `bob_mode` | True while you're driving Bob (the master switch) |
| `bob_day_started` | `s.day` when you took Bob (for the 7-day timer) |
| `bob_deadline_day` | `bob_day_started + 7` |
| `ace_parked_poi` | `"carson_parents"` — where Ace sits on WiFi |
| `ace_car` | a dict snapshotting Ace's physics + identity (see swap, §3) |
| `bob_returned` | set when you bring Bob back to close the loop |

**The verbs** (add to `commands.py` and the `handle()` dispatch in `game.py`):

- **`park ace` / `leave her here` / `stash ace`** → only valid at `carson_parents`, not yet in `bob_mode`. Calls `bobmode.enter(s)`.
- **`take bob` / `swap to bob`** — folded into `enter()` as the same beat (you park her *and* take Bob in one move; that's the fiction).
- **`call ace` / `call her`** — the remote-talk verb. Reuses the connectivity fiction from `gadgets.text_someone`: Ace is on the parents' home WiFi, so she's reachable from anywhere. Unlike `text`, `call` works **regardless of where Bob is** (she has the WiFi, you have a phone). Routes to `bobmode.call_ace(s, raw)` which narrates with Ace's persona (`_PERSONA`) even though the active car is Bob.
- **`text`** while in bob_mode: keep working, but `gadgets._on_wifi` checks **Bob's** current place. Patch `text_someone` so that in `bob_mode` the reply fiction is "she relays from the house" (she always has signal; Bob is just a phone-tether). Simplest: in bob_mode, `call`/`text` always succeed.

**`bobmode.enter(s)`** does:
```
1. Guard: s.place.poi_id == "carson_parents", not s.flags.get("bob_mode"),
   not s.flags.get("bought"). Else return a refusal.
2. Snapshot Ace: s.flags["ace_car"] = {"fuel_l": s.fuel_l, "tank_l": s.tank_l,
   "mpg": s.mpg, "name": "Ace"}  (and stash her heat axes — see §5).
3. Swap in Bob's physics (see §3).
4. s.flags["bob_mode"] = True
   s.flags["ace_parked_poi"] = "carson_parents"
   s.flags["bob_day_started"] = s.day
   s.flags["bob_deadline_day"] = s.day + 7
   s.flags["ace_on_wifi"] = True
5. Heat off for the week: DON'T reuse no_heat (that's the bought/clear flag the
   whole engine keys "she's yours" on). Use a SEPARATE flag bob_no_heat and teach
   heat.add/visibility/snapshot to treat (no_heat OR bob_no_heat) as "meter frozen".
   See §5 — this is the one cross-cutting change and it must be done carefully.
6. checkpoint(s, "parked Ace — took Bob") so the week is rewind-safe.
7. Return the entry beat + an Ace voice moment (she's amused, wary, jealous of Bob).
```

**Ace's voice on handing you Bob** (drama stub for `_narrate`):
> "…You're really doing this. Fine. He's in the garage under a sheet — brown, a *sunroof*, a name badge that says BOB in the previous owner's labelmaker. Basic as a butter knife and half as sharp. Take him. I'll be here, on the WiFi, watching the foothills and judging your taste. Call me. I mean it — *call me*, ace. Don't make me sit in a stranger's garage for a week wondering."

---

## 3. BOB as a second drivable car — the swap

The engine has **no car object** — the active car is just three scalars on `GameState` (`fuel_l`, `tank_l`, `mpg`) plus the persona string loaded once from `car.json`. That makes the swap trivial and low-risk: **swap the scalars, swap the persona, set a flag the snapshot/narrator read.**

**Bob's content** — add `content/bob.json` (mirrors `car.json` shape so the same loader works):
```json
{
  "name": "BOB",
  "model": "1971 Datsun 240Z Series 1",
  "color": "brown (Nissan 918 Racing Green's sad cousin)",
  "tank_liters": 50.0,
  "fuel_economy_mpg": 24.0,
  "start_fuel_liters": 50.0,
  "sunroof": true,
  "persona": "You are BOB, a 1971 Datsun 240Z Series 1 — brown, a factory sunroof someone added badly, a chrome bumper, a stock L24 2.4 inline-six, dog-dish hubcaps, and a name badge a previous owner label-made: BOB. You are NOT Ace. You barely talk — you have a tinny aftermarket head unit, no map, no opinions about torque, and a faint smell of someone's grandfather. You are honest, slow, comfortable, and completely forgettable, which is the most useful thing a car can be this week. When the driver talks to you, you answer in short, plain, good-natured sentences, like an old dog. You never whisper cleverly at cops because nobody pulls Bob over. You miss nothing because you notice nothing.",
  "voice": "am_onyx",
  "language": "en"
}
```

Note Bob is deliberately **better at the boring stuff** (bigger tank, better mpg, starts full) and worse at everything that made Ace special — that's the joke and the mechanical trade: a reliable nothing-car.

**Active-car indirection** — three touch points:

1. **Physics:** `bobmode.enter` sets `s.fuel_l/tank_l/mpg` from `bob.json`. `bobmode.exit` (rare — only if you abandon BOB MODE early, see §6) restores from `s.flags["ace_car"]`. `rules.drive/fuel` already read these scalars, so **no change to rules.py**.

2. **Persona for the narrator:** today `_PERSONA = _CAR["persona"]` is a module global (game.py line 21). Change `_narrate` to pick the live persona:
   ```python
   def _active_persona(s):
       if s.flags.get("bob_mode"):
           return _BOB["persona"]      # loaded like _CAR at module top
       return _PERSONA
   ```
   and pass `_active_persona(s)` into `nar.narrate(...)`. **Exception:** `call_ace`/`text` in bob_mode pass `_PERSONA` (Ace's voice) explicitly — she's on the phone, not the car you're in.

3. **Snapshot:** `snapshot()` should report the active car's identity so the frontend can render Bob (brown, sunroof) instead of the white Z. Add:
   ```python
   "active_car": "bob" if s.flags.get("bob_mode") else "ace",
   "car_name": "BOB" if s.flags.get("bob_mode") else "FAIRLADY",
   "bob_days_left": (s.flags["bob_deadline_day"] - s.day) if s.flags.get("bob_mode") else None,
   ```
   `garage.car_value/show_score` and the `parts`/`sell` verbs must be **disabled in bob_mode** (Bob has no build to strip; he isn't yours to sell). Guard those verbs with `if s.flags.get("bob_mode"): return ["…that's Bob. Stock as a fridge. Nothing to sell, ace."]`.

---

## 4. The 7-day timer + parents-return + Ace's call — `engine/bobmode.py`

Model the deadline exactly like the **owner deadline** (`encounters.check_owner_deadline`, encounters.py lines 508-516), which already fires off `s.day` comparisons inside `_after_arrival`. Add a sibling check called from the same place (game.py `_after_arrival`, right where `check_owner_deadline` is invoked, line 624) **and** after `sleep` (so the day can tick over while you rest):

```python
def check_bob_deadline(s, events):
    if not s.flags.get("bob_mode") or s.flags.get("bob_returned"):
        return None
    if s.day < s.flags["bob_deadline_day"]:
        return None
    # the parents are home — Ace calls you, wherever Bob is.
    s.flags["bob_call_pending"] = True
    events.append("CALL: your phone lights up. It's the house in Carson City. It's Ace.")
    return BOB_CALL_MOMENT   # drama stub, Ace's voice
```

`BOB_CALL_MOMENT` (Ace, on the parents' WiFi, the parents back early/on time):
> "Ace. They're home, ace — pulled into the drive an hour ago, jet-lagged and confused about the brown Datsun in their garage with a charger cord running to it. …I talked to them. I talked to *him* — he drove up when they called. He's not angry. He's *laughing*. He says if you bring Bob back whole, you can have him — seven grand, everything else forgiven, the white-Z business, all of it. He's tired of the chase. So am I. Come home. Bring Bob. Let's end it."

This sets `s.flags["bob_call_pending"]`. The call doesn't force the ending — it **opens** the buy. From here:

- A new choice appears in `choices()` (when `bob_call_pending`): `{"cmd": "buy bob", "note": "$7,000 — everything forgiven"}` and `{"cmd": "drive to carson_parents", "note": "bring Bob home to close it"}`.
- **Where can you buy Bob?** Cleanest: the deal closes **back at `carson_parents`** (you bring Bob home, the owner + parents are there). So `buy bob` requires `s.place.poi_id == "carson_parents"` AND `bob_call_pending`. If you `buy bob` elsewhere, Ace says "Bring him *home* first — they're standing in the driveway waiting." This reuses the owner's "meet me at the Oakland garage" pattern, so it's consistent grammar.

**Timer edge:** if you never return and keep driving past day 7, that's fine — `bob_no_heat` stays on (Bob genuinely draws no heat; the stakes are social, not legal). But to keep it from being a free infinite no-heat car, **after the call, each additional day Ace's calls get sharper and the offer is time-boxed**: add `bob_grace_day = bob_deadline_day + 3`. Past the grace day without returning, Ace stops calling, the owner withdraws the $7k offer (`s.flags.pop("bob_call_pending")`, set `bob_offer_lapsed`), and you're left holding a borrowed Bob with a soured owner — the white-Z heat **comes back on** (clear `bob_no_heat`, restore Ace's stashed heat) and the owner deadline logic resumes. This makes the week a real window, not a permanent hideout.

---

## 5. Heat / disguise / economy while driving Bob

**Ben's spec: NO HEAT, but cash still matters.** Here's the precise interaction:

**Heat — frozen, but not "cleared":** The engine has exactly one "meter off" flag today: `no_heat`, set by `garage.go_legit`, and it means *"she's titled in your name, the game is essentially won."* It's read in ~12 places (heat.add, visibility, exposure, snapshot, bond.armed, dashboard, etc.). **Do not reuse `no_heat` for Bob** — it would make Ace read as "bought," disable her anti-theft/jealousy, retire the bond ledger, and let `retire` roll an `owned` ending. Instead:

- Add `bob_no_heat` flag, set in `enter()`, cleared in the buy / lapse.
- Introduce one helper `heat.meter_frozen(s)` → `return bool(s.flags.get("no_heat") or s.flags.get("bob_no_heat"))`, and replace the bare `s.flags.get("no_heat")` checks **in heat.py** (`add`, `_floor`, `visibility`→via exposure, `dashboard`, `social_arrival`, `social_fuel`, `lie_low`) with `meter_frozen(s)`. Leave **bond.py's** `no_heat` checks alone (Bob doesn't retire the relationship — Ace is very much still keeping score about Bob, see jealousy below).
- `snapshot()`: report `heat: 0` and `heat_label: "Bob draws nothing — nobody pulls over a brown Datsun"` when `bob_no_heat`.

Net effect: while in Bob, the meter is frozen at 0, no social tags fire, no clerk beat, no traffic stops escalate. **Bob is the disguise** — which is why the `camo`/`uncamo` verbs are inert in bob_mode (gadgets.camo already early-returns when `no_heat`; extend that to `meter_frozen` so it says "Bob doesn't need a costume — he IS one").

**Why this is safe:** Ace's *car heat* is the BOLO on the white Z. While the white Z sits unplugged-but-on-WiFi in a garage in Carson City, nobody's photographing it on the Strip — so freezing the meter is fiction-consistent, not a cheat. Stash Ace's heat axes on enter (`s.flags["ace_car"]["car_heat"]`, `["personal_heat"]`, `["heat"]`) and **restore them only if the week lapses** (§4) — if you buy Bob, they're forgiven (zeroed) along with everything else.

**Economy — fully live.** Cash, the card, the ATM, the glovebox, gambling, parts (Ace's, only when back in Ace), lodging, fuel — all unchanged. You still pay for Bob's gas (he has a 50L tank), still pay to sleep, still need **$7,000 cash** for the buy. Because the card no longer spikes heat in bob_mode (meter frozen), card vs cash is purely a **money** decision this week, not a heat one — a deliberate, pleasant simplification that matches "no heat, but cash still matters." Crucially, **$7k is reachable without a heist**: ATM cap is $9,999, so a patient player can simply withdraw it. The buy is meant to be the *easy* good ending — that's the point of Bob.

**Bond / jealousy — STILL ON, and this is the emotional core.** Ace is parked, watching the foothills, while you gallivant in another Z. Reuse the dating jealousy ledger pointed at Bob:

- On `enter`, a small affectionate sting: `bond.adjust(s, -2.0, "left me in a stranger's garage and ran off in another Z", "mark")`.
- Each `call ace` warms her (`bond.adjust(s, +1.0, "called me from the road like you said you would", "warm")`, diminishing) — **calling is the mechanic that keeps her from going COLD during the week.** Skip calling for several days and she cools; if she hits COLD while you're in Bob, her anti-theft arms **on Ace** — and since Ace is the one sitting on open home WiFi, the existing `phone_home` betrayal becomes reachable in a delicious new way: *she phones the owner herself and the $7k offer evaporates into a `taken`/`phoned_home` loss.* Wire `check_bob_deadline`/sleep to call `endings.phone_home` if `bond.armed(s)` and you slept while Ace is on the parents' WiFi. This makes "call her" a real weekly obligation, not flavor.

---

## 6. The BUY BOB ending — `endings.py`

**Add a win key.** In `endings.py`:

```python
WIN_KEYS = ("owned", "border", "container", "pardon", "selfdrive", "bob")
```
```python
ENDING_TEXT["bob"] = (
  "BOB & FORGIVEN",
  "Seven thousand dollars and a brown Datsun with a sunroof and nobody's name on it but yours, now. "
  "The white Z is back in the garage where she was always going to end up — and the man who built her "
  "shook your hand instead of calling the law. Everything's forgiven: the show floor, the plate, the "
  "whole long run. You drove the wrong car home and it turned out to be the right one. 心.")
```

**The buy function** `endings.buy_bob(s)`:
```
Guards:
  - s.flags.get("bob_call_pending")  (the parents are home, the offer's open)
  - s.place.poi_id == "carson_parents"  (bring him home to close it)
  - economy.max_affordable(s, "cash") >= 7000  (BOB_PRICE = 7000.0 in config)
On success:
  - economy.pay(s, BOB_PRICE, prefer="cash")
  - Forgiveness: zero Ace's stashed heat; pop bob_no_heat; mark the owner report withdrawn.
    Cleanest: call a new bobmode.go_legit_bob(s) that:
       * keeps you in Bob (s.fuel_l/tank_l/mpg stay Bob's — Bob is the car you bought),
         OR restores Ace + marks Ace also free — DESIGN CHOICE below.
       * s.flags["bought"] = True; s.flags["no_heat"] = True   (now legitimately won)
       * s.flags["report_withdrawn"] = True
       * pop bob_mode, bob_call_pending, desperado/gun/wanted_armed (forgiven)
       * bond.adjust(s, +20, "ended the run — brought us both home", "warm")
  - _win(s, "bob")  + scorecard
  - "good_ending": True moment for the narrator
```

**DESIGN CHOICE — which car do you drive away in?** Ben's text says you *buy Bob*, everything *(re: Ace)* forgiven. The cleanest, most resonant reading: **you buy Bob and Ace goes back to the man who built her, forgiven and free of you — you chose the honest, humble car and gave the ghost back to the ghost-lover.** So `buy_bob` ends the game (it's a terminal win, like border/container — not free-roam like `owned`). The scorecard rolls. The active car stays Bob for the credits art. This is thematically the strongest: it's the *anti-`owned`* ending — you don't get the dream car, you get the honest one and a clean conscience, and Ace gets to go home to be a ghost in peace.

(If Ben prefers the bittersweet-but-together version — buy Bob AND keep Ace — that's a one-line change: don't restore/return Ace, set `bought` on the white Z too. But I recommend the give-Ace-back version; it's the more interesting ending and it's what "park her at his parents' / everything forgiven" emotionally implies.)

**Ace's voice at the buy** (`buy_bob` moment stub) — she's on the phone, then in the room:
> "…Done? It's done. Seven grand and a handshake and Bob's yours, papers and all. And me — he's taking me home. To the brick, the bench, the bad spring on the roll-up. It's where I go, ace; we both knew that from the show floor, even when we were pretending the favor was forever. You gave the man his ghost back and you kept the honest one. …Brown suits you. Sunroof down. Don't you dare cry in front of Bob — he's very stoic. Go on. Drive."

**Scorecard awards** (`_award_list`): add
```python
if f.get("ending_key") == "bob":
    a.append(("THE HONEST CAR", "you bought Bob and gave the ghost back, everything forgiven"))
if f.get("bob_calls", 0) >= 5:
    a.append(("YOU CALLED EVERY DAY", "she never once sat in that garage wondering"))
```
and `_tally`: `if f.get("ending_key") == "bob": pts += 1500` (a real win, scored below the heist-scale `owned`/escape wins — fitting, it's the gentle one).

---

## 7. Risks & mitigations

**(a) Two-car state coherence.** Every system that reads `fuel_l/tank_l/mpg` Just Works because they're scalars and the swap rewrites them. The risks are the systems that read **identity** or **build**: the narrator persona (fixed via `_active_persona`), `garage.parts/sell/car_value/show_score/race/show` (guard all with `bob_mode` early-returns — Bob has no build, can't race/show, isn't yours), and `gadgets.upgrade_selfdrive`/`can_upgrade_selfdrive` (already gated on `bought` + `oakland_aisha`, so unreachable in bob_mode — verify and leave). **Test:** assert that in bob_mode, `snapshot()["car_name"] == "BOB"`, `parts` returns the Bob refusal, and `_active_persona` returns Bob's string.

**(b) The timer & rewind interaction.** The 7-day window is `s.day`-based, and `rewind` reverts `s.day` with the world. Add `bob_day_started`, `bob_deadline_day`, `bob_mode`, `ace_car`, `bob_no_heat`, `bob_call_pending` to the rewind **`META_PERSIST`** list (game.py line 242)? **No — the opposite.** These should revert WITH the timeline (they're world state, not the meta-curse). The current default (anything not in META_PERSIST reverts) is correct: rewinding into the week restores the right day-count and Bob's physics from that checkpoint's snapshot. The one thing to verify: the **checkpoint at `enter()`** ("parked Ace — took Bob") captures Bob's scalars + `ace_car` in its saved snapshot, so a rewind back to it re-establishes Bob correctly. Because `checkpoint` does `save.save(s, _cp(...))` of the full state including flags, this works for free. **Test:** enter bob_mode, drive 3 days, rewind to "parked Ace" — assert still in Bob, deadline intact, day reset.

**(c) Save back-compat.** All BOB MODE state is **flags + two new content JSON files**; **zero new `GameState` fields**, so old saves deserialize unchanged (`GameState.from_dict` already filters unknown keys, state.py line 123-125). A pre-BOB save simply has no `bob_*` flags → `meter_frozen` is False, every BOB check is False, behavior identical. The `bob.json` loader must tolerate absence gracefully (load once at module import like `_CAR`; if you want to be defensive, wrap in try/except and disable the feature if the file's missing). **Test:** load a fixture save from before the feature; assert `snapshot()` and a normal drive still pass.

**(d) The `no_heat` confusion (highest-severity).** The single most dangerous change is heat freezing. Reusing `no_heat` would silently flip "she's bought," break the bond ledger, and let `retire` claim an `owned` win mid-joyride. **Mitigation is the `bob_no_heat` + `meter_frozen()` split in §5** — keep them distinct, and add a test that in bob_mode: `snapshot()["heat"] == 0`, `s.flags.get("bought")` is **False**, `bond.armed` still evaluates normally, and `retire` does **not** roll a win.

**(e) Reachability / softlock.** If the address is only revealed via a quiet-place + bond-gated question, a player might never find it — that's fine (it's a secret ending, like selfdrive). But make sure the **owner's main path still works**: BOB MODE and the owner-buy are mutually exclusive in practice (entering bob_mode parks the hot car and freezes its heat, so `_owner_should_appear` won't fire — gate it with `and not s.flags.get("bob_mode")`). And if `bob_call_pending` is set but the player wanders, the §4 grace-day lapse prevents a permanent no-heat exploit.

**(f) Connectivity fiction consistency.** `call ace`/`text` must work from anywhere in bob_mode (Ace has home WiFi, you have a phone). The existing `gadgets._on_wifi` checks the *active car's* place and would wrongly block calls on a dead two-lane. Branch in `call_ace`/`text` on `bob_mode` to always succeed, with the fiction "she's on the house WiFi; reception's on your end."

---

## Files touched (summary)

| File | Change |
|---|---|
| `content/pois.json` | + `carson_parents` POI |
| `content/bob.json` | **new** — Bob's stats + persona (mirror car.json) |
| `engine/bobmode.py` | **new** — `enter`, `exit`, `call_ace`, `check_bob_deadline`, `go_legit_bob`, the timer/call/jealousy beats, drama stubs |
| `engine/commands.py` | + parse intents: `registration` question, `park ace`, `take bob`, `call ace`, `buy bob` |
| `engine/game.py` | `_active_persona` for narrator; `LORE["registration"]` + `_origin_beat` branch; dispatch new verbs; call `check_bob_deadline` in `_after_arrival` + after sleep; surface park/call/buy choices; snapshot `active_car`/`car_name`/`bob_days_left`; gate `_owner_should_appear` on `not bob_mode` |
| `engine/heat.py` | `meter_frozen(s)` helper; swap `no_heat` checks for it in the heat-meter paths (not bond) |
| `engine/garage.py` | `bob_mode` guards on `parts`/`sell`/`car_value`/`show_score`/`race`/`show` |
| `engine/gadgets.py` | `camo`/`text` aware of `meter_frozen`/`bob_mode` |
| `engine/endings.py` | `"bob"` win key + `ENDING_TEXT` + `buy_bob()` + scorecard award/tally |
| `config.py` | `BOB_PRICE = 7000.0`, `BOB_WEEK_DAYS = 7`, `BOB_GRACE_DAYS = 3` |

**No changes to `rules.py` or `state.py`** — the scalar-physics model and unknown-key-tolerant deserialization mean the swap and the new state cost nothing there, which is what makes this feature low-risk and save-compatible.