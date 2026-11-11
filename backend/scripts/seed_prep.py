"""Demo on-call doctors, donors and volunteers for the Hospital Prep Agent (T-20). Idempotent.

Usage: python -m scripts.seed_prep
Phone numbers are obviously fake test numbers (+92300000xxxx); nothing is ever sent to them.
"""

import asyncio
from datetime import UTC, datetime

from app.deps import get_supabase
from app.services import crypto
from app.utils.geo import to_ewkt

CRASH_SITE = (31.5036, 74.3305)
SPECIALTIES = [
    "trauma_surgeon",
    "anesthetist",
    "emergency_physician",
    "orthopedic_surgeon",
    "burn_specialist",
]
# (name, blood type, is_donor, skills, offset lat, offset lng)  ~0.0005 deg = 55 m
MEMBERS = [
    ("Demo donor 1", "O+", True, [], 0.004, 0.003),
    ("Demo donor 2", "O-", True, [], -0.006, 0.002),
    ("Demo donor 3", "A+", True, [], 0.010, -0.004),
    ("Demo volunteer 1", None, False, ["cpr", "first_aid"], 0.003, 0.002),
    ("Demo volunteer 2", None, False, ["nurse"], -0.004, -0.003),
    ("Demo volunteer 3", "B+", True, ["doctor"], 0.002, -0.002),
]


async def main() -> None:
    sb = get_supabase()
    hospitals = (
        sb.rpc(
            "nearest_orgs",
            {
                "p_type": "hospital",
                "p_lat": CRASH_SITE[0],
                "p_lng": CRASH_SITE[1],
                "p_radius_m": 10000,
                "p_limit": 15,
            },
        )
        .execute()
        .data
    )
    for h in hospitals:
        have = {
            r["specialty"]
            for r in sb.table("on_call_staff")
            .select("specialty")
            .eq("hospital_id", h["id"])
            .execute()
            .data
        }
        rows = [
            {
                "hospital_id": h["id"],
                "full_name": f"Demo Dr {s.replace('_', ' ')}",
                "specialty": s,
                "priority": 1,
                "lang": "en",
            }
            for s in SPECIALTIES
            if s not in have
        ]
        if rows:
            sb.table("on_call_staff").insert(rows).execute()
    for i, (name, blood, donor, skills, dlat, dlng) in enumerate(MEMBERS, start=1):
        phone = f"+9230000000{i:02d}"
        if (
            sb.table("community_members")
            .select("id")
            .eq("phone_hash", crypto.phone_hash(phone))
            .execute()
            .data
        ):
            continue
        sb.table("community_members").insert(
            {
                "display_name": name,
                "phone_enc": crypto.encrypt_phone(phone),
                "phone_hash": crypto.phone_hash(phone),
                "home_location": to_ewkt(CRASH_SITE[0] + dlat, CRASH_SITE[1] + dlng),
                "is_donor": donor,
                "blood_type": blood,
                "skills": skills,
                "lang": "en",
                "consent_at": datetime.now(UTC).isoformat(),
            }
        ).execute()
    print(
        f"Seeded on-call staff for {len(hospitals)} hospitals and {len(MEMBERS)} demo community members."
    )


asyncio.run(main())
