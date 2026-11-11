"""Intake autopilot: keyword classifier (docs/07_AI_AGENTS.md §8) and the bare-SOS default (§7)."""

import json
import re
from pathlib import Path

from app.models.ai import IncidentExtraction

_KW = json.loads(
    (Path(__file__).parent.parent / "data" / "rules_keywords.json").read_text(
        encoding="utf-8"
    )
)
_URDU_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_HIGH_TYPES = {"attack_shooting", "explosion", "building_collapse", "riot_crowd"}

SOS_SUMMARY = {
    "en": "SOS button pressed. No details given.",
    "es": "Se pulsó el botón SOS. Sin detalles.",
    "ur": "ایس او ایس بٹن دبایا گیا۔ تفصیل نہیں دی گئی۔",
}
SILENT_SUMMARY = {
    "en": "Silent SOS - reporter may be in danger and cannot speak.",
    "es": "SOS silencioso: la persona puede estar en peligro y no puede hablar.",
    "ur": "خاموش ایس او ایس – رپورٹر خطرے میں ہو سکتا ہے اور بول نہیں سکتا۔",
}
WHAT_HAPPENED = {"en": "What happened?", "es": "¿Qué pasó?", "ur": "کیا ہوا ہے؟"}
WHAT_HAPPENED_TYPE = {
    "en": "What happened? Please type briefly.",
    "es": "¿Qué pasó? Escríbelo brevemente.",
    "ur": "کیا ہوا ہے؟ مختصر لکھیں۔",
}


def _lang(lang: str | None) -> str:
    return lang if lang in SOS_SUMMARY else "en"


def sos_default(
    lang: str | None = None, silent: bool = False, empty_voice: bool = False
) -> IncidentExtraction:
    """Fixed extraction for a bare SOS (no LLM)."""
    lang = _lang(lang)
    summary = SILENT_SUMMARY[lang] if silent else SOS_SUMMARY[lang]
    question = None
    if not silent:
        question = (WHAT_HAPPENED_TYPE if empty_voice else WHAT_HAPPENED)[lang]
    return IncidentExtraction(
        is_emergency=True,
        incident_type="other",
        severity="high",
        est_casualties_min=0,
        est_casualties_max=1,
        injury_types=["unknown"],
        needs=["ambulance", "police"],
        ongoing_danger=silent,
        location_hint=None,
        summary_en=SILENT_SUMMARY["en"] if silent else SOS_SUMMARY["en"],
        summary_local=summary,
        language_detected="unknown",
        confidence=0.5,
        missing_info=["incident_type"],
        followup_question=question,
        rationale="Bare SOS: default high-severity extraction.",
    )


def _matches(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def _casualties(text: str) -> tuple[int, int]:
    for m in re.finditer(r"\d+", text.translate(_URDU_DIGITS)):
        n = int(m.group())
        if 1 <= n <= 500:
            return n, n
    if _matches(text, _KW["many_words"]):
        return 5, 20
    if _matches(text, _KW["some_words"]):
        return 2, 6
    return 0, 0


def classify(text: str) -> IncidentExtraction:
    """Deterministic keyword classifier; used when the Intake Agent fails (Rule 2)."""
    low = text.lower().translate(_URDU_DIGITS)
    kind = next(
        (k for k, words in _KW["incident_type"].items() if _matches(low, words)),
        "other",
    )
    injuries = [k for k, words in _KW["injury_types"].items() if _matches(low, words)]
    cmin, cmax = _casualties(low)
    return IncidentExtraction(
        is_emergency=True,
        incident_type=kind,
        severity="high" if kind in _HIGH_TYPES else "medium",
        est_casualties_min=cmin,
        est_casualties_max=cmax,
        injury_types=injuries[:8] or (["unknown"] if cmax else []),
        needs=[],
        ongoing_danger=kind
        in {"attack_shooting", "fire", "building_collapse", "explosion"},
        location_hint=None,
        summary_en=("Unverified report (auto-parsed): " + text[:150])[:240],
        summary_local=text[:200],
        language_detected="unknown",
        # 0.35 when no keyword matched; 0.5 when an emergency type was recognised, so one accurate
        # report still becomes `unverified` and alerts go out (AGENTS.md Rule 2; DECISIONS.md)
        confidence=0.5 if kind != "other" else 0.35,
        missing_info=[],
        followup_question=None,
        rationale="Autopilot keyword classifier.",
    )
