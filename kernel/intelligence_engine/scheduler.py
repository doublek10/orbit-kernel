"""
Intelligence Engine - Scheduler

The spec's Scheduling section, for real: background jobs that run
"regardless of user activity" - not the kernel/scheduler/scheduler.py
stub (that one's `raise NotImplementedError`, and is a general-purpose
job scheduler nothing else in the Kernel uses yet). This is a small,
self-contained asyncio loop scoped to Intelligence's own five jobs,
since it doesn't need a general queue - just "is this job overdue for
this company", checked against intelligence_job_runs.

    health_hourly     -> every hour     -> run_cycle only
    daily_summary     -> every day      -> run_cycle + daily_summary report
    weekly_executive  -> every 7 days   -> run_cycle + weekly_executive report
    monthly_forecast  -> every 30 days  -> run_cycle + monthly_forecast report
    quarterly_trend   -> every 90 days  -> run_cycle + quarterly_trend report

A single asyncio task, ticking every `tick_seconds` (short in dev so the
behaviour is observable without waiting an hour; production would set
this to something like 300). Each tick is cheap - one query per job per
active company - so a short tick interval doesn't mean jobs run more
often than their real interval, only that they run *close to* on time.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

import asyncpg

from kernel.intelligence_engine.manager import get_intelligence_manager

logger = logging.getLogger(__name__)

_JOBS: dict[str, timedelta] = {
    "health_hourly": timedelta(hours=1),
    "daily_summary": timedelta(days=1),
    "weekly_executive": timedelta(days=7),
    "monthly_forecast": timedelta(days=30),
    "quarterly_trend": timedelta(days=90),
}

_REPORT_TYPES = {"daily_summary", "weekly_executive", "monthly_forecast", "quarterly_trend"}


class IntelligenceScheduler:
    def __init__(self, pool: asyncpg.Pool, tick_seconds: float = 60.0):
        self._pool = pool
        self._tick_seconds = tick_seconds
        self._manager = get_intelligence_manager(pool)
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while True:
            try:
                await self._tick()
            except Exception:  # noqa: BLE001 - one bad tick must never kill the loop
                logger.exception("Intelligence Scheduler tick failed")
            await asyncio.sleep(self._tick_seconds)

    async def _tick(self) -> None:
        async with self._pool.acquire() as conn:
            active_companies = await conn.fetch(
                "SELECT company_id FROM intelligence_status WHERE active = true"
            )

        for row in active_companies:
            company_id = str(row["company_id"])
            for job_name, interval in _JOBS.items():
                if await self._is_due(company_id, job_name, interval):
                    await self._run_job(company_id, job_name)

    async def _is_due(self, company_id: str, job_name: str, interval: timedelta) -> bool:
        async with self._pool.acquire() as conn:
            last_run = await conn.fetchval(
                "SELECT last_run_at FROM intelligence_job_runs WHERE company_id = $1 AND job_name = $2",
                company_id,
                job_name,
            )
        if last_run is None:
            return True
        return (datetime.now(timezone.utc) - last_run) >= interval

    async def _run_job(self, company_id: str, job_name: str) -> None:
        try:
            result = await self._manager.run_cycle(company_id, trigger="scheduled")
            if result is not None and job_name in _REPORT_TYPES:
                await self._manager.generate_report(company_id, job_name)
        finally:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO intelligence_job_runs (company_id, job_name, last_run_at)
                    VALUES ($1, $2, now())
                    ON CONFLICT (company_id, job_name) DO UPDATE SET last_run_at = now()
                    """,
                    company_id,
                    job_name,
                )
