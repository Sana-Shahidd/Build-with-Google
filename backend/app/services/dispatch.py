"""Dispatch autopilot: who must be alerted, in what order, idempotently (docs/02_PRD.md F-10).

Channels: 'dashboard' (the web responder link /r/<token>) always; 'telegram' only when
TELEGRAM_ENABLED and the org has a chat linked. Message text comes from messages.py (fixed templates).
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from postgrest.exceptions import APIError
from pydantic import BaseModel

from app.agents.context import AgentCtx
from app.config import ACK_TIMEOUT_S, settings
from app.deps import get_supabase
from app.models.ai import IncidentChange
from app.services import activity, audit, events, messages

NEAREST_RADIUS_M = 50_000
_ORG_TYPE = {
    "police": "police_station",
    "rescue": "rescue_station",
    "fire": "fire_station",
}


class RequiredTarget(BaseModel):
    key: str  # 'police' | 'rescue' | 'fire' | 'hospital:<org_id>'
    kind: str  # recipient_kind enum value
    org_id: str
    label: str
    standby: bool = False
    telegram_chat_id: int | None = None
    lang: str = "en"


async def _db(fn):
    return await asyncio.to_thread(fn)


async def _nearest(kind: str, incident: dict) -> dict | None:
    sb = get_supabase()
    rows = await _db(
        lambda: (
            sb.rpc(
                "nearest_orgs",
                {
                    "p_type": _ORG_TYPE[kind],
                    "p_lat": incident["lat"],
                    "p_lng": incident["lng"],
                    "p_radius_m": NEAREST_RADIUS_M,
                    "p_limit": 1,
                },
            )
            .execute()
            .data
        )
    )
    return rows[0] if rows else None


async def _org_info(org_ids: list[str]) -> dict[str, dict]:
    if not org_ids:
        return {}
    sb = get_supabase()
    rows = await _db(
        lambda: (
            sb.table("organizations")
            .select("id,name,telegram_chat_id,lang")
            .in_("id", org_ids)
            .execute()
            .data
        )
    )
    return {r["id"]: r for r in rows}


async def required_targets(incident: dict) -> list[RequiredTarget]:
    """Mandatory targets by status (PRD F-10 table). `review` incidents alert nobody automatically."""
    if (
        incident["status"] not in ("unverified", "verified")
        or incident.get("lat") is None
    ):
        return []
    sb = get_supabase()
    needs = set(incident["needs"])
    wanted: list[tuple[str, str, dict]] = []  # (key, kind, org row with id/name)
    if "police" in needs and (org := await _nearest("police", incident)):
        wanted.append(("police", "police", org))
    if needs & {"ambulance", "rescue"} and (org := await _nearest("rescue", incident)):
        wanted.append(("rescue", "rescue", org))
    if "fire" in needs and (org := await _nearest("fire", incident)):
        wanted.append(("fire", "fire", org))
    assigned = await _db(
        lambda: (
            sb.table("hospital_assignments")
            .select(
                "hospital_id,assigned_casualties,eta_minutes,organizations:hospital_id(id,name)"
            )
            .eq("incident_id", incident["id"])
            .gt("assigned_casualties", 0)
            .order("eta_minutes")
            .execute()
            .data
        )
    )
    verified = incident["status"] == "verified"
    for a in assigned if verified else assigned[:1]:
        wanted.append((f"hospital:{a['hospital_id']}", "hospital", a["organizations"]))
    info = await _org_info([org["id"] for _, _, org in wanted])
    return [
        RequiredTarget(
            key=key,
            kind=kind,
            org_id=org["id"],
            label=org["name"],
            standby=kind == "hospital" and not verified,
            telegram_chat_id=info[org["id"]]["telegram_chat_id"],
            lang=info[org["id"]]["lang"],
        )
        for key, kind, org in wanted
    ]


def default_order(
    targets: list[RequiredTarget], incident_type: str = "other"
) -> list[str]:
    """Dispatch autopilot: police first for attacks, else EMS, hospitals, police, fire."""
    rank = (
        ["police", "rescue", "hospital", "fire"]
        if incident_type == "attack_shooting"
        else ["rescue", "hospital", "police", "fire"]
    )
    return [t.key for t in sorted(targets, key=lambda t: rank.index(t.kind))]


async def _incident(incident_id: UUID | str) -> dict:
    sb = get_supabase()
    return (
        await _db(
            lambda: (
                sb.table("incidents")
                .select("*")
                .eq("id", str(incident_id))
                .execute()
                .data
            )
        )
    )[0]


async def _create_deliveries(
    target: dict, req: RequiredTarget, incident: dict, update: bool
) -> None:
    """One delivery row per channel. The web responder link is always available."""
    sb = get_supabase()
    rows = [
        {
            "target_id": target["id"],
            "channel": "dashboard",
            "to_masked": "responder link",
            "is_update": update,
            "status": "delivered",
        }
    ]
    if settings.TELEGRAM_ENABLED and req.telegram_chat_id:
        from app.services import (
            notify_telegram,  # optional channel, imported only when enabled
        )

        status, err, msg_id = "sent", None, None
        lines = messages.org_alert(incident, req.lang)
        try:
            msg_id = await notify_telegram.send_alert(
                req.telegram_chat_id, lines, target["id"]
            )
        except Exception as e:  # noqa: BLE001 - Telegram failure must not stop the dashboard channel
            status, err = "failed", type(e).__name__
        rows.append(
            {
                "target_id": target["id"],
                "channel": "telegram",
                "to_masked": "chat linked",
                "is_update": update,
                "status": status,
                "error": err,
                "provider_message_id": msg_id,
            }
        )
    await _db(lambda: sb.table("deliveries").insert(rows).execute())


async def send_targets(incident_id: UUID | str, keys_in_order: list[str]) -> list[str]:
    """Create alert_targets (idempotent) for the required targets. The caller's order is honoured;
    any required key it omits is appended (nothing required is ever skipped)."""
    sb = get_supabase()
    incident = await _incident(incident_id)
    required = {t.key: t for t in await required_targets(incident)}
    order = [k for k in keys_in_order if k in required] + [
        k for k in required if k not in keys_in_order
    ]
    existing = {
        r["recipient_org_id"]: r
        for r in await _db(
            lambda: (
                sb.table("alert_targets")
                .select("*")
                .eq("incident_id", incident["id"])
                .execute()
                .data
            )
        )
    }
    sent: list[str] = []
    for key in order:
        req = required[key]
        found = existing.get(req.org_id)
        if found is None:
            row = {
                "incident_id": incident["id"],
                "recipient_kind": req.kind,
                "recipient_org_id": req.org_id,
                "recipient_label": req.label,
                "is_standby": req.standby,
                "status": "sent",
                "ack_due_at": (
                    datetime.now(UTC) + timedelta(seconds=ACK_TIMEOUT_S)
                ).isoformat(),
            }
            try:
                target = (
                    await _db(
                        lambda row=row: sb.table("alert_targets").insert(row).execute()
                    )
                ).data[0]
            except APIError as e:  # unique index hit: another run created it first
                if e.code != "23505":
                    raise
                continue
            await _create_deliveries(target, req, incident, update=False)
        elif (
            found["is_standby"] and not req.standby
        ):  # standby hospital upgraded to full brief
            await _db(
                lambda found=found: (
                    sb.table("alert_targets")
                    .update({"is_standby": False})
                    .eq("id", found["id"])
                    .execute()
                )
            )
            await _create_deliveries(found, req, incident, update=True)
        else:
            continue
        sent.append(key)
        await events.add(
            incident["id"],
            "alert_sent",
            f"Alert sent to {req.label}" + (" (standby)" if req.standby else ""),
        )
    if sent:
        now = datetime.now(UTC).isoformat()
        await _db(
            lambda: (
                sb.table("incidents")
                .update({"first_alert_at": now})
                .eq("id", incident["id"])
                .is_("first_alert_at", "null")
                .execute()
            )
        )
        await audit.log(
            "system",
            "alerts_sent",
            "incident",
            incident["id"],
            details={"targets": len(sent)},
        )
    return sent


async def send_update(incident_id: UUID | str, change: IncidentChange) -> None:
    """Existing targets get an UPDATE delivery (no new ack); content is read live from the incident."""
    sb = get_supabase()
    targets = await _db(
        lambda: (
            sb.table("alert_targets")
            .select("id")
            .eq("incident_id", str(incident_id))
            .execute()
            .data
        )
    )
    if not targets:
        return
    rows = [
        {
            "target_id": t["id"],
            "channel": "dashboard",
            "to_masked": "responder link",
            "is_update": True,
            "status": "delivered",
        }
        for t in targets
    ]
    await _db(lambda: sb.table("deliveries").insert(rows).execute())
    await events.add(
        incident_id, "update_sent", f"Update sent to {len(targets)} target(s)"
    )


async def dispatch_if_needed(
    incident_id: UUID | str, change: IncidentChange, ctx: AgentCtx
) -> None:
    """Send alerts for an unverified/verified incident; send updates to existing targets on change."""
    incident = await _incident(incident_id)
    if incident["status"] not in ("unverified", "verified"):
        await activity.log(
            ctx,
            "dispatch",
            "rule",
            f"Incident is {incident['status']}: no automatic alerts",
        )
        return
    targets = await required_targets(incident)
    order = default_order(targets, incident["incident_type"])
    sent: list[str] = []
    if len(targets) > 1 and incident.get("first_alert_at") is None:
        from app.agents import (
            dispatch as dispatch_agent,  # T-17, lazy: avoids an import cycle
        )

        if await dispatch_agent.run(ctx, incident, targets):
            sent = ctx.sent_keys
    if not sent:
        sent = await send_targets(incident_id, order)
    ctx.sent_keys = sent
    if sent:
        names = ", ".join(t.label for t in targets if t.key in sent)
        await activity.log(
            ctx,
            "dispatch",
            "rule",
            f"Alerted {len(sent)} target(s) via web responder link: {names}"[:200],
            data={"keys": sent},
        )
    elif not change.created and change.significant:
        await send_update(incident_id, change)
        await activity.log(ctx, "dispatch", "rule", "Update sent to existing targets")
    if incident["status"] == "verified" and incident.get("verified_at") is not None:
        from app.agents import (
            hospital_prep,  # T-20, lazy import; runs in the background
        )

        hospital_prep.schedule_prep(incident_id)
    elif (
        incident["status"] == "unverified"
    ):  # F-24 rule: volunteers on unverified incidents, no LLM
        from app.services import hospital_prep as prep_rules

        await prep_rules.ping_volunteers(incident_id)
    if settings.SIMULATION_ENABLED and incident["status"] == "verified":
        from app.services import ambulance  # F-26, lazy import

        await ambulance.assign_if_needed(incident_id)
