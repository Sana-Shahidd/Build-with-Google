"""Dispatcher actions on incidents (docs/06_API_SPEC.md section 4). Reads happen through Supabase RLS."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from app.agents import debrief as debrief_agent
from app.agents.context import AgentCtx
from app.deps import CurrentUser, get_supabase, require_role
from app.limiter import limiter
from app.models.ai import IncidentChange
from app.services import activity, audit, dispatch, events, family
from app.utils.errors import ApiError

router = APIRouter()


class DismissBody(BaseModel):
    reason: str = Field(max_length=300)


async def _load(incident_id: UUID) -> dict:
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("incidents").select("*").eq("id", str(incident_id)).execute().data
        )
    )
    if not rows:
        raise ApiError(404, "NOT_FOUND", "Incident not found")
    return rows[0]


async def _update(incident_id: UUID, patch: dict) -> None:
    sb = get_supabase()
    await asyncio.to_thread(
        lambda: sb.table("incidents").update(patch).eq("id", str(incident_id)).execute()
    )


@router.post("/incidents/{incident_id}/verify")
@limiter.limit("30/minute")
async def verify(
    request: Request,
    incident_id: UUID,
    user: CurrentUser = Depends(require_role("dispatcher")),
) -> dict:
    """Dispatcher verifies an incident: status `verified`, then dispatch to every required target."""
    inc = await _load(incident_id)
    if inc["status"] in ("closed", "dismissed"):
        raise ApiError(409, "ALREADY_DONE", f"Incident is {inc['status']}")
    now = datetime.now(UTC).isoformat()
    await _update(
        incident_id,
        {"status": "verified", "verified_at": now, "verified_by": str(user.id)},
    )
    await events.add(incident_id, "verified", "Verified by dispatcher")
    await audit.log(
        "responder",
        "incident_verified",
        "incident",
        str(incident_id),
        actor_id=str(user.id),
    )
    ctx = AgentCtx(incident_id=incident_id)
    await activity.log(
        ctx, "orchestrator", "rule", f"{inc['short_code']} verified by dispatcher"
    )
    change = IncidentChange(
        incident_id=str(incident_id),
        short_code=inc["short_code"],
        old_status=inc["status"],
        new_status="verified",
        old_severity=inc["severity"],
        new_severity=inc["severity"],
        old_casualties_max=inc["est_casualties_max"],
        new_casualties_max=inc["est_casualties_max"],
        report_count=inc["report_count"],
        unique_reporters=inc["unique_reporters"],
        confidence=inc["confidence"],
    )
    await dispatch.dispatch_if_needed(incident_id, change, ctx)
    return {"status": "verified"}


@router.post("/incidents/{incident_id}/dismiss")
@limiter.limit("30/minute")
async def dismiss(
    request: Request,
    incident_id: UUID,
    body: DismissBody,
    user: CurrentUser = Depends(require_role("dispatcher")),
) -> dict:
    """Dismiss a false report: status `dismissed`, escalation stopped."""
    inc = await _load(incident_id)
    if inc["status"] in ("closed", "dismissed"):
        raise ApiError(409, "ALREADY_DONE", f"Incident is {inc['status']}")
    sb = get_supabase()
    await _update(incident_id, {"status": "dismissed", "dismissed_reason": body.reason})
    await asyncio.to_thread(
        lambda: (
            sb.table("alert_targets")
            .update({"ack_due_at": None})
            .eq("incident_id", str(incident_id))
            .execute()
        )
    )
    await events.add(
        incident_id, "dismissed", f"Dismissed by dispatcher: {body.reason}"[:300]
    )
    await audit.log(
        "responder",
        "incident_dismissed",
        "incident",
        str(incident_id),
        actor_id=str(user.id),
    )
    await activity.log(
        AgentCtx(incident_id=incident_id),
        "orchestrator",
        "rule",
        f"{inc['short_code']} dismissed by dispatcher",
    )
    return {"status": "dismissed"}


@router.post("/incidents/{incident_id}/close")
@limiter.limit("30/minute")
async def close(
    request: Request,
    incident_id: UUID,
    user: CurrentUser = Depends(
        require_role("dispatcher", "rescue", "police")
    ),
) -> dict:
    """Close an incident and stop escalation. (After-action report: Debrief task, 3H-B.)"""
    inc = await _load(incident_id)
    if inc["status"] in ("closed", "dismissed"):
        raise ApiError(409, "ALREADY_DONE", f"Incident is {inc['status']}")
    sb = get_supabase()
    await _update(
        incident_id,
        {
            "status": "closed",
            "closed_at": datetime.now(UTC).isoformat(),
            "closed_by": str(user.id),
        },
    )
    await asyncio.to_thread(
        lambda: (
            sb.table("alert_targets")
            .update({"ack_due_at": None})
            .eq("incident_id", str(incident_id))
            .execute()
        )
    )
    await events.add(incident_id, "closed", "Closed")
    await audit.log(
        "responder",
        "incident_closed",
        "incident",
        str(incident_id),
        actor_id=str(user.id),
    )
    await activity.log(
        AgentCtx(incident_id=incident_id),
        "orchestrator",
        "rule",
        f"{inc['short_code']} closed",
    )
    debrief_agent.schedule_debrief(
        incident_id
    )  # T-23: runs in the background, never blocks closing
    return {"status": "closed"}


@router.get("/incidents/{incident_id}/family")
@limiter.limit("30/minute")
async def incident_family(
    request: Request,
    incident_id: UUID,
    user: CurrentUser = Depends(require_role("dispatcher")),
) -> dict:
    """Card-scan family contacts a dispatcher must call by hand (F-41)."""
    await _load(incident_id)
    await audit.log(
        "dispatcher",
        "family_viewed",
        "incident",
        str(incident_id),
        actor_id=str(user.id),
    )
    return await family.manual_contacts(incident_id)


@router.get("/incidents/{incident_id}/after-action")
@limiter.limit("30/minute")
async def after_action(
    request: Request,
    incident_id: UUID,
    user: CurrentUser = Depends(require_role("dispatcher")),
) -> dict:
    inc = await _load(incident_id)
    if not inc.get("after_action_md"):
        raise ApiError(404, "NOT_FOUND", "No after-action report yet")
    return {"markdown": inc["after_action_md"], "generated_at": inc["updated_at"]}
