#!/usr/bin/env python3
"""Fetch grounding for the gazetteer: Wikipedia summary + coordinates + lead image
for every curated town, plus lead images for existing POIs that lack bespoke scenes.

Writes data/gazetteer/source.json (facts, coords, image URLs + licenses) and caches
raw images under data/gazetteer/img/. Polite: custom UA, ~5 req/s, resumable.

    ./.venv/bin/python tools/gazetteer_fetch.py            # towns + scene-gap POIs
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "gazetteer"
IMG_DIR = OUT_DIR / "img"
OUT_DIR.mkdir(parents=True, exist_ok=True)
IMG_DIR.mkdir(parents=True, exist_ok=True)
UA = "RIDE-OR-DIE-gazetteer/1.0 (single-player game content; contact ben@badler.ai)"

# ---------------------------------------------------------------- the town list
# id: (wikipedia title, region, kind, terrain, services-override)
# default kind "city", terrain 1.0, services ["gas","lodging","food"]
T = lambda title, region, kind="city", terrain=1.0, services=None: dict(
    title=title, region=region, kind=kind, terrain=terrain, services=services)

TOWNS = {
    # --- NEVADA: I-80, US-50 Loneliest Road, US-93/95, the storied corners ---
    "winnemucca":     T("Winnemucca, Nevada", "NV"),
    "elko":           T("Elko, Nevada", "NV"),
    "wells_nv":       T("Wells, Nevada", "NV"),
    "west_wendover":  T("West Wendover, Nevada", "NV"),
    "battle_mountain":T("Battle Mountain, Nevada", "NV"),
    "lovelock":       T("Lovelock, Nevada", "NV"),
    "eureka_nv":      T("Eureka, Nevada", "NV"),
    "austin_nv":      T("Austin, Nevada", "NV"),
    "hawthorne_nv":   T("Hawthorne, Nevada", "NV"),
    "mina_nv":        T("Mina, Nevada", "NV", services=["gas"]),
    "virginia_city":  T("Virginia City, Nevada", "NV", terrain=1.1),
    "genoa_nv":       T("Genoa, Nevada", "NV", services=["food"]),
    "gardnerville":   T("Gardnerville, Nevada", "NV"),
    "yerington":      T("Yerington, Nevada", "NV"),
    "fernley":        T("Fernley, Nevada", "NV"),
    "boulder_city":   T("Boulder City, Nevada", "NV"),
    "searchlight":    T("Searchlight, Nevada", "NV", services=["gas", "food"]),
    "alamo_nv":       T("Alamo, Nevada", "NV", services=["gas", "food"]),
    "caliente_nv":    T("Caliente, Nevada", "NV"),
    "pioche":         T("Pioche, Nevada", "NV"),
    "overton_nv":     T("Overton, Nevada", "NV"),
    "gerlach":        T("Gerlach, Nevada", "NV", services=["gas", "food"]),
    "jackpot_nv":     T("Jackpot, Nevada", "NV"),
    "amargosa_valley":T("Amargosa Valley, Nevada", "NV", services=["gas"]),

    # --- CALIFORNIA: Eastern Sierra, desert, coast, the far north ---
    "truckee":        T("Truckee, California", "CA", terrain=1.15),
    "south_lake_tahoe":T("South Lake Tahoe, California", "CA", terrain=1.15),
    "mammoth_lakes":  T("Mammoth Lakes, California", "CA", terrain=1.2),
    "bridgeport_ca":  T("Bridgeport, California", "CA", terrain=1.1),
    "bodie":          T("Bodie, California", "CA", kind="park", terrain=1.2, services=[]),
    "independence_ca":T("Independence, California", "CA"),
    "ridgecrest":     T("Ridgecrest, California", "CA"),
    "trona":          T("Trona, San Bernardino County, California", "CA", services=["gas"]),
    "tehachapi":      T("Tehachapi, California", "CA", terrain=1.1),
    "lancaster_ca":   T("Lancaster, California", "CA"),
    "victorville":    T("Victorville, California", "CA"),
    "twentynine_palms":T("Twentynine Palms, California", "CA"),
    "indio":          T("Indio, California", "CA"),
    "el_centro":      T("El Centro, California", "CA"),
    "blythe":         T("Blythe, California", "CA"),
    "julian_ca":      T("Julian, California", "CA", terrain=1.1),
    "borrego_springs":T("Borrego Springs, California", "CA"),
    "temecula":       T("Temecula, California", "CA"),
    "ojai":           T("Ojai, California", "CA"),
    "paso_robles":    T("Paso Robles, California", "CA"),
    "san_luis_obispo":T("San Luis Obispo, California", "CA"),
    "san_simeon":     T("San Simeon, California", "CA"),
    "big_sur":        T("Big Sur", "CA", kind="park", terrain=1.2, services=["lodging", "food"]),
    "salinas":        T("Salinas, California", "CA"),
    "santa_maria":    T("Santa Maria, California", "CA"),
    "solvang":        T("Solvang, California", "CA"),
    "santa_rosa":     T("Santa Rosa, California", "CA"),
    "petaluma":       T("Petaluma, California", "CA"),
    "mendocino":      T("Mendocino, California", "CA", services=["lodging", "food"]),
    "fort_bragg_ca":  T("Fort Bragg, California", "CA"),
    "eureka_ca":      T("Eureka, California", "CA"),
    "weed_ca":        T("Weed, California", "CA"),
    "mount_shasta_city":T("Mount Shasta, California", "CA", terrain=1.15),
    "yreka":          T("Yreka, California", "CA"),
    "susanville":     T("Susanville, California", "CA"),
    "alturas":        T("Alturas, California", "CA"),
    "chico":          T("Chico, California", "CA"),
    "placerville":    T("Placerville, California", "CA", terrain=1.05),
    "nevada_city_ca": T("Nevada City, California", "CA", terrain=1.05),
    "sonora_ca":      T("Sonora, California", "CA", terrain=1.05),
    "mariposa_ca":    T("Mariposa, California", "CA", terrain=1.05),
    "oakhurst":       T("Oakhurst, California", "CA", terrain=1.05),
    "modesto":        T("Modesto, California", "CA"),
    "visalia":        T("Visalia, California", "CA"),
    "zzyzx":          T("Zzyzx, California", "CA", kind="encounter", services=[]),
    "amboy_ca":       T("Amboy, California", "CA", kind="gas", services=["gas"]),
    "tecopa":         T("Tecopa, California", "CA", services=["lodging"]),
    "koreatown_la":   T("Koreatown, Los Angeles", "CA", kind="encounter", services=["food"]),
    "venice_beach":   T("Venice, Los Angeles", "CA", kind="encounter", services=["food"]),
    "malibu":         T("Malibu, California", "CA"),

    # --- ARIZONA: Route 66, the high country, the border, the copper towns ---
    "yuma":           T("Yuma, Arizona", "AZ"),
    "quartzsite":     T("Quartzsite, Arizona", "AZ"),
    "parker_az":      T("Parker, Arizona", "AZ"),
    "bullhead_city":  T("Bullhead City, Arizona", "AZ"),
    "oatman":         T("Oatman, Arizona", "AZ", kind="encounter", services=["food"]),
    "seligman":       T("Seligman, Arizona", "AZ"),
    "prescott":       T("Prescott, Arizona", "AZ", terrain=1.1),
    "jerome_az":      T("Jerome, Arizona", "AZ", kind="encounter", terrain=1.15,
                        services=["lodging", "food"]),
    "payson_az":      T("Payson, Arizona", "AZ", terrain=1.1),
    "show_low":       T("Show Low, Arizona", "AZ", terrain=1.1),
    "holbrook":       T("Holbrook, Arizona", "AZ"),
    "winslow_az":     T("Winslow, Arizona", "AZ"),
    "window_rock":    T("Window Rock, Arizona", "AZ"),
    "chinle":         T("Chinle, Arizona", "AZ"),
    "kayenta":        T("Kayenta, Arizona", "AZ"),
    "tuba_city":      T("Tuba City, Arizona", "AZ"),
    "globe_az":       T("Globe, Arizona", "AZ", terrain=1.05),
    "superior_az":    T("Superior, Arizona", "AZ", terrain=1.05),
    "bisbee":         T("Bisbee, Arizona", "AZ", kind="encounter", terrain=1.1),
    "tombstone":      T("Tombstone, Arizona", "AZ", kind="encounter"),
    "willcox":        T("Willcox, Arizona", "AZ"),
    "ajo":            T("Ajo, Arizona", "AZ"),
    "why_az":         T("Why, Arizona", "AZ", kind="gas", services=["gas"]),
    "gila_bend":      T("Gila Bend, Arizona", "AZ"),
    "casa_grande":    T("Casa Grande, Arizona", "AZ"),
    "wickenburg":     T("Wickenburg, Arizona", "AZ"),

    # --- UTAH: the Wasatch, the desert spine, the far corners ---
    "provo":          T("Provo, Utah", "UT"),
    "ogden":          T("Ogden, Utah", "UT"),
    "logan_ut":       T("Logan, Utah", "UT"),
    "tooele":         T("Tooele, Utah", "UT"),
    "wendover_ut":    T("Wendover, Utah", "UT"),
    "price_ut":       T("Price, Utah", "UT"),
    "helper_ut":      T("Helper, Utah", "UT"),
    "green_river_ut": T("Green River, Utah", "UT"),
    "hanksville":     T("Hanksville, Utah", "UT", services=["gas", "food"]),
    "torrey_ut":      T("Torrey, Utah", "UT", terrain=1.1),
    "escalante_ut":   T("Escalante, Utah", "UT", terrain=1.1),
    "panguitch":      T("Panguitch, Utah", "UT"),
    "beaver_ut":      T("Beaver, Utah", "UT"),
    "fillmore_ut":    T("Fillmore, Utah", "UT"),
    "delta_ut":       T("Delta, Utah", "UT"),
    "monticello_ut":  T("Monticello, Utah", "UT"),
    "blanding":       T("Blanding, Utah", "UT"),
    "bluff_ut":       T("Bluff, Utah", "UT"),
    "mexican_hat":    T("Mexican Hat, Utah", "UT", services=["gas", "lodging", "food"]),
    "hurricane_ut":   T("Hurricane, Utah", "UT"),
    "vernal_ut":      T("Vernal, Utah", "UT"),
    "heber_city":     T("Heber City, Utah", "UT", terrain=1.1),
}

# Wikipedia titles for EXISTING POIs that ride a generic kind-fallback scene —
# these get a Wikimedia sketch too (their pois.json entries stay otherwise untouched).
EXISTING_TITLES = {
    "lv_motor_speedway": "Las Vegas Motor Speedway", "spring_mountain": "Spring Mountain Motor Resort",
    "pahrump": "Pahrump, Nevada", "valley_of_fire": "Valley of Fire State Park",
    "mesquite": "Mesquite, Nevada", "moapa": "Moapa Valley, Nevada", "beatty": "Beatty, Nevada",
    "laughlin": "Laughlin, Nevada", "ely": "Ely, Nevada", "carson_city": "Carson City, Nevada",
    "barstow": "Barstow, California", "calico": "Calico, San Bernardino County, California",
    "needles": "Needles, California", "stovepipe": "Stovepipe Wells, California",
    "willow_springs": "Willow Springs International Motorsports Park",
    "buttonwillow": "Buttonwillow Raceway Park", "auto_club": "Auto Club Speedway",
    "chuckwalla": "Chuckwalla Valley Raceway", "thunderhill": "Thunderhill Raceway Park",
    "sonoma": "Sonoma Raceway", "east_la": "East Los Angeles, California",
    "artesia": "Artesia, California", "san_diego": "San Diego",
    "sf_chinatown": "Chinatown, San Francisco", "sf_north_beach": "North Beach, San Francisco",
    "sf_mission": "Mission District, San Francisco", "bakersfield": "Bakersfield, California",
    "fresno": "Fresno, California", "bishop": "Bishop, California",
    "palm_springs": "Palm Springs, California", "flagstaff": "Flagstaff, Arizona",
    "williams": "Williams, Arizona", "kingman": "Kingman, Arizona", "page": "Page, Arizona",
    "phoenix": "Phoenix, Arizona", "tucson": "Tucson, Arizona", "nogales": "Nogales, Arizona",
    "st_george": "St. George, Utah", "springdale": "Springdale, Utah",
    "cedar_city": "Cedar City, Utah", "kanab": "Kanab, Utah", "moab": "Moab, Utah",
    "park_city": "Park City, Utah", "seven_magic": "Seven Magic Mountains",
    "salvation_mountain": "Salvation Mountain", "willow_creek": "Willow Creek, California",
    "san_jose": "San Jose, California", "berkeley": "Berkeley, California",
    "sacramento": "Sacramento, California", "stockton": "Stockton, California",
    "santa_barbara": "Santa Barbara, California", "ventura": "Ventura, California",
    "oceanside": "Oceanside, California", "riverside": "Riverside, California",
    "pasadena": "Pasadena, California", "palm_desert": "Palm Desert, California",
    "gilroy": "Gilroy, California", "napa": "Napa, California",
    "half_moon_bay": "Half Moon Bay, California", "redding": "Redding, California",
}


def get(url, binary=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=25) as r:
        data = r.read()
    return data if binary else json.loads(data)


def summary(title):
    return get("https://en.wikipedia.org/api/rest_v1/page/summary/"
               + urllib.parse.quote(title.replace(" ", "_"), safe=",()_-"))


def license_for(image_url):
    """Commons extmetadata for the lead image (artist + license), best effort."""
    try:
        fname = urllib.parse.unquote(image_url.rsplit("/", 1)[-1])
        if fname.endswith((".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG")):
            api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
                   "&prop=imageinfo&iiprop=extmetadata&titles=File:"
                   + urllib.parse.quote(fname))
            pages = get(api)["query"]["pages"]
            meta = next(iter(pages.values()))["imageinfo"][0]["extmetadata"]
            return {"artist": _strip(meta.get("Artist", {}).get("value", "")),
                    "license": meta.get("LicenseShortName", {}).get("value", ""),
                    "file": f"File:{fname}"}
    except Exception:
        pass
    return {"artist": "", "license": "", "file": ""}


def _strip(html):
    import re
    return re.sub(r"<[^>]+>", "", html or "").strip()[:120]


def fetch_one(pid, title, want_image=True):
    s = summary(title)
    coord = s.get("coordinates") or {}
    img = (s.get("originalimage") or {}).get("source", "")
    out = {
        "title": s.get("title", title),
        "extract": (s.get("extract") or "")[:900],
        "lat": coord.get("lat"), "lon": coord.get("lon"),
        "image": img,
        "wiki": (s.get("content_urls") or {}).get("desktop", {}).get("page", ""),
    }
    if want_image and img:
        out.update(license_for(img))
        dest = IMG_DIR / f"{pid}{Path(urllib.parse.urlparse(img).path).suffix.lower()}"
        if not dest.exists():
            try:
                dest.write_bytes(get(img, binary=True))
            except Exception as e:
                out["img_error"] = str(e)[:80]
        out["img_file"] = dest.name if dest.exists() else ""
    return out


def main():
    src_path = OUT_DIR / "source.json"
    db = json.loads(src_path.read_text()) if src_path.exists() else {"towns": {}, "existing": {}}
    jobs = ([("towns", pid, meta["title"]) for pid, meta in TOWNS.items()]
            + [("existing", pid, t) for pid, t in EXISTING_TITLES.items()])
    done = err = 0
    for bucket, pid, title in jobs:
        if pid in db[bucket] and db[bucket][pid].get("extract") and db[bucket][pid].get("img_file"):
            continue
        try:
            rec = fetch_one(pid, title)
            if bucket == "towns":
                rec.update({k: TOWNS[pid][k] for k in ("region", "kind", "terrain", "services")})
            db[bucket][pid] = rec
            done += 1
        except Exception as e:
            db[bucket].setdefault(pid, {})["error"] = f"{type(e).__name__}: {e}"[:120]
            err += 1
        time.sleep(0.15)
        if (done + err) % 25 == 0:
            src_path.write_text(json.dumps(db, indent=1, ensure_ascii=False))
            print(f"  …{done} fetched, {err} errors", flush=True)
    src_path.write_text(json.dumps(db, indent=1, ensure_ascii=False))
    towns_ok = sum(1 for r in db["towns"].values() if r.get("extract"))
    img_ok = sum(1 for b in db.values() for r in b.values() if r.get("img_file"))
    print(f"towns with facts: {towns_ok}/{len(TOWNS)} · images on disk: {img_ok} · errors: {err}")
    bad = [p for b in db.values() for p, r in b.items() if r.get("error") or not r.get("extract")]
    if bad:
        print("needs attention:", " ".join(bad[:20]))


if __name__ == "__main__":
    main()
