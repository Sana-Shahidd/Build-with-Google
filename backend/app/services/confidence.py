"""Incident confidence and status (docs/02_PRD.md F-06). Code decides, never an LLM."""

from app.config import CONF_UNVERIFIED, CONF_VERIFIED

_RANK = {"review": 0, "unverified": 1, "verified": 2}


def compute_confidence(
    max_ai_conf: float,
    unique_reporters: int,
    has_photo: bool,
    any_phone_verified: bool,
    best_accuracy_m: float | None,
) -> float:
    c = (
        0.40 * max_ai_conf
        + 0.25 * min(1.0, (unique_reporters - 1) / 3)
        + 0.15 * (1 if has_photo else 0)
        + 0.10 * (1 if any_phone_verified else 0)
        + 0.10 * (1 if best_accuracy_m is not None and best_accuracy_m <= 100 else 0)
    )
    return max(0.0, min(1.0, c))


def status_from_confidence(c: float, current: str, all_non_emergency: bool) -> str:
    """Automatic moves only go up; closed/dismissed never change; non-emergency stays review."""
    if current in ("closed", "dismissed"):
        return current
    if all_non_emergency:
        return current if current in _RANK and _RANK[current] > 0 else "review"
    computed = (
        "verified"
        if c >= CONF_VERIFIED
        else "unverified"
        if c >= CONF_UNVERIFIED
        else "review"
    )
    return max(computed, current, key=lambda s: _RANK.get(s, 0))
