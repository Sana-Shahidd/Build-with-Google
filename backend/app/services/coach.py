"""Voice Coach logic (F-39, docs/07_AI_AGENTS.md section 6.8). No medical text is ever written here:
the words spoken for a step come from first_aid.json; the coach only picks a card and a calm phrase.
"""

import json
import re
from pathlib import Path

from app.models.ai import CoachTurn
from app.services import first_aid, labels

_KW = json.loads(
    (Path(__file__).parent.parent / "data" / "rules_keywords.json").read_text(
        encoding="utf-8"
    )
)
_URDU_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_ANY_DIGIT = re.compile(r"\d")
# docs/07 6.8 lists these among the banned words but rules_keywords.json lacks them
_EXTRA_BANNED = ["گولیاں", "گولی کھا", "tablets", "pills", "injection"]


def _contains(text: str, keyword: str) -> bool:
    """Short ASCII keywords (ok, aap...) must match whole words; longer ones may match inside words."""
    if keyword.isascii() and len(keyword) <= 3:
        return re.search(rf"(?<![a-z]){re.escape(keyword)}(?![a-z])", text) is not None
    return keyword in text


def classify_intent(text: str, lang: str = "en") -> CoachTurn:
    """Autopilot: the LONGEST matching keyword across intents and cards wins (most specific phrase)."""
    low = text.lower().translate(_URDU_DIGITS)
    best: tuple[int, str, str] | None = None  # (keyword length, "intent"/"card", name)
    for intent, words in _KW["coach_intents"].items():
        for w in words:
            if _contains(low, w) and (best is None or len(w) > best[0]):
                best = (len(w), "intent", intent)
    for card, words in _KW["coach_cards"].items():
        for w in words:
            if _contains(low, w) and (best is None or len(w) >= best[0]):
                best = (len(w), "card", card)
    if best is None:
        return CoachTurn(
            intent="unclear",
            ack=labels.coach_ack("unclear", lang),
            rationale="No keyword matched.",
        )
    _, kind, name = best
    if kind == "card":
        return CoachTurn(
            intent="switch_card",
            card_key=name if name in first_aid.card_keys() else "call_help",
            ack=labels.coach_ack("switch_card", lang),
            rationale="Autopilot keyword match.",
        )
    return CoachTurn(
        intent=name,
        ack=labels.coach_ack(name, lang),
        rationale="Autopilot keyword match.",
    )


def step_text(card_key: str, step: int, lang: str) -> dict:
    """{title, step, of, text, icon, is_last} for one step, straight from first_aid.json."""
    card = first_aid.get_card(card_key, lang)
    total = len(card["steps"])
    step = max(0, min(step, total - 1))
    return {
        "title": card["title"],
        "step": step,
        "of": total,
        "text": card["steps"][step],
        "icon": card["icon"],
        "is_last": step == total - 1,
    }


def _ack_ok(ack: str) -> bool:
    low = ack.lower().translate(_URDU_DIGITS)
    return (
        0 < len(ack) <= 120
        and not _ANY_DIGIT.search(low)
        and not any(w in low for w in [*_KW["coach_banned"], *_EXTRA_BANNED])
    )


def validate_turn(turn: CoachTurn, valid_keys: set[str], lang: str = "en") -> CoachTurn:
    """Guardrail: card_key only for switch_card and only a known key; the ack must be calm text only."""
    card_key = (
        turn.card_key
        if turn.intent == "switch_card" and turn.card_key in valid_keys
        else None
    )
    intent = turn.intent
    if intent == "switch_card" and card_key is None:
        intent = (
            "unclear"  # unknown card: never read anything the file does not contain
        )
    ack = (
        turn.ack
        if _ack_ok(turn.ack) and intent == turn.intent
        else labels.coach_ack(intent, lang)
    )
    return turn.model_copy(update={"intent": intent, "card_key": card_key, "ack": ack})
