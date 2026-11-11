"""Fixed message templates (docs/07_AI_AGENTS.md §11). Never written by an LLM.

Each builder returns plain-text LINES. The web responder inbox shows them as-is; the (optional)
Telegram channel HTML-escapes them. Variables come from incident rows, never from agent text.
"""

import html

from app.services import labels

MAP_URL = "https://maps.google.com/?q={lat},{lng}"


def map_url(incident: dict) -> str | None:
    if incident.get("lat") is None:
        return None
    return MAP_URL.format(lat=incident["lat"], lng=incident["lng"])


def _injuries(incident: dict, lang: str) -> str:
    items = incident.get("injury_types") or []
    return ", ".join(labels.label(labels.INJURY, i, lang) for i in items) or "-"


def _landmark(incident: dict, lang: str) -> str | None:
    if lang == "ur" and incident.get("landmark_local"):
        return incident["landmark_local"]
    return incident.get("landmark_text") or incident.get("landmark_local")


def _common_tail(incident: dict, lang: str) -> list[str]:
    lines = []
    if incident.get("ongoing_danger"):
        lines.append(labels.phrase("danger", lang))
    if incident.get("silent"):
        lines.append(labels.phrase("silent", lang))
    return lines


def org_alert(incident: dict, lang: str) -> list[str]:
    """Police / EMS / fire alert (Telegram org-alert template)."""
    kind = labels.label(labels.INCIDENT_TYPE, incident["incident_type"], lang)
    sev = labels.label(labels.SEVERITY, incident["severity"], lang)
    lines = []
    if incident["status"] != "verified":
        pct = round(float(incident.get("confidence") or 0) * 100)
        lines.append(
            labels.phrase(
                "unverified", lang, n=incident.get("report_count", 1), pct=pct
            )
        )
    lines.append(f"🚨 {sev} – {kind}  {incident['short_code']}")
    lines.append(f"📍 {incident.get('location_label') or '-'}")
    if lm := _landmark(incident, lang):
        lines.append(f"🧭 {lm}")
    lines.append(
        f"👥 {labels.phrase('casualties', lang)}: {incident['est_casualties_min']}–"
        f"{incident['est_casualties_max']} · {labels.phrase('injuries', lang)}: "
        f"{_injuries(incident, lang)}"
    )
    if incident.get("summary_en"):
        lines.append(f"📝 {incident['summary_en']}")
    if incident.get("local_lang") not in (None, "en") and incident.get("summary_local"):
        lines.append(f"🌐 {incident['summary_local']}")
    lines += _common_tail(incident, lang)
    lines.append(labels.phrase("press_ack", lang))
    return lines


def hospital_brief(
    incident: dict,
    assignment: dict | None,
    lang: str,
    standby: bool,
    card_line: str | None = None,
) -> list[str]:
    """Hospital pre-arrival brief, or the STANDBY version for unverified incidents."""
    kind = labels.label(labels.INCIDENT_TYPE, incident["incident_type"], lang)
    sev = labels.label(labels.SEVERITY, incident["severity"], lang)
    code = incident["short_code"]
    head = labels.phrase("standby" if standby else "pre_arrival", lang)
    lines = [f"{'🟡' if standby else '🏥'} {head} – {code}"]
    lines.append(
        f"{kind} {labels.phrase('at', lang)} {incident.get('location_label') or '-'} ({sev})"
    )
    if lm := _landmark(incident, lang):
        lines.append(f"🧭 {lm}")
    if assignment:
        total, crit = assignment["assigned_casualties"], assignment["critical"]
        lines.append(
            "➡ " + labels.phrase("expect", lang, n=total, c=crit, m=total - crit)
        )
    lines.append(f"🩸 {labels.phrase('likely', lang)}: {_injuries(incident, lang)}")
    if card_line:
        lines.append(card_line)
    if assignment and assignment.get("eta_minutes") is not None:
        lines.append(
            "🚑 " + labels.phrase("eta", lang, n=round(assignment["eta_minutes"]))
        )
    lines += _common_tail(incident, lang)
    lines.append(
        labels.phrase("standby_note", lang)
        if standby
        else labels.phrase("press_ack_er", lang)
    )
    return lines


def all_languages(builder, *args, **kwargs) -> dict[str, list[str]]:
    """Render one template in every supported language: {'en': [...], 'es': [...], 'ur': [...]}."""
    return {lang: builder(*args, lang=lang, **kwargs) for lang in labels.LANGS}


def telegram_html(lines: list[str]) -> str:
    """Escaped Telegram HTML (used only when TELEGRAM_ENABLED)."""
    escaped = [html.escape(line) for line in lines]
    if escaped:
        escaped[0] = f"<b>{escaped[0]}</b>"
    return "\n".join(escaped)


FAMILY_NOTICE = {
    "en": "🪪 {owner}'s Emergency Card was scanned near {place}. Help has been alerted ({code}).",
    "es": "🪪 Se escaneó la Tarjeta de Emergencia de {owner} cerca de {place}. Ya se avisó a los servicios ({code}).",
    "ur": "🪪 {owner} کا ایمرجنسی کارڈ {place} کے قریب اسکین ہوا ہے۔ مدد کو اطلاع دے دی گئی ہے ({code})۔",
}
FAMILY_HOSPITAL = {
    "en": " Hospital: {hospital}.",
    "es": " Hospital: {hospital}.",
    "ur": " ہسپتال: {hospital}۔",
}


def family_notice(
    owner: str, place: str, code: str, hospital: str | None, lang: str
) -> str:
    """F-41 fixed template (docs/07 section 11). The hospital part is omitted until Triage has a plan."""
    lang = lang if lang in FAMILY_NOTICE else "en"
    text = FAMILY_NOTICE[lang].format(owner=owner, place=place, code=code)
    if hospital:
        text += FAMILY_HOSPITAL[lang].format(hospital=hospital)
    return text
