import time
from uuid import uuid4

import pytest

from app.services import ack_tokens, messages
from app.services.dispatch import RequiredTarget, default_order

INCIDENT = {
    "short_code": "GM-AB23",
    "incident_type": "road_accident",
    "severity": "critical",
    "status": "verified",
    "location_label": "Ferozepur Road",
    "lat": 31.5036,
    "lng": 74.3305,
    "est_casualties_min": 5,
    "est_casualties_max": 12,
    "injury_types": ["bleeding", "fracture"],
    "ongoing_danger": True,
    "silent": False,
    "summary_en": "Bus and motorbikes crashed.",
    "summary_local": "حادثہ",
    "local_lang": "ur",
    "landmark_text": "Near Kalma Chowk, opposite the petrol pump",
    "landmark_local": "کلمہ چوک کے قریب",
    "confidence": 0.65,
    "report_count": 3,
}


def test_inbox_token_roundtrip_and_tamper():
    org = uuid4()
    token = ack_tokens.make_inbox_token(org)
    assert ack_tokens.verify_inbox_token(token) == org
    with pytest.raises(ack_tokens.InvalidToken):
        ack_tokens.verify_inbox_token(token[:-2] + "xx")
    with pytest.raises(ack_tokens.InvalidToken):  # an ack token is not an inbox token
        ack_tokens.verify_inbox_token(ack_tokens.make_token(org))


def test_inbox_token_expires(monkeypatch):
    token = ack_tokens.make_inbox_token(uuid4())
    time.sleep(1.1)
    monkeypatch.setattr(ack_tokens, "INBOX_TOKEN_MAX_AGE_S", 0)
    with pytest.raises(ack_tokens.ExpiredToken):
        ack_tokens.verify_inbox_token(token)


def test_ack_token_payload_carries_channel():
    target = uuid4()
    token = ack_tokens.make_token(target, channel="dashboard")
    payload = ack_tokens._load(token, "ack-v1", 60)
    assert payload["t"] == str(target) and payload["c"] == "dashboard" and payload["j"]


def test_org_alert_english_and_urdu():
    en = messages.org_alert(INCIDENT, "en")
    assert en[0] == "🚨 CRITICAL – Road accident  GM-AB23"
    assert any(line.startswith("🧭 Near Kalma Chowk") for line in en)
    assert "⚠ Danger may be ongoing" in en and en[-1].startswith("Press ✅")
    ur = messages.org_alert(INCIDENT, "ur")
    assert "🧭 کلمہ چوک کے قریب" in ur and any("🌐 حادثہ" in line for line in ur)


def test_unverified_alert_line():
    lines = messages.org_alert({**INCIDENT, "status": "unverified"}, "en")
    assert lines[0] == "❓ UNVERIFIED – 3 report(s), confidence 65%"


def test_silent_line_and_no_landmark_slot_when_missing():
    lines = messages.org_alert(
        {**INCIDENT, "silent": True, "landmark_text": None, "landmark_local": None},
        "en",
    )
    assert "⚠ SILENT REPORT – DO NOT CALL REPORTER" in lines
    assert not any(line.startswith("🧭") for line in lines)


def test_hospital_brief_and_standby():
    assignment = {"assigned_casualties": 8, "critical": 3, "eta_minutes": 4.2}
    brief = messages.hospital_brief(INCIDENT, assignment, "en", standby=False)
    assert brief[0] == "🏥 PRE-ARRIVAL – GM-AB23"
    assert "➡ Expect 8 patient(s): 3 critical, 5 minor" in brief
    assert "🚑 First ambulance ETA: ~4 min" in brief
    standby = messages.hospital_brief(
        {**INCIDENT, "status": "unverified"}, assignment, "en", standby=True
    )
    assert standby[0].startswith("🟡 STANDBY (UNVERIFIED)")
    assert standby[-1].startswith("Prepare, but do not activate")


def test_all_languages_and_telegram_escape():
    texts = messages.all_languages(messages.org_alert, INCIDENT)
    assert set(texts) == {"en", "es", "ur"}
    html = messages.telegram_html(["<b>x</b> & y", "second"])
    assert html.startswith("<b>&lt;b&gt;x&lt;/b&gt; &amp; y</b>")


def test_default_order_police_first_for_attacks():
    targets = [
        RequiredTarget(key=k, kind=kind, org_id=k, label=k)
        for k, kind in (
            ("fire", "fire"),
            ("police", "police"),
            ("rescue", "rescue"),
            ("hospital:1", "hospital"),
        )
    ]
    assert default_order(targets, "attack_shooting")[0] == "police"
    assert default_order(targets, "road_accident") == [
        "rescue",
        "hospital:1",
        "police",
        "fire",
    ]
