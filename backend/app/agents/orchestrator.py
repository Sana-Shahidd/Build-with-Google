"""Deterministic orchestrator (code, not an LLM). docs/03_TRD.md §6, docs/07_AI_AGENTS.md §4.

T-05 scope: transcribe -> intake (SOS default | agent | rules autopilot) -> needs rules -> save.
T-06 adds verification (rule fast-path / autopilot) and triage (spreading autopilot).
T-07 adds dispatch (alerts to the web responder link). Hospital prep is T-20.
"""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from app.agents import intake, landmark, triage, verification
from app.agents.context import AgentCtx
from app.agents.runner import run_agent
from app.deps import get_supabase
from app.models.ai import IncidentExtraction
from app.services import (
    activity,
    audit,
    country,
    dispatch,
    events,
    family,
    first_aid,
    matching,
    media,
    merge,
    needs,
    rules_classifier,
)
from app.services.transcribe import transcribe

logger = logging.getLogger(__name__)
# Gemini free-tier latency varies a lot: cap each attempt and the TOTAL so the keyword autopilot
# takes over well inside the 60 s promise.
INTAKE_TIMEOUT_S = 12
INTAKE_BUDGET_S = 20


async def _db(fn):
    return await asyncio.to_thread(fn)


async def _load(report_id: UUID) -> dict:
    sb = get_supabase()
    rows = await _db(
        lambda: sb.table("reports").select("*").eq("id", str(report_id)).execute().data
    )
    return rows[0]


async def _update(report_id: UUID, patch: dict) -> None:
    sb = get_supabase()
    await _db(
        lambda: sb.table("reports").update(patch).eq("id", str(report_id)).execute()
    )


def _with_answer(text: str, report: dict) -> str:
    """F-25: the reporter's answer to the follow-up question is read together with the first text."""
    answer = (report.get("followup_answer") or "").strip()
    if not answer:
        return text
    return f"{text}\nFollow-up answer: {answer}".strip()


async def _transcript(report: dict, ctx: AgentCtx) -> tuple[str, str | None]:
    """Whisper for voice reports; typed text otherwise. Returns (text, language)."""
    if report["input_type"] != "voice" or not report.get("audio_path"):
        return _with_answer((report.get("raw_text") or "").strip(), report), None
    data = await media.download(report["audio_path"])
    name = report["audio_path"].rsplit("/", 1)[-1]
    result = await transcribe(data, name, "audio")
    await activity.log(
        ctx,
        "intake",
        "rule",
        "Transcribed voice report"
        if result.text
        else "Transcription empty: using SOS default",
        data={"language": result.language},
    )
    return _with_answer(result.text, report), result.language


async def _extract(
    report: dict, text: str, ctx: AgentCtx
) -> tuple[IncidentExtraction, str]:
    """(extraction, ai_provider). A report must never fail to produce an extraction."""
    lang = report.get("lang")
    if not text and not report.get("photo_path"):
        empty_voice = report["input_type"] == "voice"
        await activity.log(ctx, "intake", "rule", "Bare SOS: fixed default extraction")
        return rules_classifier.sos_default(
            lang, report["silent"], empty_voice
        ), "sos_default"

    photo = None
    if report.get("photo_path"):
        photo = await media.download(report["photo_path"])
    profile = country.get_profile(report.get("country_code"))
    agent_input = intake.build_input(
        text or "(photo only)", report["lat"], report["lng"], profile["name"], photo
    )
    out = await run_agent(
        "intake",
        intake.make_agent,
        agent_input,
        ctx,
        timeout_s=INTAKE_TIMEOUT_S,
        total_budget_s=INTAKE_BUDGET_S,
        max_turns=2,
    )
    if isinstance(out, IncidentExtraction):
        provider = (ctx.model_used or "gemini:").split(":", 1)[0]
        return out, provider
    await activity.log(ctx, "intake", "rule", "Autopilot: keyword classifier used")
    return rules_classifier.classify(text), "rules"


async def _verify_and_triage(
    report_id: UUID, extraction: IncidentExtraction, ctx: AgentCtx
) -> None:
    """Verification autopilot (merge/create + confidence) then triage autopilot (spreading)."""
    report = await _load(report_id)
    rerun = (
        report.get("incident_id") is not None
    )  # F-25 follow-up answer: stay in the same incident
    ctx.candidates = (
        []
        if rerun
        else await merge.find_candidates(
            report["lat"], report["lng"], merge.window_start()
        )
    )
    incident_id = (
        UUID(report["incident_id"])
        if rerun
        else merge.fast_path(ctx.candidates, extraction)
    )
    how = "follow-up answer" if rerun else "rule fast-path"
    if rerun:
        pass
    elif incident_id is None and ctx.candidates:
        agent_answer = await verification.decide(ctx, extraction)  # T-15
        if agent_answer is False:  # no usable agent answer: autopilot rule
            incident_id = merge.autopilot_decision(ctx.candidates, extraction)
            how = "autopilot rule"
        else:
            incident_id, how = agent_answer, "verification agent"
    elif incident_id is None:
        how = "no nearby incident"
    if rerun:
        iid, created = incident_id, False
    else:
        iid, created = await merge.attach_or_create(report, extraction, incident_id)
    if (
        created and report.get("lat") is not None
    ):  # runs beside the alert path, never blocks it
        landmark.schedule_landmark(
            iid, report["lat"], report["lng"], _local_lang(report), None
        )
    ctx.incident_id = iid
    # earlier feed rows of this report (intake, landmark...) were logged before the incident existed
    sb = get_supabase()
    await _db(
        lambda: (
            sb.table("agent_activity")
            .update({"incident_id": str(iid)})
            .eq("report_id", str(report_id))
            .is_("incident_id", "null")
            .execute()
        )
    )
    change = await merge.recompute_incident(iid)
    await activity.log(
        ctx,
        "verification",
        "rule",
        f"{'Created' if created else 'Merged into'} {change.short_code} ({how}); "
        f"status {change.new_status}, confidence {change.confidence:.2f}, "
        f"{change.unique_reporters} reporter(s)",
        data={"incident": change.short_code, "status": change.new_status},
    )
    if change.significant:
        await _triage(iid, ctx)
    # idempotent: only creates targets that are missing, so it is safe after every report
    await dispatch.dispatch_if_needed(iid, change, ctx)
    if report.get(
        "card_id"
    ):  # F-41: fixed-template notice to the card family (never raises)
        await family.notify_card_family(iid, report["card_id"], ctx)


async def _triage(incident_id: UUID, ctx: AgentCtx) -> None:
    """Triage autopilot: choose hospitals and spread casualties; the plan is validated by code."""
    sb = get_supabase()
    rows = await _db(
        lambda: (
            sb.table("incidents").select("*").eq("id", str(incident_id)).execute().data
        )
    )
    incident = rows[0]
    if incident["lat"] is None or "ambulance" not in incident["needs"]:
        return
    opts = await matching.hospital_options(incident)
    ctx.hospital_options = opts
    ctx.incident_id = incident_id
    ctx.accepted_plan = []
    if (
        opts.hospitals and opts.total and await triage.plan(ctx)
    ):  # T-16: agent proposes, code validates
        await events.add(
            incident_id,
            "assignment",
            f"Triage Agent spread casualties over {len(ctx.accepted_plan)} hospital(s)",
        )
        return
    plan = matching.spread(opts)
    errors = matching.validate_plan(plan, opts)
    if errors:
        await activity.log(
            ctx, "triage", "guardrail_block", f"Plan rejected: {errors[0]}"[:200]
        )
        return
    await matching.save_plan(incident_id, plan, "autopilot")
    ctx.accepted_plan = plan
    await events.add(
        incident_id, "assignment", f"Casualties spread over {len(plan)} hospital(s)"
    )
    await activity.log(
        ctx,
        "triage",
        "rule",
        f"Autopilot spread {opts.total} casualties ({opts.critical_total} critical) over {len(plan)} hospital(s)",
        data={
            "hospitals": len(plan),
            "over_capacity": any(a.over_capacity for a in plan),
        },
    )


def _local_lang(report: dict) -> str:
    """Language for landmark lines: the reporter UI language, else the country profile default."""
    lang = report.get("lang")
    return (
        lang
        if lang in ("en", "es", "ur")
        else country.get_profile(report.get("country_code") or None)["default_lang"]
    )


async def handle_report(report_id: UUID) -> None:
    ctx = AgentCtx(report_id=report_id)
    try:
        report = await _load(report_id)
        ctx.lang = report.get("lang") or "en"
        await _update(report_id, {"status": "processing"})
        if report.get("lat") is not None and not report.get("country_code"):
            code, _ = await country.detect(report["lat"], report["lng"])
            report["country_code"] = country.profile_code(code) if code else None
            await _update(report_id, {"country_code": code})

        text, whisper_lang = await _transcript(report, ctx)
        if text and report["input_type"] == "voice":
            await _update(
                report_id, {"transcript": text, "transcript_lang": whisper_lang}
            )

        raw, provider = await _extract(report, text, ctx)
        extraction = needs.apply_rules(raw)
        ctx.extraction = extraction
        cards = first_aid.select_keys(
            extraction.incident_type.value, [i.value for i in extraction.injury_types]
        )
        await _update(
            report_id,
            {
                "extraction": extraction.model_dump(mode="json"),
                "ai_provider": provider,
                "ai_confidence": extraction.confidence,
                "followup_question": extraction.followup_question,
                "first_aid_keys": cards,
                "status": "processed",
                "processed_at": datetime.now(UTC).isoformat(),
            },
        )
        await activity.log(
            ctx,
            "intake",
            "decision",
            f"{extraction.incident_type.value} / {extraction.severity.value}: {extraction.rationale}",
            model=ctx.model_used,
            data={"provider": provider, "needs": [n.value for n in extraction.needs]},
        )
        await _verify_and_triage(report_id, extraction, ctx)
    except Exception as e:
        logger.exception("handle_report failed report_id=%s", report_id)
        await _update(report_id, {"status": "failed", "error": type(e).__name__})
        await activity.log(
            ctx,
            "orchestrator",
            "error",
            f"Report processing failed: {type(e).__name__}",
        )
        await audit.log("system", "report_failed", "report", str(report_id))
