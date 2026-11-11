"""Register the Telegram webhook at PUBLIC_BASE_URL (only needed when TELEGRAM_ENABLED=true)."""

import asyncio

from telegram import Bot

from app.config import settings


async def main() -> None:
    if not (
        settings.TELEGRAM_ENABLED
        and settings.TELEGRAM_BOT_TOKEN
        and settings.PUBLIC_BASE_URL
    ):
        raise SystemExit(
            "Telegram is disabled (TELEGRAM_ENABLED=false) or token/PUBLIC_BASE_URL missing."
        )
    async with Bot(settings.TELEGRAM_BOT_TOKEN) as bot:
        await bot.set_webhook(
            f"{settings.PUBLIC_BASE_URL}/webhooks/telegram",
            secret_token=settings.TELEGRAM_WEBHOOK_SECRET,
        )
    print("Webhook set.")


if __name__ == "__main__":
    asyncio.run(main())
