"""Family notice (F-41): when a card scan creates/joins an incident, tell the card's family contacts with a
fixed template. Telegram only when enabled and linked (`card_contacts.telegram_chat_id`); everyone else is
listed for the dispatcher as "call manually". No LLM and no card data leaves this module except the owner's
first name, place and hospital in the fixed message (AGENTS.md Rule 2)."""

import asyncio
import logging
from uuid import UUID

from app.agents.context import AgentCtx
from app.config import settings
from app.deps import get_supabase
from app.services import activity, audit, crypto, events, messages

logger = logging.getLogger(__name__)


async def _db(fn):
    return await asyncio.to_thread(fn)


async def _claim_card(incident_id: UUID | str, card_id: str) -> bool:
    """Idempotency: only the first card scan of an incident sets incidents.card_id (and notifies)."""
    sb = get_supabase()
    res = await _db(
        lambda: (
            sb.table("incidents")
            .update({"card_id": card_id})
            .eq("id", str(incident_id))
            .is_("card_id", "null")
            .execute()
        )
    )
    return bool(res.data)


async def _hospital_name(incident_id: UUID | str) -> str | None:
    sb = get_supabase()
    rows = await _db(
        lambda: (
            sb.table("hospital_assignments")
            .select("organizations:hospital_id(name)")
            .eq("incident_id", str(incident_id))
            .gt("assigned_casualties", 0)
            .order("eta_minutes")
            .limit(1)
            .execute()
            .data
        )
    )
    return rows[0]["organizations"]["name"] if rows else None


async def _one(table: str, column: str, value: str) -> dict:
    sb = get_supabase()
    rows = await _db(
        lambda: sb.table(table).select("*").eq(column, value).execute().data
    )
    return rows[0]


async def notify_card_family(
    incident_id: UUID | str, card_id: str, ctx: AgentCtx | None = None
) -> int:
    """Returns how many contacts were messaged. Never raises: it must not disturb the alert path."""
    try:
        if not await _claim_card(incident_id, card_id):
            return 0
        sb = get_supabase()
        card = await _one("emergency_cards", "id", card_id)
        contacts = await _db(
            lambda: (
                sb.table("card_contacts")
                .select("*")
                .eq("card_id", card_id)
                .execute()
                .data
            )
        )
        inc = await _one("incidents", "id", str(incident_id))
        lang = card["lang"]
        place = (
            (inc.get("landmark_local") if lang == "ur" else inc.get("landmark_text"))
            or inc.get("location_label")
            or "?"
        )
        text = messages.family_notice(
            card["full_name"].split()[0],
            place,
            inc["short_code"],
            await _hospital_name(incident_id),
            lang,
        )
        sent = 0
        if settings.TELEGRAM_ENABLED:
            from app.services import (
                notify_telegram,  # optional channel, imported only when enabled
            )

            for c in contacts:
                if c.get("telegram_chat_id"):
                    try:
                        await notify_telegram.send_text(c["telegram_chat_id"], text)
                        sent += 1
                    except Exception:  # noqa: BLE001 - one failed contact must not stop the others
                        logger.warning("family notice failed contact=%s", c["id"])
        manual = len(contacts) - sent
        await events.add(
            incident_id,
            "update_sent",
            f"Family notice: {sent} contact(s) messaged, {manual} to call manually",
        )
        await audit.log("system", "family_notified", "incident", str(incident_id))
        await activity.log(
            ctx,
            "dispatch",
            "rule",
            f"Family notice for card scan: {sent} messaged, {manual} to call manually",
        )
        return sent
    except Exception:
        logger.exception("family notice failed incident=%s", incident_id)
        return 0


async def manual_contacts(incident_id: UUID | str) -> dict:
    """For the dispatcher: contacts to call by hand. A phone is shown only for contact #1 when the owner
    ticked show_phone (S-19); everyone else appears by name and relation."""
    sb = get_supabase()
    inc = await _one("incidents", "id", str(incident_id))
    if not inc.get("card_id"):
        return {"card_scanned": False, "call_manually": []}
    card = await _one("emergency_cards", "id", inc["card_id"])
    contacts = await _db(
        lambda: (
            sb.table("card_contacts")
            .select("*")
            .eq("card_id", inc["card_id"])
            .order("position")
            .execute()
            .data
        )
    )
    out = []
    for c in contacts:
        if c.get("telegram_chat_id") and settings.TELEGRAM_ENABLED:
            continue
        item = {"name": c["name"], "relation": c["relation"]}
        if c["position"] == 1 and card["show_phone"]:
            item["phone"] = crypto.decrypt_phone(c["phone_enc"])
        out.append(item)
    return {
        "card_scanned": True,
        "owner_first_name": card["full_name"].split()[0],
        "call_manually": out,
    }
