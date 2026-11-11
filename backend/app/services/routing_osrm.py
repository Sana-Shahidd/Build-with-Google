"""OSRM routing/ETA with straight-line fallback (docs/03_TRD.md §8).

Our tuples are (lat, lng); OSRM URLs use lng,lat. Conversion happens ONLY in this file.
"""

import logging

import httpx
from geopy.distance import distance

from app.config import FALLBACK_SPEED_KMH, OSRM_TIMEOUT_S, settings

logger = logging.getLogger(__name__)
LatLng = tuple[float, float]


def _coords(points: list[LatLng]) -> str:
    return ";".join(f"{lng},{lat}" for lat, lng in points)


def fallback_minutes(a: LatLng, b: LatLng) -> float:
    return distance(a, b).km / FALLBACK_SPEED_KMH * 60


async def etas_minutes(origin: LatLng, dests: list[LatLng]) -> list[float]:
    """Driving minutes origin -> each destination; straight-line / 25 km/h if OSRM fails (3 s)."""
    if not dests:
        return []
    url = f"{settings.OSRM_BASE_URL}/table/v1/driving/{_coords([origin, *dests])}"
    try:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT_S) as client:
            resp = await client.get(
                url, params={"sources": 0, "annotations": "duration"}
            )
            resp.raise_for_status()
            row = resp.json()["durations"][0][1:]
        if len(row) == len(dests) and all(s is not None for s in row):
            return [s / 60 for s in row]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        logger.warning("osrm table failed: %s", type(e).__name__)
    return [fallback_minutes(origin, d) for d in dests]


async def route_geojson(a: LatLng, b: LatLng) -> dict | None:
    """GeoJSON LineString (coordinates [lng, lat]) or None on failure."""
    url = f"{settings.OSRM_BASE_URL}/route/v1/driving/{_coords([a, b])}"
    try:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT_S) as client:
            resp = await client.get(
                url, params={"overview": "full", "geometries": "geojson"}
            )
            resp.raise_for_status()
            return resp.json()["routes"][0]["geometry"]
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
        logger.warning("osrm route failed: %s", type(e).__name__)
        return None
