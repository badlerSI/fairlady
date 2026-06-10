"""GameState: the single source of truth. The narrator reads it; only the engine writes it."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

from config import (
    LITERS_PER_GALLON, START_CASH, CARD_LIMIT, HEAT_START, START_ISO,
)


@dataclass
class Place:
    """Where the car is, or where it's going. POIs and live-geocoded addresses share this shape."""
    name: str
    lat: float
    lon: float
    region: str = ""                      # NV/CA/AZ/UT or "" if unknown
    poi_id: Optional[str] = None          # set when this is a curated POI
    kind: str = "spot"                    # gas/lodging/city/park/track/amusement/encounter/spot
    services: list = field(default_factory=list)  # subset of {gas,lodging,food}
    blurb: str = ""
    gas_price: Optional[float] = None     # $/gal override
    terrain: float = 1.0                  # fuel multiplier for the leg INTO here
    heat_zone: bool = False               # cameras everywhere; swipes here cost more
    language: Optional[str] = None        # encounter NPC language
    voice: Optional[str] = None
    npc: Optional[str] = None
    scene: Optional[str] = None           # retro scene id for this place

    def has(self, service: str) -> bool:
        return service in self.services

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Place":
        known = {f for f in Place.__dataclass_fields__}
        return Place(**{k: v for k, v in d.items() if k in known})


@dataclass
class GameState:
    # --- car physics ---
    fuel_l: float = 5.0
    tank_l: float = 40.0
    mpg: float = 20.0

    # --- money ---
    cash: float = START_CASH
    card_limit: float = CARD_LIMIT
    card_balance: float = 0.0           # amount charged so far
    pay_method: str = "card"            # "card" | "cash"

    # --- world / position ---
    pos: dict = field(default_factory=dict)   # serialized Place
    odometer_mi: float = 0.0
    visited: list = field(default_factory=list)
    adventures: list = field(default_factory=list)  # parks/tracks/amusement reached

    # --- time ---
    clock_iso: str = START_ISO
    day: int = 1
    last_sleep_iso: str = START_ISO
    fatigue: float = 0.0

    # --- stolen-car heat ---
    heat: float = HEAT_START
    last_sleep_poi: Optional[str] = None  # for linger detection

    # --- bookkeeping ---
    status: str = "playing"             # playing | stranded | busted | impounded
    ending: Optional[str] = None
    seed: int = 73111737                # deterministic per game (overridden at new-game)
    turn: int = 0
    log: list = field(default_factory=list)  # recent mechanical events
    flags: dict = field(default_factory=dict)

    # ---- derived ----
    @property
    def gallons(self) -> float:
        return self.fuel_l / LITERS_PER_GALLON

    @property
    def range_mi(self) -> float:
        return self.gallons * self.mpg

    @property
    def tank_pct(self) -> float:
        return 100.0 * self.fuel_l / self.tank_l if self.tank_l else 0.0

    @property
    def credit_available(self) -> float:
        return max(0.0, self.card_limit - self.card_balance)

    @property
    def clock(self) -> datetime:
        return datetime.fromisoformat(self.clock_iso)

    @clock.setter
    def clock(self, dt: datetime) -> None:
        self.clock_iso = dt.isoformat()

    @property
    def place(self) -> Place:
        return Place.from_dict(self.pos) if self.pos else Place("nowhere", 0.0, 0.0)

    @place.setter
    def place(self, p: Place) -> None:
        self.pos = p.to_dict()

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "GameState":
        known = {f for f in GameState.__dataclass_fields__}
        return GameState(**{k: v for k, v in d.items() if k in known})
