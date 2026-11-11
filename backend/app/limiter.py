import hashlib

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)


def user_or_ip(request: Request) -> str:
    """Rate-limit key: the caller's token (hashed) when present, else the IP (docs/08 S-02)."""
    auth = request.headers.get("authorization")
    if auth:
        return "u:" + hashlib.sha256(auth.encode()).hexdigest()[:24]
    return get_remote_address(request)
