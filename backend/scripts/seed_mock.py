"""Mock capabilities, beds and ambulances for seeded organizations (is_mock = true).

Usage: python -m scripts.seed_mock [--demo-orgs]
  (default)    hospital_details for every hospital, 3 ambulances per rescue station
  --demo-orgs  also marks the demo hospital/police/rescue/fire nearest to the crash site; sets
               telegram_chat_id from DEMO_HOSPITAL_CHAT / DEMO_POLICE_CHAT when those are set,
               otherwise leaves it NULL (linked later in T-07). A second hospital gets 2 free beds.
Safe to re-run: hospital_details and ambulances are upserted.
"""

import argparse
import asyncio
import random
import sys

from geopy.distance import distance

from app.config import settings
from app.deps import get_supabase
from app.services import country, routing_osrm
from app.utils.geo import to_ewkt

# Ferozepur Road near Kalma Chowk (docs/12_TESTING_AND_DEMO.md §3)
CRASH_SITE = (31.5036, 74.3305)
EXTRA_CAPABILITIES = ["trauma", "burns", "neuro", "orthopedic", "cardiac", "pediatric"]
AMBULANCES_PER_STATION = 3


def mock_details(osm_ref: str) -> dict:
    """Deterministic pseudo-random capacity so re-runs give the same data."""
    rng = random.Random(osm_ref)
    caps = ["general", *rng.sample(EXTRA_CAPABILITIES, rng.randint(0, 3))]
    total = rng.randint(8, 40)
    return {
        "capabilities": caps,
        "er_beds_total": total,
        "er_beds_available": rng.randint(max(1, total // 5), max(2, total // 2)),
        "icu_available": rng.randint(0, 6),
        "accepting_patients": True,
        "capacity_known": True,
    }


def nearest(
    orgs: list[dict], kind: str, point: tuple[float, float], n: int = 1
) -> list[dict]:
    pool = [o for o in orgs if o["type"] == kind]
    return sorted(pool, key=lambda o: distance(point, (o["lat"], o["lng"])).km)[:n]


def chat_id(raw: str) -> int | None:
    return int(raw) if raw.strip().lstrip("-").isdigit() else None


async def demo_hospitals(orgs: list[dict], n: int = 2) -> list[dict]:
    """Hospitals nearest to the crash site by DRIVING time (the order Triage uses), best first."""
    near = nearest(orgs, "hospital", CRASH_SITE, 15)
    etas = await routing_osrm.etas_minutes(
        CRASH_SITE, [(h["lat"], h["lng"]) for h in near]
    )
    return [h for _, h in sorted(zip(etas, near, strict=True), key=lambda x: x[0])][:n]


def demo_updates(
    orgs: list[dict], hospitals: list[dict]
) -> tuple[dict[str, dict], dict[str, dict]]:
    """(organization updates by id, hospital_details overrides by id) for the demo scene."""
    org_updates: dict[str, dict] = {}
    detail_overrides: dict[str, dict] = {}
    if hospitals:
        first = hospitals[0]
        detail_overrides[first["id"]] = {
            "capabilities": ["general", "trauma", "burns", "neuro", "orthopedic"],
            "er_beds_total": 30,
            "er_beds_available": 12,
            "icu_available": 4,
        }
        chat = chat_id(settings.DEMO_HOSPITAL_CHAT)
        if chat:
            org_updates[first["id"]] = {"telegram_chat_id": chat}
    if len(hospitals) > 1:
        detail_overrides[hospitals[1]["id"]] = {
            "capabilities": ["general", "trauma"],
            "er_beds_available": 2,
            "er_beds_total": 20,
        }
    police = nearest(orgs, "police_station", CRASH_SITE)
    chat = chat_id(settings.DEMO_POLICE_CHAT)
    if police and chat:
        org_updates[police[0]["id"]] = {"telegram_chat_id": chat}
    return org_updates, detail_overrides


async def main(demo_orgs: bool) -> int:
    sb = get_supabase()
    orgs = (
        await asyncio.to_thread(lambda: sb.table("organizations").select("*").execute())
    ).data
    details = {
        o["id"]: {"org_id": o["id"], **mock_details(o["osm_ref"] or o["id"])}
        for o in orgs
        if o["type"] == "hospital"
    }
    org_updates: dict[str, dict] = {}
    if demo_orgs:
        org_updates, overrides = demo_updates(orgs, await demo_hospitals(orgs))
        for org_id, patch in overrides.items():
            details[org_id].update(patch)

    prefix = country.get_profile(settings.COUNTRY_PROFILE)["ambulance_call_sign_prefix"]
    ambulances = []
    for station in (o for o in orgs if o["type"] == "rescue_station"):
        for i in range(1, AMBULANCES_PER_STATION + 1):
            sid = station["id"][:4].upper()
            ambulances.append(
                {
                    "station_id": station["id"],
                    "call_sign": f"{prefix}-{sid}-{i:02d}",
                    "status": "available",
                    "location": to_ewkt(station["lat"], station["lng"]),
                }
            )

    def write() -> None:
        if details:
            sb.table("hospital_details").upsert(
                list(details.values()), on_conflict="org_id"
            ).execute()
        if ambulances:
            sb.table("ambulances").upsert(ambulances, on_conflict="call_sign").execute()
        for org_id, patch in org_updates.items():
            sb.table("organizations").update(patch).eq("id", org_id).execute()

    await asyncio.to_thread(write)
    print(
        f"hospital_details: {len(details)}, ambulances: {len(ambulances)}, "
        f"demo orgs with Telegram chat set: {len(org_updates)}"
    )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-orgs", action="store_true")
    sys.exit(asyncio.run(main(parser.parse_args().demo_orgs)))
