import asyncio
import logging

from app.deps import get_supabase

logger = logging.getLogger(__name__)


async def log(
    actor_kind: str,
    action: str,
    entity: str,
    entity_id: str | None = None,
    *,
    actor_id: str | None = None,
    details: dict | None = None,
) -> None:
    """Write one audit_log row (docs/08_SECURITY.md S-12). Never raises; never put PII in details."""
    row = {
        "actor_kind": actor_kind,
        "actor_id": actor_id,
        "action": action,
        "entity": entity,
        "entity_id": entity_id,
        "details": details or {},
    }
    try:
        await asyncio.to_thread(
            lambda: get_supabase().table("audit_log").insert(row).execute()
        )
    except Exception as e:  # noqa: BLE001 - auditing must not break the alert path
        logger.warning("audit insert failed: %s", type(e).__name__)
