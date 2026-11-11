"""Needs rules + severity floors (docs/02_PRD.md F-05 floors, F-07). Code decides, not the agent."""

import re

from app.models.ai import IncidentExtraction
from app.models.enums import Severity

_ORDER = [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _at_least(current: Severity, floor: Severity) -> Severity:
    return max(current, floor, key=_ORDER.index)


def _clean(text: str | None) -> str | None:
    return _CONTROL.sub("", text) if text else text


def apply_rules(e: IncidentExtraction) -> IncidentExtraction:
    """Validate/normalise an extraction, add required needs and raise severity to its floors."""
    kind = e.incident_type.value
    needs = {n.value for n in e.needs}
    injuries = list(dict.fromkeys(e.injury_types))
    if len(injuries) > 1 and "unknown" in injuries:
        injuries.remove("unknown")  # type: ignore[arg-type]

    if injuries or e.est_casualties_max > 0:
        needs.add("ambulance")
    if kind in ("attack_shooting", "explosion", "riot_crowd"):
        needs.add("police")
    if kind in ("fire", "explosion"):
        needs.add("fire")
    if kind in ("building_collapse", "flood"):
        needs.add("rescue")

    severity = e.severity
    if e.est_casualties_max >= 15:
        severity = _at_least(severity, Severity.CRITICAL)
    elif e.est_casualties_max >= 5:
        severity = _at_least(severity, Severity.HIGH)
    if kind in ("attack_shooting", "explosion", "building_collapse"):
        severity = _at_least(severity, Severity.HIGH)

    return IncidentExtraction.model_validate(
        {
            **e.model_dump(),
            "needs": sorted(needs),
            "injury_types": injuries,
            "severity": severity,
            "summary_en": _clean(e.summary_en),
            "summary_local": _clean(e.summary_local),
            "location_hint": _clean(e.location_hint),
            "missing_info": list(dict.fromkeys(e.missing_info)),
        }
    )
