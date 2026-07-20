"""
Intelligence Engine - Health Engine

The spec's "Monitor Business Health" capability. The scoring itself
already exists and is explainable (financial_graph.graph.health_score) -
this module's job is to turn that into a Finding the rest of the engine
can consume the same way it consumes Analysis/Forecast output, and to
record the score into Trend History every cycle.
"""

import asyncpg

from financial_graph.graph import FinancialGraph
from kernel.intelligence_engine.models import Finding

_SEVERITY = {"strong": "info", "watch": "warning", "at risk": "critical"}


class HealthEngine:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
        self._graph = FinancialGraph(pool)

    async def evaluate(self, company_id: str) -> tuple[dict, Finding]:
        health = await self._graph.health_score(company_id)
        finding = Finding(
            id="health-score",
            kind="health",
            severity=_SEVERITY[health["label"]],
            title=f"Business health: {health['label']} ({health['score']}/100)",
            message=health["signals"][0] if health["signals"] else "",
            data=health,
        )
        return health, finding
