"""Place Plan service (F-37): a shop/school/mosque registered in advance with a nearest-hospital
snapshot and a "press for help" QR. Code only (no LLM). Stores no personal data beyond the owner id."""

import asyncio
import secrets
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import CARD_TOKEN_BYTES
from app.deps import get_supabase
from app.services import country, geocode, landmarks, matching
from app.utils.geo import to_ewkt

PLACE_TYPES = "^(home|shop|school|mosque|factory|office|other)$"
NEAREST_COUNT = 3


class PlaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    place_type: str = Field(pattern=PLACE_TYPES)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    lang: str = Field(default="ur", pattern="^(en|es|ur)$")
    consent: bool


def new_token() -> str:
    return secrets.token_urlsafe(CARD_TOKEN_BYTES)


async def nearest_snapshot(lat: float, lng: float) -> list[dict]:
    """The 3 nearest accepting hospitals with distance and ETA (reuses matching.hospital_options)."""
    probe = {
        "lat": lat,
        "lng": lng,
        "injury_types": [],
        "est_casualties_max": 1,
        "needs": ["ambulance"],
        "severity": "medium",
    }
    opts = await matching.hospital_options(probe)
    nearest = sorted(opts.hospitals, key=lambda h: h.distance_m)[:NEAREST_COUNT]
    sb = get_supabase()
    phones: dict[str, str | None] = {}
    if nearest:
        rows = await asyncio.to_thread(
            lambda: (
                sb.table("organizations")
                .select("id,public_phone")
                .in_("id", [h.id for h in nearest])
                .execute()
                .data
            )
        )
        phones = {r["id"]: r["public_phone"] for r in rows}
    return [
        {
            "org_id": h.id,
            "name": h.name,
            "type": "hospital",
            "distance_m": round(h.distance_m),
            "eta_min": round(h.eta_minutes),
            "phone": phones.get(h.id),
        }
        for h in nearest
    ]


async def landmark_lines(
    lat: float, lng: float, lang: str
) -> tuple[str | None, str | None]:
    """(English line, local line) from the F-38 template; (None, None) when OSM has nothing."""
    found = await landmarks.nearby_landmarks(lat, lng, lang)
    if not found:
        return None, None
    en = landmarks.template_landmark_line(found, "en")
    local = landmarks.template_landmark_line(found, lang) if lang != "en" else en
    return en, local


async def create_place(user_id: UUID, data: PlaceCreate) -> dict:
    nearest, label, (lm_en, lm_local) = await asyncio.gather(
        nearest_snapshot(data.lat, data.lng),
        geocode.reverse_label(data.lat, data.lng),
        landmark_lines(data.lat, data.lng, data.lang),
    )
    sb = get_supabase()
    row = {
        "owner_user_id": str(user_id),
        "token": new_token(),
        "name": data.name,
        "place_type": data.place_type,
        "location": to_ewkt(data.lat, data.lng),
        "location_label": label,
        "landmark_text": lm_en,
        "landmark_local": lm_local,
        "nearest": nearest,
        "lang": data.lang,
        "consent_at": datetime.now(UTC).isoformat(),
    }
    res = await asyncio.to_thread(lambda: sb.table("place_plans").insert(row).execute())
    return res.data[0]


async def public_view(token: str) -> dict | None:
    """Only what the poster/scan page shows. Unknown or inactive token -> None (same 404)."""
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("place_plans")
            .select("*")
            .eq("token", token)
            .eq("active", True)
            .execute()
            .data
        )
    )
    if not rows:
        return None
    p = rows[0]
    profile = country.get_profile(country.fallback_code())
    return {
        "name": p["name"],
        "place_type": p["place_type"],
        "location_label": p["location_label"],
        "landmark_local": p["landmark_local"],
        "nearest": p["nearest"],
        "emergency_numbers": profile["emergency_numbers"],
        "lang": p["lang"],
    }
