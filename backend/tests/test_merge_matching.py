from uuid import uuid4

import pytest

from app.models.ai import Candidate, HospitalOption, HospitalOptions, IncidentExtraction
from app.services import confidence, matching, rules_classifier
from app.services.merge import autopilot_decision, fast_path
from app.utils.short_code import new_short_code


def cand(distance: float, kind: str = "road_accident") -> Candidate:
    return Candidate(
        id=str(uuid4()),
        incident_type=kind,
        created_at="2026-11-10T00:00:00Z",
        distance_m=distance,
    )


def extraction(kind: str):
    e = rules_classifier.sos_default("en")
    return IncidentExtraction.model_validate({**e.model_dump(), "incident_type": kind})


def hosp(
    i: int, free: int, eta: float, caps=("general",), fits=True, known=True
) -> HospitalOption:
    return HospitalOption(
        id=f"h{i}",
        name=f"Hospital {i}",
        lat=31.5,
        lng=74.3,
        capabilities=list(caps),
        free_beds=free,
        icu_available=1,
        capacity_known=known,
        eta_minutes=eta,
        distance_m=eta * 400,
        fits=fits,
    )


# ---- confidence -----------------------------------------------------------------------------
def test_confidence_formula_and_status():
    single = confidence.compute_confidence(0.95, 1, False, False, 50)
    assert single == pytest.approx(0.38 + 0.10)
    assert confidence.status_from_confidence(single, "review", False) == "unverified"
    three = confidence.compute_confidence(0.95, 3, False, False, 50)
    assert three == pytest.approx(0.38 + 0.1667 + 0.10, abs=1e-3)
    assert confidence.status_from_confidence(three, "unverified", False) == "verified"


def test_status_only_goes_up_and_non_emergency_stays_review():
    assert confidence.status_from_confidence(0.1, "verified", False) == "verified"
    assert confidence.status_from_confidence(0.9, "review", True) == "review"
    assert confidence.status_from_confidence(0.9, "dismissed", False) == "dismissed"


def test_short_code_format():
    code = new_short_code()
    assert code.startswith("GM-") and len(code) == 7 and code[3:].isalnum()


# ---- merge rules ----------------------------------------------------------------------------
def test_fast_path_one_close_same_type():
    c = cand(100)
    assert str(fast_path([c], extraction("road_accident"))) == c.id
    assert fast_path([c], extraction("fire")) is None  # different type
    assert str(fast_path([c], extraction("other"))) == c.id  # 'other' is compatible
    assert (
        fast_path([cand(100), cand(120)], extraction("road_accident")) is None
    )  # ambiguous
    assert (
        fast_path([cand(300)], extraction("road_accident")) is None
    )  # too far for fast path


def test_autopilot_decision_nearest_compatible():
    far_other, near_same = cand(400, "fire"), cand(300)
    assert (
        str(autopilot_decision([far_other, near_same], extraction("road_accident")))
        == near_same.id
    )
    assert autopilot_decision([cand(300, "fire")], extraction("road_accident")) is None


# ---- matching -------------------------------------------------------------------------------
def opts(total: int, critical: int, hospitals) -> HospitalOptions:
    return HospitalOptions(
        total=total,
        critical_total=critical,
        required_capabilities=[],
        hospitals=hospitals,
    )


def test_12_casualties_spread_over_three_hospitals():
    o = opts(12, 5, [hosp(1, 4, 3), hosp(2, 4, 5), hosp(3, 6, 8), hosp(4, 20, 12)])
    plan = matching.spread(o)
    assert matching.validate_plan(plan, o) == []
    assert len(plan) >= 3
    assert not any(
        a.over_capacity for a in plan
    )  # nobody over free beds when beds suffice


def test_critical_only_to_fitting_hospitals():
    burns = hosp(2, 10, 9, caps=("general", "burns"), fits=True)
    near = hosp(1, 10, 2, fits=False)
    o = opts(6, 3, [near, burns])
    plan = matching.spread(o)
    assert matching.validate_plan(plan, o) == []
    assert {a.hospital_id for a in plan if a.critical} == {"h2"}


def test_over_capacity_is_flagged_and_totals_hold():
    o = opts(10, 4, [hosp(1, 2, 3), hosp(2, 1, 6)])
    plan = matching.spread(o)
    assert sum(a.casualties for a in plan) == 10 and sum(a.critical for a in plan) == 4
    assert any(a.over_capacity for a in plan)
    assert matching.validate_plan(plan, o) == []


def test_unknown_capacity_hospital_gets_no_critical_free_beds():
    o = opts(4, 2, [hosp(1, 50, 2, known=False), hosp(2, 5, 9)])
    plan = {a.hospital_id: a for a in matching.spread(o)}
    assert plan["h2"].critical == 2


def test_max_five_hospitals():
    o = opts(30, 10, [hosp(i, 2, i + 1) for i in range(8)])
    plan = matching.spread(o)
    assert len(plan) <= 5
    assert matching.validate_plan(plan, o) == []


def test_validate_plan_rejects_bad_plans():
    o = opts(5, 2, [hosp(1, 10, 2, fits=False), hosp(2, 10, 5, fits=True)])
    bad = matching.spread(o)[:0] + [
        matching.PlannedAssignment(
            hospital_id="nope", casualties=4, critical=2, reason="x"
        )
    ]
    errors = matching.validate_plan(bad, o)
    assert any("unknown hospital" in e for e in errors)
    assert any("sum to 5" in e for e in errors)
    wrong_fit = [
        matching.PlannedAssignment(
            hospital_id="h1", casualties=5, critical=2, reason="x"
        )
    ]
    assert any("missing capability" in e for e in matching.validate_plan(wrong_fit, o))


def test_no_casualties_no_plan():
    assert matching.spread(opts(0, 0, [hosp(1, 5, 2)])) == []


def test_required_capabilities_and_totals():
    assert matching.required_capabilities(["gunshot", "burns", "unknown"]) == [
        "trauma",
        "burns",
    ]
    inc = {"est_casualties_max": 0, "needs": ["ambulance"], "severity": "high"}
    assert matching.totals(inc) == (1, 1)
    assert matching.totals(
        {"est_casualties_max": 12, "needs": [], "severity": "critical"}
    ) == (12, 8)


def test_autopilot_single_accurate_report_is_unverified_not_review():
    """A keyword-classified report (confidence 0.5) with a GPS fix must still alert as UNVERIFIED."""
    c = confidence.compute_confidence(0.5, 1, False, False, 20)
    assert confidence.status_from_confidence(c, "review", False) == "unverified"
