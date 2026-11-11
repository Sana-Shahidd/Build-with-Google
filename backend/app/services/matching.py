"""Hospital matching + casualty spreading (docs/02_PRD.md F-08/F-09). Triage autopilot lives here."""

import asyncio
import math
from uuid import UUID

from app.config import (
    CRITICAL_SHARE,
    HOSPITAL_CANDIDATES,
    HOSPITAL_SEARCH_RADIUS_KM,
    MAX_HOSPITALS,
)
from app.deps import get_supabase
from app.models.ai import HospitalOption, HospitalOptions, PlannedAssignment
from app.services import first_aid, routing_osrm

_CAP_PRIORITY = [
    "trauma",
    "burns",
    "neuro",
    "orthopedic",
    "cardiac",
    "pediatric",
    "general",
]


def required_capabilities(injury_types: list[str]) -> list[str]:
    """Union of capabilities for the injuries, minus 'general' (docs/07 §9)."""
    caps = {
        c
        for i in injury_types
        if i in first_aid.INJURY_MAP
        for c in first_aid.INJURY_MAP[i]["capabilities"]
        if c != "general"
    }
    return sorted(caps, key=_CAP_PRIORITY.index)


def totals(incident: dict) -> tuple[int, int]:
    """(total casualties, critical casualties) to spread."""
    total = incident["est_casualties_max"]
    if total == 0 and "ambulance" in incident["needs"]:
        total = 1
    return total, math.ceil(total * CRITICAL_SHARE[incident["severity"]])


async def hospital_options(incident: dict) -> HospitalOptions:
    """Nearest accepting hospitals with capability fit and ETA (tool for the Triage Agent)."""
    sb = get_supabase()
    lat, lng = incident["lat"], incident["lng"]
    near = await asyncio.to_thread(
        lambda: (
            sb.rpc(
                "nearest_orgs",
                {
                    "p_type": "hospital",
                    "p_lat": lat,
                    "p_lng": lng,
                    "p_radius_m": HOSPITAL_SEARCH_RADIUS_KM * 1000,
                    "p_limit": HOSPITAL_CANDIDATES,
                },
            )
            .execute()
            .data
        )
    )
    details: dict[str, dict] = {}
    if near:
        ids = [h["id"] for h in near]
        rows = await asyncio.to_thread(
            lambda: (
                sb.table("hospital_details")
                .select("*")
                .in_("org_id", ids)
                .execute()
                .data
            )
        )
        details = {r["org_id"]: r for r in rows}
    near = [
        h for h in near if h["id"] in details and details[h["id"]]["accepting_patients"]
    ]
    etas = await routing_osrm.etas_minutes(
        (lat, lng), [(h["lat"], h["lng"]) for h in near]
    )
    required = required_capabilities(incident["injury_types"])
    total, critical = totals(incident)
    options = [
        HospitalOption(
            id=h["id"],
            name=h["name"],
            lat=h["lat"],
            lng=h["lng"],
            capabilities=details[h["id"]]["capabilities"],
            free_beds=details[h["id"]]["er_beds_available"],
            icu_available=details[h["id"]]["icu_available"],
            capacity_known=details[h["id"]]["capacity_known"],
            eta_minutes=round(eta, 1),
            distance_m=h["distance_m"],
            fits=set(required) <= set(details[h["id"]]["capabilities"]),
        )
        for h, eta in zip(near, etas, strict=True)
    ]
    return HospitalOptions(
        total=total,
        critical_total=critical,
        required_capabilities=required,
        hospitals=options,
    )


def validate_plan(plan: list[PlannedAssignment], opts: HospitalOptions) -> list[str]:
    """Guardrail: error strings, [] means acceptable (F-09 step 2)."""
    if opts.total == 0:
        return [] if not plan else ["no casualties to assign"]
    errors: list[str] = []
    by_id = {h.id: h for h in opts.hospitals}
    if not 1 <= len(plan) <= MAX_HOSPITALS:
        errors.append(f"use between 1 and {MAX_HOSPITALS} hospitals")
    errors += [
        f"unknown hospital {a.hospital_id}" for a in plan if a.hospital_id not in by_id
    ]
    if sum(a.casualties for a in plan) != opts.total:
        errors.append(f"casualties must sum to {opts.total}")
    if sum(a.critical for a in plan) != opts.critical_total:
        errors.append(f"critical must sum to {opts.critical_total}")
    if any(a.critical > a.casualties for a in plan):
        errors.append("critical cannot exceed casualties for a hospital")
    if any(h.fits for h in opts.hospitals):
        for a in plan:
            h = by_id.get(a.hospital_id)
            if h and a.critical and not h.fits:
                errors.append(
                    f"critical patients cannot go to {h.name}: missing capability"
                )
    return errors


class _Allocator:
    """Tracks per-hospital allocation and free beds while spreading."""

    def __init__(self, hospitals: list[HospitalOption]):
        # hospitals with unknown capacity never receive "free-bed" allocations
        self.free = {h.id: (h.free_beds if h.capacity_known else 0) for h in hospitals}
        self.alloc: dict[str, dict] = {}

    def give(self, h: HospitalOption, n: int, critical: bool, over: bool) -> int:
        if n <= 0:
            return 0
        if h.id not in self.alloc:
            if len(self.alloc) >= MAX_HOSPITALS:
                return 0
            self.alloc[h.id] = {"c": 0, "k": 0, "over": False, "h": h}
        a = self.alloc[h.id]
        a["c"] += n
        a["k"] += n if critical else 0
        a["over"] = a["over"] or over
        self.free[h.id] = max(0, self.free[h.id] - n)
        return n


def spread(opts: HospitalOptions) -> list[PlannedAssignment]:
    """Autopilot: critical to fitting hospitals by ETA, minor over free beds, leftovers flagged over capacity."""
    if opts.total == 0 or not opts.hospitals:
        return []
    by_eta = sorted(opts.hospitals, key=lambda h: h.eta_minutes)
    fit = [h for h in by_eta if h.fits] or by_eta
    al = _Allocator(by_eta)

    critical_left = opts.critical_total
    for h in fit:
        critical_left -= al.give(h, min(critical_left, al.free[h.id]), True, False)
    if critical_left:
        critical_left -= al.give(fit[0], critical_left, True, True)

    minor_left = opts.total - opts.critical_total
    for h in by_eta:
        minor_left -= al.give(h, min(minor_left, al.free[h.id]), False, False)
    if minor_left:
        nearest_used = next(iter(al.alloc.values()))["h"] if al.alloc else by_eta[0]
        target = by_eta[0] if by_eta[0].id in al.alloc else nearest_used
        al.give(target, minor_left, False, True)

    return [
        PlannedAssignment(
            hospital_id=hid,
            casualties=a["c"],
            critical=a["k"],
            reason=_reason(a["h"], a["k"], a["over"]),
            eta_minutes=a["h"].eta_minutes,
            over_capacity=a["over"],
        )
        for hid, a in al.alloc.items()
    ]


def _reason(h: HospitalOption, critical: int, over: bool) -> str:
    parts = []
    if critical:
        parts.append(f"{critical} critical" + (", capability fit" if h.fits else ""))
    parts.append(f"ETA {h.eta_minutes:.0f} min")
    if over:
        parts.append("over free beds")
    return ", ".join(parts)[:120]


async def save_plan(
    incident_id: UUID | str, plan: list[PlannedAssignment], planned_by: str
) -> None:
    """Replace the incident's hospital_assignments with this plan."""
    sb = get_supabase()
    iid = str(incident_id)
    rows = [
        {
            "incident_id": iid,
            "hospital_id": a.hospital_id,
            "assigned_casualties": a.casualties,
            "critical": a.critical,
            "eta_minutes": a.eta_minutes,
            "over_capacity": a.over_capacity,
            "reason": a.reason,
            "planned_by": planned_by,
        }
        for a in plan
    ]

    def write() -> None:
        stale = sb.table("hospital_assignments").delete().eq("incident_id", iid)
        keep = [a.hospital_id for a in plan]
        (stale.not_.in_("hospital_id", keep) if keep else stale).execute()
        if rows:
            sb.table("hospital_assignments").upsert(
                rows, on_conflict="incident_id,hospital_id"
            ).execute()

    await asyncio.to_thread(write)
