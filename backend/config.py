"""Central configuration for FAIRLADY. All knobs in one place; env overrides."""
from __future__ import annotations
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
CONTENT_DIR = BACKEND_DIR / "content"
DATA_DIR = PROJECT_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
SAVE_DIR = DATA_DIR / "saves"
FRONTEND_DIR = PROJECT_DIR / "frontend"

for d in (DATA_DIR, CACHE_DIR, SAVE_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _b(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    return default if v is None else v.strip().lower() in ("1", "true", "yes", "on")


# --- Narration / voice adapter -------------------------------------------------
# ADAPTER: "stub" (offline, deterministic, no network) or "ace" (rop1 Ace stack).
ADAPTER = os.environ.get("FAIRLADY_ADAPTER", "stub").strip().lower()
ACE_BASE_URL = os.environ.get("FAIRLADY_ACE_URL", "https://ace-api.badler.ai").rstrip("/")
ACE_TIMEOUT = float(os.environ.get("FAIRLADY_ACE_TIMEOUT", "30"))
VOICE_ENABLED = _b("FAIRLADY_VOICE", True)  # request Kokoro audio urls

# Optional multi-voice TTS for non-Japanese NPCs (OpenAI-compatible /v1/audio/speech,
# e.g. a full Kokoro server). If unset, FAIRLADY (en) and Japanese NPCs are voiced via
# Ace; other languages get real native TEXT but no audio.
KOKORO_URL = os.environ.get("FAIRLADY_KOKORO_URL", "").rstrip("/")
KOKORO_MODEL = os.environ.get("FAIRLADY_KOKORO_MODEL", "kokoro")
TTS_DIR = DATA_DIR / "tts"
TTS_DIR.mkdir(parents=True, exist_ok=True)

# --- Routing / world -----------------------------------------------------------
# ROUTING: "osm" (live Nominatim + OSRM, disk-cached) or "offline" (haversine only).
ROUTING = os.environ.get("FAIRLADY_ROUTING", "osm").strip().lower()
NOMINATIM_URL = os.environ.get("FAIRLADY_NOMINATIM_URL", "https://nominatim.openstreetmap.org").rstrip("/")
OSRM_URL = os.environ.get("FAIRLADY_OSRM_URL", "https://router.project-osrm.org").rstrip("/")
GEO_USER_AGENT = os.environ.get("FAIRLADY_USER_AGENT", "FAIRLADY-240z-game/1.0 (single-player; contact ben)")
ROUTING_TIMEOUT = float(os.environ.get("FAIRLADY_ROUTING_TIMEOUT", "12"))

# In-region bounding box (NV/CA/AZ/UT roughly). Off-map destinations are refused.
REGION_BBOX = {"min_lat": 31.0, "max_lat": 42.5, "min_lon": -124.7, "max_lon": -108.7}
REGION_STATES = ("NV", "CA", "AZ", "UT")

# Offline fallback: roads are not straight lines.
ROAD_WINDING_FACTOR = 1.22       # multiply haversine distance to approximate road miles
OFFLINE_AVG_MPH = 52.0           # average speed for offline duration estimate

# --- Car physics ---------------------------------------------------------------
LITERS_PER_GALLON = 3.785411784

# --- Economy -------------------------------------------------------------------
DEFAULT_GAS_PRICE = {"NV": 4.25, "CA": 4.95, "AZ": 3.95, "UT": 3.89}  # $/gal, Nov 2025-ish
LODGING_PRICE = {"motel": 92.0, "lodge": 165.0, "camp": 28.0}
FOOD_PRICE = 16.0
START_CASH = 40.0
CARD_LIMIT = 2000.0

# --- Heat (stolen car) ---------------------------------------------------------
HEAT_START = 8.0
HEAT_PATROL_THRESHOLD = 45.0
HEAT_DECLINE_CARD_THRESHOLD = 70.0   # lodging/stations get nervous about the card
HEAT_ROADBLOCK_THRESHOLD = 90.0
HEAT_SWIPE_BASE = 2.0
HEAT_SWIPE_HOTZONE = 4.0
HEAT_SWIPE_FIRST_DAY = 2.0           # extra, first 24h near the show
HEAT_DECAY_PER_HOUR = 0.8            # while moving away, outside hot zones
HEAT_STATELINE_MULT = 0.82          # crossing into a new state muddies jurisdiction
HEAT_PUSH_DRIVE = 6.0               # driving fast draws attention
HEAT_SLEEP_LODGING = -4.0           # a night off the road, lying low
HEAT_LINGER = 5.0                   # sleeping twice in the same town

# --- Fatigue (the driver, not the car) -----------------------------------------
FATIGUE_PER_HOUR = 5.0
FATIGUE_WARN = 70.0
FATIGUE_FORCE = 100.0
ROUGH_SLEEP_HEAT = 3.0               # pulling over where you shouldn't draws an eye
# You have to sleep most nights. Hours-awake is the hard gate (clock-based).
AWAKE_START_ISO = "2025-11-07T07:30:00"   # you were up all day working the show
AWAKE_WARN_HOURS = 16.0
AWAKE_FORCE_HOURS = 20.0

# --- Clock ---------------------------------------------------------------------
# Pacific Standard Time (Nov 7 2025 is after DST end). Stored as naive local.
START_ISO = "2025-11-07T17:37:00"
WAKE_HOUR = 7
WAKE_MINUTE = 30
NIGHT_START_HOUR = 2     # by 02:00 you really should be down for the night
