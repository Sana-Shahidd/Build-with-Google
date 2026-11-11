import pytest
from pydantic import ValidationError

from app.services import cards, crypto


def test_card_line_templates_have_no_name_or_phone():
    card = {
        "blood_type": "O+",
        "allergies": "penicillin",
        "full_name": "Ahmad",
        "phone": "+9230",
    }
    assert cards.card_line(card, "en") == "🪪 Card: blood O+, allergy: penicillin"
    assert "Ahmad" not in cards.card_line(card, "ur") and "+92" not in cards.card_line(
        card, "ur"
    )
    assert (
        cards.card_line({"blood_type": "A-", "allergies": None}, "es")
        == "🪪 Tarjeta: sangre A-"
    )
    assert cards.card_line({"blood_type": None, "allergies": None}, "en") == ""


def test_token_is_unguessable_and_unique():
    tokens = {cards.new_token() for _ in range(50)}
    assert len(tokens) == 50 and all(len(t) == 24 for t in tokens)


def test_card_create_validation():
    ok = {
        "full_name": "Ahmad",
        "contacts": [{"name": "Bhai", "phone": "+923001234567"}],
        "consent": True,
    }
    assert cards.CardCreate(**ok).lang == "ur"
    with pytest.raises(ValidationError):
        cards.CardCreate(**{**ok, "contacts": []})
    with pytest.raises(ValidationError):
        cards.CardCreate(**{**ok, "contacts": [ok["contacts"][0]] * 4})
    with pytest.raises(ValidationError):
        cards.CardCreate(**{**ok, "blood_type": "Z+"})


def test_phone_is_normalised_and_encrypted():
    e164 = crypto.to_e164("0300 1234567", "PK")
    assert e164 == "+923001234567"
    enc = crypto.encrypt_phone(e164)
    assert e164 not in enc and crypto.decrypt_phone(enc) == e164
    assert crypto.phone_hash(e164) == crypto.phone_hash(e164)
    with pytest.raises(ValueError):
        crypto.to_e164("123", "PK")
