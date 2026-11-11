import asyncio
import time
from collections.abc import Callable
from typing import Any

from agents import Runner

from app.agents.context import AgentCtx
from app.agents.hooks import ActivityHooks
from app.agents.models import build_model, provider_of
from app.config import AGENT_TIMEOUT_S, PROVIDER_COOLDOWN_S, settings
from app.services import activity

_cooldown_until: dict[str, float] = {}


def _is_rate_limited(e: Exception) -> bool:
    return getattr(e, "status_code", None) == 429


async def run_agent(
    agent_key: str,
    agent_factory: Callable[[Any], Any],
    input: Any,
    ctx: AgentCtx,
    *,
    timeout_s: float = AGENT_TIMEOUT_S,
    total_budget_s: float | None = None,
    max_turns: int = 4,
) -> object | None:
    """Try the primary model, then the fallback. Returns final_output, or None so the caller
    runs the autopilot. Writes agent_activity rows (docs/07_AI_AGENTS.md §2)."""
    deadline = time.monotonic() + total_budget_s if total_budget_s else None
    for spec in (settings.model_for(agent_key), settings.fallback_for(agent_key)):
        if not spec:
            continue
        remaining = deadline - time.monotonic() if deadline else timeout_s
        if remaining < 2:  # budget used up: let the autopilot take over
            break
        provider = provider_of(spec)
        if _cooldown_until.get(spec, 0) > time.monotonic():
            await activity.log(
                ctx,
                agent_key,
                "fallback",
                f"{spec.split(':', 1)[1]} cooling down",
                model=spec,
            )
            continue
        started = time.monotonic()
        try:
            agent = agent_factory(build_model(spec))
            res = await asyncio.wait_for(
                Runner.run(
                    agent,
                    input,
                    context=ctx,
                    max_turns=max_turns,
                    hooks=ActivityHooks(agent_key, ctx, spec),
                ),
                timeout=min(timeout_s, remaining),
            )
            await activity.log(
                ctx,
                agent_key,
                "finished",
                "Agent finished",
                model=spec,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
            ctx.model_used = spec
            return res.final_output
        except Exception as e:  # noqa: BLE001 - timeouts, 429, validation errors, MaxTurnsExceeded
            if _is_rate_limited(e):
                _cooldown_until[spec] = time.monotonic() + PROVIDER_COOLDOWN_S
            await activity.log(
                ctx,
                agent_key,
                "fallback",
                f"{provider} failed: {type(e).__name__}",
                model=spec,
            )
    return None
