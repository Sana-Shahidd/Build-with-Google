def to_ewkt(lat: float, lng: float) -> str:
    """PostGIS geography value for Supabase writes. Longitude FIRST (docs/05 conventions)."""
    return f"SRID=4326;POINT({lng} {lat})"
