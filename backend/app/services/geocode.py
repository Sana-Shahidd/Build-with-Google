"""Location label for coordinates (docs/07_AI_AGENTS.md §13). Nominatim via geopy, cached."""

from app.services import country


async def reverse_label(lat: float, lng: float, hint: str | None = None) -> str:
    """Nominatim label, else the reporter's location hint, else 'lat, lng'."""
    _, label = await country.detect(lat, lng)
    return label or hint or f"{lat:.4f}, {lng:.4f}"
