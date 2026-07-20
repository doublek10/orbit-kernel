"""
Intelligence Engine - Metrics

Trend History, per the spec's Intelligence Database section: numbered
snapshots of derived metrics (health score, net cash flow, ...) recorded
every Intelligence Cycle, so "improved 12% vs last week" is a real
lookup against stored history rather than a value that could drift if
someone edits the underlying ledger later.
"""

from dataclasses import dataclass
from datetime import datetime

import asyncpg


@dataclass(frozen=True)
class MetricPoint:
    value: float
    context: dict
    computed_at: datetime

    def to_dict(self) -> dict:
        return {
            "value": self.value,
            "context": self.context,
            "computed_at": self.computed_at.isoformat(),
        }


class MetricsStore:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def record(self, company_id: str, metric_key: str, value: float, context: dict | None = None) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO intelligence_metrics (company_id, metric_key, value, context)
                VALUES ($1, $2, $3, $4::jsonb)
                """,
                company_id,
                metric_key,
                value,
                context or {},
            )

    async def history(self, company_id: str, metric_key: str, limit: int = 90) -> list[MetricPoint]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT value, context, computed_at FROM intelligence_metrics
                WHERE company_id = $1 AND metric_key = $2
                ORDER BY computed_at DESC
                LIMIT $3
                """,
                company_id,
                metric_key,
                limit,
            )
        return [MetricPoint(float(r["value"]), r["context"], r["computed_at"]) for r in rows]

    async def latest(self, company_id: str, metric_key: str) -> MetricPoint | None:
        points = await self.history(company_id, metric_key, limit=1)
        return points[0] if points else None

    async def all_latest(self, company_id: str) -> dict[str, MetricPoint]:
        """One most-recent point per metric_key - what the performance/
        history dashboard views read to show every tracked metric at a
        glance without N separate calls."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT ON (metric_key) metric_key, value, context, computed_at
                FROM intelligence_metrics
                WHERE company_id = $1
                ORDER BY metric_key, computed_at DESC
                """,
                company_id,
            )
        return {r["metric_key"]: MetricPoint(float(r["value"]), r["context"], r["computed_at"]) for r in rows}
