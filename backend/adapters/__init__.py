"""Narrator selection."""
from config import ADAPTER
from adapters.base import Narrator
from adapters.stub import StubNarrator

_INSTANCE = None


def get_narrator() -> Narrator:
    global _INSTANCE
    if _INSTANCE is not None:
        return _INSTANCE
    if ADAPTER == "ace":
        from adapters.ace import AceNarrator
        _INSTANCE = AceNarrator()
    else:
        _INSTANCE = StubNarrator()
    return _INSTANCE
