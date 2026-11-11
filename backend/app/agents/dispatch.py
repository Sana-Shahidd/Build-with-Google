"""Dispatch Agent (docs/07_AI_AGENTS.md section 6.4, T-17).

The agent only chooses the ORDER of alerts. Recipients are required by `dispatch.required_targets`,
message text is a fixed template, unknown keys are rejected, omitted required keys are appended.
Autopilot: `dispatch.default_order`.
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
from app.config import DISPATCH_TIMEOUT_S
from app.models.ai import DispatchPlan
from app.services import activity, dispatch

INSTRUCTIONS = """You are the Dispatch Agent of Golden Minute. All required responders will be alerted; your
job is to choose the ORDER that saves the most time.
1. Call get_required_targets.
2. Order the keys: for an active shooter or ongoing violence, police first; for many
   casualties, EMS and the hospital receiving the most critical patients first; for fire or
   explosion, fire service early. Dispatchers can come last.
3. Call send_alerts once with ALL keys in your order and a one-sentence rationale.
You cannot write messages or add recipients; messages are fixed templates."""


def split_keys(
    keys: list[str], required: list[dispatch.RequiredTarget]
) -> tuple[list[str], list[str], list[str]]:
    """(ordered valid keys without duplicates, rejected unknown keys, auto-added missing keys)."""
    valid = {t.key for t in required}
    ordered: list[str] = []
    rejected: list[str] = []
    for k in keys:
        if k not in valid:
            rejected.append(k)
        elif k not in ordered:
            ordered.append(k)
    added = [t.key for t in required if t.key not in ordered]
    return ordered, rejected, added


@function_tool
async def get_required_targets(ctx: RunContextWrapper[AgentCtx]) -> dict:
    """Responders that must be alerted for this incident (keys, kinds, labels)."""
    c = ctx.context
    inc = (
        c.extraction
    )  # set by the caller: dict with type, severity, ongoing_danger, status, casualties
    return {
        "targets": [
            {
                "key": t.key,
                "kind": t.kind,
                "label": t.label,
                "is_standby": t.standby,
                "channels": ["dashboard"],
            }
            for t in c.required_targets
        ],
        "incident": inc,
        "summary": f"{len(c.required_targets)} required target(s)",
    }


@function_tool
async def send_alerts(
    ctx: RunContextWrapper[AgentCtx], target_keys_in_order: list[str], rationale: str
) -> dict:
    """Alert all required targets in the given order. Unknown keys are rejected, missing ones added."""
    c = ctx.context
    ordered, rejected, added = split_keys(target_keys_in_order, c.required_targets)
    if rejected:
        await activity.log(
            c,
            "dispatch",
            "guardrail_block",
            f"Unknown target key(s) rejected: {len(rejected)}",
        )
    sent = await dispatch.send_targets(c.incident_id, ordered + added)
    c.sent_keys = sent
    return {
        "sent": sent,
        "auto_added": added,
        "rejected": rejected,
        "summary": f"Sent {len(sent)} alert(s)"
        + (f", auto-added {len(added)}" if added else ""),
    }


def make_agent(model) -> Agent:
    return Agent(
        name="Dispatch Agent",
        instructions=INSTRUCTIONS,
        model=model,
        model_settings=ModelSettings(temperature=0.1),
        tools=[get_required_targets, send_alerts],
        output_type=AgentOutputSchema(DispatchPlan, strict_json_schema=False),
    )


async def run(
    ctx: AgentCtx, incident: dict, targets: list[dispatch.RequiredTarget]
) -> bool:
    """True if the agent sent the alerts (ctx.sent_keys filled by the send_alerts tool)."""
    ctx.required_targets = targets
    ctx.extraction = {
        "type": incident["incident_type"],
        "severity": incident["severity"],
        "ongoing_danger": incident["ongoing_danger"],
        "casualties_max": incident["est_casualties_max"],
        "status": incident["status"],
    }
    out = await run_agent(
        "dispatch",
        make_agent,
        "<task>Order the alerts for this incident.</task>",
        ctx,
        timeout_s=DISPATCH_TIMEOUT_S,
        total_budget_s=DISPATCH_TIMEOUT_S,
        max_turns=3,
    )
    return isinstance(out, DispatchPlan) and bool(ctx.sent_keys)
