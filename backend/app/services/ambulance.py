"""Ambulance simulation (F-26): assign the nearest available ambulances to a verified incident and move them
along OSRM route geometry. Code only. Stages: en_route_scene -> at_scene (30 s) -> en_route_hospital ->
at_hospital (30 s) -> available. `jobs/ambulance_sim.py` calls `tick()` every second."""

import asyncio
import math
from datetime import UTC, datetime
from uuid import UUID

from geopy.distance import distance

from app.deps import get_supabase
from app.services import events, routing_osrm
from app.utils.geo import to_ewkt

SPEED_MPS = 40_000 / 3600  # 40 km/h-equivalent
DWELL_S = 30
MAX_AMBULANCES = 6


def ambulances_needed(casualties_max: int) -> int:
    return max(1, min(MAX_AMBULANCES, math.ceil(casualties_max / 2)))


def route_length_m(coords: list[list[float]]) -> float:
    """Length of a GeoJSON coordinate list ([lng, lat] pairs) in metres."""
    return sum(
        distance((a[1], a[0]), (b[1], b[0])).m
        for a, b in zip(coords, coords[1:], strict=False)
    )


def point_along(coords: list[list[float]], progress_m: float) -> tuple[float, float]:
    """(lat, lng) at `progress_m` metres along the line; clamps to both ends."""
    if progress_m <= 0 or len(coords) == 1:
        return coords[0][1], coords[0][0]
    left = progress_m
    for a, b in zip(coords, coords[1:], strict=False):
        seg = distance((a[1], a[0]), (b[1], b[0])).m
        if seg and left <= seg:
            f = left / seg
            return a[1] + (b[1] - a[1]) * f, a[0] + (b[0] - a[0]) * f
        left -= seg
    return coords[-1][1], coords[-1][0]


async def _db(fn):
    return await asyncio.to_thread(fn)


async def _line(a: tuple[float, float], b: tuple[float, float]) -> list[list[float]]:
    """OSRM geometry, or a straight two-point line when OSRM is unavailable."""
    geo = await routing_osrm.route_geojson(a, b)
    if geo and len(geo.get("coordinates", [])) >= 2:
        return geo["coordinates"]
    return [[a[1], a[0]], [b[1], b[0]]]


async def assign_if_needed(incident_id: UUID | str) -> int:
    """Send ambulances to a verified incident that needs one. Idempotent: does nothing if any are already
    assigned to it. Returns how many were dispatched."""
    sb = get_supabase()
    iid = str(incident_id)
    inc = (
        await _db(
            lambda: sb.table("incidents").select("*").eq("id", iid).execute().data
        )
    )[0]
    if (
        inc["status"] != "verified"
        or "ambulance" not in inc["needs"]
        or inc["lat"] is None
    ):
        return 0
    busy = await _db(
        lambda: (
            sb.table("ambulances").select("id").eq("incident_id", iid).execute().data
        )
    )
    if busy:
        return 0
    fleet = await _db(
        lambda: (
            sb.table("ambulances").select("*").eq("status", "available").execute().data
        )
    )
    scene = (inc["lat"], inc["lng"])
    fleet.sort(key=lambda a: distance((a["lat"], a["lng"]), scene).m)
    chosen = fleet[: ambulances_needed(inc["est_casualties_max"])]
    hospitals = await _db(
        lambda: (
            sb.table("hospital_assignments")
            .select("hospital_id")
            .eq("incident_id", iid)
            .gt("assigned_casualties", 0)
            .order("eta_minutes")
            .execute()
            .data
        )
    )
    now = datetime.now(UTC).isoformat()
    for i, amb in enumerate(chosen):
        line = await _line((amb["lat"], amb["lng"]), scene)
        patch = {
            "status": "en_route_scene",
            "incident_id": iid,
            "destination_hospital_id": hospitals[i % len(hospitals)]["hospital_id"]
            if hospitals
            else None,
            "route": line,
            "route_progress_m": 0,
            "route_length_m": route_length_m(line),
            "stage_started_at": now,
            "updated_at": now,
        }
        await _db(
            lambda patch=patch, amb=amb: (
                sb.table("ambulances").update(patch).eq("id", amb["id"]).execute()
            )
        )
        await events.add(
            iid,
            "ambulance_status",
            f"{amb['call_sign']} en route to the scene, ETA {patch['route_length_m'] / SPEED_MPS / 60:.0f} min",
        )
    return len(chosen)


async def _advance(amb: dict, dt: float) -> None:
    """Move one ambulance by `dt` seconds of simulated time and handle stage changes."""
    sb = get_supabase()
    now = datetime.now(UTC)
    patch: dict = {"updated_at": now.isoformat()}
    stage = amb["status"]
    if stage in ("en_route_scene", "en_route_hospital"):
        progress = amb["route_progress_m"] + SPEED_MPS * dt
        line = amb["route"]
        lat, lng = point_along(line, progress)
        patch.update(route_progress_m=progress, location=to_ewkt(lat, lng))
        if progress >= amb["route_length_m"]:
            patch["stage_started_at"] = now.isoformat()
            patch["status"] = "at_scene" if stage == "en_route_scene" else "at_hospital"
            await events.add(
                amb["incident_id"],
                "ambulance_status",
                f"{amb['call_sign']} {'at the scene' if stage == 'en_route_scene' else 'at the hospital'}",
            )
    else:  # dwelling at the scene or the hospital
        started = datetime.fromisoformat(amb["stage_started_at"])
        if (now - started).total_seconds() >= DWELL_S:
            if stage == "at_scene" and amb["destination_hospital_id"]:
                hosp = (
                    await _db(
                        lambda: (
                            sb.table("organizations")
                            .select("lat,lng")
                            .eq("id", amb["destination_hospital_id"])
                            .execute()
                            .data
                        )
                    )
                )[0]
                here = point_along(amb["route"], amb["route_length_m"])
                line = await _line(here, (hosp["lat"], hosp["lng"]))
                patch.update(
                    status="en_route_hospital",
                    route=line,
                    route_progress_m=0,
                    route_length_m=route_length_m(line),
                    stage_started_at=now.isoformat(),
                )
                await events.add(
                    amb["incident_id"],
                    "ambulance_status",
                    f"{amb['call_sign']} taking patients to hospital",
                )
            else:
                patch.update(
                    status="available",
                    incident_id=None,
                    destination_hospital_id=None,
                    route=None,
                    route_progress_m=0,
                    route_length_m=None,
                )
    await _db(
        lambda: sb.table("ambulances").update(patch).eq("id", amb["id"]).execute()
    )


async def tick(dt: float = 1.0) -> int:
    """Advance every busy ambulance. Returns how many moved."""
    sb = get_supabase()
    busy = await _db(
        lambda: (
            sb.table("ambulances").select("*").neq("status", "available").execute().data
        )
    )
    for amb in busy:
        try:
            await _advance(amb, dt)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("ambulance tick failed")
    return len(busy)
