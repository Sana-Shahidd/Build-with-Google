"""Landmark Agent (docs/07_AI_AGENTS.md section 6.9, F-38).

Code finds and ranks OSM landmarks, the agent only phrases ONE sentence, validation rejects invented
names or distances, and the template autopilot is the guaranteed fallback. Never blocks alerts.
"""

import asyncio
import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from agents import Agent, AgentOutputSchema, ModelSettings

from app.agents.context import AgentCtx
from app.agents.runner import run_agent
from app.config import LANDMARK_TIMEOUT_S
from app.deps import get_supabase
from app.models.ai import Landmark, LandmarkLine
from app.services import activity, events, landmarks

INSTRUCTIONS = """You are the Landmark Agent of Golden Minute. Write directions to the incident spot that a
local ambulance driver can follow without a map, the way people give directions in
Pakistan or the United States ("near the petrol pump, opposite the mosque"). Use ONLY the
numbered landmarks given: their names, distances and compass directions. Never invent a
place, a road name or a distance. Write ONE sentence (max 25 words) in the language given
(line_local) and the same sentence in English (line_en). Put the numbers of the landmarks
you used in "used". If no landmark is useful, return empty lines and used=[]."""

_background: set[asyncio.Task] = set()


def make_agent(model) -> Agent:
    return Agent(
        name="Landmark Agent",
        instructions=INSTRUCTIONS,
        model=model,
        model_settings=ModelSettings(temperature=0.1),
        output_type=AgentOutputSchema(LandmarkLine, strict_json_schema=False),
    )


def build_input(lang: str, area: str | None, found: list[Landmark]) -> str:
    rows = "\n".join(
        f"{lm.index} | {lm.kind} | {lm.name} | {lm.distance_m} m | {lm.compass}"
        for lm in found
    )
    return f"<incident>language: {lang} · area: {area or '-'}</incident>\n<landmarks>\n{rows}\n</landmarks>"


async def run_landmark_step(
    incident_id: UUID | str, lat: float, lng: float, lang: str, area: str | None
) -> None:
    """Find landmarks, phrase them (agent, else template) and save the line on the incident."""
    ctx = AgentCtx(incident_id=UUID(str(incident_id)), lang=lang)
    started = time.monotonic()
    found = await landmarks.nearby_landmarks(lat, lng, lang)
    if not found:
        await activity.log(
            ctx,
            "landmark",
            "rule",
            "No landmarks found: alerts use coordinates and the area label",
        )
        return

    line_local = line_en = ""
    out = await run_agent(
        "landmark",
        make_agent,
        build_input(lang, area, found),
        ctx,
        timeout_s=LANDMARK_TIMEOUT_S,
        total_budget_s=LANDMARK_TIMEOUT_S,
        max_turns=1,
    )
    if isinstance(out, LandmarkLine) and landmarks.validate_landmark_line(
        out.line_local, out.line_en, out.used, found
    ):
        line_local, line_en, how = out.line_local, out.line_en, "agent"
    else:
        if isinstance(out, LandmarkLine):
            await activity.log(
                ctx,
                "landmark",
                "guardrail_block",
                "Agent line rejected: unknown name or distance",
            )
        line_en = landmarks.template_landmark_line(found, "en")
        line_local = (
            landmarks.template_landmark_line(found, lang) if lang != "en" else line_en
        )
        how = "template"

    sb = get_supabase()
    await asyncio.to_thread(
        lambda: (
            sb.table("incidents")
            .update(
                {
                    "landmark_text": line_en,
                    "landmark_local": line_local,
                    "landmark_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", str(incident_id))
            .execute()
        )
    )
    await events.add(
        incident_id, "update_sent", f"Landmark line added: {line_en}"[:300]
    )
    await activity.log(
        ctx,
        "landmark",
        "decision" if how == "agent" else "rule",
        f"{line_en} ({len(found)} landmarks, {time.monotonic() - started:.1f} s, {how})"[
            :200
        ],
        data={"how": how},
    )


def schedule_landmark(
    incident_id: UUID | str, lat: float, lng: float, lang: str, area: str | None
) -> None:
    """Run beside the alert path: never awaited by it, never raises."""

    async def guarded() -> None:
        try:
            await run_landmark_step(incident_id, lat, lng, lang, area)
        except Exception:
            logging.getLogger(__name__).exception("landmark step failed")

    task = asyncio.create_task(guarded())
    _background.add(task)
    task.add_done_callback(_background.discard)
