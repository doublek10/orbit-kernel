"""
Error Logger

Separate from AuditLogger (which only ever records successful,
intentional actions - Development Rule #8). This records every
unhandled exception the Kernel's global FastAPI exception handlers
catch (main.py), independent of which tenant or workflow triggered it.
Backs the Admin Control Panel's "Errors" page: the list of error codes,
and the ability to drill into one specific error.
"""

# Required: this class defines an instance method named `list()` below.
# Inside a class body, once a name is bound (e.g. by `def list(...):`),
# that name shadows the builtin for the REST of the class body - so a
# later annotation like `list[dict]` tries to subscript the method
# object, not the builtin `list` type, and raises
# `TypeError: 'function' object is not subscriptable` at import time.
# Deferring annotation evaluation (PEP 563) sidesteps this entirely -
# annotations become plain strings and are never evaluated at class-
# definition time.
from __future__ import annotations

import asyncpg


class ErrorLogger:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def record(
        self,
        *,
        source: str,
        code: str,
        message: str,
        detail: dict | None = None,
        company_id: str | None = None,
        request_path: str | None = None,
    ) -> None:
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO error_log (source, code, message, detail, company_id, request_path)
                    VALUES ($1, $2, $3, $4::jsonb, $5, $6)
                    """,
                    source,
                    code,
                    message,
                    detail or {},
                    company_id,
                    request_path,
                )
        except Exception:
            # Logging an error must never itself raise and mask the
            # original failure being reported.
            pass

    async def list(self, *, limit: int = 50, code: str | None = None) -> list[dict]:
        async with self._pool.acquire() as conn:
            if code:
                rows = await conn.fetch(
                    """
                    SELECT * FROM error_log WHERE code = $1
                    ORDER BY created_at DESC LIMIT $2
                    """,
                    code,
                    limit,
                )
            else:
                rows = await conn.fetch(
                    "SELECT * FROM error_log ORDER BY created_at DESC LIMIT $1", limit
                )
        return [self._row(r) for r in rows]

    async def codes_summary(self) -> list[dict]:
        """Distinct error codes with counts - so the Admin panel can
        show 'get a specific error' by code without listing everything."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT code, count(*) AS occurrences, max(created_at) AS last_seen
                FROM error_log
                GROUP BY code
                ORDER BY last_seen DESC
                """
            )
        return [
            {
                "code": r["code"],
                "occurrences": r["occurrences"],
                "last_seen": r["last_seen"].isoformat(),
            }
            for r in rows
        ]

    async def get(self, error_id: int) -> dict | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM error_log WHERE id = $1", error_id)
        return self._row(row) if row else None

    @staticmethod
    def _row(row) -> dict:
        return {
            "id": row["id"],
            "source": row["source"],
            "code": row["code"],
            "message": row["message"],
            "detail": row["detail"],
            "company_id": str(row["company_id"]) if row["company_id"] else None,
            "request_path": row["request_path"],
            "created_at": row["created_at"].isoformat(),
        }
