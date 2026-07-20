"""
Intelligence Engine - models

Plain dataclasses shared across the engine's modules. Nothing here talks
to Postgres - that's context_builder.py, metrics.py, knowledge_graph.py,
report_generator.py, notification_engine.py. Keeping the shapes separate
means analysis_engine / forecasting_engine / recommendation_engine can be
unit tested with no database at all.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class IntelligenceStatus:
    company_id: str
    active: bool
    activated_at: datetime | None
    deactivated_at: datetime | None
    blueprint_version: int | None
    last_event_at: datetime | None
    last_cycle_at: datetime | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "active": self.active,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
            "blueprint_version": self.blueprint_version,
            "last_event_at": self.last_event_at.isoformat() if self.last_event_at else None,
            "last_cycle_at": self.last_cycle_at.isoformat() if self.last_cycle_at else None,
        }


@dataclass(frozen=True)
class Finding:
    """
    The unit of output from the Analysis / Health / Forecasting engines.
    The Reasoning Engine collects a list of these; the Recommendation,
    Notification, and Report generators all consume the same list rather
    than each recomputing their own view of "what's going on" - so a
    daily summary and a risk notification about the same fact always
    agree with each other, by construction.
    """

    id: str
    kind: str  # health | trend | spend | anomaly | forecast
    severity: str  # info | warning | critical
    title: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "data": self.data,
        }


@dataclass(frozen=True)
class ReasoningResult:
    """
    One deterministic snapshot produced by a single Intelligence Cycle
    (spec: "Event Processing Flow"). Everything downstream in that same
    cycle - the report, the notifications, the recommendations - is
    built from this one object, computed once.
    """

    company_id: str
    generated_at: datetime
    summary: dict[str, Any]
    health: dict[str, Any]
    findings: list[Finding]
    forecast: dict[str, Any]
    blueprint: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "company_id": self.company_id,
            "generated_at": self.generated_at.isoformat(),
            "summary": self.summary,
            "health": self.health,
            "findings": [f.to_dict() for f in self.findings],
            "forecast": self.forecast,
            "blueprint": self.blueprint,
        }
