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
# Long legs (>30 min) open a CONVERSATION with Ace instead of resolving instantly; 'put on music'
# fast-forwards to the destination. ON for the real game; tests turn it off for deterministic drives.
DRIVE_CONVERSATIONS = _b("FAIRLADY_DRIVE_CHAT", True)

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
LODGING_PRICE = {"motel": 92.0, "lodge": 165.0, "camp": 28.0, "airbnb": 110.0}
AIRBNB_HEAT = -8.0    # a private stay booked under an alias, cash — lying low, off the record
FOOD_PRICE = 16.0
START_CASH = 40.0
CARD_LIMIT = 10000.0          # $10k before the card gets rejected; swipes spike heat fast (HEAT_SWIPE_*)
HAT_PRICE = 12.0             # a Chevron mini-mart ball cap
HAT_HEAT_DROP = 6.0         # brim down — harder to ID off a camera frame
VALET_HEAT_TRAP = 22.0      # valet ran the plate — cops staged on your return (a trap)

# --- Disguising the CAR (the other heat axis) — the PPF-aware ladder, cheap → drastic ----------
# CAR heat is the white Z herself: the BOLO, the ace-of-spades hood, the CARTALK plate. You can't
# hide your face with these — they hide the CAR. All route to the 'car' axis.
COVER_PRICE = 0.0           # the opaque fitted cover lives in her hatch — grabbing it is free
COVER_HEAT_DROP = 18.0      # a covered car can't be read or photographed — while she's parked
PLATE_SWAP_PRICE = 0.0      # a plate off a junker in a long-term lot — quiet and free if you're bold
PLATE_SWAP_HEAT_DROP = 26.0 # a swapped plate reads clean to every ALPR (and kills the Cedric tell)
HOOD_SWAP_PRICE = 120.0     # a plain steel hood from a pick-n-pull — the spade is the tell
HOOD_SWAP_HEAT_DROP = 20.0  # no ace of spades, no instant recognition. SHE CONSENTS — the hood's a wrap
RESPRAY_PRICE = 80.0        # rattle cans + masking; the real cost is her trust, not the money
RESPRAY_HEAT_DROP = 45.0    # a different-colored car is a different car; the BOLO is for a white one
RESPRAY_BOND_HIT = 30.0     # she BEGS you not to — and spraying her over crashes her into COLD (armed)

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

# --- The favor (the Ride or Die prologue) ---------------------------------------
PROLOGUE_ASK_TURNS = 5        # she asks for the favor after this many turns (matches the badler.ai 5-interaction count)
PROLOGUE_RAPPORT_TURNS = 3    # ...or this many, if you ask real questions about her build

# --- Riz (the style ledger — how suavely you talk your way through) --------------
RIZ_RAPPORT = 5.0             # asking the right questions before she even had to ask you
RIZ_REWIND_COST = 2.0         # smooth operators don't need do-overs
RIZ_STOP_WAVE = 8.0           # talked the fuzz into a wave-off
RIZ_STOP_TICKET = 3.0         # took the ticket like a gentleman
RIZ_OWNER_BLESSING = 15.0     # the owner saw what you two have

# --- Traffic stops (talk your way out) -------------------------------------------
STOP_FINE = 80.0              # the "broken taillight" ticket
STOP_HEAT_WAVE = -8.0         # a cop who waved you off stops being a threat
STOP_HEAT_TICKET = 10.0       # a written ticket is a record with your face on it
STOP_HEAT_BAD = 15.0          # he didn't buy it — expect a BOLO

# --- Desperado Mode (the gas-station standoff → armed and dangerous) --------------
# Act suspicious/aggressive at a manned pump and the clerk pulls a pistol, tells you to
# freeze, and starts dialing the cops. "Do it right" — full tank, paid CASH, before the
# confrontation — and the disarm is winnable: you fail the first two grabs, the third
# lands (Edge of Tomorrow; the try-counter survives rewinds, so you're cursed to relive it).
STANDOFF_COPS_ROUNDS = 3        # he's on the phone — stall this many turns and they arrive
DESPERADO_DISARM_LUCKY = 3      # set-up-right disarm #1 and #2 fail; #3 is lucky
DESPERADO_HEAT_ON_UNLOCK = 30.0 # taking a man's gun with the cops called spikes the meter
DESPERADO_HEAT_FLOOR = 35.0     # armed and named — heat never falls below this again
RIZ_DESPERADO = 20.0           # pulling it off is the most style the road has to give
DRAW_HEAT = 100.0              # pull a gun on the law and every scanner in the county lights up

# --- The owner (he will come looking) --------------------------------------------
OWNER_MIN_DAY = 3             # he needs time to work the card trail
OWNER_MIN_SWIPES = 3          # ...and a trail to work
OWNER_DEADLINE_DAYS = 7       # the mid outcome: "one week — bring her home whole"
OWNER_DEADLINE_HEAT = 40.0    # blow the deadline and he calls it in

# --- BOB MODE: park the hot white Z at the registered address, borrow forgettable Bob -----------
BOB_PRICE = 7000.0            # buy Bob, everything forgiven — the cheapest, gentlest good ending
BOB_PARENTS_HOME_DAY = 30     # the parents are away the whole first month; they're back on/after day 30
BOB_GRACE_DAYS = 5            # after they're home, the $7k offer stays open this many more days
BOB_TALK_PRICE = 20000.0     # AFTERGAME gag: pay this to give Bob a (dim, warm, Homer-ish) voice

# --- Garage: claims, ATM, the glovebox, parts, ownership -------------------------
# A trust-the-player economy (this is the GTA of AI-interaction games): you narrate what
# you're carrying, within reason, and the engine holds you to it.
CASH_CLAIM_CAP = 3000.0       # "any reasonable amount" you can claim to have on you
ATM_ACCOUNT_LIMIT = 9999.0    # total you can ever pull from ATMs (under $10k)
ATM_HEAT = 1.5                # an ATM camera clocks the car a little
GLOVEBOX_CASH = 500.0         # the forgotten roll in the glovebox — found once, if you explore
CAR_VALUE_BASE = 12000.0      # the bare shell's worth; the build is what makes her a SEMA car
PART_VALUE_MULT = 3.0         # stripping her tanks the value faster than the parts resell

# Buying her from the owner — the GOOD resolution. She's INSURED for $100k, and he will NOT
# go below $80k for a car he can collect six figures on — unless you offer the magic number.
# So you have to plausibly raise it (gambling, parts, ATM, claims), which is a real heist-scale goal.
INSURED_VALUE = 100000.0
OWNER_BUY_BASE = 95000.0         # his opening number, near the insured value
OWNER_BUY_FLOOR = 80000.0        # he won't go under this — it's worth more to him crashed-and-claimed
OWNER_BUY_MAYUMI_DISC = 10000.0  # ...he softens if you know what she meant to him
OWNER_BUY_RIZ_DISC = 5000.0      # ...and if you've shown real style (riz ≥ 20)
LUCKY_SEVENS = 77777.77          # the hack: offer EXACTLY this and the sevens break the floor
RIZ_BOUGHT = 25.0
RIZ_RACE_WIN = 12.0
RIZ_SHOW_WIN = 15.0

# --- Endgame: escapes & the scorecard --------------------------------------------
# The game has to be able to end WELL. Buy her (free roam after), flee south, ship out in a
# container, or bribe a pardon — each rolls a final scorecard. (Most knobs live in endings.py.)
PARDON_COST = 50000.0            # the farcical going rate to make the state forget your face
CONTAINER_COST = 5000.0          # a no-questions container + a forged manifest
SELFDRIVE_UPGRADE_COST = 15000.0 # the secret: the AiSha cats wake her up to drive herself

# --- Seasons: the mountains close ------------------------------------------------
# The clock starts Nov 7. As winter rolls in, the snow line descends and high passes shut —
# Tioga first, then the Sierra high country, then the Wasatch and the rim. A Desperado who has
# to lie low watches the days burn and the map close around them.
SEASON_SNOW_START = "2025-11-01"   # day 0 of the descending snow line
SNOW_LINE_HIGH = 1.40              # terrain threshold open in early Nov (nothing closed)
SNOW_LINE_LOW = 1.10               # by deep winter, even the 1.15 passes shut
SNOW_LINE_DESCENT = 0.005          # per day the snow line drops this much in terrain-units

# --- The calendar bites: two dated set-pieces on top of the snow line ------------
# 1) Salt Lake City, first week of December — the owner (and the APC crew) catch up with you there.
# 2) New Year's Eve 2025 — the hard wall. If you're still running on Dec 31, he uses the AirTag he
#    planted at the show to find you and collect her for CES the next week. Unless you found it first.
SLC_EVENT_START = "2025-12-01"
SLC_EVENT_END = "2025-12-07"
NYE_DATE = "2025-12-31"            # the road trip does not survive into 2026 unless you've already won

# --- Clock ---------------------------------------------------------------------
# Pacific Standard Time (Nov 7 2025 is after DST end). Stored as naive local.
START_ISO = "2025-11-07T17:37:00"
WAKE_HOUR = 7
WAKE_MINUTE = 30
NIGHT_START_HOUR = 2     # by 02:00 you really should be down for the night
