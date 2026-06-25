"""RIDE OR DIE (愛車) web server: serves the CRT terminal and the game API.

Multi-user by design: each browser gets an opaque session cookie, and that token keys its own
game — its own save slot, its own rewind checkpoints, its own Ace voice-memory. There is NO shared
in-memory game, so the server is stateless per request and safe to run with `uvicorn --workers N`
(state lives in the per-session save files on disk)."""
from __future__ import annotations
import re
import secrets
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import FRONTEND_DIR, TTS_DIR, ADAPTER, ROUTING
from engine import game, save
from engine.state import GameState

app = FastAPI(title="RIDE OR DIE", version="1.2")

SESSION_COOKIE = "fairlady_sid"
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")          # exactly what token_urlsafe emits
COOKIE_MAX_AGE = 60 * 60 * 24 * 180                       # ~6 months of the same car


@app.middleware("http")
async def _revalidate_ui(request, call_next):
    """Dev ergonomics: the UI is edited live, so tell browsers to always revalidate the static
    assets (they have ETags — revalidation is a cheap 304 when unchanged, a fresh 200 when edited).
    Without this, Starlette's StaticFiles ships no Cache-Control and browsers heuristically cache
    stale JS/CSS, so edits silently don't show."""
    resp = await call_next(request)
    p = request.url.path
    if p == "/" or p.startswith("/ui"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


# --------------------------------------------------------------------- sessions
def _sid(request: Request):
    """The caller's session token, or a fresh one. Returns (sid, is_new)."""
    sid = request.cookies.get(SESSION_COOKIE)
    if sid and _SID_RE.match(sid):
        return sid, False
    return secrets.token_urlsafe(16), True


def _slot(sid: str) -> str:
    return f"web_{sid}"


def _respond(content: dict, sid: str, is_new: bool, secure: bool = False) -> JSONResponse:
    resp = JSONResponse(content)
    if is_new:
        resp.set_cookie(SESSION_COOKIE, sid, max_age=COOKIE_MAX_AGE,
                        httponly=True, samesite="lax", path="/", secure=secure)
    return resp


def _secure(request: Request) -> bool:
    """Send the Secure cookie flag when the request actually arrived over HTTPS (honors the proxy's
    X-Forwarded-Proto when uvicorn runs with --proxy-headers). Stays off for plain-http localhost dev."""
    return request.url.scheme == "https"


def _load_or_new(sid: str) -> GameState:
    s = save.load(_slot(sid))
    if s is None:
        return game.new_game(sid=sid)                    # first visit → a fresh car for this session
    s.flags["save_slot"] = _slot(sid)                    # belt-and-suspenders for older saves
    return s


class NewReq(BaseModel):
    seed: Optional[int] = None


class CmdReq(BaseModel):
    input: str = ""


@app.get("/api/health")
def health():
    return {"ok": True, "adapter": ADAPTER, "routing": ROUTING}


@app.post("/api/new")
def api_new(req: NewReq, request: Request):
    sid, is_new = _sid(request)
    s = game.new_game(req.seed, sid=sid)
    return _respond(game.opening_result(s), sid, is_new, _secure(request))


@app.get("/api/state")
def api_state(request: Request):
    sid, is_new = _sid(request)
    s = _load_or_new(sid)
    content = game.opening_result(s) if s.turn == 0 else game._result(s, [], "", info=None)
    return _respond(content, sid, is_new, _secure(request))


@app.post("/api/command")
def api_command(req: CmdReq, request: Request):
    sid, is_new = _sid(request)
    raw = (req.input or "").strip()
    low = raw.lower()
    if low in ("new", "new game", "restart", "reset"):
        s = game.new_game(sid=sid)
        return _respond(game.opening_result(s), sid, is_new, _secure(request))
    s = _load_or_new(sid)
    if low.startswith("load"):
        # multi-user: 'load' only reloads YOUR OWN game — never another session's file.
        content = game._result(s, [], "", info="Reloaded your game.")
        return _respond(content, sid, is_new, _secure(request))
    content = game.handle(s, raw)
    save.save(s, _slot(sid))                              # authoritative per-session persistence
    return _respond(content, sid, is_new, _secure(request))


# --- static --------------------------------------------------------------------
app.mount("/tts-audio", StaticFiles(directory=str(TTS_DIR)), name="tts")
app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


@app.get("/")
def root():
    return RedirectResponse(url="/ui/")
