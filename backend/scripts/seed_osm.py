"""Seed hospitals, police, fire and rescue stations from OpenStreetMap (Overpass) into organizations.

Usage: python -m scripts.seed_osm [--country PK]
Uses the demo_city bbox of the country profile ([south, west, north, east]).
Rows are upserted by osm_ref with source='seed', is_mock=true; existing rows are never overwritten.
"""

import argparse
import asyncio
import sys

import httpx
import phonenumbers

from app.config import settings
from app.deps import get_supabase
from app.services import activity, country
from app.utils.geo import to_ewkt

# OSM tag -> organizations.type (docs/07_AI_AGENTS.md §12.1)
TAG_TO_TYPE = {
    ("amenity", "hospital"): "hospital",
    ("amenity", "police"): "police_station",
    ("amenity", "fire_station"): "fire_station",
    ("emergency", "ambulance_station"): "rescue_station",
}


def build_query(bbox: list[float]) -> str:
    s, w, n, e = bbox
    box = f"({s},{w},{n},{e})"
    parts = "".join(f'  nwr["{k}"="{v}"]{box};\n' for (k, v) in TAG_TO_TYPE)
    return f"[out:json][timeout:60];\n(\n{parts});\nout center;"


def org_type(tags: dict) -> str | None:
    return next((t for (k, v), t in TAG_TO_TYPE.items() if tags.get(k) == v), None)


def normalize_phone(raw: str | None, region: str | None) -> str | None:
    if not raw:
        return None
    try:
        num = phonenumbers.parse(raw.split(";")[0].strip(), region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(num):
        return None
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


def to_row(el: dict, region: str | None, lang: str) -> dict | None:
    tags = el.get("tags", {})
    kind = org_type(tags)
    name = tags.get("name:en") or tags.get("name")
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lng = el.get("lon") or el.get("center", {}).get("lon")
    if not (kind and name and lat is not None and lng is not None):
        return None
    return {
        "type": kind,
        "name": name[:200],
        "osm_ref": f"{el['type']}/{el['id']}",
        "source": "seed",
        "location": to_ewkt(lat, lng),
        "address": tags.get("addr:full") or tags.get("addr:street"),
        "public_phone": normalize_phone(
            tags.get("phone") or tags.get("contact:phone"), region
        ),
        "lang": lang,
        "is_mock": True,
    }


async def fetch(bbox: list[float]) -> list[dict]:
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            settings.OVERPASS_URL,
            data={"data": build_query(bbox)},
            headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
        )
        resp.raise_for_status()
        return resp.json()["elements"]


async def main(code: str) -> int:
    profile = country.get_profile(code)
    city = profile["demo_city"]
    elements = await fetch(city["bbox"])
    lang = profile["default_lang"]
    rows = {}
    for el in elements:
        row = to_row(el, profile["phone_region"], lang)
        if row:
            rows[row["osm_ref"]] = row
    sb = get_supabase()
    await asyncio.to_thread(
        lambda: (
            sb.table("organizations")
            .upsert(list(rows.values()), on_conflict="osm_ref", ignore_duplicates=True)
            .execute()
        )
    )
    counts: dict[str, int] = {}
    for r in rows.values():
        counts[r["type"]] = counts.get(r["type"], 0) + 1
    summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
    await activity.log(
        None,
        "orchestrator",
        "rule",
        f"Seeded {summary} near {city['name']} from OpenStreetMap",
    )
    print(f"{len(elements)} OSM elements, {len(rows)} usable: {summary}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", default=settings.COUNTRY_PROFILE)
    sys.exit(asyncio.run(main(parser.parse_args().country)))
