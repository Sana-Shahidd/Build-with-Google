"""Signed acknowledgement tokens (docs/08_SECURITY.md S-04). Library: itsdangerous only.

Two token kinds, same secret, different salts:
  * ack token   {"t": target_id, "j": jti, "c": channel}  one alert, single use
  * inbox token {"o": org_id}                             one organization's responder page
"""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import ACK_TOKEN_MAX_AGE_S, INBOX_TOKEN_MAX_AGE_S, settings
from app.deps import get_supabase
from app.services import audit, events


class InvalidToken(Exception):
    pass


class ExpiredToken(Exception):
    pass


class UsedToken(Exception):
    pass


def _ser(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.ACK_SECRET, salt=salt)


def _load(token: str, salt: str, max_age: int) -> dict:
    try:
        return _ser(salt).loads(token, max_age=max_age)
    except SignatureExpired as e:
        raise ExpiredToken from e
    except BadSignature as e:
        raise InvalidToken from e


def make_token(
    target_id: UUID | str, jti: UUID | str | None = None, channel: str = "dashboard"
) -> str:
    payload = {"t": str(target_id), "j": str(jti or uuid4()), "c": channel}
    return _ser("ack-v1").dumps(payload)


async def issue_token(target_id: UUID | str, channel: str = "dashboard") -> str:
    """Token for one alert; reuses the stored jti while unused so polled pages keep a valid button."""
    sb = get_supabase()
    tid = str(target_id)
    row = (
        await asyncio.to_thread(
            lambda: (
                sb.table("alert_targets")
                .select("ack_token_jti,ack_token_used_at")
                .eq("id", tid)
                .execute()
                .data
            )
        )
    )[0]
    jti = (
        row["ack_token_jti"]
        if row["ack_token_jti"] and not row["ack_token_used_at"]
        else str(uuid4())
    )
    if jti != row["ack_token_jti"]:
        await asyncio.to_thread(
            lambda: (
                sb.table("alert_targets")
                .update({"ack_token_jti": jti})
                .eq("id", tid)
                .execute()
            )
        )
    return make_token(tid, jti, channel)


async def verify_token(token: str) -> tuple[UUID, str]:
    """(target_id, channel). Raises InvalidToken / ExpiredToken / UsedToken."""
    payload = _load(token, "ack-v1", ACK_TOKEN_MAX_AGE_S)
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("alert_targets")
            .select("ack_token_jti,ack_token_used_at")
            .eq("id", payload["t"])
            .execute()
            .data
        )
    )
    if not rows or rows[0]["ack_token_jti"] != payload["j"]:
        raise InvalidToken
    if rows[0]["ack_token_used_at"]:
        raise UsedToken
    return UUID(payload["t"]), payload["c"]


def make_inbox_token(org_id: UUID | str) -> str:
    return _ser("inbox-v1").dumps({"o": str(org_id)})


def verify_inbox_token(token: str) -> UUID:
    return UUID(_load(token, "inbox-v1", INBOX_TOKEN_MAX_AGE_S)["o"])


async def acknowledge(target_id: UUID | str, via: str, actor: str | None) -> bool:
    """Mark the target acknowledged; True if this call was the first ack (later acks no-op)."""
    sb = get_supabase()
    tid, now = str(target_id), datetime.now(UTC).isoformat()
    updated = await asyncio.to_thread(
        lambda: (
            sb.table("alert_targets")
            .update(
                {
                    "status": "acknowledged",
                    "acknowledged_at": now,
                    "acknowledged_via": via,
                    "acknowledged_by": actor,
                    "ack_due_at": None,
                    "ack_token_used_at": now,
                    "updated_at": now,
                }
            )
            .eq("id", tid)
            .neq("status", "acknowledged")
            .execute()
            .data
        )
    )
    if not updated:
        return False
    target = updated[0]
    await asyncio.to_thread(
        lambda: (
            sb.table("incidents")
            .update({"first_ack_at": now})
            .eq("id", target["incident_id"])
            .is_("first_ack_at", "null")
            .execute()
        )
    )
    await events.add(
        target["incident_id"],
        "acknowledged",
        f"{target['recipient_label']} acknowledged via {via}",
    )
    await audit.log(
        "responder", "alert_acknowledged", "alert_target", tid, details={"via": via}
    )
    if target["recipient_kind"] == "hospital" and not target["is_standby"]:
        from app.agents import hospital_prep  # T-20 rule, lazy import

        await hospital_prep.on_hospital_ack(
            target["incident_id"], target["recipient_org_id"]
        )
    return True
