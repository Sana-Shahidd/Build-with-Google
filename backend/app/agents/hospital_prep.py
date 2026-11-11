"""Hospital Prep Agent (docs/07 section 6.5, T-20). Tracked only: see services/hospital_prep.py.

Runs when an incident is verified (background). The agent picks among eligible actions; every tool
re-checks eligibility in code. Autopilot: `hospital_prep.autopilot` (every eligible action).
"""

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
from app.config import AGENT_TIMEOUT_S
from app.models.ai import PrepSummary
from app.services import activity, events, hospital_prep

INSTRUCTIONS = """You are the Hospital Prep Agent of Golden Minute. Get receiving hospitals ready before
patients arrive.
1. Call get_prep_options.
2. If doctors_eligible, call call_doctors for each assigned hospital that receives critical
   patients, requesting only the required specialties that hospital needs most (max 4).
3. If donors.eligible, call ping_donors with the allowed groups.
4. If volunteers.eligible, call ping_volunteers.
Do only what is eligible. Output the list of actions taken and a one-sentence rationale."""

_background: set[asyncio.Task] = set()
_started: set[str] = (
    set()
)  # one prep run per incident per process (actions are idempotent anyway)


@function_tool(strict_mode=False)
async def get_prep_options(ctx: RunContextWrapper[AgentCtx]) -> dict:
    """Assigned hospitals, required specialties, on-call availability, donor and volunteer eligibility."""
    opts = await hospital_prep.prep_options(ctx.context.incident_id)
    return {**opts, "summary": "Prep options loaded"}


@function_tool
async def call_doctors(
    ctx: RunContextWrapper[AgentCtx], hospital_id: str, specialties: list[str]
) -> dict:
    """Queue on-call doctors of one assigned hospital (guardrailed)."""
    return await hospital_prep.call_doctors(
        ctx.context.incident_id, hospital_id, specialties
    )


@function_tool
async def ping_donors(ctx: RunContextWrapper[AgentCtx], groups: list[str]) -> dict:
    """Queue blood donors of the allowed groups (guardrailed)."""
    return await hospital_prep.ping_donors(ctx.context.incident_id, groups)


@function_tool
async def ping_volunteers(ctx: RunContextWrapper[AgentCtx]) -> dict:
    """Queue trained volunteers close to the incident (guardrailed)."""
    return await hospital_prep.ping_volunteers(ctx.context.incident_id)


def make_agent(model) -> Agent:
    return Agent(
        name="Hospital Prep Agent",
        instructions=INSTRUCTIONS,
        model=model,
        model_settings=ModelSettings(temperature=0.1),
        tools=[get_prep_options, call_doctors, ping_donors, ping_volunteers],
        output_type=AgentOutputSchema(PrepSummary, strict_json_schema=False),
    )


async def run_prep(incident_id: UUID | str) -> str:
    """Agent first; if it gave no answer, the autopilot does every eligible action. Returns 'agent'/'autopilot'."""
    ctx = AgentCtx(incident_id=UUID(str(incident_id)))
    out = await run_agent(
        "hospital_prep",
        make_agent,
        "<task>Prepare receiving hospitals for this incident.</task>",
        ctx,
        timeout_s=AGENT_TIMEOUT_S,
        total_budget_s=AGENT_TIMEOUT_S,
        max_turns=4,
    )
    if isinstance(out, PrepSummary):
        return "agent"
    actions = await hospital_prep.autopilot(incident_id)
    await activity.log(
        ctx,
        "hospital_prep",
        "fallback",
        "Autopilot: " + ("; ".join(actions) if actions else "nothing eligible"),
    )
    return "autopilot"


async def on_hospital_ack(incident_id: UUID | str, hospital_id: str | None) -> None:
    """Rule (no LLM): when a hospital acks a verified incident and no doctors were called yet for it,
    call that hospital's required specialties."""
    try:
        opts = await hospital_prep.prep_options(incident_id)
        mine = [
            h for h in opts["assigned_hospitals"] if h["hospital_id"] == hospital_id
        ]
        if not (opts["doctors_eligible"] and mine):
            return
        r = await hospital_prep.call_doctors(
            incident_id, hospital_id, opts["required_specialties"]
        )
        if r["called"]:
            await activity.log(
                AgentCtx(incident_id=UUID(str(incident_id))),
                "hospital_prep",
                "rule",
                f"Hospital acknowledged: queued {len(r['called'])} doctor(s)",
            )
    except Exception:
        logging.getLogger(__name__).exception("hospital ack prep rule failed")


def schedule_prep(incident_id: UUID | str) -> None:
    """Runs beside the alert path and never blocks or raises."""
    if str(incident_id) in _started:
        return
    _started.add(str(incident_id))

    async def guarded() -> None:
        try:
            await run_prep(incident_id)
        except Exception:
            logging.getLogger(__name__).exception("hospital prep failed")
            await events.add(incident_id, "update_sent", "Hospital prep failed")

    task = asyncio.create_task(guarded())
    _background.add(task)
    task.add_done_callback(_background.discard)
