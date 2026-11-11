import asyncio
from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse

from app.agents import orchestrator
from app.config import MAX_TEXT_CHARS
from app.deps import CurrentUser, get_current_user, get_supabase
from app.limiter import limiter, user_or_ip
from app.services import audit, crypto, first_aid, media
from app.services.transcribe import transcribe
from app.utils.errors import ApiError
from app.utils.geo import to_ewkt

router = APIRouter()

_TARGET_KIND = {
    "hospital": "hospital",
    "ambulance": "rescue",
    "police": "police",
    "fire": "fire",
}
_SERVICES = {
    "ambulance": "ambulance",
    "police": "police",
    "fire": "fire",
    "rescue": "ambulance",
}


def _service_state(service: str, targets: list[dict]) -> dict:
    """pending (no target yet) | alerted | acknowledged (>= 1 acknowledged), per docs/06 §2."""
    mine = [t for t in targets if t["recipient_kind"] == _TARGET_KIND[service]]
    acked = sorted(t["acknowledged_at"] for t in mine if t["status"] == "acknowledged")
    return {
        "service": service,
        "state": "acknowledged" if acked else "alerted" if mine else "pending",
        "acknowledged_at": acked[0] if acked else None,
        "count_alerted": len(mine),
        "count_acknowledged": len(acked),
    }


def _lang(lang: str | None) -> str:
    return lang if lang in ("en", "es", "ur") else "en"


def _first_aid_out(keys: list[str], lang: str) -> list[dict]:
    return [first_aid.get_card(k, lang) for k in keys]


@router.post("/reports", status_code=202)
@limiter.limit("5/minute", key_func=user_or_ip)
@limiter.limit("20/hour", key_func=user_or_ip)
@limiter.limit("30/minute")
async def create_report(
    request: Request,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    client_report_id: UUID = Form(...),
    input_type: Literal["sos", "voice", "photo", "text"] = Form(...),
    lat: float | None = Form(default=None, ge=-90, le=90),
    lng: float | None = Form(default=None, ge=-180, le=180),
    accuracy_m: float | None = Form(default=None, ge=0),
    location_hint: str | None = Form(default=None, max_length=200),
    text: str | None = Form(default=None, max_length=MAX_TEXT_CHARS),
    silent: bool = Form(default=False),
    lang: Literal["en", "es", "ur"] | None = Form(default=None),
    created_offline_at: datetime | None = Form(default=None),
    audio: UploadFile | None = File(default=None),
    photo: UploadFile | None = File(default=None),
):
    sb = get_supabase()
    if (lat is None) != (lng is None):
        raise ApiError(400, "VALIDATION_ERROR", "lat and lng must be given together")
    if input_type == "text" and not (text or "").strip():
        raise ApiError(400, "VALIDATION_ERROR", "text is required for text reports")

    existing = await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .select("id,status,first_aid_keys,lang")
            .eq("client_report_id", str(client_report_id))
            .eq("reporter_id", str(user.id))
            .execute()
            .data
        )
    )
    if existing:  # idempotent: never create a duplicate
        row = existing[0]
        keys = row["first_aid_keys"] or ["stay_safe", "call_help"]
        return JSONResponse(
            status_code=200,
            content={
                "report_id": row["id"],
                "status": row["status"],
                "first_aid": _first_aid_out(keys, _lang(row["lang"])),
            },
        )

    report_id = uuid4()
    audio_path = photo_path = None
    try:
        if input_type == "voice":
            if audio is None:
                raise ApiError(
                    400, "MEDIA_INVALID", "audio is required for voice reports"
                )
            data = await audio.read()
            ext, mime = media.check_audio(data)
            audio_path = f"{user.id}/{report_id}.{ext}"
            await media.upload(audio_path, data, mime)
        if photo is not None:
            pdata = media.reencode_photo(await photo.read())
            photo_path = f"{user.id}/{report_id}.jpg"
            await media.upload(photo_path, pdata, "image/jpeg")
        elif input_type == "photo":
            raise ApiError(400, "MEDIA_INVALID", "photo is required for photo reports")
    except media.MediaInvalid as e:
        raise ApiError(400, "MEDIA_INVALID", str(e)) from e

    row = {
        "id": str(report_id),
        "client_report_id": str(client_report_id),
        "reporter_id": str(user.id),
        "channel": "app",
        "input_type": input_type,
        "raw_text": (text or "").strip() or None,
        "audio_path": audio_path,
        "photo_path": photo_path,
        "location": to_ewkt(lat, lng) if lat is not None and lng is not None else None,
        "accuracy_m": accuracy_m,
        "location_hint": location_hint,
        "lang": lang,
        "silent": silent,
        "ip_hash": crypto.ip_hash(request.client.host if request.client else "unknown"),
        "status": "received",
    }
    await asyncio.to_thread(lambda: sb.table("reports").insert(row).execute())
    await audit.log(
        "reporter",
        "report_created",
        "report",
        str(report_id),
        actor_id=str(user.id),
        details={"input_type": input_type, "silent": silent},
    )
    background.add_task(orchestrator.handle_report, report_id)
    return {
        "report_id": str(report_id),
        "status": "received",
        "first_aid": first_aid.generic_cards(_lang(lang)),
    }


@router.get("/reports/{report_id}/status")
@limiter.limit("60/minute")
async def report_status(
    request: Request, report_id: UUID, user: CurrentUser = Depends(get_current_user)
) -> dict:
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .select("*")
            .eq("id", str(report_id))
            .eq("reporter_id", str(user.id))
            .execute()
            .data
        )
    )
    if not rows:
        raise ApiError(404, "NOT_FOUND", "Report not found")
    r = rows[0]
    lang = _lang(r["lang"])
    ext = r.get("extraction") or {}
    incident = None
    if r.get("incident_id"):
        inc = await asyncio.to_thread(
            lambda: (
                sb.table("incidents")
                .select(
                    "short_code,incident_type,severity,status,silent,needs,landmark_text,landmark_local"
                )
                .eq("id", r["incident_id"])
                .execute()
                .data
            )
        )
        incident = inc[0] if inc else None
    needs = incident["needs"] if incident else ext.get("needs", [])
    wanted = list(dict.fromkeys(_SERVICES[n] for n in needs if n in _SERVICES))
    if "ambulance" in wanted:
        wanted.insert(0, "hospital")
    targets = []
    if incident:
        targets = await asyncio.to_thread(
            lambda: (
                sb.table("alert_targets")
                .select("recipient_kind,status,acknowledged_at")
                .eq("incident_id", r["incident_id"])
                .execute()
                .data
            )
        )
    services = [_service_state(name, targets) for name in wanted]
    keys = r["first_aid_keys"] or ["stay_safe", "call_help"]
    return {
        "report_id": r["id"],
        "report_status": r["status"],
        "transcript": r.get("transcript"),
        "incident": incident,
        "services": services,
        "followup_question": r.get("followup_question"),
        "followup_answered": bool(r.get("followup_answer")),
        "first_aid": _first_aid_out(keys, lang),
    }


@router.post("/reports/{report_id}/answer", status_code=202)
@limiter.limit("5/minute", key_func=user_or_ip)
async def answer_followup(
    request: Request,
    report_id: UUID,
    background: BackgroundTasks,
    user: CurrentUser = Depends(get_current_user),
    text: str | None = Form(default=None, max_length=500),
    audio: UploadFile | None = File(default=None),
) -> dict:
    """F-25: the reporter answers the one follow-up question; Intake re-runs on the combined text."""
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .select("id,followup_question,followup_answer,status")
            .eq("id", str(report_id))
            .eq("reporter_id", str(user.id))
            .execute()
            .data
        )
    )
    if not rows:
        raise ApiError(404, "NOT_FOUND", "Report not found")
    r = rows[0]
    if r["followup_answer"]:
        raise ApiError(409, "ALREADY_DONE", "Already answered")
    if not r["followup_question"]:
        raise ApiError(400, "VALIDATION_ERROR", "This report has no follow-up question")
    answer = (text or "").strip()
    if not answer and audio is not None:
        try:
            data = await audio.read()
            ext, _ = media.check_audio(data)
            answer = (await transcribe(data, f"answer.{ext}", "audio")).text.strip()
        except media.MediaInvalid as e:
            raise ApiError(400, "MEDIA_INVALID", str(e)) from e
    if not answer:
        raise ApiError(400, "VALIDATION_ERROR", "text or audio is required")
    answer = answer[:500]
    await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .update({"followup_answer": answer, "status": "received"})
            .eq("id", str(report_id))
            .execute()
        )
    )
    await audit.log(
        "reporter", "followup_answered", "report", str(report_id), actor_id=str(user.id)
    )
    background.add_task(orchestrator.handle_report, report_id)
    return {"report_id": str(report_id), "status": "processing"}
