from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass
class AgentCtx:
    """Per-run state shared by the orchestrator, agent tools and hooks (docs/07_AI_AGENTS.md §5)."""

    report_id: UUID | None = None
    incident_id: UUID | None = None
    extraction: Any = None
    candidates: list[Any] = field(default_factory=list)
    hospital_options: Any = None
    required_targets: list[Any] = field(default_factory=list)
    accepted_plan: list[Any] = field(default_factory=list)
    sent_keys: list[str] = field(default_factory=list)
    lang: str = "en"
    model_used: str | None = None  # set by run_agent: which model produced the output
