import asyncio

from fastapi import APIRouter, Request

from app.agents.context import AgentCtx
from app.deps import get_supabase
from app.limiter import limiter
from app.services import ack_tokens, activity
from app.utils.errors import ApiError

router = APIRouter()


async def _verified(token: str):
    try:
        return await ack_tokens.verify_token(token)
    except ack_tokens.ExpiredToken as e:
        raise ApiError(410, "TOKEN_EXPIRED", "This link has expired") from e
    except ack_tokens.UsedToken as e:
        raise ApiError(410, "TOKEN_USED", "Already acknowledged") from e
    except ack_tokens.InvalidToken as e:
        raise ApiError(404, "NOT_FOUND", "Invalid link") from e


@router.get("/ack/{token}")
@limiter.limit("20/minute")
async def ack_preview(request: Request, token: str) -> dict:
    """Preview only: never acknowledges (link-preview bots must not ack)."""
    target_id, _ = await _verified(token)
    sb = get_supabase()
    target = (
        await asyncio.to_thread(
            lambda: (
                sb.table("alert_targets")
                .select("recipient_label,status,incident_id")
                .eq("id", str(target_id))
                .execute()
                .data
            )
        )
    )[0]
    inc = (
        await asyncio.to_thread(
            lambda: (
                sb.table("incidents")
                .select("short_code,incident_type,severity,location_label,summary_en")
                .eq("id", target["incident_id"])
                .execute()
                .data
            )
        )
    )[0]
    return {
        "recipient_label": target["recipient_label"],
        "incident": inc,
        "already_acknowledged": target["status"] == "acknowledged",
    }


@router.post("/ack/{token}")
@limiter.limit("10/minute")
async def ack(request: Request, token: str) -> dict:
    """Acknowledge. The channel comes from the token ('dashboard' for the web responder link)."""
    target_id, channel = await _verified(token)
    first = await ack_tokens.acknowledge(target_id, via=channel, actor="link")
    sb = get_supabase()
    row = (
        await asyncio.to_thread(
            lambda: (
                sb.table("alert_targets")
                .select("acknowledged_at,incident_id,recipient_label")
                .eq("id", str(target_id))
                .execute()
                .data
            )
        )
    )[0]
    if first:
        await activity.log(
            AgentCtx(incident_id=row["incident_id"]),
            "dispatch",
            "rule",
            f"{row['recipient_label']} acknowledged via {channel}",
        )
    return {
        "acknowledged": True,
        "acknowledged_at": row["acknowledged_at"],
        "first": first,
    }
