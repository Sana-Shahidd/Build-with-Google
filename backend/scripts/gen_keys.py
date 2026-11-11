"""Print secrets to paste into backend/.env (docs/08_SECURITY.md S-13). Prints values only."""

import secrets

from cryptography.fernet import Fernet

print(f"ACK_SECRET={secrets.token_urlsafe(48)}")
print(f"FIELD_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
print(f"PHONE_HASH_PEPPER={secrets.token_urlsafe(48)}")
print(f"TELEGRAM_WEBHOOK_SECRET={secrets.token_urlsafe(32)}")
