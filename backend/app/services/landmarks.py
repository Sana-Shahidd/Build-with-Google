"""Landmark lines (F-38, docs/07_AI_AGENTS.md section 6.9): OSM landmarks -> directions people can follow.

Code fetches and ranks the landmarks; the Landmark Agent (optional) only phrases them; validation and
the template autopilot guarantee the line never contains an invented place or distance.
"""

import logging
import re

import httpx
from geopy.distance import geodesic

from app.config import LANDMARK_MAX, LANDMARK_RADIUS_M, LANDMARK_TIMEOUT_S, settings
from app.models.ai import Landmark

logger = logging.getLogger(__name__)

COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
COMPASS_WORD = {
    "en": dict(zip(COMPASS, COMPASS, strict=True)),
    "es": dict(
        zip(
            COMPASS,
            [
                "norte",
                "noreste",
                "este",
                "sureste",
                "sur",
                "suroeste",
                "oeste",
                "noroeste",
            ],
            strict=True,
        )
    ),
    "ur": dict(
        zip(
            COMPASS,
            [
                "شمال",
                "شمال مشرق",
                "مشرق",
                "جنوب مشرق",
                "جنوب",
                "جنوب مغرب",
                "مغرب",
                "شمال مغرب",
            ],
            strict=True,
        )
    ),
}
_URDU_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# lower index = more useful to a driver
PRIORITY = [
    "place_of_worship",
    "fuel",
    "hospital",
    "school",
    "college",
    "university",
    "bank",
    "junction",
    "bridge",
    "marketplace",
    "mall",
    "bus_stop",
    "neighbourhood",
    "police",
    "fire_station",
]

QUERY = """[out:json][timeout:6];
(
  nwr["amenity"~"^(place_of_worship|fuel|hospital|school|college|university|bank|marketplace|police|fire_station)$"]["name"](around:{r},{lat},{lng});
  nwr["shop"="mall"]["name"](around:{r},{lat},{lng});
  nwr["highway"="bus_stop"]["name"](around:{r},{lat},{lng});
  nwr["junction"="roundabout"]["name"](around:{r},{lat},{lng});
  nwr["bridge"="yes"]["name"](around:{r},{lat},{lng});
  nwr["place"~"^(neighbourhood|suburb|quarter)$"]["name"](around:{r},{lat},{lng});
);
out center 40;"""


def compass(from_pt: tuple[float, float], to_pt: tuple[float, float]) -> str:
    """8-point compass direction of `to_pt` as seen from `from_pt` (the incident)."""
    import math

    (lat1, lng1), (lat2, lng2) = from_pt, to_pt
    bearing = (
        math.degrees(
            math.atan2((lng2 - lng1) * math.cos(math.radians(lat1)), lat2 - lat1)
        )
        % 360
    )
    return COMPASS[round(bearing / 45) % 8]


def kind_of(tags: dict) -> str:
    if tags.get("junction") == "roundabout":
        return "junction"
    if tags.get("bridge") == "yes":
        return "bridge"
    if tags.get("highway") == "bus_stop":
        return "bus_stop"
    if tags.get("shop") == "mall":
        return "mall"
    if "place" in tags:
        return "neighbourhood"
    return tags.get("amenity", "other")


def _name(tags: dict, lang: str) -> str | None:
    order = ("name:ur", "name:en", "name") if lang == "ur" else ("name:en", "name")
    return next((tags[k] for k in order if tags.get(k)), None)


def rank(elements: list[dict], lat: float, lng: float, lang: str) -> list[Landmark]:
    """Drop unnamed, measure, sort by (priority, distance), keep LANDMARK_MAX."""
    found = []
    for el in elements:
        tags = el.get("tags", {})
        name = _name(tags, lang)
        elat = el.get("lat") or el.get("center", {}).get("lat")
        elng = el.get("lon") or el.get("center", {}).get("lon")
        if not name or elat is None or elng is None:
            continue
        d = int(geodesic((lat, lng), (elat, elng)).m)
        if d > LANDMARK_RADIUS_M:
            continue
        kind = kind_of(tags)
        found.append(
            (
                PRIORITY.index(kind) if kind in PRIORITY else 99,
                d,
                kind,
                name[:80],
                compass((lat, lng), (elat, elng)),
            )
        )
    found.sort(key=lambda x: (x[0], x[1]))
    seen: set[str] = set()
    out: list[Landmark] = []
    for _, d, kind, name, direction in found:
        if name in seen:
            continue
        seen.add(name)
        out.append(
            Landmark(
                index=len(out) + 1,
                kind=kind,
                name=name,
                distance_m=d,
                compass=direction,
            )
        )
        if len(out) == LANDMARK_MAX:
            break
    return out


async def nearby_landmarks(lat: float, lng: float, lang: str = "en") -> list[Landmark]:
    """Landmarks within LANDMARK_RADIUS_M via OpenStreetMap Overpass. [] on any failure (alerts go on)."""
    query = QUERY.format(r=LANDMARK_RADIUS_M, lat=lat, lng=lng)
    try:
        async with httpx.AsyncClient(timeout=LANDMARK_TIMEOUT_S) as client:
            resp = await client.post(
                settings.OVERPASS_URL,
                data={"data": query},
                headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
            )
            resp.raise_for_status()
            return rank(resp.json()["elements"], lat, lng, lang)
    except (httpx.HTTPError, KeyError, ValueError) as e:
        logger.warning("overpass landmarks failed: %s", type(e).__name__)
        return []


def validate_landmark_line(
    line_local: str, line_en: str, used: list[int], landmarks: list[Landmark]
) -> bool:
    """Names and distances must come from the given list (no invented places or numbers)."""
    by_index = {lm.index: lm for lm in landmarks}
    if not used or not set(used) <= set(by_index):
        return False
    if not line_en or len(line_en) > 160 or len(line_local) > 160:
        return False
    if re.search(r"https?://|www\.", line_en + line_local, re.IGNORECASE):
        return False
    if not all(by_index[i].name in line_en for i in used):
        return False
    allowed = [lm.distance_m for lm in landmarks]
    for text in (line_local, line_en):
        for m in re.findall(r"\d+", text.translate(_URDU_DIGITS)):
            if not any(abs(int(m) - a) <= 50 for a in allowed):
                return False
    return True


def template_landmark_line(landmarks: list[Landmark], lang: str) -> str:
    """Autopilot line (no LLM). Empty string when there are no landmarks."""
    if not landmarks:
        return ""
    a = landmarks[0]
    b = landmarks[1] if len(landmarks) > 1 else None
    word = COMPASS_WORD.get(lang, COMPASS_WORD["en"])
    if lang == "ur":
        line = f"{a.name} کے قریب ({a.distance_m} میٹر {word[a.compass]})"
        return line + (f"، {b.name} کے نزدیک۔" if b else "۔")
    if lang == "es":
        line = f"Cerca de {a.name} ({a.distance_m} m {word[a.compass]})"
        return line + (f", junto a {b.name}." if b else ".")
    line = f"Near {a.name} ({a.distance_m} m {a.compass})"
    return line + (f", close to {b.name}." if b else ".")


def used_for_template(landmarks: list[Landmark]) -> list[int]:
    return [lm.index for lm in landmarks[:2]]


__all__ = [
    "nearby_landmarks",
    "rank",
    "template_landmark_line",
    "validate_landmark_line",
]
