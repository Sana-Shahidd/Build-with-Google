"""Hour-1 check: every configured agent model must support tool calling + typed output.

Usage: python -m scripts.agent_smoke
Each distinct model spec is tested once (a tool call and a JSON-schema output); results are
then printed per agent x primary/fallback.
"""

import asyncio
import time

from agents import Agent, AgentOutputSchema, ModelSettings, Runner, function_tool
from pydantic import BaseModel

from app.agents.models import build_model
from app.config import settings

AGENT_KEYS = (
    "intake",
    "verification",
    "triage",
    "dispatch",
    "hospital_prep",
    "debrief",
    "landmark",
    "coach",
    "preparedness",
)


class Smoke(BaseModel):
    answer: int
    rationale: str


@function_tool
def add_numbers(a: int, b: int) -> dict:
    """Add two integers."""
    return {"sum": a + b, "summary": f"{a}+{b}={a + b}"}


# Groq rejects tools + JSON-schema output together (docs/DECISIONS.md), so only these agents
# use tools; the others are tested (and run) with typed output only.
TOOL_AGENTS = {
    "intake",
    "verification",
    "triage",
    "dispatch",
    "hospital_prep",
    "debrief",
}


async def check(spec: str, use_tools: bool = True) -> str:
    started = time.monotonic()
    try:
        agent = Agent(
            name="smoke",
            instructions=(
                "Use the add_numbers tool for 2 and 3, then return its sum as answer."
                if use_tools
                else "Return answer=5 and a short rationale."
            ),
            model=build_model(spec),
            model_settings=ModelSettings(temperature=0.1),
            tools=[add_numbers] if use_tools else [],
            output_type=AgentOutputSchema(Smoke, strict_json_schema=False),
        )
        res = await asyncio.wait_for(Runner.run(agent, "go", max_turns=4), timeout=30)
        out = res.final_output
        ms = int((time.monotonic() - started) * 1000)
        return f"ok ({ms} ms)" if out.answer == 5 else f"WRONG answer={out.answer}"
    except Exception as e:  # noqa: BLE001
        return f"ERROR {type(e).__name__}: {str(e)[:120]}"


async def main() -> None:
    results: dict[tuple[str, bool], str] = {}
    for k in AGENT_KEYS:
        for spec in (settings.model_for(k), settings.fallback_for(k)):
            key = (spec, k in TOOL_AGENTS)
            if (
                spec and key not in results
            ):  # sequential: stay under free-tier rate limits
                results[key] = await check(spec, key[1])
    for k in AGENT_KEYS:
        for label, spec in (
            ("primary", settings.model_for(k)),
            ("fallback", settings.fallback_for(k)),
        ):
            res = results.get((spec, k in TOOL_AGENTS), "unset")
            print(f"{k:14s} {label:8s} {spec:34s} {res}")


if __name__ == "__main__":
    asyncio.run(main())
