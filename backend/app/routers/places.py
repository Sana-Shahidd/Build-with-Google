"""Place Plan endpoints (docs/06_API_SPEC.md, F-37). The `/places/draft` voice prefill belongs to the
Preparedness Agent (cut in this build)."""

import asyncio
from uuid import UUID, uuid4

import segno
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.agents import orchestrator
from app.config import CARD_ALERT_RATE, CARD_SCAN_RATE, settings
from app.deps import CurrentUser, get_current_user, get_supabase
from app.limiter import limiter, user_or_ip
from app.services import audit, crypto, places
from app.utils.errors import ApiError
from app.utils.geo import to_ewkt

router = APIRouter()


async def _owned(place_id: UUID, user: CurrentUser) -> dict:
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("place_plans")
            .select("*")
            .eq("id", str(place_id))
            .eq("owner_user_id", str(user.id))
            .execute()
            .data
        )
    )
    if not rows:
        raise ApiError(404, "NOT_FOUND", "Place not found")
    return rows[0]


def _scan_url(token: str) -> str:
    return f"{(settings.PUBLIC_BASE_URL or settings.FRONTEND_BASE_URL).rstrip('/')}/p/{token}"


@router.post("/places", status_code=201)
@limiter.limit("10/hour", key_func=user_or_ip)
async def create_place(
    request: Request,
    body: places.PlaceCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if not body.consent:
        raise ApiError(400, "VALIDATION_ERROR", "consent must be true")
    place = await places.create_place(user.id, body)
    await audit.log(
        "reporter", "place_created", "place_plan", place["id"], actor_id=str(user.id)
    )
    return {
        "place_id": place["id"],
        "token": place["token"],
        "scan_url": _scan_url(place["token"]),
        "print_url": f"/place/{place['id']}/print",
    }


@router.get("/places/me")
@limiter.limit("30/minute")
async def my_places(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("place_plans")
            .select("*")
            .eq("owner_user_id", str(user.id))
            .order("created_at", desc=True)
            .execute()
            .data
        )
    )
    return {
        "places": [
            {
                "place_id": p["id"],
                "name": p["name"],
                "place_type": p["place_type"],
                "location_label": p["location_label"],
                "landmark_local": p["landmark_local"],
                "nearest": p["nearest"],
                "active": p["active"],
                "scan_url": _scan_url(p["token"]),
            }
            for p in rows
        ]
    }


@router.get("/places/{place_id}/qr.svg")
@limiter.limit("30/minute")
async def place_qr(
    request: Request, place_id: UUID, user: CurrentUser = Depends(get_current_user)
) -> Response:
    place = await _owned(place_id, user)
    svg = segno.make(_scan_url(place["token"]), error="q").svg_inline(scale=8, border=2)
    return Response(content=svg, media_type="image/svg+xml")


@router.delete("/places/{place_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_place(
    request: Request, place_id: UUID, user: CurrentUser = Depends(get_current_user)
) -> Response:
    await _owned(place_id, user)
    sb = get_supabase()
    await asyncio.to_thread(
        lambda: sb.table("place_plans").delete().eq("id", str(place_id)).execute()
    )
    await audit.log(
        "reporter", "place_deleted", "place_plan", str(place_id), actor_id=str(user.id)
    )
    return Response(status_code=204)


@router.get("/public/place/{token}")
@limiter.limit(CARD_SCAN_RATE)
async def public_place(request: Request, token: str) -> dict:
    view = await places.public_view(token)
    if view is None:
        raise ApiError(404, "NOT_FOUND", "Place not found")
    return view


class PlaceAlertBody(BaseModel):
    client_report_id: UUID


@router.post("/public/place/{token}/alert", status_code=202)
@limiter.limit(CARD_ALERT_RATE, key_func=user_or_ip)
async def place_alert(
    request: Request,
    token: str,
    body: PlaceAlertBody,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """'Press for help' on a place poster: an SOS report at the place's fixed location."""
    sb = get_supabase()
    found = await asyncio.to_thread(
        lambda: (
            sb.table("place_plans")
            .select("id,lat,lng,lang")
            .eq("token", token)
            .eq("active", True)
            .execute()
            .data
        )
    )
    if not found:
        raise ApiError(404, "NOT_FOUND", "Place not found")
    place = found[0]
    existing = await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .select("id")
            .eq("client_report_id", str(body.client_report_id))
            .eq("reporter_id", str(user.id))
            .execute()
            .data
        )
    )
    if existing:
        return JSONResponse(status_code=200, content={"report_id": existing[0]["id"]})
    report_id = uuid4()
    row = {
        "id": str(report_id),
        "client_report_id": str(body.client_report_id),
        "reporter_id": str(user.id),
        "channel": "app",
        "input_type": "sos",
        "place_id": place["id"],
        "location": to_ewkt(place["lat"], place["lng"]),
        "accuracy_m": 10,  # the place pin is fixed and known, so indoor GPS is not needed
        "lang": place["lang"],
        "ip_hash": crypto.ip_hash(request.client.host if request.client else "unknown"),
        "status": "received",
    }
    await asyncio.to_thread(lambda: sb.table("reports").insert(row).execute())
    await audit.log(
        "reporter",
        "place_help_requested",
        "place_plan",
        place["id"],
        actor_id=str(user.id),
    )
    background.add_task(orchestrator.handle_report, report_id)
    return {"report_id": str(report_id)}
