"""Hospital Prep (F-19, F-23, F-24): doctor call-in, blood-donor ping, volunteer ping. TRACKED ONLY.

This build has no outbound channel for doctors, donors or volunteers (no voice, email, Telegram or push),
so these functions create `alert_targets` rows with status 'queued' (no delivery row, no fake 'sent') and
write incident events saying so. When a channel is added later, it sends the queued targets.
Eligibility and guardrails are code; the Hospital Prep Agent only chooses among eligible actions.
Nothing here returns phone numbers, names or locations of staff/members (counts only).
"""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from postgrest.exceptions import APIError

from app.config import (
    BLOOD_LOW_UNITS,
    DONOR_COOLDOWN_H,
    DONOR_MAX,
    DONOR_RADIUS_KM,
    VOLUNTEER_COOLDOWN_H,
    VOLUNTEER_MAX,
    VOLUNTEER_RADIUS_KM,
)
from app.deps import get_supabase
from app.services import audit, events, first_aid

SPECIALTY_ORDER = [
    "trauma_surgeon",
    "burn_specialist",
    "neurosurgeon",
    "orthopedic_surgeon",
    "cardiologist",
    "general_surgeon",
    "anesthetist",
    "emergency_physician",
]
MAX_SPECIALTIES = 4
MAX_DOCTORS_PER_HOSPITAL = 4
DONOR_INJURIES = {"gunshot", "blast_shrapnel", "bleeding", "crush"}
VOLUNTEER_SKILLS = {"cpr", "first_aid", "nurse", "doctor"}
ALWAYS_GROUPS = ["O-", "O+"]
NO_CHANNEL = "tracked only: no outbound channel in this build"


def required_specialties(injury_types: list[str]) -> list[str]:
    """Union of specialties for the injuries, in the doc order, max 4 (docs/07 section 9)."""
    found = {
        s
        for i in injury_types
        if i in first_aid.INJURY_MAP
        for s in first_aid.INJURY_MAP[i]["specialties"]
    }
    return [s for s in SPECIALTY_ORDER if s in found][:MAX_SPECIALTIES]


def doctors_eligible(incident: dict) -> bool:
    return incident["status"] == "verified" and incident["severity"] == "critical"


def donors_eligible(incident: dict) -> bool:
    return (
        incident["status"] == "verified"
        and incident["est_casualties_max"] >= 3
        and bool(set(incident["injury_types"]) & DONOR_INJURIES)
    )


def volunteers_eligible(incident: dict) -> bool:
    return (
        "ambulance" in incident["needs"]
        and not incident["ongoing_danger"]
        and incident["status"] in ("unverified", "verified")
    )


def allowed_groups(stocks: list[dict]) -> list[str]:
    """O-/O+ plus every group below BLOOD_LOW_UNITS in any assigned hospital."""
    groups = list(ALWAYS_GROUPS)
    for stock in stocks:
        for group, units in (stock or {}).items():
            if units < BLOOD_LOW_UNITS and group not in groups:
                groups.append(group)
    return groups


async def _db(fn):
    return await asyncio.to_thread(fn)


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


async def _assigned(incident_id: str) -> list[dict]:
    sb = get_supabase()
    return await _db(
        lambda: (
            sb.table("hospital_assignments")
            .select(
                "hospital_id,assigned_casualties,critical,organizations:hospital_id(name)"
            )
            .eq("incident_id", incident_id)
            .gt("assigned_casualties", 0)
            .order("critical", desc=True)
            .execute()
            .data
        )
    )


async def _members_near(lat: float, lng: float, radius_km: float) -> list[dict]:
    sb = get_supabase()
    return await _db(
        lambda: (
            sb.rpc(
                "members_near",
                {"p_lat": lat, "p_lng": lng, "p_radius_m": radius_km * 1000},
            )
            .execute()
            .data
        )
    )


def _cooled(last: str | None, hours: int) -> bool:
    if not last:
        return True
    return datetime.now(UTC) - datetime.fromisoformat(last) >= timedelta(hours=hours)


async def _eligible_donors(incident: dict, groups: list[str]) -> list[dict]:
    near = await _members_near(incident["lat"], incident["lng"], DONOR_RADIUS_KM)
    return [
        m
        for m in near
        if m["is_donor"]
        and m["blood_type"] in groups
        and _cooled(m["last_donor_ping_at"], DONOR_COOLDOWN_H)
    ][:DONOR_MAX]


async def _eligible_volunteers(incident: dict) -> list[dict]:
    near = await _members_near(incident["lat"], incident["lng"], VOLUNTEER_RADIUS_KM)
    return [
        m
        for m in near
        if VOLUNTEER_SKILLS & set(m["skills"] or [])
        and _cooled(m["last_volunteer_ping_at"], VOLUNTEER_COOLDOWN_H)
    ][:VOLUNTEER_MAX]


async def prep_options(incident_id: UUID | str) -> dict:
    """What the Hospital Prep Agent may do (counts and flags only, no personal data)."""
    inc = await _incident(incident_id)
    iid = str(incident_id)
    assigned = await _assigned(iid)
    specialties = required_specialties(inc["injury_types"])
    sb = get_supabase()
    hospital_ids = [a["hospital_id"] for a in assigned]
    staff, details = [], []
    if hospital_ids:
        staff = await _db(
            lambda: (
                sb.table("on_call_staff")
                .select("hospital_id,specialty")
                .in_("hospital_id", hospital_ids)
                .eq("on_duty", True)
                .execute()
                .data
            )
        )
        details = await _db(
            lambda: (
                sb.table("hospital_details")
                .select("blood_stock")
                .in_("org_id", hospital_ids)
                .execute()
                .data
            )
        )
    groups = allowed_groups([d["blood_stock"] for d in details])
    d_ok, v_ok = donors_eligible(inc), volunteers_eligible(inc)
    return {
        "assigned_hospitals": [
            {
                "hospital_id": a["hospital_id"],
                "name": a["organizations"]["name"],
                "critical": a["critical"],
                "casualties": a["assigned_casualties"],
            }
            for a in assigned
        ],
        "required_specialties": specialties,
        "on_call": [
            {"hospital_id": h, "specialty": sp, "available": n}
            for (h, sp), n in _count(staff).items()
        ],
        "donors": {
            "eligible": d_ok,
            "allowed_groups": groups if d_ok else [],
            "nearby_count": len(await _eligible_donors(inc, groups)) if d_ok else 0,
        },
        "volunteers": {
            "eligible": v_ok,
            "nearby_count": len(await _eligible_volunteers(inc)) if v_ok else 0,
        },
        "doctors_eligible": doctors_eligible(inc),
    }


def _count(staff: list[dict]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = {}
    for s in staff:
        key = (s["hospital_id"], s["specialty"])
        counts[key] = counts.get(key, 0) + 1
    return counts


async def _queue_target(incident_id: str, kind: str, label: str, **recipient) -> bool:
    """Insert one queued alert_target. False if it already exists (idempotent)."""
    sb = get_supabase()
    row = {
        "incident_id": incident_id,
        "recipient_kind": kind,
        "recipient_label": label,
        "status": "queued",
        "ack_due_at": None,  # doctors/donors/volunteers are never escalated
        **recipient,
    }
    try:
        await _db(lambda: sb.table("alert_targets").insert(row).execute())
    except APIError as e:
        if e.code == "23505":
            return False
        raise
    return True


async def call_doctors(
    incident_id: UUID | str, hospital_id: str, specialties: list[str]
) -> dict:
    """Guardrail: eligible incident, assigned hospital, specialties within the required ones, max 4."""
    inc = await _incident(incident_id)
    iid = str(incident_id)
    if not doctors_eligible(inc):
        return {"called": [], "rejected": specialties, "summary": "Not eligible"}
    if hospital_id not in {a["hospital_id"] for a in await _assigned(iid)}:
        return {
            "called": [],
            "rejected": specialties,
            "summary": "Hospital not assigned",
        }
    required = required_specialties(inc["injury_types"])
    ok = [s for s in dict.fromkeys(specialties) if s in required][
        :MAX_DOCTORS_PER_HOSPITAL
    ]
    rejected = [s for s in specialties if s not in ok]
    sb = get_supabase()
    called: list[str] = []
    for spec in ok:
        staff = await _db(
            lambda spec=spec: (
                sb.table("on_call_staff")
                .select("id,full_name")
                .eq("hospital_id", hospital_id)
                .eq("specialty", spec)
                .eq("on_duty", True)
                .order("priority")
                .limit(1)
                .execute()
                .data
            )
        )
        if not staff:
            rejected.append(spec)
            continue
        if await _queue_target(
            iid,
            "doctor",
            f"On-call {spec.replace('_', ' ')}",
            recipient_staff_id=staff[0]["id"],
        ):
            called.append(spec)
    if called:
        await events.add(
            iid,
            "doctor_called",
            f"{len(called)} on-call doctor(s) queued ({', '.join(called)}); {NO_CHANNEL}",
        )
        await audit.log(
            "system", "doctors_called", "incident", iid, details={"n": len(called)}
        )
    return {
        "called": called,
        "rejected": rejected,
        "summary": f"{len(called)} doctor(s) queued",
    }


async def ping_donors(incident_id: UUID | str, groups: list[str]) -> dict:
    inc = await _incident(incident_id)
    iid = str(incident_id)
    if not donors_eligible(inc):
        return {"pinged": 0, "summary": "Not eligible"}
    assigned = await _assigned(iid)
    sb = get_supabase()
    stocks = (
        await _db(
            lambda: (
                sb.table("hospital_details")
                .select("blood_stock")
                .in_("org_id", [a["hospital_id"] for a in assigned])
                .execute()
                .data
            )
        )
        if assigned
        else []
    )
    allowed = set(allowed_groups([s["blood_stock"] for s in stocks]))
    wanted = [g for g in groups if g in allowed]
    if not wanted:
        return {"pinged": 0, "summary": "No allowed blood group requested"}
    pinged = 0
    now = datetime.now(UTC).isoformat()
    for m in await _eligible_donors(inc, wanted):
        if await _queue_target(
            iid, "donor", "Blood donor", recipient_member_id=m["id"]
        ):
            pinged += 1
            await _db(
                lambda m=m: (
                    sb.table("community_members")
                    .update({"last_donor_ping_at": now})
                    .eq("id", m["id"])
                    .execute()
                )
            )
    if pinged:
        await events.add(
            iid,
            "donors_pinged",
            f"{pinged} blood donor(s) queued (groups {', '.join(wanted)}); {NO_CHANNEL}",
        )
        await audit.log(
            "system", "donors_pinged", "incident", iid, details={"n": pinged}
        )
    return {"pinged": pinged, "summary": f"{pinged} donor(s) queued"}


async def ping_volunteers(incident_id: UUID | str) -> dict:
    inc = await _incident(incident_id)
    iid = str(incident_id)
    if not volunteers_eligible(inc):
        return {"pinged": 0, "summary": "Not eligible"}
    sb = get_supabase()
    pinged = 0
    now = datetime.now(UTC).isoformat()
    for m in await _eligible_volunteers(inc):
        if await _queue_target(
            iid, "volunteer", "Trained volunteer", recipient_member_id=m["id"]
        ):
            pinged += 1
            await _db(
                lambda m=m: (
                    sb.table("community_members")
                    .update({"last_volunteer_ping_at": now})
                    .eq("id", m["id"])
                    .execute()
                )
            )
    if pinged:
        await events.add(
            iid,
            "volunteers_pinged",
            f"{pinged} trained volunteer(s) queued; {NO_CHANNEL}",
        )
        await audit.log(
            "system", "volunteers_pinged", "incident", iid, details={"n": pinged}
        )
    return {"pinged": pinged, "summary": f"{pinged} volunteer(s) queued"}


async def autopilot(incident_id: UUID | str) -> list[str]:
    """Do every eligible action with all allowed values. Returns a list of action descriptions."""
    opts = await prep_options(incident_id)
    actions: list[str] = []
    if opts["doctors_eligible"]:
        for h in opts["assigned_hospitals"]:
            if h["critical"] > 0:
                r = await call_doctors(
                    incident_id, h["hospital_id"], opts["required_specialties"]
                )
                if r["called"]:
                    actions.append(
                        f"queued {len(r['called'])} doctor(s) at {h['name']}"
                    )
    if opts["donors"]["eligible"]:
        r = await ping_donors(incident_id, opts["donors"]["allowed_groups"])
        if r["pinged"]:
            actions.append(f"queued {r['pinged']} donor(s)")
    if opts["volunteers"]["eligible"]:
        r = await ping_volunteers(incident_id)
        if r["pinged"]:
            actions.append(f"queued {r['pinged']} volunteer(s)")
    return actions
