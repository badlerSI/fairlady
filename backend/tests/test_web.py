"""Web-layer tests: per-session isolation. Run network-free (stub narrator, offline routing).

These hit the FastAPI app through a TestClient — two clients are two browsers, with their own
cookie jars — and prove that one visitor's game never touches another's."""
import os
os.environ.setdefault("FAIRLADY_ROUTING", "offline")
os.environ.setdefault("FAIRLADY_ADAPTER", "stub")

import glob

from starlette.testclient import TestClient

from app import app, SESSION_COOKIE
from engine import save
from config import SAVE_DIR


def _cleanup(token):
    if not token:
        return
    save.delete(f"web_{token}")
    for p in glob.glob(str(SAVE_DIR / f"cp_{token}_*.json")):
        os.remove(p)


def test_health_reports_adapter_and_routing():
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] and "adapter" in body and "routing" in body


def test_first_contact_sets_a_session_cookie():
    c = TestClient(app)
    r = c.get("/api/state")
    assert r.status_code == 200
    sid = c.cookies.get(SESSION_COOKIE)
    try:
        assert sid and 16 <= len(sid) <= 64
        assert r.json()["snapshot"]["turn"] == 0           # a fresh car on the show floor
    finally:
        _cleanup(sid)


def test_two_browsers_get_independent_games():
    c1, c2 = TestClient(app), TestClient(app)
    c1.get("/api/state"); c2.get("/api/state")
    sid1 = c1.cookies.get(SESSION_COOKIE)
    sid2 = c2.cookies.get(SESSION_COOKIE)
    try:
        assert sid1 and sid2 and sid1 != sid2              # distinct sessions
        c1.post("/api/command", json={"input": "look"})    # player 1 takes a turn
        t1 = c1.get("/api/state").json()["snapshot"]["turn"]
        t2 = c2.get("/api/state").json()["snapshot"]["turn"]
        assert t1 == 1 and t2 == 0                          # player 2 is wholly untouched
    finally:
        _cleanup(sid1); _cleanup(sid2)


def test_same_browser_keeps_its_game_across_requests():
    c = TestClient(app)
    c.get("/api/state")
    sid = c.cookies.get(SESSION_COOKIE)
    try:
        c.post("/api/command", json={"input": "look"})
        a = c.get("/api/state").json()["snapshot"]["turn"]
        c.post("/api/command", json={"input": "how much torque do you make?"})
        b = c.get("/api/state").json()["snapshot"]["turn"]
        assert a >= 1 and b >= a                            # the session accumulates, doesn't reset
    finally:
        _cleanup(sid)


def test_new_resets_only_the_callers_game():
    c1, c2 = TestClient(app), TestClient(app)
    c1.get("/api/state"); c2.get("/api/state")
    sid1 = c1.cookies.get(SESSION_COOKIE)
    sid2 = c2.cookies.get(SESSION_COOKIE)
    try:
        c1.post("/api/command", json={"input": "look"})
        c2.post("/api/command", json={"input": "look"})
        c1.post("/api/command", json={"input": "new"})      # player 1 starts over
        assert c1.get("/api/state").json()["snapshot"]["turn"] == 0
        assert c2.get("/api/state").json()["snapshot"]["turn"] == 1   # player 2 unaffected
    finally:
        _cleanup(sid1); _cleanup(sid2)


def test_load_cannot_reach_another_sessions_file():
    # 'load <name>' in the web API must only ever reload the caller's own game.
    victim = TestClient(app)
    victim.get("/api/state")
    vsid = victim.cookies.get(SESSION_COOKIE)
    attacker = TestClient(app)
    attacker.get("/api/state")
    asid = attacker.cookies.get(SESSION_COOKIE)
    try:
        victim.post("/api/command", json={"input": "look"})           # victim is at turn 1
        # attacker tries to load the victim's slot by name
        r = attacker.post("/api/command", json={"input": f"load web_{vsid}"})
        assert r.status_code == 200
        # attacker still sees ONLY their own (turn 0) game, not the victim's turn-1 state
        assert attacker.get("/api/state").json()["snapshot"]["turn"] == 0
    finally:
        _cleanup(vsid); _cleanup(asid)
