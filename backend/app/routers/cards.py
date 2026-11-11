"""Emergency Card endpoints (docs/06_API_SPEC.md section 6.1, F-36)."""

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
from app.services import audit, cards, country, crypto
from app.utils.errors import ApiError
from app.utils.geo import to_ewkt

router = APIRouter()


async def _owned(card_id: UUID, user: CurrentUser) -> dict:
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("emergency_cards")
            .select("*")
            .eq("id", str(card_id))
            .eq("owner_user_id", str(user.id))
            .execute()
            .data
        )
    )
    if not rows:
        raise ApiError(404, "NOT_FOUND", "Card not found")
    return rows[0]


def _scan_url(token: str) -> str:
    return f"{(settings.PUBLIC_BASE_URL or settings.FRONTEND_BASE_URL).rstrip('/')}/c/{token}"


@router.post("/cards", status_code=201)
@limiter.limit("5/hour", key_func=user_or_ip)
async def create_card(
    request: Request,
    body: cards.CardCreate,
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    if not body.consent:
        raise ApiError(400, "VALIDATION_ERROR", "consent must be true")
    region = country.get_profile(country.fallback_code())["phone_region"]
    try:
        card = await cards.create_card(user.id, body, region)
    except ValueError as e:
        raise ApiError(
            400, "VALIDATION_ERROR", "A family phone number is not valid"
        ) from e
    await audit.log(
        "reporter", "card_created", "emergency_card", card["id"], actor_id=str(user.id)
    )
    return {
        "card_id": card["id"],
        "token": card["token"],
        "scan_url": _scan_url(card["token"]),
        "print_url": f"/card/{card['id']}/print",
    }


@router.get("/cards/me")
@limiter.limit("30/minute")
async def my_cards(
    request: Request, user: CurrentUser = Depends(get_current_user)
) -> dict:
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("emergency_cards")
            .select("*")
            .eq("owner_user_id", str(user.id))
            .order("created_at", desc=True)
            .execute()
            .data
        )
    )
    return {
        "cards": [
            {
                "card_id": c["id"],
                "full_name": c["full_name"],
                "active": c["active"],
                "scan_count": c["scan_count"],
                "last_scanned_at": c["last_scanned_at"],
                "scan_url": _scan_url(c["token"]),
            }
            for c in rows
        ]
    }


@router.get("/cards/{card_id}/qr.svg")
@limiter.limit("30/minute")
async def card_qr(
    request: Request, card_id: UUID, user: CurrentUser = Depends(get_current_user)
) -> Response:
    """QR sticker for the card (segno, error level Q). It encodes the scan URL (the tunnel URL when set)."""
    card = await _owned(card_id, user)
    svg = segno.make(_scan_url(card["token"]), error="q").svg_inline(scale=8, border=2)
    return Response(content=svg, media_type="image/svg+xml")


@router.delete("/cards/{card_id}", status_code=204)
@limiter.limit("10/minute")
async def delete_card(
    request: Request, card_id: UUID, user: CurrentUser = Depends(get_current_user)
) -> Response:
    await _owned(card_id, user)
    sb = get_supabase()
    await asyncio.to_thread(
        lambda: sb.table("emergency_cards").delete().eq("id", str(card_id)).execute()
    )
    await audit.log(
        "reporter",
        "card_deleted",
        "emergency_card",
        str(card_id),
        actor_id=str(user.id),
    )
    return Response(status_code=204)


@router.get("/public/card/{token}")
@limiter.limit(CARD_SCAN_RATE)
async def public_card(request: Request, token: str) -> dict:
    ip = crypto.ip_hash(request.client.host if request.client else "unknown")
    view = await cards.public_view(token, ip)
    if view is None:
        raise ApiError(404, "NOT_FOUND", "Card not found")
    view.pop("card_id", None)
    return view


class AlertBody(BaseModel):
    client_report_id: UUID
    lat: float | None = None
    lng: float | None = None
    accuracy_m: float | None = None


@router.post("/public/card/{token}/alert", status_code=202)
@limiter.limit(CARD_ALERT_RATE, key_func=user_or_ip)
async def card_alert(
    request: Request,
    token: str,
    body: AlertBody,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
):
    """'Get help' on a scanned card: an SOS report with `card_id`, through the normal pipeline."""
    sb = get_supabase()
    found = await asyncio.to_thread(
        lambda: (
            sb.table("emergency_cards")
            .select("id,lang")
            .eq("token", token)
            .eq("active", True)
            .execute()
            .data
        )
    )
    if not found:
        raise ApiError(404, "NOT_FOUND", "Card not found")
    card = found[0]
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
    has_loc = body.lat is not None and body.lng is not None
    row = {
        "id": str(report_id),
        "client_report_id": str(body.client_report_id),
        "reporter_id": str(user.id),
        "channel": "app",
        "input_type": "sos",
        "card_id": card["id"],
        "location": to_ewkt(body.lat, body.lng) if has_loc else None,
        "accuracy_m": body.accuracy_m if has_loc else None,
        "lang": card["lang"],
        "ip_hash": crypto.ip_hash(request.client.host if request.client else "unknown"),
        "status": "received",
    }
    await asyncio.to_thread(lambda: sb.table("reports").insert(row).execute())
    await asyncio.to_thread(
        lambda: (
            sb.table("card_scans")
            .insert({"card_id": card["id"], "report_id": str(report_id)})
            .execute()
        )
    )
    await audit.log(
        "reporter",
        "card_help_requested",
        "emergency_card",
        card["id"],
        actor_id=str(user.id),
    )
    background.add_task(orchestrator.handle_report, report_id)
    return {"report_id": str(report_id)}
