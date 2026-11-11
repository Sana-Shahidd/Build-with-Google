import asyncio
import threading
from dataclasses import dataclass
from uuid import UUID

from fastapi import Request
from supabase import Client, create_client

from app.config import settings
from app.utils.errors import ApiError

_local = threading.local()


def get_supabase() -> Client:
    """Service-role client, ONE PER THREAD: the synchronous client is not thread-safe, and every call
    runs through asyncio.to_thread, so concurrent reports shared one socket and failed (ReadError)."""
    client = getattr(_local, "client", None)
    if client is None:
        client = create_client(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
        )
        _local.client = client
    return client


@dataclass
class CurrentUser:
    id: UUID
    role: str
    org_id: UUID | None
    is_anonymous: bool
    phone_verified: bool


async def get_current_user(request: Request) -> CurrentUser:
    """Validate the Supabase JWT with auth.get_user (never hand-verify), then load the profile."""
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise ApiError(401, "UNAUTHENTICATED", "Missing token")
    token = header[7:].strip()
    sb = get_supabase()
    try:
        res = await asyncio.to_thread(lambda: sb.auth.get_user(token))
        user = res.user
        profile = await asyncio.to_thread(
            lambda: (
                sb.table("profiles")
                .select("role,org_id")
                .eq("id", user.id)
                .execute()
                .data
            )
        )
    except Exception as e:
        raise ApiError(401, "UNAUTHENTICATED", "Invalid token") from e
    if not user or not profile:
        raise ApiError(401, "UNAUTHENTICATED", "Invalid token")
    return CurrentUser(
        id=UUID(user.id),
        role=profile[0]["role"],
        org_id=UUID(profile[0]["org_id"]) if profile[0]["org_id"] else None,
        is_anonymous=bool(getattr(user, "is_anonymous", False)),
        phone_verified=bool(getattr(user, "phone_confirmed_at", None)),
    )


def require_role(*roles: str):
    async def dep(request: Request) -> CurrentUser:
        user = await get_current_user(request)
        if user.role not in roles:
            raise ApiError(403, "FORBIDDEN", "Not allowed")
        return user

    return dep
