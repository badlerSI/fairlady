#!/usr/bin/env python3
"""Merge the gazetteer into the game: new town POIs (facts + judged beats + wm scenes),
wm scenes for existing fallback POIs, and ATTRIBUTION.md for the Wikimedia imagery.

Inputs:  data/gazetteer/source.json   (facts/coords/images — tools/gazetteer_fetch.py)
         data/gazetteer/beats.json    (id → beat, from the beat-evolution workflow)
Outputs: backend/content/pois.json    (updated in place, idempotent)
         ATTRIBUTION.md
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = json.loads((ROOT / "data/gazetteer/source.json").read_text())
BEATS_PATH = ROOT / "data/gazetteer/beats.json"
BEATS = json.loads(BEATS_PATH.read_text()) if BEATS_PATH.exists() else {}
POIS_PATH = ROOT / "backend/content/pois.json"
WM_DIR = ROOT / "frontend/scenes_wm"

BBOX = {"min_lat": 31.0, "max_lat": 42.5, "min_lon": -124.7, "max_lon": -108.7}
NAME_OVERRIDES = {
    "venice_beach": "Venice Beach", "koreatown_la": "Koreatown",
    "mount_shasta_city": "Mount Shasta", "eureka_ca": "Eureka, CA",
    "wendover_ut": "Wendover", "nevada_city_ca": "Nevada City",
}


def first_sentence(text, cap=180):
    s = (text or "").split(". ")[0].strip()
    return (s[: cap - 1] + "…") if len(s) > cap else (s + "." if s and not s.endswith(".") else s)


def main():
    db = json.loads(POIS_PATH.read_text())
    have = {p["id"] for p in db["pois"]} | {db["start"]["id"]}

    added = scened = skipped = 0
    for pid, r in SRC["towns"].items():
        if pid in have:
            continue
        lat, lon = r.get("lat"), r.get("lon")
        if lat is None or not (BBOX["min_lat"] <= lat <= BBOX["max_lat"]
                               and BBOX["min_lon"] <= lon <= BBOX["max_lon"]):
            print(f"  skip {pid}: coords missing/out of box ({lat},{lon})")
            skipped += 1
            continue
        entry = {
            "id": pid,
            "name": NAME_OVERRIDES.get(pid, r["title"].split(",")[0].strip()),
            "kind": r.get("kind", "city"),
            "region": r["region"],
            "lat": round(lat, 5), "lon": round(lon, 5),
            "services": (r.get("services") if r.get("services") is not None
                         else ["gas", "lodging", "food"]),
            "blurb": first_sentence(r.get("extract", "")),
        }
        if r.get("terrain", 1.0) != 1.0:
            entry["terrain"] = r["terrain"]
        beat = BEATS.get(pid, "").strip()
        if beat:
            entry["beat"] = beat
        if (WM_DIR / f"{pid}.png").exists():
            entry["scene"] = f"wm_{pid}"
        db["pois"].append(entry)
        added += 1

    for pid, r in SRC["existing"].items():
        if not (WM_DIR / f"{pid}.png").exists():
            continue
        for p in db["pois"]:
            if p["id"] == pid and not p.get("scene"):
                p["scene"] = f"wm_{pid}"
                scened += 1

    POIS_PATH.write_text(json.dumps(db, indent=1, ensure_ascii=False))

    rows = []
    for bucket in ("towns", "existing"):
        for pid, r in sorted(SRC[bucket].items()):
            if r.get("img_file") and (WM_DIR / f"{pid}.png").exists():
                artist = re.sub(r"\s+", " ", r.get("artist", "")).strip() or "unknown"
                rows.append(f"| `{pid}` | {r.get('title','')} | {r.get('file','')} | "
                            f"{artist} | {r.get('license','') or 'see file page'} |")
    (ROOT / "ATTRIBUTION.md").write_text(
        "# Imagery attribution\n\n"
        "The in-game place sketches under `frontend/scenes_wm/` are 1-bit cyan posterizations\n"
        "derived from the lead images of the corresponding English Wikipedia articles\n"
        "(via Wikimedia Commons). Each derivative inherits its source license. Sources:\n\n"
        "| scene | place | source file | author | license |\n|---|---|---|---|---|\n"
        + "\n".join(rows) + "\n")

    beats_n = sum(1 for p in db["pois"] if p.get("beat"))
    print(f"towns added: {added} (skipped {skipped}) · existing POIs given wm scenes: {scened}")
    print(f"pois total: {len(db['pois'])} · with beats: {beats_n} · attribution rows: {len(rows)}")


if __name__ == "__main__":
    main()
