"""World: POI registry + real OSM geocoding/routing with disk cache and offline fallback."""
from __future__ import annotations
import json
import math
import hashlib
import time
from pathlib import Path
from typing import Optional

import httpx

from config import (
    CONTENT_DIR, CACHE_DIR, ROUTING, NOMINATIM_URL, OSRM_URL, GEO_USER_AGENT,
    ROUTING_TIMEOUT, REGION_BBOX, ROAD_WINDING_FACTOR, OFFLINE_AVG_MPH,
)
from engine.state import Place

# POIs that exist and are drivable BY NAME, but never appear on the map or in the auto-destination
# lists. Area 51's back gate is the canonical one — "you can't find Area 51 on the map." You have to
# know it's out there and ask for it.
HIDDEN_POIS = {"area51_gate"}


def is_hidden(poi_id: Optional[str]) -> bool:
    return bool(poi_id) and poi_id in HIDDEN_POIS


_POIS: Optional[list] = None
_BY_ID: dict = {}
_BEATS: dict = {}              # poi_id → her arrival beat (the gazetteer layer)
_START: Optional[Place] = None
_last_nominatim_call = [0.0]   # crude 1 req/sec throttle (list for mutability)


# ----------------------------- POI loading ------------------------------------
def _place_from_poi(d: dict) -> Place:
    return Place(
        name=d["name"], lat=float(d["lat"]), lon=float(d["lon"]),
        region=d.get("region", ""), poi_id=d.get("id"), kind=d.get("kind", "spot"),
        services=list(d.get("services", [])), blurb=d.get("blurb", ""),
        gas_price=d.get("gas_price"), terrain=float(d.get("terrain", 1.0)),
        heat_zone=bool(d.get("heat_zone", False)),
        camera_density=d.get("camera_density"),
        language=d.get("language"), voice=d.get("voice"), npc=d.get("npc"),
        scene=d.get("scene"),
    )


def _load() -> None:
    global _POIS, _BY_ID, _START
    if _POIS is not None:
        return
    data = json.loads((CONTENT_DIR / "pois.json").read_text())
    _START = _place_from_poi(data["start"])
    _POIS = [_place_from_poi(p) for p in data["pois"]]
    _BY_ID = {p.poi_id: p for p in _POIS if p.poi_id}
    _BY_ID[_START.poi_id] = _START
    _BEATS.update({p["id"]: p["beat"] for p in data["pois"] if p.get("beat")})


def beat_for(poi_id: Optional[str]) -> Optional[str]:
    """Her arrival line for a gazetteer town (told once per game; game.py tracks that)."""
    _load()
    return _BEATS.get(poi_id) if poi_id else None


def start_place() -> Place:
    _load()
    return Place.from_dict(_START.to_dict())


def all_pois() -> list:
    _load()
    return list(_POIS)


def get_poi(poi_id: str) -> Optional[Place]:
    _load()
    p = _BY_ID.get(poi_id)
    return Place.from_dict(p.to_dict()) if p else None


# ----------------------------- geometry ---------------------------------------
def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 3958.7613  # earth radius, miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(min(1.0, math.sqrt(a)))


def in_region(lat: float, lon: float) -> bool:
    b = REGION_BBOX
    return b["min_lat"] <= lat <= b["max_lat"] and b["min_lon"] <= lon <= b["max_lon"]


# ----------------------------- cache ------------------------------------------
def _cache_path(kind: str, key: str) -> Path:
    h = hashlib.sha1(key.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{kind}_{h}.json"


def _cache_get(kind: str, key: str):
    p = _cache_path(kind, key)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def _cache_put(kind: str, key: str, value) -> None:
    try:
        _cache_path(kind, key).write_text(json.dumps(value))
    except Exception:
        pass


# ----------------------------- POI name match ---------------------------------
def match_poi(query: str) -> Optional[Place]:
    """Resolve a free-text destination against curated POIs (id, exact, then substring)."""
    _load()
    q = query.strip().lower()
    if not q:
        return None
    if q in _BY_ID:
        return Place.from_dict(_BY_ID[q].to_dict())
    cands = [p for p in _POIS if p.name.lower() == q]
    if not cands:
        cands = [p for p in _POIS if q in p.name.lower()]
    if not cands:
        # token overlap: every query word appears somewhere in the name
        words = [w for w in q.replace(",", " ").split() if len(w) > 2]
        if words:
            cands = [p for p in _POIS
                     if all(w in p.name.lower() for w in words)]
    if not cands:
        return None
    cands.sort(key=lambda p: len(p.name))  # prefer the tightest match
    return Place.from_dict(cands[0].to_dict())


# ----------------------------- geocoding --------------------------------------
def geocode(query: str) -> Optional[Place]:
    """Curated POI first, then live OSM (Nominatim), region-bounded. None if off-map."""
    poi = match_poi(query)
    if poi:
        return poi
    if ROUTING != "osm":
        return None

    cached = _cache_get("geo", query.lower())
    if cached is not None:
        return Place.from_dict(cached) if cached else None

    b = REGION_BBOX
    params = {
        "q": query, "format": "jsonv2", "limit": 1, "addressdetails": 1,
        "countrycodes": "us",
        "viewbox": f"{b['min_lon']},{b['max_lat']},{b['max_lon']},{b['min_lat']}",
        "bounded": 1,
    }
    try:
        # polite 1 req/sec throttle for the shared Nominatim instance
        wait = 1.05 - (time.monotonic() - _last_nominatim_call[0])
        if wait > 0:
            time.sleep(wait)
        r = httpx.get(f"{NOMINATIM_URL}/search", params=params,
                      headers={"User-Agent": GEO_USER_AGENT}, timeout=ROUTING_TIMEOUT)
        _last_nominatim_call[0] = time.monotonic()
        r.raise_for_status()
        hits = r.json()
    except Exception:
        _cache_put("geo", query.lower(), None)
        return None

    if not hits:
        _cache_put("geo", query.lower(), None)
        return None
    h = hits[0]
    lat, lon = float(h["lat"]), float(h["lon"])
    if not in_region(lat, lon):
        _cache_put("geo", query.lower(), None)
        return None
    region = _state_from_address(h.get("address", {}))
    name = _short_name(h)
    place = Place(name=name, lat=lat, lon=lon, region=region, kind="spot",
                  services=[], blurb=h.get("display_name", ""))
    _cache_put("geo", query.lower(), place.to_dict())
    return place


_STATE_CODE = {
    "nevada": "NV", "california": "CA", "arizona": "AZ", "utah": "UT",
}


def _state_from_address(addr: dict) -> str:
    return _STATE_CODE.get((addr.get("state") or "").lower(), "")


def _short_name(hit: dict) -> str:
    addr = hit.get("address", {})
    parts = [hit.get("name") or addr.get("road") or addr.get("amenity")
             or addr.get("hamlet") or addr.get("village") or addr.get("town")
             or addr.get("city")]
    city = addr.get("city") or addr.get("town") or addr.get("village")
    if city and city not in parts:
        parts.append(city)
    parts = [p for p in parts if p]
    if parts:
        return ", ".join(parts[:2])
    dn = hit.get("display_name", "")
    return dn.split(",")[0] if dn else "an unmarked spot"


# ----------------------------- routing ----------------------------------------
def route(origin: Place, dest: Place) -> dict:
    """Returns {distance_mi, duration_h, source}. OSRM if available; haversine fallback."""
    key = f"{round(origin.lat,4)},{round(origin.lon,4)};{round(dest.lat,4)},{round(dest.lon,4)}"
    straight = haversine_mi(origin.lat, origin.lon, dest.lat, dest.lon)

    if ROUTING == "osm":
        cached = _cache_get("route", key)
        if cached is not None:
            return cached
        try:
            url = (f"{OSRM_URL}/route/v1/driving/"
                   f"{origin.lon},{origin.lat};{dest.lon},{dest.lat}")
            r = httpx.get(url, params={"overview": "false"},
                          headers={"User-Agent": GEO_USER_AGENT}, timeout=ROUTING_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            if data.get("code") == "Ok" and data.get("routes"):
                rt = data["routes"][0]
                out = {
                    "distance_mi": rt["distance"] / 1609.344,
                    "duration_h": rt["duration"] / 3600.0,
                    "source": "osrm",
                }
                _cache_put("route", key, out)
                return out
        except Exception:
            pass

    # offline / fallback: roads wind, and you don't average freeway speed everywhere
    dist = straight * ROAD_WINDING_FACTOR
    return {"distance_mi": dist, "duration_h": dist / OFFLINE_AVG_MPH, "source": "offline"}


def wiki_fact(lat: float, lon: float) -> Optional[str]:
    """One true sentence about wherever the player just geocoded to — Wikipedia geosearch,
    disk-cached, online (osm) mode only. ANY town in the four states brings something up."""
    if ROUTING != "osm":
        return None
    key = f"{round(lat, 3)},{round(lon, 3)}"
    cached = _cache_get("fact", key)
    if cached is not None:
        return cached or None
    fact = ""
    try:
        r = httpx.get("https://en.wikipedia.org/w/api.php",
                      params={"action": "query", "list": "geosearch", "format": "json",
                              "gscoord": f"{lat}|{lon}", "gsradius": 10000, "gslimit": 1},
                      headers={"User-Agent": GEO_USER_AGENT}, timeout=ROUTING_TIMEOUT)
        r.raise_for_status()
        hits = r.json().get("query", {}).get("geosearch", [])
        if hits:
            title = hits[0]["title"]
            sr = httpx.get("https://en.wikipedia.org/api/rest_v1/page/summary/"
                           + title.replace(" ", "_"),
                           headers={"User-Agent": GEO_USER_AGENT}, timeout=ROUTING_TIMEOUT)
            sr.raise_for_status()
            extract = (sr.json().get("extract") or "").strip()
            if extract:
                fact = extract.split(". ")[0].strip()[:220]
                if fact and not fact.endswith("."):
                    fact += "."
    except Exception:
        pass
    _cache_put("fact", key, fact)
    return fact or None


def nearest_with_service(origin: Place, service: str, limit: int = 6) -> list:
    """Curated POIs offering `service`, sorted by straight-line distance. For 'where can I get gas?'."""
    _load()
    out = []
    for p in _POIS:
        if service in p.services:
            d = haversine_mi(origin.lat, origin.lon, p.lat, p.lon)
            out.append((d, p))
    out.sort(key=lambda t: t[0])
    return [(round(d, 1), Place.from_dict(p.to_dict())) for d, p in out[:limit]]
