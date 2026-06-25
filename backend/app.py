"""RIDE OR DIE (愛車) web server: serves the CRT terminal and the game API."""
from __future__ import annotations
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import FRONTEND_DIR, TTS_DIR, ADAPTER, ROUTING
from engine import game, save
from engine.state import GameState

app = FastAPI(title="RIDE OR DIE", version="1.1")


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


# the current game lives in memory and is autosaved every turn
CURRENT: Optional[GameState] = None


def _current() -> GameState:
    global CURRENT
    if CURRENT is None:
        CURRENT = save.load("autosave") or game.new_game()
    return CURRENT


class NewReq(BaseModel):
    seed: Optional[int] = None


class CmdReq(BaseModel):
    input: str = ""


@app.get("/api/health")
def health():
    return {"ok": True, "adapter": ADAPTER, "routing": ROUTING}


@app.post("/api/new")
def api_new(req: NewReq):
    global CURRENT
    CURRENT = game.new_game(req.seed)
    return JSONResponse(game.opening_result(CURRENT))


@app.get("/api/state")
def api_state():
    s = _current()
    return JSONResponse(game.opening_result(s) if s.turn == 0
                        else game._result(s, [], "", info=None))


@app.post("/api/command")
def api_command(req: CmdReq):
    global CURRENT
    raw = (req.input or "").strip()
    low = raw.lower()
    if low in ("new", "new game", "restart", "reset"):
        CURRENT = game.new_game()
        return JSONResponse(game.opening_result(CURRENT))
    if low.startswith("load"):
        name = low[4:].strip() or "autosave"
        loaded = save.load(name)
        if loaded is None:
            s = _current()
            return JSONResponse(game._result(s, [], "", info=f"No save named '{name}'."))
        CURRENT = loaded
        return JSONResponse(game._result(CURRENT, [], "", info=f"Loaded '{name}'."))
    s = _current()
    return JSONResponse(game.handle(s, raw))


# --- static --------------------------------------------------------------------
app.mount("/tts-audio", StaticFiles(directory=str(TTS_DIR)), name="tts")
app.mount("/ui", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="ui")


@app.get("/")
def root():
    return RedirectResponse(url="/ui/")
