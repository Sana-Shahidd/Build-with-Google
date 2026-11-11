"""POST /api/v1/reports/{id}/coach (docs/06_API_SPEC.md section 6.1, F-39)."""

import asyncio
from collections import Counter
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from app.agents import voice_coach
from app.agents.context import AgentCtx
from app.config import COACH_MAX_PER_REPORT
from app.deps import CurrentUser, get_current_user, get_supabase
from app.limiter import limiter, user_or_ip
from app.services import activity, coach, first_aid, media
from app.services.transcribe import transcribe
from app.utils.errors import ApiError

router = APIRouter()
_turns: Counter[str] = (
    Counter()
)  # per-report turn counter (one backend process in this build)


@router.post("/reports/{report_id}/coach")
@limiter.limit("12/hour", key_func=user_or_ip)
async def coach_turn(
    request: Request,
    report_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    text: str | None = Form(default=None, max_length=300),
    audio: UploadFile | None = File(default=None),
    card_key: str | None = Form(default=None, max_length=40),
    step: int = Form(default=0, ge=0, le=20),
    lang: Literal["en", "es", "ur"] = Form(default="en"),
) -> dict:
    sb = get_supabase()
    owned = await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .select("id,incident_id")
            .eq("id", str(report_id))
            .eq("reporter_id", str(user.id))
            .execute()
            .data
        )
    )
    if not owned:
        raise ApiError(404, "NOT_FOUND", "Report not found")
    if _turns[str(report_id)] >= COACH_MAX_PER_REPORT:
        raise ApiError(429, "RATE_LIMITED", "Too many coach turns for this report")
    _turns[str(report_id)] += 1

    utterance = (text or "").strip()
    if audio is not None:
        data = await audio.read()
        try:
            ext, mime = media.check_audio(data)
        except media.MediaInvalid as e:
            raise ApiError(400, "MEDIA_INVALID", str(e)) from e
        utterance = (await transcribe(data, f"coach.{ext}", mime)).text
    if not utterance:
        raise ApiError(400, "VALIDATION_ERROR", "text or audio is required")

    ctx = AgentCtx(report_id=report_id, incident_id=owned[0]["incident_id"], lang=lang)
    turn, source = await voice_coach.decide_turn(utterance, lang, card_key, step, ctx)

    valid = first_aid.card_keys()
    current = card_key if card_key in valid else None
    key, n = current, step
    if turn.intent == "switch_card" and turn.card_key:
        key, n = turn.card_key, 0
    elif turn.intent == "call_help":
        key, n = "call_help", 0
    elif turn.intent == "next":
        n = step + 1
    elif turn.intent == "previous":
        n = step - 1
    key = key or "call_help"  # nothing selected yet: the safe default card
    body = coach.step_text(key, n, lang)
    reply = {
        "intent": turn.intent,
        "card_key": key,
        "step": body["step"],
        "of": body["of"],
        "ack": turn.ack,
        "text": "" if turn.intent == "done" else body["text"],
        "icon": body["icon"],
        "is_last": body["is_last"],
        "source": source,
        "disclaimer_key": "firstaid.disclaimer",
    }
    await activity.log(
        ctx,
        "coach",
        "decision" if source == "agent" else "rule",
        f"Coach turn: {turn.intent}"
        + (f" -> {key}" if turn.intent == "switch_card" else ""),
        data={"source": source},
    )
    return reply
