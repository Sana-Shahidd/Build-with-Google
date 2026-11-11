"""Emergency Card service (F-36). Health-adjacent data: only the fields in 05_DATABASE_SCHEMA.md,
phones encrypted at rest, nothing here is ever sent to an LLM (AGENTS.md Rule 2)."""

import asyncio
import secrets
from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.config import CARD_MAX_CONTACTS, CARD_TOKEN_BYTES
from app.deps import get_supabase
from app.models.enums import BloodType
from app.services import country, crypto

CARD_LABEL = {"en": "Card", "es": "Tarjeta", "ur": "کارڈ"}
BLOOD_LABEL = {"en": "blood", "es": "sangre", "ur": "خون کا گروپ"}
ALLERGY_LABEL = {"en": "allergy", "es": "alergia", "ur": "الرجی"}


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    relation: str | None = Field(default=None, max_length=30)
    phone: str = Field(min_length=5, max_length=25)


class CardCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=80)
    blood_type: BloodType | None = None
    allergies: str | None = Field(default=None, max_length=120)
    contacts: list[ContactIn] = Field(min_length=1, max_length=CARD_MAX_CONTACTS)
    lang: str = Field(default="ur", pattern="^(en|es|ur)$")
    show_phone: bool = False
    consent: bool


def new_token() -> str:
    return secrets.token_urlsafe(CARD_TOKEN_BYTES)


async def create_card(user_id: UUID, data: CardCreate, region: str | None) -> dict:
    """Validate phones (E.164), encrypt them, store card + contacts. Raises ValueError on a bad phone."""
    contacts = []
    for i, c in enumerate(data.contacts, start=1):
        e164 = crypto.to_e164(c.phone, region)
        contacts.append(
            {
                "position": i,
                "name": c.name,
                "relation": c.relation,
                "phone_enc": crypto.encrypt_phone(e164),
                "phone_hash": crypto.phone_hash(e164),
            }
        )
    sb = get_supabase()
    card = (
        await asyncio.to_thread(
            lambda: (
                sb.table("emergency_cards")
                .insert(
                    {
                        "owner_user_id": str(user_id),
                        "token": new_token(),
                        "full_name": data.full_name,
                        "blood_type": data.blood_type.value
                        if data.blood_type
                        else None,
                        "allergies": data.allergies or None,
                        "lang": data.lang,
                        "show_phone": data.show_phone,
                        "consent_at": datetime.now(UTC).isoformat(),
                    }
                )
                .execute()
            )
        )
    ).data[0]
    await asyncio.to_thread(
        lambda: (
            sb.table("card_contacts")
            .insert([{**c, "card_id": card["id"]} for c in contacts])
            .execute()
        )
    )
    return card


def card_line(card: dict, lang: str) -> str:
    """Fixed template for the hospital brief, e.g. 'Card: blood O+, allergy: penicillin'. No phones, no name."""
    parts = []
    if card.get("blood_type"):
        parts.append(f"{BLOOD_LABEL.get(lang, BLOOD_LABEL['en'])} {card['blood_type']}")
    if card.get("allergies"):
        parts.append(
            f"{ALLERGY_LABEL.get(lang, ALLERGY_LABEL['en'])}: {card['allergies']}"
        )
    if not parts:
        return ""
    return f"🪪 {CARD_LABEL.get(lang, CARD_LABEL['en'])}: " + (
        "، " if lang == "ur" else ", "
    ).join(parts)


async def public_view(token: str, ip_hash: str) -> dict | None:
    """What a stranger sees after scanning. Logs the scan; phone only for contact #1 when consented."""
    sb = get_supabase()
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("emergency_cards")
            .select("*")
            .eq("token", token)
            .eq("active", True)
            .execute()
            .data
        )
    )
    if not rows:
        return None
    card = rows[0]
    contacts = await asyncio.to_thread(
        lambda: (
            sb.table("card_contacts")
            .select("position,name,relation,phone_enc")
            .eq("card_id", card["id"])
            .order("position")
            .execute()
            .data
        )
    )
    await asyncio.to_thread(
        lambda: (
            sb.table("card_scans")
            .insert({"card_id": card["id"], "ip_hash": ip_hash})
            .execute()
        )
    )
    await asyncio.to_thread(
        lambda: (
            sb.table("emergency_cards")
            .update(
                {
                    "scan_count": card["scan_count"] + 1,
                    "last_scanned_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", card["id"])
            .execute()
        )
    )
    out_contacts = []
    for c in contacts:
        item = {"name": c["name"], "relation": c["relation"]}
        if c["position"] == 1 and card["show_phone"]:
            item["phone"] = crypto.decrypt_phone(c["phone_enc"])
        out_contacts.append(item)
    profile = country.get_profile(country.fallback_code())
    return {
        "card_id": card["id"],
        "full_name": card["full_name"],
        "blood_type": card["blood_type"],
        "allergies": card["allergies"],
        "lang": card["lang"],
        "contacts": out_contacts,
        "emergency_numbers": profile["emergency_numbers"],
    }


async def card_for_incident(incident_id: str) -> dict | None:
    """The Emergency Card (blood group / allergy only) behind a report of this incident, if any."""
    sb = get_supabase()
    reports = await asyncio.to_thread(
        lambda: (
            sb.table("reports")
            .select("card_id")
            .eq("incident_id", incident_id)
            .not_.is_("card_id", "null")
            .limit(1)
            .execute()
            .data
        )
    )
    if not reports:
        return None
    rows = await asyncio.to_thread(
        lambda: (
            sb.table("emergency_cards")
            .select("blood_type,allergies")
            .eq("id", reports[0]["card_id"])
            .execute()
            .data
        )
    )
    return rows[0] if rows else None
