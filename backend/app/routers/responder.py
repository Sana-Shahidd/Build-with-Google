"""Web responder inbox API (replaces the Telegram channel in the demo; docs/06_API_SPEC.md §3.1)."""

import asyncio

from fastapi import APIRouter, Request

from app.deps import get_supabase
from app.limiter import limiter
from app.services import ack_tokens, cards, messages
from app.utils.errors import ApiError

router = APIRouter()

MAX_ALERTS = 10
_INCIDENT_FIELDS = (
    "id,short_code,incident_type,severity,status,location_label,lat,lng,landmark_text,landmark_local,"
    "est_casualties_min,est_casualties_max,injury_types,ongoing_danger,silent,summary_en,"
    "summary_local,local_lang,confidence,report_count"
)


def _texts(
    target: dict, incident: dict, assignment: dict | None, card: dict | None
) -> dict[str, list[str]]:
    if target["recipient_kind"] == "hospital":
        return {
            lang: messages.hospital_brief(
                incident,
                assignment,
                lang,
                standby=target["is_standby"],
                card_line=cards.card_line(card, lang) if card else None,
            )
            for lang in ("en", "es", "ur")
        }
    return messages.all_languages(messages.org_alert, incident)


async def _alert_view(
    target: dict, incident: dict, assignment: dict | None, card: dict | None
) -> dict:
    acked = target["status"] == "acknowledged"
    token = None if acked else await ack_tokens.issue_token(target["id"], "dashboard")
    return {
        "target_id": target["id"],
        "kind": "standby" if target["is_standby"] else target["recipient_kind"],
        "state": target["status"],
        "acknowledged_at": target["acknowledged_at"],
        "created_at": target["created_at"],
        "ack_token": token,
        "incident": {
            "short_code": incident["short_code"],
            "incident_type": incident["incident_type"],
            "severity": incident["severity"],
            "status": incident["status"],
            "location_label": incident["location_label"],
            "map_url": messages.map_url(incident),
        },
        "text": _texts(target, incident, assignment, card),
    }


@router.get("/responder/{token}")
@limiter.limit("60/minute")
async def inbox(request: Request, token: str) -> dict:
    """Alerts for ONE organization, newest first. Token = signed org link; no login.

    Never returns phone numbers, chat ids or other organizations' data."""
    try:
        org_id = ack_tokens.verify_inbox_token(token)
    except ack_tokens.ExpiredToken as e:
        raise ApiError(410, "TOKEN_EXPIRED", "This link has expired") from e
    except ack_tokens.InvalidToken as e:
        raise ApiError(404, "NOT_FOUND", "Invalid link") from e
    sb = get_supabase()
    org = await asyncio.to_thread(
        lambda: (
            sb.table("organizations")
            .select("id,name,type,lang")
            .eq("id", str(org_id))
            .execute()
            .data
        )
    )
    if not org:
        raise ApiError(404, "NOT_FOUND", "Invalid link")
    targets = await asyncio.to_thread(
        lambda: (
            sb.table("alert_targets")
            .select("*")
            .eq("recipient_org_id", str(org_id))
            .order("created_at", desc=True)
            .limit(MAX_ALERTS)
            .execute()
            .data
        )
    )
    alerts = []
    for t in targets:
        inc = (
            await asyncio.to_thread(
                lambda t=t: (
                    sb.table("incidents")
                    .select(_INCIDENT_FIELDS)
                    .eq("id", t["incident_id"])
                    .execute()
                    .data
                )
            )
        )[0]
        assignment = None
        if t["recipient_kind"] == "hospital":
            rows = await asyncio.to_thread(
                lambda t=t: (
                    sb.table("hospital_assignments")
                    .select("assigned_casualties,critical,eta_minutes")
                    .eq("incident_id", t["incident_id"])
                    .eq("hospital_id", str(org_id))
                    .execute()
                    .data
                )
            )
            assignment = rows[0] if rows else None
        card = (
            await cards.card_for_incident(t["incident_id"])
            if t["recipient_kind"] == "hospital"
            else None
        )
        alerts.append(await _alert_view(t, inc, assignment, card))
    sent_ids = [t["id"] for t in targets if t["status"] == "sent"]
    if sent_ids:  # first time the responder page shows them
        await asyncio.to_thread(
            lambda: (
                sb.table("alert_targets")
                .update({"status": "delivered"})
                .in_("id", sent_ids)
                .execute()
            )
        )
    return {"org": org[0], "alerts": alerts}
