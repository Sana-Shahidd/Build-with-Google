"""Python mirror of the DB enums (docs/05_DATABASE_SCHEMA.md §1 and 0006a)."""

from enum import StrEnum


class UserRole(StrEnum):
    REPORTER = "reporter"
    DISPATCHER = "dispatcher"
    HOSPITAL_STAFF = "hospital_staff"
    POLICE = "police"
    RESCUE = "rescue"
    FIRE = "fire"
    ADMIN = "admin"


class OrgType(StrEnum):
    HOSPITAL = "hospital"
    POLICE_STATION = "police_station"
    RESCUE_STATION = "rescue_station"
    FIRE_STATION = "fire_station"


class ReportChannel(StrEnum):
    APP = "app"
    SMS = "sms"
    MISSED_CALL = "missed_call"
    WHATSAPP = "whatsapp"


class IncidentType(StrEnum):
    ATTACK_SHOOTING = "attack_shooting"
    EXPLOSION = "explosion"
    FIRE = "fire"
    ROAD_ACCIDENT = "road_accident"
    BUILDING_COLLAPSE = "building_collapse"
    MEDICAL = "medical"
    RIOT_CROWD = "riot_crowd"
    FLOOD = "flood"
    OTHER = "other"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    REVIEW = "review"
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    CLOSED = "closed"
    DISMISSED = "dismissed"


class InjuryType(StrEnum):
    GUNSHOT = "gunshot"
    BLAST_SHRAPNEL = "blast_shrapnel"
    BURNS = "burns"
    FRACTURE = "fracture"
    HEAD_INJURY = "head_injury"
    BLEEDING = "bleeding"
    CRUSH = "crush"
    SMOKE_INHALATION = "smoke_inhalation"
    DROWNING = "drowning"
    CARDIAC = "cardiac"
    UNCONSCIOUS = "unconscious"
    BREATHING_DIFFICULTY = "breathing_difficulty"
    UNKNOWN = "unknown"


class NeedType(StrEnum):
    AMBULANCE = "ambulance"
    POLICE = "police"
    FIRE = "fire"
    RESCUE = "rescue"


class Capability(StrEnum):
    TRAUMA = "trauma"
    BURNS = "burns"
    NEURO = "neuro"
    ORTHOPEDIC = "orthopedic"
    CARDIAC = "cardiac"
    PEDIATRIC = "pediatric"
    GENERAL = "general"


class Specialty(StrEnum):
    TRAUMA_SURGEON = "trauma_surgeon"
    BURN_SPECIALIST = "burn_specialist"
    NEUROSURGEON = "neurosurgeon"
    ORTHOPEDIC_SURGEON = "orthopedic_surgeon"
    CARDIOLOGIST = "cardiologist"
    ANESTHETIST = "anesthetist"
    EMERGENCY_PHYSICIAN = "emergency_physician"
    GENERAL_SURGEON = "general_surgeon"
    PEDIATRICIAN = "pediatrician"


class RecipientKind(StrEnum):
    HOSPITAL = "hospital"
    POLICE = "police"
    RESCUE = "rescue"
    FIRE = "fire"
    DOCTOR = "doctor"
    DONOR = "donor"
    VOLUNTEER = "volunteer"
    PUBLIC = "public"
    DISPATCHER = "dispatcher"


class TargetStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    ESCALATED = "escalated"
    NO_RESPONSE = "no_response"
    FAILED = "failed"


class DeliveryChannel(StrEnum):
    TELEGRAM = "telegram"
    SMS = "sms"
    VOICE = "voice"
    EMAIL = "email"
    PUSH = "push"
    DASHBOARD = "dashboard"


class DeliveryStatus(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class AmbulanceStatus(StrEnum):
    AVAILABLE = "available"
    EN_ROUTE_SCENE = "en_route_scene"
    AT_SCENE = "at_scene"
    EN_ROUTE_HOSPITAL = "en_route_hospital"
    AT_HOSPITAL = "at_hospital"


class BloodType(StrEnum):
    A_POS = "A+"
    A_NEG = "A-"
    B_POS = "B+"
    B_NEG = "B-"
    AB_POS = "AB+"
    AB_NEG = "AB-"
    O_POS = "O+"
    O_NEG = "O-"


class MemberSkill(StrEnum):
    CPR = "cpr"
    FIRST_AID = "first_aid"
    NURSE = "nurse"
    DOCTOR = "doctor"


class CommunityResponse(StrEnum):
    COMING = "coming"
    CANNOT = "cannot"


class Sex(StrEnum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    UNKNOWN = "unknown"


class AgentName(StrEnum):
    ORCHESTRATOR = "orchestrator"
    INTAKE = "intake"
    VERIFICATION = "verification"
    TRIAGE = "triage"
    DISPATCH = "dispatch"
    HOSPITAL_PREP = "hospital_prep"
    DEBRIEF = "debrief"
    LANDMARK = "landmark"
    VOICE_COACH = "voice_coach"
    PREPAREDNESS = "preparedness"


class ActivityKind(StrEnum):
    STARTED = "started"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DECISION = "decision"
    GUARDRAIL_BLOCK = "guardrail_block"
    FALLBACK = "fallback"
    RULE = "rule"
    ERROR = "error"
    FINISHED = "finished"
