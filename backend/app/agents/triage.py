"""Triage Agent (docs/07_AI_AGENTS.md section 6.3, T-16).

The agent proposes a casualty spread; `matching.validate_plan` (code) accepts or rejects it.
Autopilot: `matching.spread`. The caller falls back to it when no plan was accepted.
"""

from agents import (
    Agent,
    AgentOutputSchema,
    ModelSettings,
    RunContextWrapper,
    function_tool,
)

from app.agents.context import AgentCtx
from app.agents.runner import run_agent
from app.config import TRIAGE_TIMEOUT_S
from app.models.ai import HospitalOptions, PlannedAssignment, TriagePlan
from app.services import activity, matching

INSTRUCTIONS = """You are the Triage Agent of Golden Minute. Distribute the expected casualties of one
incident across hospitals so every patient gets the right care fast and no ER is
overwhelmed.
1. Call get_hospital_options.
2. Send critical patients ONLY to hospitals where fits=true (they have the required
   capabilities, e.g. burns unit or trauma center), nearest first, within their free ER beds.
3. Send minor patients to the nearest hospitals with free beds, preferring hospitals that
   are NOT receiving many critical patients.
4. Use between 1 and 5 hospitals. The casualties must add up exactly to total, and critical
   to critical_total.
5. Call propose_assignment_plan once with your plan and a one-sentence rationale. If it
   returns errors, fix them and call it one more time.
Final output: accepted = whether the last proposal returned ok; rationale = one sentence."""


def finalize_plan(
    plan: list[PlannedAssignment], opts: HospitalOptions
) -> list[PlannedAssignment]:
    """Fill code-owned fields (ETA, over-capacity flag) so an agent cannot set them."""
    by_id = {h.id: h for h in opts.hospitals}
    out: list[PlannedAssignment] = []
    for a in plan:
        h = by_id[a.hospital_id]
        out.append(
            a.model_copy(
                update={
                    "eta_minutes": h.eta_minutes,
                    "over_capacity": h.capacity_known and a.casualties > h.free_beds,
                }
            )
        )
    return out


@function_tool
async def get_hospital_options(ctx: RunContextWrapper[AgentCtx]) -> dict:
    """Hospitals near the incident with capabilities, free ER beds, ETA and capability fit."""
    opts: HospitalOptions = ctx.context.hospital_options
    return {
        "total": opts.total,
        "critical_total": opts.critical_total,
        "required_capabilities": opts.required_capabilities,
        "options": [
            {
                "hospital_id": h.id,
                "name": h.name,
                "capabilities": h.capabilities,
                "free_er_beds": h.free_beds if h.capacity_known else None,
                "icu_available": h.icu_available,
                "eta_minutes": h.eta_minutes,
                "fits": h.fits,
            }
            for h in opts.hospitals
        ],
        "summary": f"{len(opts.hospitals)} hospital option(s) for {opts.total} casualties "
        f"({opts.critical_total} critical)",
    }


@function_tool(strict_mode=False)
async def propose_assignment_plan(
    ctx: RunContextWrapper[AgentCtx],
    assignments: list[PlannedAssignment],
    rationale: str,
) -> dict:
    """Validate a plan with the guardrail; if ok it is saved as the incident's plan."""
    c = ctx.context
    errors = matching.validate_plan(assignments, c.hospital_options)
    if errors:
        await activity.log(
            c, "triage", "guardrail_block", f"Plan rejected: {errors[0]}"[:200]
        )
        return {"ok": False, "errors": errors, "summary": f"Rejected: {errors[0]}"}
    final = finalize_plan(assignments, c.hospital_options)
    await matching.save_plan(c.incident_id, final, "agent")
    c.accepted_plan = final
    return {
        "ok": True,
        "errors": [],
        "summary": f"Plan accepted: {len(final)} hospital(s)",
    }


def make_agent(model) -> Agent:
    return Agent(
        name="Triage Agent",
        instructions=INSTRUCTIONS,
        model=model,
        model_settings=ModelSettings(temperature=0.1),
        tools=[get_hospital_options, propose_assignment_plan],
        output_type=AgentOutputSchema(TriagePlan, strict_json_schema=False),
    )


async def plan(ctx: AgentCtx) -> bool:
    """Run the agent. True only if code accepted a plan (ctx.accepted_plan is set and saved)."""
    out = await run_agent(
        "triage",
        make_agent,
        "<task>Plan the hospital assignment for this incident.</task>",
        ctx,
        timeout_s=TRIAGE_TIMEOUT_S,
        total_budget_s=TRIAGE_TIMEOUT_S,
        max_turns=4,
    )
    return isinstance(out, TriagePlan) and bool(ctx.accepted_plan)
