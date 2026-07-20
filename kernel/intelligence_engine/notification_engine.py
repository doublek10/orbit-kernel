"""
Intelligence Engine - Notification Engine

"Notifications are sent according to company preferences" (spec). Today
"sent" means persisted to intelligence_notifications for the Frontend's
Notification Center to read - there's no email/SMS/push channel wired up
yet, same honest-stub convention workflow_engine/automation.py already
uses for its own notify action.

Only findings at or above the company's min_notification_severity
generate a notification, and each (company, category) pair is deduped
over a rolling window so a still-true condition doesn't renotify every
cycle.
"""

from datetime import timedelta

import asyncpg

from kernel.intelligence_engine.models import Finding, ReasoningResult

_SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}
_DEDUP_WINDOW = timedelta(hours=6)


class NotificationEngine:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def notify(self, result: ReasoningResult) -> list[dict]:
        min_severity = await self._min_severity(result.company_id)
        threshold = _SEVERITY_RANK[min_severity]

        created = []
        async with self._pool.acquire() as conn:
            for finding in result.findings:
                if _SEVERITY_RANK.get(finding.severity, 0) < threshold:
                    continue

                recent = await conn.fetchval(
                    """
                    SELECT id FROM intelligence_notifications
                    WHERE company_id = $1 AND category = $2
                      AND created_at >= now() - $3::interval
                    LIMIT 1
                    """,
                    result.company_id,
                    finding.kind,
                    _DEDUP_WINDOW,
                )
                if recent:
                    continue

                row = await conn.fetchrow(
                    """
                    INSERT INTO intelligence_notifications (company_id, category, severity, title, message, data)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb)
                    RETURNING id, created_at
                    """,
                    result.company_id,
                    finding.kind,
                    finding.severity,
                    finding.title,
                    finding.message,
                    finding.data,
                )
                created.append(
                    {
                        "id": str(row["id"]),
                        "category": finding.kind,
                        "severity": finding.severity,
                        "title": finding.title,
                        "message": finding.message,
                        "created_at": row["created_at"].isoformat(),
                    }
                )
        return created

    async def _min_severity(self, company_id: str) -> str:
        async with self._pool.acquire() as conn:
            value = await conn.fetchval(
                "SELECT min_notification_severity FROM intelligence_preferences WHERE company_id = $1",
                company_id,
            )
        return value or "info"
