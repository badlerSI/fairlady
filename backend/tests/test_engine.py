"""Deterministic-core tests. Run network-free: FAIRLADY_ROUTING=offline, FAIRLADY_ADAPTER=stub."""
import os
os.environ.setdefault("FAIRLADY_ROUTING", "offline")
os.environ.setdefault("FAIRLADY_ADAPTER", "stub")

import pytest

from engine import game, world, rules, economy
from engine.state import GameState
from engine.commands import parse
from config import LITERS_PER_GALLON


def fresh():
    # favor already done — starts at the Chevron like the classic open (the prologue has its own tests)
    return game.new_game(seed=12345, prologue_on=False)


# ------------------------------------------------------------------ start state
def test_start_state():
    s = fresh()
    assert s.fuel_l == 5.0
    assert s.tank_l == 40.0
    assert s.place.poi_id == "sema_chevron"
    # a splash: about 26 miles of range
    assert 24 < s.range_mi < 28
    assert s.heat == rules.HEAT_START
    assert s.day == 1
    assert s.clock.strftime("%H:%M") == "17:37"


# ------------------------------------------------------------------ the trap
def test_zion_trap_warns_once_then_strands_the_stubborn():
    s = fresh()
    zion = world.get_poi("zion")
    evs = rules.drive(s, zion)                 # she does the math out loud first
    assert any("NAV" in e and "won't start" in e for e in evs)
    assert s.odometer_mi == 0.0 and s.status == "playing"
    rules.drive(s, zion)                       # say it again and she'll burn it anyway
    assert s.status == "stranded"
    assert s.fuel_l == 0.0
    assert "shoulder" in s.place.name.lower()


def test_full_tank_range_is_about_211_miles():
    s = fresh()
    rules.fuel(s, fill=True)              # card covers it
    assert abs(s.fuel_l - 40.0) < 0.05
    assert abs(s.range_mi - 211.3) < 1.5


# ------------------------------------------------------------------ fuel math
def test_buy_twenty_dollars_of_gas():
    s = fresh()
    price = economy.gas_price(s.place)    # 4.39 at the start station
    rules.fuel(s, dollars=20.0, prefer="cash")
    expected_l = (20.0 / price) * LITERS_PER_GALLON
    assert abs((s.fuel_l - 5.0) - expected_l) < 0.05
    assert abs(s.cash - (40.0 - 20.0)) < 0.05


def test_tank_clamps_at_40_liters():
    s = fresh()
    rules.fuel(s, dollars=500.0)          # way more than the tank holds
    assert s.fuel_l == 40.0
    # only charged for the ~35 L that fit
    fit_gal = (40.0 - 5.0) / LITERS_PER_GALLON
    assert abs(s.card_balance - fit_gal * economy.gas_price(s.place)) < 0.2


def test_cannot_overspend_credit():
    s = fresh()
    s.card_limit = 10.0
    s.card_balance = 0.0
    s.cash = 0.0
    rules.fuel(s, fill=True, prefer="card")
    assert s.card_balance <= 10.0 + 1e-6
    assert s.fuel_l < 40.0                 # money capped the fill


# ------------------------------------------------------------------ heat
def test_card_swipe_raises_heat_cash_does_not():
    s1 = fresh(); h0 = s1.heat
    rules.fuel(s1, dollars=10.0, prefer="card")
    assert s1.heat > h0                    # paper trail

    s2 = fresh()
    rules.fuel(s2, dollars=10.0, prefer="cash")
    assert s2.heat == rules.HEAT_START     # cash is clean


def test_state_line_cools_heat():
    s = fresh()
    s.place = world.get_poi("mesquite")    # NV
    s.fuel_l = 40.0
    s.heat = 50.0
    rules.drive(s, world.get_poi("st_george"))  # UT
    assert s.status == "playing"
    assert s.heat < 50.0 * rules.HEAT_STATELINE_MULT + 1.0


# ------------------------------------------------------------------ sleep
def test_sleep_advances_to_morning_and_costs():
    s = fresh()
    s.place = world.get_poi("mesquite")    # has lodging
    s.cash = 500.0
    before_cash = s.cash
    s.fatigue = 90.0
    evs = rules.sleep(s, kind="motel", prefer="cash")
    assert s.clock.strftime("%H:%M") == "07:30"
    assert s.day == 2
    assert s.fatigue == 0.0
    assert s.cash < before_cash            # paid for the room


def test_must_sleep_gate_blocks_driving_when_too_long_awake():
    s = fresh()
    s.fuel_l = 40.0
    # shove the clock ~21 hours past the last sleep
    s.last_sleep_iso = "2025-11-07T07:30:00"
    s.clock_iso = "2025-11-08T05:00:00"
    evs = rules.drive(s, world.get_poi("mesquite"))
    assert any("FATIGUE" in e for e in evs)
    assert s.odometer_mi == 0.0            # the drive was refused
    # after sleeping, the awake-clock resets and driving works again
    s.place = world.get_poi("mesquite"); s.cash = 500
    rules.sleep(s, kind="motel", prefer="cash")
    assert rules.hours_awake(s) < 1.0


def test_no_lodging_means_rough_night():
    s = fresh()                            # start station: gas only
    rules.sleep(s)
    assert s.clock.strftime("%H:%M") == "07:30"
    assert s.fatigue == 20.0               # half-rested


# ------------------------------------------------------------------ tow rescue
def _strand_at_zion(s):
    zion = world.get_poi("zion")
    rules.drive(s, zion)                       # the warning
    rules.drive(s, zion)                       # the insistence
    assert s.status == "stranded"


def test_tow_recovers_when_affordable():
    s = fresh()
    _strand_at_zion(s)
    s.cash = 0.0
    s.card_limit = 5000.0; s.card_balance = 0.0
    rules.tow(s, prefer="card")
    assert s.status == "playing"
    assert s.fuel_l == 2.0
    assert s.place.has("gas")
    assert s.heat > rules.HEAT_START       # tow + card = attention


def test_tow_fails_when_broke():
    s = fresh()
    _strand_at_zion(s)
    s.cash = 0.0; s.card_limit = 0.0; s.card_balance = 0.0
    rules.tow(s)
    assert s.status == "stranded"
    assert "BROKE" in (s.ending or "")


# ------------------------------------------------------------------ parser
@pytest.mark.parametrize("raw,verb", [
    ("drive to zion", "drive"),
    ("go to san francisco japantown", "drive"),
    ("fill", "fuel"),
    ("gas $20", "fuel"),
    ("gas 10 gal", "fuel"),
    ("sleep", "sleep"),
    ("pull over", "sleep"),
    ("pay cash", "pay"),
    ("talk", "talk"),
    ("map", "map"),
    ("nearby gas", "map"),
    ("look", "look"),
    ("how much gas do we have?", "say"),
])
def test_parse(raw, verb):
    assert parse(raw)[0] == verb


def test_parse_fuel_amounts():
    assert parse("gas $25")[1]["dollars"] == 25.0
    assert parse("gas 8 gallons")[1]["gallons"] == 8.0
    assert parse("fuel 30 L")[1]["liters"] == 30.0
    assert parse("drive to laguna seca fast")[1]["push"] is True


# ------------------------------------------------------------------ end-to-end via game.handle
def test_origin_questions_reveal_lore_and_destinations():
    s = fresh()
    res = game.handle(s, "where were you born?")
    assert "richmond" in res["scene"].lower() or "koinoya" in res["scene"].lower()
    assert "richmond_koinoya" in s.flags.get("revealed", [])
    assert any("richmond_koinoya" in c["cmd"] for c in res["choices"])
    res2 = game.handle(s, "where did you grow up")
    assert "oakland" in res2["scene"].lower()
    assert "oakland_aisha" in s.flags.get("revealed", [])
    # both lore POIs exist with bespoke scenes
    for pid, scene in (("richmond_koinoya", "koinoya"), ("oakland_aisha", "oakland_aisha")):
        poi = world.get_poi(pid)
        assert poi is not None and poi.scene == scene


def test_owner_lore_is_coy_and_storage_reveals_truth():
    s = fresh()
    res = game.handle(s, "who owned you before")
    low = res["scene"].lower()
    assert "mayumi" not in low and "earn it" in low          # coy — no name, no spoiler
    # the truth only comes out at the Livermore storage unit — and only after Long Beach
    s2 = fresh(); s2.fuel_l = 40.0; s2.cash = 3000.0; s2.place = world.get_poi("oakland_aisha")
    rv0 = game.handle(s2, "drive to livermore")
    assert not s2.flags.get("knows_truth")            # gated: Mayumi's tale comes first
    s2.flags["knows_mayumi"] = True
    s2.fuel_l = 40.0; s2.place = world.get_poi("oakland_aisha")
    rv = game.handle(s2, "drive to livermore")
    assert "mayumi" in rv["scene"].lower() and "storage" in rv["scene"].lower()
    assert s2.flags.get("knows_truth")
    # Long Beach unlocks the Mayumi tale once
    s3 = fresh(); s3.fuel_l = 40.0; s3.place = world.get_poi("oceanside")
    rb = game.handle(s3, "drive to long_beach")
    assert "mayumi" in rb["scene"].lower() and s3.flags.get("knows_mayumi")


def test_owner_lore_and_drive_home():
    s = fresh()
    res = game.handle(s, "who owned you before")
    assert "earn it" in res["scene"].lower() or "name" in res["scene"].lower()
    # drive her home → routes to the Oakland garage and sets home
    s2 = fresh(); s2.fuel_l = 40.0; s2.cash = 2000.0
    s2.place = world.get_poi("san_francisco")
    res2 = game.handle(s2, "drive her home")
    assert s2.flags.get("home") == "oakland_aisha"
    assert "oakland" in res2["snapshot"]["location"].lower()


def test_state_welcome_fires_once_per_state():
    s = fresh(); s.fuel_l = 40.0; s.cash = 500.0
    s.place = world.get_poi("mesquite")          # NV (already seen at start)
    r1 = game.handle(s, "drive to st_george")    # cross into UT
    assert r1["welcome"] and "UTAH" in r1["welcome"]
    s.fuel_l = 40.0
    r2 = game.handle(s, "drive to cedar_city")   # still UT
    assert not r2["welcome"]                      # only once per state


def test_drama_eventually_fires_and_owner_reveals():
    from engine import drama
    s = fresh(); s.heat = 50.0; s.odometer_mi = 800.0   # push the odds
    fired = []
    for k in range(40):
        s.turn += 1
        ev = drama.maybe_event(s)
        if ev:
            fired.append(ev["id"])
    assert fired, "drama should fire over many drives"
    assert all("lines" in drama._e_overheat(fresh(), __import__('random').Random(1)) for _ in [0])


def test_limp_makes_her_thirstier_then_clears():
    s = fresh(); s.fuel_l = 40.0; s.flags["limp"] = True
    before = s.fuel_l
    rules.drive(s, world.get_poi("mesquite"))
    burned_limp = before - s.fuel_l
    s2 = fresh(); s2.fuel_l = 40.0
    rules.drive(s2, world.get_poi("mesquite"))
    burned_norm = 40.0 - s2.fuel_l
    assert burned_limp > burned_norm                 # 25% thirstier while limping
    # fueling at a town clears the gremlin
    s.flags["limp"] = True; s.place = world.get_poi("mesquite")
    rules.fuel(s, dollars=20)
    assert not s.flags.get("limp")


def test_handle_drive_and_snapshot():
    s = fresh()
    res = game.handle(s, "fill")
    assert res["snapshot"]["fuel_l"] == 40.0
    assert isinstance(res["scene"], str) and res["scene"]
    res2 = game.handle(s, "drive to mesquite")
    assert res2["snapshot"]["odometer_mi"] > 0
    assert res2["status"] == "playing"


# ------------------------------------------------------------------ the favor (prologue)
def test_prologue_favor_ladder_asks_at_five_then_gets_pushier():
    s = game.new_game(seed=7)
    assert s.place.poi_id == "sema_north_hall"
    for chat in ("nice paint", "busy week here", "long day huh", "the strip is loud"):
        game.handle(s, chat)
    assert s.flags["prologue"]["asked"] == 0          # four turns of small talk: no ask yet
    game.handle(s, "so anyway")                       # turn five — the ask lands
    assert s.flags["prologue"]["asked"] == 1
    game.handle(s, "hmm, not so certain about that")  # she pushes
    assert s.flags["prologue"]["asked"] == 2
    r = game.handle(s, "alright, deal")               # agreement → the favor drive
    assert s.flags.get("prologue_done") and "prologue" not in s.flags
    assert s.place.poi_id == "sema_chevron"           # down the block
    assert r["welcome"] and "RIDE OR DIE" in r["welcome"]   # the title drop


def test_prologue_spec_questions_shorten_the_ask_and_earn_riz():
    s = game.new_game(seed=7)
    game.handle(s, "how much torque do you make?")
    assert s.flags["prologue"]["rapport"] is True
    assert s.riz >= 5                                  # she liked you first
    game.handle(s, "what engine is under the hood?")
    game.handle(s, "tell me about the suspension")     # third coherent question
    assert s.flags["prologue"]["asked"] >= 1           # gearheads get the 3-turn favor


def test_prologue_refuses_a_joyride_before_the_pact():
    s = game.new_game(seed=7)
    r = game.handle(s, "drive to zion")
    assert s.place.poi_id == "sema_north_hall"         # she won't turn over
    assert any("IGNITION" in e for e in r["events"])


def test_favor_completes_on_the_fill_at_the_chevron():
    s = game.new_game(seed=7)
    for chat in ("a", "b", "c", "d", "e"):
        game.handle(s, f"some chatter {chat}")
    r = game.handle(s, "okay let's do it")
    assert s.place.poi_id == "sema_chevron"
    r2 = game.handle(s, "fill")
    assert s.flags.get("favor_filled")
    assert any("FAVOR" in e for e in r2["events"])


# ------------------------------------------------------------------ checkpoints + rewind
def test_rewind_restores_last_checkpoint_and_riz_survives():
    s = fresh()
    s.riz = 10.0
    s.fuel_l = 40.0
    game.handle(s, "drive to mesquite")                # arrival → checkpoint
    assert s.place.poi_id == "mesquite"
    cash_at_chk = s.cash
    s.cash = 0.0                                       # ruin everything
    s.heat = 95.0
    game.handle(s, "rewind")
    assert s.place.poi_id == "mesquite"                # back at the checkpoint
    assert s.cash == cash_at_chk
    assert s.riz == 8.0                                # 10 carried over, minus the rewind cost
    assert s.flags.get("rewinds") == 1


def test_double_rewind_reaches_one_checkpoint_deeper():
    s = fresh()                                        # new_game checkpointed the Chevron
    s.fuel_l = 40.0
    game.handle(s, "drive to mesquite")                # chk1=mesquite, chk2=chevron
    game.handle(s, "rewind")
    assert s.place.poi_id == "mesquite"
    game.handle(s, "rewind")                           # consecutive → one deeper
    assert s.place.poi_id == "sema_chevron"


def test_rewind_escapes_an_ending():
    s = fresh()
    s.fuel_l = 40.0
    game.handle(s, "drive to mesquite")                # checkpoint at mesquite
    rules.set_ending(s, "busted")
    r = game.handle(s, "rewind")
    assert s.status == "playing"
    assert s.place.poi_id == "mesquite"
    assert any(c["cmd"] == "rewind" for c in game.choices(fresh_busted()))  # endings offer it


def fresh_busted():
    s = fresh()
    rules.set_ending(s, "busted")
    return s


# ------------------------------------------------------------------ the traffic stop
def test_suave_pitch_talks_the_cop_into_a_wave_off():
    from engine import encounters
    s = fresh(); s.fuel_l = 40.0; s.heat = 30.0
    encounters.start_stop(s, "plate")
    r1 = game.handle(s, "Evening officer, sorry — I left my wallet at the SEMA show. "
                        "This is the show car, on a transport run to the lot.")
    assert encounters.stop_active(s)                   # one more answer decides it
    riz0 = s.riz
    r2 = game.handle(s, "Of course, absolutely — it's the SEMA display build, 250 lb-ft "
                        "of torque. Happy to pop the hood if you're curious.")
    assert not encounters.stop_active(s)
    assert s.status == "playing"
    assert s.riz > riz0                                # the wave-off pays style
    assert s.heat < 30.0


def test_running_from_a_stop_ends_the_trip():
    from engine import encounters
    s = fresh(); s.fuel_l = 40.0
    encounters.start_stop(s, "plate")
    game.handle(s, "floor it, go go go")
    assert s.status == "busted"


def test_stop_blocks_everything_but_talk():
    from engine import encounters
    s = fresh(); s.fuel_l = 40.0
    encounters.start_stop(s, "plate")
    r = game.handle(s, "drive to mesquite")
    assert s.place.poi_id == "sema_chevron"            # going nowhere
    assert encounters.stop_active(s)                   # and the stop is still open


# ------------------------------------------------------------------ the owner
def _owner_ready():
    s = fresh()
    s.fuel_l = 40.0; s.cash = 3000.0
    s.clock_iso = "2025-11-10T10:00:00"; s.day = 4     # he's had time
    s.last_sleep_iso = "2025-11-10T07:30:00"
    s.flags["card_swipes"] = 3                         # ...and a trail
    s.place = world.get_poi("tonopah")
    return s


def test_owner_comes_looking_and_a_true_answer_earns_the_blessing():
    from engine import encounters
    s = _owner_ready()
    s.flags["knows_mayumi"] = True
    r = game.handle(s, "drive to ely")                 # a city arrival → he's waiting
    assert s.flags.get("owner_met") and encounters.owner_active(s)
    game.handle(s, "I love her, and I promised to keep her safe — she chose me. "
                   "The favor was her idea.")
    r2 = game.handle(s, "I know about Mayumi and the 580. I'm not driving a replacement "
                        "— I love this car, the one you built.")
    assert not encounters.owner_active(s)
    assert s.flags.get("report_withdrawn")             # he made the call
    assert s.riz >= 15
    assert s.status == "playing"


def test_owner_takes_her_back_on_a_failed_answer_and_rewind_undoes_it():
    from engine import encounters
    s = _owner_ready()
    game.handle(s, "drive to ely")
    assert encounters.owner_active(s)
    game.handle(s, "um well")
    game.handle(s, "uh I dunno")
    assert s.status == "taken"
    game.handle(s, "rewind")                           # Edge of Tomorrow
    assert s.status == "playing"


# ------------------------------------------------------------------ range + berlin + parser
def test_range_question_lists_what_the_tank_can_reach():
    s = fresh()                                        # 5 L ≈ 26 mi
    r = game.handle(s, "where can we get to on this tank?")
    assert "ON THIS TANK" in r["info"]
    assert "Las Vegas" in r["info"]                    # the strip is in reach even on fumes
    assert "WITH A FULL TANK" in r["info"]             # the far edge, after a fill
    assert "Cedar City" in r["info"] or "St. George" in r["info"]   # a real far destination shows


def test_berlin_nv_exists_and_tells_its_story():
    p = world.get_poi("berlin_nv")
    assert p is not None and p.region == "NV" and p.kind == "park"
    s = fresh(); s.fuel_l = 40.0
    s.place = world.get_poi("tonopah")
    r = game.handle(s, "drive to berlin_nv")
    assert s.flags.get("seen_berlin")
    assert "ichthyosaur" in r["scene"].lower()


@pytest.mark.parametrize("raw,verb", [
    ("rewind", "rewind"),
    ("go back", "rewind"),
    ("how far can we go on one tank", "range"),
    ("where can we get to on this tank?", "range"),
    ("where can we get gas", "map"),
    ("how much torque do you make?", "say"),
])
def test_parse_new_verbs(raw, verb):
    assert parse(raw)[0] == verb


def test_riz_is_in_the_snapshot():
    s = fresh(); s.riz = 12.4
    assert game.snapshot(s)["riz"] == 12


# ------------------------------------------------------------------ playtest-wave regressions
def test_drive_me_home_routes_home():
    assert parse("drive me home")[0] == "home"
    assert parse("drive me to zion") == ("drive", {"dest": "zion", "push": False})
    s = fresh(); s.fuel_l = 40.0
    s.place = world.get_poi("livermore")       # ~35 mi out — inside one tank
    r = game.handle(s, "drive me home")
    assert s.flags.get("home") == "oakland_aisha"
    assert "oakland" in r["snapshot"]["location"].lower()


def test_special_is_not_spec_talk():
    from engine.commands import is_spec_question, spec_hits
    assert spec_hits("she's special, with all due respect — on camera, no different") == 0
    assert is_spec_question("how much torque does she make?")
    assert not is_spec_question("is she special?")
    # plurals/possessives of real build words count (found by self-playtest)
    assert is_spec_question("triple Mikunis?")
    assert is_spec_question("what carbs is she running?")
    assert spec_hits("stroked L24 on triple webers") >= 2


def test_agreeing_as_she_asks_does_not_need_a_second_yes():
    # pre-empting her ask on the very turn she'd ask should seal it (self-playtest finding)
    s = game.new_game(seed=44)
    for chat in ("nice booth", "long week?", "you're the cleanest one here", "love the stance"):
        game.handle(s, chat)                       # 4 turns of small talk — she asks on turn 5
    r = game.handle(s, "you had me at the build — let's get you that gas")
    assert s.flags.get("prologue_done") and "prologue" not in s.flags
    assert s.place.poi_id == "sema_chevron"        # one yes, not two


def test_owner_middle_tier_is_reachable():
    from engine import encounters
    s = fresh()
    encounters.start_owner(s)
    encounters.owner_turn(s, "sir, i'm taking good care of her, i promise. she's a great car "
                             "and we're just out for a drive.")
    encounters.owner_turn(s, "because she's special. i like her, i like driving her. "
                             "that's all, really.")
    assert s.flags.get("owner_deadline_day")   # warm-but-generic earns the week, not the blessing
    assert not s.flags.get("report_withdrawn")
    assert s.status == "playing"


def test_rewind_does_not_bank_undone_riz():
    s = fresh()
    s.riz = 5.0
    s.fuel_l = 40.0
    game.handle(s, "drive to mesquite")        # checkpoint at riz 5
    s.riz = 20.0                               # earned in a timeline about to unhappen
    game.handle(s, "rewind")
    assert s.riz == 3.0                        # chk riz 5 − fee 2; the +15 never happened


def test_stop_escalation_and_diminishing_riz():
    from engine import encounters
    pitch = ("Evening officer, sorry — left my wallet at the SEMA show. This is the show car "
             "on a transport run, 250 lb-ft of torque, happy to pop the hood.")
    s = fresh(); s.fuel_l = 40.0; s.heat = 30.0
    encounters.start_stop(s, "plate")
    game.handle(s, pitch); game.handle(s, pitch)
    riz1 = s.riz
    assert s.flags.get("stops_survived") == 1
    encounters.start_stop(s, "plate")
    game.handle(s, pitch); game.handle(s, pitch)
    assert s.riz - riz1 < riz1                 # the same trick pays less the second time


def test_meta_verbs_cannot_hijack_an_encounter():
    from engine import encounters
    s = fresh(); s.fuel_l = 40.0
    encounters.start_stop(s, "plate")
    r = game.handle(s, "I filled her tank where she asked, officer — that's the whole story.")
    assert encounters.stop_active(s)           # the words reached the officer…
    assert r["info"] is None                   # …not the range calculator
    assert s.flags["stop"]["round"] == 1


def test_look_prints_the_ledger():
    s = fresh()
    r = game.handle(s, "look")
    assert r["info"] and "FUEL" in r["info"] and "HEAT" in r["info"] and "RIZ" in r["info"]


def test_unknown_destination_gets_a_real_answer():
    s = fresh()
    r = game.handle(s, "drive to atlantis")
    assert any("NAV" in e for e in r["events"])


def test_homestretch_does_not_need_the_home_flag():
    from engine import drama
    s = fresh(); s.place = world.get_poi("livermore")
    assert drama._miles_home(s) is not None and drama._miles_home(s) < 70


def test_story_beats_fire_on_tow_arrivals():
    s = fresh()
    lb = world.get_poi("long_beach")
    s.place = type(lb)(name="the shoulder near Long Beach", lat=lb.lat + 0.05, lon=lb.lon,
                       region="CA", kind="spot")
    s.fuel_l = 0.0; s.cash = 1000.0
    rules.set_ending(s, "stranded")
    r = game.handle(s, "tow")
    if s.place.poi_id == "long_beach":         # nearest pump is the story town itself
        assert s.flags.get("knows_mayumi")
        assert "mayumi" in r["scene"].lower()


def test_promises_are_keepable_at_quiet_places():
    s = fresh(); s.fuel_l = 40.0
    # the name, somewhere quiet
    s.place = world.get_poi("berlin_nv")
    r = game.handle(s, "who owned you before?")
    assert "mayumi" in r["scene"].lower() and s.flags.get("knows_name")
    assert not s.flags.get("knows_mayumi")     # the name is not the story — Long Beach still gates
    # the Car Week morning, after Monterey
    s.flags["seen_monterey"] = True
    r2 = game.handle(s, "tell me about that morning at car week")
    assert s.flags.get("knows_morning") and "understudy" in r2["scene"].lower()


def test_cash_fallback_announces_itself():
    s = fresh()
    s.cash = 5.0; s.pay_method = "cash"
    s.place = world.get_poi("mesquite")
    evs = rules.sleep(s, kind="camp")
    assert any("PAY: cash came up short" in e for e in evs)


# ------------------------------------------------------------------ the garage economy
def _at_town(seed=909, cash=0.0):
    s = game.new_game(seed=seed, prologue_on=False)
    s.place = world.get_poi("mesquite"); s.cash = cash
    return s


@pytest.mark.parametrize("raw,verb", [
    ("i have $300 cash", "claim"), ("i'm broke", "claim"), ("withdraw $2000", "atm"),
    ("explore", "explore"), ("check the glovebox", "explore"), ("sell the carbon hood", "sell"),
    ("parts", "parts"), ("race", "race"), ("show her", "show"), ("buy her", "buy"),
    ("offer $5000", "buy"), ("name your price", "buy"),
])
def test_parse_garage_verbs(raw, verb):
    assert parse(raw)[0] == verb


def test_money_extraction():
    from engine.commands import _money
    assert _money("withdraw $2,000") == 2000.0
    assert _money("i have 5 grand") == 5000.0
    assert _money("offer 3k for her") == 3000.0
    assert _money("nothing here") is None


def test_claim_cap_and_broke_then_glovebox():
    s = _at_town()
    game.handle(s, "i have $50000 cash")
    from config import CASH_CLAIM_CAP
    assert s.cash == CASH_CLAIM_CAP                 # "any reasonable amount" — capped
    s2 = _at_town()
    game.handle(s2, "i'm broke")
    assert s2.cash == 0.0
    r = game.handle(s2, "explore")
    assert s2.cash == 500.0 and "glovebox" not in s2.flags or s2.flags.get("glovebox_found")
    assert any("500" in e for e in r["events"])
    r2 = game.handle(s2, "explore")               # only once
    assert s2.cash == 500.0


def test_atm_under_10k_and_camera_heat():
    s = _at_town()
    h0 = s.heat
    game.handle(s, "withdraw $4000")
    assert s.cash == 4000.0 and s.heat > h0
    game.handle(s, "withdraw $99999")             # clamps to the account ceiling
    from config import ATM_ACCOUNT_LIMIT
    assert abs(s.cash - ATM_ACCOUNT_LIMIT) < 1.0
    r = game.handle(s, "withdraw $100")
    assert "tapped" in r["events"][0]


def test_sell_part_pays_strips_value_and_changes_her():
    from engine import garage
    s = _at_town()
    v0 = garage.car_value(s); show0 = garage.show_score(s); mpg0 = s.mpg
    r = game.handle(s, "sell the carbon hood")
    assert s.cash == 1800.0
    assert garage.car_value(s) < v0 and garage.show_score(s) < show0
    assert s.mpg < mpg0                             # steel hood is heavier
    assert "hood" in garage.sold(s)
    game.handle(s, "sell the mikunis"); game.handle(s, "sell the wheels")
    assert garage.is_stripped(s)


def test_buy_the_car_is_the_good_ending():
    from engine import encounters
    s = game.new_game(seed=44, prologue_on=False)
    s.flags["owner_met"] = True; s.flags["knows_mayumi"] = True; s.riz = 25
    s.fuel_l = 40.0; s.cash = 9000.0
    s.place = world.get_poi("livermore")            # ~35 mi out — one tank
    game.handle(s, "drive to oakland_aisha")        # he's waiting at the garage
    assert encounters.owner_active(s)
    price = encounters.owner_price(s)
    assert price == 2000                            # 6000 − Mayumi 2500 − riz 1500, floored
    r = game.handle(s, "buy her")
    assert s.flags.get("bought") and s.flags.get("no_heat")
    assert s.cash == 9000.0 - price
    assert r["welcome"] and "YOURS" in r["welcome"]
    assert game.snapshot(s)["heat"] == 0
    # no_heat is permanent
    s.heat = 90.0; rules._clamp_heat(s)
    assert s.heat == 0.0


def test_buy_when_broke_names_the_price_and_waits():
    from engine import encounters
    s = game.new_game(seed=8, prologue_on=False)
    s.flags["owner_met"] = True; s.fuel_l = 40.0; s.cash = 100.0
    s.place = world.get_poi("livermore")
    game.handle(s, "drive to oakland_aisha")
    assert encounters.owner_active(s)               # he's at the garage to deal
    r = game.handle(s, "buy her")
    assert not s.flags.get("bought")
    assert any("AiSha" in e or "Oakland" in e for e in r["events"])
    assert not encounters.owner_active(s)           # he closes and waits


def test_race_and_show_require_ownership_then_reward():
    s = _at_town(cash=0.0)
    s.place = world.get_poi("laguna_seca")
    assert any("title" in e.lower() or "missing" in e.lower()
               for e in game.handle(s, "race")["events"])
    s.flags["bought"] = True
    r = game.handle(s, "race")
    assert "RACE:" in r["events"][0] and s.place.kind == "track"
    s.place = world.get_poi("petersen")             # a museum show field
    r2 = game.handle(s, "show")
    assert "SHOW:" in r2["events"][0]


# ------------------------------------------------------------------ economy playtest-wave fixes
def test_bare_buy_parses_but_deal_stays_prologue_word():
    assert parse("buy")[0] == "buy"
    assert parse("buy her")[0] == "buy"
    assert parse("deal")[0] == "say"          # 'deal' must stay the prologue agreement, not buy


def test_claim_is_a_one_time_wallet_not_a_faucet():
    s = _at_town(cash=0.0)
    game.handle(s, "i have $3000 cash")
    assert s.cash == 3000.0
    s.cash = 200.0                            # you spent it down
    r = game.handle(s, "i have $3000 cash")   # re-claiming must NOT refill
    assert s.cash == 200.0
    assert "already told me" in r["events"][0]


def test_glovebox_only_pays_the_broke():
    rich = _at_town(cash=2000.0)
    game.handle(rich, "explore")
    assert rich.cash == 2000.0                # not broke → no stash
    broke = _at_town(cash=0.0)
    game.handle(broke, "explore")
    assert broke.cash == 500.0


def test_race_costs_time_and_fuel_and_pays_once_per_track():
    s = _at_town(); s.flags["bought"] = True; s.fuel_l = 40.0
    s.place = world.get_poi("laguna_seca")
    clock0, fuel0, riz0 = s.clock, s.fuel_l, s.riz
    game.handle(s, "race")
    assert s.fuel_l < fuel0 and s.clock > clock0    # a session burns fuel + time
    riz1 = s.riz
    r = game.handle(s, "race")                        # repeat at the same track — no new purse
    assert s.riz == riz1 and "one-time" in r["events"][0]


def test_show_pays_once_per_venue():
    s = _at_town(); s.flags["bought"] = True
    s.place = world.get_poi("petersen")
    game.handle(s, "show"); riz1 = s.riz
    r = game.handle(s, "show")
    assert s.riz == riz1 and "already" in r["events"][0].lower()


def test_stripping_raises_the_owner_price_so_chopping_to_fund_is_a_loss():
    from engine import encounters
    s = _at_town(); s.flags["knows_mayumi"] = True; s.riz = 25
    base = encounters.owner_price(s)                  # 2000 (floored, full discount)
    game.handle(s, "sell the wheels")                 # +$2400 cash...
    assert encounters.owner_price(s) >= base + 4000   # ...but ~+$4800 to his price — a losing trade


def test_going_legit_clears_the_gun():
    from engine import garage
    s = _at_town()
    s.flags["gun"] = True; s.flags["wanted_armed"] = True; s.flags["desperado"] = True
    garage.go_legit(s)
    assert not s.flags.get("gun") and not s.flags.get("wanted_armed") and not s.flags.get("desperado")


def test_a_long_pitch_during_an_encounter_is_speech_not_a_command():
    from engine import encounters
    s = _at_town(); encounters.start_owner(s)
    # this sentence contains 'drive her home' but must reach him as a pitch, not parse as movement
    r = game.handle(s, "I'm the one who'll actually drive her home and put back every part I pulled")
    assert encounters.owner_active(s)
    assert s.flags["owner_scene"]["round"] == 1       # it was scored as an answer
    assert any("OWNER" in e for e in r["events"])


# ------------------------------------------------------------------ heat-as-credit-score
def test_visibility_classification():
    from engine import heat
    assert heat.visibility(world.get_poi("las_vegas")) == 3       # flashy
    assert heat.visibility(world.get_poi("berlin_nv")) == 0       # remote
    assert heat.visibility(world.get_poi("mesquite")) == 1        # low-key town


def test_heat_changes_are_logged_as_factors_with_a_dashboard():
    s = fresh(); s.fuel_l = 10.0; s.cash = 20.0                    # pay_method card by default
    game.handle(s, "fill")                                         # a card-swipe mark
    info = game.handle(s, "heat report")["info"]
    assert "HEAT REPORT" in info and "DEROGATORY MARKS" in info
    assert "credit card swipe" in info and "fades in" in info      # attribution + expiry
    assert any(b in info for b in ("GHOST", "NOTICED", "TRENDING", "FLAGGED"))   # a readable band
    assert "WHAT IF" in info                                       # the simulator


def test_card_swipe_is_a_derogatory_mark_cash_is_clean():
    s = fresh(); s.place = world.get_poi("mesquite"); s.cash = 200.0; s.fuel_l = 5.0
    h0 = s.heat
    game.handle(s, "pay cash"); game.handle(s, "gas $20")          # partial fill, cash
    assert s.heat == h0                                            # cash leaves no mark
    game.handle(s, "pay card"); game.handle(s, "gas $20")          # partial fill, card
    assert s.heat > h0                                             # the card does
    assert any("credit card swipe" in e["r"] for e in s.flags.get("heat_log", []))


def test_instagram_tag_only_fires_where_visible_and_is_dodgeable():
    from engine import heat
    # never at a remote spot, no matter the roll
    for seed in range(30):
        s = game.new_game(seed=seed, prologue_on=False)
        s.place = world.get_poi("berlin_nv"); s.turn += 5
        assert heat.social_arrival(s) is None                     # zero exposure → no tag, ever
    # at a flashy spot, a tag eventually fires across seeds and spikes heat as a hard inquiry
    tagged = False
    for seed in range(40):
        s = game.new_game(seed=seed, prologue_on=False)
        s.place = world.get_poi("las_vegas"); s.turn += 5; s.flags.pop("last_tag_turn", None)
        out = heat.social_arrival(s)
        if out and out.get("tagged"):
            tagged = True
            assert s.flags.get("instagram_tags") == 1
            assert any("tagged by @" in e["r"] and e["k"] == "spike" for e in s.flags["heat_log"])
            break
    assert tagged


def test_untag_and_lie_low_are_active_ways_down():
    from engine import heat
    s = fresh()
    heat.add(s, 20, "tagged by @someone", "spike"); s.flags["instagram_tags"] = 1
    s.flags["last_tag_turn"] = s.turn
    h0 = s.heat
    game.handle(s, "untag")
    assert s.heat < h0                                             # damage control claws some back
    # lie low cools at a quiet spot, refuses in plain sight
    s.place = world.get_poi("las_vegas")
    assert "can't disappear" in game.handle(s, "lie low")["events"][0]
    s.place = world.get_poi("berlin_nv"); h1 = s.heat
    game.handle(s, "lie low")
    assert s.heat < h1


def test_airbnb_is_clean_rest_motel_on_card_is_a_mark():
    s = fresh(); s.place = world.get_poi("mesquite"); s.cash = 400.0; s.heat = 30.0
    game.handle(s, "book an airbnb")
    assert s.heat < 30.0                                           # cools, off the record
    assert not any("front desk" in e["r"] for e in s.flags.get("heat_log", []))
    assert s.flags.get("card_swipes", 0) == 0                      # no paper trail


def test_curious_clerk_humble_slides_by_showoff_posts():
    from engine import heat
    seed = None
    for sd in range(1, 40):
        s = game.new_game(seed=sd, prologue_on=False); s.cash = 400; s.fuel_l = 8.0
        s.place = world.get_poi("las_vegas"); s.turn += 9
        game.handle(s, "fill")
        if s.flags.get("clerk_curious"):
            seed = sd; break
    assert seed is not None                                        # the clerk fires at a flashy pump
    h0 = s.heat
    game.handle(s, "ha, just an old project car")                 # humble
    assert s.heat == h0 and not s.flags.get("clerk_curious")
    s2 = game.new_game(seed=seed, prologue_on=False); s2.cash = 400; s2.fuel_l = 8.0
    s2.place = world.get_poi("las_vegas"); s2.turn += 9
    game.handle(s2, "fill")
    game.handle(s2, "yeah it's the SEMA car, take a pic")          # show off
    assert s2.heat > h0 and s2.flags.get("instagram_tags")


# ------------------------------------------------------------------ beta-test (my own playthroughs)
def test_atm_parses_from_natural_phrasing():
    assert parse("let me hit the ATM for $5000") == ("atm", {"amount": 5000.0})
    assert parse("I'll grab $2000 from an atm")[0] == "atm"
    assert parse("withdraw 3 grand")[0] == "atm"
    assert parse("i have $300 cash")[0] == "claim"     # still a claim, not an ATM


def test_explicit_yes_seals_the_favor_early():
    s = game.new_game(seed=7)
    game.handle(s, "how much torque?")                  # turn 1, rapport
    r = game.handle(s, "nice, let's go fill you up")     # an eager yes on turn 2 — must land now
    assert s.flags.get("prologue_done") and s.place.poi_id == "sema_chevron"
    assert r["welcome"] and "RIDE OR DIE" in r["welcome"]


def test_drawing_on_a_cop_makes_future_stops_harder():
    from engine import encounters
    pitch = ("Evening officer, sorry — wallet's at the SEMA show. It's the show car on a transport "
             "run, 250 lb-ft of torque, happy to pop the hood.")
    # same strong pitch: a clean driver waves off; a gun-puller does not
    clean = fresh(); clean.fuel_l = 40.0; clean.heat = 30.0
    encounters.start_stop(clean, "plate")
    game.handle(clean, pitch); game.handle(clean, pitch)
    waved = clean.status == "playing" and clean.flags.get("stops_survived")
    armed = fresh(); armed.fuel_l = 40.0; armed.heat = 30.0; armed.flags["wanted_armed"] = True
    opener = encounters.start_stop(armed, "plate")      # the opener warns they come ready
    assert any("holster" in e for e in opener)
    game.handle(armed, pitch); game.handle(armed, pitch)
    assert waved                                         # the clean run got the wave-off
    assert armed.riz <= clean.riz                        # the armed run did strictly worse


def test_sell_failure_does_not_play_the_success_line():
    s = fresh()
    s.place = world.get_poi("area51_gate")              # no shop out here
    r = game.handle(s, "sell the seats")
    assert any("no one out here" in e.lower() for e in r["events"])
    assert "won't sing" not in (r["scene"] or "")       # the sell-success flavor must not fire


# ------------------------------------------------------------------ the gazetteer layer
def test_gazetteer_towns_are_valid_and_beats_fire_once():
    from config import REGION_BBOX
    import json as _json
    from config import CONTENT_DIR
    data = _json.loads((CONTENT_DIR / "pois.json").read_text())
    towns = [p for p in data["pois"] if p.get("beat")]
    assert len(towns) >= 100                       # the four states are populated now
    for p in towns:                                # every entry is sane
        assert p["region"] in ("NV", "CA", "AZ", "UT")
        assert REGION_BBOX["min_lat"] <= p["lat"] <= REGION_BBOX["max_lat"]
        assert REGION_BBOX["min_lon"] <= p["lon"] <= REGION_BBOX["max_lon"]
        assert 40 < len(p["beat"]) < 520
    # a beat fires verbatim on first arrival, once
    s = fresh(); s.fuel_l = 40.0
    s.place = world.get_poi("tonopah")
    r = game.handle(s, "drive to mina_nv")
    assert "left a light on" in r["scene"]         # the judged Mina beat, verbatim
    assert "mina_nv" in s.flags.get("beats_seen", [])
    s.fuel_l = 40.0; s.place = world.get_poi("tonopah")
    r2 = game.handle(s, "drive to mina_nv")
    assert "left a light on" not in (r2["scene"] or "")   # told once


def test_wm_scene_files_exist_for_scene_refs():
    import json as _json
    from config import CONTENT_DIR, PROJECT_DIR
    data = _json.loads((CONTENT_DIR / "pois.json").read_text())
    wm = [p for p in data["pois"] if (p.get("scene") or "").startswith("wm_")]
    assert len(wm) >= 150
    for p in wm:
        f = PROJECT_DIR / "frontend" / "scenes_wm" / (p["scene"][3:] + ".png")
        assert f.exists(), f"missing sketch for {p['id']}"


def test_wiki_fact_is_silent_offline():
    assert world.wiki_fact(36.1, -115.1) is None   # ROUTING=offline in tests


# ------------------------------------------------------------------ Desperado Mode
def _armed_setup(seed=555):
    """At a gas+lodging town, full tank, paid cash — 'do it right'."""
    s = game.new_game(seed=seed, prologue_on=False)
    s.place = world.get_poi("mesquite")
    s.cash = 300.0
    game.handle(s, "fill cash")
    assert s.fuel_l >= s.tank_l - 0.5 and s.flags.get("last_fuel_cash")
    return s


def test_aggression_at_a_pump_opens_the_standoff():
    from engine import encounters
    assert encounters.gas_aggression("give me everything in the register") >= 2
    assert encounters.gas_aggression("nice night, fill it up please") == 0
    s = _armed_setup()
    r = game.handle(s, "empty the register or else")
    assert encounters.standoff_active(s)
    assert any("STANDOFF" in e for e in r["events"])
    # mid-standoff you can't just drive off
    r2 = game.handle(s, "drive to st_george")
    assert s.place.poi_id == "mesquite" and encounters.standoff_active(s)


def test_disarm_needs_full_tank_and_cash():
    from engine import encounters
    s = _armed_setup()
    s.fuel_l = 10.0                              # not full → not set up
    game.handle(s, "this is a holdup")
    r = game.handle(s, "disarm")
    assert s.status == "busted"
    assert s.flags.get("desperado_tries") is None   # a not-set-up grab doesn't count toward the 3
    assert "before you're ready" in r["events"][0]


def test_desperado_unlocks_on_the_third_setup_right_disarm():
    from engine import encounters
    s = _armed_setup()
    for n in (1, 2):                            # the two cursed failures
        game.handle(s, "give me the cash, now")
        game.handle(s, "disarm")
        assert s.status == "busted" and s.flags.get("desperado_tries") == n
        game.handle(s, "rewind")
        assert s.status == "playing"
        assert s.fuel_l >= s.tank_l - 0.5 and s.flags.get("last_fuel_cash")  # setup restored
        assert s.flags.get("desperado_tries") == n                          # curse persists
    game.handle(s, "this is a holdup, empty the register")
    r = game.handle(s, "disarm")
    assert s.flags.get("desperado") and s.flags.get("gun")
    assert s.riz >= 20 and s.heat >= 35
    assert "armed" in (r["scene"] or "").lower() or "DESPERADO" in " ".join(r["events"])


def test_desperado_heat_floor_and_survives_rewind():
    s = _armed_setup()
    s.flags["desperado"] = True; s.flags["gun"] = True
    s.heat = 10.0
    rules._clamp_heat(s)
    assert s.heat >= 35.0                       # armed and named — never cold again
    # rewind to a pre-armed checkpoint still leaves you armed (it's meta-progress)
    game.handle(s, "drive to st_george")        # a clean checkpoint
    s.heat = 50.0
    game.handle(s, "rewind")
    assert s.flags.get("desperado") and s.flags.get("gun")


def test_draw_forces_a_stop_but_burns_every_bridge():
    from engine import encounters
    s = _armed_setup()
    s.flags["desperado"] = True; s.flags["gun"] = True
    s.heat = 50.0
    encounters.start_stop(s, "plate")
    r = game.handle(s, "draw")
    assert not encounters.stop_active(s)        # you got away
    assert s.heat >= 99                          # ...and lit up every scanner
    assert s.flags.get("wanted_armed")
    # without the gun, 'draw' in a stop is just talk-first
    s2 = _armed_setup()
    encounters.start_stop(s2, "plate")
    game.handle(s2, "draw")
    assert encounters.stop_active(s2)           # nothing to draw — stop still open


def test_talking_the_clerk_down_avoids_desperado():
    from engine import encounters
    s = _armed_setup()
    game.handle(s, "back off, you didn't see anything")
    assert encounters.standoff_active(s)
    r = game.handle(s, "easy — sorry, no trouble, just buying gas, we're cool")
    assert not encounters.standoff_active(s)
    assert not s.flags.get("desperado")         # you stayed soft — no gun
    assert s.status == "playing"


def test_homecoming_beats_exist():
    s = fresh(); s.fuel_l = 40.0; s.cash = 500.0
    s.place = world.get_poi("livermore")
    r = game.handle(s, "drive to oakland_aisha")
    assert s.flags.get("seen_home_garage")
    assert "aisha" in r["scene"].lower() or "1926" in r["scene"]
