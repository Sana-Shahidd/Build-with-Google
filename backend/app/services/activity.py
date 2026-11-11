import asyncio
import logging

from app.agents.context import AgentCtx
from app.deps import get_supabase

logger = logging.getLogger(__name__)

# agent keys used in env vars / runner -> agent_name enum value
_AGENT_NAME = {"coach": "voice_coach"}


async def log(
    ctx: AgentCtx | None,
    agent: str,
    kind: str,
    message: str,
    *,
    model: str | None = None,
    tool: str | None = None,
    latency_ms: int | None = None,
    data: dict | None = None,
) -> None:
    """Insert one agent_activity row (the live feed). Never raises: the feed must not stop alerts."""
    row = {
        "incident_id": str(ctx.incident_id) if ctx and ctx.incident_id else None,
        "report_id": str(ctx.report_id) if ctx and ctx.report_id else None,
        "agent": _AGENT_NAME.get(agent, agent),
        "kind": kind,
        "message": message[:200],
        "model": model,
        "tool": tool,
        "latency_ms": latency_ms,
        "data": data or {},
    }
    try:
        await asyncio.to_thread(
            lambda: get_supabase().table("agent_activity").insert(row).execute()
        )
    except Exception as e:  # noqa: BLE001 - activity logging is best-effort
        logger.warning("activity insert failed: %s", type(e).__name__)
