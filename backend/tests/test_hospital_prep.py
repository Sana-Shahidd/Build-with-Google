from app.services import hospital_prep as hp


def inc(**kw):
    base = {
        "status": "verified",
        "severity": "critical",
        "est_casualties_max": 6,
        "injury_types": ["gunshot", "burns"],
        "needs": ["ambulance"],
        "ongoing_danger": False,
    }
    return {**base, **kw}


def test_required_specialties_order_and_cap():
    assert hp.required_specialties(["burns", "gunshot"]) == [
        "trauma_surgeon",
        "burn_specialist",
        "anesthetist",
    ]
    assert hp.required_specialties([]) == []
    many = ["gunshot", "burns", "head_injury", "fracture", "cardiac", "blast_shrapnel"]
    assert len(hp.required_specialties(many)) == 4


def test_eligibility_rules():
    assert hp.doctors_eligible(inc())
    assert not hp.doctors_eligible(inc(severity="high"))
    assert not hp.doctors_eligible(inc(status="unverified"))
    assert hp.donors_eligible(inc())
    assert not hp.donors_eligible(inc(est_casualties_max=2))
    assert not hp.donors_eligible(inc(injury_types=["fracture"]))
    assert hp.volunteers_eligible(inc(status="unverified"))
    assert not hp.volunteers_eligible(inc(ongoing_danger=True))
    assert not hp.volunteers_eligible(inc(needs=["police"]))
    assert not hp.volunteers_eligible(inc(status="closed"))


def test_allowed_groups_adds_low_stock():
    stock = {"A+": 10, "A-": 2, "B+": 5, "O-": 1, "O+": 12}
    assert hp.allowed_groups([stock]) == ["O-", "O+", "A-"]
    assert hp.allowed_groups([]) == ["O-", "O+"]
