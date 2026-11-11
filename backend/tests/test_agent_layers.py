from uuid import uuid4

from app.agents import dispatch as dispatch_agent
from app.agents import triage, verification
from app.models.ai import (
    Candidate,
    HospitalOption,
    HospitalOptions,
    PlannedAssignment,
    VerificationDecision,
)
from app.services import dispatch


def cand(i: str) -> Candidate:
    return Candidate(
        id=i, incident_type="fire", created_at="2026-01-01T00:00:00Z", distance_m=50
    )


def test_verification_guardrail():
    a, b = str(uuid4()), str(uuid4())
    cands = [cand(a)]
    ok = VerificationDecision(
        action="merge", incident_id=a, confidence=0.8, rationale="same"
    )
    assert verification.validate_decision(ok, cands) is not None
    low = ok.model_copy(update={"confidence": 0.5})
    assert verification.validate_decision(low, cands) is None
    unknown = ok.model_copy(update={"incident_id": b})
    assert verification.validate_decision(unknown, cands) is None
    new = VerificationDecision(action="new", confidence=0.9, rationale="different")
    assert verification.validate_decision(new, cands) is None


def opts() -> HospitalOptions:
    def h(i: str, free: int) -> HospitalOption:
        return HospitalOption(
            id=i,
            name=i,
            lat=0,
            lng=0,
            capabilities=["trauma"],
            free_beds=free,
            icu_available=0,
            capacity_known=True,
            eta_minutes=5,
            distance_m=1000,
            fits=True,
        )

    return HospitalOptions(
        total=4,
        critical_total=1,
        required_capabilities=[],
        hospitals=[h("h1", 2), h("h2", 5)],
    )


def test_triage_finalize_sets_code_owned_fields():
    plan = [PlannedAssignment(hospital_id="h1", casualties=4, critical=1, reason="x")]
    out = triage.finalize_plan(plan, opts())
    assert out[0].eta_minutes == 5 and out[0].over_capacity is True  # 4 > 2 free beds


def test_dispatch_split_keys():
    t = lambda k, kind: dispatch.RequiredTarget(key=k, kind=kind, org_id=k, label=k)
    req = [t("rescue", "rescue"), t("police", "police"), t("hospital:1", "hospital")]
    ordered, rejected, added = dispatch_agent.split_keys(
        ["police", "bogus", "police", "rescue"], req
    )
    assert ordered == ["police", "rescue"]
    assert rejected == ["bogus"]
    assert added == ["hospital:1"]
