"""Optional Telegram channel. Used ONLY when TELEGRAM_ENABLED=true (off by default: Telegram is not
usable in Pakistan). Not exercised in the 3-hour demo; the web responder link is the demo channel.
"""

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.services import messages


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
async def send_alert(chat_id: int, lines: list[str], target_id: str) -> str:
    """Send one alert with a ✅ button (callback_data 'ack:<target_id>'); returns the message id."""
    async with Bot(settings.TELEGRAM_BOT_TOKEN) as bot:
        msg = await bot.send_message(
            chat_id,
            messages.telegram_html(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✅ Acknowledge", callback_data=f"ack:{target_id}"
                        )
                    ]
                ]
            ),
            read_timeout=10,
        )
    return str(msg.message_id)


@retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
async def send_text(chat_id: int, text: str) -> str:
    """Plain fixed-template text (family notice, F-41); HTML-escaped."""
    async with Bot(settings.TELEGRAM_BOT_TOKEN) as bot:
        msg = await bot.send_message(
            chat_id, messages.telegram_html([text]), parse_mode="HTML", read_timeout=10
        )
    return str(msg.message_id)
