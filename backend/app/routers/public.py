from fastapi import APIRouter, Query, Request

from app.config import settings
from app.limiter import limiter
from app.services import country

router = APIRouter()


@router.get("/config")
@limiter.limit("30/minute")
async def get_config(
    request: Request,
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
) -> dict:
    """Country profile for the reporter's location (F-35); COUNTRY_PROFILE fallback without it."""
    code, detected, label = country.fallback_code(), False, None
    if lat is not None and lng is not None:
        found, label = await country.detect(lat, lng)
        if found:
            code, detected = country.profile_code(found), True
    return {
        "country": code,
        "detected": detected,
        "location_label": label,
        **country.get_profile(code),
        "vapid_public_key": settings.VAPID_PUBLIC_KEY or None,
        "telegram_bot_username": settings.TELEGRAM_BOT_USERNAME or None,
        "app_env": settings.APP_ENV,
    }
