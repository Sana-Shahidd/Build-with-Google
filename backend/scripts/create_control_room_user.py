"""Create the Control Room login (role 'admin') in Supabase Auth. Idempotent.

Usage: python -m scripts.create_control_room_user [--email controlroom@goldenminute.demo]

The password is generated here and saved ONLY in backend/control_room_login.txt (git-ignored); it is not
printed. Delete the file after you have stored the password somewhere safe. Re-running keeps the existing
user and its password; use --reset-password to generate a new one.
"""

import argparse
import secrets
from pathlib import Path

from app.deps import get_supabase

OUT = Path(__file__).resolve().parents[1] / "control_room_login.txt"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="controlroom@goldenminute.demo")
    parser.add_argument("--reset-password", action="store_true")
    args = parser.parse_args()

    sb = get_supabase()
    users = sb.auth.admin.list_users()
    existing = next(
        (u for u in users if (u.email or "").lower() == args.email.lower()), None
    )
    password = secrets.token_urlsafe(12)

    if existing is None:
        res = sb.auth.admin.create_user(
            {"email": args.email, "password": password, "email_confirm": True}
        )
        user_id = res.user.id
        action = "created"
    else:
        user_id = existing.id
        if args.reset_password:
            sb.auth.admin.update_user_by_id(user_id, {"password": password})
            action = "password reset"
        else:
            action = "kept (password unchanged)"

    sb.table("profiles").update({"role": "admin", "display_name": "Control Room"}).eq(
        "id", user_id
    ).execute()

    if action != "kept (password unchanged)":
        OUT.write_text(
            f"Control Room login\nemail: {args.email}\npassword: {password}\n",
            encoding="utf-8",
        )
    print(f"Control room user {args.email}: {action}.")
    if action != "kept (password unchanged)":
        print(f"Credentials saved in {OUT} (git-ignored). The password is not printed.")


main()
