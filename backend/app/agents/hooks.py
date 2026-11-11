from typing import Any

from agents import RunHooks

from app.agents.context import AgentCtx
from app.services import activity


def _summary(result: object) -> str:
    """Tools return a dict/model with a `summary` field used for the feed."""
    if isinstance(result, dict) and "summary" in result:
        return str(result["summary"])
    summary = getattr(result, "summary", None)
    return str(summary) if summary else str(result)[:120]


def _ctx(context: Any) -> AgentCtx | None:
    inner = getattr(context, "context", None)
    return inner if isinstance(inner, AgentCtx) else None


class ActivityHooks(RunHooks[AgentCtx]):
    """Writes the Agent Activity feed (docs/07_AI_AGENTS.md §3)."""

    def __init__(
        self, agent_key: str, ctx: AgentCtx | None = None, model: str | None = None
    ):
        self.agent_key = agent_key
        self.ctx = ctx
        self.model = model

    def _c(self, context: Any) -> AgentCtx | None:
        return self.ctx or _ctx(context)

    async def on_agent_start(self, context, agent) -> None:
        await activity.log(
            self._c(context), self.agent_key, "started", "Started", model=self.model
        )

    async def on_tool_start(self, context, agent, tool) -> None:
        await activity.log(
            self._c(context),
            self.agent_key,
            "tool_call",
            f"Calling {tool.name}",
            tool=tool.name,
        )

    async def on_tool_end(self, context, agent, tool, result) -> None:
        await activity.log(
            self._c(context),
            self.agent_key,
            "tool_result",
            _summary(result),
            tool=tool.name,
        )

    async def on_agent_end(self, context, agent, output) -> None:
        rationale = getattr(output, "rationale", None) or "Finished"
        await activity.log(
            self._c(context),
            self.agent_key,
            "decision",
            str(rationale)[:200],
            model=self.model,
        )
