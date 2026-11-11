import asyncio
import logging
from uuid import UUID

from app.deps import get_supabase

logger = logging.getLogger(__name__)


async def add(
    incident_id: UUID | str, kind: str, message: str, data: dict | None = None
) -> None:
    """Write one incident_events row (the incident timeline). Never raises."""
    row = {
        "incident_id": str(incident_id),
        "kind": kind,
        "message": message,
        "data": data or {},
    }
    try:
        await asyncio.to_thread(
            lambda: get_supabase().table("incident_events").insert(row).execute()
        )
    except Exception as e:  # noqa: BLE001
        logger.warning("event insert failed: %s", type(e).__name__)
