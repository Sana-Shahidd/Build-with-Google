"""After-action data and the template autopilot of the Debrief Agent (docs/07 section 6.6, F-31).

`timeline()` gathers PII-free facts (no phones, no names, no report text). `template_report()` fills the
same sections the agent is asked for with computed numbers, so a report always exists.
"""

import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app.deps import get_supabase
from app.services import country

_PHONE_LIKE = re.compile(r"\+?\d[\d\s-]{7,}\d")


def _t(ts: str | None, tz: ZoneInfo) -> str:
    if not ts:
        return "-"
    return datetime.fromisoformat(ts).astimezone(tz).strftime("%H:%M:%S")


def _secs(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    return int((datetime.fromisoformat(b) - datetime.fromisoformat(a)).total_seconds())


async def timeline(incident_id: str) -> dict:
    sb = get_supabase()

    def load():
        inc = sb.table("incidents").select("*").eq("id", incident_id).execute().data[0]
        ev = (
            sb.table("incident_events")
            .select("kind,message,created_at")
            .eq("incident_id", incident_id)
            .order("created_at")
            .execute()
            .data
        )
        tg = (
            sb.table("alert_targets")
            .select(
                "recipient_label,recipient_kind,created_at,acknowledged_at,escalation_level,status,is_standby"
            )
            .eq("incident_id", incident_id)
            .order("created_at")
            .execute()
            .data
        )
        asg = (
            sb.table("hospital_assignments")
            .select(
                "assigned_casualties,critical,eta_minutes,over_capacity,planned_by,organizations:hospital_id(name)"
            )
            .eq("incident_id", incident_id)
            .execute()
            .data
        )
        act = (
            sb.table("agent_activity")
            .select("agent,kind")
            .eq("incident_id", incident_id)
            .execute()
            .data
        )
        return inc, ev, tg, asg, act

    inc, ev, tg, asg, act = await asyncio.to_thread(load)
    profile = country.get_profile(inc.get("country_code"))
    return {
        "timezone": profile["timezone"],
        "incident": {
            "short_code": inc["short_code"],
            "type": inc["incident_type"],
            "severity": inc["severity"],
            "status": inc["status"],
            "location_label": inc.get("location_label"),
            "casualties_max": inc["est_casualties_max"],
            "report_count": inc["report_count"],
            "unique_reporters": inc["unique_reporters"],
            "confidence": inc["confidence"],
            "created_at": inc["created_at"],
            "first_alert_at": inc.get("first_alert_at"),
            "first_ack_at": inc.get("first_ack_at"),
            "closed_at": inc.get("closed_at"),
        },
        "events": [
            {"time": e["created_at"], "kind": e["kind"], "message": e["message"]}
            for e in ev
        ],
        "targets": [
            {
                "label": t["recipient_label"],
                "kind": t["recipient_kind"],
                "created_at": t["created_at"],
                "acknowledged_at": t["acknowledged_at"],
                "escalation_level": t["escalation_level"],
                "status": t["status"],
                "standby": t["is_standby"],
            }
            for t in tg
        ],
        "assignments": [
            {
                "hospital": a["organizations"]["name"],
                "casualties": a["assigned_casualties"],
                "critical": a["critical"],
                "eta_minutes": a["eta_minutes"],
                "over_capacity": a["over_capacity"],
                "planned_by": a["planned_by"],
            }
            for a in asg
        ],
        "agent_stats": {
            "agent_decisions": sum(1 for a in act if a["kind"] == "decision"),
            "autopilot": sum(1 for a in act if a["kind"] in ("rule", "fallback")),
            "guardrail_blocks": sum(1 for a in act if a["kind"] == "guardrail_block"),
        },
    }


def template_report(data: dict) -> str:
    """Autopilot: same sections as the agent, numbers computed by code."""
    tz = ZoneInfo(data["timezone"])
    inc = data["incident"]
    first_alert = _secs(inc["created_at"], inc["first_alert_at"])
    first_ack = _secs(inc["first_alert_at"], inc["first_ack_at"])
    stats = data["agent_stats"]
    lines = [
        "## Summary",
        f"{inc['short_code']}: {inc['type'].replace('_', ' ')}, severity {inc['severity']}"
        f" near {inc['location_label'] or 'unknown location'}. Up to {inc['casualties_max']} casualties"
        f" reported by {inc['unique_reporters']} reporter(s) in {inc['report_count']} report(s)."
        f" Final status: {inc['status']}.",
        "",
        "## Timeline",
        *[f"- {_t(e['time'], tz)} {e['message']}" for e in data["events"]],
        "",
        "## Response performance",
        f"- Time from first report to first alert: {first_alert if first_alert is not None else 'n/a'} s",
        f"- Time from first alert to first acknowledgement: {first_ack if first_ack is not None else 'n/a'} s",
    ]
    for t in data["targets"]:
        ack = _secs(t["created_at"], t["acknowledged_at"])
        lines.append(
            f"- {t['label']}: "
            + (
                f"acknowledged after {ack} s"
                if ack is not None
                else "no acknowledgement"
            )
            + (
                f", escalation level {t['escalation_level']}"
                if t["escalation_level"]
                else ""
            )
        )
    lines.append(
        f"- Decisions: {stats['agent_decisions']} by agents, {stats['autopilot']} by autopilot rules,"
        f" {stats['guardrail_blocks']} guardrail block(s)"
    )
    missing = [t["label"] for t in data["targets"] if not t["acknowledged_at"]]
    slow = first_ack is not None and first_ack > 60
    lines += [
        "",
        "## What worked",
        "- Alerts were sent to all required responders"
        if data["targets"]
        else "- No alerts were required",
        "",
        "## Delays and gaps",
        *(
            [f"- No acknowledgement from: {', '.join(missing)}"]
            if missing
            else ["- None found"]
        ),
        *(["- First acknowledgement took longer than 60 s"] if slow else []),
        "",
        "## Recommendations",
        *(
            ["- Follow up with responders that did not acknowledge"]
            if missing
            else ["- Keep the current alert setup"]
        ),
        *(["- Review why acknowledgement was slow"] if slow else []),
    ]
    return "\n".join(lines)


def validate_markdown(md: str) -> bool:
    """Guardrail for the agent text: required sections present and no phone-like numbers."""
    needed = (
        "## Summary",
        "## Timeline",
        "## Response performance",
        "## Recommendations",
    )
    return all(h in md for h in needed) and not _PHONE_LIKE.search(md)
