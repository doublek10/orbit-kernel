"""
Intelligence Engine - Report Generator

"Reports are generated automatically" - one persisted document per
report_type per period, built from the same ReasoningResult the
Notification and Recommendation engines already used this cycle. Only
daily_summary, weekly_executive, monthly_forecast, and quarterly_trend
are implemented, matching the Scheduler's actual jobs
(kernel/intelligence_engine/scheduler.py); the spec's full report list
(payroll/inventory reports etc.) waits on those Business Systems being
connected, same honesty convention as the rest of this codebase.
"""

from datetime import datetime, timedelta, timezone

import asyncpg

from kernel.intelligence_engine.models import ReasoningResult

_PERIODS = {
    "daily_summary": timedelta(days=1),
    "weekly_executive": timedelta(weeks=1),
    "monthly_forecast": timedelta(days=30),
    "quarterly_trend": timedelta(days=90),
}


class ReportGenerator:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def generate(self, result: ReasoningResult, report_type: str) -> dict:
        if report_type not in _PERIODS:
            raise ValueError(f"Unknown report_type '{report_type}'")

        period_end = result.generated_at
        period_start = period_end - _PERIODS[report_type]
        data = result.to_dict()

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO intelligence_reports (company_id, report_type, period_start, period_end, data)
                VALUES ($1, $2, $3, $4, $5::jsonb)
                RETURNING id, generated_at
                """,
                result.company_id,
                report_type,
                period_start,
                period_end,
                data,
            )

        return {
            "id": str(row["id"]),
            "report_type": report_type,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "generated_at": row["generated_at"].isoformat(),
            "data": data,
        }

    async def list_reports(self, company_id: str, report_type: str | None = None, limit: int = 20) -> list[dict]:
        async with self._pool.acquire() as conn:
            if report_type:
                rows = await conn.fetch(
                    """
                    SELECT id, report_type, period_start, period_end, data, generated_at
                    FROM intelligence_reports
                    WHERE company_id = $1 AND report_type = $2
                    ORDER BY generated_at DESC LIMIT $3
                    """,
                    company_id,
                    report_type,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, report_type, period_start, period_end, data, generated_at
                    FROM intelligence_reports
                    WHERE company_id = $1
                    ORDER BY generated_at DESC LIMIT $2
                    """,
                    company_id,
                    limit,
                )
        return [
            {
                "id": str(r["id"]),
                "report_type": r["report_type"],
                "period_start": r["period_start"].isoformat(),
                "period_end": r["period_end"].isoformat(),
                "generated_at": r["generated_at"].isoformat(),
                "data": r["data"],
            }
            for r in rows
        ]
