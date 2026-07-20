"""
Health (stub)

Reports Kernel liveness/readiness, including whether the self-hosted
Postgres connection is up.
"""

import asyncpg


class HealthCheck:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def check(self) -> dict:
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            db_ok = True
        except Exception:
            db_ok = False
        return {"status": "ok" if db_ok else "degraded", "database": db_ok}
