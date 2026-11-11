import pytest

from app.models.ai import CoachTurn
from app.services import coach, first_aid

KEYS = first_aid.card_keys()


@pytest.mark.parametrize(
    "text,intent,card",
    [
        ("khoon nahi ruk raha", "switch_card", "bleeding"),
        ("saans nahi aa rahi, behosh hai", "switch_card", "cardiac"),
        ("اب کیا کروں", "unclear", None),
        ("ambulance aa gayi", "done", None),
        ("ok", "next", None),
        ("okay next", "next", None),
        ("dobara bolo", "repeat", None),
        ("he is not breathing", "switch_card", "cardiac"),
        ("my hand is burned", "switch_card", "burns"),
        ("book", "unclear", None),  # 'ok' inside a word must not match
    ],
)
def test_autopilot_intents(text, intent, card):
    turn = coach.classify_intent(text, "en")
    assert (turn.intent, turn.card_key) == (intent, card)


def test_fixed_ack_is_in_the_language():
    assert coach.classify_intent("ok", "ur").ack == "ٹھیک ہے۔ اگلا قدم۔"


def test_step_text_comes_from_the_card_file():
    s = coach.step_text("bleeding", 0, "en")
    assert s["text"] == first_aid.get_card("bleeding", "en")["steps"][0]
    assert coach.step_text("bleeding", 99, "en")["is_last"] is True
    assert coach.step_text("bleeding", -3, "en")["step"] == 0


def turn(**kw):
    base = {
        "intent": "switch_card",
        "card_key": "bleeding",
        "ack": "Okay, stay with me.",
        "rationale": "x",
    }
    return CoachTurn(**{**base, **kw})


def test_validate_accepts_a_calm_turn():
    t = coach.validate_turn(turn(), KEYS)
    assert (t.intent, t.card_key, t.ack) == (
        "switch_card",
        "bleeding",
        "Okay, stay with me.",
    )


@pytest.mark.parametrize(
    "ack",
    [
        "Take 2 aspirin now",
        "Give 500 mg",
        "Take paracetamol",
        "دو گولیاں",
        "take pills",
        "",
    ],
)
def test_validate_replaces_unsafe_acks(ack):
    t = coach.validate_turn(turn(ack=ack), KEYS)
    assert t.ack == "Okay, stay with me. I will tell you what to do."


def test_validate_rejects_unknown_or_misplaced_cards():
    unknown = coach.validate_turn(turn(card_key="surgery"), KEYS)
    assert unknown.intent == "unclear" and unknown.card_key is None
    misplaced = coach.validate_turn(turn(intent="next", card_key="bleeding"), KEYS)
    assert misplaced.card_key is None and misplaced.intent == "next"
