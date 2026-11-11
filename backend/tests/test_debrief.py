from app.services import debrief

DATA = {
    "timezone": "Asia/Karachi",
    "incident": {
        "short_code": "GM-TEST",
        "type": "road_accident",
        "severity": "high",
        "status": "closed",
        "location_label": "Kalma Chowk",
        "casualties_max": 6,
        "report_count": 4,
        "unique_reporters": 3,
        "confidence": 0.6,
        "created_at": "2026-01-01T10:00:00+00:00",
        "first_alert_at": "2026-01-01T10:00:30+00:00",
        "first_ack_at": "2026-01-01T10:02:00+00:00",
        "closed_at": "2026-01-01T10:30:00+00:00",
    },
    "events": [
        {
            "time": "2026-01-01T10:00:00+00:00",
            "kind": "created",
            "message": "Incident created",
        }
    ],
    "targets": [
        {
            "label": "Rescue 1122",
            "kind": "rescue",
            "created_at": "2026-01-01T10:00:30+00:00",
            "acknowledged_at": "2026-01-01T10:02:00+00:00",
            "escalation_level": 0,
            "status": "acknowledged",
            "standby": False,
        },
        {
            "label": "Police",
            "kind": "police",
            "created_at": "2026-01-01T10:00:30+00:00",
            "acknowledged_at": None,
            "escalation_level": 1,
            "status": "sent",
            "standby": False,
        },
    ],
    "assignments": [],
    "agent_stats": {"agent_decisions": 2, "autopilot": 3, "guardrail_blocks": 1},
}


def test_template_has_sections_numbers_and_gaps():
    md = debrief.template_report(DATA)
    assert debrief.validate_markdown(md)
    assert (
        "30 s" in md and "90 s" in md
    )  # first alert 30 s, first ack 90 s after the alert
    assert "No acknowledgement from: Police" in md
    assert "15:00:00" in md  # 10:00 UTC shown in Asia/Karachi


def test_validate_rejects_phone_numbers_and_missing_sections():
    md = debrief.template_report(DATA)
    assert not debrief.validate_markdown(md + "\nCall +92 300 1234567")
    assert not debrief.validate_markdown("## Summary\nonly this")
