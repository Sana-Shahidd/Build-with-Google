"""Hashing and encryption helpers (docs/08_SECURITY.md S-10). Libraries only: hmac + Fernet."""

import hashlib
import hmac

import phonenumbers
from cryptography.fernet import Fernet

from app.config import settings


def ip_hash(ip: str) -> str:
    """HMAC of the client IP so bursts can be detected without storing IPs."""
    return hmac.new(
        settings.PHONE_HASH_PEPPER.encode(), ip.encode(), hashlib.sha256
    ).hexdigest()


def to_e164(raw: str, region: str | None) -> str:
    """Parse to E.164 or raise ValueError."""
    try:
        num = phonenumbers.parse(raw, region)
    except phonenumbers.NumberParseException as e:
        raise ValueError("invalid phone number") from e
    if not phonenumbers.is_valid_number(num):
        raise ValueError("invalid phone number")
    return phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164)


def phone_hash(e164: str) -> str:
    return hmac.new(
        settings.PHONE_HASH_PEPPER.encode(), e164.encode(), hashlib.sha256
    ).hexdigest()


def encrypt_phone(e164: str) -> str:
    return (
        Fernet(settings.FIELD_ENCRYPTION_KEY.encode()).encrypt(e164.encode()).decode()
    )


def decrypt_phone(token: str) -> str:
    return (
        Fernet(settings.FIELD_ENCRYPTION_KEY.encode()).decrypt(token.encode()).decode()
    )
