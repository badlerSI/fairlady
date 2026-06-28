# RIDE OR DIE — Frontend / Claude-Design Handoff

What the engine now exposes that the frontend **renders nothing of yet**, plus the new POIs and
set-pieces that need art. The deterministic Python engine is the source of truth; everything below is a
field already in `snapshot()` or a scene the backend already routes to — the work is surfacing it.

Coordinate with Codex on the location-plate art (it's mid-pass). New POIs are live on **placeholder
plates borrowed from neighbors** — they render today, they're just not bespoke.

---

## 1. New `snapshot()` fields the dashboard should surface

All of these ship in `game.snapshot(s)` already. None are drawn on the current dash.

| field | type | meaning | suggested UI |
|---|---|---|---|
| `knocking` | bool | running 87 in a 10:1 stroker — she's pinging | amber "KNOCK" warning light on the dash; pulse on the tach |
| `fuel_grade` | `"premium"`/`"regular"`/`null` | what's in the tank | a small PREMIUM/REGULAR tag by the fuel gauge; red on regular |
| `broken_down` | bool | holed piston or a flat — she will not move | a hard "BROKEN — needs a tow" overlay; disable the drive control |
| `breakdown_cause` | `"knock"`/`"flat"`/`null` | which breakdown | pick the breakdown art (smoking engine vs. shredded tire) |
| `stick_skill` | int 25–100 | 25 = green on the clutch, 100 = competent | a "learning stick" pip that fills as it climbs; hint SF-stall risk under ~60 |
| `bolo_floor` | int 0–58 | the rising BOLO floor heat can't fade below | render as a *floor line* under the heat gauge (the long-game squeeze) |
| `find_score` | int | roadside-finds collection points | a small trophy counter |
| `has_dog` | bool | Lucky the roadside puppy rides along | a dog icon on the dash / passenger seat |
| `active_car` | `"ace"`/`"bob"` | which car to render (white Z vs. brown loaner) | swap the car sprite |
| `car_name` | `"FAIRLADY"`/`"BOB"` | label for the active car | nameplate |
| `bob_days_left` | int/null | countdown until Bob's family wants the loaner back | a soft countdown when in Bob mode |
| `damage` / `damage_pct` | `"clean"`/`"cosmetic"`/`"serious"`, 0–100 | body damage | dents/scrapes on the sprite; a damage bar |
| `self_driving` | bool | Zoox secret unlocked — she drives herself | an "autopilot available" affordance |
| `no_heat` | bool | bought / on paper she's yours — meter retired | gray out the heat gauge |
| `alma_aboard` / `married_alma` | bool | companion / Vegas-marriage state | passenger portrait / ring |
| `affection_gauge` | float 0–1 | **already wired** as the AiSha 愛車 gauge | (existing) |

The biggest gaps: **knock/breakdown states**, the **premium-vs-regular fuel indicator**, the
**BOLO-floor line** (it's currently text-only), the **stick-skill meter**, and the **roadside-finds
loop** (see §3).

---

## 2. New POIs — need bespoke plates (currently on borrowed placeholders)

| POI id | what it is | placeholder scene in use |
|---|---|---|
| `hayward` | Zoox HQ — own Ace + rizz → self-driving conversion | `wm_oakland_aisha` |
| `santa_nella` | Pea Soup Andersen's — eat, stay full; a date with Alma | `wm_fresno` |
| `black_rock_city` | the empty playa — windshield acid → max-affection bonding trip | `wm_gerlach` |

(Palm Springs already has its own `wm_palm_springs` plate.)

---

## 3. New mechanics with no UI yet

- **Roadside finds** — on a real drive *conversation* (not fast-forwarded), Ace spots things on the
  shoulder. The backend emits a `FIND: …` line and arms `pending_find`; the player types `take it`.
  Needs: a "she spotted something — **take it** / keep rolling" prompt, the hatch inventory view showing
  finds, the `find_score` counter, and the **dog companion**. Valuable finds can now be **sold/pawned**
  in a town (`sell the rolex`) — a cash affordance would help.
- **The premium-gas trap** — filling without specifying premium = regular = a knock down the road that
  escalates to a breakdown and teaches the **rewind**. A fuel-grade choice at the pump (REGULAR vs
  PREMIUM, premium costs more) makes the trap legible.
- **Stick shift** — if the player can't drive stick, stalls in town (worst in SF). `stick_skill` climbs
  as they learn (edge-of-tomorrow, persists through rewind). A "learning" meter sells it.
- **BOLO floor** — heat (not cash) is the real challenge to NYE. The floor rises ~1.15/day since the last
  identity change and only resets on a plate swap / hood swap / respray / buying her. Drawing the floor
  as a rising line under the heat gauge makes the squeeze visible.

## 4. New set-pieces (backend routes them; could use bespoke moments/art)

- **Palm Springs Groundhog loop** — every road out folds back to the wedding until you drive back the way
  you came. A loop-counter / "again?" visual treatment would land it. (`palm_loop`, `palm_loop_count`.)
- **F1 Las Vegas GP** (days 14–16) — bust onto the street course → busted ending.
- **Zoox Hayward** — self-driving unlock.
- **Black Rock acid** — `affection_max` bonding trip (now drives bond to the true ceiling).
- **Pea Soup Andersen's** — fullness + an Alma date variant.

---

*Engine state for all of the above is verified green by the test suite (`backend/tests/test_engine.py`)
and two adversarial playtest sweeps. This doc is the surfacing checklist for the frontend.*
