from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Constants from docs/03_TRD.md §5 (names are referenced by the docs).
MERGE_RADIUS_M = 500
AUTO_MERGE_RADIUS_M = 150
MERGE_WINDOW_MIN = 15
CONF_VERIFIED = 0.60
CONF_UNVERIFIED = 0.30
ACK_TIMEOUT_S = 60
ESCALATION_TICK_S = 10
HOSPITAL_SEARCH_RADIUS_KM = 25
HOSPITAL_CANDIDATES = 15
MAX_HOSPITALS = 5
CRITICAL_SHARE = {"low": 0.0, "medium": 0.2, "high": 0.4, "critical": 0.6}
FALLBACK_SPEED_KMH = 25
OSRM_TIMEOUT_S = 3
AGENT_TIMEOUT_S = 15
DEBRIEF_TIMEOUT_S = 30
PROVIDER_COOLDOWN_S = 60
DISCOVERY_MIN_HOSPITALS = 3
DISCOVERY_TIMEOUT_S = 8
DISCOVERY_TILE_TTL_H = 24
COUNTRY_CACHE_TTL_D = 7
DONOR_RADIUS_KM = 10
DONOR_COOLDOWN_H = 24
DONOR_MAX = 30
BLOOD_LOW_UNITS = 5
VOLUNTEER_RADIUS_KM = 1.5
VOLUNTEER_COOLDOWN_H = 6
VOLUNTEER_MAX = 10
PUBLIC_ALERT_RADIUS_KM = 2
MAX_AUDIO_SECONDS = 60
LANDMARK_RADIUS_M = 300
LANDMARK_MAX = 3
LANDMARK_RELOCATE_M = 150
LANDMARK_TIMEOUT_S = 6
VERIFICATION_TIMEOUT_S = 8
TRIAGE_TIMEOUT_S = 12
DISPATCH_TIMEOUT_S = 8
COACH_TIMEOUT_S = 6
PREPAREDNESS_TIMEOUT_S = 12
CARD_TOKEN_BYTES = 18
CARD_MAX_CONTACTS = 3
CARD_SCAN_RATE = "30/minute"
CARD_ALERT_RATE = "3/hour"
COACH_RATE = "12/hour"
COACH_MAX_PER_REPORT = 10
RIDE_IMPACT_G = 4.0
RIDE_COUNTDOWN_S = 20
BLACKSPOT_GRID_M = 200
MAX_AUDIO_BYTES = 10 * 1024 * 1024
MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_TEXT_CHARS = 1000
ACK_TOKEN_MAX_AGE_S = 6 * 3600
SIM_TICK_S = 2
SIM_SPEED_KMH = 40
RETENTION_DAYS_AFTER_CLOSE = 7
INBOX_TOKEN_MAX_AGE_S = ACK_TOKEN_MAX_AGE_S  # responder inbox link lifetime


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "dev"
    PUBLIC_BASE_URL: str = ""
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    COUNTRY_PROFILE: str = "PK"
    SIMULATION_ENABLED: bool = False

    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    INTAKE_MODEL: str = ""
    INTAKE_FALLBACK_MODEL: str = ""
    VERIFICATION_MODEL: str = ""
    VERIFICATION_FALLBACK_MODEL: str = ""
    TRIAGE_MODEL: str = ""
    TRIAGE_FALLBACK_MODEL: str = ""
    DISPATCH_MODEL: str = ""
    DISPATCH_FALLBACK_MODEL: str = ""
    HOSPITAL_PREP_MODEL: str = ""
    HOSPITAL_PREP_FALLBACK_MODEL: str = ""
    DEBRIEF_MODEL: str = ""
    DEBRIEF_FALLBACK_MODEL: str = ""
    LANDMARK_MODEL: str = ""
    LANDMARK_FALLBACK_MODEL: str = ""
    COACH_MODEL: str = ""
    COACH_FALLBACK_MODEL: str = ""
    PREPAREDNESS_MODEL: str = ""
    PREPAREDNESS_FALLBACK_MODEL: str = ""

    TELEGRAM_ENABLED: bool = (
        False  # off by default: Telegram is not usable in Pakistan (DECISIONS.md)
    )
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_BOT_USERNAME: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    VAPID_PUBLIC_KEY: str = ""

    ACK_SECRET: str = ""
    FIELD_ENCRYPTION_KEY: str = ""
    PHONE_HASH_PEPPER: str = ""

    OSRM_BASE_URL: str = "https://router.project-osrm.org"
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    NOMINATIM_USER_AGENT: str = "golden-minute-hackathon/1.0"

    DEMO_HOSPITAL_CHAT: str = ""
    DEMO_POLICE_CHAT: str = ""

    def model_for(self, agent_key: str) -> str:
        return getattr(self, f"{agent_key.upper()}_MODEL")

    def fallback_for(self, agent_key: str) -> str:
        return getattr(self, f"{agent_key.upper()}_FALLBACK_MODEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
