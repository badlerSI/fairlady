"""Save/load games as JSON under data/saves."""
from __future__ import annotations
import json
import re

from config import SAVE_DIR
from engine.state import GameState


def _safe(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", name or "autosave")[:64] or "autosave"


def save(state: GameState, name: str = "autosave") -> str:
    path = SAVE_DIR / f"{_safe(name)}.json"
    path.write_text(json.dumps(state.to_dict(), indent=2))
    return str(path)


def load(name: str = "autosave") -> GameState | None:
    path = SAVE_DIR / f"{_safe(name)}.json"
    if not path.exists():
        return None
    return GameState.from_dict(json.loads(path.read_text()))


def exists(name: str = "autosave") -> bool:
    return (SAVE_DIR / f"{_safe(name)}.json").exists()


def delete(name: str) -> None:
    path = SAVE_DIR / f"{_safe(name)}.json"
    if path.exists():
        path.unlink()
