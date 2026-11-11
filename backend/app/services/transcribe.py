"""Speech-to-text with Groq Whisper (docs/07_AI_AGENTS.md §8, TRD §8)."""

import logging

from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.models.ai import TranscriptResult

logger = logging.getLogger(__name__)

PROMPT = (
    "Emergency report. English, Spanish, Urdu, Roman Urdu, Punjabi or Pashto. Words: accident, "
    "haadsa, khoon, ambulance, 1122, dhamaka, firing, aag, tiroteo, disparos, 911."
)


@retry(stop=stop_after_attempt(2), wait=wait_fixed(1), reraise=True)
async def _call(audio_bytes: bytes, filename: str):
    client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=15)
    return await client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=(filename, audio_bytes),
        temperature=0,
        response_format="verbose_json",
        prompt=PROMPT,
    )


async def transcribe(audio_bytes: bytes, filename: str, mime: str) -> TranscriptResult:
    """Transcript text and detected language; empty text on failure (caller falls back to SOS)."""
    try:
        resp = await _call(audio_bytes, filename)
    except Exception as e:  # noqa: BLE001 - never block an alert on speech-to-text
        logger.warning("whisper failed: %s", type(e).__name__)
        return TranscriptResult(text="", language=None)
    return TranscriptResult(
        text=(resp.text or "").strip(), language=getattr(resp, "language", None)
    )
