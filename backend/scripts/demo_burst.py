"""Send the `highway_crash` demo scenario (docs/12_TESTING_AND_DEMO.md section 3) to the running backend.

Usage: python -m scripts.demo_burst --scenario highway_crash [--fast]
Each report comes from its own anonymous session (so unique_reporters grows), a few metres apart:
  t=0    Urdu VOICE report (gTTS-generated clip, so no microphone is needed)
  +15 s  Roman Urdu text
  +30 s  English text
  +45 s  helmet-card scan -> "Get help" (creates the demo card for Ahmad, O+, penicillin)
Then prints the incident progress and the links to open. Needs the backend on --api (default :8000).
"""

import argparse
import io
import random
import sys
import time
import uuid
from pathlib import Path

import httpx

from app.config import settings

CRASH = (31.5036, 74.3305)  # Ferozepur Road near Kalma Chowk
FRONTEND_ENV = Path(__file__).resolve().parents[2] / "frontend" / ".env"

URDU = "فیروز پور روڈ پر بس اور موٹر سائیکلوں کا حادثہ ہوا ہے، کئی لوگ زخمی ہیں"
ROMAN = "ferozepur road pe bohat bara hadsa hua hai, bohat khoon beh raha hai"
ENGLISH = "Bus and two motorbikes crashed near Kalma Chowk, about 10 people hurt, one not moving"


def anon_key() -> str:
    for line in FRONTEND_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("VITE_SUPABASE_ANON_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("VITE_SUPABASE_ANON_KEY missing in frontend/.env")


def new_session() -> dict[str, str]:
    r = httpx.post(
        f"{settings.SUPABASE_URL}/auth/v1/signup",
        headers={"apikey": anon_key(), "Content-Type": "application/json"},
        json={},
        timeout=20,
    )
    r.raise_for_status()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def jitter() -> dict[str, str]:
    """A spot 20-150 m from the crash site."""
    metres = random.uniform(20, 150)
    dlat = metres / 111_000 * random.choice([-1, 1])
    dlng = metres / 111_000 * random.choice([-1, 1]) * 0.7
    return {
        "lat": f"{CRASH[0] + dlat:.6f}",
        "lng": f"{CRASH[1] + dlng:.6f}",
        "accuracy_m": "20",
    }


def post_report(
    api: str,
    headers: dict,
    input_type: str,
    lang: str,
    text: str | None = None,
    audio: bytes | None = None,
) -> str:
    data = {
        "client_report_id": str(uuid.uuid4()),
        "input_type": input_type,
        "lang": lang,
        **jitter(),
    }
    if text:
        data["text"] = text
    files = {"audio": ("report.mp3", audio, "audio/mpeg")} if audio else None
    r = httpx.post(
        f"{api}/api/v1/reports", headers=headers, data=data, files=files, timeout=60
    )
    r.raise_for_status()
    return r.json()["report_id"]


def urdu_voice() -> bytes:
    from gtts import gTTS

    buf = io.BytesIO()
    gTTS(URDU, lang="ur").write_to_fp(buf)
    return buf.getvalue()


def make_card(api: str, headers: dict) -> dict:
    r = httpx.post(
        f"{api}/api/v1/cards",
        headers=headers,
        timeout=30,
        json={
            "full_name": "Ahmad",
            "blood_type": "O+",
            "allergies": "penicillin",
            "contacts": [
                {"name": "Bhai", "relation": "brother", "phone": "0300 1234567"}
            ],
            "lang": "ur",
            "show_phone": True,
            "consent": True,
        },
    )
    r.raise_for_status()
    return r.json()


def wait_for(seconds: float, label: str) -> None:
    print(f"   ... {label} in {seconds:.0f} s")
    time.sleep(seconds)


def main(api: str, fast: bool) -> int:
    gap = 3 if fast else 15
    print("Golden Minute demo burst: highway_crash")
    owner = new_session()
    card = make_card(api, owner)
    print(f"[card] Ahmad's helmet card: {card['scan_url']}")

    print("[t=0] Urdu voice report")
    first = post_report(api, new_session(), "voice", "ur", audio=urdu_voice())
    wait_for(gap, "Roman Urdu text")
    print("[t+1] Roman Urdu text report")
    post_report(api, new_session(), "text", "ur", text=ROMAN)
    wait_for(gap, "English text")
    print("[t+2] English text report")
    post_report(api, new_session(), "text", "en", text=ENGLISH)
    wait_for(gap, "helmet-card scan")
    print("[t+3] Helmet QR scanned -> Get help")
    scanner = new_session()
    r = httpx.post(
        f"{api}/api/v1/public/card/{card['token']}/alert",
        headers=scanner,
        timeout=30,
        json={
            "client_report_id": str(uuid.uuid4()),
            "lat": CRASH[0],
            "lng": CRASH[1],
            "accuracy_m": 20,
        },
    )
    r.raise_for_status()

    print(
        "Reports sent. Watch /dashboard, /flow and the responder pages (python -m scripts.demo_links)."
    )
    print(f"First report id: {first}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario", default="highway_crash", choices=["highway_crash"]
    )
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--fast", action="store_true", help="3 s gaps instead of 15 s")
    args = parser.parse_args()
    sys.exit(main(args.api, args.fast))
