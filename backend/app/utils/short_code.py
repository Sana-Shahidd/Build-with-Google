import secrets

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_short_code() -> str:
    """'GM-' + 4 chars from [A-Z2-9] (no 0/1/O/I lookalikes)."""
    return "GM-" + "".join(secrets.choice(_ALPHABET) for _ in range(4))
