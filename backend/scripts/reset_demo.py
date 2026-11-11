"""Clear DEMO data between rehearsals: reports, incidents (and their targets/assignments/events),
the agent activity feed, emergency cards and their scans.

Keeps organizations, hospital details, ambulances, profiles/users and seed data.
Usage: python -m scripts.reset_demo --yes        (refuses to run without --yes, and in production)
"""

import argparse
import sys

from app.config import settings
from app.deps import get_supabase

# child tables first; every delete targets all rows of that table via a filter that matches any id
TABLES = [
    ("deliveries", "id"),
    ("alert_targets", "id"),
    ("hospital_assignments", "id"),
    ("incident_events", "id"),
    ("agent_activity", "id"),
    ("card_scans", "id"),
    ("reports", "id"),
    ("incidents", "id"),
    ("emergency_cards", "id"),
]


def main(confirmed: bool) -> int:
    if settings.APP_ENV == "production":
        print("Refusing: APP_ENV=production")
        return 1
    if not confirmed:
        print(
            "This deletes all demo reports, incidents, alerts, feed rows and emergency cards."
        )
        print("Run again with --yes to confirm.")
        return 1
    sb = get_supabase()
    for table, key in TABLES:
        res = sb.table(table).delete().not_.is_(key, "null").execute()
        print(f"{table}: {len(res.data)} deleted")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true")
    sys.exit(main(parser.parse_args().yes))
