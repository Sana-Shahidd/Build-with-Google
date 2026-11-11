"""Print the responder URLs for the demo orgs (hospital + police near the crash site).

Usage: python -m scripts.demo_links
Base URL = PUBLIC_BASE_URL (the Cloudflare tunnel) if set, else http://localhost:5173.
Links expire after INBOX_TOKEN_MAX_AGE_S (6 h) - re-run to get fresh ones. Treat them as secrets.
"""

import asyncio
import sys

from app.config import settings
from app.deps import get_supabase
from app.services import ack_tokens
from scripts.seed_mock import CRASH_SITE, demo_hospitals, nearest


async def main() -> int:
    sb = get_supabase()
    orgs = (
        await asyncio.to_thread(lambda: sb.table("organizations").select("*").execute())
    ).data
    hospital = (await demo_hospitals(orgs, 1))[0]
    police = nearest(orgs, "police_station", CRASH_SITE)[0]
    base = (settings.PUBLIC_BASE_URL or "http://localhost:5173").rstrip("/")
    for role, org in (("HOSPITAL", hospital), ("POLICE  ", police)):
        url = f"{base}/r/{ack_tokens.make_inbox_token(org['id'])}"
        print(
            f"{role}  {org['name'].encode('ascii', 'replace').decode()}\n          {url}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
