"""First-aid card selection from the vetted static file (docs/07_AI_AGENTS.md §9-§10).

No agent or code ever writes first-aid text; everything spoken comes from first_aid.json.
"""

import json
from pathlib import Path

_DATA = Path(__file__).parent.parent / "data"
_CARDS: dict[str, dict] = json.loads(
    (_DATA / "first_aid.json").read_text(encoding="utf-8")
)
INJURY_MAP: dict[str, dict] = json.loads(
    (_DATA / "injury_capability_map.json").read_text(encoding="utf-8")
)

_STAY_SAFE_TYPES = {
    "attack_shooting",
    "explosion",
    "riot_crowd",
    "fire",
    "building_collapse",
    "flood",
}
_PRIORITY = [
    "unconscious",
    "cardiac",
    "bleeding",
    "drowning",
    "breathing",
    "burns",
    "smoke",
    "head_injury",
    "crush",
    "fracture",
    "call_help",
]
MAX_CARDS = 3


def card_keys() -> set[str]:
    return set(_CARDS)


def select_keys(incident_type: str | None, injury_types: list[str]) -> list[str]:
    """Card keys for an incident: stay_safe first for dangerous types, then injuries by priority."""
    keys: list[str] = []
    if incident_type in _STAY_SAFE_TYPES:
        keys.append("stay_safe")
    wanted = {INJURY_MAP[i]["first_aid"] for i in injury_types if i in INJURY_MAP}
    keys += sorted(wanted, key=_PRIORITY.index)
    keys = list(dict.fromkeys(keys))[:MAX_CARDS]
    return keys or ["call_help"]


def get_card(key: str, lang: str = "en") -> dict:
    """{key, icon, title, steps} in the requested language (fallback en)."""
    card = _CARDS[key]
    body = card.get(lang) or card["en"]
    return {
        "key": key,
        "icon": card["icon"],
        "title": body["title"],
        "steps": body["steps"],
    }


def select(
    incident_type: str | None, injury_types: list[str], lang: str = "en"
) -> list[dict]:
    return [get_card(k, lang) for k in select_keys(incident_type, injury_types)]


def generic_cards(lang: str = "en") -> list[dict]:
    """Shown immediately after a report is received, before Intake finishes."""
    return [get_card("stay_safe", lang), get_card("call_help", lang)]
