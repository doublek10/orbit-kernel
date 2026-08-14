"""
Security Alerts

Distinct from error_log: these are specifically security-relevant
events, not ordinary bugs - a mismatched Gateway secret, an invalid or
expired admin session, an access attempt against a deactivated company
or user, a failed admin login. The Admin Control Panel polls
`GET /admin/security-alerts` from a global banner mounted in its
dashboard layout, so an operator sees a new alert no matter which page
they're currently on ("instant security alert from each page").
"""

# Required: this class defines an instance method named `list()` below,
# which shadows the builtin `list` for the rest of the class body once
# Python executes that `def` line - so a later annotation like
# `list[dict]` fails with `TypeError: 'function' object is not
# subscriptable`. Deferring annotation evaluation (PEP 563) avoids it.
from __future__ import annotations

import asyncpg


class SecurityAlerts:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def record(
        self,
        *,
        severity: str,
        category: str,
        message: str,
        company_id: str | None = None,
        source_page: str | None = None,
    ) -> None:
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO security_alerts (severity, category, message, company_id, source_page)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    severity,
                    category,
                    message,
                    company_id,
                    source_page,
                )
        except Exception:
            pass

    async def list(self, *, resolved: bool | None = None, limit: int = 50) -> list[dict]:
        async with self._pool.acquire() as conn:
            if resolved is None:
                rows = await conn.fetch(
                    "SELECT * FROM security_alerts ORDER BY created_at DESC LIMIT $1",
                    limit,
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM security_alerts WHERE resolved = $1
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    resolved,
                    limit,
                )
        return [self._row(r) for r in rows]

    async def resolve(self, alert_id: int) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE security_alerts SET resolved = true WHERE id = $1", alert_id
            )

    @staticmethod
    def _row(row) -> dict:
        return {
            "id": row["id"],
            "severity": row["severity"],
            "category": row["category"],
            "message": row["message"],
            "company_id": str(row["company_id"]) if row["company_id"] else None,
            "source_page": row["source_page"],
            "resolved": row["resolved"],
            "created_at": row["created_at"].isoformat(),
        }
