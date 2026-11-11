"""Verification autopilot: candidate search, same-event rule, incident create/merge, recompute.

docs/02_PRD.md F-06. The rule fast-path and the autopilot decision need no LLM; the Verification
Agent layer (T-15) wraps `autopilot_decision`.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from postgrest.exceptions import APIError

from app.config import AUTO_MERGE_RADIUS_M, MERGE_RADIUS_M, MERGE_WINDOW_MIN
from app.deps import get_supabase
from app.models.ai import Candidate, IncidentChange, IncidentExtraction
from app.services import audit, confidence, events, geocode
from app.utils.geo import to_ewkt
from app.utils.short_code import new_short_code

_SEVERITY = ["low", "medium", "high", "critical"]


def window_start() -> datetime:
    return datetime.now(UTC) - timedelta(minutes=MERGE_WINDOW_MIN)


async def find_candidates(
    lat: float | None, lng: float | None, since: datetime
) -> list[Candidate]:
    """Open incidents within MERGE_RADIUS_M and the merge window (max 3, nearest first)."""
    if lat is None or lng is None:
        return []
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.rpc(
                "incidents_near_for_merge",
                {
                    "p_lat": lat,
                    "p_lng": lng,
                    "p_radius_m": MERGE_RADIUS_M,
                    "p_since": since.isoformat(),
                },
            )
            .execute()
            .data
        )
    )
    return [Candidate(**r) for r in rows]


def _compatible(candidate: Candidate, extraction: IncidentExtraction) -> bool:
    kind = extraction.incident_type.value
    return candidate.incident_type == kind or "other" in (candidate.incident_type, kind)


def fast_path(
    candidates: list[Candidate], extraction: IncidentExtraction
) -> UUID | None:
    """Exactly one candidate within AUTO_MERGE_RADIUS_M and the same type (or either 'other')."""
    close = [c for c in candidates if c.distance_m <= AUTO_MERGE_RADIUS_M]
    if len(close) == 1 and _compatible(close[0], extraction):
        return UUID(close[0].id)
    return None


def autopilot_decision(
    candidates: list[Candidate], extraction: IncidentExtraction
) -> UUID | None:
    """Verification autopilot: nearest compatible candidate within MERGE_RADIUS_M, else new."""
    for c in sorted(candidates, key=lambda c: c.distance_m):
        if c.distance_m <= MERGE_RADIUS_M and _compatible(c, extraction):
            return UUID(c.id)
    return None


async def _create_incident(report: dict, extraction: IncidentExtraction) -> dict:
    sb = get_supabase()
    base = {
        "country_code": report.get("country_code"),
        "incident_type": extraction.incident_type.value,
        "severity": extraction.severity.value,
        "status": "review",
        "location": to_ewkt(report["lat"], report["lng"])
        if report.get("lat") is not None
        else None,
        "summary_en": extraction.summary_en,
        "summary_local": extraction.summary_local,
        "local_lang": report.get("lang") or extraction.language_detected,
        "silent": report["silent"],
    }
    for _ in range(5):  # short_code is unique: retry on the rare collision
        try:
            res = await asyncio.to_thread(
                lambda: (
                    sb.table("incidents")
                    .insert({**base, "short_code": new_short_code()})
                    .execute()
                )
            )
            return res.data[0]
        except APIError as e:
            if "short_code" not in str(e):
                raise
    raise RuntimeError("could not allocate a short_code")


async def attach_or_create(
    report: dict, extraction: IncidentExtraction, incident_id: UUID | None
) -> tuple[UUID, bool]:
    """Attach the report to `incident_id`, or create a new incident. Returns (id, created)."""
    sb = get_supabase()
    created = incident_id is None
    if created:
        incident = await _create_incident(report, extraction)
        incident_id = UUID(incident["id"])
        await events.add(
            incident_id, "created", f"Incident {incident['short_code']} created"
        )
        await audit.log("system", "incident_created", "incident", str(incident_id))
    await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .update({"incident_id": str(incident_id)})
            .eq("id", report["id"])
            .execute()
        )
    )
    if not created:
        await events.add(
            incident_id, "report_merged", "Another report merged into this incident"
        )
    return incident_id, created


def _injuries(exts: list[dict]) -> list[str]:
    found = {i for e in exts for i in e["injury_types"]}
    if len(found) > 1:
        found.discard("unknown")
    return sorted(found)


def _max_severity(values: list[str]) -> str:
    return max(values, key=_SEVERITY.index)


async def recompute_incident(incident_id: UUID) -> IncidentChange:
    """Recompute incident fields from all its reports (code only; docs/02 F-06 step 6-8)."""
    sb = get_supabase()
    iid = str(incident_id)
    inc = (
        await asyncio.to_thread(
            lambda: sb.table("incidents").select("*").eq("id", iid).execute().data
        )
    )[0]
    reports = await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .select("*")
            .eq("incident_id", iid)
            .order("created_at")
            .execute()
            .data
        )
    )
    exts = [r["extraction"] for r in reports if r.get("extraction")]
    if not exts:
        raise ValueError("incident has no processed reports")

    severity = _max_severity([e["severity"] for e in exts])
    cmin = max(e["est_casualties_min"] for e in exts)
    cmax = max(e["est_casualties_max"] for e in exts)
    reporters = {
        r.get("reporter_id") or r.get("phone_hash") or r["id"] for r in reports
    }
    accuracies = [r["accuracy_m"] for r in reports if r.get("accuracy_m") is not None]
    best_accuracy = min(accuracies) if accuracies else None
    located = [r for r in reports if r.get("lat") is not None]
    best = min(
        located,
        key=lambda r: r["accuracy_m"] if r["accuracy_m"] is not None else 1e9,
        default=None,
    )
    conf = confidence.compute_confidence(
        max(e["confidence"] for e in exts),
        len(reporters),
        any(r.get("photo_path") for r in reports),
        any(r.get("phone_verified") for r in reports),
        best_accuracy,
    )
    all_non_emergency = all(not e["is_emergency"] for e in exts)
    status = confidence.status_from_confidence(conf, inc["status"], all_non_emergency)
    lead = max(
        exts, key=lambda e: _SEVERITY.index(e["severity"]) * 10 + e["confidence"]
    )

    patch: dict = {
        "severity": severity,
        "status": status,
        "est_casualties_min": cmin,
        "est_casualties_max": cmax,
        "injury_types": _injuries(exts),
        "needs": sorted({n for e in exts for n in e["needs"]}),
        "ongoing_danger": any(e["ongoing_danger"] for e in exts),
        "confidence": round(conf, 3),
        "report_count": len(reports),
        "unique_reporters": len(reporters),
        "silent": any(r["silent"] for r in reports),
        "best_accuracy_m": best_accuracy,
        "summary_en": lead["summary_en"],
        "summary_local": lead["summary_local"],
        "updated_at": datetime.now(UTC).isoformat(),
    }
    if inc["incident_type"] == "other" and lead["incident_type"] != "other":
        patch["incident_type"] = lead["incident_type"]
    if best is not None:
        patch["location"] = to_ewkt(best["lat"], best["lng"])
        if not inc.get("location_label"):
            patch["location_label"] = await geocode.reverse_label(
                best["lat"], best["lng"], best.get("location_hint")
            )
    if status == "verified" and inc["status"] != "verified":
        patch["verified_at"] = datetime.now(UTC).isoformat()
    await asyncio.to_thread(
        lambda: sb.table("incidents").update(patch).eq("id", iid).execute()
    )

    if status != inc["status"]:
        await events.add(
            iid,
            "verified" if status == "verified" else "update_sent",
            f"Status {inc['status']} -> {status} (confidence {conf:.2f})",
        )
        await audit.log(
            "system",
            "incident_status",
            "incident",
            iid,
            details={"from": inc["status"], "to": status},
        )
    return IncidentChange(
        incident_id=iid,
        short_code=inc["short_code"],
        created=inc["report_count"] == 0,
        old_status=None if inc["report_count"] == 0 else inc["status"],
        new_status=status,
        old_severity=None if inc["report_count"] == 0 else inc["severity"],
        new_severity=severity,
        old_casualties_max=inc["est_casualties_max"],
        new_casualties_max=cmax,
        report_count=len(reports),
        unique_reporters=len(reporters),
        confidence=conf,
    )
