"""Upload validation and storage (docs/08_SECURITY.md S-08). Magic bytes + Pillow, never trust mime."""

import asyncio
import io

from PIL import Image, UnidentifiedImageError

from app.config import MAX_AUDIO_BYTES, MAX_PHOTO_BYTES
from app.deps import get_supabase

BUCKET = "report-media"


class MediaInvalid(ValueError):
    pass


def audio_kind(data: bytes) -> tuple[str, str]:
    """(extension, mime) from the first bytes; raises MediaInvalid."""
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "webm", "audio/webm"
    if data[:4] == b"OggS":
        return "ogg", "audio/ogg"
    if data[4:8] == b"ftyp":
        return "mp4", "audio/mp4"
    if data[:4] == b"RIFF":
        return "wav", "audio/wav"
    if data[:3] == b"ID3" or (
        len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0
    ):
        return "mp3", "audio/mpeg"
    raise MediaInvalid("unsupported audio format")


def check_audio(data: bytes) -> tuple[str, str]:
    if not data or len(data) > MAX_AUDIO_BYTES:
        raise MediaInvalid("audio empty or larger than 10 MB")
    return audio_kind(data)


def reencode_photo(data: bytes) -> bytes:
    """Verify with Pillow and re-encode as JPEG q85, max 1600 px (strips EXIF/GPS)."""
    if not data or len(data) > MAX_PHOTO_BYTES:
        raise MediaInvalid("photo empty or larger than 8 MB")
    try:
        Image.open(io.BytesIO(data)).verify()
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except (UnidentifiedImageError, OSError) as e:
        raise MediaInvalid("not a valid image") from e
    img.thumbnail((1600, 1600))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return out.getvalue()


async def upload(path: str, data: bytes, mime: str) -> None:
    await asyncio.to_thread(
        lambda: (
            get_supabase()
            .storage.from_(BUCKET)
            .upload(path, data, {"content-type": mime})
        )
    )


async def download(path: str) -> bytes:
    return await asyncio.to_thread(
        lambda: get_supabase().storage.from_(BUCKET).download(path)
    )
