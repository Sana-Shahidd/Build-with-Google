"""Typed agent outputs (docs/07_AI_AGENTS.md §5). Pydantic validates; code decides."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import IncidentType, InjuryType, NeedType, Severity


class IncidentExtraction(BaseModel):
    is_emergency: bool
    incident_type: IncidentType
    severity: Severity
    est_casualties_min: int = Field(ge=0, le=500)
    est_casualties_max: int = Field(ge=0, le=500)
    injury_types: list[InjuryType] = Field(default_factory=list, max_length=8)
    needs: list[NeedType] = Field(default_factory=list, max_length=4)
    ongoing_danger: bool
    location_hint: str | None = Field(default=None, max_length=200)
    summary_en: str = Field(max_length=240)
    summary_local: str = Field(max_length=240)  # in the report's language
    language_detected: str = Field(max_length=8)  # ISO 639-1 or 'unknown'
    confidence: float = Field(ge=0, le=1)
    missing_info: list[str] = Field(default_factory=list, max_length=4)
    followup_question: str | None = Field(default=None, max_length=160)
    rationale: str = Field(max_length=200)

    @field_validator("est_casualties_max")
    @classmethod
    def max_ge_min(cls, v: int, info) -> int:
        return max(v, info.data.get("est_casualties_min", 0))


class VerificationDecision(BaseModel):
    action: Literal["merge", "new"]
    incident_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    rationale: str = Field(max_length=200)


class TranscriptResult(BaseModel):
    text: str
    language: str | None = None


class PlannedAssignment(BaseModel):
    hospital_id: str
    casualties: int = Field(ge=0, le=500)
    critical: int = Field(ge=0, le=500)
    reason: str = Field(max_length=120)
    # filled by code (matching.spread / save_plan), never by an agent
    eta_minutes: float | None = None
    over_capacity: bool = False


class Candidate(BaseModel):
    """An existing incident near a new report (output of incidents_near_for_merge)."""

    id: str
    incident_type: str
    summary_en: str | None = None
    created_at: str
    distance_m: float


class IncidentChange(BaseModel):
    """What recompute_incident changed; drives triage and update alerts."""

    incident_id: str
    short_code: str
    created: bool = False
    old_status: str | None = None
    new_status: str
    old_severity: str | None = None
    new_severity: str
    old_casualties_max: int = 0
    new_casualties_max: int = 0
    report_count: int = 1
    unique_reporters: int = 1
    confidence: float = 0.0

    @property
    def status_changed(self) -> bool:
        return self.old_status != self.new_status

    @property
    def significant(self) -> bool:
        """Triage/update trigger: new incident, status moved, severity or casualties grew."""
        return (
            self.created
            or self.status_changed
            or self.old_severity != self.new_severity
            or self.new_casualties_max > self.old_casualties_max
        )


class HospitalOption(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    capabilities: list[str]
    free_beds: int
    icu_available: int
    capacity_known: bool
    eta_minutes: float
    distance_m: float
    fits: bool


class HospitalOptions(BaseModel):
    total: int
    critical_total: int
    required_capabilities: list[str]
    hospitals: list[HospitalOption]


class Landmark(BaseModel):
    """Built by code from OpenStreetMap; the only facts the Landmark Agent may use."""

    index: int
    kind: str
    name: str = Field(max_length=80)
    distance_m: int = Field(ge=0, le=300)
    compass: Literal["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


class LandmarkLine(BaseModel):
    line_local: str = Field(max_length=160)
    line_en: str = Field(max_length=160)
    used: list[int] = Field(default_factory=list, max_length=3)
    rationale: str = Field(max_length=200)


CoachIntent = Literal[
    "next", "repeat", "previous", "switch_card", "call_help", "done", "unclear"
]


class CoachTurn(BaseModel):
    intent: CoachIntent
    card_key: str | None = (
        None  # only with switch_card; validated against first_aid.json keys
    )
    ack: str = Field(max_length=120)  # calm reassurance only; no medical content
    rationale: str = Field(max_length=200)


class TriagePlan(BaseModel):
    accepted: bool  # true only if propose_assignment_plan returned ok
    rationale: str = Field(max_length=200)


class DispatchPlan(BaseModel):
    sent: bool
    rationale: str = Field(max_length=200)


class PrepSummary(BaseModel):
    actions: list[str] = Field(default_factory=list, max_length=6)
    rationale: str = Field(max_length=200)


class AfterActionReport(BaseModel):
    markdown: str = Field(max_length=6000)
    rationale: str = Field(max_length=200)
