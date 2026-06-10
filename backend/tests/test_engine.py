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
    return game.new_game(seed=12345)


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
def test_zion_trap_strands_you():
    s = fresh()
    zion = world.get_poi("zion")
    rules.drive(s, zion)
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
def test_tow_recovers_when_affordable():
    s = fresh()
    rules.drive(s, world.get_poi("zion"))
    assert s.status == "stranded"
    s.cash = 0.0
    s.card_limit = 5000.0; s.card_balance = 0.0
    rules.tow(s, prefer="card")
    assert s.status == "playing"
    assert s.fuel_l == 2.0
    assert s.place.has("gas")
    assert s.heat > rules.HEAT_START       # tow + card = attention


def test_tow_fails_when_broke():
    s = fresh()
    rules.drive(s, world.get_poi("zion"))
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
    # the truth only comes out at the Livermore storage unit
    s.place = world.get_poi("livermore")
    r = game.handle(s, "look")            # arrival reveal is on drive; force via the story hook
    # (drive there for the real path)
    s2 = fresh(); s2.fuel_l = 40.0; s2.cash = 3000.0; s2.place = world.get_poi("oakland_aisha")
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
