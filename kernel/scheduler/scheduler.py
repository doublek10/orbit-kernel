"""
Scheduler (stub)

Background/recurring work (e.g. nightly reconciliation, scheduled
reports). Not implemented yet - candidates are APScheduler for a single
process, or a proper job queue (e.g. Postgres-backed) once this needs to
run across multiple Kernel instances.
"""


class Scheduler:
    async def schedule(self, job_name: str, run_at, payload: dict):
        raise NotImplementedError("Scheduler not implemented yet")
