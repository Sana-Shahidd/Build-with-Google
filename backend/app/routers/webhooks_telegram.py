"""Telegram webhook (only registered when TELEGRAM_ENABLED). Handles the ✅ button callback."""

import hmac

from fastapi import APIRouter, Request
from telegram import Update

from app.config import settings
from app.services import ack_tokens
from app.utils.errors import ApiError

router = APIRouter()


@router.post("/webhooks/telegram")
async def telegram_webhook(request: Request) -> dict:
    secret = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not settings.TELEGRAM_WEBHOOK_SECRET or not hmac.compare_digest(
        secret, settings.TELEGRAM_WEBHOOK_SECRET
    ):
        raise ApiError(403, "FORBIDDEN", "Bad webhook secret")
    update = Update.de_json(await request.json(), None)
    query = update.callback_query if update else None
    if query and query.data and query.data.startswith("ack:"):
        await ack_tokens.acknowledge(
            query.data[4:], via="telegram", actor=f"chat:{query.message.chat_id}"
        )
    return {"ok": True}
