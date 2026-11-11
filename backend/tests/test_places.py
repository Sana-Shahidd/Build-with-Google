import pytest
from pydantic import ValidationError

from app.services import places


def test_place_create_validation():
    ok = places.PlaceCreate(
        name="Ali Store", place_type="shop", lat=31.5, lng=74.3, consent=True
    )
    assert ok.lang == "ur"
    with pytest.raises(ValidationError):
        places.PlaceCreate(
            name="A", place_type="shop", lat=31.5, lng=74.3, consent=True
        )
    with pytest.raises(ValidationError):
        places.PlaceCreate(
            name="Ali Store", place_type="castle", lat=31.5, lng=74.3, consent=True
        )
    with pytest.raises(ValidationError):
        places.PlaceCreate(
            name="Ali Store", place_type="shop", lat=131.5, lng=74.3, consent=True
        )


def test_place_tokens_are_unguessable_and_unique():
    tokens = {places.new_token() for _ in range(50)}
    assert len(tokens) == 50 and all(len(t) >= 24 for t in tokens)
