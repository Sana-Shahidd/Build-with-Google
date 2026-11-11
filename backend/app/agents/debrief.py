"""Debrief Agent (docs/07 section 6.6, T-23): after-action report when an incident closes.
Autopilot: `debrief.template_report`. Runs in the background; never blocks closing."""

import asyncio
import logging
from uuid import UUID

from agents import (
    Agent,
    AgentOutputSchema,
    ModelSettings,
    RunContextWrapper,
    function_tool,
)

from app.agents.context import AgentCtx
from app.agents.runner import run_agent
from app.config import DEBRIEF_TIMEOUT_S
from app.deps import get_supabase
from app.models.ai import AfterActionReport
from app.services import activity, debrief, events

INSTRUCTIONS = """You are the Debrief Agent of Golden Minute. Call get_incident_timeline, then write a short
after-action report in Markdown for the control room, using ONLY that data. No personal
data, no phone numbers, no medical advice. Times in the time zone given, HH:MM:SS.
Sections: ## Summary, ## Timeline (bullets), ## Response performance (time to first alert,
time to each acknowledgement, escalations, agent vs autopilot decisions), ## What worked,
## Delays and gaps, ## Recommendations (max 5 bullets)."""

_background: set[asyncio.Task] = set()


@function_tool(strict_mode=False)
async def get_incident_timeline(ctx: RunContextWrapper[AgentCtx]) -> dict:
    """The incident facts, events, alert targets, hospital assignments and agent statistics."""
    data = await debrief.timeline(str(ctx.context.incident_id))
    return {**data, "summary": f"Timeline with {len(data['events'])} events"}


def make_agent(model) -> Agent:
    return Agent(
        name="Debrief Agent",
        instructions=INSTRUCTIONS,
        model=model,
        model_settings=ModelSettings(temperature=0.2),
        tools=[get_incident_timeline],
        output_type=AgentOutputSchema(AfterActionReport, strict_json_schema=False),
    )


async def run_debrief(incident_id: UUID | str) -> str:
    """Generate and save the after-action report. Returns 'agent' or 'template'."""
    ctx = AgentCtx(incident_id=UUID(str(incident_id)))
    out = await run_agent(
        "debrief",
        make_agent,
        "<task>Write the after-action report for this incident.</task>",
        ctx,
        timeout_s=DEBRIEF_TIMEOUT_S,
        total_budget_s=DEBRIEF_TIMEOUT_S,
        max_turns=2,
    )
    how = "agent"
    if isinstance(out, AfterActionReport) and debrief.validate_markdown(out.markdown):
        markdown = out.markdown
    else:
        if isinstance(out, AfterActionReport):
            await activity.log(
                ctx,
                "debrief",
                "guardrail_block",
                "Agent report rejected: sections or numbers",
            )
        markdown = debrief.template_report(await debrief.timeline(str(incident_id)))
        how = "template"
        await activity.log(
            ctx, "debrief", "fallback", "Autopilot: template after-action report"
        )
    sb = get_supabase()
    await asyncio.to_thread(
        lambda: (
            sb.table("incidents")
            .update({"after_action_md": markdown})
            .eq("id", str(incident_id))
            .execute()
        )
    )
    await events.add(incident_id, "update_sent", f"After-action report ready ({how})")
    return how


def schedule_debrief(incident_id: UUID | str) -> None:
    async def guarded() -> None:
        try:
            await run_debrief(incident_id)
        except Exception:
            logging.getLogger(__name__).exception("debrief failed")

    task = asyncio.create_task(guarded())
    _background.add(task)
    task.add_done_callback(_background.discard)
