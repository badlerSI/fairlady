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
    s = GameState.from_dict(json.loads(path.read_text()))
    # back-compat: saves from before the two-axis heat split have no car/personal flags — seed both
    # to the combined meter (the conservative "could be hot either way" assumption) so the HUD is sane.
    if s.heat > 0 and "car_heat" not in s.flags and "personal_heat" not in s.flags:
        s.flags["car_heat"] = s.heat
        s.flags["personal_heat"] = s.heat
    return s


def exists(name: str = "autosave") -> bool:
    return (SAVE_DIR / f"{_safe(name)}.json").exists()


def delete(name: str) -> None:
    path = SAVE_DIR / f"{_safe(name)}.json"
    if path.exists():
        path.unlink()
