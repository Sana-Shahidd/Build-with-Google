import asyncio
import json
from pathlib import Path

from geopy.exc import GeopyError
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from app.config import settings

_PROFILES: dict[str, dict] = json.loads(
    (Path(__file__).parent.parent / "data" / "country_profiles.json").read_text(
        encoding="utf-8"
    )
)
_cache: dict[tuple[float, float], tuple[str | None, str | None]] = {}


def profile_code(code: str | None) -> str:
    """Known country code, else DEFAULT (international 112)."""
    code = (code or "").upper()
    return code if code in _PROFILES else "DEFAULT"


def get_profile(code: str | None) -> dict:
    return _PROFILES[profile_code(code)]


def fallback_code() -> str:
    return profile_code(settings.COUNTRY_PROFILE)


def _reverse(lat: float, lng: float) -> tuple[str | None, str | None]:
    geocoder = Nominatim(user_agent=settings.NOMINATIM_USER_AGENT, timeout=5)
    reverse = RateLimiter(geocoder.reverse, min_delay_seconds=1)
    loc = reverse((lat, lng), zoom=16, language="en", addressdetails=True)
    if loc is None:
        return None, None
    addr = loc.raw.get("address", {})
    code = addr.get("country_code")
    first = next(
        (addr[k] for k in ("amenity", "road", "neighbourhood", "suburb") if k in addr),
        None,
    )
    city = addr.get("city") or addr.get("town") or addr.get("village")
    label = ", ".join(p for p in (first, city) if p) or None
    return (code.upper() if code else None), label


async def detect(lat: float, lng: float) -> tuple[str | None, str | None]:
    """(country_code, location_label) from coordinates via Nominatim; (None, None) on failure."""
    key = (round(lat, 3), round(lng, 3))
    if key not in _cache:
        try:
            _cache[key] = await asyncio.to_thread(_reverse, lat, lng)
        except (GeopyError, OSError):
            return None, None
    return _cache[key]
