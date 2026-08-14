"""
Health

Reports Kernel liveness/readiness: whether the self-hosted Postgres
connection is up, and - since the Kernel is a long-running Python
process managed outside of any request/response cycle - basic proof
that the Python process itself is alive and how long it's been running.
This second part is what backs the Admin Control Panel's "is our Python
running" check: if this endpoint responds at all, the process is
running; `uptime_seconds` and `pid` let an operator tell a fresh restart
apart from a process that's been up for weeks.
"""

import os
import platform
import time

import asyncpg

_PROCESS_STARTED_AT = time.time()


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

        return {
            "status": "ok" if db_ok else "degraded",
            "database": db_ok,
            "python": {
                "running": True,  # trivially true if this code executed at all
                "pid": os.getpid(),
                "version": platform.python_version(),
                "uptime_seconds": round(time.time() - _PROCESS_STARTED_AT, 1),
            },
        }
