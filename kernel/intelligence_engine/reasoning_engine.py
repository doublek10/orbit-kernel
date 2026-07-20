"""
Intelligence Engine - Reasoning Engine

The composition root for a single Intelligence Cycle (spec's "Event
Processing Flow": ... Generate Analysis -> Update Knowledge Graph ->
Store Intelligence -> Generate Notifications -> Generate Reports).
Everything else in the cycle - the Report Generator, the Notification
Engine, the Recommendation Engine - reads the one ReasoningResult this
produces, instead of each recomputing balance_summary/health/analysis
independently. That's what keeps a daily report and a same-day
notification about the exact same fact from ever disagreeing.
"""

from datetime import datetime, timezone

import asyncpg

from financial_graph.graph import FinancialGraph
from kernel.company_blueprint.loader import BlueprintLoader
from kernel.company_blueprint.recommendations import relevant_insight_ids
from kernel.intelligence_engine.analysis_engine import AnalysisEngine
from kernel.intelligence_engine.forecasting_engine import ForecastingEngine
from kernel.intelligence_engine.health_engine import HealthEngine
from kernel.intelligence_engine.models import ReasoningResult


class ReasoningEngine:
    def __init__(self, pool: asyncpg.Pool):
        self._graph = FinancialGraph(pool)
        self._health = HealthEngine(pool)
        self._analysis = AnalysisEngine(pool)
        self._forecasting = ForecastingEngine()
        self._blueprints = BlueprintLoader(pool)

    async def run(self, company_id: str) -> ReasoningResult:
        blueprint = await self._blueprints.load(company_id)
        allowed_categories = blueprint.allowed_categories if blueprint else None
        enabled_capabilities = set(blueprint.enabled_capabilities) if blueprint and blueprint.enabled_capabilities else None

        summary = await self._graph.balance_summary(company_id)
        health, health_finding = await self._health.evaluate(company_id)
        findings = [health_finding, *await self._analysis.analyze(company_id, allowed_categories)]

        forecast = self._forecasting.project(summary)
        findings.append(self._forecasting.finding(forecast))

        # Blueprint Governance: enabled_capabilities is the spec's
        # "Allowed Questions" made real - a capability outside the list
        # never reaches findings (so it never notifies, never gets
        # recommended, never appears on the dashboard's findings feed).
        # `health` and `forecast` above stay populated as top-level
        # dashboard fields regardless - they're the two structural
        # summary tiles every company sees, not optional capabilities;
        # gating only applies to which *Findings* get surfaced from them.
        if enabled_capabilities is not None:
            findings = [f for f in findings if f.kind in enabled_capabilities]

        if blueprint is not None and blueprint.priorities:
            # Same rule ai.list already applies (kernel/company_blueprint/
            # recommendations.py): health stays the headline, findings
            # that match a stated Blueprint priority move up next,
            # everything else keeps its statistically-driven order after
            # that. Nothing is hidden - Blueprint priorities steer
            # attention, they don't gate what the Engine is allowed to
            # observe (that's enabled_capabilities' job, above).
            relevant = relevant_insight_ids(blueprint.priorities)
            findings.sort(key=lambda f: (f.id != "health-score", f.id not in relevant))

        return ReasoningResult(
            company_id=company_id,
            generated_at=datetime.now(timezone.utc),
            summary=summary,
            health=health,
            findings=findings,
            forecast=forecast,
            blueprint=blueprint.to_dict() if blueprint else None,
        )
